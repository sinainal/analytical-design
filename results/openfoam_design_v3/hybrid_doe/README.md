# Design V3 OpenFOAM Hybrid DOE

V3 uses the existing OpenFOAM spiral electric-potential solve as the
device-field anchor, then runs a stochastic finite-size population model.

This is not a deformable-cell solver. It is a computationally cheap
optimization layer intended to be validated later with a heavier model
or experiments.

## OpenFOAM Field Anchor

- OpenFOAM case: `cases/design_v0`
- parsed field cells: `3840`
- mean |grad(phi)|: `6.67e+04`
- p95 |grad(phi)|: `6.97e+04`
- max |grad(phi)|: `7.03e+04`

## V3 Improvements Over V2

- finite cell radius and 3D inlet z-position
- Poiseuille-like axial velocity instead of constant residence time
- Brownian lateral perturbation
- stochastic adhesion/wall-loss after wall contact
- voltage-dependent over-deflection risk through wall loss
- design/validation seed split retained
- multiple metrics retained: recovery, removal, purity, wall loss

## Selected By Design, Checked On Validation

- case: `turns_3.5_voltage_7_velocity_2600um_s`
- validation correct: `0.459`
- validation live recovery: `0.320`
- validation dead removal: `0.598`
- validation wall loss: `0.099`

## Best Validation Condition

- case: `turns_3.5_voltage_7_velocity_2600um_s`
- validation correct: `0.459`
- validation live recovery: `0.320`
- validation dead removal: `0.598`
- validation live purity: `0.481`
- validation dead outlet purity: `0.526`
- validation wall loss: `0.099`

## Top Validation Conditions

| Rank | Case | Correct | Live recovery | Dead removal | Live purity | Wall loss |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `turns_3.5_voltage_7_velocity_2600um_s` | 0.459 | 0.320 | 0.598 | 0.481 | 0.099 |
| 2 | `turns_4.5_voltage_7_velocity_2600um_s` | 0.444 | 0.309 | 0.580 | 0.492 | 0.144 |
| 3 | `turns_3.5_voltage_7_velocity_1800um_s` | 0.435 | 0.280 | 0.591 | 0.436 | 0.128 |
| 4 | `turns_3.5_voltage_9_velocity_2600um_s` | 0.427 | 0.270 | 0.583 | 0.436 | 0.134 |
| 5 | `turns_4.5_voltage_7_velocity_1800um_s` | 0.424 | 0.250 | 0.598 | 0.449 | 0.155 |
| 6 | `turns_3.5_voltage_7_velocity_1200um_s` | 0.420 | 0.244 | 0.596 | 0.408 | 0.131 |
| 7 | `turns_4.5_voltage_9_velocity_2600um_s` | 0.414 | 0.248 | 0.580 | 0.440 | 0.185 |
| 8 | `turns_3.5_voltage_9_velocity_1800um_s` | 0.412 | 0.224 | 0.600 | 0.397 | 0.159 |
| 9 | `turns_5.5_voltage_7_velocity_2600um_s` | 0.400 | 0.237 | 0.563 | 0.448 | 0.188 |
| 10 | `turns_3.5_voltage_13_velocity_2600um_s` | 0.391 | 0.183 | 0.598 | 0.352 | 0.203 |
| 11 | `turns_3.5_voltage_11_velocity_1800um_s` | 0.390 | 0.211 | 0.569 | 0.384 | 0.209 |
| 12 | `turns_4.5_voltage_9_velocity_1800um_s` | 0.384 | 0.187 | 0.581 | 0.374 | 0.220 |

## Honest Limitations

- It does not solve two-way fluid-cell coupling.
- It does not deform cells.
- It uses OpenFOAM field statistics, not full 3D interpolation at each point yet.
- The next V4 step should sample `grad(|E|^2)` directly from cell centers or a VTK export.
