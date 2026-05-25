#!/usr/bin/env python3
"""Shared reduced-order methods for Design V4-V6 studies."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from design_v0_particle_tracking import EPS0, MEDIUM_EPS_R, MEDIUM_VISCOSITY_PA_S, SpiralSpec, ds_dtheta, point_xy
from design_v2_population_sim import DEAD_DIST, LIVE_DIST, lognormal_positive, truncated_normal_positive
from design_v3_openfoam_hybrid import KB, TEMPERATURE_K, OpenFOAMFieldStats, field_shape, load_openfoam_field_stats, run_openfoam_case


MEDIUM_SIGMA_S_M = 0.002
CHANNEL_HEIGHT_M = 50e-6


@dataclass(frozen=True)
class StudyCell:
    name: str
    radius_m: float
    re_cm: float
    initial_lateral_m: float
    initial_z_m: float
    adhesion_index: float


def complex_permittivity(eps_r: float, sigma: float, omega: float) -> complex:
    return EPS0 * eps_r - 1j * sigma / omega


def re_cm_at_frequency(
    radius_m: float,
    membrane_thickness_m: float,
    membrane_eps_r: float,
    membrane_sigma_s_m: float,
    cytoplasm_eps_r: float,
    cytoplasm_sigma_s_m: float,
    frequency_hz: float,
) -> float:
    omega = 2.0 * math.pi * frequency_hz
    eps_medium = complex_permittivity(MEDIUM_EPS_R, MEDIUM_SIGMA_S_M, omega)
    eps_mem = complex_permittivity(membrane_eps_r, membrane_sigma_s_m, omega)
    eps_cyto = complex_permittivity(cytoplasm_eps_r, cytoplasm_sigma_s_m, omega)
    membrane_capacitance = eps_mem / membrane_thickness_m
    eps_cell = membrane_capacitance * radius_m * eps_cyto / (membrane_capacitance * radius_m + eps_cyto)
    return float(np.real((eps_cell - eps_medium) / (eps_cell + 2.0 * eps_medium)))


def sample_cell(
    rng: np.random.Generator,
    name: str,
    width_m: float,
    frequency_hz: float,
    inlet_offset_ratio: float = 0.0,
    inlet_spread_ratio: float = 1.0,
) -> StudyCell:
    dist = LIVE_DIST if name == "live" else DEAD_DIST
    diameter = truncated_normal_positive(
        rng,
        dist.diameter_mean_m,
        dist.diameter_cv * dist.diameter_mean_m,
        0.65 * dist.diameter_mean_m,
        1.35 * dist.diameter_mean_m,
    )
    radius = 0.5 * diameter
    membrane_thickness = truncated_normal_positive(
        rng,
        dist.membrane_thickness_mean_m,
        dist.membrane_thickness_cv * dist.membrane_thickness_mean_m,
        0.65 * dist.membrane_thickness_mean_m,
        1.35 * dist.membrane_thickness_mean_m,
    )
    re_cm = re_cm_at_frequency(
        radius,
        membrane_thickness,
        dist.membrane_eps_r,
        lognormal_positive(rng, dist.membrane_sigma_mean_s_m, 0.45),
        dist.cytoplasm_eps_r,
        lognormal_positive(rng, dist.cytoplasm_sigma_mean_s_m, 0.35),
        frequency_hz,
    )
    clearance = radius + 2.0e-6
    low = -0.5 * width_m + clearance
    high = 0.5 * width_m - clearance
    center = float(np.clip(inlet_offset_ratio, -0.9, 0.9)) * 0.5 * width_m
    span = max(0.05, float(np.clip(inlet_spread_ratio, 0.05, 1.0))) * (high - low)
    focus_low = max(low, center - 0.5 * span)
    focus_high = min(high, center + 0.5 * span)
    if focus_low >= focus_high:
        focus_low, focus_high = low, high
    lateral = float(rng.uniform(focus_low, focus_high))
    z = float(rng.uniform(clearance, CHANNEL_HEIGHT_M - clearance))
    adhesion_index = float(rng.lognormal(mean=0.0 if name == "live" else 0.35, sigma=0.45))
    return StudyCell(name, radius, re_cm, lateral, z, adhesion_index)


def spiral_length(spec: SpiralSpec, samples: int = 1200) -> float:
    theta = np.linspace(0.0, 2.0 * math.pi * spec.turns, samples)
    values = np.array([ds_dtheta(spec, float(t)) for t in theta])
    return float(np.trapz(values, theta))


def local_axial_velocity(spec: SpiralSpec, lateral_m: float, z_m: float) -> float:
    y = 2.0 * lateral_m / spec.channel_width_m
    z = 2.0 * (z_m / CHANNEL_HEIGHT_M - 0.5)
    profile = max(0.15, (1.0 - 0.65 * y * y) * (1.0 - 0.55 * z * z))
    return spec.inlet_velocity_m_s * profile


def lateral_velocity(
    spec: SpiralSpec,
    cell: StudyCell,
    lateral_m: float,
    z_m: float,
    field_stats: OpenFOAMFieldStats,
    geometry: str,
    dep_enabled: bool,
    dep_sign: float,
    dean_scale: float = 1.0,
) -> float:
    dep_v = 0.0
    if dep_enabled:
        eps_m = EPS0 * MEDIUM_EPS_R
        _, grad_e2 = field_shape(spec, lateral_m, z_m, field_stats)
        dep_v = eps_m * cell.radius_m * cell.radius_m * cell.re_cm * grad_e2 / (3.0 * MEDIUM_VISCOSITY_PA_S)
        dep_v *= 5.0e-4 * dep_sign
    dean_v = 0.0
    if geometry == "spiral":
        dean_v = dean_scale * 0.12e-6 * (spec.inlet_velocity_m_s / 1000e-6) ** 1.35
    shear_lift_v = 0.05e-6 * math.tanh(lateral_m / (0.22 * spec.channel_width_m))
    return dep_v + dean_v + shear_lift_v


def run_particle(
    spec: SpiralSpec,
    cell: StudyCell,
    field_stats: OpenFOAMFieldStats,
    rng: np.random.Generator,
    particle_id: int,
    steps: int,
    frequency_hz: float,
    outlet_split_ratio: float,
    geometry: str = "spiral",
    dep_enabled: bool = True,
    dep_sign: float = 1.0,
    keep_path: bool = False,
    length_m: float | None = None,
    dep_start_fraction: float = 0.0,
    dep_end_fraction: float = 1.0,
    dean_scale: float = 1.0,
) -> tuple[dict, list[dict]]:
    length = spiral_length(spec) if length_m is None else length_m
    theta_end = 2.0 * math.pi * spec.turns
    dtheta = theta_end / steps
    ds_straight = length / steps
    theta = 0.0
    lateral = cell.initial_lateral_m
    z = cell.initial_z_m
    wall_state = ""
    path: list[dict] = []
    diffusion = KB * TEMPERATURE_K / (6.0 * math.pi * MEDIUM_VISCOSITY_PA_S * cell.radius_m)

    for step in range(steps + 1):
        progress = step / steps
        if geometry == "straight":
            x, y = length * progress, lateral
        else:
            x, y = point_xy(spec, theta, lateral)
        if keep_path:
            path.append(
                {
                    "class": cell.name,
                    "particle_id": particle_id,
                    "progress": progress,
                    "theta_rad": theta,
                    "lateral_m": lateral,
                    "x_m": x,
                    "y_m": y,
                }
            )
        if step == steps or wall_state:
            break

        axial_u = local_axial_velocity(spec, lateral, z)
        local_ds = ds_straight if geometry == "straight" else ds_dtheta(spec, theta) * dtheta
        local_dt_s = local_ds / max(1e-9, axial_u)
        dep_active = dep_enabled and dep_start_fraction <= progress <= dep_end_fraction
        lateral += (
            lateral_velocity(spec, cell, lateral, z, field_stats, geometry, dep_active, dep_sign, dean_scale) * local_dt_s
            + math.sqrt(2.0 * diffusion * local_dt_s) * rng.normal()
        )
        z += math.sqrt(2.0 * diffusion * local_dt_s) * rng.normal()
        clearance = cell.radius_m + 1.0e-6
        inner_limit = -0.5 * spec.channel_width_m + clearance
        outer_limit = 0.5 * spec.channel_width_m - clearance
        z = float(np.clip(z, clearance, CHANNEL_HEIGHT_M - clearance))

        if lateral <= inner_limit or lateral >= outer_limit:
            lateral = inner_limit if lateral <= inner_limit else outer_limit
            voltage_risk = (spec.voltage_v / 13.0) ** 2
            adhesion_probability = min(0.95, 0.08 * cell.adhesion_index * voltage_risk)
            if rng.random() < adhesion_probability:
                wall_state = "inner_wall_loss" if lateral <= inner_limit else "outer_wall_loss"
        theta += dtheta

    threshold = -0.5 * spec.channel_width_m + outlet_split_ratio * spec.channel_width_m
    outlet = "lost" if wall_state else ("inner" if lateral < threshold else "outer")
    result = {
        "class": cell.name,
        "particle_id": particle_id,
        "frequency_hz": frequency_hz,
        "radius_um": cell.radius_m * 1e6,
        "re_cm": cell.re_cm,
        "initial_lateral_um": cell.initial_lateral_m * 1e6,
        "final_lateral_um": lateral * 1e6,
        "outlet": outlet,
        "wall_state": wall_state,
    }
    if keep_path and wall_state and path[-1]["progress"] < 1.0:
        last = path[-1]
        for hold_step in range(len(path), steps + 1):
            row = dict(last)
            row["progress"] = hold_step / steps
            path.append(row)
    return result, path


def simulate_population(
    spec: SpiralSpec,
    field_stats: OpenFOAMFieldStats,
    seed: int,
    particles_per_class: int,
    steps: int,
    frequency_hz: float,
    outlet_split_ratio: float,
    geometry: str = "spiral",
    dep_enabled: bool = True,
    dep_sign: float = 1.0,
    keep_paths: bool = False,
    inlet_offset_ratio: float = 0.0,
    inlet_spread_ratio: float = 1.0,
    dep_start_fraction: float = 0.0,
    dep_end_fraction: float = 1.0,
    dean_scale: float = 1.0,
) -> tuple[list[dict], dict, list[dict]]:
    rng = np.random.default_rng(seed)
    results = []
    paths = []
    pid = 0
    length_m = spiral_length(spec)
    for name in ["live", "dead"]:
        for _ in range(particles_per_class):
            cell = sample_cell(
                rng,
                name,
                spec.channel_width_m,
                frequency_hz,
                inlet_offset_ratio=inlet_offset_ratio,
                inlet_spread_ratio=inlet_spread_ratio,
            )
            result, path = run_particle(
                spec,
                cell,
                field_stats,
                rng,
                pid,
                steps,
                frequency_hz,
                outlet_split_ratio,
                geometry,
                dep_enabled,
                dep_sign,
                keep_paths,
                length_m,
                dep_start_fraction,
                dep_end_fraction,
                dean_scale,
            )
            results.append(result)
            paths.extend(path)
            pid += 1
    return results, summarize(results, spec, seed, frequency_hz, outlet_split_ratio, geometry, dep_enabled, dep_sign), paths


def summarize(
    results: list[dict],
    spec: SpiralSpec,
    seed: int,
    frequency_hz: float,
    outlet_split_ratio: float,
    geometry: str,
    dep_enabled: bool,
    dep_sign: float,
) -> dict:
    live = [r for r in results if r["class"] == "live"]
    dead = [r for r in results if r["class"] == "dead"]
    live_inner = sum(r["outlet"] == "inner" for r in live)
    live_outer = sum(r["outlet"] == "outer" for r in live)
    dead_inner = sum(r["outlet"] == "inner" for r in dead)
    dead_outer = sum(r["outlet"] == "outer" for r in dead)
    lost = sum(r["outlet"] == "lost" for r in results)
    total = len(results)
    final_live = np.array([r["final_lateral_um"] for r in live])
    final_dead = np.array([r["final_lateral_um"] for r in dead])
    correct_a = (live_inner + dead_outer) / total
    correct_b = (live_outer + dead_inner) / total
    return {
        "case_id": (
            f"{geometry}_dep_{int(dep_enabled)}_sign_{dep_sign:g}_"
            f"f_{frequency_hz / 1000:g}kHz_V_{spec.voltage_v:g}_"
            f"u_{spec.inlet_velocity_m_s * 1e6:.0f}_split_{outlet_split_ratio:g}"
        ),
        "seed": seed,
        "geometry": geometry,
        "dep_enabled": dep_enabled,
        "dep_sign": dep_sign,
        "frequency_hz": frequency_hz,
        "turns": spec.turns,
        "pitch_um": spec.pitch_m * 1e6,
        "channel_width_um": spec.channel_width_m * 1e6,
        "voltage_v": spec.voltage_v,
        "velocity_um_s": spec.inlet_velocity_m_s * 1e6,
        "outlet_split_ratio": outlet_split_ratio,
        "correct_A_live_inner_dead_outer": correct_a,
        "correct_B_live_outer_dead_inner": correct_b,
        "target_correct": max(correct_a, correct_b),
        "preferred_direction": "A_live_inner_dead_outer" if correct_a >= correct_b else "B_live_outer_dead_inner",
        "live_recovery_A": live_inner / len(live),
        "dead_removal_A": dead_outer / len(dead),
        "wall_loss": lost / total,
        "live_final_lateral_mean_um": float(np.mean(final_live)),
        "dead_final_lateral_mean_um": float(np.mean(final_dead)),
        "distribution_gap_um": float(abs(np.mean(final_live) - np.mean(final_dead))),
    }


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
