# Strategy Update

Date: 2026-05-23

## What New Literature Adds

### 1. Recent live/dead DEP benchmarks

The 2025 ODEP live/dead paper and the 2025 viable Legionella DEP paper are useful because they focus directly on viability, not just cell type or size. They give us practical targets for:

- recovery
- purity
- operating voltage/frequency
- viability-selective DEP response
- quantifiable response metrics

### 2. Modern electrode-design ideas

The 2024 facing-electrode DEP paper is valuable because it aims to reduce sensitivity to particle position and simplify fabrication compared with side-wall electrode designs. This matters for our spiral device because the particles enter the DEP region at different cross-channel positions.

### 3. Spiral microchannel design theory

The 2024 spiral inertial review is useful for geometry selection: width, height, aspect ratio, cross-section shape, focusing behavior, Dean flow, and fabrication choices. Even if our main force is DEP, spiral hydrodynamics will affect residence time and lateral migration.

### 4. Thermal and AC electrokinetic risks

The 2024 DEP+AC electrothermal simulation paper is important because a DEP device can fail biologically even if particles separate, if Joule heating or AC electrothermal flow becomes dominant. Our design should include a temperature/thermal-risk check before publication-level claims.

## Design Direction

The best first original design is not a trap-and-release device. It should be a continuous deflection device:

- one inlet
- two outlets
- Archimedean spiral channel
- side-wall or top-bottom/facing electrode zones
- particles continuously separate by different lateral displacement

Reason:

- It matches the long-term goal of an analysis/separation device.
- It is easier to evaluate with outlet purity/recovery metrics.
- It avoids long retention near electrodes, which may harm cells.

## Proposed First Cell Model

Start with a generic mammalian viable/nonviable pair rather than a specific clinical claim:

- radius: same or near-same radius in the first model
- main difference: Clausius-Mossotti factor over frequency
- medium: low-conductivity DEP buffer

This forces the design to prove viability-based separation, not just size-based separation.

## First Simulation Matrix

Keep the first matrix small:

| Parameter | Values |
|---|---|
| turns | 3, 5 |
| inlet velocity | 1000, 3000 um/s |
| voltage | 2, 4, 6, 8, 10, 12 V |
| frequency | one selected viability-discriminating value first |
| electrode layout | continuous side-wall baseline, facing-electrode variant |

## Minimum Acceptance Criteria

Before writing manuscript text, require:

- at least 90% outlet classification in the idealized particle model
- purity/recovery table for both live and dead fractions
- residence time below a biologically reasonable limit
- electric solve convergence
- no particle stalling
- mesh-independence check on at least one representative condition
- Joule-heating estimate or thermal simulation

## Next Implementation Steps

1. Build a parameter table from the literature for viable/dead cell dielectric properties.
2. Implement a lightweight analytical estimator for DEP displacement vs drag.
3. Generate the first `design_v0` OpenFOAM case.
4. Run a two-geometry comparison:
   - side-wall electrodes
   - facing electrodes
5. Select the design that separates with the lowest voltage and cleanest outlet split.
