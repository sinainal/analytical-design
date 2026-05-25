# V6 Post-hoc Validation

These checks deliberately try to break the optimized design. They are
not part of the surrogate objective and use held-out random seeds.

## Optimized Candidate

- source stage: `segmented_spiral`
- target correct in optimizer validation: `0.999`
- voltage: `17.87 V`
- frequency: `988.1 kHz`
- flow velocity: `3311 um/s`
- turns: `3.80`
- channel width: `77.6 um`
- inlet offset/spread: `-0.667` / `0.176`
- DEP segment: `0.120` to `0.640`

## Key Results

- nominal held-out target correct: `0.999` +/- `0.002`
- tolerance-perturbed target correct: `0.920` +/- `0.127`
- same-length straight DEP target correct: `0.937`
- spiral without DEP target correct: `0.501`
- spiral DEP with unfocused inlet target correct: `0.502`

## Interpretation

The design passes the >0.8 target under the nominal reduced-order model.
However, the same-length straight DEP control is also high, so the spiral
is not yet the dominant mechanism. The current honest claim is: segmented
DEP plus focused inlet gives strong separation, while the spiral gives a
measurable but secondary improvement. This should be strengthened in the
next design version by optimizing spiral-specific geometry or by reporting
the spiral as a compact residence-time and Dean-flow aid rather than the
sole separator.
