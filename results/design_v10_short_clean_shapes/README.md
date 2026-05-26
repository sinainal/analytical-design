# Design V10 Short Clean Shapes

V10 screens short, symmetric or deliberately clean formula-defined microfluidic shapes.
No random free-form curves are used.

## Shape Families
- `circular_archimedean_short`: `r(theta)=a+b theta`. Clean compact Archimedean reference.
- `elliptic_archimedean_short`: `x=(a+b theta) cos(theta), y=e(a+b theta) sin(theta)`. Symmetric elliptical spiral; tests whether anisotropic curvature helps shorten the channel.
- `monotone_curvature_spiral`: `r(theta)=r0/(1+k theta)^p`. Curvature increases smoothly along the path instead of adding arbitrary waves.
- `elliptic_prefocus_spiral`: `straight inlet + x=(a+b theta) cos(theta), y=e(a+b theta) sin(theta)`. Explicit inlet-focusing segment followed by an elliptical spiral.
- `superellipse_oval_spiral`: `x=r sign(cos(theta))|cos(theta)|^q, y=e r sign(sin(theta))|sin(theta)|^q`. Smooth oval/stadium-like compact spiral, not a random curve.
- `concentric_electrode_spiral`: `r(theta)=a+b theta with constant electrode gap g`. Closest clean abstraction of the reference-style concentric-electrode spiral.

## Best Candidate

- family: `monotone_curvature_spiral`
- equation: `r(theta)=r0/(1+k theta)^p`
- inlet kind: `outer_low_curvature_entry`
- target correct: `0.953 +/- 0.013`
- topology gain vs same-length straight DEP: `0.374`
- length: `9.1 mm`
- residence time: `7.78 s`
- wall loss: `0.000`
- active Joule power proxy: `8.22 mW`
- steady substrate temp-rise proxy: `10.55 C`
- manufacturable gap ok: `True`
- manufacturable bend ok: `True`
- passes V10 gate: `True`

## Academic Improvements Over V9

- Shape parameters are named physical variables: eccentricity, monotone curvature power, inlet length, electrode gap, and electrode coverage.
- Short-channel screening is explicit; the pass gate requires length <= 20 mm.
- The same-length straight DEP, no-DEP, and unfocused-inlet controls are reported for each finalist.
- Manufacturability proxies include minimum bend radius and minimum electrode gap.
- Thermal and pressure proxies are recorded for ranking, not hidden.

## Stored Shape Data

Top candidates are saved as `rank*_formula.json` and `rank*_centerline.csv` files.

## Honest Limitation

DEP is still represented by a reduced-order electrode-gap field-gain proxy. The selected V10 geometry should be rebuilt with an electrode-resolved field solve before a final device claim.

## Best Formula Parameters

```json
{
  "family": "monotone_curvature_spiral",
  "equation": "r(theta)=r0/(1+k theta)^p",
  "shape_class": "monotone_curvature_spiral",
  "inlet_kind": "outer_low_curvature_entry",
  "frequency_hz": 1042590.8728057459,
  "voltage_v": 18.810081267852933,
  "velocity_m_s": 0.0011762560753614808,
  "turns": 1.7857538358587857,
  "radius_m": 0.001076692597705587,
  "pitch_m_per_rad": 1.9661924658286767e-05,
  "channel_width_m": 0.0001043108772156677,
  "eccentricity": 1.0,
  "curvature_power": 1.326822841770499,
  "inlet_length_m": 0.0004153955856670296,
  "outlet_split_ratio": 0.5274213444009215,
  "inlet_offset_ratio": -0.7055222736503389,
  "inlet_spread_ratio": 0.38208954060500677,
  "dep_start_fraction": 0.2752116514959491,
  "dep_end_fraction": 0.9117126008749034,
  "dep_edge_smoothness": 0.042767678064083776,
  "electrode_gap_m": 5.598634471608172e-05,
  "electrode_coverage": 0.6407190136129008,
  "field_gain": 1.0995464242508084,
  "dep_sign": -1.0,
  "dean_base": 1.0497539269351188,
  "note": "Curvature increases smoothly along the path instead of adding arbitrary waves.",
  "dean_scale": 1.732093979442946
}
```
