# Analytical Design

OpenFOAM-based analytical design and simulation workspace for a spiral dielectrophoretic microfluidic device targeting continuous live/dead cell sorting.

## Project Aim

The goal is to develop and evaluate a low-voltage spiral DEP microdevice for label-free separation of viable and nonviable cells. The project combines literature-grounded analytical modeling, geometry generation, electric-field simulation, particle tracking, and automated separation metrics.

## Current Scope

- Build a literature base for spiral microchannels, dielectrophoresis, and live/dead cell separation.
- Define a new spiral DEP device geometry from first principles.
- Generate reproducible OpenFOAM cases.
- Evaluate outlet purity, recovery, voltage threshold, residence time, and robustness across flow rates.

## Repository Layout

- `papers/`: local paper pool for literature review.
- `notes/`: technical notes, design assumptions, and planning records.
- `src/`: reusable implementation code.
- `scripts/`: command-line tools for building and running cases.
- `results/`: generated summaries and simulation outputs.
- `docs/`: manuscript-facing figures, tables, and documentation drafts.

## First Research Question

Can a compact spiral DEP microchannel separate live and dead/nonviable cells at lower voltage than conventional straight-channel DEP layouts while preserving continuous-flow operation?

## License

MIT License. See `LICENSE`.
