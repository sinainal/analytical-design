#!/usr/bin/env python3
"""Design V1 DOE sweep with ParaView-readable trajectory outputs."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from design_v0_particle_tracking import SpiralSpec, centerline, simulate


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "openfoam_design_v1" / "doe"
PARAVIEW_DIR = ROOT / "results" / "openfoam_design_v1" / "paraview"


SEEDS = [7, 11, 13, 17, 19]
TURNS = [3.0, 4.0, 5.0]
VOLTAGES = [8.0, 10.0, 12.0]
VELOCITIES = [1000e-6, 2000e-6, 3000e-6]


def case_id(turns: float, voltage: float, velocity: float) -> str:
    return f"turns_{turns:g}_voltage_{voltage:g}_velocity_{velocity * 1e6:.0f}um_s"


def run_doe() -> tuple[list[dict], dict, list[dict]]:
    rows = []
    replicate_rows = []
    for turns in TURNS:
        for voltage in VOLTAGES:
            for velocity in VELOCITIES:
                cid = case_id(turns, voltage, velocity)
                scores = []
                live_inner = []
                dead_outer = []
                wall_limited = []
                for seed in SEEDS:
                    spec = SpiralSpec(
                        turns=turns,
                        voltage_v=voltage,
                        inlet_velocity_m_s=velocity,
                    )
                    _, summary = simulate(spec, particles_per_class=100, steps=360, seed=seed)
                    correct = summary["overall"]["correct_fraction"]
                    live_inner_fraction = summary["live"]["inner_fraction"]
                    dead_outer_fraction = summary["dead"]["outer_outlet"] / summary["dead"]["particles"]
                    scores.append(correct)
                    live_inner.append(live_inner_fraction)
                    dead_outer.append(dead_outer_fraction)
                    wall_limited.append(summary["live"]["wall_limited_count"] + summary["dead"]["wall_limited_count"])
                    replicate_rows.append(
                        {
                            "case_id": cid,
                            "seed": seed,
                            "turns": turns,
                            "voltage_v": voltage,
                            "velocity_um_s": velocity * 1e6,
                            "correct_fraction": correct,
                            "live_inner_fraction": live_inner_fraction,
                            "dead_outer_fraction": dead_outer_fraction,
                            "wall_limited_count": wall_limited[-1],
                        }
                    )

                row = {
                    "case_id": cid,
                    "turns": turns,
                    "voltage_v": voltage,
                    "velocity_um_s": velocity * 1e6,
                    "mean_correct": float(np.mean(scores)),
                    "std_correct": float(np.std(scores, ddof=1)),
                    "min_correct": float(np.min(scores)),
                    "robust_score": float(np.mean(scores) - np.std(scores, ddof=1)),
                    "mean_live_inner": float(np.mean(live_inner)),
                    "mean_dead_outer": float(np.mean(dead_outer)),
                    "mean_wall_limited": float(np.mean(wall_limited)),
                }
                rows.append(row)

    rows.sort(key=lambda row: (row["robust_score"], row["mean_correct"]), reverse=True)
    return rows, rows[0], replicate_rows


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def plot_doe(rows: list[dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    labels = [row["case_id"].replace("_", "\n") for row in rows]
    values = [row["mean_correct"] for row in rows]
    errors = [row["std_correct"] for row in rows]
    colors = ["#238b45" if row["min_correct"] >= 0.9 else "#74c476" if row["mean_correct"] >= 0.9 else "#fd8d3c" for row in rows]

    plt.figure(figsize=(14, 6))
    plt.bar(range(len(rows)), values, yerr=errors, color=colors, capsize=2)
    plt.axhline(0.9, color="black", linestyle="--", linewidth=1, label="publication target")
    plt.axhline(0.8, color="0.4", linestyle=":", linewidth=1, label="screening target")
    plt.xticks(range(len(rows)), labels, rotation=90, fontsize=6)
    plt.ylabel("Mean correct classification")
    plt.ylim(0.45, 1.02)
    plt.title("Design V1 DOE: mean classification with seed variability")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "doe_mean_correct_with_seed_error.png", dpi=180)
    plt.close()

    grouped: dict[float, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["velocity_um_s"]].append(row)

    fig, axes = plt.subplots(1, len(VELOCITIES), figsize=(14, 4), sharey=True)
    for ax, velocity in zip(axes, sorted(grouped)):
        grid = np.full((len(TURNS), len(VOLTAGES)), np.nan)
        for row in grouped[velocity]:
            i = TURNS.index(row["turns"])
            j = VOLTAGES.index(row["voltage_v"])
            grid[i, j] = row["mean_correct"]
        im = ax.imshow(grid, vmin=0.5, vmax=1.0, cmap="viridis", origin="lower")
        ax.set_title(f"{velocity:.0f} um/s")
        ax.set_xticks(range(len(VOLTAGES)), [f"{v:g}V" for v in VOLTAGES])
        ax.set_yticks(range(len(TURNS)), [f"{t:g}T" for t in TURNS])
        ax.set_xlabel("Voltage")
        if ax is axes[0]:
            ax.set_ylabel("Turns")
        for i in range(len(TURNS)):
            for j in range(len(VOLTAGES)):
                ax.text(j, i, f"{grid[i, j]:.2f}", ha="center", va="center", color="white", fontsize=8)
    fig.colorbar(im, ax=axes.ravel().tolist(), label="Mean correct classification")
    fig.suptitle("Design V1 DOE heatmaps")
    fig.savefig(out_dir / "doe_heatmaps.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def xml_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_vtp_polyline(records: list[dict], path: Path) -> None:
    by_key: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in records:
        by_key[(row["class"], int(row["particle_id"]))].append(row)

    points = []
    lines = []
    class_ids = []
    offset = 0
    for (name, _), rows in sorted(by_key.items()):
        rows = sorted(rows, key=lambda row: row["progress"])
        indices = []
        class_id = 1 if name == "live" else 2
        for row in rows:
            points.append((row["x_m"], row["y_m"], 0.0))
            class_ids.append(class_id)
            indices.append(offset)
            offset += 1
        lines.append(indices)

    connectivity = " ".join(str(i) for line in lines for i in line)
    offsets = []
    running = 0
    for line in lines:
        running += len(line)
        offsets.append(str(running))

    point_text = "\n".join(f"{x:.12g} {y:.12g} {z:.12g}" for x, y, z in points)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""<?xml version="1.0"?>
<VTKFile type="PolyData" version="0.1" byte_order="LittleEndian">
  <PolyData>
    <Piece NumberOfPoints="{len(points)}" NumberOfLines="{len(lines)}">
      <PointData Scalars="class_id">
        <DataArray type="Int32" Name="class_id" format="ascii">
          {' '.join(str(v) for v in class_ids)}
        </DataArray>
      </PointData>
      <Points>
        <DataArray type="Float32" NumberOfComponents="3" format="ascii">
{point_text}
        </DataArray>
      </Points>
      <Lines>
        <DataArray type="Int32" Name="connectivity" format="ascii">{connectivity}</DataArray>
        <DataArray type="Int32" Name="offsets" format="ascii">{' '.join(offsets)}</DataArray>
      </Lines>
    </Piece>
  </PolyData>
</VTKFile>
""",
        encoding="utf-8",
    )


