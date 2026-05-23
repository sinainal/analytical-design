# Design V0 Trajectory Result

## Why This Was Generated

This result is the first live/dead particle-trajectory test for Design V0. It
uses the OpenFOAM-validated spiral geometry concept and the selected `455 kHz`
Clausius-Mossotti values, then applies a reduced-order DEP-plus-drift particle
model.

The goal is not to claim final device performance. The goal is to test whether
the design produces a measurable live/dead outlet bias before investing in a
full field-interpolated OpenFOAM particle workflow.

## Generator

Run from the repository root:

```bash
python3 scripts/design_v0_particle_tracking.py
```

## Outputs

| File | Purpose |
|---|---|
| `design_v0_trajectories.csv` | Raw particle trajectory table for live/dead classes. |
| `trajectory_summary.json` | Machine-readable outlet and lateral-position metrics. |
| `trajectory_summary.txt` | Human-readable result summary. |
| `design_v0_trajectory_plot.png` | Static trajectory plot. |
| `design_v0_trajectory_video.mp4` | Fixed-camera trajectory animation. |

## Main Result

- Live particles reaching inner outlet: `77 / 100`
- Dead particles reaching outer outlet: `58 / 100`
- Correct live-inner/dead-outer classification: `67.5%`
- Live mean final lateral position: `-16.41 um`
- Dead mean final lateral position: `3.00 um`

## Interpretation

The first reduced-order model shows a real outlet bias, but the result does not
yet meet the V0 target of at least `80%` correct classification. The system is
therefore functioning as a diagnostic model, not a final result.

## Limitation

The current model uses an analytical side-wall field-gradient proxy rather than
interpolating `grad(E^2)` from the OpenFOAM solution. The next version should
replace this proxy with field-derived electric forces and sweep voltage,
velocity, and turn count.

## 12-Case Sweep

An autonomous sweep was added in `sweep_12/`.

Best reduced-order candidate:

- `5 turns`
- `12 V`
- `1000 um/s`
- correct classification: `85.5%`
- live inner fraction: `100%`
- dead outer fraction: `71%`

The best candidate has a separate fixed-camera animation in
`best_sweep_case/design_v0_trajectory_video.mp4`.
