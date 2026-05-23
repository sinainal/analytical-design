# Design V1 DOE And V2 Robustness Plan

Date: 2026-05-24

## Why V1 Was Needed

The V0 single-condition result was useful, but it could be misleading because a
single seed and a single parameter set can look artificially optimal. V1
therefore treats the problem as a design-of-experiments task.

## V1 DOE Scope

V1 optimizes the first three controllable parameters:

- spiral turns: `3`, `4`, `5`
- voltage: `8`, `10`, `12 V`
- inlet velocity: `1000`, `2000`, `3000 um/s`

Each condition was repeated with five random seeds:

- `7`, `11`, `13`, `17`, `19`

Total reduced-order runs:

```text
3 turns * 3 voltages * 3 velocities * 5 seeds = 135 simulations
```

## Classification Targets

Use two thresholds:

- screening target: `>=80%` correct classification
- publication-level target: mean `>=90%` and minimum replicate/seed result
  `>=90%`

Reason:

- R5 reports live/dead DEP performance around high dead-cell removal, so a weak
  60-70% result is not enough for a strong manuscript claim.
- R9 reports live-cell purity around `96.4%` and recovery around `78.3%`; this
  suggests that final reporting should separate purity and recovery, not just
  one overall score.
- R10 reports explicit separation efficiency and purity; our design should use
  similarly explicit metrics.

## V1 Result

Best robust condition:

- case: `5 turns / 12 V / 1000 um/s`
- mean correct classification: `86.3%`
- standard deviation across seeds: `0.7%`
- minimum seed result: `85.5%`
- mean live-to-inner fraction: `99.0%`
- mean dead-to-outer fraction: `73.6%`

Interpretation:

The best V1 condition passes the screening target but does not pass the
publication-level robustness target.

## Is The Model Overfitting?

It can overfit if we select only the single best run from a deterministic or
single-seed sweep.

V1 reduces that risk by:

- using five seeds per condition
- selecting by robust score, not only best single run
- reporting mean, standard deviation, and minimum seed result
- keeping the publication target stricter than the screening target

But V1 does not eliminate overfit because:

- the electric field is still a reduced analytical proxy
- the particle inlet distribution is simplified
- cell dielectric properties are fixed at one literature-derived parameter set
- no fabrication/geometric tolerance has been sampled yet

## How The Literature Handles This Problem

R1 sweeps design variables such as spiral turns, velocity, and voltage instead
of relying on a single trajectory. This supports our DOE structure.

R10 varies electrode and flow parameters and reports separation efficiency and
purity explicitly. This supports response-surface style optimization and
multi-metric reporting.

R4, R5, and R9 report recovery, removal, and purity-style metrics. This means
our final claims should not be based only on a visual trajectory plot.

R11 and R15 warn that DEP devices can fail because of conductivity, heating, or
electrothermal effects even when particle trajectories look good. This supports
adding thermal/electrothermal checks before publication-level claims.

## Additional Adjustable Parameters

After the first three parameters, the next adjustable parameters are:

- channel width
- channel height
- electrode layout: side-wall, facing, segmented
- electrode length or duty cycle
- pitch / spacing between turns
- medium conductivity
- frequency
- inlet particle distribution
- outlet split ratio
- number of outlets
- cell size and dielectric-property uncertainty

These should not all be optimized at once. V2 should add only the parameters
needed to address the V1 failure mode.

## V2 Plan To Avoid Overfitting

V2 should use a stricter validation workflow:

1. Replace analytical DEP field proxy with OpenFOAM-derived `grad(E^2)`.
2. Use train/validation separation:
   - train/design seeds for parameter search
   - held-out seeds for final reporting
3. Add uncertainty sampling:
   - live/dead radius variation
   - CM-factor perturbation
   - inlet lateral-position variation
4. Add geometry tolerance:
   - width and height perturbations
   - electrode-voltage perturbation
5. Report multiple metrics:
   - live recovery
   - dead-cell removal
   - live purity
   - dead outlet purity
   - overall correct classification
6. Add mesh independence:
   - coarse, medium, fine OpenFOAM potential meshes
7. Add thermal-risk check:
   - Joule heating estimate
   - AC electrothermal warning region

## V2 Success Criterion

V2 should not pass based on one best run.

V2 passes only if:

- mean correct classification is `>=90%`
- held-out minimum replicate is `>=90%`
- live recovery and dead-cell removal are both reported separately
- no excessive wall-limited/stalled particles appear
- the trend survives OpenFOAM field interpolation
- thermal-risk estimate remains acceptable

## Current Decision

Use V1 best condition, `5 turns / 12 V / 1000 um/s`, as the first candidate for
OpenFOAM-field-interpolated particle tracking.
