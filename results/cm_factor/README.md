# CM Factor Result: Design V0

## Why This Was Generated

Before building an OpenFOAM spiral case, the project needs a defensible
frequency choice for live/dead DEP contrast. This result scans the real
Clausius-Mossotti factor for the first mammalian live/dead cell parameter set.

## Generator

Run from the repository root:

```bash
python3 scripts/cm_factor_model.py
```

## Outputs

| File | Purpose |
|---|---|
| `design_v0_cm_factor.csv` | Frequency, live `Re(CM)`, dead `Re(CM)`, and contrast values. |
| `design_v0_cm_summary.txt` | Human-readable selected frequency and interpretation. |
| `design_v0_cm_factor.png` | Manuscript-candidate plot for the first design study. |

## Main Finding

The strongest current-model contrast occurs near `455 kHz`:

- live cell `Re(CM) = 0.976616`
- dead cell `Re(CM) = -0.000044`

This indicates strong positive DEP for live cells and near-neutral DEP for dead
cells under the first parameter set.

## Manuscript Use

This plot can support the methods/results sequence:

1. Literature-derived live/dead dielectric parameters.
2. Frequency-domain DEP contrast check.
3. Selected frequency for spiral OpenFOAM-backed trajectory simulations.

## Limitation

This is an analytical electrical-property scan only. It does not include
spiral-channel flow, electrode geometry, electric-field gradients, particle
trajectories, Joule heating, or AC electrothermal flow.
