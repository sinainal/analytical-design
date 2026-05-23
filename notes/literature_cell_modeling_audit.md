# Literature Cell Modeling Audit

Date: 2026-05-24

## Purpose

This note audits how the key reference papers model cells and how they reduce
the risk of deterministic or over-optimistic separation claims.

## Main Finding

The concern that the current reduced-order model can become too deterministic is
valid. Some spiral DEP simulation papers also use deterministic threshold-style
logic, but stronger studies support those models with experimental validation,
replicates, uncertainty, mesh independence, and multiple performance metrics.

## R5: Elitas 2017 Live/Dead U937 DEP

Cell model:

- Single-shell live/dead U937 cell model.
- DEP force uses `2*pi*epsilon_m*r^3*Re(CM)*grad(E_rms^2)`.
- CM factor computed from effective cell permittivity.
- Live/dead differences are membrane/cytoplasm conductivity and permittivity.
- Frequency scan is used to choose operating conditions.

Validation/anti-overclaim:

- They experimentally scan frequency from `50 kHz` to `1 MHz`.
- They use flow-rate experiments with three independent repeats and error bars.
- They report that dead cells are weakly affected or nearly unaffected by DEP.
- They report dead-cell removal around `90%`, not just a trajectory figure.

Implication for us:

- Our CM model is aligned with their theory, but our trajectory model is weaker
  because it lacks experimental-style replicate validation and field-derived
  gradients.

## R6: Patel 2012 Live/Dead Yeast rDEP

Cell model:

- Uses a spherical rigid-cell DEP mobility model.
- Uses a two-shell yeast model for live/dead dielectric properties.
- Builds a frequency/AC-DC phase diagram for live/dead trapping windows.

Validation/anti-overclaim:

- Compares numerical predictions with microscope images and streak trajectories.
- Monitors current and states Joule heating was insignificant under tested
  conditions.
- Explicitly admits throughput limitations.
- Explicitly admits missing cell-cell and some cell-fluid interactions.

Implication for us:

- We need a frequency/operating-window map, not only a best voltage.
- We should state missing cell-cell interactions and throughput limitations.

## R1: Betyar and Ramiar 2026 OpenFOAM Spiral DEP

Cell model:

- OpenFOAM custom solver.
- Eulerian fluid flow, Lagrangian particles.
- Particle equation includes drag and DEP force.
- RBC and MDA-MB-231 cells are modeled with different radius and CM response.
- Sweeps number of turns, inlet velocity, and voltage.

Validation/anti-overclaim:

- Validates solver against a previous semicircular-channel particle trajectory.
- Performs mesh independence using outlet distance from the inner wall.
- Reports threshold voltage versus turns and velocity.

Risk:

- Uses critical inlet positions and deterministic threshold logic.
- Reports cases with `100%` separation accuracy.
- Does not appear to use population-level stochastic variability the way an
  experimental live/dead assay would.

Implication for us:

- We can borrow OpenFOAM + threshold-voltage + mesh-independence workflow.
- We should not copy the deterministic success logic without adding robust
  validation.

## R10: Nguyen 2024 Facing-Electrode DEP

Cell model:

- Uses DEP force, hydrodynamic drag, electric potential, and single-shell cell
  model.
- Uses Newton's second law for particle trajectories.
- Ignores gravity and Brownian motion because modeled cells are larger than
  `1 um`.
- Sweeps electrode angle, channel height, applied voltage, and electrode number.

Validation/anti-overclaim:

- Reports separation efficiency and purity, not only trajectories.
- Shows non-monotonic voltage behavior: too much voltage can over-deflect cells
  into wrong outlets.
- Discusses wall trapping at low channel height.

Implication for us:

- V2 must include wrong-outlet over-deflection and wall-loss penalties.
- Voltage must not be treated as always beneficial.

## R4: Choi/Kwon 2018 Spiral Inertial Nonviable-Cell Removal

Cell model:

- Experimental, not DEP.
- Treats viable/nonviable separation as a distribution problem, mainly size and
  inertial behavior.
- Reports measured cell diameter distributions with large sample counts.

Validation/anti-overclaim:

- Uses replicates and reports ranges or standard deviations.
- Reports live-cell retention, dead-cell removal efficiency, removal purity,
  throughput, and flow split ratio.
- Emphasizes size overlap between viable and nonviable cells as a limitation.

Implication for us:

- We need population distributions, not only representative particles.
- We need throughput and purity/recovery metrics in addition to accuracy.

## R3: Yilmaz 2010 Spiral DEP Thesis

Cell/particle model:

- Analytical spiral DEP design and finite-element electric-field analysis.
- Discusses how geometry controls electric field and DEP force.

Anti-overclaim:

- Explicitly frames design parameters as trade-offs.
- More turns increase exposure time but also increase separation time/distance.
- Discusses Brownian motion, adhesion to walls, and voltage sharing through
  channel walls/medium.
- Uses experimental speed variation and coefficient of variation to define
  resolution and accuracy.

Implication for us:

- V2 should include residence-time and throughput penalties.
- Wall adhesion/loss and voltage-sharing/field-loss should be acknowledged or
  modeled.

## What This Means For Our Current Model

The current V1 model is acceptable only as a screening model.

It is not publication-grade because:

- field gradient is analytical, not interpolated from OpenFOAM
- cell properties are fixed
- no cell-cell interactions
- no wall adhesion model
- no throughput penalty in the objective
- no Joule-heating/electrothermal constraint
- voltage, turns, and velocity produce almost monotonic improvement unless
  explicit penalties are added

## Required V2 Corrections

1. Use OpenFOAM-derived `grad(E^2)` for DEP force.
2. Add cell-property distributions:
   - radius
   - membrane conductivity
   - cytoplasm conductivity
   - CM-factor uncertainty
3. Add inlet-position distributions and held-out seeds.
4. Add wall-loss and over-deflection penalties.
5. Add throughput/residence-time penalty.
6. Add Joule-heating estimate.
7. Report:
   - live recovery
   - dead-cell removal
   - live purity
   - dead outlet purity
   - overall correct classification
   - wall-limited particle count
8. Use mesh independence and solver validation before publication-level claims.

## Revised Interpretation

If V2 can only reach high accuracy by increasing turns indefinitely or slowing
the flow excessively, that is not a real device optimum. It is a model artifact.

The real target should be a Pareto optimum:

> high live/dead separation at acceptable voltage, acceptable throughput,
> acceptable residence time, low wall loss, and low thermal risk.
