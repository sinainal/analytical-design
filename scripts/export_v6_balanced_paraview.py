#!/usr/bin/env python3
"""Export ParaView-readable trajectories for the V6 balanced candidate."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from design_v1_doe import write_pvd, write_vtp_frame, write_vtp_polyline
from optimization_v1_surrogate import sample_from_summary
from study_common import load_openfoam_field_stats, run_openfoam_case, simulate_population, write_csv
from validation_v6_balanced_candidate import select_balanced_candidate


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "optimization_v1" / "balanced_synergy_validation"
PARAVIEW_DIR = OUT_DIR / "paraview"


def main() -> int:
    run_openfoam_case()
    field_stats = load_openfoam_field_stats()
    candidate, synergy = select_balanced_candidate()
    sample = sample_from_summary(candidate)
    spec = __import__("optimization_v1_surrogate").make_spec(sample)
    particles, summary, records = simulate_population(
        spec,
        field_stats,
        seed=3109,
        particles_per_class=100,
        steps=420,
        frequency_hz=sample["frequency_hz"],
        outlet_split_ratio=sample["outlet_split_ratio"],
        geometry="spiral",
        dep_enabled=True,
        dep_sign=sample.get("dep_sign", 1.0),
        keep_paths=True,
        inlet_offset_ratio=sample.get("inlet_offset_ratio", 0.0),
        inlet_spread_ratio=sample.get("inlet_spread_ratio", 1.0),
        dep_start_fraction=sample.get("dep_start_fraction", 0.0),
        dep_end_fraction=sample.get("dep_end_fraction", 1.0),
        dean_scale=sample.get("dean_scale", 1.0),
    )

    PARAVIEW_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(particles, OUT_DIR / "paraview_visual_particles.csv")
    (OUT_DIR / "paraview_visual_summary.json").write_text(
        json.dumps({"summary": summary, "candidate": candidate, "synergy": synergy}, indent=2) + "\n",
        encoding="utf-8",
    )
    write_vtp_polyline(records, PARAVIEW_DIR / "best_validation_trajectories.vtp")
    frame_dir = PARAVIEW_DIR / "animation_frames"
    frames = []
    for i, progress in enumerate(np.linspace(0.0, 1.0, 110)):
        frame = frame_dir / f"frame_{i:04d}.vtp"
        write_vtp_frame(records, spec, float(progress), frame)
        frames.append(frame)
    write_pvd(frames, PARAVIEW_DIR / "best_validation_particles.pvd")
    (PARAVIEW_DIR / "v6_balanced.foam").write_text("", encoding="utf-8")
    (PARAVIEW_DIR / "README.md").write_text(
        "# V6 Balanced Candidate ParaView Outputs\n\n"
        "Open `best_validation_particles.pvd` for the time-resolved particle animation, "
        "or `best_validation_trajectories.vtp` for complete paths.\n",
        encoding="utf-8",
    )
    print(f"Wrote V6 balanced ParaView files to {PARAVIEW_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
