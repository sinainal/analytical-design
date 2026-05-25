# Design V5 Spiral/DEP Ablation

This study asks whether the spiral contributes more than residence time.
The straight-channel cases use the same path length in the reduced model.

## Main Scores

- spiral DEP on: `0.469`
- straight DEP on: `0.498`
- spiral flow only: `0.492`
- straight flow only: `0.531`
- DEP gain in spiral: `-0.023`
- spiral gain over same-length straight DEP: `-0.029`
- same-length DEP gain: `-0.033`
- synergy score: `-0.029`

## Interpretation Rule

`synergy_score > 0` supports spiral+DEP synergy. If it is near zero or
negative, the current spiral is not yet doing more than a straight
same-length DEP channel.

## Summary Table

| Condition | Target correct | Correct A | Correct B | Wall loss | Gap um |
|---|---:|---:|---:|---:|---:|
| `straight_flow_only` | 0.531 | 0.531 | 0.469 | 0.000 | 4.941 |
| `spiral_dep_reversed` | 0.508 | 0.452 | 0.504 | 0.044 | 3.775 |
| `straight_dep_on` | 0.498 | 0.440 | 0.498 | 0.062 | 3.531 |
| `spiral_flow_only` | 0.492 | 0.467 | 0.456 | 0.077 | 3.054 |
| `spiral_dep_on` | 0.469 | 0.438 | 0.454 | 0.108 | 4.492 |