def write_vtp_frame(records: list[dict], spec: SpiralSpec, progress: float, path: Path) -> None:
    by_key: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in records:
        by_key[(row["class"], int(row["particle_id"]))].append(row)

    particle_points = []
    class_ids = []
    for (name, _), rows in sorted(by_key.items()):
        rows = sorted(rows, key=lambda row: row["progress"])
        selected = min(rows, key=lambda row: abs(row["progress"] - progress))
        particle_points.append((selected["x_m"], selected["y_m"], 0.0))
        class_ids.append(1 if name == "live" else 2)

    theta = np.linspace(0, 2.0 * math.pi * spec.turns, 900)
    cx, cy = centerline(spec, theta)
    channel_points = [(float(x), float(y), 0.0) for x, y in zip(cx, cy)]
    points = channel_points + particle_points
    class_ids = [0] * len(channel_points) + class_ids
    vertex_indices = list(range(len(channel_points), len(points)))
    point_text = "\n".join(f"{x:.12g} {y:.12g} {z:.12g}" for x, y, z in points)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""<?xml version="1.0"?>
<VTKFile type="PolyData" version="0.1" byte_order="LittleEndian">
  <PolyData>
    <Piece NumberOfPoints="{len(points)}" NumberOfLines="1" NumberOfVerts="{len(vertex_indices)}">
      <PointData Scalars="class_id">
        <DataArray type="Int32" Name="class_id" format="ascii">{' '.join(str(v) for v in class_ids)}</DataArray>
      </PointData>
      <Points>
        <DataArray type="Float32" NumberOfComponents="3" format="ascii">
{point_text}
        </DataArray>
      </Points>
      <Lines>
        <DataArray type="Int32" Name="connectivity" format="ascii">{' '.join(str(i) for i in range(len(channel_points)))}</DataArray>
        <DataArray type="Int32" Name="offsets" format="ascii">{len(channel_points)}</DataArray>
      </Lines>
      <Verts>
        <DataArray type="Int32" Name="connectivity" format="ascii">{' '.join(str(i) for i in vertex_indices)}</DataArray>
        <DataArray type="Int32" Name="offsets" format="ascii">{' '.join(str(i + 1) for i in range(len(vertex_indices)))}</DataArray>
      </Verts>
    </Piece>
  </PolyData>
