# Design V0 Particle Tracking Status

Date: 2026-05-24

## What Was Added

`scripts/design_v0_particle_tracking.py` adds the first live/dead trajectory
layer on top of the Design V0 spiral concept.

The animation uses a fixed camera. The spiral device does not rotate. Particles
move through the channel while the view remains stationary.

## Model Type

This is a reduced-order first-pass model.

Inputs:

- Design V0 Archimedean spiral dimensions.
- Selected frequency from the CM scan: about `455 kHz`.
- Live-cell `Re(CM)`: `0.976616`.
- Dead-cell `Re(CM)`: `-0.000044`.
- Inner side-wall electrode treated as the high-field side.
- 100 live particles and 100 dead particles.

Forces:

- spiral-aligned advective motion
- DEP lateral velocity proxy from `Re(CM) * grad(E^2)`
- small outward drift term representing first-pass curvature/Dean tendency

## Result

Generated outputs:

- `results/openfoam_design_v0/trajectories/design_v0_trajectories.csv`
- `results/openfoam_design_v0/trajectories/trajectory_summary.json`
- `results/openfoam_design_v0/trajectories/trajectory_summary.txt`
- `results/openfoam_design_v0/trajectories/design_v0_trajectory_plot.png`
- `results/openfoam_design_v0/trajectories/design_v0_trajectory_video.mp4`

Current metrics:

- live to inner outlet: `77 / 100`
- dead to outer outlet: `58 / 100`
- correct classification if live-inner/dead-outer: `67.5%`
- live mean final lateral position: `-16.41 um`
- dead mean final lateral position: `3.00 um`

## Interpretation

The first trajectory model produces separation bias, but it does not yet meet
the V0 success target of `>=80%` correct outlet classification.

This is useful because it tells us the current baseline is not publication-level
yet. The next design step should be optimization, not manuscript claiming.

## Next Step

Run a small sweep:

- voltage: `8, 10, 12 V`
- turns: `3, 5`
- inlet velocity: `1000, 3000 um/s`

Then choose a condition for the first OpenFOAM-field-interpolated trajectory
run.
