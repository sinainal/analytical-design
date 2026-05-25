#!/usr/bin/env python3
"""Surrogate-assisted operating-condition optimization.

The optimizer searches for higher live/dead outlet classification without
including spiral synergy in the objective. Spiral synergy is evaluated only
after candidate selection.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from time import perf_counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor

from design_v0_particle_tracking import SpiralSpec
from study_common import load_openfoam_field_stats, run_openfoam_case, simulate_population, write_csv


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "optimization_v1"

BASE_FEATURES = [
    "log_frequency_hz",
    "voltage_v",
    "velocity_um_s",
    "turns",
    "inner_radius_um",
    "pitch_um",
    "channel_width_um",
    "outlet_split_ratio",
]
ENHANCED_FEATURES = BASE_FEATURES + ["inlet_offset_ratio", "inlet_spread_ratio"]
TOPOLOGY_FEATURES = ENHANCED_FEATURES + ["dep_start_fraction", "dep_end_fraction", "dean_scale", "dep_sign"]

BASE_RANGES = {
    "frequency_hz": (20e3, 5.0e6),
    "voltage_v": (2.0, 24.0),
    "velocity_m_s": (300e-6, 8000e-6),
    "turns": (1.5, 9.0),
    "inner_radius_m": (450e-6, 2200e-6),
    "pitch_m": (80e-6, 450e-6),
    "channel_width_m": (50e-6, 240e-6),
    "outlet_split_ratio": (0.25, 0.75),
}

ENHANCED_RANGES = {
    **BASE_RANGES,
    "inlet_offset_ratio": (-0.75, 0.75),
    "inlet_spread_ratio": (0.12, 0.85),
}
TOPOLOGY_RANGES = {
    **ENHANCED_RANGES,
    "dep_start_fraction": (0.0, 0.75),
    "dep_end_fraction": (0.25, 1.0),
    "dean_scale": (0.0, 1.8),
    "dep_sign": (-1.0, 1.0),
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


def random_candidates(n: int, ranges: dict[str, tuple[float, float]], seed: int) -> list[dict]:
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        rows.append({key: float(rng.uniform(low, high)) for key, (low, high) in ranges.items()})
    return rows


def make_spec(row: dict) -> SpiralSpec:
    return SpiralSpec(
        turns=row["turns"],
        inner_radius_m=row["inner_radius_m"],
        pitch_m=row["pitch_m"],
        channel_width_m=row["channel_width_m"],
        voltage_v=row["voltage_v"],
        inlet_velocity_m_s=row["velocity_m_s"],
    )


def normalized_sample(row: dict) -> dict:
    out = dict(row)
    if "dep_start_fraction" in out or "dep_end_fraction" in out:
        start = float(out.get("dep_start_fraction", 0.0))
        end = float(out.get("dep_end_fraction", 1.0))
        start = float(np.clip(start, 0.0, 0.9))
        end = float(np.clip(end, 0.1, 1.0))
        if end < start + 0.12:
            start, end = max(0.0, min(start, end) - 0.06), min(1.0, max(start, end) + 0.06)
        if end <= start:
            start, end = 0.0, 1.0
        out["dep_start_fraction"] = start
        out["dep_end_fraction"] = end
    if "dep_sign" in out:
        out["dep_sign"] = 1.0 if out["dep_sign"] >= 0 else -1.0
    return out


def feature_row(row: dict, features: list[str]) -> list[float]:
    row = normalized_sample(row)
    values = {
        "log_frequency_hz": np.log10(row["frequency_hz"]),
        "voltage_v": row["voltage_v"],
        "velocity_um_s": row["velocity_m_s"] * 1e6,
        "turns": row["turns"],
        "inner_radius_um": row["inner_radius_m"] * 1e6,
        "pitch_um": row["pitch_m"] * 1e6,
        "channel_width_um": row["channel_width_m"] * 1e6,
        "outlet_split_ratio": row["outlet_split_ratio"],
        "inlet_offset_ratio": row.get("inlet_offset_ratio", 0.0),
        "inlet_spread_ratio": row.get("inlet_spread_ratio", 1.0),
        "dep_start_fraction": row.get("dep_start_fraction", 0.0),
        "dep_end_fraction": row.get("dep_end_fraction", 1.0),
        "dean_scale": row.get("dean_scale", 1.0),
        "dep_sign": row.get("dep_sign", 1.0),
    }
    return [float(values[key]) for key in features]


def score(summary: dict) -> float:
    wall_loss = summary["wall_loss"]
    hard_penalty = 1.0 if wall_loss > 0.20 else 0.0
    return (
        summary["target_correct"]
        - 1.35 * wall_loss
        + 0.0035 * summary["distribution_gap_um"]
        - hard_penalty
    )


def run_sample(
    sample: dict,
    field_stats,
    seed: int,
    particles_per_class: int,
    steps: int,
    stage: str,
    sample_id: int,
) -> dict:
    sample = normalized_sample(sample)
    spec = make_spec(sample)
    _, summary, _ = simulate_population(
        spec,
        field_stats,
        seed=seed,
        particles_per_class=particles_per_class,
        steps=steps,
        frequency_hz=sample["frequency_hz"],
        outlet_split_ratio=sample["outlet_split_ratio"],
        dep_sign=sample.get("dep_sign", 1.0),
        inlet_offset_ratio=sample.get("inlet_offset_ratio", 0.0),
        inlet_spread_ratio=sample.get("inlet_spread_ratio", 1.0),
        dep_start_fraction=sample.get("dep_start_fraction", 0.0),
        dep_end_fraction=sample.get("dep_end_fraction", 1.0),
        dean_scale=sample.get("dean_scale", 1.0),
    )
    summary.update(
        {
            "stage": stage,
            "sample_id": sample_id,
            "inner_radius_um": sample["inner_radius_m"] * 1e6,
            "inlet_offset_ratio": sample.get("inlet_offset_ratio", 0.0),
            "inlet_spread_ratio": sample.get("inlet_spread_ratio", 1.0),
            "dep_start_fraction": sample.get("dep_start_fraction", 0.0),
            "dep_end_fraction": sample.get("dep_end_fraction", 1.0),
            "dean_scale": sample.get("dean_scale", 1.0),
            "dep_sign": sample.get("dep_sign", 1.0),
        }
    )
    summary["optimization_score"] = score(summary)
    return summary


def train_surrogate(samples: list[dict], rows: list[dict], features: list[str]) -> ExtraTreesRegressor:
    x = np.array([feature_row(samples[int(row["sample_id"])], features) for row in rows])
    y = np.array([row["optimization_score"] for row in rows])
    model = ExtraTreesRegressor(
        n_estimators=320,
        random_state=42,
        min_samples_leaf=2,
        max_features=1.0,
        n_jobs=-1,
    )
    model.fit(x, y)
    return model


def write_feature_importance(model: ExtraTreesRegressor, features: list[str], out_dir: Path, prefix: str) -> None:
    importances = model.feature_importances_
    rows = [{"feature": f, "importance": float(v)} for f, v in sorted(zip(features, importances), key=lambda x: x[1], reverse=True)]
    write_csv(rows, out_dir / f"{prefix}_feature_importance.csv")
    plt.figure(figsize=(8, 4.5))
    plt.bar([r["feature"] for r in rows], [r["importance"] for r in rows])
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("ExtraTrees importance")
    plt.tight_layout()
    plt.savefig(out_dir / f"{prefix}_feature_importance.png", dpi=180)
    plt.close()


def select_virtual_candidates(
    model: ExtraTreesRegressor,
    ranges: dict[str, tuple[float, float]],
    features: list[str],
    n_virtual: int,
    n_select: int,
    seed: int,
) -> tuple[list[dict], list[dict]]:
    virtual = random_candidates(n_virtual, ranges, seed)
    x = np.array([feature_row(row, features) for row in virtual])
    pred = model.predict(x)
    for row, value in zip(virtual, pred):
        row["predicted_score"] = float(value)
    ranked = sorted(virtual, key=lambda row: row["predicted_score"], reverse=True)
    selected = []
    for row in ranked:
        # A light diversity rule avoids selecting 25 nearly identical virtual points.
        if len(selected) >= n_select:
            break
        if all(abs(np.log10(row["frequency_hz"]) - np.log10(prev["frequency_hz"])) > 0.015 or abs(row["voltage_v"] - prev["voltage_v"]) > 0.35 for prev in selected):
            selected.append(row)
    return ranked[:200], selected


def aggregate_validation(rows: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["stage"], int(row["sample_id"]))].append(row)
    out = []
    for (stage, sample_id), items in grouped.items():
        first = items[0]
        out.append(
            {
                "stage": stage,
                "sample_id": sample_id,
                "case_id": first["case_id"],
                "mean_target_correct": float(np.mean([r["target_correct"] for r in items])),
                "std_target_correct": float(np.std([r["target_correct"] for r in items], ddof=1)),
                "mean_wall_loss": float(np.mean([r["wall_loss"] for r in items])),
                "mean_gap_um": float(np.mean([r["distribution_gap_um"] for r in items])),
                "mean_score": float(np.mean([r["optimization_score"] for r in items])),
                "preferred_direction": first["preferred_direction"],
                "frequency_hz": first["frequency_hz"],
                "voltage_v": first["voltage_v"],
                "velocity_um_s": first["velocity_um_s"],
                "turns": first["turns"],
                "inner_radius_um": first["inner_radius_um"],
                "pitch_um": first["pitch_um"],
                "channel_width_um": first["channel_width_um"],
                "outlet_split_ratio": first["outlet_split_ratio"],
                "inlet_offset_ratio": first["inlet_offset_ratio"],
                "inlet_spread_ratio": first["inlet_spread_ratio"],
                "dep_start_fraction": first.get("dep_start_fraction", 0.0),
                "dep_end_fraction": first.get("dep_end_fraction", 1.0),
                "dean_scale": first.get("dean_scale", 1.0),
                "dep_sign": first.get("dep_sign", 1.0),
            }
        )
    out.sort(key=lambda row: row["mean_score"], reverse=True)
    return out


def sample_from_summary(row: dict) -> dict:
    return {
        "frequency_hz": row["frequency_hz"],
        "voltage_v": row["voltage_v"],
        "velocity_m_s": row["velocity_um_s"] * 1e-6,
        "turns": row["turns"],
        "inner_radius_m": row["inner_radius_um"] * 1e-6,
        "pitch_m": row["pitch_um"] * 1e-6,
        "channel_width_m": row["channel_width_um"] * 1e-6,
        "outlet_split_ratio": row["outlet_split_ratio"],
        "inlet_offset_ratio": row.get("inlet_offset_ratio", 0.0),
        "inlet_spread_ratio": row.get("inlet_spread_ratio", 1.0),
        "dep_start_fraction": row.get("dep_start_fraction", 0.0),
        "dep_end_fraction": row.get("dep_end_fraction", 1.0),
        "dean_scale": row.get("dean_scale", 1.0),
        "dep_sign": row.get("dep_sign", 1.0),
    }


def synergy_for_candidate(row: dict, field_stats, sample_id: int) -> dict:
    sample = sample_from_summary(row)
    spec = make_spec(sample)
    scenarios = [
        ("spiral_dep_on", "spiral", True, 1.0),
        ("straight_dep_on", "straight", True, 1.0),
        ("spiral_flow_only", "spiral", False, 1.0),
        ("straight_flow_only", "straight", False, 1.0),
    ]
    scenario_rows = []
    for name, geometry, dep_enabled, dep_sign in scenarios:
        scores = []
        losses = []
        for seed in [701, 709]:
            _, summary, _ = simulate_population(
                spec,
                field_stats,
                seed=seed,
                particles_per_class=80,
                steps=220,
                frequency_hz=sample["frequency_hz"],
                outlet_split_ratio=sample["outlet_split_ratio"],
                geometry=geometry,
                dep_enabled=dep_enabled,
                dep_sign=sample.get("dep_sign", dep_sign) * dep_sign,
                inlet_offset_ratio=sample.get("inlet_offset_ratio", 0.0),
                inlet_spread_ratio=sample.get("inlet_spread_ratio", 1.0),
                dep_start_fraction=sample.get("dep_start_fraction", 0.0),
                dep_end_fraction=sample.get("dep_end_fraction", 1.0),
                dean_scale=sample.get("dean_scale", 1.0),
            )
            scores.append(summary["target_correct"])
            losses.append(summary["wall_loss"])
        scenario_rows.append(
            {
                "scenario": name,
                "target_correct": float(np.mean(scores)),
                "wall_loss": float(np.mean(losses)),
            }
        )
    by_name = {r["scenario"]: r for r in scenario_rows}
    spiral_dep = by_name["spiral_dep_on"]["target_correct"]
    straight_dep = by_name["straight_dep_on"]["target_correct"]
    spiral_flow = by_name["spiral_flow_only"]["target_correct"]
    return {
        "stage": row["stage"],
        "sample_id": sample_id,
        "spiral_dep_on": spiral_dep,
        "straight_dep_on": straight_dep,
        "spiral_flow_only": spiral_flow,
        "straight_flow_only": by_name["straight_flow_only"]["target_correct"],
        "spiral_gain": spiral_dep - straight_dep,
        "dep_gain": spiral_dep - spiral_flow,
        "synergy_score": spiral_dep - max(straight_dep, spiral_flow),
        "spiral_wall_loss": by_name["spiral_dep_on"]["wall_loss"],
    }


def plot_search(rows: list[dict], validation: list[dict], out_dir: Path, prefix: str) -> None:
    plt.figure(figsize=(7, 4.6))
    plt.scatter(
        [r["wall_loss"] for r in rows],
        [r["target_correct"] for r in rows],
        c=[r["optimization_score"] for r in rows],
        cmap="viridis",
        s=28,
    )
    plt.axhline(0.8, color="black", linestyle="--", linewidth=1)
    plt.axvline(0.15, color="0.35", linestyle=":", linewidth=1)
    plt.xlabel("Wall loss")
    plt.ylabel("Target correct")
    plt.colorbar(label="Optimization score")
    plt.tight_layout()
    plt.savefig(out_dir / f"{prefix}_correct_vs_wall_loss.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 4.5))
    labels = [f"{r['stage']}:{r['sample_id']}" for r in validation]
    plt.bar(range(len(validation)), [r["mean_target_correct"] for r in validation])
    plt.axhline(0.8, color="black", linestyle="--", linewidth=1)
    plt.xticks(range(len(validation)), labels, rotation=45, ha="right")
    plt.ylabel("Validated target correct")
    plt.tight_layout()
    plt.savefig(out_dir / f"{prefix}_validation_correct.png", dpi=180)
    plt.close()


def plot_best_distribution(best: dict, field_stats, out_dir: Path) -> None:
    sample = sample_from_summary(best)
    spec = make_spec(sample)
    particles, _, _ = simulate_population(
        spec,
        field_stats,
        seed=901,
        particles_per_class=180,
        steps=260,
        frequency_hz=sample["frequency_hz"],
        outlet_split_ratio=sample["outlet_split_ratio"],
        dep_sign=sample.get("dep_sign", 1.0),
        inlet_offset_ratio=sample.get("inlet_offset_ratio", 0.0),
        inlet_spread_ratio=sample.get("inlet_spread_ratio", 1.0),
        dep_start_fraction=sample.get("dep_start_fraction", 0.0),
        dep_end_fraction=sample.get("dep_end_fraction", 1.0),
        dean_scale=sample.get("dean_scale", 1.0),
    )
    write_csv(particles, out_dir / "best_design_particles.csv")
    live = [p["final_lateral_um"] for p in particles if p["class"] == "live"]
    dead = [p["final_lateral_um"] for p in particles if p["class"] == "dead"]
    threshold_um = (-0.5 + sample["outlet_split_ratio"]) * sample["channel_width_m"] * 1e6
    plt.figure(figsize=(7, 4))
    plt.hist(live, bins=28, alpha=0.65, label="live")
    plt.hist(dead, bins=28, alpha=0.65, label="dead")
    plt.axvline(threshold_um, color="black", linestyle="--", linewidth=1, label="outlet split")
    plt.xlabel("Final lateral position (um)")
    plt.ylabel("Cell count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "best_design_distribution.png", dpi=180)
    plt.close()


def run_stage(
    name: str,
    ranges: dict[str, tuple[float, float]],
    features: list[str],
    field_stats,
    lhs_n: int,
    virtual_n: int,
    selected_n: int,
    seed_offset: int,
) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    stage_dir = OUT_DIR / name
    stage_dir.mkdir(parents=True, exist_ok=True)
    start = perf_counter()

    samples = latin_hypercube(lhs_n, ranges, seed=1000 + seed_offset)
    lhs_rows = []
    for i, sample in enumerate(samples):
        lhs_rows.append(run_sample(sample, field_stats, seed=111, particles_per_class=70, steps=220, stage=f"{name}_lhs", sample_id=i))
    lhs_rows.sort(key=lambda r: r["optimization_score"], reverse=True)
    write_csv(lhs_rows, stage_dir / "initial_lhs.csv")

    model = train_surrogate(samples, lhs_rows, features)
    write_feature_importance(model, features, stage_dir, name)

    virtual_top, selected = select_virtual_candidates(model, ranges, features, virtual_n, selected_n, seed=2000 + seed_offset)
    write_csv(virtual_top, stage_dir / "surrogate_virtual_top200.csv")

    selected_rows = []
    selected_base_id = len(samples)
    selected_samples = samples + selected
    for j, sample in enumerate(selected):
        sample_id = selected_base_id + j
        selected_rows.append(run_sample(sample, field_stats, seed=303, particles_per_class=95, steps=260, stage=f"{name}_ml_selected", sample_id=sample_id))
    selected_rows.sort(key=lambda r: r["optimization_score"], reverse=True)
    write_csv(selected_rows, stage_dir / "ml_selected_real_runs.csv")

    candidates = sorted(lhs_rows[:8] + selected_rows[:12], key=lambda r: r["optimization_score"], reverse=True)[:8]
    validation_rows = []
    for candidate in candidates:
        sample = selected_samples[int(candidate["sample_id"])]
        for seed in [401, 409, 419]:
            validation_rows.append(
                run_sample(
                    sample,
                    field_stats,
                    seed=seed,
                    particles_per_class=120,
                    steps=300,
                    stage=name,
                    sample_id=int(candidate["sample_id"]),
                )
            )
    validation_summary = aggregate_validation(validation_rows)
    write_csv(validation_rows, stage_dir / "top_validation_replicates.csv")
    write_csv(validation_summary, stage_dir / "top_validation_summary.csv")

    synergy_rows = []
    for row in validation_summary[:3]:
        synergy_rows.append(synergy_for_candidate(row, field_stats, int(row["sample_id"])))
    write_csv(synergy_rows, stage_dir / "synergy_check_top3.csv")
    plot_search(lhs_rows + selected_rows, validation_summary, stage_dir, name)

    elapsed = perf_counter() - start
    (stage_dir / "stage_runtime_seconds.txt").write_text(f"{elapsed:.2f}\n", encoding="utf-8")
    return samples + selected, lhs_rows, selected_rows, validation_summary, synergy_rows


def write_readme(stage_results: list[dict], best: dict, synergy: dict | None, elapsed: float) -> None:
    lines = [
        "# Optimization V1",
        "",
        "Surrogate-assisted optimization for live/dead separation. The objective",
        "does not include spiral synergy; synergy is checked after selection.",
        "",
        "## Wall Loss",
        "",
        "`wall_loss` is the fraction of cells that hit/stick to the wall before",
        "reaching an outlet. It is penalized because a high-correct design that",
        "loses many cells is not a useful separation device.",
        "",
        "## Best Validated Candidate",
        "",
        f"- stage: `{best['stage']}`",
        f"- sample id: `{best['sample_id']}`",
        f"- target correct: `{best['mean_target_correct']:.3f}`",
        f"- validation std: `{best['std_target_correct']:.3f}`",
        f"- wall loss: `{best['mean_wall_loss']:.3f}`",
        f"- preferred direction: `{best['preferred_direction']}`",
        f"- frequency: `{best['frequency_hz'] / 1000:.1f} kHz`",
        f"- voltage: `{best['voltage_v']:.2f} V`",
        f"- flow velocity: `{best['velocity_um_s']:.0f} um/s`",
        f"- turns: `{best['turns']:.2f}`",
        f"- inner radius: `{best['inner_radius_um']:.1f} um`",
        f"- pitch: `{best['pitch_um']:.1f} um`",
        f"- channel width: `{best['channel_width_um']:.1f} um`",
        f"- outlet split ratio: `{best['outlet_split_ratio']:.3f}`",
        f"- inlet offset ratio: `{best['inlet_offset_ratio']:.3f}`",
        f"- inlet spread ratio: `{best['inlet_spread_ratio']:.3f}`",
        f"- DEP active segment: `{best.get('dep_start_fraction', 0.0):.3f}` to `{best.get('dep_end_fraction', 1.0):.3f}`",
        f"- Dean scale: `{best.get('dean_scale', 1.0):.3f}`",
        f"- DEP sign: `{best.get('dep_sign', 1.0):.0f}`",
    ]
    if synergy:
        lines.extend(
            [
                "",
                "## Spiral Synergy Check",
                "",
                f"- spiral DEP on: `{synergy['spiral_dep_on']:.3f}`",
                f"- same-length straight DEP on: `{synergy['straight_dep_on']:.3f}`",
                f"- spiral flow only: `{synergy['spiral_flow_only']:.3f}`",
                f"- synergy score: `{synergy['synergy_score']:.3f}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "If target correct remains below 0.8, the current physics/topology model",
            "does not yet support the desired separation. If target correct exceeds",
            "0.8 but synergy is weak, the design may be separating because of long",
            "residence time or inlet focusing rather than spiral-specific benefit.",
            "",
            f"Total runtime recorded by the script: `{elapsed / 60:.1f} min`.",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_DIR / "best_design_summary.json").write_text(json.dumps({"best": best, "synergy": synergy}, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    overall_start = perf_counter()
    run_openfoam_case()
    field_stats = load_openfoam_field_stats()

    all_validation = []
    all_synergy = []

    _, _, _, base_validation, base_synergy = run_stage(
        "baseline",
        BASE_RANGES,
        BASE_FEATURES,
        field_stats,
        lhs_n=120,
        virtual_n=12000,
        selected_n=25,
        seed_offset=1,
    )
    all_validation.extend(base_validation)
    all_synergy.extend(base_synergy)

    best = sorted(all_validation, key=lambda r: r["mean_score"], reverse=True)[0]
    best_synergy = next(
        (s for s in all_synergy if s["stage"] == best["stage"] and int(s["sample_id"]) == int(best["sample_id"])),
        None,
    )

    if best["mean_target_correct"] < 0.80:
        _, _, _, enhanced_validation, enhanced_synergy = run_stage(
            "inlet_focusing",
            ENHANCED_RANGES,
            ENHANCED_FEATURES,
            field_stats,
            lhs_n=130,
            virtual_n=15000,
            selected_n=30,
            seed_offset=2,
        )
        all_validation.extend(enhanced_validation)
        all_synergy.extend(enhanced_synergy)
        best = sorted(all_validation, key=lambda r: r["mean_score"], reverse=True)[0]
        best_synergy = next(
            (s for s in all_synergy if s["stage"] == best["stage"] and int(s["sample_id"]) == int(best["sample_id"])),
            None,
        )

    if best["mean_target_correct"] < 0.80 or (best_synergy and best_synergy["synergy_score"] <= 0.0):
        _, _, _, topology_validation, topology_synergy = run_stage(
            "segmented_spiral",
            TOPOLOGY_RANGES,
            TOPOLOGY_FEATURES,
            field_stats,
            lhs_n=150,
            virtual_n=18000,
            selected_n=35,
            seed_offset=3,
        )
        all_validation.extend(topology_validation)
        all_synergy.extend(topology_synergy)
        best = sorted(all_validation, key=lambda r: r["mean_score"], reverse=True)[0]
        best_synergy = next(
            (s for s in all_synergy if s["stage"] == best["stage"] and int(s["sample_id"]) == int(best["sample_id"])),
            None,
        )

    write_csv(all_validation, OUT_DIR / "all_validation_summary.csv")
    write_csv(all_synergy, OUT_DIR / "all_synergy_checks.csv")
    plot_best_distribution(best, field_stats, OUT_DIR)
    elapsed = perf_counter() - overall_start
    write_readme(all_validation, best, best_synergy, elapsed)
    print((OUT_DIR / "README.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
