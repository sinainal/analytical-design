# Design V4 Model Realism

V4 adds frequency-dependent live/dead CM response, outlet split ratio,
and two outlet-label conventions:

- `correct_A`: live to inner outlet, dead to outer outlet
- `correct_B`: live to outer outlet, dead to inner outlet

The reported target is `max(correct_A, correct_B)` so the model can reveal
whether the physical separation direction is reversed.

## Best Quick Condition

- case: `spiral_dep_1_sign_1_f_455.326kHz_V_7_u_2600_split_0.45`
- target correct: `0.529`
- preferred direction: `A_live_inner_dead_outer`
- correct A: `0.529`
- correct B: `0.400`
- wall loss: `0.071`
- distribution gap: `6.887 um`

## Interpretation

If both correct values stay near 0.5 and the distribution gap is small,
the current design is not separating live/dead populations strongly. If
`correct_B` exceeds `correct_A`, the outlet labeling assumption is reversed.
