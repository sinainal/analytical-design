# Simulation Stack And Literature Alignment

Date: 2026-05-23

## Question

Is OpenFOAM enough for the project, or do we need additional simulation and
analysis tools?

## Short Answer

OpenFOAM should be the main field-solver and visualization-compatible
simulation base, but it should not be the only tool. A credible workflow needs
OpenFOAM plus small project-specific Python tools for dielectric-property
modeling, particle trajectory integration, metrics, plotting, and quality
control.

## Why OpenFOAM Is Still Central

OpenFOAM is aligned with the spiral DEP precedent in the literature:

- R1 uses OpenFOAM for spiral DEP particle separation and sweeps channel
  turns, velocity, and voltage.
- R1 also supports side-wall electrodes, one inlet, two outlets, and spiral
  residence-time/voltage-threshold logic.
- Our proposed V0 model can use OpenFOAM for meshable spiral geometry,
  laminar-flow fields, electric potential fields, and ParaView-compatible
  outputs.

This makes OpenFOAM a good backbone for the paper because it gives us
reproducible CFD/electric-field cases and standard visualization outputs.

## What OpenFOAM Does Not Give Us By Itself

The project still needs additional scripts or custom solvers for:

- live/dead Clausius-Mossotti frequency scans
- DEP force calculation from `Re(CM)` and `grad(E^2)`
- cell trajectory integration and outlet classification
- recovery, purity, separation efficiency, and dead-cell removal metrics
- voltage/flow/turn sweep orchestration
- plot generation for manuscript figures
- Joule-heating and AC electrothermal risk checks

Therefore, the practical stack should be:

| Layer | Tool |
|---|---|
| Geometry/case generation | Python |
| Flow and electric-field solution | OpenFOAM |
| Particle tracking, DEP force, metrics | Python first, custom OpenFOAM later if needed |
| Visualization | ParaView |
| Plotting/report tables | Python |
| Reproducibility | Git scripts and committed compact outputs |

## Is The First CM Finding Parallel To The Papers?

Yes, at the level it was meant to test.

The first CM scan found a strong live/dead DEP contrast near `455 kHz`, where
the live-cell model has strong positive DEP and the dead-cell model is nearly
DEP-neutral.

This is parallel to the literature in three ways:

1. R5 supports using live/dead dielectric differences and crossover/frequency
   behavior as the separation basis.
2. R6, R7, R9, and R12 support the broader claim that viability-selective DEP
   can distinguish live/dead or viable/nonviable cells.
3. R1-R3 support putting DEP into a spiral/curved geometry to increase
   interaction length and reduce required voltage.

It is not yet a replication of an OpenFOAM spiral result, and it should not be
described that way. It is a literature-grounded parameter selection result
that prepares the OpenFOAM-backed device simulation.

## Current Interpretation

The first design hypothesis is:

> In a spiral side-wall DEP channel, live cells can be biased toward the
> high-field side at the selected frequency while dead cells remain closer to
> hydrodynamic/inertial transport, enabling outlet enrichment.

This is plausible and consistent with the literature base, but it still needs
to be tested in the coupled spiral geometry.

## Next Required Simulation Step

Build `design_v0` as an OpenFOAM-backed case:

1. Generate Archimedean spiral geometry.
2. Solve or prescribe laminar flow.
3. Solve electric potential between side-wall electrodes.
4. Export `E` and `grad(E^2)`.
5. Track live/dead particles at `455 kHz`.
6. Compute outlet metrics automatically.
7. Save ParaView-ready output and compact plots/tables.

## Manuscript Caution

Do not claim final separation performance from the CM scan alone. The CM scan
only justifies frequency selection. The paper-level claim must come from
geometry-specific trajectories, outlet metrics, and thermal-risk checks.
