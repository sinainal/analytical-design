#!/usr/bin/env python3
"""Design V6 fast optimization scaffold."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from design_v0_particle_tracking import SpiralSpec
from study_common import load_openfoam_field_stats, run_openfoam_case, simulate_population, write_csv


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "openfoam_design_v6" / "optimization_setup"

QUICK_SAMPLES = 48
QUICK_SEED = 101
VALIDATION_SEEDS = [101, 103, 107]

RANGES = {
    "frequency_hz": (50e3, 2.0e6),
    "voltage_v": (4.0, 18.0),
    "velocity_m_s": (600e-6, 4500e-6),
    "turns": (2.5, 7.0),
    "pitch_m": (120e-6, 320e-6),
    "channel_width_m": (70e-6, 180e-6),
    "outlet_split_ratio": (0.35, 0.65),
}


def latin_hypercube(n: int, ranges: dict[str, tuple[float, float]], seed: int) -> list[dict]:
    rng = np.random.default_rng(seed)
    keys = list(ranges)
    columns = {}
    for key in keys:
        low, high = ranges[key]
        values = (np.arange(n) + rng.random(n)) / n
        rng.shuffle(values)
        columns[key] = low + values * (high - low)
    return [{key: float(columns[key][i]) for key in keys} for i in range(n)]


def make_spec(row: dict) -> SpiralSpec:
    return SpiralSpec(
        turns=row["turns"],
        pitch_m=row["pitch_m"],
        channel_width_m=row["channel_width_m"],
        voltage_v=row["voltage_v"],
        inlet_velocity_m_s=row["velocity_m_s"],
    )


def score(row: dict) -> float:
    hard_penalty = 0.8 if row["wall_loss"] > 0.20 else 0.0
    return row["target_correct"] - 1.2 * row["wall_loss"] + 0.004 * row["distribution_gap_um"] - hard_penalty


def run_quick(field_stats) -> tuple[list[dict], list[dict]]:
    rows = []
    samples = latin_hypercube(QUICK_SAMPLES, RANGES, seed=2026)
    for i, sample in enumerate(samples):
        spec = make_spec(sample)
        _, summary, _ = simulate_population(
            spec,
            field_stats,
            seed=QUICK_SEED,
            particles_per_class=60,
            steps=180,
            frequency_hz=sample["frequency_hz"],
            outlet_split_ratio=sample["outlet_split_ratio"],
        )
        summary["sample_id"] = i
        summary["optimization_score"] = score(summary)
        rows.append(summary)
    rows.sort(key=lambda r: r["optimization_score"], reverse=True)
    return samples, rows


def run_validation(field_stats, quick_rows: list[dict], samples: list[dict]) -> list[dict]:
    selected = quick_rows[:5]
    validation = []
    for quick in selected:
        sample = samples[int(quick["sample_id"])]
        spec = make_spec(sample)
        for seed in VALIDATION_SEEDS:
            _, summary, _ = simulate_population(
                spec,
                field_stats,
                seed=seed,
                particles_per_class=80,
                steps=220,
                frequency_hz=sample["frequency_hz"],
                outlet_split_ratio=sample["outlet_split_ratio"],
            )
            summary["sample_id"] = quick["sample_id"]
            summary["optimization_score"] = score(summary)
            validation.append(summary)
    return validation


def aggregate_validation(rows: list[dict]) -> list[dict]:
    out = []
    for sample_id in sorted({int(r["sample_id"]) for r in rows}):
        items = [r for r in rows if int(r["sample_id"]) == sample_id]
        first = items[0]
        out.append(
            {
                "sample_id": sample_id,
                "case_id": first["case_id"],
                "mean_target_correct": float(np.mean([r["target_correct"] for r in items])),
                "std_target_correct": float(np.std([r["target_correct"] for r in items], ddof=1)),
                "mean_wall_loss": float(np.mean([r["wall_loss"] for r in items])),
                "mean_gap_um": float(np.mean([r["distribution_gap_um"] for r in items])),
                "mean_score": float(np.mean([r["optimization_score"] for r in items])),
                "preferred_direction": first["preferred_direction"],
            }
        )
    out.sort(key=lambda r: r["mean_score"], reverse=True)
    return out


def plot_results(quick_rows: list[dict], validation_summary: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 4))
    plt.scatter(
        [r["wall_loss"] for r in quick_rows],
        [r["target_correct"] for r in quick_rows],
        c=[r["optimization_score"] for r in quick_rows],
        cmap="viridis",
    )
    plt.axhline(0.8, color="black", linestyle="--", linewidth=1, label="target correct 0.8")
    plt.axvline(0.15, color="0.4", linestyle=":", linewidth=1, label="wall loss 0.15")
    plt.xlabel("Wall loss")
    plt.ylabel("Target correct")
    plt.colorbar(label="Optimization score")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "quick_search_correct_vs_wall_loss.png", dpi=180)
    plt.close()

    labels = [str(r["sample_id"]) for r in validation_summary]
    plt.figure(figsize=(7, 4))
    plt.bar(range(len(validation_summary)), [r["mean_target_correct"] for r in validation_summary])
    plt.axhline(0.8, color="black", linestyle="--", linewidth=1)
    plt.xticks(range(len(validation_summary)), labels)
    plt.xlabel("Sample id")
    plt.ylabel("Validation target correct")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "top5_validation_correct.png", dpi=180)
    plt.close()


def write_readme(quick_rows: list[dict], validation_summary: list[dict]) -> None:
    best_quick = quick_rows[0]
    best_val = validation_summary[0]
    lines = [
        "# Design V6 Optimization Setup",
        "",
        "This is the fast optimization handoff. It uses Latin hypercube sampling",
        "for broad coverage and validates the top five quick candidates with",
        "three seeds.",
        "",
        "## Scope",
        "",
        f"- quick samples: `{QUICK_SAMPLES}`",
        "- quick particles: `60 live + 60 dead`",
        "- validation particles: `80 live + 80 dead`",
        f"- validation seeds: `{VALIDATION_SEEDS}`",
        "",
        "## Optimization Variables",
        "",
    ]
    for key, (low, high) in RANGES.items():
        lines.append(f"- `{key}`: `{low:g}` to `{high:g}`")
    lines.extend(
        [
            "",
            "## Best Quick Candidate",
            "",
            f"- sample id: `{best_quick['sample_id']}`",
            f"- target correct: `{best_quick['target_correct']:.3f}`",
            f"- wall loss: `{best_quick['wall_loss']:.3f}`",
            f"- preferred direction: `{best_quick['preferred_direction']}`",
            "",
            "## Best Validated Candidate",
            "",
            f"- sample id: `{best_val['sample_id']}`",
            f"- validation target correct: `{best_val['mean_target_correct']:.3f}`",
            f"- validation std: `{best_val['std_target_correct']:.3f}`",
            f"- validation wall loss: `{best_val['mean_wall_loss']:.3f}`",
            f"- preferred direction: `{best_val['preferred_direction']}`",
            "",
            "## Next Run",
            "",
            "For the real 20-30 minute run, increase quick samples to 150-200 and",
            "validate the top 10. This script is intentionally configured as a",
            "small smoke test first.",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_openfoam_case()
    field_stats = load_openfoam_field_stats()
    samples, quick_rows = run_quick(field_stats)
    validation_rows = run_validation(field_stats, quick_rows, samples)
    validation_summary = aggregate_validation(validation_rows)
    write_csv(quick_rows, OUT_DIR / "v6_quick_search.csv")
    write_csv(validation_rows, OUT_DIR / "v6_top5_validation_replicates.csv")
    write_csv(validation_summary, OUT_DIR / "v6_top5_validation_summary.csv")
    (OUT_DIR / "v6_lhs_samples.json").write_text(json.dumps(samples, indent=2) + "\n", encoding="utf-8")
    plot_results(quick_rows, validation_summary)
    write_readme(quick_rows, validation_summary)
    print((OUT_DIR / "README.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
