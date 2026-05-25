#!/usr/bin/env python3
"""Design V8 shape-family ML optimization and professional figures.

V8 asks a stricter question than V6/V7:

    Which short, manufacturable geometry gives the best separation?

The script uses a reduced-order particle model for the expensive evaluations
and an ExtraTrees surrogate to triage thousands of virtual candidates. The ML
model proposes candidates; all reported finalists are re-simulated with held-out
random seeds.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor

from design_v1_doe import write_pvd, write_vtp_frame, write_vtp_polyline
from design_v7_geometry_feasibility import (
    CP_WATER_J_KG_K,
    MU_PA_S,
    RHO_WATER_KG_M3,
    active_fraction,
    performance_metrics,
    read_balanced_v6,
)
from optimization_v1_surrogate import make_spec
from study_common import (
    CHANNEL_HEIGHT_M,
    MEDIUM_SIGMA_S_M,
    load_openfoam_field_stats,
    run_openfoam_case,
    run_particle,
    sample_cell,
    spiral_length,
    summarize,
    write_csv,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "design_v8_shape_ml_optimization"


@dataclass(frozen=True)
class ShapeFamily:
    name: str
    visual_shape: str
    solver_geometry: str
    turns_range: tuple[float, float]
    inner_radius_range_um: tuple[float, float]
    pitch_range_um: tuple[float, float]
    width_range_um: tuple[float, float]
    length_factor_range: tuple[float, float]
    dean_scale_range: tuple[float, float]
    field_gain_range: tuple[float, float]
    dep_start_range: tuple[float, float]
    dep_end_range: tuple[float, float]
    footprint_factor: float
    note: str


FAMILIES = [
    ShapeFamily(
        "asymmetric_c_spiral",
        "asymmetric_spiral",
        "spiral",
        (2.2, 4.4),
        (500, 950),
        (170, 310),
        (130, 220),
        (0.50, 0.82),
        (0.70, 1.25),
        (1.05, 1.40),
        (0.25, 0.58),
        (0.72, 0.98),
        0.78,
        "C/spiral hybrid with asymmetric curvature and segmented electrodes.",
    ),
    ShapeFamily(
        "pinched_step_spiral",
        "pinched_spiral",
        "spiral",
        (3.0, 5.8),
        (520, 980),
        (150, 280),
        (125, 210),
        (0.58, 0.90),
        (0.75, 1.35),
        (1.15, 1.55),
        (0.42, 0.70),
        (0.78, 0.99),
        0.90,
        "Spiral with late high-gradient electrode zone represented by field gain.",
    ),
    ShapeFamily(
        "compact_c_arc_facing",
        "c_arc",
        "spiral",
        (0.9, 2.1),
        (650, 1250),
        (180, 380),
        (135, 235),
        (0.55, 0.88),
        (0.25, 0.65),
        (1.20, 1.70),
        (0.12, 0.45),
        (0.65, 0.98),
        0.55,
        "Short C-shaped/facing-electrode-like DEP path.",
    ),
    ShapeFamily(
        "serpentine_stepwise",
        "serpentine",
        "straight",
        (2.6, 5.8),
        (500, 1050),
        (140, 280),
        (135, 240),
        (0.52, 0.90),
        (0.00, 0.18),
        (1.05, 1.45),
        (0.35, 0.68),
        (0.76, 0.99),
        0.42,
        "Packed serpentine control with segmented DEP but no spiral Dean term.",
    ),
    ShapeFamily(
        "wide_low_heat_asymmetric",
        "asymmetric_spiral",
        "spiral",
        (2.8, 5.6),
        (700, 1300),
        (220, 390),
        (200, 285),
        (0.60, 0.92),
        (0.45, 0.95),
        (0.95, 1.25),
        (0.42, 0.72),
        (0.78, 0.99),
        0.92,
        "Wider lower-field asymmetric spiral for thermal feasibility.",
    ),
]


def rng_uniform(rng: np.random.Generator, bounds: tuple[float, float]) -> float:
    return float(rng.uniform(bounds[0], bounds[1]))


def sample_candidate(family: ShapeFamily, base: dict, rng: np.random.Generator) -> dict:
    start = rng_uniform(rng, family.dep_start_range)
    end = rng_uniform(rng, family.dep_end_range)
    if end <= start + 0.15:
        end = min(1.0, start + 0.15)
    return {
        "family": family.name,
        "visual_shape": family.visual_shape,
        "solver_geometry": family.solver_geometry,
        "frequency_hz": float(np.clip(base["frequency_hz"] * rng.uniform(0.65, 1.45), 120e3, 4.8e6)),
        "voltage_v": float(rng.uniform(12.0, 24.0)),
        "velocity_m_s": float(rng.uniform(1000e-6, 5200e-6)),
        "turns": rng_uniform(rng, family.turns_range),
        "inner_radius_m": rng_uniform(rng, family.inner_radius_range_um) * 1e-6,
        "pitch_m": rng_uniform(rng, family.pitch_range_um) * 1e-6,
        "channel_width_m": rng_uniform(rng, family.width_range_um) * 1e-6,
        "outlet_split_ratio": float(rng.uniform(0.28, 0.58)),
        "inlet_offset_ratio": float(rng.uniform(-0.80, -0.30)),
        "inlet_spread_ratio": float(rng.uniform(0.16, 0.50)),
        "dep_start_fraction": start,
        "dep_end_fraction": end,
        "dep_sign": -1.0,
        "dean_scale": rng_uniform(rng, family.dean_scale_range),
        "field_gain": rng_uniform(rng, family.field_gain_range),
        "length_factor": rng_uniform(rng, family.length_factor_range),
        "footprint_factor": family.footprint_factor,
        "note": family.note,
    }


def sample_to_spec(sample: dict, effective_voltage: bool = True):
    row = dict(sample)
    if effective_voltage:
        row["voltage_v"] = sample["voltage_v"] * sample.get("field_gain", 1.0)
    return make_spec(row)


def candidate_length(sample: dict) -> float:
    return spiral_length(sample_to_spec(sample, effective_voltage=False)) * sample["length_factor"]


def feasibility(sample: dict, length_m: float) -> dict:
    width = sample["channel_width_m"]
    height = CHANNEL_HEIGHT_M
    velocity = sample["velocity_m_s"]
    flow_m3_s = velocity * width * height
    aspect = min(height, width) / max(height, width)
    correction = max(0.12, 1.0 - 0.63 * aspect)
    pressure_pa = 12.0 * MU_PA_S * length_m * flow_m3_s / (width * height**3 * correction)
    hydraulic_diameter = 2.0 * width * height / (width + height)
    reynolds = RHO_WATER_KG_M3 * velocity * hydraulic_diameter / MU_PA_S
    effective_field = sample["voltage_v"] * sample["field_gain"] / width
    active_power_w = MEDIUM_SIGMA_S_M * effective_field**2 * length_m * width * height * active_fraction(sample)
    residence_s = length_m / max(1e-12, velocity)
    volume_m3 = length_m * width * height
    adiabatic_delta_c = active_power_w * residence_s / max(1e-18, RHO_WATER_KG_M3 * CP_WATER_J_KG_K * volume_m3)
    r_outer = sample["inner_radius_m"] + sample["pitch_m"] * sample["turns"] + 0.5 * width
    footprint_m2 = sample["footprint_factor"] * math.pi * r_outer * r_outer
    steady_delta_c = active_power_w * 1.0e-3 / max(1e-18, 0.20 * footprint_m2)
    risk = "low"
    if active_power_w * 1000 > 25.0 or steady_delta_c > 10.0:
        risk = "high"
    elif active_power_w * 1000 > 10.0 or steady_delta_c > 5.0:
        risk = "moderate"
    return {
        "length_mm": length_m * 1e3,
        "footprint_mm2": footprint_m2 * 1e6,
        "residence_s": residence_s,
        "flow_uL_min": flow_m3_s * 1e9 * 60.0,
        "pressure_drop_kPa": pressure_pa / 1000.0,
        "reynolds": reynolds,
        "effective_field_kV_m": effective_field / 1000.0,
        "active_joule_power_mW": active_power_w * 1000.0,
        "adiabatic_delta_c_proxy": adiabatic_delta_c,
        "steady_substrate_delta_c_proxy": steady_delta_c,
        "thermal_risk": risk,
    }


def simulate_candidate(
    sample: dict,
    field_stats,
    seed: int,
    particles_per_class: int,
    steps: int,
    keep_paths: bool = False,
    geometry_override: str | None = None,
    dep_enabled: bool = True,
    inlet_override: tuple[float, float] | None = None,
) -> tuple[list[dict], dict, list[dict], float]:
    rng = np.random.default_rng(seed)
    spec = sample_to_spec(sample, effective_voltage=True)
    length_m = candidate_length(sample)
    results = []
    paths = []
    pid = 0
    inlet_offset = sample["inlet_offset_ratio"]
    inlet_spread = sample["inlet_spread_ratio"]
    if inlet_override is not None:
        inlet_offset, inlet_spread = inlet_override
    geometry = geometry_override or sample["solver_geometry"]
    for name in ["live", "dead"]:
        for _ in range(particles_per_class):
            cell = sample_cell(
                rng,
                name,
                spec.channel_width_m,
                sample["frequency_hz"],
                inlet_offset_ratio=inlet_offset,
                inlet_spread_ratio=inlet_spread,
            )
            result, path = run_particle(
                spec,
                cell,
                field_stats,
                rng,
                pid,
                steps,
                sample["frequency_hz"],
                sample["outlet_split_ratio"],
                geometry=geometry,
                dep_enabled=dep_enabled,
                dep_sign=sample["dep_sign"],
                keep_path=keep_paths,
                length_m=length_m,
                dep_start_fraction=sample["dep_start_fraction"],
                dep_end_fraction=sample["dep_end_fraction"],
                dean_scale=sample["dean_scale"],
            )
            results.append(result)
            paths.extend(path)
            pid += 1
    summary = summarize(results, spec, seed, sample["frequency_hz"], sample["outlet_split_ratio"], geometry, dep_enabled, sample["dep_sign"])
    return results, summary, paths, length_m


def row_from_run(sample: dict, particles: list[dict], summary: dict, length_m: float, sample_id: int, stage: str, seed: int) -> dict:
    row = {
        "stage": stage,
        "sample_id": sample_id,
        "seed": seed,
        "family": sample["family"],
        "visual_shape": sample["visual_shape"],
        "frequency_hz": sample["frequency_hz"],
        "voltage_v": sample["voltage_v"],
        "field_gain": sample["field_gain"],
        "effective_voltage_v": sample["voltage_v"] * sample["field_gain"],
        "velocity_um_s": sample["velocity_m_s"] * 1e6,
        "turns": sample["turns"],
        "inner_radius_um": sample["inner_radius_m"] * 1e6,
        "pitch_um": sample["pitch_m"] * 1e6,
        "channel_width_um": sample["channel_width_m"] * 1e6,
        "outlet_split_ratio": sample["outlet_split_ratio"],
        "inlet_offset_ratio": sample["inlet_offset_ratio"],
        "inlet_spread_ratio": sample["inlet_spread_ratio"],
        "dep_start_fraction": sample["dep_start_fraction"],
        "dep_end_fraction": sample["dep_end_fraction"],
        "dean_scale": sample["dean_scale"],
        "length_factor": sample["length_factor"],
    }
    row.update(performance_metrics(particles, summary))
    row.update(feasibility(sample, length_m))
    row["short_channel_score"] = (row["target_correct"] - 0.50) / max(1e-6, row["length_mm"])
    row["v8_score"] = (
        row["target_correct"]
        + 10.0 * row["short_channel_score"]
        - 1.05 * row["wall_loss"]
        - 0.0010 * max(0.0, row["length_mm"] - 45.0)
        - 0.0035 * max(0.0, row["active_joule_power_mW"] - 9.0)
        - {"low": 0.0, "moderate": 0.05, "high": 0.18}[row["thermal_risk"]]
    )
    return row


FEATURES = [
    "family_id",
    "log_frequency_hz",
    "voltage_v",
    "field_gain",
    "velocity_um_s",
    "turns",
    "inner_radius_um",
    "pitch_um",
    "channel_width_um",
    "outlet_split_ratio",
    "inlet_offset_ratio",
    "inlet_spread_ratio",
    "dep_start_fraction",
    "dep_end_fraction",
    "dean_scale",
    "length_factor",
]


def feature_row(sample: dict) -> list[float]:
    fam_id = {family.name: i for i, family in enumerate(FAMILIES)}[sample["family"]]
    return [
        fam_id,
        math.log10(sample["frequency_hz"]),
        sample["voltage_v"],
        sample["field_gain"],
        sample["velocity_m_s"] * 1e6,
        sample["turns"],
        sample["inner_radius_m"] * 1e6,
        sample["pitch_m"] * 1e6,
        sample["channel_width_m"] * 1e6,
        sample["outlet_split_ratio"],
        sample["inlet_offset_ratio"],
        sample["inlet_spread_ratio"],
        sample["dep_start_fraction"],
        sample["dep_end_fraction"],
        sample["dean_scale"],
        sample["length_factor"],
    ]


def train_ml(samples: list[dict], rows: list[dict]) -> ExtraTreesRegressor:
    x = np.array([feature_row(samples[int(row["sample_id"])]) for row in rows])
    y = np.array([row["v8_score"] for row in rows])
    model = ExtraTreesRegressor(n_estimators=420, random_state=88, min_samples_leaf=2, n_jobs=-1)
    model.fit(x, y)
    return model


def write_feature_importance(model: ExtraTreesRegressor) -> None:
    rows = [
        {"feature": name, "importance": float(value)}
        for name, value in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: x[1], reverse=True)
    ]
    write_csv(rows, OUT_DIR / "v8_ml_feature_importance.csv")
    plt.figure(figsize=(7.2, 4.2))
    plt.barh([r["feature"] for r in rows[::-1]], [r["importance"] for r in rows[::-1]], color="#2a6f97")
    plt.xlabel("ExtraTrees feature importance")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "v8_ml_feature_importance.png", dpi=220)
    plt.close()


def generate_screen(field_stats, base: dict) -> tuple[list[dict], list[dict], ExtraTreesRegressor]:
    rng = np.random.default_rng(8801)
    samples = []
    for family in FAMILIES:
        for _ in range(38):
            samples.append(sample_candidate(family, base, rng))
    rows = []
    for i, sample in enumerate(samples):
        particles, summary, _, length_m = simulate_candidate(sample, field_stats, seed=10_000 + i, particles_per_class=55, steps=210)
        rows.append(row_from_run(sample, particles, summary, length_m, i, "lhs_real", 10_000 + i))
    model = train_ml(samples, rows)
    write_feature_importance(model)

    virtual = []
    for family in FAMILIES:
        for _ in range(2200):
            virtual.append(sample_candidate(family, base, rng))
    pred = model.predict(np.array([feature_row(s) for s in virtual]))
    for s, p in zip(virtual, pred):
        s["predicted_v8_score"] = float(p)
    selected = []
    for sample in sorted(virtual, key=lambda s: s["predicted_v8_score"], reverse=True):
        if len(selected) >= 30:
            break
        if sum(1 for s in selected if s["family"] == sample["family"]) >= 8:
            continue
        selected.append(sample)
    offset = len(samples)
    for j, sample in enumerate(selected):
        sample_id = offset + j
        samples.append(sample)
        particles, summary, _, length_m = simulate_candidate(sample, field_stats, seed=20_000 + j, particles_per_class=90, steps=260)
        rows.append(row_from_run(sample, particles, summary, length_m, sample_id, "ml_selected_real", 20_000 + j))
    return samples, rows, model


def aggregate(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, int], list[dict]] = {}
    for row in rows:
        grouped.setdefault((row["family"], int(row["sample_id"])), []).append(row)
    out = []
    for (family, sample_id), items in grouped.items():
        first = items[0]
        row = {
            "family": family,
            "sample_id": sample_id,
            "mean_target_correct": float(np.mean([r["target_correct"] for r in items])),
            "std_target_correct": float(np.std([r["target_correct"] for r in items], ddof=1)) if len(items) > 1 else 0.0,
            "mean_wall_loss": float(np.mean([r["wall_loss"] for r in items])),
            "mean_live_recovery": float(np.mean([r["live_recovery"] for r in items])),
            "mean_dead_removal": float(np.mean([r["dead_removal"] for r in items])),
            "mean_live_outlet_purity": float(np.mean([r["live_outlet_purity"] for r in items])),
            "mean_dead_outlet_purity": float(np.mean([r["dead_outlet_purity"] for r in items])),
            "length_mm": first["length_mm"],
            "residence_s": first["residence_s"],
            "pressure_drop_kPa": first["pressure_drop_kPa"],
            "active_joule_power_mW": first["active_joule_power_mW"],
            "steady_substrate_delta_c_proxy": first["steady_substrate_delta_c_proxy"],
            "thermal_risk": first["thermal_risk"],
            "short_channel_score": float(np.mean([r["short_channel_score"] for r in items])),
            "v8_score": float(np.mean([r["v8_score"] for r in items])),
        }
        out.append(row)
    out.sort(key=lambda r: (r["v8_score"], r["mean_target_correct"]), reverse=True)
    return out


def validate(samples: list[dict], screen_rows: list[dict], field_stats) -> tuple[list[dict], list[dict], list[dict]]:
    aggregate_screen = aggregate(screen_rows)
    selected = []
    seen_family = set()
    for row in aggregate_screen:
        if row["family"] not in seen_family or len(selected) < 4:
            selected.append(row)
            seen_family.add(row["family"])
        if len(selected) >= 8:
            break
    validation_rows = []
    control_rows = []
    for rank, row in enumerate(selected):
        sample = samples[int(row["sample_id"])]
        for seed in [30_101, 30_109, 30_127, 30_149, 30_163]:
            particles, summary, _, length_m = simulate_candidate(sample, field_stats, seed=seed, particles_per_class=150, steps=330)
            validation_rows.append(row_from_run(sample, particles, summary, length_m, int(row["sample_id"]), "heldout_validation", seed))
        for control_name, kwargs in [
            ("same_length_straight_dep", {"geometry_override": "straight", "dep_enabled": True}),
            ("no_dep", {"dep_enabled": False}),
            ("unfocused_inlet", {"inlet_override": (0.0, 1.0)}),
        ]:
            scores = []
            losses = []
            for seed in [31_003, 31_021, 31_039]:
                particles, summary, _, length_m = simulate_candidate(sample, field_stats, seed=seed, particles_per_class=120, steps=280, **kwargs)
                perf = performance_metrics(particles, summary)
                scores.append(perf["target_correct"])
                losses.append(perf["wall_loss"])
            control_rows.append(
                {
                    "family": sample["family"],
                    "sample_id": int(row["sample_id"]),
                    "control": control_name,
                    "mean_target_correct": float(np.mean(scores)),
                    "mean_wall_loss": float(np.mean(losses)),
                }
            )
    validation_summary = aggregate(validation_rows)
    by_control = {(r["family"], r["sample_id"], r["control"]): r for r in control_rows}
    for row in validation_summary:
        straight = by_control[(row["family"], row["sample_id"], "same_length_straight_dep")]
        no_dep = by_control[(row["family"], row["sample_id"], "no_dep")]
        unfocused = by_control[(row["family"], row["sample_id"], "unfocused_inlet")]
        row["straight_control_correct"] = straight["mean_target_correct"]
        row["no_dep_correct"] = no_dep["mean_target_correct"]
        row["unfocused_inlet_correct"] = unfocused["mean_target_correct"]
        row["topology_gain_vs_straight"] = row["mean_target_correct"] - straight["mean_target_correct"]
        row["passes_v8_gate"] = (
            row["mean_target_correct"] >= 0.90
            and row["length_mm"] <= 50.0
            and row["topology_gain_vs_straight"] >= 0.08
            and row["mean_wall_loss"] < 0.10
            and row["thermal_risk"] != "high"
        )
    validation_summary.sort(key=lambda r: (r["passes_v8_gate"], r["v8_score"], r["topology_gain_vs_straight"]), reverse=True)
    return validation_rows, control_rows, validation_summary


def centerline(shape: str, turns: float, inner_radius_m: float, pitch_m: float, samples: int = 1200) -> tuple[np.ndarray, np.ndarray]:
    if shape in {"asymmetric_spiral", "pinched_spiral"}:
        theta = np.linspace(-0.15 * math.pi, 2.0 * math.pi * turns, samples)
        r = inner_radius_m + pitch_m * theta / (2.0 * math.pi)
        asym = 1.0 + 0.10 * np.sin(1.7 * theta) + (0.06 if shape == "pinched_spiral" else 0.0) * np.sin(4.3 * theta)
        x = r * np.cos(theta) * asym
        y = r * np.sin(theta) * (1.0 - 0.07 * np.cos(1.2 * theta))
        return x, y
    if shape == "c_arc":
        theta = np.linspace(-0.85 * math.pi, 0.85 * math.pi, samples)
        r = inner_radius_m + 0.35 * pitch_m * np.sin(np.linspace(0, math.pi, samples))
        return r * np.cos(theta), r * np.sin(theta)
    if shape == "serpentine":
        t = np.linspace(0, 1, samples)
        length = 2.0 * math.pi * max(turns, 1.0) * (inner_radius_m + 0.5 * pitch_m * turns)
        x = (t - 0.5) * min(length, 0.055)
        y = 0.00075 * np.sin(2.0 * math.pi * turns * t)
        return x, y
    theta = np.linspace(0.0, 2.0 * math.pi * turns, samples)
    r = inner_radius_m + pitch_m * theta / (2.0 * math.pi)
    return r * np.cos(theta), r * np.sin(theta)


def make_professional_shape_gallery(samples: list[dict], validation: list[dict]) -> None:
    top_by_family = {}
    for row in validation:
        top_by_family.setdefault(row["family"], samples[int(row["sample_id"])])
    fig, axes = plt.subplots(2, 3, figsize=(10, 6.8))
    axes = axes.ravel()
    for ax, (family_name, sample) in zip(axes, top_by_family.items()):
        x, y = centerline(sample["visual_shape"], sample["turns"], sample["inner_radius_m"], sample["pitch_m"])
        ax.plot(x * 1e3, y * 1e3, color="#1f2937", lw=2.2)
        n = len(x)
        start = int(sample["dep_start_fraction"] * (n - 1))
        end = int(sample["dep_end_fraction"] * (n - 1))
        ax.plot(x[start:end] * 1e3, y[start:end] * 1e3, color="#d95f02", lw=4.0, alpha=0.75)
        ax.set_title(family_name.replace("_", " "), fontsize=9)
        ax.set_aspect("equal")
        ax.axis("off")
    for ax in axes[len(top_by_family):]:
        ax.axis("off")
    fig.suptitle("V8 candidate geometry families; orange indicates active DEP zone", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "v8_geometry_family_gallery.png", dpi=240)
    plt.close(fig)


def plot_results(screen_rows: list[dict], validation: list[dict], controls: list[dict]) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    families = sorted(set(r["family"] for r in screen_rows))
    color_map = {name: plt.cm.tab10(i % 10) for i, name in enumerate(families)}

    plt.figure(figsize=(8.5, 5.2))
    for fam in families:
        subset = [r for r in screen_rows if r["family"] == fam]
        plt.scatter(
            [r["length_mm"] for r in subset],
            [r["target_correct"] for r in subset],
            s=[18 + 3.0 * r["active_joule_power_mW"] for r in subset],
            alpha=0.55,
            label=fam.replace("_", " "),
            color=color_map[fam],
            edgecolors="none",
        )
    plt.axhline(0.90, color="black", ls="--", lw=1)
    plt.xlabel("Channel length (mm)")
    plt.ylabel("Target correct")
    plt.title("V8 screening: accuracy versus channel length")
    plt.legend(fontsize=7, ncol=2, frameon=True)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "v8_screen_accuracy_vs_length.png", dpi=240)
    plt.close()

    labels = [r["family"].replace("_", "\n") for r in validation]
    x = np.arange(len(labels))
    width = 0.22
    plt.figure(figsize=(10, 5.3))
    plt.bar(x - width, [r["mean_target_correct"] for r in validation], width, label="validated", color="#2a9d8f")
    plt.bar(x, [r["straight_control_correct"] for r in validation], width, label="straight control", color="#8d99ae")
    plt.bar(x + width, [r["no_dep_correct"] for r in validation], width, label="no DEP", color="#e76f51")
    plt.axhline(0.90, color="black", ls="--", lw=1)
    plt.xticks(x, labels, fontsize=8)
    plt.ylabel("Target correct")
    plt.title("V8 held-out validation and controls")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "v8_validation_controls.png", dpi=240)
    plt.close()

    metrics = ["mean_target_correct", "topology_gain_vs_straight", "length_mm", "active_joule_power_mW", "steady_substrate_delta_c_proxy"]
    mat = np.array([[r[m] for m in metrics] for r in validation], dtype=float)
    norm = (mat - mat.min(axis=0)) / np.maximum(1e-12, mat.max(axis=0) - mat.min(axis=0))
    plt.figure(figsize=(8.6, 4.8))
    im = plt.imshow(norm, cmap="viridis", aspect="auto")
    plt.yticks(range(len(validation)), [r["family"].replace("_", " ") for r in validation], fontsize=8)
    plt.xticks(range(len(metrics)), [m.replace("_", "\n") for m in metrics], fontsize=8)
    plt.colorbar(im, label="Column-normalized value")
    plt.title("V8 finalist metric map")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "v8_finalist_metric_heatmap.png", dpi=240)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.scatter(
        [r["active_joule_power_mW"] for r in validation],
        [r["short_channel_score"] for r in validation],
        s=[80 + 80 * max(0, r["topology_gain_vs_straight"]) for r in validation],
        c=[r["mean_target_correct"] for r in validation],
        cmap="mako" if "mako" in plt.colormaps() else "viridis",
        edgecolors="black",
        linewidth=0.5,
    )
    for r in validation:
        plt.annotate(r["family"].replace("_", " "), (r["active_joule_power_mW"], r["short_channel_score"]), fontsize=7)
    plt.xlabel("Active Joule power proxy (mW)")
    plt.ylabel("Short-channel score ((correct - 0.5) / mm)")
    plt.title("V8 short-channel efficiency versus Joule power")
    plt.colorbar(label="Validated correct")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "v8_short_channel_vs_power.png", dpi=240)
    plt.close()


def path_position(sample: dict, progress: float, lateral_m: float) -> tuple[float, float]:
    x, y = centerline(sample["visual_shape"], sample["turns"], sample["inner_radius_m"], sample["pitch_m"], samples=1400)
    idx = min(len(x) - 2, max(1, int(progress * (len(x) - 1))))
    dx = x[idx + 1] - x[idx - 1]
    dy = y[idx + 1] - y[idx - 1]
    norm = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / norm, dx / norm
    return float(x[idx] + nx * lateral_m), float(y[idx] + ny * lateral_m)


def render_professional_animation(best_sample: dict, field_stats) -> None:
    particles, summary, records, length_m = simulate_candidate(
        best_sample,
        field_stats,
        seed=44_001,
        particles_per_class=140,
        steps=420,
        keep_paths=True,
    )
    write_csv(particles, OUT_DIR / "v8_best_visual_particles.csv")
    (OUT_DIR / "v8_best_visual_summary.json").write_text(json.dumps({"sample": best_sample, "summary": summary}, indent=2) + "\n", encoding="utf-8")

    by_key: dict[tuple[str, int], list[dict]] = {}
    for row in records:
        by_key.setdefault((row["class"], int(row["particle_id"])), []).append(row)
    for rows in by_key.values():
        rows.sort(key=lambda r: r["progress"])

    cx, cy = centerline(best_sample["visual_shape"], best_sample["turns"], best_sample["inner_radius_m"], best_sample["pitch_m"], samples=1600)
    allx, ally = cx * 1e3, cy * 1e3
    margin = 0.45
    xmin, xmax = float(allx.min() - margin), float(allx.max() + margin)
    ymin, ymax = float(ally.min() - margin), float(ally.max() + margin)
    frames_dir = OUT_DIR / "professional_animation_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    video_path = OUT_DIR / "v8_best_professional_animation.mp4"

    n = len(cx)
    s0 = int(best_sample["dep_start_fraction"] * (n - 1))
    s1 = int(best_sample["dep_end_fraction"] * (n - 1))
    for i, progress in enumerate(np.linspace(0, 1, 120)):
        fig, ax = plt.subplots(figsize=(8, 8), facecolor="#f8fafc")
        ax.set_facecolor("#f8fafc")
        ax.plot(cx * 1e3, cy * 1e3, color="#d0d7de", lw=13, solid_capstyle="round", zorder=1)
        ax.plot(cx * 1e3, cy * 1e3, color="#f8fafc", lw=9, solid_capstyle="round", zorder=2)
        ax.plot(cx[s0:s1] * 1e3, cy[s0:s1] * 1e3, color="#f4a261", lw=14, alpha=0.35, solid_capstyle="round", zorder=0)
        ax.plot(cx[s0:s1] * 1e3, cy[s0:s1] * 1e3, color="#d95f02", lw=2.0, alpha=0.9, zorder=3)

        live_points = []
        dead_points = []
        for (name, _pid), rows in by_key.items():
            selected = min(rows, key=lambda r: abs(r["progress"] - progress))
            px, py = path_position(best_sample, selected["progress"], selected["lateral_m"])
            (live_points if name == "live" else dead_points).append((px * 1e3, py * 1e3))
        if live_points:
            arr = np.array(live_points)
            ax.scatter(arr[:, 0], arr[:, 1], s=12, color="#d62828", alpha=0.80, label="live", zorder=4)
        if dead_points:
            arr = np.array(dead_points)
            ax.scatter(arr[:, 0], arr[:, 1], s=12, color="#1d4ed8", alpha=0.80, label="dead", zorder=4)

        ax.text(0.02, 0.96, "V8 optimized short-channel DEP geometry", transform=ax.transAxes, fontsize=12, weight="bold", color="#111827")
        ax.text(0.02, 0.92, f"{best_sample['family']} | active DEP zone shown in orange", transform=ax.transAxes, fontsize=9, color="#374151")
        ax.text(0.02, 0.04, f"progress {progress:0.2f}", transform=ax.transAxes, fontsize=9, color="#374151")
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.legend(loc="lower right", frameon=True, fontsize=8)
        fig.tight_layout(pad=0)
        frame = frames_dir / f"frame_{i:04d}.png"
        fig.savefig(frame, dpi=150)
        plt.close(fig)

    first = cv2.imread(str(frames_dir / "frame_0000.png"))
    h, w = first.shape[:2]
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), 24.0, (w, h))
    for frame_path in sorted(frames_dir.glob("frame_*.png")):
        writer.write(cv2.imread(str(frame_path)))
    writer.release()
    still = OUT_DIR / "v8_best_professional_still.png"
    still.write_bytes((frames_dir / "frame_0070.png").read_bytes())


def write_readme(validation: list[dict]) -> None:
    best = validation[0]
    lines = [
        "# Design V8 Shape ML Optimization",
        "",
        "V8 searches across non-identical geometry families and explicitly rewards",
        "short-channel separation. The final reported candidates are not ML",
        "predictions; they are held-out reduced-order particle simulations selected",
        "after surrogate triage.",
        "",
        "## How ML Was Used",
        "",
        "1. A real simulation set was generated with Latin/random samples across",
        "   shape family, voltage, velocity, width, DEP segment, field-gain proxy,",
        "   and geometry dimensions.",
        "2. An ExtraTreesRegressor learned `v8_score`, a multi-objective score that",
        "   includes target correct, short-channel score, wall loss, channel length,",
        "   Joule-power proxy, and thermal-risk penalty.",
        "3. The surrogate ranked thousands of virtual candidates.",
        "4. The selected candidates were re-run with the particle model, then the",
        "   finalists were validated on held-out seeds and controls.",
        "",
        "ML did not generate final metrics directly and was not trained on the",
        "held-out validation seeds.",
        "",
        "## Best Current Candidate",
        "",
        f"- family: `{best['family']}`",
        f"- target correct: `{best['mean_target_correct']:.3f} +/- {best['std_target_correct']:.3f}`",
        f"- short-channel score: `{best['short_channel_score']:.4f}` per mm",
        f"- topology gain vs same-length straight DEP: `{best['topology_gain_vs_straight']:.3f}`",
        f"- wall loss: `{best['mean_wall_loss']:.3f}`",
        f"- live recovery: `{best['mean_live_recovery']:.3f}`",
        f"- dead removal: `{best['mean_dead_removal']:.3f}`",
        f"- live/dead outlet purity: `{best['mean_live_outlet_purity']:.3f}` / `{best['mean_dead_outlet_purity']:.3f}`",
        f"- length: `{best['length_mm']:.1f} mm`",
        f"- residence time: `{best['residence_s']:.1f} s`",
        f"- pressure drop proxy: `{best['pressure_drop_kPa']:.2f} kPa`",
        f"- active Joule power proxy: `{best['active_joule_power_mW']:.2f} mW`",
        f"- steady substrate temperature-rise proxy: `{best['steady_substrate_delta_c_proxy']:.2f} C`",
        f"- thermal risk: `{best['thermal_risk']}`",
        f"- passes V8 gate: `{best['passes_v8_gate']}`",
        "",
        "## Important Limitation",
        "",
        "The `field_gain` term is a reduced-order electrode-concentration proxy. It",
        "represents shaped/facing/pinched electrode regions, not a solved 3D",
        "electric-field map. V8 is stronger than V7 for design triage, but final",
        "claims still require electrode-resolved OpenFOAM or FEM field solutions.",
        "",
        "## Files",
        "",
        "- `v8_validation_summary.csv`",
        "- `v8_control_rows.csv`",
        "- `v8_screening_rows.csv`",
        "- `v8_screen_accuracy_vs_length.png`",
        "- `v8_validation_controls.png`",
        "- `v8_finalist_metric_heatmap.png`",
        "- `v8_short_channel_vs_power.png`",
        "- `v8_ml_feature_importance.png`",
        "- `v8_geometry_family_gallery.png`",
        "- `v8_best_professional_animation.mp4`",
        "- `v8_best_professional_still.png`",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_openfoam_case()
    field_stats = load_openfoam_field_stats()
    base = read_balanced_v6()
    samples, screen_rows, model = generate_screen(field_stats, base)
    validation_rows, control_rows, validation_summary = validate(samples, screen_rows, field_stats)
    write_csv(screen_rows, OUT_DIR / "v8_screening_rows.csv")
    write_csv(validation_rows, OUT_DIR / "v8_validation_replicates.csv")
    write_csv(control_rows, OUT_DIR / "v8_control_rows.csv")
    write_csv(validation_summary, OUT_DIR / "v8_validation_summary.csv")
    plot_results(screen_rows, validation_summary, control_rows)
    make_professional_shape_gallery(samples, validation_summary)
    best_sample = samples[int(validation_summary[0]["sample_id"])]
    render_professional_animation(best_sample, field_stats)
    write_readme(validation_summary)
    print((OUT_DIR / "README.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