</VTKFile>
""",
        encoding="utf-8",
    )


def write_pvd(frame_paths: list[Path], path: Path) -> None:
    datasets = "\n".join(
        f'    <DataSet timestep="{i}" group="" part="0" file="{xml_escape(str(frame.relative_to(path.parent)))}"/>'
        for i, frame in enumerate(frame_paths)
    )
    path.write_text(
        f"""<?xml version="1.0"?>
<VTKFile type="Collection" version="0.1" byte_order="LittleEndian">
  <Collection>
{datasets}
  </Collection>
</VTKFile>
""",
        encoding="utf-8",
    )


def write_readme(rows: list[dict], best: dict, out_dir: Path) -> None:
    target = "pass" if best["min_correct"] >= 0.9 else "not yet pass"
    lines = [
        "# Design V1 DOE",
        "",
        "Design V1 runs a 27-condition, 5-seed DOE over the first three",
        "optimization parameters: turn count, voltage, and inlet velocity.",
        "",
        "## Targets",
        "",
        "- screening target: `>= 80%` correct classification",
        "- publication-level target: mean `>= 90%` and minimum seed result `>= 90%`",
        "",
        "## Best Robust Condition",
        "",
        f"- case: `{best['case_id']}`",
        f"- mean correct: `{best['mean_correct']:.3f}`",
        f"- std correct: `{best['std_correct']:.3f}`",
        f"- min correct across seeds: `{best['min_correct']:.3f}`",
        f"- robust target status: `{target}`",
        "",
        "## Top Conditions",
        "",
        "| Rank | Case | Mean | Std | Min | Live inner | Dead outer |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for i, row in enumerate(rows[:10], 1):
        lines.append(
            f"| {i} | `{row['case_id']}` | {row['mean_correct']:.3f} | "
            f"{row['std_correct']:.3f} | {row['min_correct']:.3f} | "
            f"{row['mean_live_inner']:.3f} | {row['mean_dead_outer']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## ParaView Outputs",
            "",
            "- `../paraview/best_case_trajectories.vtp`: all best-case trajectory lines",
            "- `../paraview/best_case_particles.pvd`: time-resolved fixed-camera particle animation source",
            "",
            "These files can be opened directly in ParaView.",
        ]
    )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PARAVIEW_DIR.mkdir(parents=True, exist_ok=True)
    rows, best, replicate_rows = run_doe()
    write_csv(rows, OUT_DIR / "doe_summary.csv")
    write_csv(replicate_rows, OUT_DIR / "doe_replicates.csv")
    plot_doe(rows, OUT_DIR)
    write_readme(rows, best, OUT_DIR)

    best_spec = SpiralSpec(
        turns=best["turns"],
        voltage_v=best["voltage_v"],
        inlet_velocity_m_s=best["velocity_um_s"] * 1e-6,
    )
    records, summary = simulate(best_spec, particles_per_class=100, steps=360, seed=SEEDS[0])
    (OUT_DIR / "best_case_seed7_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_vtp_polyline(records, PARAVIEW_DIR / "best_case_trajectories.vtp")
    frame_paths = []
    frame_dir = PARAVIEW_DIR / "animation_frames"
    for i, progress in enumerate(np.linspace(0, 1, 80)):
        frame = frame_dir / f"frame_{i:04d}.vtp"
        write_vtp_frame(records, best_spec, float(progress), frame)
        frame_paths.append(frame)
    write_pvd(frame_paths, PARAVIEW_DIR / "best_case_particles.pvd")

    print((OUT_DIR / "README.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
