#!/usr/bin/env python3
"""Design V2 population-level live/dead trajectory simulation.

V2 samples cell diameter and dielectric-property distributions instead of using
one representative live and one representative dead cell. It also separates
design seeds from validation seeds and reports recovery, purity, dead removal,
wall loss, and correct outlet classification.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from design_v0_particle_tracking import (
    EPS0,
    MEDIUM_EPS_R,
    MEDIUM_VISCOSITY_PA_S,
    SpiralSpec,
    centerline,
    ds_dtheta,
    point_xy,
)
from design_v1_doe import write_pvd, write_vtp_frame, write_vtp_polyline


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "openfoam_design_v2"
DOE_DIR = OUT_DIR / "population_doe"
PARAVIEW_DIR = OUT_DIR / "paraview"

FREQUENCY_HZ = 455_326.0
MEDIUM_SIGMA_S_M = 0.002

DESIGN_SEEDS = [7, 11, 13]
VALIDATION_SEEDS = [101, 103, 107]

TURNS = [4.0, 5.0, 6.0]
VOLTAGES = [8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0]
VELOCITIES = [800e-6, 1000e-6, 1500e-6, 2000e-6, 3000e-6]


@dataclass(frozen=True)
class SampledCell:
    name: str
    radius_m: float
    re_cm: float
    initial_lateral_m: float


@dataclass(frozen=True)
class CellDistribution:
    name: str
    diameter_mean_m: float
    diameter_cv: float
    membrane_thickness_mean_m: float
    membrane_thickness_cv: float
    membrane_eps_r: float
    membrane_sigma_mean_s_m: float
    cytoplasm_eps_r: float
    cytoplasm_sigma_mean_s_m: float


LIVE_DIST = CellDistribution(
    name="live",
    diameter_mean_m=23e-6,
    diameter_cv=0.10,
    membrane_thickness_mean_m=7e-9,
    membrane_thickness_cv=0.08,
    membrane_eps_r=12.5,
    membrane_sigma_mean_s_m=1e-6,
    cytoplasm_eps_r=50.0,
    cytoplasm_sigma_mean_s_m=0.5,
)

DEAD_DIST = CellDistribution(
    name="dead",
    diameter_mean_m=22e-6,
    diameter_cv=0.10,
    membrane_thickness_mean_m=7e-9,
    membrane_thickness_cv=0.08,
    membrane_eps_r=12.5,
    membrane_sigma_mean_s_m=0.01,
    cytoplasm_eps_r=80.0,
    cytoplasm_sigma_mean_s_m=0.002,
)


def case_id(turns: float, voltage: float, velocity: float) -> str:
    return f"turns_{turns:g}_voltage_{voltage:g}_velocity_{velocity * 1e6:.0f}um_s"


def complex_permittivity(eps_r: float, sigma: float, omega: float) -> complex:
    return EPS0 * eps_r - 1j * sigma / omega


def sampled_re_cm(
    radius_m: float,
    membrane_thickness_m: float,
    membrane_eps_r: float,
    membrane_sigma_s_m: float,
    cytoplasm_eps_r: float,
    cytoplasm_sigma_s_m: float,
) -> float:
    omega = 2.0 * math.pi * FREQUENCY_HZ
    eps_medium = complex_permittivity(MEDIUM_EPS_R, MEDIUM_SIGMA_S_M, omega)
    eps_mem = complex_permittivity(membrane_eps_r, membrane_sigma_s_m, omega)
    eps_cyto = complex_permittivity(cytoplasm_eps_r, cytoplasm_sigma_s_m, omega)
    membrane_capacitance = eps_mem / membrane_thickness_m
    eps_cell = (
        membrane_capacitance
        * radius_m
        * eps_cyto
        / (membrane_capacitance * radius_m + eps_cyto)
    )
    return float(np.real((eps_cell - eps_medium) / (eps_cell + 2.0 * eps_medium)))


def lognormal_positive(rng: np.random.Generator, mean: float, sigma_ln: float) -> float:
    return float(rng.lognormal(mean=math.log(mean), sigma=sigma_ln))


def truncated_normal_positive(
    rng: np.random.Generator,
    mean: float,
    std: float,
    lower: float,
    upper: float,
) -> float:
    for _ in range(100):
        value = float(rng.normal(mean, std))
        if lower <= value <= upper:
            return value
    return float(np.clip(mean, lower, upper))


def sample_cell(
    rng: np.random.Generator,
    distribution: CellDistribution,
    channel_width_m: float,
) -> SampledCell:
    diameter = truncated_normal_positive(
        rng,
        distribution.diameter_mean_m,
        distribution.diameter_cv * distribution.diameter_mean_m,
        0.65 * distribution.diameter_mean_m,
        1.35 * distribution.diameter_mean_m,
    )
    membrane_thickness = truncated_normal_positive(
        rng,
        distribution.membrane_thickness_mean_m,
        distribution.membrane_thickness_cv * distribution.membrane_thickness_mean_m,
        0.65 * distribution.membrane_thickness_mean_m,
        1.35 * distribution.membrane_thickness_mean_m,
    )
    membrane_sigma = lognormal_positive(rng, distribution.membrane_sigma_mean_s_m, 0.45)
    cytoplasm_sigma = lognormal_positive(rng, distribution.cytoplasm_sigma_mean_s_m, 0.35)
    radius = 0.5 * diameter
    re_cm = sampled_re_cm(
        radius,
        membrane_thickness,
        distribution.membrane_eps_r,
        membrane_sigma,
        distribution.cytoplasm_eps_r,
        cytoplasm_sigma,
    )
    clearance = radius + 2e-6
    lateral = float(rng.uniform(-0.5 * channel_width_m + clearance, 0.5 * channel_width_m - clearance))
    return SampledCell(distribution.name, radius, re_cm, lateral)


def dep_lateral_velocity(spec: SpiralSpec, cell: SampledCell, lateral_m: float) -> float:
    width = spec.channel_width_m
    eps_m = EPS0 * MEDIUM_EPS_R
    electric_field = spec.voltage_v / width
    decay_length = 0.35 * width
    distance_from_inner = lateral_m + 0.5 * width
    e2 = electric_field * electric_field * math.exp(-distance_from_inner / decay_length)
    grad_e2 = -e2 / decay_length
    gradient_attenuation = 7.5e-4
    return (
        eps_m
        * cell.radius_m
        * cell.radius_m
        * cell.re_cm
        * gradient_attenuation
        * grad_e2
        / (3.0 * MEDIUM_VISCOSITY_PA_S)
    )


def run_particle(
    spec: SpiralSpec,
    cell: SampledCell,
    particle_id: int,
    steps: int,
    keep_path: bool,
) -> tuple[dict, list[dict]]:
    theta_end = 2.0 * math.pi * spec.turns
    dtheta = theta_end / steps
    theta = 0.0
    lateral = cell.initial_lateral_m
    wall_state = ""
    path: list[dict] = []

    for step in range(steps + 1):
        progress = step / steps
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

        local_dt_s = ds_dtheta(spec, theta) * dtheta / spec.inlet_velocity_m_s
        dep_v = dep_lateral_velocity(spec, cell, lateral)
        dean_v = 0.18e-6 * (spec.inlet_velocity_m_s / 1000e-6) ** 1.2
        lateral += (dep_v + dean_v) * local_dt_s

        clearance = cell.radius_m + 1e-6
        inner_limit = -0.5 * spec.channel_width_m + clearance
        outer_limit = 0.5 * spec.channel_width_m - clearance
        if lateral <= inner_limit:
            lateral = inner_limit
            wall_state = "inner_wall_loss"
        elif lateral >= outer_limit:
            lateral = outer_limit
            wall_state = "outer_wall_loss"
        theta += dtheta

    outlet = "lost" if wall_state else ("inner" if lateral < 0 else "outer")
    result = {
        "class": cell.name,
        "particle_id": particle_id,
        "radius_um": cell.radius_m * 1e6,
        "re_cm": cell.re_cm,
        "initial_lateral_um": cell.initial_lateral_m * 1e6,
        "final_lateral_um": lateral * 1e6,
        "outlet": outlet,
        "wall_state": wall_state,
    }
    if keep_path and wall_state and path[-1]["progress"] < 1.0:
        # Hold lost particles at the wall for the remaining visual frames.
        last = path[-1]
        for step in range(len(path), steps + 1):
            row = dict(last)
            row["progress"] = step / steps
            path.append(row)
    return result, path


def summarize(results: list[dict], spec: SpiralSpec, seed: int, split: str) -> dict:
    live = [row for row in results if row["class"] == "live"]
    dead = [row for row in results if row["class"] == "dead"]
    live_inner = sum(row["outlet"] == "inner" for row in live)
    live_outer = sum(row["outlet"] == "outer" for row in live)
    dead_inner = sum(row["outlet"] == "inner" for row in dead)
    dead_outer = sum(row["outlet"] == "outer" for row in dead)
    live_lost = sum(row["outlet"] == "lost" for row in live)
    dead_lost = sum(row["outlet"] == "lost" for row in dead)
    total = len(results)

    live_recovery = live_inner / len(live)
    dead_removal = dead_outer / len(dead)
    live_purity = live_inner / max(1, live_inner + dead_inner)
    dead_outlet_purity = dead_outer / max(1, dead_outer + live_outer)
    correct_fraction = (live_inner + dead_outer) / total
    wall_loss = (live_lost + dead_lost) / total

    return {
        "case_id": case_id(spec.turns, spec.voltage_v, spec.inlet_velocity_m_s),
        "split": split,
        "seed": seed,
        "turns": spec.turns,
        "voltage_v": spec.voltage_v,
        "velocity_um_s": spec.inlet_velocity_m_s * 1e6,
        "particles_total": total,
        "correct_fraction": correct_fraction,
        "live_recovery": live_recovery,
        "dead_removal": dead_removal,
        "live_purity": live_purity,
        "dead_outlet_purity": dead_outlet_purity,
        "wall_loss": wall_loss,
        "live_inner": live_inner,
        "live_outer": live_outer,
        "live_lost": live_lost,
        "dead_inner": dead_inner,
        "dead_outer": dead_outer,
        "dead_lost": dead_lost,
        "mean_live_re_cm": float(np.mean([row["re_cm"] for row in live])),
        "mean_dead_re_cm": float(np.mean([row["re_cm"] for row in dead])),
        "mean_live_radius_um": float(np.mean([row["radius_um"] for row in live])),
        "mean_dead_radius_um": float(np.mean([row["radius_um"] for row in dead])),
    }


def simulate_population(
    spec: SpiralSpec,
    seed: int,
    split: str,
    particles_per_class: int,
    steps: int,
    keep_paths: bool = False,
) -> tuple[list[dict], dict, list[dict]]:
    rng = np.random.default_rng(seed)
    particle_results = []
    paths = []
    particle_id = 0
    for distribution in [LIVE_DIST, DEAD_DIST]:
        for _ in range(particles_per_class):
            cell = sample_cell(rng, distribution, spec.channel_width_m)
            result, path = run_particle(spec, cell, particle_id, steps, keep_paths)
            particle_results.append(result)
            paths.extend(path)
            particle_id += 1
    return particle_results, summarize(particle_results, spec, seed, split), paths


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows: list[dict], split: str) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["split"] == split:
            grouped[row["case_id"]].append(row)

    output = []
    for cid, items in grouped.items():
        first = items[0]
        output.append(
            {
                "case_id": cid,
                "split": split,
                "turns": first["turns"],
                "voltage_v": first["voltage_v"],
                "velocity_um_s": first["velocity_um_s"],
                "mean_correct": float(np.mean([x["correct_fraction"] for x in items])),
                "min_correct": float(np.min([x["correct_fraction"] for x in items])),
                "std_correct": float(np.std([x["correct_fraction"] for x in items], ddof=1)),
                "mean_live_recovery": float(np.mean([x["live_recovery"] for x in items])),
                "mean_dead_removal": float(np.mean([x["dead_removal"] for x in items])),
                "mean_live_purity": float(np.mean([x["live_purity"] for x in items])),
                "mean_dead_outlet_purity": float(np.mean([x["dead_outlet_purity"] for x in items])),
                "mean_wall_loss": float(np.mean([x["wall_loss"] for x in items])),
            }
        )
    output.sort(
        key=lambda row: (
            row["mean_correct"],
            row["mean_live_recovery"],
            row["mean_dead_removal"],
            -row["mean_wall_loss"],
        ),
        reverse=True,
    )
    return output


def run_doe() -> tuple[list[dict], list[dict], list[dict], dict]:
    replicate_rows = []
    for turns in TURNS:
        for voltage in VOLTAGES:
            for velocity in VELOCITIES:
                spec = SpiralSpec(turns=turns, voltage_v=voltage, inlet_velocity_m_s=velocity)
                for split, seeds in [("design", DESIGN_SEEDS), ("validation", VALIDATION_SEEDS)]:
                    for seed in seeds:
                        _, summary, _ = simulate_population(
                            spec,
                            seed,
                            split,
                            particles_per_class=150,
                            steps=420,
                        )
                        replicate_rows.append(summary)

    design_rows = aggregate(replicate_rows, "design")
    validation_rows = aggregate(replicate_rows, "validation")
    validation_by_case = {row["case_id"]: row for row in validation_rows}

    # Choose the best design condition, then inspect its validation performance.
    selected_design = design_rows[0]
    selected_validation = validation_by_case[selected_design["case_id"]]
    best_validation = validation_rows[0]
    selection = {
        "selected_by_design": selected_design,
        "selected_validation": selected_validation,
        "best_by_validation": best_validation,
    }
    return replicate_rows, design_rows, validation_rows, selection


def plot_outputs(design_rows: list[dict], validation_rows: list[dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    top = validation_rows[:25]
    labels = [row["case_id"].replace("_", "\n") for row in top]
    values = [row["mean_correct"] for row in top]
    errors = [row["std_correct"] for row in top]
    colors = ["#238b45" if row["mean_wall_loss"] < 0.05 else "#fd8d3c" for row in top]
    plt.figure(figsize=(14, 6))
    plt.bar(range(len(top)), values, yerr=errors, color=colors, capsize=2)
    plt.axhline(0.9, color="black", linestyle="--", linewidth=1, label="publication target")
    plt.axhline(0.85, color="0.35", linestyle=":", linewidth=1, label="V2 screening target")
    plt.xticks(range(len(top)), labels, rotation=90, fontsize=6)
    plt.ylabel("Validation mean correct classification")
    plt.ylim(0.35, 1.02)
    plt.title("Design V2 validation ranking with population uncertainty")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "v2_validation_ranking.png", dpi=180)
    plt.close()

    for metric, filename, title in [
        ("mean_live_recovery", "v2_live_recovery_heatmaps.png", "Live recovery"),
        ("mean_dead_removal", "v2_dead_removal_heatmaps.png", "Dead-cell removal"),
        ("mean_wall_loss", "v2_wall_loss_heatmaps.png", "Wall loss"),
    ]:
        fig, axes = plt.subplots(1, len(VELOCITIES), figsize=(17, 4.5), sharey=True)
        for ax, velocity in zip(axes, sorted([v * 1e6 for v in VELOCITIES])):
            grid = np.full((len(TURNS), len(VOLTAGES)), np.nan)
            for row in validation_rows:
                if abs(row["velocity_um_s"] - velocity) < 1e-6:
                    grid[TURNS.index(row["turns"]), VOLTAGES.index(row["voltage_v"])] = row[metric]
            im = ax.imshow(grid, vmin=0.0, vmax=1.0, cmap="viridis", origin="lower")
            ax.set_title(f"{velocity:.0f} um/s")
            ax.set_xticks(range(len(VOLTAGES)), [f"{v:g}" for v in VOLTAGES])
            ax.set_yticks(range(len(TURNS)), [f"{t:g}" for t in TURNS])
            ax.set_xlabel("Voltage")
            if ax is axes[0]:
                ax.set_ylabel("Turns")
            for i in range(len(TURNS)):
                for j in range(len(VOLTAGES)):
                    ax.text(j, i, f"{grid[i, j]:.2f}", ha="center", va="center", color="white", fontsize=7)
        fig.colorbar(im, ax=axes.ravel().tolist(), label=metric)
        fig.suptitle(f"Design V2 validation: {title}")
        fig.savefig(out_dir / filename, dpi=180, bbox_inches="tight")
        plt.close(fig)


def write_readme(selection: dict, validation_rows: list[dict], out_dir: Path) -> None:
    selected = selection["selected_by_design"]
    selected_val = selection["selected_validation"]
    best_val = selection["best_by_validation"]
    lines = [
        "# Design V2 Population DOE",
        "",
        "V2 samples cell diameter, dielectric properties, and inlet positions.",
        "It separates design seeds from validation seeds and reports recovery,",
        "purity, dead-cell removal, and wall loss.",
        "",
        "## DOE Grid",
        "",
        f"- turns: `{', '.join(str(int(v)) for v in TURNS)}`",
        f"- voltage: `{', '.join(str(int(v)) for v in VOLTAGES)} V`",
        f"- velocity: `{', '.join(str(int(v * 1e6)) for v in VELOCITIES)} um/s`",
        f"- design seeds: `{DESIGN_SEEDS}`",
        f"- validation seeds: `{VALIDATION_SEEDS}`",
        "- particles per class per replicate: `150`",
        "",
        "## Selected By Design Seeds",
        "",
        f"- case: `{selected['case_id']}`",
        f"- design mean correct: `{selected['mean_correct']:.3f}`",
        f"- validation mean correct: `{selected_val['mean_correct']:.3f}`",
        f"- validation live recovery: `{selected_val['mean_live_recovery']:.3f}`",
        f"- validation dead removal: `{selected_val['mean_dead_removal']:.3f}`",
        f"- validation live purity: `{selected_val['mean_live_purity']:.3f}`",
        f"- validation wall loss: `{selected_val['mean_wall_loss']:.3f}`",
        "",
        "## Best By Validation",
        "",
        f"- case: `{best_val['case_id']}`",
        f"- validation mean correct: `{best_val['mean_correct']:.3f}`",
        f"- validation live recovery: `{best_val['mean_live_recovery']:.3f}`",
        f"- validation dead removal: `{best_val['mean_dead_removal']:.3f}`",
        f"- validation live purity: `{best_val['mean_live_purity']:.3f}`",
        f"- validation dead outlet purity: `{best_val['mean_dead_outlet_purity']:.3f}`",
        f"- validation wall loss: `{best_val['mean_wall_loss']:.3f}`",
        "",
        "## Top Validation Conditions",
        "",
        "| Rank | Case | Correct | Live recovery | Dead removal | Live purity | Wall loss |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for i, row in enumerate(validation_rows[:12], 1):
        lines.append(
            f"| {i} | `{row['case_id']}` | {row['mean_correct']:.3f} | "
            f"{row['mean_live_recovery']:.3f} | {row['mean_dead_removal']:.3f} | "
            f"{row['mean_live_purity']:.3f} | {row['mean_wall_loss']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "V2 is intentionally harder than V1. High voltage and long residence",
            "time can now create wall loss, and cell-property distributions can",
            "weaken apparently clean deterministic separation.",
            "",
            "The next step is replacing the analytical field-gradient proxy with",
            "OpenFOAM-interpolated `grad(E^2)` for the best validation condition.",
        ]
    )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_paraview_outputs(selection: dict) -> None:
    best = selection["best_by_validation"]
    spec = SpiralSpec(
        turns=best["turns"],
        voltage_v=best["voltage_v"],
        inlet_velocity_m_s=best["velocity_um_s"] * 1e-6,
    )
    particles, summary, records = simulate_population(
        spec,
        seed=VALIDATION_SEEDS[0],
        split="validation_best_visual",
        particles_per_class=120,
        steps=420,
        keep_paths=True,
    )
    PARAVIEW_DIR.mkdir(parents=True, exist_ok=True)
    (DOE_DIR / "best_validation_visual_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(particles, DOE_DIR / "best_validation_visual_particles.csv")
    write_vtp_polyline(records, PARAVIEW_DIR / "best_validation_trajectories.vtp")
    frame_dir = PARAVIEW_DIR / "animation_frames"
    frame_paths = []
    for i, progress in enumerate(np.linspace(0, 1, 90)):
        frame = frame_dir / f"frame_{i:04d}.vtp"
        write_vtp_frame(records, spec, float(progress), frame)
        frame_paths.append(frame)
    write_pvd(frame_paths, PARAVIEW_DIR / "best_validation_particles.pvd")


def main() -> int:
    DOE_DIR.mkdir(parents=True, exist_ok=True)
    replicate_rows, design_rows, validation_rows, selection = run_doe()
    write_csv(replicate_rows, DOE_DIR / "v2_replicates.csv")
    write_csv(design_rows, DOE_DIR / "v2_design_summary.csv")
    write_csv(validation_rows, DOE_DIR / "v2_validation_summary.csv")
    (DOE_DIR / "v2_selection.json").write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    plot_outputs(design_rows, validation_rows, DOE_DIR)
    write_readme(selection, validation_rows, DOE_DIR)
    write_paraview_outputs(selection)
    print((DOE_DIR / "README.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
