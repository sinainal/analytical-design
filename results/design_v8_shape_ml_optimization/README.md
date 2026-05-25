# Design V8 Shape ML Optimization

V8 searches across non-identical geometry families and explicitly rewards
short-channel separation. The final reported candidates are not ML
predictions; they are held-out reduced-order particle simulations selected
after surrogate triage.

## How ML Was Used

1. A real simulation set was generated with Latin/random samples across
   shape family, voltage, velocity, width, DEP segment, field-gain proxy,
   and geometry dimensions.
2. An ExtraTreesRegressor learned `v8_score`, a multi-objective score that
   includes target correct, short-channel score, wall loss, channel length,
   Joule-power proxy, and thermal-risk penalty.
3. The surrogate ranked thousands of virtual candidates.
4. The selected candidates were re-run with the particle model, then the
   finalists were validated on held-out seeds and controls.

ML did not generate final metrics directly and was not trained on the
held-out validation seeds.

## Best Current Candidate

- family: `asymmetric_c_spiral`
- target correct: `0.957 +/- 0.006`
- short-channel score: `0.0418` per mm
- topology gain vs same-length straight DEP: `0.129`
- wall loss: `0.000`
- live recovery: `0.997`
- dead removal: `0.916`
- live/dead outlet purity: `0.922` / `0.997`
- length: `10.9 mm`
- residence time: `3.9 s`
- pressure drop proxy: `0.19 kPa`
- active Joule power proxy: `3.34 mW`
- steady substrate temperature-rise proxy: `3.67 C`
- thermal risk: `low`
- passes V8 gate: `True`

## Important Limitation

The `field_gain` term is a reduced-order electrode-concentration proxy. It
represents shaped/facing/pinched electrode regions, not a solved 3D
electric-field map. V8 is stronger than V7 for design triage, but final
claims still require electrode-resolved OpenFOAM or FEM field solutions.

## Files

- `v8_validation_summary.csv`
- `v8_control_rows.csv`
- `v8_screening_rows.csv`
- `v8_screen_accuracy_vs_length.png`
- `v8_validation_controls.png`
- `v8_finalist_metric_heatmap.png`
- `v8_short_channel_vs_power.png`
- `v8_ml_feature_importance.png`
- `v8_geometry_family_gallery.png`
- `v8_best_professional_animation.mp4`
- `v8_best_professional_still.png`
