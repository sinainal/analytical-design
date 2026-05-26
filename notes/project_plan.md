# Project Plan

Date: 2026-05-23

## Phase 1 - Literature and Design Envelope

- Build a paper matrix for live/dead DEP, spiral microchannels, and prior spiral DEP devices.
- Extract plausible cell properties:
  - radius
  - membrane capacitance
  - cytoplasm conductivity
  - medium conductivity
  - Clausius-Mossotti response vs frequency
- Define the first target cell pair:
  - viable mammalian cell
  - nonviable/dead counterpart or debris-rich nonviable fraction

## Phase 2 - Analytical Device Definition

- Define spiral centerline using an Archimedean model:
  - `r(theta) = r0 + b theta`
  - `b = pitch / (2*pi)`
- Define channel width, height, turn count, outlet split, and electrode layout.
- Estimate DEP force, Stokes drag, residence time, and expected lateral displacement.
- Choose a first operating sweep:
  - turns: `3, 5, 7`
  - voltage: `2-20 V`
  - frequency: selected from dielectric response window
  - flow rate: low, medium, high continuous-flow cases

## Phase 3 - OpenFOAM Prototype

- Generate mesh programmatically.
- Solve electric potential.
- Solve or prescribe laminar flow for the first pass.
- Track particles with DEP and drag.
- Compute outlet classification automatically.

Status update, 2026-05-24:

- V0/V1/V2 produced useful screening outputs, but V2 confirmed that the current
  reduced-order DEP proxy is not realistic enough for final claims.
- Before optimization, build Design V3 as a field-coupled OpenFOAM workflow:
  OpenFOAM `U` + OpenFOAM `phiE` + exported/interpolated `grad(|E|^2)` +
  particle tracking in the actual mesh.
- Use `notes/openfoam_microfluidics_reference_audit.md` as the immediate V3
  realism checklist.

## Phase 4 - Simulation Study

- Voltage threshold map.
- Flow-rate robustness map.
- Mesh independence.
- Geometry sensitivity:
  - pitch
  - width
  - height
  - outlet split
  - electrode segmentation

Status update, 2026-05-25:

The next school-project scope is intentionally compact and defensible:

1. Design V4 - model realism check:
   - frequency-dependent live/dead Clausius-Mossotti response
   - both outlet label conventions, `correct_A` and `correct_B`
   - outlet split ratio
   - final lateral distribution plots
2. Design V5 - spiral/DEP isolation:
   - spiral with DEP off
   - spiral with DEP on
   - same-length straight channel with DEP on/off
   - reversed DEP sign sanity check
   - report `spiral_gain`, `dep_gain`, and `synergy_score`
3. Design V6 - optimization handoff:
   - fast Latin-hypercube/random search scaffold
   - target `max(correct_A, correct_B) >= 0.8`
   - keep wall loss and purity as constraints, not hidden penalties

These versions avoid deformable cells, cell-cell coupling, GPU code, and Joule
heating. They are meant to be fast enough for 100-200 condition optimization
while still being more rigorous than a single ideal particle trajectory.

V6 result update, 2026-05-25:

- Max-accuracy design reached `0.999` target correct, but its same-length
  straight DEP control was also high (`0.937`), so it is not the best
  spiral-specific argument.
- The selected paper-facing V6 design is the balanced-synergy candidate:
  `0.945 +/- 0.007` nominal held-out target correct, `0.922 +/- 0.083`
  tolerance-perturbed target correct, same-length straight DEP control `0.737`,
  and screened synergy `0.178`.
- The honest claim is segmented DEP plus inlet focusing in a compact spiral
  microchannel. Spiral geometry contributes measurably, but DEP and inlet
  focusing remain essential.
- Detailed outputs are in `results/optimization_v1/V6_DECISION_SUMMARY.md` and
  `results/optimization_v1/balanced_synergy_validation/`.

V7 result update, 2026-05-25:

- Added geometry/feasibility screening across smooth spiral, short spiral,
  low-heat spiral, compact C-arc, serpentine controls, and stepwise late-DEP
  spiral variants.
- Best current V7 candidate is `stepwise_late_dep_spiral`: validated target
  correct `0.914 +/- 0.014`, topology gain versus same-length straight DEP
  `0.239`, wall loss `0.000`, length `64.4 mm`, active Joule power proxy
  `5.90 mW`, and steady substrate temperature-rise proxy `1.6 C`.
- The no-cooling adiabatic proxy is still high (`87.9 C`), so any final
  experimental safety claim needs a real heat-transfer solve. For project-level
  ranking, the steady substrate proxy suggests this candidate is more feasible
  than V6 while being much more geometry-specific.
