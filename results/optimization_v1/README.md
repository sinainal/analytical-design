# Optimization V1

Surrogate-assisted optimization for live/dead separation. The objective
does not include spiral synergy; synergy is checked after selection.

## Wall Loss

`wall_loss` is the fraction of cells that hit/stick to the wall before
reaching an outlet. It is penalized because a high-correct design that
loses many cells is not a useful separation device.

## Best Validated Candidate

- stage: `segmented_spiral`
- sample id: `129`
- target correct: `0.999`
- validation std: `0.002`
- wall loss: `0.001`
- preferred direction: `B_live_outer_dead_inner`
- frequency: `988.1 kHz`
- voltage: `17.87 V`
- flow velocity: `3311 um/s`
- turns: `3.80`
- inner radius: `533.0 um`
- pitch: `301.3 um`
- channel width: `77.6 um`
- outlet split ratio: `0.411`
- inlet offset ratio: `-0.667`
- inlet spread ratio: `0.176`
- DEP active segment: `0.120` to `0.640`
- Dean scale: `0.558`
- DEP sign: `-1`

## Spiral Synergy Check

- spiral DEP on: `0.997`
- same-length straight DEP on: `0.934`
- spiral flow only: `0.503`
- synergy score: `0.062`

## Interpretation

If target correct remains below 0.8, the current physics/topology model
does not yet support the desired separation. If target correct exceeds
0.8 but synergy is weak, the design may be separating because of long
residence time or inlet focusing rather than spiral-specific benefit.

Total runtime recorded by the script: `2.0 min`.
