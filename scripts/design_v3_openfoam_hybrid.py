#!/usr/bin/env python3
"""Design V3 OpenFOAM-backed hybrid population model.

V3 keeps OpenFOAM as the device-field source and uses a cheap stochastic
finite-size particle model for live/dead populations. It is not a deformable
cell solver; it is the practical optimization layer before expensive validation.
"""

from __future__ import annotations

import csv
import json
import math
import re
import subprocess
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
    ds_dtheta,
    point_xy,
)
from design_v1_doe import write_pvd, write_vtp_frame, write_vtp_polyline
from design_v2_population_sim import DEAD_DIST, LIVE_DIST, sampled_re_cm, truncated_normal_positive, lognormal_positive


ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "cases" / "design_v0"
OUT_DIR = ROOT / "results" / "openfoam_design_v3"
DOE_DIR = OUT_DIR / "hybrid_doe"
PARAVIEW_DIR = OUT_DIR / "paraview"

FREQUENCY_HZ = 455_326.0
MEDIUM_SIGMA_S_M = 0.002
KB = 1.380649e-23
TEMPERATURE_K = 300.0

DESIGN_SEEDS = [7, 11, 13]
VALIDATION_SEEDS = [101, 103, 107]
TURNS = [3.5, 4.5, 5.5]
VOLTAGES = [7.0, 9.0, 11.0, 13.0]
VELOCITIES = [800e-6, 1200e-6, 1800e-6, 2600e-6]


@dataclass(frozen=True)
class HybridCell:
    name: str
    radius_m: float
    re_cm: float
    initial_lateral_m: float
    initial_z_m: float
    adhesion_index: float


@dataclass(frozen=True)
class OpenFOAMFieldStats:
    grad_mag_mean: float
    grad_mag_p95: float
    grad_mag_max: float
    cell_count: int


def case_id(turns: float, voltage: float, velocity: float) -> str:
    return f"turns_{turns:g}_voltage_{voltage:g}_velocity_{velocity * 1e6:.0f}um_s"


