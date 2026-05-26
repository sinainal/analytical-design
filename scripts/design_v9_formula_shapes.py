#!/usr/bin/env python3
"""Design V9 formula-defined spiral geometries.

V9 removes "free-form" geometry language. Every candidate is generated from a
small set of mathematical functions:

    r(theta) = a + b theta + c sin(n theta + phi)
    w(s)     = w0 [1 + beta sigmoid((s - s_out) / ell_out)]
    alpha(s) = sigmoid((s-s1)/ell1) [1 - sigmoid((s-s2)/ell2)]

The particle model remains reduced-order, but the geometry itself is explicit,
smooth, and exportable.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor

from design_v7_geometry_feasibility import CP_WATER_J_KG_K, MU_PA_S, RHO_WATER_KG_M3, performance_metrics, read_balanced_v6
from optimization_v1_surrogate import make_spec
from study_common import (
    CHANNEL_HEIGHT_M,
    MEDIUM_SIGMA_S_M,
    load_openfoam_field_stats,
    run_openfoam_case,
    run_particle,
    sample_cell,
    summarize,
    write_csv,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "design_v9_formula_shapes"


@dataclass(frozen=True)
class FormulaFamily:
    name: str
    equation: str
    turns_range: tuple[float, float]
    a_um: tuple[float, float]
    b_um_per_rad: tuple[float, float]
    c_ratio: tuple[float, float]
    n_mode: tuple[float, float]
    width_um: tuple[float, float]
    outlet_expansion: tuple[float, float]
    dep_start: tuple[float, float]
    dep_end: tuple[float, float]
    field_gain: tuple[float, float]
    dean_scale: tuple[float, float]
    footprint_factor: float
    solver_geometry: str
    note: str


FAMILIES = [
    FormulaFamily(
        "curvature_modulated_spiral",
        "r(theta)=a+b theta+c sin(n theta+phi)",
        (2.3, 4.6),
        (520, 850),
        (25, 55),
        (0.035, 0.115),
        (1.4, 2.8),
        (135, 210),
        (0.00, 0.35),
        (0.26, 0.55),
        (0.72, 0.98),
        (1.05, 1.45),
        (0.70, 1.20),
        0.82,
        "spiral",
        "Smooth curvature modulation to align Dean drift with DEP staging.",
    ),
    FormulaFamily(
        "outlet_expanded_modulated_spiral",
        "r(theta)=a+b theta+c sin(n theta+phi), w(s)=w0[1+beta sigmoid(...)]",
        (2.6, 5.2),
        (560, 980),
        (24, 58),
        (0.025, 0.095),
        (1.2, 2.4),
        (125, 190),
        (0.20, 0.70),
        (0.38, 0.68),
        (0.74, 0.99),
        (1.12, 1.55),
        (0.80, 1.35),
        0.92,
        "spiral",
        "Late outlet expansion to reduce wall loss after DEP separation.",
    ),
    FormulaFamily(
        "tapered_c_spiral",
        "theta in [-pi, pi]; r(theta)=a+b theta+c sin(2 theta+phi)",
        (0.85, 1.85),
        (720, 1250),
        (20, 85),
        (0.025, 0.095),
        (1.7, 2.5),
        (140, 230),
        (0.00, 0.45),
        (0.10, 0.42),
        (0.65, 0.96),
        (1.18, 1.70),
        (0.25, 0.70),
        0.58,
        "spiral",
        "Short C-shaped spiral limit for shortest possible channel.",
    ),
    FormulaFamily(
        "logarithmic_dean_spiral",
        "r(theta)=a exp(k theta) with small sinusoidal curvature modulation",
        (2.2, 4.2),
        (480, 820),
        (12, 32),
        (0.015, 0.075),
        (1.1, 2.2),
        (150, 235),
        (0.05, 0.45),
        (0.32, 0.62),
        (0.72, 0.98),
        (1.00, 1.35),
        (0.55, 1.05),
        0.78,
        "spiral",
        "Log-like radius growth gives high initial curvature and calmer outlet.",
    ),
]


def sigmoid(x: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-x))


def family_by_name() -> dict[str, FormulaFamily]:
    return {f.name: f for f in FAMILIES}


def sample_formula(family: FormulaFamily, base: dict, rng: np.random.Generator) -> dict:
    dep_start = float(rng.uniform(*family.dep_start))
    dep_end = float(rng.uniform(*family.dep_end))
    if dep_end <= dep_start + 0.16:
        dep_end = min(1.0, dep_start + 0.16)
    width0_um = float(rng.uniform(*family.width_um))
    beta = float(rng.uniform(*family.outlet_expansion))
    return {
        "family": family.name,
        "equation": family.equation,
        "solver_geometry": family.solver_geometry,
        "frequency_hz": float(np.clip(base["frequency_hz"] * rng.uniform(0.70, 1.35), 150e3, 4.5e6)),
        "voltage_v": float(rng.uniform(12.0, 24.0)),
        "velocity_m_s": float(rng.uniform(1100e-6, 5600e-6)),
        "turns": float(rng.uniform(*family.turns_range)),
        "a_m": float(rng.uniform(*family.a_um)) * 1e-6,
        "b_m_per_rad": float(rng.uniform(*family.b_um_per_rad)) * 1e-6,
        "c_ratio": float(rng.uniform(*family.c_ratio)),
        "n_mode": float(rng.uniform(*family.n_mode)),
        "phase_rad": float(rng.uniform(-math.pi, math.pi)),
        "width0_m": width0_um * 1e-6,
        "outlet_expansion_beta": beta,
        "outlet_expansion_center": float(rng.uniform(0.72, 0.90)),
        "outlet_expansion_ell": float(rng.uniform(0.035, 0.090)),
        "outlet_split_ratio": float(rng.uniform(0.30, 0.58)),
        "inlet_offset_ratio": float(rng.uniform(-0.82, -0.34)),
        "inlet_spread_ratio": float(rng.uniform(0.15, 0.45)),
        "dep_start_fraction": dep_start,
        "dep_end_fraction": dep_end,
        "dep_edge_smoothness": float(rng.uniform(0.018, 0.055)),
        "field_gain": float(rng.uniform(*family.field_gain)),
        "dep_sign": -1.0,
        "dean_scale": float(rng.uniform(*family.dean_scale)),
        "footprint_factor": family.footprint_factor,
        "note": family.note,
    }


def radius_theta(sample: dict, theta: np.ndarray) -> np.ndarray:
    if sample["family"] == "logarithmic_dean_spiral":
        k = sample["b_m_per_rad"] / max(sample["a_m"], 1e-12)
        base = sample["a_m"] * np.exp(k * theta)
    else:
        base = sample["a_m"] + sample["b_m_per_rad"] * theta
    amp = sample["c_ratio"] * sample["a_m"]
    return np.maximum(100e-6, base + amp * np.sin(sample["n_mode"] * theta + sample["phase_rad"]))


def centerline(sample: dict, n: int = 1400) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if sample["family"] == "tapered_c_spiral":
        theta = np.linspace(-math.pi * sample["turns"], math.pi * sample["turns"], n)
    else:
        theta = np.linspace(0.0, 2.0 * math.pi * sample["turns"], n)
    r = radius_theta(sample, theta)
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    if sample["family"] in {"curvature_modulated_spiral", "outlet_expanded_modulated_spiral"}:
        # Smooth anisotropic scaling creates a controlled asymmetric spiral,
        # not a random free-form curve.
        y *= 1.0 - 0.055 * np.cos(0.6 * theta + sample["phase_rad"])
    return theta, x, y


def path_length(sample: dict) -> float:
    _, x, y = centerline(sample)
    return float(np.sum(np.hypot(np.diff(x), np.diff(y))))


def width_at(sample: dict, progress: float) -> float:
    return sample["width0_m"] * (
        1.0
        + sample["outlet_expansion_beta"]
        * sigmoid((progress - sample["outlet_expansion_center"]) / sample["outlet_expansion_ell"])
    )


def mean_width(sample: dict) -> float:
    p = np.linspace(0, 1, 200)
    return float(np.mean([width_at(sample, float(v)) for v in p]))


def active_fraction_smooth(sample: dict) -> float:
    p = np.linspace(0, 1, 300)
    ell = sample["dep_edge_smoothness"]
    alpha = sigmoid((p - sample["dep_start_fraction"]) / ell) * (1.0 - sigmoid((p - sample["dep_end_fraction"]) / ell))
    return float(np.trapz(alpha, p))


def sample_to_spec(sample: dict, effective_voltage: bool = True):
    width = mean_width(sample)
    row = {
        "turns": sample["turns"],
        "inner_radius_m": sample["a_m"],
        "pitch_m": sample["b_m_per_rad"] * 2.0 * math.pi,
        "channel_width_m": width,
        "voltage_v": sample["voltage_v"] * (sample["field_gain"] if effective_voltage else 1.0),
        "velocity_m_s": sample["velocity_m_s"],
    }
    return make_spec(row)


def feasibility(sample: dict, length_m: float) -> dict:
    width = mean_width(sample)
    height = CHANNEL_HEIGHT_M
    velocity = sample["velocity_m_s"]
    flow = velocity * width * height
    aspect = min(height, width) / max(height, width)
    correction = max(0.12, 1.0 - 0.63 * aspect)
    pressure_pa = 12.0 * MU_PA_S * length_m * flow / (width * height**3 * correction)
    dh = 2.0 * width * height / (width + height)
    reynolds = RHO_WATER_KG_M3 * velocity * dh / MU_PA_S
    e_field = sample["voltage_v"] * sample["field_gain"] / width
    active_power = MEDIUM_SIGMA_S_M * e_field**2 * length_m * width * height * active_fraction_smooth(sample)
    residence = length_m / max(1e-12, velocity)
    volume = length_m * width * height
    adiabatic = active_power * residence / max(1e-18, RHO_WATER_KG_M3 * CP_WATER_J_KG_K * volume)
    _, x, y = centerline(sample)
    footprint_m2 = sample["footprint_factor"] * (x.max() - x.min() + width) * (y.max() - y.min() + width)
    steady = active_power * 1e-3 / max(1e-18, 0.20 * footprint_m2)
    risk = "low"
    if active_power * 1000 > 25 or steady > 10:
        risk = "high"
    elif active_power * 1000 > 10 or steady > 5:
        risk = "moderate"
    return {
        "length_mm": length_m * 1e3,
        "mean_width_um": width * 1e6,
        "footprint_mm2": footprint_m2 * 1e6,
        "residence_s": residence,
        "flow_uL_min": flow * 1e9 * 60,
        "pressure_drop_kPa": pressure_pa / 1000,
        "reynolds": reynolds,
        "effective_field_kV_m": e_field / 1000,
        "active_joule_power_mW": active_power * 1000,
        "adiabatic_delta_c_proxy": adiabatic,
        "steady_substrate_delta_c_proxy": steady,
        "thermal_risk": risk,
    }


def simulate(sample: dict, field_stats, seed: int, particles_per_class: int, steps: int, dep_enabled: bool = True, geometry_override: str | None = None, inlet_override: tuple[float, float] | None = None):
    rng = np.random.default_rng(seed)
    spec = sample_to_spec(sample, effective_voltage=True)
    length_m = path_length(sample)
    inlet_offset = sample["inlet_offset_ratio"]
    inlet_spread = sample["inlet_spread_ratio"]
    if inlet_override is not None:
        inlet_offset, inlet_spread = inlet_override
    results = []
    pid = 0
    for name in ["live", "dead"]:
        for _ in range(particles_per_class):
            cell = sample_cell(rng, name, spec.channel_width_m, sample["frequency_hz"], inlet_offset, inlet_spread)
            result, _ = run_particle(
                spec,
                cell,
                field_stats,
                rng,
                pid,
                steps,
                sample["frequency_hz"],
                sample["outlet_split_ratio"],
                geometry=geometry_override or sample["solver_geometry"],
                dep_enabled=dep_enabled,
                dep_sign=sample["dep_sign"],
                keep_path=False,
                length_m=length_m,
                dep_start_fraction=sample["dep_start_fraction"],
                dep_end_fraction=sample["dep_end_fraction"],
                dean_scale=sample["dean_scale"],
            )
            results.append(result)
            pid += 1
    summary = summarize(results, spec, seed, sample["frequency_hz"], sample["outlet_split_ratio"], geometry_override or sample["solver_geometry"], dep_enabled, sample["dep_sign"])
    return results, summary, length_m


def run_row(sample: dict, field_stats, sample_id: int, seed: int, stage: str, particles: int, steps: int) -> dict:
    particle_rows, summary, length_m = simulate(sample, field_stats, seed, particles, steps)
    row = {
        "stage": stage,
        "sample_id": sample_id,
        "seed": seed,
        "family": sample["family"],
        "equation": sample["equation"],
        "frequency_hz": sample["frequency_hz"],
        "voltage_v": sample["voltage_v"],
        "field_gain": sample["field_gain"],
        "effective_voltage_v": sample["voltage_v"] * sample["field_gain"],
        "velocity_um_s": sample["velocity_m_s"] * 1e6,
        "turns": sample["turns"],
        "a_um": sample["a_m"] * 1e6,
        "b_um_per_rad": sample["b_m_per_rad"] * 1e6,
        "c_ratio": sample["c_ratio"],
        "n_mode": sample["n_mode"],
        "phase_rad": sample["phase_rad"],
        "width0_um": sample["width0_m"] * 1e6,
        "outlet_expansion_beta": sample["outlet_expansion_beta"],
        "outlet_expansion_center": sample["outlet_expansion_center"],
        "outlet_expansion_ell": sample["outlet_expansion_ell"],
        "outlet_split_ratio": sample["outlet_split_ratio"],
        "inlet_offset_ratio": sample["inlet_offset_ratio"],
        "inlet_spread_ratio": sample["inlet_spread_ratio"],
        "dep_start_fraction": sample["dep_start_fraction"],
        "dep_end_fraction": sample["dep_end_fraction"],
        "dep_edge_smoothness": sample["dep_edge_smoothness"],
        "dean_scale": sample["dean_scale"],
    }
    row.update(performance_metrics(particle_rows, summary))
    row.update(feasibility(sample, length_m))
    row["short_channel_score"] = (row["target_correct"] - 0.5) / max(1e-9, row["length_mm"])
    row["v9_score"] = (
        row["target_correct"]
        + 9.0 * row["short_channel_score"]
        - 1.0 * row["wall_loss"]
        - 0.0012 * max(0.0, row["length_mm"] - 35.0)
        - 0.0035 * max(0.0, row["active_joule_power_mW"] - 8.0)
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
    "a_um",
    "b_um_per_rad",
    "c_ratio",
    "n_mode",
    "width0_um",
    "outlet_expansion_beta",
    "dep_start_fraction",
    "dep_end_fraction",
    "dean_scale",
]


def feature(sample: dict) -> list[float]:
    fam_id = family_by_name().keys()
    fam_index = list(fam_id).index(sample["family"])
    return [
        fam_index,
        math.log10(sample["frequency_hz"]),
        sample["voltage_v"],
        sample["field_gain"],
        sample["velocity_m_s"] * 1e6,
        sample["turns"],
        sample["a_m"] * 1e6,
        sample["b_m_per_rad"] * 1e6,
        sample["c_ratio"],
        sample["n_mode"],
        sample["width0_m"] * 1e6,
        sample["outlet_expansion_beta"],
        sample["dep_start_fraction"],
        sample["dep_end_fraction"],
        sample["dean_scale"],
    ]


def write_formula_shape(sample: dict, out_dir: Path, prefix: str) -> None:
    theta, x, y = centerline(sample, n=1600)
    rows = []
    for i, (t, xi, yi) in enumerate(zip(theta, x, y)):
        p = i / (len(theta) - 1)
        rows.append(
            {
                "index": i,
                "progress": p,
                "theta_rad": t,
                "x_m": xi,
                "y_m": yi,
                "width_m": width_at(sample, p),
                "alpha_dep": sigmoid((p - sample["dep_start_fraction"]) / sample["dep_edge_smoothness"])
                * (1.0 - sigmoid((p - sample["dep_end_fraction"]) / sample["dep_edge_smoothness"])),
            }
        )
    write_csv(rows, out_dir / f"{prefix}_centerline.csv")
    (out_dir / f"{prefix}_formula.json").write_text(json.dumps(sample, indent=2) + "\n", encoding="utf-8")


def aggregate(rows: list[dict]) -> list[dict]:
    grouped: dict[int, list[dict]] = {}
    for row in rows:
        grouped.setdefault(int(row["sample_id"]), []).append(row)
    out = []
    for sample_id, items in grouped.items():
        first = items[0]
        out.append(
            {
                "sample_id": sample_id,
                "family": first["family"],
                "equation": first["equation"],
                "mean_target_correct": float(np.mean([r["target_correct"] for r in items])),
                "std_target_correct": float(np.std([r["target_correct"] for r in items], ddof=1)) if len(items) > 1 else 0.0,
                "mean_wall_loss": float(np.mean([r["wall_loss"] for r in items])),
                "mean_live_recovery": float(np.mean([r["live_recovery"] for r in items])),
                "mean_dead_removal": float(np.mean([r["dead_removal"] for r in items])),
                "mean_live_outlet_purity": float(np.mean([r["live_outlet_purity"] for r in items])),
                "mean_dead_outlet_purity": float(np.mean([r["dead_outlet_purity"] for r in items])),
                "length_mm": first["length_mm"],
                "mean_width_um": first["mean_width_um"],
                "residence_s": first["residence_s"],
                "active_joule_power_mW": first["active_joule_power_mW"],
                "steady_substrate_delta_c_proxy": first["steady_substrate_delta_c_proxy"],
                "thermal_risk": first["thermal_risk"],
                "short_channel_score": float(np.mean([r["short_channel_score"] for r in items])),
                "v9_score": float(np.mean([r["v9_score"] for r in items])),
            }
        )
    out.sort(key=lambda r: (r["v9_score"], r["mean_target_correct"]), reverse=True)
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_openfoam_case()
    field_stats = load_openfoam_field_stats()
    base = read_balanced_v6()
    rng = np.random.default_rng(9901)

    samples = []
    rows = []
    for fam in FAMILIES:
        for _ in range(34):
            samples.append(sample_formula(fam, base, rng))
    for i, sample in enumerate(samples):
        rows.append(run_row(sample, field_stats, i, 60_000 + i, "formula_initial", 55, 210))

    model = ExtraTreesRegressor(n_estimators=360, random_state=91, min_samples_leaf=2, n_jobs=-1)
    model.fit(np.array([feature(samples[int(r["sample_id"])]) for r in rows]), np.array([r["v9_score"] for r in rows]))
    imp = [{"feature": k, "importance": float(v)} for k, v in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: x[1], reverse=True)]
    write_csv(imp, OUT_DIR / "v9_ml_feature_importance.csv")

    virtual = []
    for fam in FAMILIES:
        for _ in range(1600):
            virtual.append(sample_formula(fam, base, rng))
    pred = model.predict(np.array([feature(s) for s in virtual]))
    for s, p in zip(virtual, pred):
        s["predicted_v9_score"] = float(p)
    selected = []
    for s in sorted(virtual, key=lambda r: r["predicted_v9_score"], reverse=True):
        if len(selected) >= 24:
            break
        if sum(1 for x in selected if x["family"] == s["family"]) >= 7:
            continue
        selected.append(s)
    offset = len(samples)
    for j, sample in enumerate(selected):
        sample_id = offset + j
        samples.append(sample)
        rows.append(run_row(sample, field_stats, sample_id, 70_000 + j, "ml_selected_formula", 90, 270))

    screen_summary = aggregate(rows)
    validation_rows = []
    control_rows = []
    top = screen_summary[:8]
    for item in top:
        sample = samples[int(item["sample_id"])]
        for seed in [80_101, 80_109, 80_127, 80_149]:
            validation_rows.append(run_row(sample, field_stats, int(item["sample_id"]), seed, "heldout_formula", 150, 330))
        for control_name, kwargs in [
            ("same_length_straight_dep", {"geometry_override": "straight", "dep_enabled": True}),
            ("no_dep", {"dep_enabled": False}),
            ("unfocused_inlet", {"inlet_override": (0.0, 1.0)}),
        ]:
            scores = []
            losses = []
            for seed in [81_003, 81_021, 81_039]:
                particles, summary, length_m = simulate(sample, field_stats, seed, 120, 280, **kwargs)
                perf = performance_metrics(particles, summary)
                scores.append(perf["target_correct"])
                losses.append(perf["wall_loss"])
            control_rows.append(
                {
                    "sample_id": int(item["sample_id"]),
                    "family": sample["family"],
                    "control": control_name,
                    "mean_target_correct": float(np.mean(scores)),
                    "mean_wall_loss": float(np.mean(losses)),
                }
            )
    validation = aggregate(validation_rows)
    controls = {(r["sample_id"], r["control"]): r for r in control_rows}
    for row in validation:
        straight = controls[(row["sample_id"], "same_length_straight_dep")]
        no_dep = controls[(row["sample_id"], "no_dep")]
        unfocused = controls[(row["sample_id"], "unfocused_inlet")]
        row["straight_control_correct"] = straight["mean_target_correct"]
        row["no_dep_correct"] = no_dep["mean_target_correct"]
        row["unfocused_inlet_correct"] = unfocused["mean_target_correct"]
        row["topology_gain_vs_straight"] = row["mean_target_correct"] - straight["mean_target_correct"]
        row["passes_v9_gate"] = (
            row["mean_target_correct"] >= 0.90
            and row["length_mm"] <= 35
            and row["topology_gain_vs_straight"] >= 0.08
            and row["mean_wall_loss"] < 0.10
            and row["thermal_risk"] != "high"
        )
    validation.sort(key=lambda r: (r["passes_v9_gate"], r["v9_score"], r["topology_gain_vs_straight"]), reverse=True)

    write_csv(rows, OUT_DIR / "v9_screening_rows.csv")
    write_csv(screen_summary, OUT_DIR / "v9_screening_summary.csv")
    write_csv(validation_rows, OUT_DIR / "v9_validation_replicates.csv")
    write_csv(control_rows, OUT_DIR / "v9_control_rows.csv")
    write_csv(validation, OUT_DIR / "v9_validation_summary.csv")

    for rank, row in enumerate(validation[:5], start=1):
        write_formula_shape(samples[int(row["sample_id"])], OUT_DIR, f"rank{rank}_{row['family']}")

    # Academic plots.
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(8, 5))
    fams = sorted(set(r["family"] for r in rows))
    colors = {fam: plt.cm.tab10(i) for i, fam in enumerate(fams)}
    for fam in fams:
        subset = [r for r in rows if r["family"] == fam]
        ax.scatter([r["length_mm"] for r in subset], [r["target_correct"] for r in subset], s=22, alpha=0.55, color=colors[fam], label=fam.replace("_", " "))
    ax.axhline(0.90, color="black", ls="--", lw=1)
    ax.set_xlabel("Formula channel length (mm)")
    ax.set_ylabel("Target correct")
    ax.set_title("V9 formula-defined geometry screening")
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "v9_formula_accuracy_vs_length.png", dpi=240)
    plt.close(fig)

    labels = [r["family"].replace("_", "\n") for r in validation]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - 0.22, [r["mean_target_correct"] for r in validation], 0.22, label="validated", color="#2a9d8f")
    ax.bar(x, [r["straight_control_correct"] for r in validation], 0.22, label="straight control", color="#8d99ae")
    ax.bar(x + 0.22, [r["no_dep_correct"] for r in validation], 0.22, label="no DEP", color="#e76f51")
    ax.axhline(0.90, color="black", ls="--", lw=1)
    ax.set_xticks(x, labels, fontsize=8)
    ax.set_ylabel("Target correct")
    ax.set_title("V9 held-out validation and controls")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "v9_validation_controls.png", dpi=240)
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(10, 6.5))
    axes = axes.ravel()
    for ax, row in zip(axes, validation[:6]):
        sample = samples[int(row["sample_id"])]
        _, xline, yline = centerline(sample, n=1300)
        p = np.linspace(0, 1, len(xline))
        alpha = sigmoid((p - sample["dep_start_fraction"]) / sample["dep_edge_smoothness"]) * (1 - sigmoid((p - sample["dep_end_fraction"]) / sample["dep_edge_smoothness"]))
        ax.plot(xline * 1e3, yline * 1e3, color="#111827", lw=1.8)
        ax.scatter(xline[::12] * 1e3, yline[::12] * 1e3, c=alpha[::12], cmap="inferno", s=8)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"{row['family']}\\nC={row['mean_target_correct']:.3f}, L={row['length_mm']:.1f} mm", fontsize=8)
    for ax in axes[len(validation[:6]):]:
        ax.axis("off")
    fig.suptitle("V9 formula-defined finalists; color shows smooth DEP activation", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "v9_formula_shape_gallery.png", dpi=240)
    plt.close(fig)

    best = validation[0]
    best_sample = samples[int(best["sample_id"])]
    readme = [
        "# Design V9 Formula Shapes",
        "",
        "V9 uses explicit mathematical shape functions rather than informal",
        "free-form geometry labels.",
        "",
        "## Shape Functions",
        "",
        "- Radius: `r(theta)=a+b theta+c sin(n theta+phi)` or a log-like variant.",
        "- Width: `w(s)=w0[1+beta sigmoid((s-s_out)/ell_out)]`.",
        "- DEP activation: `alpha(s)=sigmoid((s-s1)/ell1)[1-sigmoid((s-s2)/ell2)]`.",
        "",
        "## Best Candidate",
        "",
        f"- family: `{best['family']}`",
        f"- target correct: `{best['mean_target_correct']:.3f} +/- {best['std_target_correct']:.3f}`",
        f"- topology gain vs same-length straight DEP: `{best['topology_gain_vs_straight']:.3f}`",
        f"- length: `{best['length_mm']:.1f} mm`",
        f"- short-channel score: `{best['short_channel_score']:.4f}` per mm",
        f"- wall loss: `{best['mean_wall_loss']:.3f}`",
        f"- active Joule power proxy: `{best['active_joule_power_mW']:.2f} mW`",
        f"- steady substrate temperature-rise proxy: `{best['steady_substrate_delta_c_proxy']:.2f} C`",
        f"- passes V9 gate: `{best['passes_v9_gate']}`",
        "",
        "## Stored Shape Data",
        "",
        "The top five formula geometries are saved as `rank*_centerline.csv` and",
        "`rank*_formula.json`, including `x`, `y`, local width, and smooth DEP",
        "activation values.",
        "",
        "## Honest Limitation",
        "",
        "The electric-field effect still uses a reduced-order `field_gain` proxy.",
        "The shape functions are now mathematically explicit, but the best formula",
        "must still be converted into an electrode-resolved field solve before a",
        "final device claim.",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    print((OUT_DIR / "README.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
