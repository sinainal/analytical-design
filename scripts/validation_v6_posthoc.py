#!/usr/bin/env python3
"""Post-hoc robustness checks for the V6 optimized design."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from optimization_v1_surrogate import OUT_DIR as OPT_DIR
from optimization_v1_surrogate import make_spec, sample_from_summary
from study_common import load_openfoam_field_stats, run_openfoam_case, simulate_population, write_csv


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "optimization_v1" / "posthoc_validation"


def metric_from_particles(particles: list[dict], summary: dict) -> dict:
    live = [p for p in particles if p["class"] == "live"]
    dead = [p for p in particles if p["class"] == "dead"]
    live_inner = sum(p["outlet"] == "inner" for p in live)
    live_outer = sum(p["outlet"] == "outer" for p in live)
    dead_inner = sum(p["outlet"] == "inner" for p in dead)
    dead_outer = sum(p["outlet"] == "outer" for p in dead)
    live_lost = sum(p["outlet"] == "lost" for p in live)
    dead_lost = sum(p["outlet"] == "lost" for p in dead)
    preferred = summary["preferred_direction"]
    if preferred.startswith("B_"):
        live_target = live_outer
        dead_target = dead_inner
        live_outlet_total = live_outer + dead_outer
        dead_outlet_total = dead_inner + live_inner
    else:
        live_target = live_inner
        dead_target = dead_outer
        live_outlet_total = live_inner + dead_inner
        dead_outlet_total = dead_outer + live_outer
    return {
        "target_correct": summary["target_correct"],
        "wall_loss": summary["wall_loss"],
        "distribution_gap_um": summary["distribution_gap_um"],
        "preferred_direction": preferred,
        "live_recovery": live_target / max(1, len(live)),
        "dead_removal": dead_target / max(1, len(dead)),
        "live_outlet_purity": live_target / max(1, live_outlet_total),
        "dead_outlet_purity": dead_target / max(1, dead_outlet_total),
        "live_wall_loss": live_lost / max(1, len(live)),
        "dead_wall_loss": dead_lost / max(1, len(dead)),
    }


def perturb_sample(base: dict, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    sample = dict(base)
    sample["voltage_v"] *= float(rng.normal(1.0, 0.05))
    sample["velocity_m_s"] *= float(rng.normal(1.0, 0.10))
    sample["channel_width_m"] *= float(rng.normal(1.0, 0.04))
    sample["pitch_m"] *= float(rng.normal(1.0, 0.04))
    sample["inlet_offset_ratio"] = float(np.clip(sample["inlet_offset_ratio"] + rng.normal(0.0, 0.055), -0.85, 0.85))
    sample["inlet_spread_ratio"] = float(np.clip(sample["inlet_spread_ratio"] * rng.normal(1.0, 0.20), 0.08, 0.90))
    sample["dep_start_fraction"] = float(np.clip(sample["dep_start_fraction"] + rng.normal(0.0, 0.035), 0.0, 0.85))
    sample["dep_end_fraction"] = float(np.clip(sample["dep_end_fraction"] + rng.normal(0.0, 0.035), 0.15, 1.0))
    if sample["dep_end_fraction"] <= sample["dep_start_fraction"] + 0.12:
        sample["dep_end_fraction"] = min(1.0, sample["dep_start_fraction"] + 0.12)
    return sample


def run_case(
    name: str,
    base: dict,
    field_stats,
    seeds: list[int],
    particles_per_class: int,
    geometry: str = "spiral",
    dep_enabled: bool = True,
    inlet_control: str = "optimized",
    tolerance: bool = False,
) -> list[dict]:
    rows = []
    for i, seed in enumerate(seeds):
        sample = perturb_sample(base, seed + 10_000) if tolerance else dict(base)
        if inlet_control == "unfocused":
            sample["inlet_offset_ratio"] = 0.0
            sample["inlet_spread_ratio"] = 1.0
        elif inlet_control == "moderate":
            sample["inlet_offset_ratio"] = -0.35
            sample["inlet_spread_ratio"] = 0.45
        spec = make_spec(sample)
        particles, summary, _ = simulate_population(
            spec,
            field_stats,
            seed=seed,
            particles_per_class=particles_per_class,
            steps=340,
            frequency_hz=sample["frequency_hz"],
            outlet_split_ratio=sample["outlet_split_ratio"],
            geometry=geometry,
            dep_enabled=dep_enabled,
            dep_sign=sample.get("dep_sign", 1.0),
            inlet_offset_ratio=sample.get("inlet_offset_ratio", 0.0),
            inlet_spread_ratio=sample.get("inlet_spread_ratio", 1.0),
            dep_start_fraction=sample.get("dep_start_fraction", 0.0),
            dep_end_fraction=sample.get("dep_end_fraction", 1.0),
            dean_scale=sample.get("dean_scale", 1.0),
        )
        row = {
            "scenario": name,
            "replicate": i,
            "seed": seed,
            "geometry": geometry,
            "dep_enabled": dep_enabled,
            "inlet_control": inlet_control,
            "tolerance": tolerance,
        }
        row.update(metric_from_particles(particles, summary))
        rows.append(row)
    return rows


def summarize_rows(rows: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["scenario"]].append(row)
    out = []
    for scenario, items in grouped.items():
        out.append(
            {
                "scenario": scenario,
                "n": len(items),
                "mean_target_correct": float(np.mean([r["target_correct"] for r in items])),
                "std_target_correct": float(np.std([r["target_correct"] for r in items], ddof=1)) if len(items) > 1 else 0.0,
                "min_target_correct": float(np.min([r["target_correct"] for r in items])),
                "mean_wall_loss": float(np.mean([r["wall_loss"] for r in items])),
                "mean_live_recovery": float(np.mean([r["live_recovery"] for r in items])),
                "mean_dead_removal": float(np.mean([r["dead_removal"] for r in items])),
                "mean_live_outlet_purity": float(np.mean([r["live_outlet_purity"] for r in items])),
                "mean_dead_outlet_purity": float(np.mean([r["dead_outlet_purity"] for r in items])),
            }
        )
    return sorted(out, key=lambda row: row["mean_target_correct"], reverse=True)


def plot(rows: list[dict], summary: list[dict]) -> None:
    scenarios = [r["scenario"] for r in summary]
    values = [[r["target_correct"] for r in rows if r["scenario"] == scenario] for scenario in scenarios]
    plt.figure(figsize=(9, 4.8))
    plt.boxplot(values, labels=scenarios, showmeans=True)
    plt.axhline(0.8, color="black", linestyle="--", linewidth=1)
    plt.ylabel("Target correct")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "posthoc_target_correct_boxplot.png", dpi=180)
    plt.close()

    plt.figure(figsize=(9, 4.8))
    x = np.arange(len(scenarios))
    plt.bar(x - 0.2, [r["mean_live_recovery"] for r in summary], width=0.2, label="live recovery")
    plt.bar(x, [r["mean_dead_removal"] for r in summary], width=0.2, label="dead removal")
    plt.bar(x + 0.2, [1.0 - r["mean_wall_loss"] for r in summary], width=0.2, label="not lost")
    plt.xticks(x, scenarios, rotation=30, ha="right")
    plt.ylim(0, 1.05)
    plt.ylabel("Fraction")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "posthoc_recovery_loss_bars.png", dpi=180)
    plt.close()


def write_readme(summary: list[dict], best: dict) -> None:
    row_by_name = {row["scenario"]: row for row in summary}
    nominal = row_by_name["nominal_heldout"]
    straight = row_by_name["straight_same_length_dep"]
    no_dep = row_by_name["spiral_no_dep"]
    tolerance = row_by_name["tolerance_perturbed"]
    unfocused = row_by_name["spiral_dep_unfocused_inlet"]
    lines = [
        "# V6 Post-hoc Validation",
        "",
        "These checks deliberately try to break the optimized design. They are",
        "not part of the surrogate objective and use held-out random seeds.",
        "",
        "## Optimized Candidate",
        "",
        f"- source stage: `{best['stage']}`",
        f"- target correct in optimizer validation: `{best['mean_target_correct']:.3f}`",
        f"- voltage: `{best['voltage_v']:.2f} V`",
        f"- frequency: `{best['frequency_hz'] / 1000:.1f} kHz`",
        f"- flow velocity: `{best['velocity_um_s']:.0f} um/s`",
        f"- turns: `{best['turns']:.2f}`",
        f"- channel width: `{best['channel_width_um']:.1f} um`",
        f"- inlet offset/spread: `{best['inlet_offset_ratio']:.3f}` / `{best['inlet_spread_ratio']:.3f}`",
        f"- DEP segment: `{best['dep_start_fraction']:.3f}` to `{best['dep_end_fraction']:.3f}`",
        "",
        "## Key Results",
        "",
        f"- nominal held-out target correct: `{nominal['mean_target_correct']:.3f}` +/- `{nominal['std_target_correct']:.3f}`",
        f"- tolerance-perturbed target correct: `{tolerance['mean_target_correct']:.3f}` +/- `{tolerance['std_target_correct']:.3f}`",
        f"- same-length straight DEP target correct: `{straight['mean_target_correct']:.3f}`",
        f"- spiral without DEP target correct: `{no_dep['mean_target_correct']:.3f}`",
        f"- spiral DEP with unfocused inlet target correct: `{unfocused['mean_target_correct']:.3f}`",
        "",
        "## Interpretation",
        "",
        "The design passes the >0.8 target under the nominal reduced-order model.",
        "However, the same-length straight DEP control is also high, so the spiral",
        "is not yet the dominant mechanism. The current honest claim is: segmented",
        "DEP plus focused inlet gives strong separation, while the spiral gives a",
        "measurable but secondary improvement. This should be strengthened in the",
        "next design version by optimizing spiral-specific geometry or by reporting",
        "the spiral as a compact residence-time and Dean-flow aid rather than the",
        "sole separator.",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_openfoam_case()
    field_stats = load_openfoam_field_stats()
    data = json.loads((OPT_DIR / "best_design_summary.json").read_text(encoding="utf-8"))
    best = data["best"]
    base = sample_from_summary(best)

    rows = []
    rows.extend(run_case("nominal_heldout", base, field_stats, [901, 907, 911, 919, 929, 937], 350))
    rows.extend(run_case("tolerance_perturbed", base, field_stats, list(range(1001, 1013)), 250, tolerance=True))
    rows.extend(run_case("straight_same_length_dep", base, field_stats, [1101, 1109, 1117, 1123], 300, geometry="straight"))
    rows.extend(run_case("spiral_no_dep", base, field_stats, [1201, 1213, 1223, 1231], 300, dep_enabled=False))
    rows.extend(run_case("spiral_dep_unfocused_inlet", base, field_stats, [1301, 1303, 1307, 1319], 300, inlet_control="unfocused"))
    rows.extend(run_case("spiral_dep_moderate_inlet", base, field_stats, [1409, 1423, 1427, 1429], 300, inlet_control="moderate"))

    summary = summarize_rows(rows)
    write_csv(rows, OUT_DIR / "posthoc_replicates.csv")
    write_csv(summary, OUT_DIR / "posthoc_summary.csv")
    plot(rows, summary)
    write_readme(summary, best)
    print((OUT_DIR / "README.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