def run_openfoam_case() -> None:
    foam_bashrc = Path("/usr/lib/openfoam/openfoam2312/etc/bashrc")
    if foam_bashrc.exists():
        command = f"source {foam_bashrc} && bash Allrun"
    else:
        command = "bash Allrun"
    result = subprocess.run(
        ["bash", "-lc", command],
        cwd=CASE_DIR,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    DOE_DIR.mkdir(parents=True, exist_ok=True)
    (DOE_DIR / "openfoam_allrun.log").write_text(result.stdout, encoding="utf-8")
    required = [CASE_DIR / "1" / "gradTx", CASE_DIR / "1" / "gradTy"]
    if result.returncode != 0 and not all(path.exists() for path in required):
        raise RuntimeError("OpenFOAM Allrun failed and required prior field files are missing.")


def parse_internal_scalar_field(path: Path) -> np.ndarray:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;", text, re.S)
    if not match:
        raise ValueError(f"Could not parse nonuniform scalar field: {path}")
    expected = int(match.group(1))
    values = np.fromstring(match.group(2), sep="\n")
    if values.size != expected:
        raise ValueError(f"Expected {expected} values in {path}, parsed {values.size}")
    return values


def load_openfoam_field_stats() -> OpenFOAMFieldStats:
    grad_x = parse_internal_scalar_field(CASE_DIR / "1" / "gradTx")
    grad_y = parse_internal_scalar_field(CASE_DIR / "1" / "gradTy")
    grad_mag = np.sqrt(grad_x * grad_x + grad_y * grad_y)
    return OpenFOAMFieldStats(
        grad_mag_mean=float(np.mean(grad_mag)),
        grad_mag_p95=float(np.percentile(grad_mag, 95)),
        grad_mag_max=float(np.max(grad_mag)),
        cell_count=int(grad_mag.size),
    )


def sample_cell(rng: np.random.Generator, name: str, width: float, height: float) -> HybridCell:
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
    re_cm = sampled_re_cm(
        radius,
        membrane_thickness,
        dist.membrane_eps_r,
        lognormal_positive(rng, dist.membrane_sigma_mean_s_m, 0.45),
        dist.cytoplasm_eps_r,
        lognormal_positive(rng, dist.cytoplasm_sigma_mean_s_m, 0.35),
    )
    clearance = radius + 2.0e-6
    lateral = float(rng.uniform(-0.5 * width + clearance, 0.5 * width - clearance))
    z = float(rng.uniform(clearance, height - clearance))
    adhesion_index = float(rng.lognormal(mean=0.0 if name == "live" else 0.35, sigma=0.45))
    return HybridCell(name, radius, re_cm, lateral, z, adhesion_index)


def field_shape(spec: SpiralSpec, lateral_m: float, z_m: float, field_stats: OpenFOAMFieldStats) -> tuple[float, float]:
    width = spec.channel_width_m
    height = 50e-6
    distance_from_inner = lateral_m + 0.5 * width
    wall_decay = math.exp(-distance_from_inner / (0.28 * width))
    z_shape = 0.55 + 0.45 * math.sin(math.pi * z_m / height) ** 2
    openfoam_scale = field_stats.grad_mag_p95 / max(1.0, field_stats.grad_mag_mean)
    e_field = spec.voltage_v / width
    e2 = (e_field * e_field) * wall_decay * z_shape * openfoam_scale
    grad_e2 = -e2 / (0.28 * width)
    return e2, grad_e2


def lateral_velocity(spec: SpiralSpec, cell: HybridCell, lateral_m: float, z_m: float, field_stats: OpenFOAMFieldStats) -> float:
    eps_m = EPS0 * MEDIUM_EPS_R
    _, grad_e2 = field_shape(spec, lateral_m, z_m, field_stats)
    dep_v = eps_m * cell.radius_m * cell.radius_m * cell.re_cm * grad_e2 / (3.0 * MEDIUM_VISCOSITY_PA_S)
    dep_v *= 5.0e-4
    dean_v = 0.12e-6 * (spec.inlet_velocity_m_s / 1000e-6) ** 1.35
    shear_lift_v = 0.05e-6 * math.tanh(lateral_m / (0.22 * spec.channel_width_m))
    return dep_v + dean_v + shear_lift_v


def local_axial_velocity(spec: SpiralSpec, lateral_m: float, z_m: float) -> float:
    width = spec.channel_width_m
    height = 50e-6
    y = 2.0 * lateral_m / width
    z = 2.0 * (z_m / height - 0.5)
    profile = max(0.15, (1.0 - 0.65 * y * y) * (1.0 - 0.55 * z * z))
    return spec.inlet_velocity_m_s * profile


def run_particle(
    spec: SpiralSpec,
    cell: HybridCell,
    field_stats: OpenFOAMFieldStats,
    rng: np.random.Generator,
    particle_id: int,
    steps: int,
    keep_path: bool,
) -> tuple[dict, list[dict]]:
    theta_end = 2.0 * math.pi * spec.turns
    dtheta = theta_end / steps
    theta = 0.0
    lateral = cell.initial_lateral_m
    z = cell.initial_z_m
    wall_state = ""
    path: list[dict] = []

    diffusion = KB * TEMPERATURE_K / (6.0 * math.pi * MEDIUM_VISCOSITY_PA_S * cell.radius_m)

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

        axial_u = local_axial_velocity(spec, lateral, z)
        local_dt_s = ds_dtheta(spec, theta) * dtheta / max(1e-9, axial_u)
        brownian_step = math.sqrt(2.0 * diffusion * local_dt_s) * rng.normal()
        lateral += lateral_velocity(spec, cell, lateral, z, field_stats) * local_dt_s + brownian_step
        z += math.sqrt(2.0 * diffusion * local_dt_s) * rng.normal()

        clearance = cell.radius_m + 1.0e-6
        inner_limit = -0.5 * spec.channel_width_m + clearance
        outer_limit = 0.5 * spec.channel_width_m - clearance
        z = float(np.clip(z, clearance, 50e-6 - clearance))

        if lateral <= inner_limit or lateral >= outer_limit:
            lateral = inner_limit if lateral <= inner_limit else outer_limit
            _, e2 = field_shape(spec, lateral, z, field_stats)
            voltage_risk = (spec.voltage_v / 13.0) ** 2
            adhesion_probability = min(0.95, 0.08 * cell.adhesion_index * voltage_risk * (1.0 + abs(e2) / 1.0e13))
            if rng.random() < adhesion_probability:
                wall_state = "inner_wall_loss" if lateral <= inner_limit else "outer_wall_loss"

        theta += dtheta

    outlet = "lost" if wall_state else ("inner" if lateral < -0.08 * spec.channel_width_m else "outer")
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
        last = path[-1]
        for hold_step in range(len(path), steps + 1):
            row = dict(last)
            row["progress"] = hold_step / steps
            path.append(row)
    return result, path


def summarize(results: list[dict], spec: SpiralSpec, seed: int, split: str) -> dict:
    live = [r for r in results if r["class"] == "live"]
    dead = [r for r in results if r["class"] == "dead"]
    live_inner = sum(r["outlet"] == "inner" for r in live)
    live_outer = sum(r["outlet"] == "outer" for r in live)
    dead_inner = sum(r["outlet"] == "inner" for r in dead)
    dead_outer = sum(r["outlet"] == "outer" for r in dead)
    live_lost = sum(r["outlet"] == "lost" for r in live)
    dead_lost = sum(r["outlet"] == "lost" for r in dead)
    total = len(results)
    return {
        "case_id": case_id(spec.turns, spec.voltage_v, spec.inlet_velocity_m_s),
        "split": split,
        "seed": seed,
        "turns": spec.turns,
        "voltage_v": spec.voltage_v,
        "velocity_um_s": spec.inlet_velocity_m_s * 1e6,
        "correct_fraction": (live_inner + dead_outer) / total,
        "live_recovery": live_inner / len(live),
        "dead_removal": dead_outer / len(dead),
        "live_purity": live_inner / max(1, live_inner + dead_inner),
        "dead_outlet_purity": dead_outer / max(1, dead_outer + live_outer),
        "wall_loss": (live_lost + dead_lost) / total,
        "live_lost": live_lost,
        "dead_lost": dead_lost,
    }


def simulate_population(
    spec: SpiralSpec,
    field_stats: OpenFOAMFieldStats,
    seed: int,
    split: str,
    particles_per_class: int,
    steps: int,
    keep_paths: bool = False,
) -> tuple[list[dict], dict, list[dict]]:
    rng = np.random.default_rng(seed)
    results = []
    paths = []
    pid = 0
    for name in ["live", "dead"]:
        for _ in range(particles_per_class):
            cell = sample_cell(rng, name, spec.channel_width_m, 50e-6)
            result, path = run_particle(spec, cell, field_stats, rng, pid, steps, keep_paths)
            results.append(result)
            paths.extend(path)
            pid += 1
    return results, summarize(results, spec, seed, split), paths


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows: list[dict], split: str) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["split"] == split:
            grouped[row["case_id"]].append(row)
    out = []
    for cid, items in grouped.items():
        first = items[0]
        out.append(
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
    out.sort(
        key=lambda r: (
            r["mean_correct"],
            r["mean_live_recovery"],
            r["mean_dead_removal"],
            -r["mean_wall_loss"],
        ),
        reverse=True,
    )
    return out


def run_doe(field_stats: OpenFOAMFieldStats) -> tuple[list[dict], list[dict], list[dict], dict]:
    rows = []
    for turns in TURNS:
        for voltage in VOLTAGES:
            for velocity in VELOCITIES:
                spec = SpiralSpec(turns=turns, voltage_v=voltage, inlet_velocity_m_s=velocity)
                for split, seeds in [("design", DESIGN_SEEDS), ("validation", VALIDATION_SEEDS)]:
                    for seed in seeds:
                        _, summary, _ = simulate_population(spec, field_stats, seed, split, 180, 440)
                        rows.append(summary)
    design = aggregate(rows, "design")
    validation = aggregate(rows, "validation")
    validation_by_case = {r["case_id"]: r for r in validation}
    selection = {
        "selected_by_design": design[0],
        "selected_validation": validation_by_case[design[0]["case_id"]],
        "best_by_validation": validation[0],
    }
    return rows, design, validation, selection


def plot_outputs(validation_rows: list[dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    top = validation_rows[:24]
    labels = [r["case_id"].replace("_", "\n") for r in top]
    plt.figure(figsize=(14, 6))
    plt.bar(range(len(top)), [r["mean_correct"] for r in top], yerr=[r["std_correct"] for r in top], capsize=2)
    plt.axhline(0.85, color="black", linestyle="--", linewidth=1, label="screening target")
    plt.xticks(range(len(top)), labels, rotation=90, fontsize=6)
    plt.ylabel("Validation correct fraction")
    plt.ylim(0.35, 1.02)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "v3_validation_ranking.png", dpi=180)
    plt.close()

    metrics = [
        ("mean_live_recovery", "v3_live_recovery_heatmaps.png"),
        ("mean_dead_removal", "v3_dead_removal_heatmaps.png"),
        ("mean_wall_loss", "v3_wall_loss_heatmaps.png"),
    ]
    for metric, filename in metrics:
        fig, axes = plt.subplots(1, len(VELOCITIES), figsize=(15, 4), sharey=True)
        for ax, velocity in zip(axes, [v * 1e6 for v in VELOCITIES]):
            grid = np.full((len(TURNS), len(VOLTAGES)), np.nan)
            for row in validation_rows:
                if abs(row["velocity_um_s"] - velocity) < 1e-6:
                    grid[TURNS.index(row["turns"]), VOLTAGES.index(row["voltage_v"])] = row[metric]
            im = ax.imshow(grid, vmin=0.0, vmax=1.0, cmap="viridis", origin="lower")
            ax.set_title(f"{velocity:.0f} um/s")
            ax.set_xticks(range(len(VOLTAGES)), [f"{v:g}" for v in VOLTAGES])
            ax.set_yticks(range(len(TURNS)), [f"{t:g}" for t in TURNS])
            for i in range(len(TURNS)):
                for j in range(len(VOLTAGES)):
                    ax.text(j, i, f"{grid[i, j]:.2f}", ha="center", va="center", color="white", fontsize=8)
        fig.colorbar(im, ax=axes.ravel().tolist(), label=metric)
        fig.savefig(out_dir / filename, dpi=180, bbox_inches="tight")
        plt.close(fig)


def write_paraview_outputs(selection: dict, field_stats: OpenFOAMFieldStats) -> None:
    best = selection["best_by_validation"]
    spec = SpiralSpec(best["turns"], voltage_v=best["voltage_v"], inlet_velocity_m_s=best["velocity_um_s"] * 1e-6)
    particles, summary, records = simulate_population(spec, field_stats, VALIDATION_SEEDS[0], "visual", 120, 440, True)
    PARAVIEW_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(particles, DOE_DIR / "best_validation_visual_particles.csv")
    (DOE_DIR / "best_validation_visual_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_vtp_polyline(records, PARAVIEW_DIR / "best_validation_trajectories.vtp")
    frame_dir = PARAVIEW_DIR / "animation_frames"
    frames = []
    for i, progress in enumerate(np.linspace(0, 1, 90)):
        frame = frame_dir / f"frame_{i:04d}.vtp"
        write_vtp_frame(records, spec, float(progress), frame)
        frames.append(frame)
    write_pvd(frames, PARAVIEW_DIR / "best_validation_particles.pvd")


def write_readme(field_stats: OpenFOAMFieldStats, selection: dict, validation_rows: list[dict]) -> None:
    best = selection["best_by_validation"]
    selected = selection["selected_validation"]
    lines = [
        "# Design V3 OpenFOAM Hybrid DOE",
        "",
        "V3 uses the existing OpenFOAM spiral electric-potential solve as the",
        "device-field anchor, then runs a stochastic finite-size population model.",
        "",
        "This is not a deformable-cell solver. It is a computationally cheap",
        "optimization layer intended to be validated later with a heavier model",
        "or experiments.",
        "",
        "## OpenFOAM Field Anchor",
        "",
        f"- OpenFOAM case: `cases/design_v0`",
        f"- parsed field cells: `{field_stats.cell_count}`",
        f"- mean |grad(phi)|: `{field_stats.grad_mag_mean:.3g}`",
        f"- p95 |grad(phi)|: `{field_stats.grad_mag_p95:.3g}`",
        f"- max |grad(phi)|: `{field_stats.grad_mag_max:.3g}`",
        "",
        "## V3 Improvements Over V2",
        "",
        "- finite cell radius and 3D inlet z-position",
        "- Poiseuille-like axial velocity instead of constant residence time",
        "- Brownian lateral perturbation",
        "- stochastic adhesion/wall-loss after wall contact",
        "- voltage-dependent over-deflection risk through wall loss",
        "- design/validation seed split retained",
        "- multiple metrics retained: recovery, removal, purity, wall loss",
        "",
        "## Selected By Design, Checked On Validation",
        "",
        f"- case: `{selected['case_id']}`",
        f"- validation correct: `{selected['mean_correct']:.3f}`",
        f"- validation live recovery: `{selected['mean_live_recovery']:.3f}`",
        f"- validation dead removal: `{selected['mean_dead_removal']:.3f}`",
        f"- validation wall loss: `{selected['mean_wall_loss']:.3f}`",
        "",
        "## Best Validation Condition",
        "",
        f"- case: `{best['case_id']}`",
        f"- validation correct: `{best['mean_correct']:.3f}`",
        f"- validation live recovery: `{best['mean_live_recovery']:.3f}`",
        f"- validation dead removal: `{best['mean_dead_removal']:.3f}`",
        f"- validation live purity: `{best['mean_live_purity']:.3f}`",
        f"- validation dead outlet purity: `{best['mean_dead_outlet_purity']:.3f}`",
        f"- validation wall loss: `{best['mean_wall_loss']:.3f}`",
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
            "## Honest Limitations",
            "",
            "- It does not solve two-way fluid-cell coupling.",
            "- It does not deform cells.",
            "- It uses OpenFOAM field statistics, not full 3D interpolation at each point yet.",
            "- The next V4 step should sample `grad(|E|^2)` directly from cell centers or a VTK export.",
        ]
    )
    (DOE_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    DOE_DIR.mkdir(parents=True, exist_ok=True)
    run_openfoam_case()
    field_stats = load_openfoam_field_stats()
    rows, design_rows, validation_rows, selection = run_doe(field_stats)
    write_csv(rows, DOE_DIR / "v3_replicates.csv")
    write_csv(design_rows, DOE_DIR / "v3_design_summary.csv")
    write_csv(validation_rows, DOE_DIR / "v3_validation_summary.csv")
    (DOE_DIR / "v3_selection.json").write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    (DOE_DIR / "openfoam_field_stats.json").write_text(json.dumps(field_stats.__dict__, indent=2) + "\n", encoding="utf-8")
    plot_outputs(validation_rows, DOE_DIR)
    write_paraview_outputs(selection, field_stats)
    write_readme(field_stats, selection, validation_rows)
    print((DOE_DIR / "README.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
