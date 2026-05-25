#!/usr/bin/env python3
"""Design V7 geometry and feasibility comparison.

V7 treats high accuracy as insufficient by itself. It compares alternative
geometry families and reports fabrication/operation proxies: length, footprint,
residence time, pressure drop, Joule heating, and control-case performance.
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

from design_v0_particle_tracking import SpiralSpec
from optimization_v1_surrogate import sample_from_summary
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
OUT_DIR = ROOT / "results" / "design_v7_geometry_feasibility"

RHO_WATER_KG_M3 = 997.0
CP_WATER_J_KG_K = 4180.0
MU_PA_S = 1.0e-3


@dataclass(frozen=True)
class GeometryFamily:
    name: str
    path_geometry: str
    base_turns: float
    base_inner_radius_m: float
    base_pitch_m: float
    base_width_m: float
    length_factor: float
    dean_scale: float
    dep_start: float
    dep_end: float
    footprint_factor: float
    note: str


def read_balanced_v6() -> dict:
    with (ROOT / "results" / "optimization_v1" / "all_validation_summary.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["stage"] == "segmented_spiral" and int(float(row["sample_id"])) == 164:
                out = {}
                for key, value in row.items():
                    try:
                        out[key] = float(value)
                    except ValueError:
                        out[key] = value
                return sample_from_summary(out)
    raise FileNotFoundError("V6 balanced candidate not found in all_validation_summary.csv")


def spec_from_sample(sample: dict) -> SpiralSpec:
    return SpiralSpec(
        turns=sample["turns"],
        inner_radius_m=sample["inner_radius_m"],
        pitch_m=sample["pitch_m"],
        channel_width_m=sample["channel_width_m"],
        voltage_v=sample["voltage_v"],
        inlet_velocity_m_s=sample["velocity_m_s"],
    )


def active_fraction(sample: dict) -> float:
    return max(0.0, min(1.0, sample.get("dep_end_fraction", 1.0) - sample.get("dep_start_fraction", 0.0)))


def feasibility_metrics(sample: dict, length_m: float, family: GeometryFamily) -> dict:
    width = sample["channel_width_m"]
    height = CHANNEL_HEIGHT_M
    velocity = sample["velocity_m_s"]
    voltage = sample["voltage_v"]
    flow_m3_s = velocity * width * height
    aspect = min(height, width) / max(height, width)
    hydraulic_diameter = 2.0 * width * height / (width + height)
    correction = max(0.12, 1.0 - 0.63 * aspect)
    pressure_pa = 12.0 * MU_PA_S * length_m * flow_m3_s / (width * height**3 * correction)
    reynolds = RHO_WATER_KG_M3 * velocity * hydraulic_diameter / MU_PA_S
    electric_field = voltage / width
    volume_m3 = length_m * width * height
    active_power_w = MEDIUM_SIGMA_S_M * electric_field**2 * volume_m3 * active_fraction(sample)
    residence_s = length_m / max(1e-12, velocity)
    thermal_mass_j_k = RHO_WATER_KG_M3 * CP_WATER_J_KG_K * volume_m3
    adiabatic_delta_c = active_power_w * residence_s / max(1e-18, thermal_mass_j_k)
    r_outer = sample["inner_radius_m"] + sample["pitch_m"] * sample["turns"] + 0.5 * width
    footprint_m2 = family.footprint_factor * math.pi * r_outer * r_outer
    min_bend_radius_m = max(1e-9, sample["inner_radius_m"] - 0.5 * width)
    # A first-order steady heat-loss proxy through a 1 mm PDMS/glass support.
    # This is not a heat-transfer solve; it prevents the adiabatic no-cooling
    # proxy from being misread as the actual chip temperature rise.
    support_thickness_m = 1.0e-3
    support_k_w_m_k = 0.20
    thermal_resistance_k_w = support_thickness_m / max(1e-18, support_k_w_m_k * footprint_m2)
    steady_delta_c_proxy = active_power_w * thermal_resistance_k_w
    risk = "low"
    if active_power_w * 1000.0 > 25.0 or steady_delta_c_proxy > 10.0:
        risk = "high"
    elif active_power_w * 1000.0 > 10.0 or steady_delta_c_proxy > 5.0:
        risk = "moderate"
    return {
        "length_mm": length_m * 1e3,
        "footprint_mm2": footprint_m2 * 1e6,
        "residence_s": residence_s,
        "flow_uL_min": flow_m3_s * 1e9 * 60.0,
        "pressure_drop_kPa": pressure_pa / 1000.0,
        "reynolds": reynolds,
        "electric_field_kV_m": electric_field / 1000.0,
        "active_joule_power_mW": active_power_w * 1000.0,
        "adiabatic_delta_c_proxy": adiabatic_delta_c,
        "steady_substrate_delta_c_proxy": steady_delta_c_proxy,
        "min_bend_radius_um": min_bend_radius_m * 1e6,
        "thermal_risk": risk,
    }


def simulate_sample(
    sample: dict,
    family: GeometryFamily,
    field_stats,
    seed: int,
    particles_per_class: int,
    steps: int,
    geometry_override: str | None = None,
    dep_enabled: bool = True,
    inlet_override: tuple[float, float] | None = None,
) -> tuple[list[dict], dict, float]:
    spec = spec_from_sample(sample)
    length_m = spiral_length(spec) * family.length_factor
    rng = np.random.default_rng(seed)
    results = []
    paths = []
    pid = 0
    geometry = geometry_override or family.path_geometry
    inlet_offset = sample.get("inlet_offset_ratio", 0.0)
    inlet_spread = sample.get("inlet_spread_ratio", 1.0)
    if inlet_override is not None:
        inlet_offset, inlet_spread = inlet_override
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
                dep_sign=sample.get("dep_sign", 1.0),
                keep_path=False,
                length_m=length_m,
                dep_start_fraction=sample.get("dep_start_fraction", 0.0),
                dep_end_fraction=sample.get("dep_end_fraction", 1.0),
                dean_scale=sample.get("dean_scale", family.dean_scale),
            )
            results.append(result)
            paths.extend(path)
            pid += 1
    summary = summarize(
        results,
        spec,
        seed,
        sample["frequency_hz"],
        sample["outlet_split_ratio"],
        geometry,
        dep_enabled,
        sample.get("dep_sign", 1.0),
    )
    return results, summary, length_m


def performance_metrics(particles: list[dict], summary: dict) -> dict:
    live = [p for p in particles if p["class"] == "live"]
    dead = [p for p in particles if p["class"] == "dead"]
    live_inner = sum(p["outlet"] == "inner" for p in live)
    live_outer = sum(p["outlet"] == "outer" for p in live)
    dead_inner = sum(p["outlet"] == "inner" for p in dead)
    dead_outer = sum(p["outlet"] == "outer" for p in dead)
    if summary["preferred_direction"].startswith("B_"):
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
        "live_recovery": live_target / max(1, len(live)),
        "dead_removal": dead_target / max(1, len(dead)),
        "live_outlet_purity": live_target / max(1, live_outlet_total),
        "dead_outlet_purity": dead_target / max(1, dead_outlet_total),
    }


def apply_family(base: dict, family: GeometryFamily, rng: np.random.Generator, jitter: bool) -> dict:
    sample = dict(base)
    sample["turns"] = family.base_turns
    sample["inner_radius_m"] = family.base_inner_radius_m
    sample["pitch_m"] = family.base_pitch_m
    sample["channel_width_m"] = family.base_width_m
    sample["dean_scale"] = family.dean_scale
    sample["dep_start_fraction"] = family.dep_start
    sample["dep_end_fraction"] = family.dep_end
    if jitter:
        sample["turns"] *= float(rng.normal(1.0, 0.08))
        sample["inner_radius_m"] *= float(rng.normal(1.0, 0.10))
        sample["pitch_m"] *= float(rng.normal(1.0, 0.12))
        sample["channel_width_m"] *= float(rng.normal(1.0, 0.09))
        sample["voltage_v"] *= float(rng.normal(1.0, 0.10))
        sample["velocity_m_s"] *= float(rng.normal(1.0, 0.16))
        sample["inlet_offset_ratio"] = float(np.clip(sample.get("inlet_offset_ratio", -0.5) + rng.normal(0.0, 0.08), -0.85, 0.85))
        sample["inlet_spread_ratio"] = float(np.clip(sample.get("inlet_spread_ratio", 0.3) * rng.normal(1.0, 0.25), 0.10, 0.90))
        start = float(np.clip(sample["dep_start_fraction"] + rng.normal(0.0, 0.06), 0.0, 0.85))
        end = float(np.clip(sample["dep_end_fraction"] + rng.normal(0.0, 0.06), 0.15, 1.0))
        if end <= start + 0.12:
            end = min(1.0, start + 0.12)
        sample["dep_start_fraction"] = start
        sample["dep_end_fraction"] = end
    sample["turns"] = float(np.clip(sample["turns"], 0.75, 9.5))
    sample["inner_radius_m"] = float(np.clip(sample["inner_radius_m"], 350e-6, 2400e-6))
    sample["pitch_m"] = float(np.clip(sample["pitch_m"], 70e-6, 520e-6))
    sample["channel_width_m"] = float(np.clip(sample["channel_width_m"], 60e-6, 260e-6))
    sample["voltage_v"] = float(np.clip(sample["voltage_v"], 4.0, 24.0))
    sample["velocity_m_s"] = float(np.clip(sample["velocity_m_s"], 500e-6, 8000e-6))
    return sample


def candidate_score(row: dict) -> float:
    thermal_penalty = {"low": 0.0, "moderate": 0.06, "high": 0.16}[row["thermal_risk"]]
    return (
        row["target_correct"]
        - 1.15 * row["wall_loss"]
        - thermal_penalty
        - 0.0015 * max(0.0, row["residence_s"] - 30.0)
        - 0.0010 * max(0.0, row["length_mm"] - 80.0)
        - 0.0040 * max(0.0, row["active_joule_power_mW"] - 12.0)
    )


def families_from_v6(base: dict) -> list[GeometryFamily]:
    return [
        GeometryFamily("v6_balanced_spiral", "spiral", base["turns"], base["inner_radius_m"], base["pitch_m"], base["channel_width_m"], 1.0, base.get("dean_scale", 0.42), base["dep_start_fraction"], base["dep_end_fraction"], 1.0, "Current V6 selected candidate."),
        GeometryFamily("short_smooth_spiral", "spiral", 4.8, 650e-6, 230e-6, 170e-6, 1.0, 0.65, 0.35, 0.88, 1.0, "Shorter smooth Archimedean spiral."),
        GeometryFamily("wide_low_heat_spiral", "spiral", 5.6, 850e-6, 260e-6, 230e-6, 1.0, 0.55, 0.35, 0.92, 1.0, "Wider channel to reduce electric field and heating."),
        GeometryFamily("compact_c_arc", "spiral", 1.35, 950e-6, 320e-6, 170e-6, 1.0, 0.35, 0.10, 0.95, 0.75, "C-shaped/circular-arc DEP path, short and compact."),
        GeometryFamily("same_length_serpentine", "straight", base["turns"], base["inner_radius_m"], base["pitch_m"], base["channel_width_m"], 1.0, 0.0, base["dep_start_fraction"], base["dep_end_fraction"], 0.45, "Same-length packed serpentine with no spiral Dean contribution."),
        GeometryFamily("short_serpentine", "straight", 4.8, 650e-6, 230e-6, 170e-6, 1.0, 0.0, 0.35, 0.88, 0.42, "Shorter packed straight/serpentine control."),
        GeometryFamily("stepwise_late_dep_spiral", "spiral", 6.2, 750e-6, 220e-6, 180e-6, 1.0, 0.85, 0.55, 0.96, 1.0, "Stepwise/multi-stage-inspired late DEP activation."),
        GeometryFamily("long_low_voltage_spiral", "spiral", 8.8, 900e-6, 245e-6, 220e-6, 1.0, 0.55, 0.48, 0.95, 1.0, "Longer path intended to reduce field intensity need."),
    ]


def run_screen(base: dict, families: list[GeometryFamily], field_stats) -> list[dict]:
    rng = np.random.default_rng(7007)
    rows = []
    sample_id = 0
    for family in families:
        for j in range(18):
            sample = apply_family(base, family, rng, jitter=j > 0)
            particles, summary, length_m = simulate_sample(
                sample,
                family,
                field_stats,
                seed=8000 + sample_id,
                particles_per_class=70,
                steps=240,
            )
            row = {
                "family": family.name,
                "sample_id": sample_id,
                "note": family.note,
                "frequency_hz": sample["frequency_hz"],
                "voltage_v": sample["voltage_v"],
                "velocity_um_s": sample["velocity_m_s"] * 1e6,
                "turns": sample["turns"],
                "inner_radius_um": sample["inner_radius_m"] * 1e6,
                "pitch_um": sample["pitch_m"] * 1e6,
                "channel_width_um": sample["channel_width_m"] * 1e6,
                "outlet_split_ratio": sample["outlet_split_ratio"],
                "inlet_offset_ratio": sample.get("inlet_offset_ratio", 0.0),
                "inlet_spread_ratio": sample.get("inlet_spread_ratio", 1.0),
                "dep_start_fraction": sample["dep_start_fraction"],
                "dep_end_fraction": sample["dep_end_fraction"],
                "dep_sign": sample.get("dep_sign", 1.0),
                "dean_scale": sample.get("dean_scale", family.dean_scale),
            }
            row.update(performance_metrics(particles, summary))
            row.update(feasibility_metrics(sample, length_m, family))
            row["v7_score"] = candidate_score(row)
            rows.append(row)
            sample_id += 1
    rows.sort(key=lambda row: row["v7_score"], reverse=True)
    return rows


def sample_from_row(row: dict) -> dict:
    return {
        "frequency_hz": row["frequency_hz"],
        "voltage_v": row["voltage_v"],
        "velocity_m_s": row["velocity_um_s"] * 1e-6,
        "turns": row["turns"],
        "inner_radius_m": row["inner_radius_um"] * 1e-6,
        "pitch_m": row["pitch_um"] * 1e-6,
        "channel_width_m": row["channel_width_um"] * 1e-6,
        "outlet_split_ratio": row["outlet_split_ratio"],
        "inlet_offset_ratio": row["inlet_offset_ratio"],
        "inlet_spread_ratio": row["inlet_spread_ratio"],
        "dep_start_fraction": row["dep_start_fraction"],
        "dep_end_fraction": row["dep_end_fraction"],
        "dep_sign": row["dep_sign"],
        "dean_scale": row["dean_scale"],
    }


def family_by_name(families: list[GeometryFamily]) -> dict[str, GeometryFamily]:
    return {family.name: family for family in families}


def validate_top(screen_rows: list[dict], families: list[GeometryFamily], field_stats) -> tuple[list[dict], list[dict]]:
    by_family = family_by_name(families)
    selected = []
    seen = set()
    for row in screen_rows:
        if row["family"] not in seen:
            selected.append(row)
            seen.add(row["family"])
        if len(selected) >= 6:
            break
    rows = []
    controls = []
    for rank, row in enumerate(selected):
        sample = sample_from_row(row)
        family = by_family[row["family"]]
        for seed in [9101, 9109, 9127, 9133]:
            particles, summary, length_m = simulate_sample(sample, family, field_stats, seed, 150, 320)
            out = {
                "family": family.name,
                "sample_id": int(row["sample_id"]),
                "rank": rank,
                "seed": seed,
            }
            out.update(performance_metrics(particles, summary))
            out.update(feasibility_metrics(sample, length_m, family))
            rows.append(out)

        for name, kwargs in [
            ("same_length_straight_dep", {"geometry_override": "straight", "dep_enabled": True}),
            ("no_dep", {"geometry_override": family.path_geometry, "dep_enabled": False}),
            ("unfocused_inlet", {"geometry_override": family.path_geometry, "dep_enabled": True, "inlet_override": (0.0, 1.0)}),
        ]:
            scores = []
            losses = []
            for seed in [9203, 9221]:
                particles, summary, length_m = simulate_sample(sample, family, field_stats, seed, 120, 280, **kwargs)
                perf = performance_metrics(particles, summary)
                scores.append(perf["target_correct"])
                losses.append(perf["wall_loss"])
            controls.append(
                {
                    "family": family.name,
                    "sample_id": int(row["sample_id"]),
                    "control": name,
                    "mean_target_correct": float(np.mean(scores)),
                    "mean_wall_loss": float(np.mean(losses)),
                }
            )
    return rows, controls


def aggregate_validation(rows: list[dict], controls: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, int], list[dict]] = {}
    for row in rows:
        grouped.setdefault((row["family"], int(row["sample_id"])), []).append(row)
    controls_by_key = {(row["family"], int(row["sample_id"]), row["control"]): row for row in controls}
    out = []
    for (family, sample_id), items in grouped.items():
        first = items[0]
        straight = controls_by_key[(family, sample_id, "same_length_straight_dep")]
        no_dep = controls_by_key[(family, sample_id, "no_dep")]
        unfocused = controls_by_key[(family, sample_id, "unfocused_inlet")]
        mean_correct = float(np.mean([r["target_correct"] for r in items]))
        row = {
            "family": family,
            "sample_id": sample_id,
            "mean_target_correct": mean_correct,
            "std_target_correct": float(np.std([r["target_correct"] for r in items], ddof=1)),
            "mean_wall_loss": float(np.mean([r["wall_loss"] for r in items])),
            "mean_live_recovery": float(np.mean([r["live_recovery"] for r in items])),
            "mean_dead_removal": float(np.mean([r["dead_removal"] for r in items])),
            "mean_live_outlet_purity": float(np.mean([r["live_outlet_purity"] for r in items])),
            "mean_dead_outlet_purity": float(np.mean([r["dead_outlet_purity"] for r in items])),
            "length_mm": first["length_mm"],
            "footprint_mm2": first["footprint_mm2"],
            "residence_s": first["residence_s"],
            "pressure_drop_kPa": first["pressure_drop_kPa"],
            "active_joule_power_mW": first["active_joule_power_mW"],
            "adiabatic_delta_c_proxy": first["adiabatic_delta_c_proxy"],
            "steady_substrate_delta_c_proxy": first["steady_substrate_delta_c_proxy"],
            "thermal_risk": first["thermal_risk"],
            "straight_control_correct": straight["mean_target_correct"],
            "no_dep_correct": no_dep["mean_target_correct"],
            "unfocused_inlet_correct": unfocused["mean_target_correct"],
            "topology_gain_vs_straight": mean_correct - straight["mean_target_correct"],
        }
        row["passes_v7_gate"] = (
            row["mean_target_correct"] >= 0.85
            and row["mean_wall_loss"] < 0.10
            and row["topology_gain_vs_straight"] >= 0.10
            and row["thermal_risk"] != "high"
        )
        out.append(row)
    out.sort(key=lambda r: (r["passes_v7_gate"], r["topology_gain_vs_straight"], r["mean_target_correct"]), reverse=True)
    return out


def plot_results(screen_rows: list[dict], validation: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 5))
    colors = {"low": "tab:green", "moderate": "tab:orange", "high": "tab:red"}
    for risk, color in colors.items():
        subset = [r for r in screen_rows if r["thermal_risk"] == risk]
        if subset:
            plt.scatter([r["active_joule_power_mW"] for r in subset], [r["target_correct"] for r in subset], s=22, alpha=0.75, label=risk, color=color)
    plt.axhline(0.85, color="black", linestyle="--", linewidth=1)
    plt.xlabel("Active Joule power proxy (mW)")
    plt.ylabel("Target correct")
    plt.legend(title="Thermal risk")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "v7_accuracy_vs_joule_power.png", dpi=180)
    plt.close()

    labels = [r["family"] for r in validation]
    x = np.arange(len(labels))
    plt.figure(figsize=(10, 5))
    plt.bar(x - 0.2, [r["mean_target_correct"] for r in validation], width=0.2, label="validated")
    plt.bar(x, [r["straight_control_correct"] for r in validation], width=0.2, label="straight control")
    plt.bar(x + 0.2, [r["no_dep_correct"] for r in validation], width=0.2, label="no DEP")
    plt.axhline(0.85, color="black", linestyle="--", linewidth=1)
    plt.xticks(x, labels, rotation=35, ha="right")
    plt.ylabel("Target correct")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "v7_validation_controls.png", dpi=180)
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.scatter([r["length_mm"] for r in validation], [r["mean_target_correct"] for r in validation], s=90)
    for r in validation:
        plt.annotate(r["family"], (r["length_mm"], r["mean_target_correct"]), fontsize=8)
    plt.axhline(0.85, color="black", linestyle="--", linewidth=1)
    plt.xlabel("Length (mm)")
    plt.ylabel("Validated target correct")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "v7_length_vs_validated_correct.png", dpi=180)
    plt.close()


def write_readme(validation: list[dict], screen_rows: list[dict]) -> None:
    best = validation[0]
    lines = [
        "# Design V7 Geometry Feasibility",
        "",
        "V7 compares geometry families using both separation metrics and device",
        "feasibility proxies. It is intentionally stricter than V6: high accuracy",
        "alone is not considered enough.",
        "",
        "## Best Current Candidate",
        "",
        f"- family: `{best['family']}`",
        f"- target correct: `{best['mean_target_correct']:.3f} +/- {best['std_target_correct']:.3f}`",
        f"- topology gain vs same-length straight DEP: `{best['topology_gain_vs_straight']:.3f}`",
        f"- wall loss: `{best['mean_wall_loss']:.3f}`",
        f"- live recovery: `{best['mean_live_recovery']:.3f}`",
        f"- dead removal: `{best['mean_dead_removal']:.3f}`",
        f"- live/dead outlet purity: `{best['mean_live_outlet_purity']:.3f}` / `{best['mean_dead_outlet_purity']:.3f}`",
        f"- length: `{best['length_mm']:.1f} mm`",
        f"- residence time: `{best['residence_s']:.1f} s`",
        f"- pressure drop proxy: `{best['pressure_drop_kPa']:.2f} kPa`",
        f"- active Joule power proxy: `{best['active_joule_power_mW']:.2f} mW`",
        f"- adiabatic temperature-rise proxy: `{best['adiabatic_delta_c_proxy']:.1f} C`",
        f"- steady substrate temperature-rise proxy: `{best['steady_substrate_delta_c_proxy']:.1f} C`",
        f"- thermal risk: `{best['thermal_risk']}`",
        f"- passes V7 gate: `{best['passes_v7_gate']}`",
        "",
        "## Interpretation",
        "",
        "Two thermal proxies are reported. The adiabatic proxy is a no-cooling",
        "upper-bound warning and should not be read as actual chip temperature.",
        "The steady substrate proxy assumes first-order heat loss through a 1 mm",
        "PDMS/glass support. A full thermal solve is still required before any",
        "experimental safety claim.",
        "",
        "## Literature/Device Comparison",
        "",
        "| Reference/device class | Reported strength | V7 use |",
        "|---|---|---|",
        "| Nguyen et al. 2024 facing-electrode DEP, Scientific Reports | numerical SE/purity, high-efficiency cell enrichment; also reports wall/voltage trade-offs | benchmark for reporting SE, purity, voltage and geometry factors |",
        "| Huang et al. 2025 ODEP live/dead | live recovery about 78.3%, live purity about 96.4% | live/dead experimental benchmark |",
        "| Elitas et al. 2017 3D carbon DEP live/dead | dead-cell removal around 90% | mammalian live/dead DEP parameter benchmark |",
        "| Circular OpenFOAM DEP, DOI 10.1016/j.apt.2023.104046 | public abstract reports 100% purity/efficiency in selected numerical cases | warning that deterministic DEP models can overstate performance |",
        "| Stepwise multi-stage DEP + microfilter, DOI 10.1016/j.talanta.2024.126585 | staged electrodes and microfilter improve stability/purity | inspiration for non-smooth, staged V8 geometries |",
        "",
        "## Files",
        "",
        "- `v7_screening_rows.csv`: all geometry-screening runs",
        "- `v7_validation_summary.csv`: held-out validation and controls",
        "- `v7_control_rows.csv`: same-length straight, no-DEP, and unfocused controls",
        "- `v7_accuracy_vs_joule_power.png`",
        "- `v7_validation_controls.png`",
        "- `v7_length_vs_validated_correct.png`",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_openfoam_case()
    field_stats = load_openfoam_field_stats()
    base = read_balanced_v6()
    families = families_from_v6(base)
    screen_rows = run_screen(base, families, field_stats)
    validation_rows, control_rows = validate_top(screen_rows, families, field_stats)
    validation_summary = aggregate_validation(validation_rows, control_rows)
    write_csv(screen_rows, OUT_DIR / "v7_screening_rows.csv")
    write_csv(validation_rows, OUT_DIR / "v7_validation_replicates.csv")
    write_csv(control_rows, OUT_DIR / "v7_control_rows.csv")
    write_csv(validation_summary, OUT_DIR / "v7_validation_summary.csv")
    plot_results(screen_rows, validation_summary)
    write_readme(validation_summary, screen_rows)
    print((OUT_DIR / "README.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