- Detailed outputs are in `results/design_v7_geometry_feasibility/`.

V8 result update, 2026-05-26:

- Added ML-assisted shape-family optimization across asymmetric C-spiral,
  pinched/step spiral, compact C-arc/facing-electrode-like, serpentine-stepwise,
  and wide low-heat asymmetric families.
- ML role: ExtraTrees surrogate ranked virtual candidates after real
  reduced-order simulations; reported finalists are held-out particle
  simulations, not direct ML predictions.
- Best short-channel candidate: `asymmetric_c_spiral`, validated target correct
  `0.957 +/- 0.006`, length `10.9 mm`, topology gain versus same-length
  straight DEP `0.129`, active Joule power proxy `3.34 mW`, steady substrate
  temperature-rise proxy `3.67 C`, wall loss `0.000`.
- Highest-accuracy geometry-specific alternative: `pinched_step_spiral`,
  validated target correct `0.991 +/- 0.005`, length `15.6 mm`, topology gain
  `0.452`.
- V8 still uses a reduced-order `field_gain` proxy for shaped/facing/pinched
  electrode concentration. The next rigor step is electrode-resolved OpenFOAM or
  FEM field solution for the chosen V8 family.
- Detailed outputs are in `results/design_v8_shape_ml_optimization/`.

V9 result update, 2026-05-26:

- Replaced informal/free-form shape labels with explicit mathematical shape
  functions. Tested curvature-modulated spirals, outlet-expanded modulated
  spirals, tapered C-spirals, and log-like Dean spirals.
- Best V9 candidate is a curvature-modulated spiral defined by
  `r(theta)=a+b theta+c sin(n theta+phi)`. Held-out validation gave target
  correct `0.943 +/- 0.014`, same-length straight DEP control `0.518`,
  topology gain `0.424`, length `34.8 mm`, wall loss `0.000`, active Joule
  power proxy `7.32 mW`, and steady substrate temperature-rise proxy `3.50 C`.
- This is the strongest current argument that spiral curvature is doing more
  than simply adding channel length. The no-DEP and unfocused-inlet controls
  remain near weak-baseline levels, so inlet focusing plus DEP staging are still
  essential.
- The top five formula geometries are saved as parameter JSON files and
  centerline CSV files with `x`, `y`, local width, and DEP activation values.
- V9 still uses a reduced-order electric-field concentration proxy. Before a
  final device claim, the selected formula should be rebuilt with
  electrode-resolved OpenFOAM/FEM fields.
- Detailed outputs are in `results/design_v9_formula_shapes/`.

V10 result update, 2026-05-26:

- Replaced visually irregular V9 modulation with clean named geometry families:
  circular Archimedean spiral, elliptic Archimedean spiral, monotone-curvature
  spiral, elliptic-prefocus spiral, superellipse/oval spiral, and
  concentric-electrode spiral.
- The V10 pass gate explicitly prioritizes short devices: length `<= 20 mm`,
  target correct `>= 0.80`, positive topology gain versus same-length straight
  DEP, low wall loss, acceptable electrode gap, acceptable bend radius, and no
  high thermal-risk flag.
- Best V10 candidate is `monotone_curvature_spiral` with
  `r(theta)=r0/(1+k theta)^p`, outer low-curvature inlet, target correct
  `0.953 +/- 0.013`, length `9.15 mm`, same-length straight DEP control
  `0.579`, topology gain `0.374`, wall loss `0.000`, active Joule power proxy
  `8.22 mW`, and steady substrate temperature-rise proxy `10.55 C`
  (`moderate` thermal flag).
- Some short elliptic candidates reached `1.000` target correct, but their
  same-length straight controls were also near `0.99`; these are therefore not
  strong evidence for geometry synergy and were rejected by the V10 gate.
- V10 stores each finalist as a formula JSON and centerline CSV with channel
  width, electrode gap, and DEP activation values. Detailed outputs are in
  `results/design_v10_short_clean_shapes/`.

## Phase 5 - Manuscript Package

- Introduction and literature gap.
- Analytical design model.
- Numerical methods.
- Results:
  - field maps
  - trajectory maps
  - separation efficiency
  - voltage/flow/geometry sweeps
- Limitations and experimental fabrication path.

## Immediate Next Step

Complete a literature table with parameter values and decide the first live/dead cell model before writing any new solver code.

Primary manuscript-support note:

- `reference_knowledge_base.md`

First simulation specification:

- `design_v0_spec.md`
