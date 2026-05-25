#!/usr/bin/env python3
"""Validate the V6 candidate with the strongest useful spiral contribution."""

from __future__ import annotations

import csv
from pathlib import Path

import validation_v6_posthoc as posthoc
from optimization_v1_surrogate import OUT_DIR as OPT_DIR
from optimization_v1_surrogate import sample_from_summary
from study_common import load_openfoam_field_stats, run_openfoam_case, write_csv


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "optimization_v1" / "balanced_synergy_validation"


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for key, value in list(row.items()):
            try:
                row[key] = float(value)
            except (TypeError, ValueError):
                pass
    return rows


def select_balanced_candidate() -> tuple[dict, dict]:
    validation = read_rows(OPT_DIR / "all_validation_summary.csv")
    synergy = read_rows(OPT_DIR / "all_synergy_checks.csv")
    by_key = {(row["stage"], int(row["sample_id"])): row for row in validation}
    joined = []
    for row in synergy:
        key = (row["stage"], int(row["sample_id"]))
        if key in by_key:
            merged = dict(by_key[key])
            merged.update(row)
            joined.append(merged)
    viable = [
        row
        for row in joined
        if row["mean_target_correct"] >= 0.85
        and row["mean_wall_loss"] <= 0.05
        and row["synergy_score"] > 0.0
    ]
    if not viable:
        raise RuntimeError("No viable balanced candidate found.")
    best = sorted(viable, key=lambda row: (row["synergy_score"], row["mean_target_correct"]), reverse=True)[0]
    validation_row = by_key[(best["stage"], int(best["sample_id"]))]
    return validation_row, best


def write_readme(summary: list[dict], candidate: dict, synergy: dict) -> None:
    rows = {row["scenario"]: row for row in summary}
    lines = [
        "# Balanced Synergy Candidate Validation",
        "",
        "This run validates the best candidate selected by positive spiral synergy",
        "under a useful accuracy constraint, rather than by maximum accuracy alone.",
        "",
        "## Candidate",
        "",
        f"- stage: `{candidate['stage']}`",
        f"- sample id: `{int(candidate['sample_id'])}`",
        f"- optimizer target correct: `{candidate['mean_target_correct']:.3f}`",
        f"- optimizer wall loss: `{candidate['mean_wall_loss']:.3f}`",
        f"- synergy score in screening: `{synergy['synergy_score']:.3f}`",
        f"- spiral DEP on / straight DEP on: `{synergy['spiral_dep_on']:.3f}` / `{synergy['straight_dep_on']:.3f}`",
        f"- voltage: `{candidate['voltage_v']:.2f} V`",
        f"- frequency: `{candidate['frequency_hz'] / 1000:.1f} kHz`",
        f"- flow velocity: `{candidate['velocity_um_s']:.0f} um/s`",
        f"- turns: `{candidate['turns']:.2f}`",
        f"- channel width: `{candidate['channel_width_um']:.1f} um`",
        f"- inlet offset/spread: `{candidate['inlet_offset_ratio']:.3f}` / `{candidate['inlet_spread_ratio']:.3f}`",
        f"- DEP segment: `{candidate['dep_start_fraction']:.3f}` to `{candidate['dep_end_fraction']:.3f}`",
        "",
        "## Held-out Results",
        "",
        f"- nominal held-out target correct: `{rows['nominal_heldout']['mean_target_correct']:.3f}` +/- `{rows['nominal_heldout']['std_target_correct']:.3f}`",
        f"- tolerance-perturbed target correct: `{rows['tolerance_perturbed']['mean_target_correct']:.3f}` +/- `{rows['tolerance_perturbed']['std_target_correct']:.3f}`",
        f"- same-length straight DEP target correct: `{rows['straight_same_length_dep']['mean_target_correct']:.3f}`",
        f"- spiral without DEP target correct: `{rows['spiral_no_dep']['mean_target_correct']:.3f}`",
        f"- spiral DEP with unfocused inlet target correct: `{rows['spiral_dep_unfocused_inlet']['mean_target_correct']:.3f}`",
        "",
        "## Interpretation",
        "",
        "This is a better paper-facing candidate than the max-accuracy design if",
        "we want to argue that the spiral contributes beyond residence time. It",
        "still depends strongly on DEP and inlet focusing, but the straight-channel",
        "control is lower, so the spiral-specific contribution is more defensible.",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    posthoc.OUT_DIR = OUT_DIR
    run_openfoam_case()
    field_stats = load_openfoam_field_stats()
    candidate, synergy = select_balanced_candidate()
    base = sample_from_summary(candidate)

    rows = []
    rows.extend(posthoc.run_case("nominal_heldout", base, field_stats, [1901, 1907, 1913, 1931, 1933, 1949], 350))
    rows.extend(posthoc.run_case("tolerance_perturbed", base, field_stats, list(range(2001, 2013)), 250, tolerance=True))
    rows.extend(posthoc.run_case("straight_same_length_dep", base, field_stats, [2101, 2111, 2113, 2129], 300, geometry="straight"))
    rows.extend(posthoc.run_case("spiral_no_dep", base, field_stats, [2203, 2213, 2221, 2237], 300, dep_enabled=False))
    rows.extend(posthoc.run_case("spiral_dep_unfocused_inlet", base, field_stats, [2309, 2311, 2333, 2339], 300, inlet_control="unfocused"))
    rows.extend(posthoc.run_case("spiral_dep_moderate_inlet", base, field_stats, [2401, 2411, 2417, 2423], 300, inlet_control="moderate"))

    summary = posthoc.summarize_rows(rows)
    write_csv(rows, OUT_DIR / "posthoc_replicates.csv")
    write_csv(summary, OUT_DIR / "posthoc_summary.csv")
    posthoc.plot(rows, summary)
    write_readme(summary, candidate, synergy)
    print((OUT_DIR / "README.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
