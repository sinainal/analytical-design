# Design V1 DOE

Design V1 runs a 27-condition, 5-seed DOE over the first three
optimization parameters: turn count, voltage, and inlet velocity.

## Targets

- screening target: `>= 80%` correct classification
- publication-level target: mean `>= 90%` and minimum seed result `>= 90%`

## Best Robust Condition

- case: `turns_5_voltage_12_velocity_1000um_s`
- mean correct: `0.863`
- std correct: `0.007`
- min correct across seeds: `0.855`
- robust target status: `not yet pass`

## Top Conditions

| Rank | Case | Mean | Std | Min | Live inner | Dead outer |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `turns_5_voltage_12_velocity_1000um_s` | 0.863 | 0.007 | 0.855 | 0.990 | 0.736 |
| 2 | `turns_5_voltage_10_velocity_1000um_s` | 0.846 | 0.013 | 0.825 | 0.956 | 0.736 |
| 3 | `turns_4_voltage_12_velocity_1000um_s` | 0.825 | 0.014 | 0.810 | 0.970 | 0.680 |
| 4 | `turns_4_voltage_10_velocity_1000um_s` | 0.799 | 0.022 | 0.780 | 0.918 | 0.680 |
| 5 | `turns_3_voltage_12_velocity_1000um_s` | 0.785 | 0.012 | 0.775 | 0.938 | 0.632 |
| 6 | `turns_5_voltage_8_velocity_1000um_s` | 0.790 | 0.020 | 0.760 | 0.844 | 0.736 |
| 7 | `turns_5_voltage_12_velocity_2000um_s` | 0.774 | 0.016 | 0.755 | 0.922 | 0.626 |
| 8 | `turns_3_voltage_10_velocity_1000um_s` | 0.738 | 0.014 | 0.725 | 0.844 | 0.632 |
| 9 | `turns_4_voltage_12_velocity_2000um_s` | 0.736 | 0.013 | 0.725 | 0.868 | 0.604 |
| 10 | `turns_4_voltage_8_velocity_1000um_s` | 0.741 | 0.020 | 0.720 | 0.802 | 0.680 |

## ParaView Outputs

- `../paraview/best_case_trajectories.vtp`: all best-case trajectory lines
- `../paraview/best_case_particles.pvd`: time-resolved fixed-camera particle animation source

These files can be opened directly in ParaView.
