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
