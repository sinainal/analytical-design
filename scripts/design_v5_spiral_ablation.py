#!/usr/bin/env python3
"""Design V5 spiral and DEP ablation study."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from design_v0_particle_tracking import SpiralSpec
from study_common import load_openfoam_field_stats, run_openfoam_case, simulate_population, write_csv


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "openfoam_design_v5" / "spiral_ablation"

SEEDS = [31, 37, 41]
FREQUENCY_HZ = 455_326.0
OUTLET_SPLIT = 0.45

CONDITIONS = [
    ("spiral_flow_only", "spiral", False, 1.0),
    ("spiral_dep_on", "spiral", True, 1.0),
    ("straight_flow_only", "straight", False, 1.0),
    ("straight_dep_on", "straight", True, 1.0),
    ("spiral_dep_reversed", "spiral", True, -1.0),
]


def aggregate(rows: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["condition"]].append(row)
    out = []
    for condition, items in grouped.items():
        first = items[0]
        out.append(
            {
                "condition": condition,
                "geometry": first["geometry"],
                "dep_enabled": first["dep_enabled"],
                "dep_sign": first["dep_sign"],
                "mean_target_correct": float(np.mean([x["target_correct"] for x in items])),
                "std_target_correct": float(np.std([x["target_correct"] for x in items], ddof=1)),
                "mean_correct_A": float(np.mean([x["correct_A_live_inner_dead_outer"] for x in items])),
                "mean_correct_B": float(np.mean([x["correct_B_live_outer_dead_inner"] for x in items])),
                "mean_wall_loss": float(np.mean([x["wall_loss"] for x in items])),
                "mean_distribution_gap_um": float(np.mean([x["distribution_gap_um"] for x in items])),
            }
        )
    out.sort(key=lambda row: row["mean_target_correct"], reverse=True)
    return out


def plot_bars(summary: list[dict]) -> None:
    labels = [row["condition"].replace("_", "\n") for row in summary]
    values = [row["mean_target_correct"] for row in summary]
    errors = [row["std_target_correct"] for row in summary]
    plt.figure(figsize=(8, 4.5))
    plt.bar(range(len(summary)), values, yerr=errors, capsize=3)
    plt.axhline(0.5, color="black", linestyle="--", linewidth=1, label="random baseline")
    plt.ylabel("Target correct")
    plt.xticks(range(len(summary)), labels)
    plt.ylim(0.25, 0.75)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "ablation_target_correct.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 4.5))
    plt.bar(range(len(summary)), [row["mean_distribution_gap_um"] for row in summary])
    plt.ylabel("Live/dead final lateral mean gap (um)")
    plt.xticks(range(len(summary)), labels)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "ablation_distribution_gap.png", dpi=180)
    plt.close()


def write_readme(summary: list[dict]) -> None:
    by_name = {row["condition"]: row for row in summary}
    spiral_dep = by_name["spiral_dep_on"]["mean_target_correct"]
    straight_dep = by_name["straight_dep_on"]["mean_target_correct"]
    spiral_flow = by_name["spiral_flow_only"]["mean_target_correct"]
    straight_flow = by_name["straight_flow_only"]["mean_target_correct"]
    dep_gain = spiral_dep - spiral_flow
    spiral_gain = spiral_dep - straight_dep
    length_control_gain = straight_dep - straight_flow
    synergy_score = spiral_dep - max(straight_dep, spiral_flow)
    lines = [
        "# Design V5 Spiral/DEP Ablation",
        "",
        "This study asks whether the spiral contributes more than residence time.",
        "The straight-channel cases use the same path length in the reduced model.",
        "",
        "## Main Scores",
        "",
        f"- spiral DEP on: `{spiral_dep:.3f}`",
        f"- straight DEP on: `{straight_dep:.3f}`",
        f"- spiral flow only: `{spiral_flow:.3f}`",
        f"- straight flow only: `{straight_flow:.3f}`",
        f"- DEP gain in spiral: `{dep_gain:.3f}`",
        f"- spiral gain over same-length straight DEP: `{spiral_gain:.3f}`",
        f"- same-length DEP gain: `{length_control_gain:.3f}`",
        f"- synergy score: `{synergy_score:.3f}`",
        "",
        "## Interpretation Rule",
        "",
        "`synergy_score > 0` supports spiral+DEP synergy. If it is near zero or",
        "negative, the current spiral is not yet doing more than a straight",
        "same-length DEP channel.",
        "",
        "## Summary Table",
        "",
        "| Condition | Target correct | Correct A | Correct B | Wall loss | Gap um |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| `{row['condition']}` | {row['mean_target_correct']:.3f} | "
            f"{row['mean_correct_A']:.3f} | {row['mean_correct_B']:.3f} | "
            f"{row['mean_wall_loss']:.3f} | {row['mean_distribution_gap_um']:.3f} |"
        )
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_openfoam_case()
    field_stats = load_openfoam_field_stats()
    spec = SpiralSpec(turns=3.5, voltage_v=7.0, inlet_velocity_m_s=2600e-6)
    rows = []
    for condition, geometry, dep_enabled, dep_sign in CONDITIONS:
        for seed in SEEDS:
            _, summary, _ = simulate_population(
                spec,
                field_stats,
                seed=seed,
                particles_per_class=80,
                steps=240,
                frequency_hz=FREQUENCY_HZ,
                outlet_split_ratio=OUTLET_SPLIT,
                geometry=geometry,
                dep_enabled=dep_enabled,
                dep_sign=dep_sign,
            )
            summary["condition"] = condition
            rows.append(summary)
    summary = aggregate(rows)
    write_csv(rows, OUT_DIR / "v5_ablation_replicates.csv")
    write_csv(summary, OUT_DIR / "v5_ablation_summary.csv")
    plot_bars(summary)
    write_readme(summary)
    print((OUT_DIR / "README.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
