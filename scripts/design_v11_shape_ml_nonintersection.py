#!/usr/bin/env python3
"""Design V11 clean-shape ML screening with non-intersection constraints.

V11 extends V10 in two ways:

* more named, smooth, formula-defined shape families are screened;
* every candidate centerline is checked for self-intersection before it is
  accepted for simulation.

The solver remains a reduced-order particle model. The reported candidates are
therefore screening-quality designs, not final electrode-resolved CFD/FEM
claims.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor

from design_v7_geometry_feasibility import CP_WATER_J_KG_K, MU_PA_S, RHO_WATER_KG_M3, performance_metrics, read_balanced_v6
from optimization_v1_surrogate import make_spec
from study_common import (
    CHANNEL_HEIGHT_M,
    MEDIUM_SIGMA_S_M,
    load_openfoam_field_stats,
    run_openfoam_case,
    run_particle,
    sample_cell,
    summarize,
    write_csv,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "design_v11_shape_ml_nonintersection"


@dataclass(frozen=True)
class CleanFamily:
    name: str
    equation: str
    shape_class: str
    turns: tuple[float, float]
    radius_um: tuple[float, float]
    pitch_um: tuple[float, float]
    width_um: tuple[float, float]
    eccentricity: tuple[float, float]
    curvature_power: tuple[float, float]
    inlet_kind: str
    inlet_length_um: tuple[float, float]
    dep_start: tuple[float, float]
    dep_end: tuple[float, float]
    electrode_gap_um: tuple[float, float]
    electrode_coverage: tuple[float, float]
    dean_base: tuple[float, float]
    note: str


FAMILIES = [
    CleanFamily(
        "circular_archimedean_short",
        "r(theta)=a+b theta",
        "circular_spiral",
        (0.95, 2.10),
        (470, 920),
        (75, 170),
        (95, 165),
        (1.00, 1.00),
        (1.00, 1.00),
        "tangential",
        (180, 650),
        (0.18, 0.48),
        (0.58, 0.92),
        (28, 80),
        (0.28, 0.68),
        (0.55, 1.15),
        "Clean compact Archimedean reference.",
    ),
    CleanFamily(
        "elliptic_archimedean_short",
        "x=(a+b theta) cos(theta), y=e(a+b theta) sin(theta)",
        "elliptic_spiral",
        (0.90, 2.00),
        (520, 1100),
        (70, 165),
        (95, 175),
        (0.52, 0.86),
        (1.00, 1.00),
        "major_axis_prefocus",
        (240, 850),
        (0.16, 0.44),
        (0.56, 0.90),
        (25, 72),
        (0.32, 0.75),
        (0.70, 1.35),
        "Symmetric elliptical spiral; tests whether anisotropic curvature helps shorten the channel.",
    ),
    CleanFamily(
        "monotone_curvature_spiral",
        "r(theta)=r0/(1+k theta)^p",
        "monotone_curvature_spiral",
        (0.85, 1.90),
        (850, 1650),
        (55, 125),
        (95, 170),
        (1.00, 1.00),
        (0.75, 1.45),
        "outer_low_curvature_entry",
        (220, 760),
        (0.18, 0.50),
        (0.58, 0.94),
        (26, 75),
        (0.30, 0.72),
        (0.65, 1.30),
        "Curvature increases smoothly along the path instead of adding arbitrary waves.",
    ),
    CleanFamily(
        "elliptic_prefocus_spiral",
        "straight inlet + x=(a+b theta) cos(theta), y=e(a+b theta) sin(theta)",
        "elliptic_spiral_with_inlet",
        (0.80, 1.80),
        (500, 1050),
        (65, 150),
        (90, 165),
        (0.48, 0.80),
        (1.00, 1.00),
        "straight_prefocus",
        (500, 1400),
        (0.20, 0.52),
        (0.60, 0.95),
        (24, 70),
        (0.35, 0.78),
        (0.62, 1.20),
        "Explicit inlet-focusing segment followed by an elliptical spiral.",
    ),
    CleanFamily(
        "superellipse_oval_spiral",
        "x=r sign(cos(theta))|cos(theta)|^q, y=e r sign(sin(theta))|sin(theta)|^q",
        "superellipse_oval",
        (0.85, 1.85),
        (520, 1150),
        (70, 155),
        (95, 175),
        (0.55, 0.88),
        (0.62, 0.88),
        "rounded_oval_entry",
        (260, 900),
        (0.18, 0.48),
        (0.58, 0.92),
        (26, 78),
        (0.30, 0.72),
        (0.58, 1.18),
        "Smooth oval/stadium-like compact spiral, not a random curve.",
    ),
    CleanFamily(
        "concentric_electrode_spiral",
        "r(theta)=a+b theta with constant electrode gap g",
        "circular_spiral",
        (1.20, 2.35),
        (520, 980),
        (70, 150),
        (95, 160),
        (1.00, 1.00),
        (1.00, 1.00),
        "dual_side_electrode_entry",
        (220, 800),
        (0.22, 0.54),
        (0.62, 0.96),
        (20, 58),
        (0.42, 0.82),
        (0.65, 1.28),
        "Closest clean abstraction of the reference-style concentric-electrode spiral.",
    ),
    CleanFamily(
        "logarithmic_spiral_short",
        "r(theta)=a exp(k theta)",
        "logarithmic_spiral",
        (0.75, 1.65),
        (430, 950),
        (45, 135),
        (90, 160),
        (1.00, 1.00),
        (1.00, 1.00),
        "tangential",
        (180, 700),
        (0.16, 0.46),
        (0.56, 0.90),
        (24, 70),
        (0.30, 0.72),
        (0.58, 1.20),
        "Smooth logarithmic spiral; constant growth ratio rather than arbitrary modulation.",
    ),
    CleanFamily(
        "elliptic_logarithmic_spiral",
        "x=a exp(k theta) cos(theta), y=e a exp(k theta) sin(theta)",
        "elliptic_logarithmic_spiral",
        (0.70, 1.55),
        (450, 1000),
        (45, 125),
        (90, 165),
        (0.52, 0.84),
        (1.00, 1.00),
        "major_axis_prefocus",
        (240, 850),
        (0.16, 0.46),
        (0.56, 0.90),
        (24, 70),
        (0.32, 0.75),
        (0.65, 1.30),
        "Elliptic logarithmic spiral for controlled anisotropic curvature.",
    ),
    CleanFamily(
        "fermat_spiral_short",
        "r(theta)=a sqrt(1+k theta)",
        "fermat_spiral",
        (0.85, 1.85),
        (430, 980),
        (55, 145),
        (90, 165),
        (1.00, 1.00),
        (1.00, 1.00),
        "tangential",
        (180, 680),
        (0.16, 0.46),
        (0.56, 0.90),
        (24, 72),
        (0.30, 0.72),
        (0.55, 1.18),
        "Fermat-like spiral with slower radial growth and compact footprint.",
    ),
    CleanFamily(
        "elliptic_s_bend_prefocus_spiral",
        "S-bend inlet + x=(a+b theta) cos(theta), y=e(a+b theta) sin(theta)",
        "elliptic_spiral_with_s_bend",
        (0.70, 1.55),
        (460, 1000),
        (60, 145),
        (90, 160),
        (0.50, 0.82),
        (1.00, 1.00),
        "s_bend_prefocus",
        (520, 1500),
        (0.20, 0.52),
        (0.60, 0.95),
        (24, 70),
        (0.35, 0.78),
        (0.60, 1.20),
        "Smooth S-bend focusing inlet followed by a clean elliptic spiral.",
    ),
    CleanFamily(
        "short_circular_c_arc",
        "partial circular spiral arc r(theta)=a+b theta, theta<1.2 turns",
        "short_c_arc",
        (0.45, 1.15),
        (520, 1250),
        (55, 150),
        (90, 170),
        (1.00, 1.00),
        (1.00, 1.00),
        "dual_side_electrode_entry",
        (260, 900),
        (0.12, 0.40),
        (0.52, 0.88),
        (20, 62),
        (0.40, 0.85),
        (0.25, 0.80),
        "Very short C-arc/facing-electrode reference geometry.",
    ),
]


FEATURES = [
    "family_id",
    "log_frequency_hz",
    "voltage_v",
    "velocity_um_s",
    "turns",
    "radius_um",
    "pitch_um_per_rad",
    "width_um",
    "eccentricity",
    "curvature_power",
    "inlet_length_um",
    "inlet_offset_ratio",
    "inlet_spread_ratio",
    "dep_start_fraction",
    "dep_end_fraction",
    "electrode_gap_um",
    "electrode_coverage",
    "field_gain",
    "dean_scale",
]


def sigmoid(x: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-x))


def family_index(name: str) -> int:
    return [f.name for f in FAMILIES].index(name)


def uniform(rng: np.random.Generator, bounds: tuple[float, float]) -> float:
    return float(rng.uniform(bounds[0], bounds[1]))


def field_gain_from_electrodes(width_m: float, gap_m: float, coverage: float, family: CleanFamily) -> float:
    gap_ratio = width_m / max(gap_m, 1e-12)
    family_boost = 1.06 if "electrode" in family.name else 1.0
    raw = 1.0 + 0.18 * coverage * max(0.0, gap_ratio - 1.0)
    return float(np.clip(raw * family_boost, 1.0, 1.75))


def sample_candidate(family: CleanFamily, base: dict, rng: np.random.Generator) -> dict:
    width_m = uniform(rng, family.width_um) * 1e-6
    gap_m = uniform(rng, family.electrode_gap_um) * 1e-6
    coverage = uniform(rng, family.electrode_coverage)
    dep_start = uniform(rng, family.dep_start)
    dep_end = uniform(rng, family.dep_end)
    if dep_end <= dep_start + 0.16:
        dep_end = min(0.98, dep_start + 0.16)
    inlet_spread = uniform(rng, (0.10, 0.42))
    if "prefocus" in family.inlet_kind or "electrode_entry" in family.inlet_kind:
        inlet_spread = uniform(rng, (0.07, 0.28))
    sample = {
        "family": family.name,
        "equation": family.equation,
        "shape_class": family.shape_class,
        "inlet_kind": family.inlet_kind,
        "frequency_hz": float(np.clip(base["frequency_hz"] * rng.uniform(0.75, 1.40), 250e3, 3.2e6)),
        "voltage_v": float(rng.uniform(8.0, 23.0)),
        "velocity_m_s": float(rng.uniform(850e-6, 5200e-6)),
        "turns": uniform(rng, family.turns),
        "radius_m": uniform(rng, family.radius_um) * 1e-6,
        "pitch_m_per_rad": uniform(rng, family.pitch_um) * 1e-6 / (2.0 * math.pi),
        "channel_width_m": width_m,
        "eccentricity": uniform(rng, family.eccentricity),
        "curvature_power": uniform(rng, family.curvature_power),
        "inlet_length_m": uniform(rng, family.inlet_length_um) * 1e-6,
        "outlet_split_ratio": float(rng.uniform(0.30, 0.58)),
        "inlet_offset_ratio": float(rng.uniform(-0.82, -0.32)),
        "inlet_spread_ratio": inlet_spread,
        "dep_start_fraction": dep_start,
        "dep_end_fraction": dep_end,
        "dep_edge_smoothness": float(rng.uniform(0.018, 0.052)),
        "electrode_gap_m": gap_m,
        "electrode_coverage": coverage,
        "field_gain": field_gain_from_electrodes(width_m, gap_m, coverage, family),
        "dep_sign": -1.0,
        "dean_base": uniform(rng, family.dean_base),
        "note": family.note,
    }
    sample["dean_scale"] = dean_scale(sample)
    return sample


def theta_grid(sample: dict, n: int = 1200) -> np.ndarray:
    return np.linspace(0.0, 2.0 * math.pi * sample["turns"], n)


def centerline(sample: dict, n: int = 1200) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    theta = theta_grid(sample, n)
    family = sample["family"]
    a = sample["radius_m"]
    b = sample["pitch_m_per_rad"]
    e = sample["eccentricity"]
    q = sample["curvature_power"]

    if family == "monotone_curvature_spiral":
        # Starts with low curvature and smoothly tightens. The pitch parameter
        # is converted into a dimensionless curvature growth coefficient.
        k = max(0.03, b / max(a, 1e-12) * 3.0)
        r = a / np.power(1.0 + k * theta, q)
    elif family in {"logarithmic_spiral_short", "elliptic_logarithmic_spiral"}:
        k = np.clip(b / max(a, 1e-12), 0.004, 0.055)
        r = a * np.exp(k * theta)
    elif family == "fermat_spiral_short":
        k = np.clip(6.0 * b / max(a, 1e-12), 0.05, 0.95)
        r = a * np.sqrt(1.0 + k * theta)
    else:
        r = a + b * theta

    if family == "superellipse_oval_spiral":
        c = np.cos(theta)
        s = np.sin(theta)
        x = r * np.sign(c) * np.power(np.abs(c), q)
        y = e * r * np.sign(s) * np.power(np.abs(s), q)
    elif "elliptic" in family:
        x = r * np.cos(theta)
        y = e * r * np.sin(theta)
    else:
        x = r * np.cos(theta)
        y = r * np.sin(theta)

    if sample["inlet_kind"] in {"straight_prefocus", "major_axis_prefocus", "dual_side_electrode_entry", "rounded_oval_entry", "outer_low_curvature_entry", "tangential", "s_bend_prefocus"}:
        inlet_n = max(24, int(0.12 * n))
        x0, y0 = x[0], y[0]
        dx, dy = x[1] - x[0], y[1] - y[0]
        norm = max(1e-12, math.hypot(dx, dy))
        tx, ty = dx / norm, dy / norm
        nx, ny = -ty, tx
        s_in = np.linspace(-sample["inlet_length_m"], 0.0, inlet_n)
        inlet_x = x0 + tx * s_in
        inlet_y = y0 + ty * s_in
        if sample["inlet_kind"] == "s_bend_prefocus":
            u = np.linspace(0.0, 1.0, inlet_n)
            amp = 0.32 * sample["channel_width_m"]
            offset = amp * np.sin(2.0 * math.pi * u) * (1.0 - 0.15 * u)
            inlet_x = inlet_x + nx * offset
            inlet_y = inlet_y + ny * offset
        x = np.concatenate([inlet_x[:-1], x])
        y = np.concatenate([inlet_y[:-1], y])
        theta = np.concatenate([np.full(inlet_n - 1, theta[0]), theta])
    return theta, x, y


def path_length(sample: dict) -> float:
    _, x, y = centerline(sample, n=1500)
    return float(np.sum(np.hypot(np.diff(x), np.diff(y))))


def _orient(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    return float((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))


def _segments_intersect(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> bool:
    o1 = _orient(a, b, c)
    o2 = _orient(a, b, d)
    o3 = _orient(c, d, a)
    o4 = _orient(c, d, b)
    return (o1 * o2 < 0.0) and (o3 * o4 < 0.0)


def geometry_screen(sample: dict, n: int = 180) -> dict:
    _, x, y = centerline(sample, n=n)
    pts = np.column_stack([x, y])
    intersects = False
    for i in range(len(pts) - 1):
        for j in range(i + 3, len(pts) - 1):
            if i == 0 and j >= len(pts) - 3:
                continue
            if _segments_intersect(pts[i], pts[i + 1], pts[j], pts[j + 1]):
                intersects = True
                break
        if intersects:
            break

    min_nonlocal = float("inf")
    skip = max(8, len(pts) // 35)
    for i in range(len(pts)):
        lo = min(len(pts), i + skip)
        if lo >= len(pts):
            continue
        dist = np.hypot(pts[lo:, 0] - pts[i, 0], pts[lo:, 1] - pts[i, 1])
        if len(dist):
            min_nonlocal = min(min_nonlocal, float(np.min(dist)))
    if not math.isfinite(min_nonlocal):
        min_nonlocal = 1.0
    channel_overlap = min_nonlocal < 1.08 * sample["channel_width_m"]
    return {
        "self_intersects": intersects,
        "min_nonlocal_clearance_um": min_nonlocal * 1e6,
        "channel_overlap_flag": channel_overlap,
        "geometry_valid": (not intersects) and (not channel_overlap),
    }


def curvature_stats(sample: dict) -> dict:
    _, x, y = centerline(sample, n=1800)
    ds = np.hypot(np.diff(x), np.diff(y))
    good = ds > 1e-12
    dx = np.gradient(x)
    dy = np.gradient(y)
    ddx = np.gradient(dx)
    ddy = np.gradient(dy)
    kappa = np.abs(dx * ddy - dy * ddx) / np.maximum((dx * dx + dy * dy) ** 1.5, 1e-18)
    kappa = kappa[np.isfinite(kappa)]
    mean_k = float(np.mean(kappa))
    p95_k = float(np.percentile(kappa, 95))
    min_radius = 1.0 / max(1e-12, p95_k)
    return {
        "mean_curvature_1_m": mean_k,
        "p95_curvature_1_m": p95_k,
        "min_curvature_radius_um": min_radius * 1e6,
        "smoothness_index": float(np.std(kappa) / max(1e-12, mean_k)),
        "path_samples_valid": int(np.sum(good)),
    }


def dean_scale(sample: dict) -> float:
    stats = curvature_stats({**sample, "dean_scale": 1.0}) if "dean_base" in sample else {"mean_curvature_1_m": 650.0, "smoothness_index": 0.25}
    curvature_gain = np.clip(stats["mean_curvature_1_m"] / 650.0, 0.45, 1.65)
    smooth_penalty = 1.0 / (1.0 + 0.10 * max(0.0, stats["smoothness_index"] - 0.8))
    return float(np.clip(sample["dean_base"] * curvature_gain * smooth_penalty, 0.15, 1.75))


def active_fraction_smooth(sample: dict) -> float:
    p = np.linspace(0, 1, 300)
    ell = sample["dep_edge_smoothness"]
    alpha = sigmoid((p - sample["dep_start_fraction"]) / ell) * (1.0 - sigmoid((p - sample["dep_end_fraction"]) / ell))
    return float(np.trapz(alpha, p))


def sample_to_spec(sample: dict, effective_voltage: bool = True):
    return make_spec(
        {
            "turns": sample["turns"],
            "inner_radius_m": sample["radius_m"],
            "pitch_m": sample["pitch_m_per_rad"] * 2.0 * math.pi,
            "channel_width_m": sample["channel_width_m"],
            "voltage_v": sample["voltage_v"] * (sample["field_gain"] if effective_voltage else 1.0),
            "velocity_m_s": sample["velocity_m_s"],
        }
    )


def feasibility(sample: dict, length_m: float) -> dict:
    width = sample["channel_width_m"]
    height = CHANNEL_HEIGHT_M
    velocity = sample["velocity_m_s"]
    flow_m3_s = velocity * width * height
    aspect = min(height, width) / max(height, width)
    correction = max(0.12, 1.0 - 0.63 * aspect)
    pressure_pa = 12.0 * MU_PA_S * length_m * flow_m3_s / (width * height**3 * correction)
    hydraulic_diameter = 2.0 * width * height / (width + height)
    reynolds = RHO_WATER_KG_M3 * velocity * hydraulic_diameter / MU_PA_S
    effective_field = sample["voltage_v"] * sample["field_gain"] / max(1e-12, sample["electrode_gap_m"])
    volume_m3 = length_m * width * height
    active_power_w = MEDIUM_SIGMA_S_M * effective_field**2 * volume_m3 * active_fraction_smooth(sample)
    residence_s = length_m / max(1e-12, velocity)
    adiabatic_delta_c = active_power_w * residence_s / max(1e-18, RHO_WATER_KG_M3 * CP_WATER_J_KG_K * volume_m3)
    _, x, y = centerline(sample, n=900)
    footprint_m2 = (x.max() - x.min() + width) * (y.max() - y.min() + width)
    steady_delta_c = active_power_w * 1.0e-3 / max(1e-18, 0.20 * footprint_m2)
    curv = curvature_stats(sample)
    geom = geometry_screen(sample)
    bend_ok = curv["min_curvature_radius_um"] > 1.8 * width * 1e6
    gap_ok = sample["electrode_gap_m"] >= 20e-6
    thermal_risk = "low"
    if active_power_w * 1000 > 30.0 or steady_delta_c > 12.0:
        thermal_risk = "high"
    elif active_power_w * 1000 > 12.0 or steady_delta_c > 6.0:
        thermal_risk = "moderate"
    return {
        "length_mm": length_m * 1e3,
        "footprint_mm2": footprint_m2 * 1e6,
        "residence_s": residence_s,
        "flow_uL_min": flow_m3_s * 1e9 * 60.0,
        "pressure_drop_kPa": pressure_pa / 1000.0,
        "reynolds": reynolds,
        "effective_field_kV_m": effective_field / 1000.0,
        "active_joule_power_mW": active_power_w * 1000.0,
        "adiabatic_delta_c_proxy": adiabatic_delta_c,
        "steady_substrate_delta_c_proxy": steady_delta_c,
        "thermal_risk": thermal_risk,
        "manufacturable_gap_ok": gap_ok,
        "manufacturable_bend_ok": bend_ok,
        "manufacturable_no_intersection_ok": geom["geometry_valid"],
        "self_intersects": geom["self_intersects"],
        "channel_overlap_flag": geom["channel_overlap_flag"],
        "min_nonlocal_clearance_um": geom["min_nonlocal_clearance_um"],
        **curv,
    }


def simulate(
    sample: dict,
    field_stats,
    seed: int,
    particles_per_class: int,
    steps: int,
    dep_enabled: bool = True,
    geometry_override: str | None = None,
    inlet_override: tuple[float, float] | None = None,
):
    rng = np.random.default_rng(seed)
    spec = sample_to_spec(sample, effective_voltage=True)
    length_m = path_length(sample)
    inlet_offset = sample["inlet_offset_ratio"]
    inlet_spread = sample["inlet_spread_ratio"]
    if inlet_override is not None:
        inlet_offset, inlet_spread = inlet_override
    results = []
    pid = 0
    for name in ["live", "dead"]:
        for _ in range(particles_per_class):
            cell = sample_cell(rng, name, spec.channel_width_m, sample["frequency_hz"], inlet_offset, inlet_spread)
            result, _ = run_particle(
                spec,
                cell,
                field_stats,
                rng,
                pid,
                steps,
                sample["frequency_hz"],
                sample["outlet_split_ratio"],
                geometry=geometry_override or "spiral",
                dep_enabled=dep_enabled,
                dep_sign=sample["dep_sign"],
                keep_path=False,
                length_m=length_m,
                dep_start_fraction=sample["dep_start_fraction"],
                dep_end_fraction=sample["dep_end_fraction"],
                dean_scale=sample["dean_scale"],
            )
            results.append(result)
            pid += 1
    summary = summarize(
        results,
        spec,
        seed,
        sample["frequency_hz"],
        sample["outlet_split_ratio"],
        geometry_override or "spiral",
        dep_enabled,
        sample["dep_sign"],
    )
    return results, summary, length_m


def run_row(sample: dict, field_stats, sample_id: int, seed: int, stage: str, particles: int, steps: int) -> dict:
    particles_rows, summary, length_m = simulate(sample, field_stats, seed, particles, steps)
    row = {
        "stage": stage,
        "sample_id": sample_id,
        "seed": seed,
        "family": sample["family"],
        "equation": sample["equation"],
        "shape_class": sample["shape_class"],
        "inlet_kind": sample["inlet_kind"],
        "frequency_hz": sample["frequency_hz"],
        "voltage_v": sample["voltage_v"],
        "effective_voltage_v": sample["voltage_v"] * sample["field_gain"],
        "velocity_um_s": sample["velocity_m_s"] * 1e6,
        "turns": sample["turns"],
        "radius_um": sample["radius_m"] * 1e6,
        "pitch_um_per_turn": sample["pitch_m_per_rad"] * 2.0 * math.pi * 1e6,
        "width_um": sample["channel_width_m"] * 1e6,
        "eccentricity": sample["eccentricity"],
        "curvature_power": sample["curvature_power"],
        "inlet_length_um": sample["inlet_length_m"] * 1e6,
        "inlet_offset_ratio": sample["inlet_offset_ratio"],
        "inlet_spread_ratio": sample["inlet_spread_ratio"],
        "dep_start_fraction": sample["dep_start_fraction"],
        "dep_end_fraction": sample["dep_end_fraction"],
        "electrode_gap_um": sample["electrode_gap_m"] * 1e6,
        "electrode_coverage": sample["electrode_coverage"],
        "field_gain": sample["field_gain"],
        "dean_scale": sample["dean_scale"],
    }
    row.update(performance_metrics(particles_rows, summary))
    row.update(feasibility(sample, length_m))
    row["short_channel_score"] = (row["target_correct"] - 0.50) / max(1e-9, row["length_mm"])
    row["v11_score"] = (
        row["target_correct"]
        + 15.0 * row["short_channel_score"]
        - 1.2 * row["wall_loss"]
        - 0.010 * max(0.0, row["length_mm"] - 18.0)
        - 0.010 * max(0.0, row["residence_s"] - 12.0)
        - 0.004 * max(0.0, row["active_joule_power_mW"] - 10.0)
        - {"low": 0.0, "moderate": 0.05, "high": 0.16}[row["thermal_risk"]]
        - (0.08 if not row["manufacturable_gap_ok"] else 0.0)
        - (0.08 if not row["manufacturable_bend_ok"] else 0.0)
        - (0.25 if not row["manufacturable_no_intersection_ok"] else 0.0)
    )
    return row


def feature(sample: dict) -> list[float]:
    return [
        family_index(sample["family"]),
        math.log10(sample["frequency_hz"]),
        sample["voltage_v"],
        sample["velocity_m_s"] * 1e6,
        sample["turns"],
        sample["radius_m"] * 1e6,
        sample["pitch_m_per_rad"] * 1e6,
        sample["channel_width_m"] * 1e6,
        sample["eccentricity"],
        sample["curvature_power"],
        sample["inlet_length_m"] * 1e6,
        sample["inlet_offset_ratio"],
        sample["inlet_spread_ratio"],
        sample["dep_start_fraction"],
        sample["dep_end_fraction"],
        sample["electrode_gap_m"] * 1e6,
        sample["electrode_coverage"],
        sample["field_gain"],
        sample["dean_scale"],
    ]


def aggregate(rows: list[dict]) -> list[dict]:
    grouped: dict[int, list[dict]] = {}
    for row in rows:
        grouped.setdefault(int(row["sample_id"]), []).append(row)
    out = []
    for sample_id, items in grouped.items():
        first = items[0]
        out.append(
            {
                "sample_id": sample_id,
                "family": first["family"],
                "equation": first["equation"],
                "shape_class": first["shape_class"],
                "inlet_kind": first["inlet_kind"],
                "mean_target_correct": float(np.mean([r["target_correct"] for r in items])),
                "std_target_correct": float(np.std([r["target_correct"] for r in items], ddof=1)) if len(items) > 1 else 0.0,
                "mean_wall_loss": float(np.mean([r["wall_loss"] for r in items])),
                "mean_live_recovery": float(np.mean([r["live_recovery"] for r in items])),
                "mean_dead_removal": float(np.mean([r["dead_removal"] for r in items])),
                "mean_live_outlet_purity": float(np.mean([r["live_outlet_purity"] for r in items])),
                "mean_dead_outlet_purity": float(np.mean([r["dead_outlet_purity"] for r in items])),
                "length_mm": first["length_mm"],
                "footprint_mm2": first["footprint_mm2"],
                "residence_s": first["residence_s"],
                "flow_uL_min": first["flow_uL_min"],
                "active_joule_power_mW": first["active_joule_power_mW"],
                "steady_substrate_delta_c_proxy": first["steady_substrate_delta_c_proxy"],
                "thermal_risk": first["thermal_risk"],
                "manufacturable_gap_ok": first["manufacturable_gap_ok"],
                "manufacturable_bend_ok": first["manufacturable_bend_ok"],
                "manufacturable_no_intersection_ok": first["manufacturable_no_intersection_ok"],
                "self_intersects": first["self_intersects"],
                "channel_overlap_flag": first["channel_overlap_flag"],
                "min_nonlocal_clearance_um": first["min_nonlocal_clearance_um"],
                "min_curvature_radius_um": first["min_curvature_radius_um"],
                "short_channel_score": float(np.mean([r["short_channel_score"] for r in items])),
                "v11_score": float(np.mean([r["v11_score"] for r in items])),
            }
        )
    out.sort(key=lambda r: (r["v11_score"], r["mean_target_correct"]), reverse=True)
    return out


def write_shape_data(sample: dict, out_dir: Path, prefix: str) -> None:
    theta, x, y = centerline(sample, n=1600)
    rows = []
    for i, (t, xi, yi) in enumerate(zip(theta, x, y)):
        p = i / (len(theta) - 1)
        alpha = sigmoid((p - sample["dep_start_fraction"]) / sample["dep_edge_smoothness"]) * (
            1.0 - sigmoid((p - sample["dep_end_fraction"]) / sample["dep_edge_smoothness"])
        )
        rows.append(
            {
                "index": i,
                "progress": p,
                "theta_rad": t,
                "x_m": xi,
                "y_m": yi,
                "channel_width_m": sample["channel_width_m"],
                "electrode_gap_m": sample["electrode_gap_m"],
                "alpha_dep": alpha,
            }
        )
    write_csv(rows, out_dir / f"{prefix}_centerline.csv")
    (out_dir / f"{prefix}_formula.json").write_text(json.dumps(sample, indent=2) + "\n", encoding="utf-8")


def plot_gallery(validation: list[dict], samples: list[dict]) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 3, figsize=(10, 6.5))
    axes = axes.ravel()
    for ax, row in zip(axes, validation[:6]):
        sample = samples[int(row["sample_id"])]
        _, x, y = centerline(sample, n=1300)
        p = np.linspace(0, 1, len(x))
        alpha = sigmoid((p - sample["dep_start_fraction"]) / sample["dep_edge_smoothness"]) * (
            1.0 - sigmoid((p - sample["dep_end_fraction"]) / sample["dep_edge_smoothness"])
        )
        ax.plot(x * 1e3, y * 1e3, color="#111827", lw=2.1)
        ax.scatter(x[::10] * 1e3, y[::10] * 1e3, c=alpha[::10], cmap="viridis", s=10, zorder=3)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"{row['family'].replace('_', ' ')}\nC={row['mean_target_correct']:.3f}, L={row['length_mm']:.1f} mm", fontsize=8)
    for ax in axes[len(validation[:6]) :]:
        ax.axis("off")
    fig.suptitle("V11 non-intersecting formula finalists; color shows DEP activation", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "v11_clean_shape_gallery.png", dpi=260)
    plt.close(fig)


def plot_metrics(rows: list[dict], validation: list[dict], controls: list[dict]) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(8, 5))
    fams = sorted(set(r["family"] for r in rows))
    colors = {fam: plt.cm.tab10(i) for i, fam in enumerate(fams)}
    for fam in fams:
        sub = [r for r in rows if r["family"] == fam]
        ax.scatter([r["length_mm"] for r in sub], [r["target_correct"] for r in sub], s=22, alpha=0.55, color=colors[fam], label=fam.replace("_", " "))
    ax.axhline(0.80, color="#111827", ls="--", lw=1)
    ax.axvline(20.0, color="#6b7280", ls=":", lw=1)
    ax.set_xlabel("Channel length (mm)")
    ax.set_ylabel("Target correct")
    ax.set_title("V11 clean shape screening with non-intersection filter")
    ax.legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "v11_accuracy_vs_length.png", dpi=260)
    plt.close(fig)

    labels = [r["family"].replace("_", "\n") for r in validation]
    x = np.arange(len(labels))
    control_map = {(r["sample_id"], r["control"]): r for r in controls}
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - 0.25, [r["mean_target_correct"] for r in validation], 0.25, label="validated", color="#2a9d8f")
    ax.bar(
        x,
        [control_map[(r["sample_id"], "same_length_straight_dep")]["mean_target_correct"] for r in validation],
        0.25,
        label="straight DEP",
        color="#8d99ae",
    )
    ax.bar(
        x + 0.25,
        [control_map[(r["sample_id"], "no_dep")]["mean_target_correct"] for r in validation],
        0.25,
        label="no DEP",
        color="#e76f51",
    )
    ax.axhline(0.80, color="#111827", ls="--", lw=1)
    ax.set_xticks(x, labels, fontsize=7)
    ax.set_ylabel("Target correct")
    ax.set_title("V11 held-out validation and controls")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "v11_validation_controls.png", dpi=260)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(
        [r["length_mm"] for r in validation],
        [r["topology_gain_vs_straight"] for r in validation],
        c=[r["mean_target_correct"] for r in validation],
        cmap="viridis",
        s=90,
        edgecolor="#111827",
    )
    ax.axhline(0.08, color="#111827", ls="--", lw=1)
    ax.axvline(20.0, color="#6b7280", ls=":", lw=1)
    ax.set_xlabel("Length (mm)")
    ax.set_ylabel("Gain vs same-length straight DEP")
    ax.set_title("V11 geometry contribution check")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "v11_topology_gain_vs_length.png", dpi=260)
    plt.close(fig)


def accepted_sample(family: CleanFamily, base: dict, rng: np.random.Generator, max_length_mm: float = 26.0) -> tuple[dict | None, str]:
    sample = sample_candidate(family, base, rng)
    geom = geometry_screen(sample, n=100)
    if not geom["geometry_valid"]:
        return None, "intersection_or_overlap"
    if path_length(sample) * 1e3 > max_length_mm:
        return None, "too_long"
    return sample, "accepted"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_openfoam_case()
    field_stats = load_openfoam_field_stats()
    base = read_balanced_v6()
    rng = np.random.default_rng(11110)

    samples: list[dict] = []
    rows: list[dict] = []
    rejection_rows: list[dict] = []
    for family in FAMILIES:
        accepted = 0
        attempts = 0
        rejected_intersection = 0
        rejected_length = 0
        while accepted < 18 and attempts < 250:
            attempts += 1
            sample, reason = accepted_sample(family, base, rng, max_length_mm=26.0)
            if sample is None:
                if reason == "intersection_or_overlap":
                    rejected_intersection += 1
                elif reason == "too_long":
                    rejected_length += 1
                continue
            samples.append(sample)
            accepted += 1
        rejection_rows.append(
            {
                "family": family.name,
                "stage": "initial_sampling",
                "attempts": attempts,
                "accepted": accepted,
                "rejected_intersection_or_overlap": rejected_intersection,
                "rejected_too_long": rejected_length,
            }
        )
    for i, sample in enumerate(samples):
        rows.append(run_row(sample, field_stats, i, 111_000 + i, "nonintersecting_initial", 45, 190))

    model = ExtraTreesRegressor(n_estimators=420, random_state=101, min_samples_leaf=2, n_jobs=-1)
    model.fit(np.array([feature(samples[int(r["sample_id"])]) for r in rows]), np.array([r["v11_score"] for r in rows]))
    importances = [
        {"feature": k, "importance": float(v)}
        for k, v in sorted(zip(FEATURES, model.feature_importances_), key=lambda kv: kv[1], reverse=True)
    ]
    write_csv(importances, OUT_DIR / "v11_ml_feature_importance.csv")

    virtual: list[dict] = []
    for family in FAMILIES:
        accepted = 0
        rejected_length = 0
        for _ in range(450):
            sample = sample_candidate(family, base, rng)
            if path_length(sample) * 1e3 > 24.0:
                rejected_length += 1
                continue
            virtual.append(sample)
            accepted += 1
        rejection_rows.append(
            {
                "family": family.name,
                "stage": "virtual_ml_pool",
                "attempts": 450,
                "accepted": accepted,
                "rejected_intersection_or_overlap": "deferred_to_finalist_filter",
                "rejected_too_long": rejected_length,
            }
        )
    pred = model.predict(np.array([feature(s) for s in virtual]))
    for sample, score in zip(virtual, pred):
        sample["predicted_v11_score"] = float(score)

    selected: list[dict] = []
    for sample in sorted(virtual, key=lambda s: s["predicted_v11_score"], reverse=True):
        if len(selected) >= 30:
            break
        if sum(1 for s in selected if s["family"] == sample["family"]) >= 7:
            continue
        if path_length(sample) * 1e3 > 24.0:
            continue
        if not geometry_screen(sample, n=180)["geometry_valid"]:
            continue
        selected.append(sample)

    offset = len(samples)
    for j, sample in enumerate(selected):
        sample_id = offset + j
        samples.append(sample)
        rows.append(run_row(sample, field_stats, sample_id, 112_000 + j, "ml_selected_nonintersecting", 80, 270))

    screen_summary = aggregate(rows)

    validation_rows: list[dict] = []
    control_rows: list[dict] = []
    for item in screen_summary[:10]:
        sample = samples[int(item["sample_id"])]
        for seed in [113_001, 113_019, 113_041, 113_073]:
            validation_rows.append(run_row(sample, field_stats, int(item["sample_id"]), seed, "heldout_nonintersecting", 140, 330))
        for control_name, kwargs in [
            ("same_length_straight_dep", {"geometry_override": "straight", "dep_enabled": True}),
            ("no_dep", {"dep_enabled": False}),
            ("unfocused_inlet", {"inlet_override": (0.0, 1.0)}),
        ]:
            scores, losses = [], []
            for seed in [114_003, 114_021, 114_039]:
                particles, summary, _ = simulate(sample, field_stats, seed, 110, 270, **kwargs)
                perf = performance_metrics(particles, summary)
                scores.append(perf["target_correct"])
                losses.append(perf["wall_loss"])
            control_rows.append(
                {
                    "sample_id": int(item["sample_id"]),
                    "family": sample["family"],
                    "control": control_name,
                    "mean_target_correct": float(np.mean(scores)),
                    "mean_wall_loss": float(np.mean(losses)),
                }
            )

    validation = aggregate(validation_rows)
    controls = {(r["sample_id"], r["control"]): r for r in control_rows}
    for row in validation:
        straight = controls[(row["sample_id"], "same_length_straight_dep")]
        no_dep = controls[(row["sample_id"], "no_dep")]
        unfocused = controls[(row["sample_id"], "unfocused_inlet")]
        row["straight_control_correct"] = straight["mean_target_correct"]
        row["no_dep_correct"] = no_dep["mean_target_correct"]
        row["unfocused_inlet_correct"] = unfocused["mean_target_correct"]
        row["topology_gain_vs_straight"] = row["mean_target_correct"] - straight["mean_target_correct"]
        row["passes_v11_gate"] = (
            row["mean_target_correct"] >= 0.80
            and row["length_mm"] <= 20.0
            and row["topology_gain_vs_straight"] >= 0.06
            and row["mean_wall_loss"] < 0.10
            and row["manufacturable_gap_ok"]
            and row["manufacturable_bend_ok"]
            and row["manufacturable_no_intersection_ok"]
            and row["thermal_risk"] != "high"
        )
    validation.sort(
        key=lambda r: (
            r["passes_v11_gate"],
            r["mean_target_correct"],
            r["topology_gain_vs_straight"],
            r["short_channel_score"],
        ),
        reverse=True,
    )

    write_csv(rows, OUT_DIR / "v11_screening_rows.csv")
    write_csv(screen_summary, OUT_DIR / "v11_screening_summary.csv")
    write_csv(validation_rows, OUT_DIR / "v11_validation_replicates.csv")
    write_csv(control_rows, OUT_DIR / "v11_control_rows.csv")
    write_csv(validation, OUT_DIR / "v11_validation_summary.csv")
    write_csv(rejection_rows, OUT_DIR / "v11_geometry_rejections.csv")

    for rank, row in enumerate(validation[:6], start=1):
        write_shape_data(samples[int(row["sample_id"])], OUT_DIR, f"rank{rank}_{row['family']}")

    plot_gallery(validation, samples)
    plot_metrics(rows, validation, control_rows)

    best = validation[0]
    best_sample = samples[int(best["sample_id"])]
    readme = [
        "# Design V11 Shape ML Non-Intersection Screening",
        "",
        "V11 screens more short, symmetric or deliberately clean formula-defined microfluidic shapes.",
        "No random free-form curves are used, and self-intersecting or overlapping centerlines are rejected before simulation.",
        "",
        "## Shape Families",
    ]
    for family in FAMILIES:
        readme.append(f"- `{family.name}`: `{family.equation}`. {family.note}")
    readme.extend(
        [
            "",
            "## Best Candidate",
            "",
            f"- family: `{best['family']}`",
            f"- equation: `{best['equation']}`",
            f"- inlet kind: `{best['inlet_kind']}`",
            f"- target correct: `{best['mean_target_correct']:.3f} +/- {best['std_target_correct']:.3f}`",
            f"- topology gain vs same-length straight DEP: `{best['topology_gain_vs_straight']:.3f}`",
            f"- length: `{best['length_mm']:.1f} mm`",
            f"- residence time: `{best['residence_s']:.2f} s`",
            f"- wall loss: `{best['mean_wall_loss']:.3f}`",
            f"- active Joule power proxy: `{best['active_joule_power_mW']:.2f} mW`",
            f"- steady substrate temp-rise proxy: `{best['steady_substrate_delta_c_proxy']:.2f} C`",
            f"- manufacturable gap ok: `{best['manufacturable_gap_ok']}`",
            f"- manufacturable bend ok: `{best['manufacturable_bend_ok']}`",
            f"- no self-intersection/overlap ok: `{best['manufacturable_no_intersection_ok']}`",
            f"- minimum nonlocal clearance: `{best['min_nonlocal_clearance_um']:.1f} um`",
            f"- passes V11 gate: `{best['passes_v11_gate']}`",
            "",
            "## Academic Improvements Over V10",
            "",
            "- Additional families include logarithmic spirals, elliptic logarithmic spirals, Fermat spirals, S-bend prefocus spirals, and short C-arcs.",
            "- Non-intersection and channel-overlap checks are hard geometric constraints before simulation.",
            "- Shape parameters remain named physical variables: eccentricity, curvature power, inlet length, electrode gap, and electrode coverage.",
            "- Short-channel screening remains explicit; the pass gate requires length <= 20 mm.",
            "- The same-length straight DEP, no-DEP, and unfocused-inlet controls are reported for each finalist.",
            "- Manufacturability proxies include minimum bend radius, minimum electrode gap, and nonlocal channel clearance.",
            "- Thermal and pressure proxies are recorded for ranking, not hidden.",
            "",
            "## How ML Optimizes Shape Here",
            "",
            "The ML model does not draw arbitrary curves. It learns a surrogate from reduced-order simulations and ranks formula-parameter candidates. The optimized variables are family id, frequency, voltage, flow velocity, turns, radius, pitch, width, eccentricity, curvature power, inlet length, inlet focusing, DEP start/end, electrode gap, electrode coverage, field gain, and Dean scale. Finalists are re-simulated with held-out seeds and controls.",
            "",
            "## Stored Shape Data",
            "",
            "Top candidates are saved as `rank*_formula.json` and `rank*_centerline.csv` files.",
            "",
            "## Honest Limitation",
            "",
            "DEP is still represented by a reduced-order electrode-gap field-gain proxy. "
            "The selected V11 geometry should be rebuilt with an electrode-resolved field solve before a final device claim.",
            "",
            "## Best Formula Parameters",
            "",
            "```json",
            json.dumps(best_sample, indent=2),
            "```",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(readme), encoding="utf-8")

    print(json.dumps({"best": best, "out_dir": str(OUT_DIR)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
