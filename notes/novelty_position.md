# Novelty Position

Date: 2026-05-23

## Search Question

Is there already a recent paper that directly does the same thing as the proposed project?

Target combination:

- spiral microchannel
- dielectrophoresis
- continuous outlet-based live/dead or viable/nonviable cell sorting
- mammalian-cell-oriented design
- numerical model suitable for OpenFOAM reproduction or extension

## Current Answer

No directly matching paper has been identified in the current search.

The literature contains strong neighboring work, but each misses at least one core element:

1. Spiral DEP biological separation exists, but not specifically as live/dead mammalian-cell sorting.
2. Live/dead DEP separation exists, but mostly in straight, reservoir, CMOS, cDEP, ODEP, 3D-carbon, or electrode-array devices rather than spiral microchannels.
3. Spiral live/dead or nonviable-cell separation exists, but primarily through inertial microfluidics rather than DEP.
4. OpenFOAM spiral DEP exists for RBC/cancer-cell separation, but not for viable/nonviable cell sorting.

## Safe Claim

A safe manuscript claim would be:

> Recent literature provides separate precedents for spiral microfluidic live/dead or nonviable-cell handling and DEP-based live/dead separation, but a continuous spiral DEP device for viable/nonviable mammalian-cell sorting has not been identified in the current search.

Avoid claiming absolute first-in-world novelty until a full database search is completed.

## Proposed Research Object

Design and numerically evaluate a continuous-flow spiral dielectrophoretic microdevice for live/dead or viable/nonviable mammalian-cell sorting.

The first version should be an analytical/numerical design study, not an experimental paper.

## Core Hypothesis

A spiral DEP device can increase DEP interaction length and residence time while keeping the device compact, reducing the required voltage for viability-based lateral deflection compared with a straight DEP channel of similar footprint.

## What We Need To Prove

1. Viable and nonviable cells have sufficiently different frequency-dependent DEP response in the selected medium.
2. The proposed spiral geometry generates enough lateral displacement before the outlets.
3. The separation remains continuous, not trap-and-release.
4. Voltage and Joule heating remain within biologically acceptable limits.
5. Performance is robust to initial particle position, flow rate, and modest parameter variation.

## Minimum Study Design

### Analytical model

- Clausius-Mossotti factor vs frequency.
- DEP force estimate.
- Stokes drag balance.
- Residence time estimate.
- Lateral displacement estimate.

### Numerical model

- Spiral geometry generated from an Archimedean centerline.
- Electric field solve.
- Laminar flow solve or controlled prescribed-flow baseline.
- Lagrangian particle tracking.
- Outlet classification.

### Parameter sweep

- turns: 3 and 5 in the first round
- voltage: 2 to 12 V
- flow velocity: 1000 and 3000 um/s
- electrode strategy:
  - continuous side-wall baseline
  - facing-electrode variant

### Metrics

- live recovery
- dead/nonviable removal
- purity
- separation efficiency
- residence time
- required threshold voltage
- maximum electric field
- Joule-heating estimate

## Decision Gate

Proceed to manuscript drafting only if the first numerical sweep shows:

- at least 90% correct outlet classification under idealized parameters
- clear voltage threshold behavior
- no particle stalling
- acceptable thermal-risk estimate
- reproducible results from scripted runs

## Current Risk

The main scientific risk is that viable/nonviable DEP contrast may depend strongly on cell type, medium conductivity, preparation method, and frequency. The project should therefore start with a generic but literature-grounded mammalian viable/nonviable model, then later specialize to one cell type.
