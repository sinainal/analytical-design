# Design V2 Realistic Cell Modeling Plan

Date: 2026-05-24

## Why V2 Is Needed

V1 is useful as a screening model, but it can be driven toward unrealistically
high classification by increasing residence time or voltage. V2 must therefore
move from "best deterministic trajectory" to "robust population behavior".

The goal is not to add an artificial penalty. The goal is to model the real
conditions that papers use to keep cell-separation claims honest:

- measured or literature-based cell-property distributions
- random inlet positions
- repeated populations
- wall collision / trapping behavior
- over-deflection at high voltage
- recovery, purity, and removal metrics
- field values interpolated from OpenFOAM, not an analytical shortcut

## What The Literature Actually Does

### Elitas 2017: U937 live/dead DEP

Use for our biological model.

They use a single-shell live/dead U937 model:

- live diameter: about `23 um`
- dead diameter: about `22 um`
- membrane thickness: `7 nm`
- live cytoplasm conductivity: `0.5 S/m`
- dead cytoplasm conductivity: `0.002 S/m`
- live membrane conductivity: `1e-6 S/m`
- dead membrane conductivity: `0.01 S/m`
- medium conductivity: `0.002 S/m`

But they do not stop at the numerical CM curve. They:

- experimentally scan frequency
- rate cell behavior over frequency
- use flow-rate experiments
- run three independent experiments
- report error bars and dead-cell removal

V2 implication:

The U937 dielectric parameters can seed the model, but V2 must sample around
them instead of using one fixed live and one fixed dead cell.

### Choi/Kwon 2018: spiral nonviable-cell removal

Use for population-distribution thinking.

They treat viable/nonviable sorting as a distribution problem:

- input cell diameter distribution
- inner/outer outlet diameter distributions
- large sample counts
- live-cell retention
- dead-cell removal efficiency
- removal purity
- throughput
- flow split ratio

V2 implication:

We should model live/dead cells as overlapping populations. A result is only
meaningful if it survives this overlap.

### Nguyen 2024: numerical DEP separation

Use for particle simulation structure and metrics.

They use:

- 3D electric field
- creeping flow
- particle tracing
- single-shell cell model
- random inlet cell addition
- wall collision behavior
- mesh independence
- separation efficiency and separation purity

They also show that higher voltage is not always better: too much deflection can
push cells into wrong outlets.

V2 implication:

High voltage must be allowed to fail through over-deflection. We should not
force monotonic improvement with voltage.

### Betyar and Ramiar 2026: OpenFOAM spiral DEP

Use for OpenFOAM workflow.

They use:

- OpenFOAM custom solver
- Eulerian flow
- Lagrangian particles
- DEP + drag force
- turn/velocity/voltage sweep
- mesh independence
- threshold voltage map

Risk:

They rely heavily on critical entry positions and deterministic threshold logic.
That is useful for threshold estimation, but not enough for a robust live/dead
population model.

V2 implication:

Use the OpenFOAM workflow, but add population-level validation.

### Patel 2012 and Patel/Xuan 2011

Use for limitations.

They explicitly discuss:

- operating windows / phase diagrams
- Joule heating checks
- throughput limits
- particle-wall interactions
- particle adhesion and aggregation control
- missing cell-cell interactions

V2 implication:

If our model ignores interactions, wall effects, and heating, we must state that
clearly and avoid publication-level claims.

## V2 Cell Population Model

Instead of two fixed particles, V2 should generate cell populations.

### Live Population

Initial distribution:

- diameter: normal or truncated normal centered at `23 um`
- coefficient of variation: start with `8-12%` unless exact U937 supplement data
  are extracted
- membrane conductivity: log-normal around `1e-6 S/m`
- cytoplasm conductivity: log-normal around `0.5 S/m`
- membrane thickness: narrow normal around `7 nm`

### Dead Population

Initial distribution:

- diameter: normal or truncated normal centered at `22 um`
- coefficient of variation: start with `8-12%`
- membrane conductivity: log-normal around `0.01 S/m`
- cytoplasm conductivity: log-normal around `0.002 S/m`
- membrane thickness: narrow normal around `7 nm`

### Why Log-Normal For Conductivity

Conductivity is positive and can vary multiplicatively. A normal distribution can
generate impossible negative values. Log-normal sampling is safer for membrane
and cytoplasm conductivity.

### What Must Be Improved Later

The `8-12%` diameter CV is a placeholder until we extract exact distributions
from:

- Elitas supplementary Figure S1 for U937 live/dead diameters
- Choi/Kwon-style measured diameter distributions if we choose CHO or another
  better-documented mammalian cell target
