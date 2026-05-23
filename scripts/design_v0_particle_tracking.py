#!/usr/bin/env python3
"""Reduced-order live/dead trajectory simulation for Design V0.

This script uses the Design V0 spiral geometry and the selected CM-factor
values from the first frequency scan. It is intentionally lightweight: the
OpenFOAM case validates the spiral mesh and electrode potential solve, while
this script tests whether the resulting design hypothesis can create outlet
separation under a simple DEP-plus-drift particle model.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "openfoam_design_v0" / "trajectories"

EPS0 = 8.8541878128e-12
MEDIUM_EPS_R = 80.0
MEDIUM_VISCOSITY_PA_S = 1.0e-3


@dataclass(frozen=True)
class SpiralSpec:
    turns: float = 3.0
    inner_radius_m: float = 1000e-6
    pitch_m: float = 180e-6
    channel_width_m: float = 120e-6
    voltage_v: float = 8.0
    inlet_velocity_m_s: float = 1000e-6


@dataclass(frozen=True)
class CellClass:
    name: str
    radius_m: float
    re_cm: float
    color_bgr: tuple[int, int, int]


LIVE = CellClass("live", 11.5e-6, 0.976616, (50, 80, 235))
DEAD = CellClass("dead", 11.0e-6, -0.000044, (235, 130, 30))


def centerline(spec: SpiralSpec, theta: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    b = spec.pitch_m / (2.0 * math.pi)
    radius = spec.inner_radius_m + b * theta
    return radius * np.cos(theta), radius * np.sin(theta)


def centerline_scalar(spec: SpiralSpec, theta: float) -> tuple[float, float]:
    b = spec.pitch_m / (2.0 * math.pi)
    radius = spec.inner_radius_m + b * theta
    return radius * math.cos(theta), radius * math.sin(theta)


def tangent_normal(spec: SpiralSpec, theta: float) -> tuple[float, float, float, float]:
    b = spec.pitch_m / (2.0 * math.pi)
    radius = spec.inner_radius_m + b * theta
    dx = b * math.cos(theta) - radius * math.sin(theta)
    dy = b * math.sin(theta) + radius * math.cos(theta)
    norm = math.hypot(dx, dy)
    tx, ty = dx / norm, dy / norm
    nx, ny = -ty, tx
    return tx, ty, nx, ny


def point_xy(spec: SpiralSpec, theta: float, lateral_m: float) -> tuple[float, float]:
    cx, cy = centerline_scalar(spec, theta)
    _, _, nx, ny = tangent_normal(spec, theta)
    return cx + lateral_m * nx, cy + lateral_m * ny


def ds_dtheta(spec: SpiralSpec, theta: float) -> float:
    b = spec.pitch_m / (2.0 * math.pi)
    radius = spec.inner_radius_m + b * theta
    return math.sqrt(radius * radius + b * b)


def dep_lateral_velocity(spec: SpiralSpec, cell: CellClass, lateral_m: float) -> float:
    """Return lateral DEP velocity; negative is toward the inner electrode."""
    width = spec.channel_width_m
    eps_m = EPS0 * MEDIUM_EPS_R
    electric_field = spec.voltage_v / width
    decay_length = 0.35 * width
    distance_from_inner = lateral_m + 0.5 * width

    e2 = electric_field * electric_field * math.exp(-distance_from_inner / decay_length)
    grad_e2 = -e2 / decay_length

    # Reduced-order attenuation: the real 3D side-wall field gradient is weaker
    # than the 1D wall estimate across much of the channel.
    gradient_attenuation = 7.5e-4
    force_velocity = (
        eps_m
        * cell.radius_m
        * cell.radius_m
        * cell.re_cm
        * gradient_attenuation
        * grad_e2
        / (3.0 * MEDIUM_VISCOSITY_PA_S)
    )
    return force_velocity


def simulate(
    spec: SpiralSpec,
    particles_per_class: int,
    steps: int,
    seed: int,
) -> tuple[list[dict], dict]:
    rng = np.random.default_rng(seed)
    theta_end = 2.0 * math.pi * spec.turns
    dt = theta_end / steps
    records: list[dict] = []
    summary: dict[str, dict] = {}

    for cell in [LIVE, DEAD]:
        final_inner = 0
        stalled = 0
        final_laterals = []
        for particle_id in range(particles_per_class):
            lateral = float(rng.normal(0.0, 0.12 * spec.channel_width_m))
            lateral = float(np.clip(lateral, -0.32 * spec.channel_width_m, 0.32 * spec.channel_width_m))
            theta = 0.0
            path: list[tuple[float, float, float, float]] = []

            for step in range(steps + 1):
                x, y = point_xy(spec, theta, lateral)
                path.append((step / steps, theta, lateral, x, y))
                if step == steps:
                    break

                local_dt_s = ds_dtheta(spec, theta) * dt / spec.inlet_velocity_m_s
                dep_v = dep_lateral_velocity(spec, cell, lateral)

                # Small outward Dean-like drift placeholder. This keeps the
                # reduced model from becoming a pure electric-field plot.
                dean_v = 0.18e-6
                lateral += (dep_v + dean_v) * local_dt_s
                lateral = float(np.clip(lateral, -0.49 * spec.channel_width_m, 0.49 * spec.channel_width_m))
                theta += dt

            outlet = "inner" if lateral < 0 else "outer"
            final_inner += int(outlet == "inner")
            final_laterals.append(lateral)
            if abs(lateral) > 0.485 * spec.channel_width_m:
                stalled += 1

            for progress, path_theta, path_lateral, x, y in path:
                records.append(
                    {
                        "class": cell.name,
                        "particle_id": particle_id,
                        "progress": progress,
                        "theta_rad": path_theta,
                        "lateral_m": path_lateral,
                        "x_m": x,
                        "y_m": y,
                        "outlet": outlet if progress == 1.0 else "",
                    }
                )

        inner_fraction = final_inner / particles_per_class
        summary[cell.name] = {
            "particles": particles_per_class,
            "inner_outlet": final_inner,
            "outer_outlet": particles_per_class - final_inner,
            "inner_fraction": inner_fraction,
            "mean_final_lateral_um": float(np.mean(final_laterals) * 1e6),
            "std_final_lateral_um": float(np.std(final_laterals) * 1e6),
            "wall_limited_count": stalled,
        }

    live_inner = summary["live"]["inner_outlet"]
    dead_outer = summary["dead"]["outer_outlet"]
    summary["overall"] = {
        "correct_if_live_inner_dead_outer": live_inner + dead_outer,
        "total_particles": 2 * particles_per_class,
        "correct_fraction": (live_inner + dead_outer) / (2 * particles_per_class),
        "model_status": "reduced_order_first_pass",
        "turns": spec.turns,
        "voltage_v": spec.voltage_v,
        "inlet_velocity_m_s": spec.inlet_velocity_m_s,
    }
    return records, summary


def write_csv(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["class", "particle_id", "progress", "theta_rad", "lateral_m", "x_m", "y_m", "outlet"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def plot_static(records: list[dict], spec: SpiralSpec, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    theta = np.linspace(0, 2.0 * math.pi * spec.turns, 700)
    cx, cy = centerline(spec, theta)

    plt.figure(figsize=(7.2, 7.2))
    plt.plot(cx * 1e3, cy * 1e3, color="0.75", linewidth=8, solid_capstyle="round")
    for label, color in [("live", "#e34a33"), ("dead", "#1f78b4")]:
        subset = [r for r in records if r["class"] == label and r["particle_id"] < 24]
        by_id: dict[int, list[dict]] = {}
        for row in subset:
            by_id.setdefault(int(row["particle_id"]), []).append(row)
        for rows in by_id.values():
            plt.plot(
                [r["x_m"] * 1e3 for r in rows],
                [r["y_m"] * 1e3 for r in rows],
                color=color,
                alpha=0.45,
                linewidth=1.2,
            )
    plt.axis("equal")
    plt.xlabel("x (mm)")
    plt.ylabel("y (mm)")
    plt.title("Design V0 reduced-order live/dead trajectories")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def world_to_pixel(x: float, y: float, bounds: tuple[float, float, float, float], size: int) -> tuple[int, int]:
    xmin, xmax, ymin, ymax = bounds
    pad = 0.08
    xrange = xmax - xmin
    yrange = ymax - ymin
    xmin -= pad * xrange
    xmax += pad * xrange
    ymin -= pad * yrange
    ymax += pad * yrange
    px = int((x - xmin) / (xmax - xmin) * (size - 1))
    py = int((1.0 - (y - ymin) / (ymax - ymin)) * (size - 1))
    return px, py


def render_video(records: list[dict], spec: SpiralSpec, path: Path, frames: int, size: int, fps: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    theta = np.linspace(0, 2.0 * math.pi * spec.turns, 1600)
    cx, cy = centerline(spec, theta)
    bounds = (float(cx.min()), float(cx.max()), float(cy.min()), float(cy.max()))
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (size, size),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Could not open video writer: {path}")

    by_key: dict[tuple[str, int], list[dict]] = {}
    for row in records:
        by_key.setdefault((row["class"], int(row["particle_id"])), []).append(row)

    try:
        for frame_index in range(frames):
            progress_limit = frame_index / max(1, frames - 1)
            image = np.full((size, size, 3), 248, dtype=np.uint8)

            for i in range(len(cx) - 1):
                p1 = world_to_pixel(float(cx[i]), float(cy[i]), bounds, size)
                p2 = world_to_pixel(float(cx[i + 1]), float(cy[i + 1]), bounds, size)
                cv2.line(image, p1, p2, (210, 210, 210), 18, lineType=cv2.LINE_AA)
                cv2.line(image, p1, p2, (160, 160, 160), 1, lineType=cv2.LINE_AA)

            for (cell_name, _), rows in by_key.items():
                color = LIVE.color_bgr if cell_name == "live" else DEAD.color_bgr
                visible = [r for r in rows if r["progress"] <= progress_limit]
                if not visible:
                    continue
                points = [world_to_pixel(float(r["x_m"]), float(r["y_m"]), bounds, size) for r in visible]
                for p1, p2 in zip(points[:-1], points[1:]):
                    cv2.line(image, p1, p2, color, 1, lineType=cv2.LINE_AA)
                cv2.circle(image, points[-1], 3, color, -1, lineType=cv2.LINE_AA)

            cv2.putText(image, "fixed camera - reduced-order trajectories", (24, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (40, 40, 40), 2)
            cv2.putText(image, "live: red   dead: blue", (24, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (40, 40, 40), 2)
            cv2.putText(image, f"progress {progress_limit * 100:5.1f}%", (24, size - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (40, 40, 40), 2)
            writer.write(image)
    finally:
        writer.release()


def write_summary(summary: dict, path: Path) -> None:
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = [
        "Design V0 reduced-order trajectory summary",
        "==========================================",
        "",
        f"Turns: {summary['overall']['turns']}",
        f"Voltage: {summary['overall']['voltage_v']} V",
        f"Inlet velocity: {summary['overall']['inlet_velocity_m_s'] * 1e6:.0f} um/s",
        "",
        f"Live inner outlet: {summary['live']['inner_outlet']} / {summary['live']['particles']}",
        f"Dead outer outlet: {summary['dead']['outer_outlet']} / {summary['dead']['particles']}",
        f"Correct fraction: {summary['overall']['correct_fraction']:.3f}",
        f"Live mean final lateral: {summary['live']['mean_final_lateral_um']:.2f} um",
        f"Dead mean final lateral: {summary['dead']['mean_final_lateral_um']:.2f} um",
        "",
        "Status: reduced-order first pass; not yet field-interpolated from OpenFOAM.",
    ]
    (path.parent / "trajectory_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--particles", type=int, default=100)
    parser.add_argument("--steps", type=int, default=360)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--turns", type=float, default=3.0)
    parser.add_argument("--voltage", type=float, default=8.0)
    parser.add_argument("--velocity", type=float, default=1000e-6)
    parser.add_argument("--frames", type=int, default=144)
    parser.add_argument("--size", type=int, default=900)
    parser.add_argument("--fps", type=float, default=24.0)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--skip-video", action="store_true")
    parser.add_argument("--skip-plot", action="store_true")
    args = parser.parse_args()

    spec = SpiralSpec(
        turns=args.turns,
        voltage_v=args.voltage,
        inlet_velocity_m_s=args.velocity,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    records, summary = simulate(spec, args.particles, args.steps, args.seed)
    write_csv(records, args.out_dir / "design_v0_trajectories.csv")
    write_summary(summary, args.out_dir / "trajectory_summary.json")
    if not args.skip_plot:
        plot_static(records, spec, args.out_dir / "design_v0_trajectory_plot.png")
    if not args.skip_video:
        render_video(
            records,
            spec,
            args.out_dir / "design_v0_trajectory_video.mp4",
            args.frames,
            args.size,
            args.fps,
        )
    print((args.out_dir / "trajectory_summary.txt").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
