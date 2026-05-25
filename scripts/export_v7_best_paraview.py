#!/usr/bin/env python3
"""Export ParaView-readable animation files for the V7 best candidate."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from design_v1_doe import write_pvd, write_vtp_frame, write_vtp_polyline
from design_v7_geometry_feasibility import (
    OUT_DIR,
    families_from_v6,
    read_balanced_v6,
    sample_from_row,
    simulate_sample,
    spec_from_sample,
)
from study_common import load_openfoam_field_stats, run_openfoam_case, write_csv


PARAVIEW_DIR = OUT_DIR / "paraview"


def read_best_screen_row() -> dict:
    with (OUT_DIR / "v7_validation_summary.csv").open(newline="", encoding="utf-8") as handle:
        best = next(csv.DictReader(handle))
    sample_id = int(best["sample_id"])
    with (OUT_DIR / "v7_screening_rows.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if int(row["sample_id"]) == sample_id:
                out = {}
                for key, value in row.items():
                    try:
                        out[key] = float(value)
                    except ValueError:
                        out[key] = value
                return out
    raise FileNotFoundError(f"sample_id {sample_id} not found in v7_screening_rows.csv")


def main() -> int:
    run_openfoam_case()
    field_stats = load_openfoam_field_stats()
    base = read_balanced_v6()
    family_map = {family.name: family for family in families_from_v6(base)}
    row = read_best_screen_row()
    family = family_map[row["family"]]
    sample = sample_from_row(row)
    spec = spec_from_sample(sample)

    particles, summary, _ = simulate_sample(
        sample,
        family,
        field_stats,
        seed=9701,
        particles_per_class=120,
        steps=420,
    )

    # Re-run with paths kept by calling simulate_sample's underlying convention
    # through a local copy of the same parameters.
    from study_common import sample_cell, run_particle

    rng = np.random.default_rng(9701)
    records = []
    pid = 0
    length_m = row["length_mm"] * 1e-3
    for name in ["live", "dead"]:
        for _ in range(120):
            cell = sample_cell(
                rng,
                name,
                spec.channel_width_m,
                sample["frequency_hz"],
                inlet_offset_ratio=sample["inlet_offset_ratio"],
                inlet_spread_ratio=sample["inlet_spread_ratio"],
            )
            _, path = run_particle(
                spec,
                cell,
                field_stats,
                rng,
                pid,
                420,
                sample["frequency_hz"],
                sample["outlet_split_ratio"],
                geometry=family.path_geometry,
                dep_enabled=True,
                dep_sign=sample["dep_sign"],
                keep_path=True,
                length_m=length_m,
                dep_start_fraction=sample["dep_start_fraction"],
                dep_end_fraction=sample["dep_end_fraction"],
                dean_scale=sample["dean_scale"],
            )
            records.extend(path)
            pid += 1

    PARAVIEW_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(particles, OUT_DIR / "v7_best_visual_particles.csv")
    (OUT_DIR / "v7_best_visual_summary.json").write_text(
        json.dumps({"family": family.name, "screen_row": row, "summary": summary}, indent=2) + "\n",
        encoding="utf-8",
    )
    write_vtp_polyline(records, PARAVIEW_DIR / "v7_best_trajectories.vtp")
    frame_dir = PARAVIEW_DIR / "animation_frames"
    frames = []
    for i, progress in enumerate(np.linspace(0.0, 1.0, 110)):
        frame = frame_dir / f"frame_{i:04d}.vtp"
        write_vtp_frame(records, spec, float(progress), frame)
        frames.append(frame)
    write_pvd(frames, PARAVIEW_DIR / "v7_best_particles.pvd")
    (PARAVIEW_DIR / "README.md").write_text(
        "# V7 Best Candidate ParaView Outputs\n\n"
        "Open `v7_best_particles.pvd` for time-resolved particle animation, or "
        "`v7_best_trajectories.vtp` for full trajectories.\n\n"
        "Note: the visible path is a spiral channel; the `stepwise` part of the "
        "V7 candidate is modeled as late segmented DEP activation rather than "
        "a serrated physical wall shape.\n",
        encoding="utf-8",
    )
    print(f"Wrote V7 ParaView files to {PARAVIEW_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
