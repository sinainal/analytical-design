# Design V9 Formula Shapes

V9 uses explicit mathematical shape functions rather than informal
free-form geometry labels.

## Shape Functions

- Radius: `r(theta)=a+b theta+c sin(n theta+phi)` or a log-like variant.
- Width: `w(s)=w0[1+beta sigmoid((s-s_out)/ell_out)]`.
- DEP activation: `alpha(s)=sigmoid((s-s1)/ell1)[1-sigmoid((s-s2)/ell2)]`.

## Best Candidate

- family: `curvature_modulated_spiral`
- target correct: `0.943 +/- 0.014`
- topology gain vs same-length straight DEP: `0.424`
- length: `34.8 mm`
- short-channel score: `0.0127` per mm
- wall loss: `0.000`
- active Joule power proxy: `7.32 mW`
- steady substrate temperature-rise proxy: `3.50 C`
- passes V9 gate: `True`

## Stored Shape Data

The top five formula geometries are saved as `rank*_centerline.csv` and
`rank*_formula.json`, including `x`, `y`, local width, and smooth DEP
activation values.

## Honest Limitation

The electric-field effect still uses a reduced-order `field_gain` proxy.
The shape functions are now mathematically explicit, but the best formula
must still be converted into an electrode-resolved field solve before a
final device claim.
