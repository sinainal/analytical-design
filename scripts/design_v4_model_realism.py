#!/usr/bin/env python3
"""Design V4 model realism checks."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from design_v0_particle_tracking import SpiralSpec
from study_common import load_openfoam_field_stats, run_openfoam_case, simulate_population, write_csv


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "openfoam_design_v4" / "model_realism"

FREQUENCIES = [50e3, 100e3, 250e3, 455_326.0, 750e3, 1e6, 2e6]
OUTLET_SPLITS = [0.45, 0.50, 0.55]


def plot_frequency_sweep(rows: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for split in OUTLET_SPLITS:
        subset = [r for r in rows if abs(r["outlet_split_ratio"] - split) < 1e-9]
        subset.sort(key=lambda r: r["frequency_hz"])
        plt.plot(
            [r["frequency_hz"] / 1000 for r in subset],
            [r["target_correct"] for r in subset],
            marker="o",
            label=f"split {split:.2f}",
        )
    plt.axhline(0.5, color="0.25", linestyle="--", linewidth=1, label="random baseline")
    plt.xlabel("Frequency (kHz)")
    plt.ylabel("Target correct = max(correct A, correct B)")
    plt.ylim(0.2, 0.9)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "frequency_outlet_sweep.png", dpi=180)
    plt.close()


def plot_distribution(particles: list[dict], summary: dict) -> None:
    live = [p["final_lateral_um"] for p in particles if p["class"] == "live"]
    dead = [p["final_lateral_um"] for p in particles if p["class"] == "dead"]
    plt.figure(figsize=(7, 4))
    plt.hist(live, bins=24, alpha=0.65, label="live")
    plt.hist(dead, bins=24, alpha=0.65, label="dead")
    plt.axvline(-60 + 120 * summary["outlet_split_ratio"], color="black", linestyle="--", linewidth=1)
    plt.xlabel("Final lateral position (um)")
    plt.ylabel("Cell count")
    plt.title("Best V4 final lateral distribution")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "best_final_lateral_distribution.png", dpi=180)
    plt.close()


def write_readme(rows: list[dict], best: dict) -> None:
    lines = [
        "# Design V4 Model Realism",
        "",
        "V4 adds frequency-dependent live/dead CM response, outlet split ratio,",
        "and two outlet-label conventions:",
        "",
        "- `correct_A`: live to inner outlet, dead to outer outlet",
        "- `correct_B`: live to outer outlet, dead to inner outlet",
        "",
        "The reported target is `max(correct_A, correct_B)` so the model can reveal",
        "whether the physical separation direction is reversed.",
        "",
        "## Best Quick Condition",
        "",
        f"- case: `{best['case_id']}`",
        f"- target correct: `{best['target_correct']:.3f}`",
        f"- preferred direction: `{best['preferred_direction']}`",
        f"- correct A: `{best['correct_A_live_inner_dead_outer']:.3f}`",
        f"- correct B: `{best['correct_B_live_outer_dead_inner']:.3f}`",
        f"- wall loss: `{best['wall_loss']:.3f}`",
        f"- distribution gap: `{best['distribution_gap_um']:.3f} um`",
        "",
        "## Interpretation",
        "",
        "If both correct values stay near 0.5 and the distribution gap is small,",
        "the current design is not separating live/dead populations strongly. If",
        "`correct_B` exceeds `correct_A`, the outlet labeling assumption is reversed.",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_openfoam_case()
    field_stats = load_openfoam_field_stats()
    spec = SpiralSpec(turns=3.5, voltage_v=7.0, inlet_velocity_m_s=2600e-6)
    rows = []
    particle_cache = {}
    for frequency in FREQUENCIES:
        for split in OUTLET_SPLITS:
            particles, summary, _ = simulate_population(
                spec,
                field_stats,
                seed=23,
                particles_per_class=70,
                steps=220,
                frequency_hz=frequency,
                outlet_split_ratio=split,
            )
            rows.append(summary)
            particle_cache[summary["case_id"]] = particles
    rows.sort(key=lambda r: (r["target_correct"], -r["wall_loss"]), reverse=True)
    best = rows[0]
    write_csv(rows, OUT_DIR / "v4_frequency_outlet_sweep.csv")
    write_csv(particle_cache[best["case_id"]], OUT_DIR / "best_particles.csv")
    (OUT_DIR / "best_summary.json").write_text(json.dumps(best, indent=2) + "\n", encoding="utf-8")
    plot_frequency_sweep(rows)
    plot_distribution(particle_cache[best["case_id"]], best)
    write_readme(rows, best)
    print((OUT_DIR / "README.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
