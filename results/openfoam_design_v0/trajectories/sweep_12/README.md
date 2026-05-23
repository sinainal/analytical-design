# Design V0 12-Case Sweep

This sweep tests the reduced-order live/dead trajectory model across
turn count, voltage, and inlet velocity. It is a planning/diagnostic
sweep, not a final OpenFOAM field-interpolated particle result.

## Sweep Grid

- turns: `3`, `5`
- voltage: `8`, `10`, `12 V`
- inlet velocity: `1000`, `3000 um/s`
- particles per class: `100`

## Best Case

- case: `turns_5_voltage_12_velocity_1000um_s`
- correct classification: `0.855`
- live inner fraction: `1.000`
- dead outer fraction: `0.710`

## Results

| Case | Correct | Live inner | Dead outer |
|---|---:|---:|---:|
| `turns_5_voltage_12_velocity_1000um_s` | 0.855 | 1.000 | 0.710 |
| `turns_5_voltage_10_velocity_1000um_s` | 0.850 | 0.990 | 0.710 |
| `turns_5_voltage_8_velocity_1000um_s` | 0.805 | 0.900 | 0.710 |
| `turns_3_voltage_12_velocity_1000um_s` | 0.775 | 0.970 | 0.580 |
| `turns_3_voltage_10_velocity_1000um_s` | 0.740 | 0.900 | 0.580 |
| `turns_5_voltage_12_velocity_3000um_s` | 0.725 | 0.900 | 0.550 |
| `turns_5_voltage_10_velocity_3000um_s` | 0.680 | 0.810 | 0.550 |
| `turns_3_voltage_8_velocity_1000um_s` | 0.675 | 0.770 | 0.580 |
| `turns_5_voltage_8_velocity_3000um_s` | 0.655 | 0.760 | 0.550 |
| `turns_3_voltage_12_velocity_3000um_s` | 0.625 | 0.770 | 0.480 |
| `turns_3_voltage_10_velocity_3000um_s` | 0.620 | 0.760 | 0.480 |
| `turns_3_voltage_8_velocity_3000um_s` | 0.595 | 0.710 | 0.480 |

## Interpretation

Cases above `0.8` correct classification are candidates for the next
OpenFOAM field-interpolated trajectory run. Cases below that threshold
still provide useful diagnostics for sensitivity to voltage, residence
time, and flow speed.
