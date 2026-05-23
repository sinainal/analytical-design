# Design V0 Sweep Status

Date: 2026-05-24

## What Was Asked

Run an autonomous multi-experiment plan instead of manually checking one
simulation at a time.

## What Was Run

`scripts/design_v0_sweep.py` ran a 12-case reduced-order trajectory sweep:

- turns: `3`, `5`
- voltage: `8`, `10`, `12 V`
- inlet velocity: `1000`, `3000 um/s`
- particles per class: `100`

The sweep is still reduced-order. It does not yet interpolate the DEP force from
OpenFOAM `grad(E^2)`. It is meant to identify the best next OpenFOAM-backed
candidate.

## Best Candidate

Best case:

- turns: `5`
- voltage: `12 V`
- inlet velocity: `1000 um/s`
- correct classification: `85.5%`
- live inner outlet fraction: `100%`
- dead outer outlet fraction: `71%`

This passes the preliminary V0 target of `>=80%` correct classification in the
reduced-order model.

## Important Interpretation

The sweep supports two expected trends:

1. More turns improve separation by increasing residence time.
2. Higher velocity weakens separation by reducing field exposure time.

This is parallel to the spiral DEP literature logic: longer spiral interaction
length can reduce the effective voltage burden, but higher flow speed requires
stronger DEP forcing.

## Caveat

The cell model uses literature-derived dielectric parameters and a
single-shell CM-factor estimate. It is a reasonable first model, but it is not
yet final validation. The next quality jump is to replace the analytical field
proxy with field data from the OpenFOAM potential solution.

## Generated Outputs

- `results/openfoam_design_v0/trajectories/sweep_12/sweep_results.csv`
- `results/openfoam_design_v0/trajectories/sweep_12/sweep_correct_fraction.png`
- `results/openfoam_design_v0/trajectories/sweep_12/README.md`
- `results/openfoam_design_v0/trajectories/best_sweep_case/design_v0_trajectory_video.mp4`

## Next Step

Use the best case, `5 turns / 12 V / 1000 um/s`, for the first
OpenFOAM-field-interpolated trajectory model.