- additional U937 morphology/diameter papers if we keep U937 as the target

## What Held-Out Seed Means

A seed controls the random population sample:

- initial lateral positions
- cell diameters
- cell dielectric properties
- possibly flow perturbations

If we optimize and report on the same seeds, we may accidentally tune to one
random sample. That is the simulation version of overfitting.

V2 split:

- design seeds: used to search good conditions
- validation seeds: never used during search

Example:

- design seeds: `7, 11, 13, 17, 19`
- validation seeds: `101, 103, 107, 109, 113`

A condition passes only if it performs well on validation seeds.

## What Uncertainty Validation Means

Uncertainty validation means we do not ask:

> Does this exact ideal cell separate?

We ask:

> Does this design still separate when the cell population varies within
> plausible biological and fabrication ranges?

V2 uncertainty axes:

- cell diameter variation
- membrane conductivity variation
- cytoplasm conductivity variation
- inlet lateral position variation
- electrode voltage tolerance
- channel width/height tolerance
- medium conductivity variation

This is different from adding a penalty. It is rerunning the actual simulation
under plausible alternate realities.

## What Over-Deflection Means

Over-deflection is when DEP is too strong and pushes a target population past
its desired outlet stream or into a wall/wrong outlet.

Nguyen 2024 shows this concept: increasing voltage can reduce separation
efficiency because cells are deflected too far and collected at wrong outlets.

For our spiral:

- live cells are pulled toward the high-field inner wall
- if voltage/turns/residence time are too high, live cells may become
  wall-limited or trapped
- if outlet geometry is fixed, too much lateral displacement can place cells in
  the wrong outlet band

V2 should therefore record:

- correct outlet
- wrong outlet
- wall-limited / trapped
- over-deflected inner-wall loss

## Metrics Explained

Assume the desired assignment is:

- live cells -> live outlet
- dead cells -> dead outlet

### Live Recovery

Fraction of all injected live cells that reach the live outlet:

```text
live_recovery = live_at_live_outlet / live_injected
```

This tells us how many useful live cells we keep.

### Dead-Cell Removal

Fraction of injected dead cells that are removed into the dead outlet:

```text
dead_removal = dead_at_dead_outlet / dead_injected
```

This tells us how well dead contamination is removed.

### Live Purity

Fraction of all cells in the live outlet that are actually live:

```text
live_purity = live_at_live_outlet /
              (live_at_live_outlet + dead_at_live_outlet)
```

This matters because the live outlet may still contain dead-cell contamination.

### Dead Outlet Purity

Fraction of all cells in the dead outlet that are actually dead:

```text
dead_outlet_purity = dead_at_dead_outlet /
                     (dead_at_dead_outlet + live_at_dead_outlet)
```

This matters if the removed stream is analyzed or if live-cell loss is costly.

### Wall Loss

Fraction of cells that hit or stay too close to a wall:

```text
wall_loss = wall_limited_particles / injected_particles
```

A high wall-loss result is not a good separator, even if the remaining particles
look well separated.

## V2 Implementation Steps

1. Extract or approximate realistic live/dead diameter distributions.
2. Implement sampled cell populations instead of fixed live/dead particles.
3. Add validation seeds separate from design seeds.
4. Generate OpenFOAM `5-turn / 12 V / 1000 um/s` case.
5. Export/interpolate electric field and `grad(E^2)` from OpenFOAM.
6. Track particles using:
   - OpenFOAM field-derived DEP force
   - Stokes drag
   - inlet-position variation
   - wall collision/trap state
7. Sweep voltage narrowly around the V1 best:
   - `10, 11, 12, 13 V`
8. Keep turns and velocity near V1 best first:
   - turns: `5`
   - velocity: `1000 um/s`
9. Report recovery, purity, dead removal, wall loss, and validation-seed
   performance.

## V2 Pass Criteria

V2 passes screening if:

- validation mean correct classification `>=85%`
- live recovery `>=90%`
- dead-cell removal `>=75%`
- wall loss `<5%`

V2 becomes publication-candidate only if:

- validation mean correct classification `>=90%`
- live recovery `>=90%`
- dead-cell removal `>=85%`
- live purity `>=90%`
- wall loss `<5%`
- result survives OpenFOAM field interpolation
- mesh dependence is small

## Key Decision

Do not optimize indefinitely by adding more turns or lowering velocity.

For V2, first test whether the V1 best condition remains good after replacing
the idealized cell model with a population-distribution model and replacing the
field proxy with OpenFOAM-derived fields.
