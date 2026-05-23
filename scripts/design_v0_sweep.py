#!/usr/bin/env python3
"""Run a 12-case reduced-order Design V0 trajectory sweep."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt

from design_v0_particle_tracking import OUT_DIR, SpiralSpec, simulate


SWEEP_DIR = OUT_DIR / "sweep_12"


def case_id(turns: float, voltage: float, velocity: float) -> str:
    return f"turns_{turns:g}_voltage_{voltage:g}_velocity_{velocity * 1e6:.0f}um_s"


def flatten_summary(case: str, summary: dict) -> dict:
    return {
        "case_id": case,
        "turns": summary["overall"]["turns"],
        "voltage_v": summary["overall"]["voltage_v"],
        "inlet_velocity_um_s": summary["overall"]["inlet_velocity_m_s"] * 1e6,
        "correct_fraction": summary["overall"]["correct_fraction"],
        "live_inner_fraction": summary["live"]["inner_fraction"],
        "dead_outer_fraction": summary["dead"]["outer_outlet"] / summary["dead"]["particles"],
        "live_inner_count": summary["live"]["inner_outlet"],
        "dead_outer_count": summary["dead"]["outer_outlet"],
        "live_mean_final_lateral_um": summary["live"]["mean_final_lateral_um"],
        "dead_mean_final_lateral_um": summary["dead"]["mean_final_lateral_um"],
        "live_wall_limited_count": summary["live"]["wall_limited_count"],
        "dead_wall_limited_count": summary["dead"]["wall_limited_count"],
    }


def write_csv(rows: list[dict], path: Path) -> None:
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def plot(rows: list[dict], path: Path) -> None:
    labels = [
        f"{row['turns']:g}T {row['voltage_v']:g}V {row['inlet_velocity_um_s']:.0f}"
        for row in rows
    ]
    values = [row["correct_fraction"] for row in rows]
    colors = ["#2ca25f" if value >= 0.8 else "#f03b20" for value in values]

    plt.figure(figsize=(12, 5))
    plt.bar(range(len(rows)), values, color=colors)
    plt.axhline(0.8, color="black", linestyle="--", linewidth=1, label="V0 target")
    plt.xticks(range(len(rows)), labels, rotation=35, ha="right")
    plt.ylabel("Correct classification fraction")
    plt.ylim(0, 1)
    plt.title("Design V0 reduced-order sweep")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def write_markdown(rows: list[dict], best: dict, path: Path) -> None:
    lines = [
        "# Design V0 12-Case Sweep",
        "",
        "This sweep tests the reduced-order live/dead trajectory model across",
        "turn count, voltage, and inlet velocity. It is a planning/diagnostic",
        "sweep, not a final OpenFOAM field-interpolated particle result.",
        "",
        "## Sweep Grid",
        "",
        "- turns: `3`, `5`",
        "- voltage: `8`, `10`, `12 V`",
        "- inlet velocity: `1000`, `3000 um/s`",
        "- particles per class: `100`",
        "",
        "## Best Case",
        "",
        f"- case: `{best['case_id']}`",
        f"- correct classification: `{best['correct_fraction']:.3f}`",
        f"- live inner fraction: `{best['live_inner_fraction']:.3f}`",
        f"- dead outer fraction: `{best['dead_outer_fraction']:.3f}`",
        "",
        "## Results",
        "",
        "| Case | Correct | Live inner | Dead outer |",
        "|---|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['case_id']}` | {row['correct_fraction']:.3f} | "
            f"{row['live_inner_fraction']:.3f} | {row['dead_outer_fraction']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Cases above `0.8` correct classification are candidates for the next",
            "OpenFOAM field-interpolated trajectory run. Cases below that threshold",
            "still provide useful diagnostics for sensitivity to voltage, residence",
            "time, and flow speed.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    SWEEP_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for turns in [3.0, 5.0]:
        for voltage in [8.0, 10.0, 12.0]:
            for velocity in [1000e-6, 3000e-6]:
                spec = SpiralSpec(turns=turns, voltage_v=voltage, inlet_velocity_m_s=velocity)
                _, summary = simulate(spec, particles_per_class=100, steps=360, seed=7)
                row = flatten_summary(case_id(turns, voltage, velocity), summary)
                rows.append(row)
                (SWEEP_DIR / f"{row['case_id']}.json").write_text(
                    json.dumps(summary, indent=2) + "\n",
                    encoding="utf-8",
                )

    rows.sort(key=lambda row: row["correct_fraction"], reverse=True)
    best = rows[0]
    write_csv(rows, SWEEP_DIR / "sweep_results.csv")
    plot(rows, SWEEP_DIR / "sweep_correct_fraction.png")
    write_markdown(rows, best, SWEEP_DIR / "README.md")
    print((SWEEP_DIR / "README.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
