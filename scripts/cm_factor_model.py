#!/usr/bin/env python3
"""First-pass Clausius-Mossotti scan for live/dead cell DEP contrast."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np


EPS0 = 8.8541878128e-12
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "cm_factor"


@dataclass(frozen=True)
class CellModel:
    name: str
    radius_m: float
    membrane_thickness_m: float
    membrane_eps_r: float
    membrane_sigma_s_m: float
    cytoplasm_eps_r: float
    cytoplasm_sigma_s_m: float


MEDIUM_EPS_R = 80.0
MEDIUM_SIGMA_S_M = 0.002

LIVE = CellModel(
    name="live",
    radius_m=11.5e-6,
    membrane_thickness_m=7e-9,
    membrane_eps_r=12.5,
    membrane_sigma_s_m=1e-6,
    cytoplasm_eps_r=50.0,
    cytoplasm_sigma_s_m=0.5,
)

DEAD = CellModel(
    name="dead",
    radius_m=11.0e-6,
    membrane_thickness_m=7e-9,
    membrane_eps_r=12.5,
    membrane_sigma_s_m=0.01,
    cytoplasm_eps_r=80.0,
    cytoplasm_sigma_s_m=0.002,
)


def complex_permittivity(eps_r: float, sigma: float, omega: np.ndarray) -> np.ndarray:
    return EPS0 * eps_r - 1j * sigma / omega


def shelled_cell_effective_permittivity(
    cell: CellModel, omega: np.ndarray
) -> np.ndarray:
    eps_mem = complex_permittivity(
        cell.membrane_eps_r, cell.membrane_sigma_s_m, omega
    )
    eps_cyto = complex_permittivity(
        cell.cytoplasm_eps_r, cell.cytoplasm_sigma_s_m, omega
    )
    membrane_capacitance = eps_mem / cell.membrane_thickness_m
    return (
        membrane_capacitance
        * cell.radius_m
        * eps_cyto
        / (membrane_capacitance * cell.radius_m + eps_cyto)
    )


def cm_factor(cell: CellModel, frequency_hz: np.ndarray) -> np.ndarray:
    omega = 2.0 * math.pi * frequency_hz
    eps_medium = complex_permittivity(MEDIUM_EPS_R, MEDIUM_SIGMA_S_M, omega)
    eps_cell = shelled_cell_effective_permittivity(cell, omega)
    return (eps_cell - eps_medium) / (eps_cell + 2.0 * eps_medium)


def write_csv(
    path: Path,
    frequency_hz: np.ndarray,
    live_re: np.ndarray,
    dead_re: np.ndarray,
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            ["frequency_hz", "live_re_cm", "dead_re_cm", "dead_minus_live"]
        )
        for freq, live_value, dead_value in zip(frequency_hz, live_re, dead_re):
            writer.writerow([f"{freq:.8g}", live_value, dead_value, dead_value - live_value])


def write_plot(
    path: Path,
    frequency_hz: np.ndarray,
    live_re: np.ndarray,
    dead_re: np.ndarray,
    selected_frequency_hz: float,
) -> bool:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    plt.figure(figsize=(8, 5))
    plt.semilogx(frequency_hz, live_re, label="Live cell Re(CM)", linewidth=2)
    plt.semilogx(frequency_hz, dead_re, label="Dead cell Re(CM)", linewidth=2)
    plt.axvline(
        selected_frequency_hz,
        color="black",
        linestyle="--",
        linewidth=1,
        label=f"Selected {selected_frequency_hz:,.0f} Hz",
    )
    plt.axhline(0, color="0.5", linewidth=0.8)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Real Clausius-Mossotti factor")
    plt.title("Design V0 live/dead DEP contrast scan")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    return True


def dep_regime(value: float) -> str:
    if value > 1e-3:
        return "positive DEP"
    if value < -1e-3:
        return "negative DEP"
    return "near-zero DEP"


def interpretation(live_value: float, dead_value: float) -> str:
    live_regime = dep_regime(live_value)
    dead_regime = dep_regime(dead_value)
    if live_regime != dead_regime:
        return (
            f"Live cells are in {live_regime} while dead cells are in {dead_regime}; "
            "this is a useful first-pass operating point for lateral DEP biasing."
        )
    return (
        f"Both cell states are in {live_regime}; the design must rely on "
        "force-magnitude contrast or refined medium/cell parameters."
    )


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    frequency_hz = np.logspace(3, 7, 800)
    live_re = np.real(cm_factor(LIVE, frequency_hz))
    dead_re = np.real(cm_factor(DEAD, frequency_hz))
    contrast = dead_re - live_re
    best_idx = int(np.argmax(np.abs(contrast)))

    selected_frequency_hz = float(frequency_hz[best_idx])
    selected_live = float(live_re[best_idx])
    selected_dead = float(dead_re[best_idx])
    selected_delta = float(contrast[best_idx])

    csv_path = OUT_DIR / "design_v0_cm_factor.csv"
    summary_path = OUT_DIR / "design_v0_cm_summary.txt"
    plot_path = OUT_DIR / "design_v0_cm_factor.png"

    write_csv(csv_path, frequency_hz, live_re, dead_re)
    plot_written = write_plot(
        plot_path, frequency_hz, live_re, dead_re, selected_frequency_hz
    )

    summary = "\n".join(
        [
            "Design V0 Clausius-Mossotti scan",
            "==================================",
            "",
            f"Medium conductivity: {MEDIUM_SIGMA_S_M:g} S/m",
            f"Frequency scan: {frequency_hz[0]:.0f} Hz to {frequency_hz[-1]:.0f} Hz",
            "",
            "Selected point: maximum |dead Re(CM) - live Re(CM)|",
            f"Selected frequency: {selected_frequency_hz:.6g} Hz",
            f"Live Re(CM): {selected_live:.6f}",
            f"Dead Re(CM): {selected_dead:.6f}",
            f"Dead - live contrast: {selected_delta:.6f}",
            "",
            "Interpretation:",
            interpretation(selected_live, selected_dead),
            "",
            f"CSV: {csv_path.relative_to(ROOT)}",
            f"Plot: {plot_path.relative_to(ROOT) if plot_written else 'not generated'}",
        ]
    )
    summary_path.write_text(summary + "\n", encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
