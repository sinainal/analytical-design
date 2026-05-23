# Spiral-Based Dead/Nonviable Cell Separation

Date: 2026-05-23

## Direct Answer

Yes, spiral microchannels have been used directly for dead/nonviable cell separation or depletion, but the mechanism is mainly inertial microfluidics, not dielectrophoresis.

The closest examples are:

- Kwon et al., 2018: continuous removal of small nonviable suspended mammalian cells and debris from bioreactors using inertial microfluidics.
- Spiral inertial microfluidic CAR-T purification: depletion of nonviable cells and enrichment of viable CAR-T cells.
- Spiral inertial bioprocessing reviews that summarize CHO live/dead or nonviable-cell removal cases.

## What Is Not Yet Found

No directly matching paper has been identified that combines all of these:

- spiral microchannel
- DEP as the primary active force
- continuous live/dead or viable/nonviable mammalian-cell separation
- numerical design workflow suitable for OpenFOAM extension

This is the key project gap.

## How A Spiral Channel Supports Separation

### In inertial-only spiral separation

Spiral channels create curved-flow inertial effects:

- shear-gradient lift force
- wall-induced lift force
- Dean secondary flow and Dean drag

These forces push particles/cells toward size- and deformability-dependent equilibrium positions. Since many dead or apoptotic cells shrink, they can focus differently from larger viable cells. Debris and small nonviable cells can therefore be enriched toward a different outlet.

### In our DEP-assisted spiral concept

The spiral is not only a passive separator. It supports DEP separation by:

- increasing interaction length in a compact footprint
- increasing residence time under the electric field
- allowing lower voltage for the same lateral displacement
- pre-positioning particles through hydrodynamic focusing
- making outlet split easier after gradual lateral migration

The hypothesis is that spiral geometry gives the DEP force more time and distance to act, while DEP provides the viability selectivity that inertial separation alone lacks.

## Design Implication

The new device should not rely only on size differences between live and dead cells. That would duplicate inertial spiral work. The design should intentionally use a frequency-dependent DEP contrast between viable and nonviable cells, with spiral geometry acting as the residence-time amplifier.
