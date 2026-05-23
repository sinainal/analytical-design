# Design V2 Population DOE

V2 samples cell diameter, dielectric properties, and inlet positions.
It separates design seeds from validation seeds and reports recovery,
purity, dead-cell removal, and wall loss.

## DOE Grid

- turns: `4, 5, 6`
- voltage: `8, 9, 10, 11, 12, 13, 14 V`
- velocity: `800, 1000, 1500, 2000, 3000 um/s`
- design seeds: `[7, 11, 13]`
- validation seeds: `[101, 103, 107]`
- particles per class per replicate: `150`

## Selected By Design Seeds

- case: `turns_4_voltage_8_velocity_3000um_s`
- design mean correct: `0.448`
- validation mean correct: `0.429`
- validation live recovery: `0.342`
- validation dead removal: `0.516`
- validation live purity: `0.451`
- validation wall loss: `0.109`

## Best By Validation

- case: `turns_4_voltage_8_velocity_3000um_s`
- validation mean correct: `0.429`
- validation live recovery: `0.342`
- validation dead removal: `0.516`
- validation live purity: `0.451`
- validation dead outlet purity: `0.503`
- validation wall loss: `0.109`

## Top Validation Conditions

| Rank | Case | Correct | Live recovery | Dead removal | Live purity | Wall loss |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `turns_4_voltage_8_velocity_3000um_s` | 0.429 | 0.342 | 0.516 | 0.451 | 0.109 |
| 2 | `turns_4_voltage_9_velocity_3000um_s` | 0.409 | 0.304 | 0.513 | 0.421 | 0.131 |
| 3 | `turns_5_voltage_8_velocity_3000um_s` | 0.406 | 0.316 | 0.496 | 0.438 | 0.147 |
| 4 | `turns_4_voltage_10_velocity_2000um_s` | 0.394 | 0.273 | 0.516 | 0.391 | 0.177 |
| 5 | `turns_6_voltage_8_velocity_3000um_s` | 0.393 | 0.264 | 0.522 | 0.431 | 0.196 |
| 6 | `turns_4_voltage_8_velocity_2000um_s` | 0.393 | 0.278 | 0.509 | 0.393 | 0.152 |
| 7 | `turns_4_voltage_12_velocity_3000um_s` | 0.393 | 0.278 | 0.509 | 0.397 | 0.182 |
| 8 | `turns_4_voltage_8_velocity_1500um_s` | 0.392 | 0.276 | 0.509 | 0.390 | 0.169 |
| 9 | `turns_4_voltage_8_velocity_1000um_s` | 0.392 | 0.273 | 0.511 | 0.385 | 0.196 |
| 10 | `turns_4_voltage_10_velocity_3000um_s` | 0.391 | 0.273 | 0.509 | 0.393 | 0.158 |
| 11 | `turns_4_voltage_9_velocity_1500um_s` | 0.391 | 0.271 | 0.511 | 0.386 | 0.181 |
| 12 | `turns_4_voltage_9_velocity_2000um_s` | 0.391 | 0.269 | 0.513 | 0.387 | 0.173 |

## Interpretation

V2 is intentionally harder than V1. High voltage and long residence
time can now create wall loss, and cell-property distributions can
weaken apparently clean deterministic separation.

The next step is replacing the analytical field-gradient proxy with
OpenFOAM-interpolated `grad(E^2)` for the best validation condition.
