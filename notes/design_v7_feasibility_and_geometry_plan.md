# Design V7 Feasibility And Geometry Plan

Date: 2026-05-25

## Why V7 Is Needed

V6 is useful as a reduced-order optimization result, but it is not yet enough
for a strong academic claim. The max-accuracy candidate reached nearly perfect
classification, but the same-length straight DEP control was also very high.
That means the model can produce over-clean separation when inlet focusing and
segmented DEP are optimized together.

V7 should therefore stop optimizing only for correct classification and instead
test whether the geometry is physically useful, fabricable, and better than
shorter or simpler alternatives.

## Literature Comparison To Add

Already in the repository:

- R1: OpenFOAM spiral DEP precedent; reports deterministic high-separation
  cases and threshold-voltage behavior.
- R5/R6/R7/R9/R12: live/dead DEP precedents.
- R10: facing-electrode DEP numerical study; reports separation efficiency and
  purity and shows non-monotonic voltage/wall-trapping behavior.
- R4/R8/R16: spiral inertial/nonviable-cell background.

New high-performance references to track:

- Circular OpenFOAM DEP microchannel paper, DOI `10.1016/j.apt.2023.104046`.
  Public abstract/search snippet reports an OpenFOAM code and `100%` purity and
  separation efficiency for some particle/cell conditions. Use this as a warning
  that deterministic OpenFOAM DEP studies can report perfect separation.
- Stepwise multi-stage DEP chip with microfilter structures, DOI
  `10.1016/j.talanta.2024.126585`. Use this as a shape/topology inspiration:
  staged electrodes plus passive flow-conditioning structures, not a plain
  smooth spiral.

ScienceDirect blocked direct command-line download with HTTP 403. Metadata files
in `papers/` record the attempted URLs; full text should be fetched through
library access or open alternatives if needed.

## Geometry Hypothesis

The current Archimedean spiral may be too ideal and too smooth. It may only
provide compact path length, not a unique separation mechanism.

V7 should compare:

1. Smooth Archimedean spiral.
2. Same-footprint straight serpentine.
3. Circular arc or C-shaped DEP channel.
4. Spiral with segmented electrode-active region.
5. Spiral with outlet-side expansion or contraction.
6. Spiral with stepwise electrode zones inspired by multi-stage DEP chips.
7. Spiral plus simple passive focusing section before DEP activation.

## Feasibility Checks

For each candidate geometry, report:

- footprint area
- centerline length
- residence time
- pressure drop proxy
- electric field strength proxy
- Joule-heating proxy
- minimum channel width and bend radius
- wall-loss fraction
- target correct
- live recovery
- dead removal
- outlet purities
- spiral/topology gain versus equal-length straight control

## V7 Acceptance Criteria

A candidate is V7-credible only if:

- nominal target correct is at least `0.85`
- tolerance-perturbed target correct is at least `0.80`
- wall loss is below `0.10`
- same-length straight DEP is lower by at least `0.10`
- no-DEP control stays near chance
- unfocused-inlet control does not collapse below `0.60` unless the report
  explicitly states that a sheath/focusing inlet is required
- pressure and heating proxies stay within a plausible microfluidic operating
  window

## Planned V7 Experiments

1. Geometry audit:
   - generate comparable shape descriptors for current spiral, circular arc,
     serpentine, and staged spiral
   - do not run optimization yet
2. Feasibility metric layer:
   - add residence time, footprint, pressure-drop proxy, and Joule-heating proxy
   - make these constraints visible in every CSV
3. Shape ablation:
   - run each geometry at the V6 balanced operating condition
   - compare against same-length and same-footprint controls
4. Compact optimization:
   - optimize over shape family, turns/length, voltage, velocity, DEP segment,
     outlet split, and inlet focusing
   - objective should be multi-objective, not only accuracy
5. Final validation:
   - held-out seeds
   - tolerance perturbation
   - straight/equal-length control
   - no-DEP control
   - unfocused and moderate-focused inlet controls

## Expected Outcome

The most defensible V7 result may not be the highest accuracy design. It should
be the shortest, simplest, and most feasible design that still clears the
performance target and beats the straight-channel control.
