# Design V6 Optimization Setup

This is the fast optimization handoff. It uses Latin hypercube sampling
for broad coverage and validates the top five quick candidates with
three seeds.

## Scope

- quick samples: `48`
- quick particles: `60 live + 60 dead`
- validation particles: `80 live + 80 dead`
- validation seeds: `[101, 103, 107]`

## Optimization Variables

- `frequency_hz`: `50000` to `2e+06`
- `voltage_v`: `4` to `18`
- `velocity_m_s`: `0.0006` to `0.0045`
- `turns`: `2.5` to `7`
- `pitch_m`: `0.00012` to `0.00032`
- `channel_width_m`: `7e-05` to `0.00018`
- `outlet_split_ratio`: `0.35` to `0.65`

## Best Quick Candidate

- sample id: `46`
- target correct: `0.583`
- wall loss: `0.042`
- preferred direction: `A_live_inner_dead_outer`

## Best Validated Candidate

- sample id: `2`
- validation target correct: `0.546`
- validation std: `0.058`
- validation wall loss: `0.033`
- preferred direction: `B_live_outer_dead_inner`

## Next Run

For the real 20-30 minute run, increase quick samples to 150-200 and
validate the top 10. This script is intentionally configured as a
small smoke test first.
