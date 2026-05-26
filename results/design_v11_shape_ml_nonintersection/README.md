# Design V11 Shape ML Non-Intersection Screening

V11 screens more short, symmetric or deliberately clean formula-defined microfluidic shapes.
No random free-form curves are used, and self-intersecting or overlapping centerlines are rejected before simulation.

## Shape Families
- `circular_archimedean_short`: `r(theta)=a+b theta`. Clean compact Archimedean reference.
- `elliptic_archimedean_short`: `x=(a+b theta) cos(theta), y=e(a+b theta) sin(theta)`. Symmetric elliptical spiral; tests whether anisotropic curvature helps shorten the channel.
- `monotone_curvature_spiral`: `r(theta)=r0/(1+k theta)^p`. Curvature increases smoothly along the path instead of adding arbitrary waves.
- `elliptic_prefocus_spiral`: `straight inlet + x=(a+b theta) cos(theta), y=e(a+b theta) sin(theta)`. Explicit inlet-focusing segment followed by an elliptical spiral.
- `superellipse_oval_spiral`: `x=r sign(cos(theta))|cos(theta)|^q, y=e r sign(sin(theta))|sin(theta)|^q`. Smooth oval/stadium-like compact spiral, not a random curve.
- `concentric_electrode_spiral`: `r(theta)=a+b theta with constant electrode gap g`. Closest clean abstraction of the reference-style concentric-electrode spiral.
- `logarithmic_spiral_short`: `r(theta)=a exp(k theta)`. Smooth logarithmic spiral; constant growth ratio rather than arbitrary modulation.
- `elliptic_logarithmic_spiral`: `x=a exp(k theta) cos(theta), y=e a exp(k theta) sin(theta)`. Elliptic logarithmic spiral for controlled anisotropic curvature.
- `fermat_spiral_short`: `r(theta)=a sqrt(1+k theta)`. Fermat-like spiral with slower radial growth and compact footprint.
- `elliptic_s_bend_prefocus_spiral`: `S-bend inlet + x=(a+b theta) cos(theta), y=e(a+b theta) sin(theta)`. Smooth S-bend focusing inlet followed by a clean elliptic spiral.
- `short_circular_c_arc`: `partial circular spiral arc r(theta)=a+b theta, theta<1.2 turns`. Very short C-arc/facing-electrode reference geometry.

## Best Candidate

- family: `monotone_curvature_spiral`
- equation: `r(theta)=r0/(1+k theta)^p`
- inlet kind: `outer_low_curvature_entry`
- target correct: `0.963 +/- 0.004`
- topology gain vs same-length straight DEP: `0.185`
- length: `7.1 mm`
- residence time: `4.46 s`
- wall loss: `0.000`
- active Joule power proxy: `4.83 mW`
- steady substrate temp-rise proxy: `6.57 C`
- manufacturable gap ok: `True`
- manufacturable bend ok: `True`
- no self-intersection/overlap ok: `True`
- minimum nonlocal clearance: `238.4 um`
- passes V11 gate: `True`

## Academic Improvements Over V10

- Additional families include logarithmic spirals, elliptic logarithmic spirals, Fermat spirals, S-bend prefocus spirals, and short C-arcs.
- Non-intersection and channel-overlap checks are hard geometric constraints before simulation.
- Shape parameters remain named physical variables: eccentricity, curvature power, inlet length, electrode gap, and electrode coverage.
- Short-channel screening remains explicit; the pass gate requires length <= 20 mm.
- The same-length straight DEP, no-DEP, and unfocused-inlet controls are reported for each finalist.
- Manufacturability proxies include minimum bend radius, minimum electrode gap, and nonlocal channel clearance.
- Thermal and pressure proxies are recorded for ranking, not hidden.

## How ML Optimizes Shape Here

The ML model does not draw arbitrary curves. It learns a surrogate from reduced-order simulations and ranks formula-parameter candidates. The optimized variables are family id, frequency, voltage, flow velocity, turns, radius, pitch, width, eccentricity, curvature power, inlet length, inlet focusing, DEP start/end, electrode gap, electrode coverage, field gain, and Dean scale. Finalists are re-simulated with held-out seeds and controls.

## Stored Shape Data

Top candidates are saved as `rank*_formula.json` and `rank*_centerline.csv` files.

## Honest Limitation

DEP is still represented by a reduced-order electrode-gap field-gain proxy. The selected V11 geometry should be rebuilt with an electrode-resolved field solve before a final device claim.

## Best Formula Parameters

```json
{
  "family": "monotone_curvature_spiral",
  "equation": "r(theta)=r0/(1+k theta)^p",
  "shape_class": "monotone_curvature_spiral",
  "inlet_kind": "outer_low_curvature_entry",
  "frequency_hz": 1636501.6717966013,
  "voltage_v": 14.375166824617455,
  "velocity_m_s": 0.0015884416940968884,
  "turns": 1.2059665261655397,
  "radius_m": 0.0010146160483793763,
  "pitch_m_per_rad": 1.6647328861290954e-05,
  "channel_width_m": 9.60862568502108e-05,
  "eccentricity": 1.0,
  "curvature_power": 1.1638201410895466,
  "inlet_length_m": 0.0007048073199949251,
  "outlet_split_ratio": 0.407209068445479,
  "inlet_offset_ratio": -0.48002269110239293,
  "inlet_spread_ratio": 0.16963066435447183,
  "dep_start_fraction": 0.2335934765508016,
  "dep_end_fraction": 0.8799601523090045,
  "dep_edge_smoothness": 0.027692251855850718,
  "electrode_gap_m": 4.8143367589183365e-05,
  "electrode_coverage": 0.6152455414719535,
  "field_gain": 1.1102830371292187,
  "dep_sign": -1.0,
  "dean_base": 1.0237251786973132,
  "note": "Curvature increases smoothly along the path instead of adding arbitrary waves.",
  "dean_scale": 1.6863615959255893
}
```
