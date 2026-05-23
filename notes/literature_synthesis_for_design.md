# Literature Synthesis for the Proposed Design

Date: 2026-05-23

## Core Interpretation

The literature does not give us one paper to copy. It gives us three separate ingredients that can be combined into a new design:

1. Spiral microchannels can handle dead/nonviable-cell removal, mostly through inertial focusing.
2. DEP can separate live/dead cells, mostly in straight, reservoir, 3D electrode, cDEP, or ODEP devices.
3. Spiral DEP can separate biological particles/cells, but the local matrix has no exact live/dead spiral DEP paper.

Our paper should explicitly combine these three lines:

> spiral residence-time advantage + viability-selective DEP response + continuous outlet-based sorting

## What Each Literature Cluster Gives Us

### S1 D0 T1 - Spiral, no DEP, dead/nonviable topic

Representative: Choi/Kwon 2018 nonviable cell removal in spiral inertial microfluidics.

Useful takeaways:

- Spiral channels are already relevant to nonviable-cell handling.
- Inertial spiral separation can retain viable cells at high efficiency.
- Reported metrics include live-cell retention, dead-cell removal purity, dead-cell removal efficiency, concentration, and throughput.
- Their result highlights a limitation: inertial separation depends heavily on size and flow-rate effects. Size overlap between viable and nonviable cells limits removal.

Design implication:

- We should not present the new device as merely another size-based spiral separator.
- Our differentiator should be viability-selective DEP contrast, with the spiral acting as an interaction-length amplifier.

Metrics to borrow:

- live-cell retention/recovery
- dead-cell removal efficiency
- dead-cell removal purity
- throughput
- flow split ratio

### S0 D1 T1 - DEP, no spiral, dead/live topic

Representative papers:

- Elitas et al. 2017: live/dead U937 monocytes with 3D carbon DEP.
- Patel et al. 2012: live/dead yeast reservoir DEP.
- Huang 2025: ODEP live/dead chondrocyte separation.

Useful takeaways:

- The physical basis is frequency-dependent polarizability.
- Crossover frequency is a key viability-sensitive descriptor.
- Dead cells can polarize differently because membrane integrity and membrane conductivity change after death.
- DEP live/dead studies often use low-conductivity media.

Numerical values worth carrying forward:

- Elitas et al. modeled U937 monocytes with:
  - live diameter: about `23 um`
  - dead diameter: about `22 um`
  - membrane thickness: `7 nm`
  - membrane permittivity: `12.5 epsilon0`
  - live cytoplasm conductivity: `0.5 S/m`
  - dead cytoplasm conductivity: `0.002 S/m`
  - live membrane conductivity: `1e-6 S/m`
  - dead membrane conductivity: `0.01 S/m`
  - medium conductivity: `0.002 S/m`
- Elitas et al. used `20 Vpp`, `300 kHz`, and `1 uL/min` as an effective separation condition, removing about `90%` of dead cells.
- Huang 2025 reported ODEP at `8 V`, live-cell manipulation force around `49.4 pN`, dead-cell force around `-20.1 pN`, live-cell recovery around `78.3%`, and live-cell purity around `96.4%`.
- Patel et al. showed that a live/dead operating window can be chosen using an AC/DC phase diagram; for yeast, one demonstrated condition was `4 V` DC-biased `47.5 V` AC at `1 kHz`.

Design implication:

- Start with an equal-size or near-equal-size viable/nonviable model so the simulation is not secretly size separation.
- Use frequency as a design variable, not only voltage.
- Report CM-factor curves before running full device simulations.

Metrics to borrow:

- recovery
- purity
- dead-cell depletion/removal
- crossover frequency
- force-vs-voltage characterization

### S1 D1 T0 - Spiral + DEP, not dead/live

Representative papers:

- Betyar and Ramiar 2026: OpenFOAM spiral DEP RBC/cancer-cell separation.
- Patel/Xuan 2011: curvature-induced DEP in spiral microchannels.
- Yilmaz 2010: spiral DEP separator thesis.

Useful takeaways:

- Spiral DEP is an established device class.
- Spiral geometry can reduce required voltage by increasing residence time and interaction length.
- Betyar and Ramiar used:
  - OpenFOAM
  - side-wall electrodes
  - one inlet and two outlets
  - spiral turns as a swept design parameter
  - velocity sweep
  - voltage threshold search
- Betyar and Ramiar's useful method pattern:
  - choose critical initial positions
  - increment voltage in `1 V` steps
  - classify whether each particle reaches the correct outlet
  - report voltage threshold vs turn count and flow velocity

Design implication:

- Our study should mirror this structure but change the target from RBC/cancer to viable/nonviable cells.
- The key graph should be threshold voltage vs turn count and flow rate.

Metrics to borrow:

- threshold voltage
- turns vs voltage
- flow velocity vs voltage
- outlet classification
- trajectory plots

### S0 D1 T0 - DEP, no spiral, not dead/live

Representative:

- Nguyen 2024 facing-electrode DEP.
- Tian 2024 DEP single-cell manipulation review.

Useful takeaways:

- Facing-electrode DEP may reduce fabrication complexity and reduce dependence on particle vertical/lateral position.
- Modern DEP simulation papers report separation efficiency and separation purity explicitly.
- Nguyen defines:
  - separation efficiency: target particles reaching target outlet divided by target particles injected
  - separation purity: target particles at target outlet divided by all particles collected at that outlet
- Nguyen sweeps:
  - voltage
  - flow velocity ratio
  - electrode angle
  - channel height
  - number of electrodes

Design implication:

- Use side-wall electrodes as the baseline because it aligns with spiral geometry.
- Include a facing-electrode variant as a second design if the baseline is too position-sensitive.
- Use Nguyen-style SE and SP equations in the manuscript.

## Proposed Paper Structure

### Introduction

Use the matrix logic:

- Spiral microchannels have been used for nonviable-cell/debris removal, but mostly inertial and size-dependent.
- DEP can separate live/dead cells, but common layouts are non-spiral and often trapping/release or straight-channel based.
- Spiral DEP exists for other biological separations, but not identified for continuous viable/nonviable sorting.
- Therefore, a spiral DEP design for continuous viable/nonviable sorting is worth modeling.

### Theory

Include:

- Archimedean spiral geometry.
- DEP force:
  - proportional to `r^3`
  - proportional to `Re(CM)`
  - proportional to gradient of electric field squared.
- Stokes drag.
- Residence time/lateral displacement estimate.
- CM-factor curves for live and dead cell model.

### Numerical Methods

Model choices:

- first design: continuous side-wall electrodes in a spiral channel
- one inlet, two outlets
- live/dead particles with near-equal diameter
- low-conductivity DEP buffer
- solve electric field
- solve or prescribe laminar flow in first model, then solve laminar flow for publication-grade runs
- Lagrangian particle tracking

Sweeps:

- turns: `3, 5`
- flow velocity: `1000, 3000 um/s`
- voltage: `2, 4, 6, 8, 10, 12 V`
- frequency: chosen from CM contrast window

### Results

Minimum results:

- CM-factor vs frequency plot.
- Electric field / `grad(E^2)` maps.
- Trajectory plots for live and dead cells.
- Outlet classification table.
- SE/SP/purity/recovery table.
- Threshold voltage map.
- Sensitivity to initial position.
- Joule-heating estimate.

## Strongest Novelty Sentence

Use a cautious version:

> Although spiral microchannels and DEP-based live/dead separation have each been widely studied, the current literature matrix did not identify a continuous spiral DEP design specifically targeting viable/nonviable mammalian-cell sorting. This work therefore evaluates whether spiral geometry can act as a compact residence-time amplifier for viability-selective DEP separation.

## What We Should Not Claim Yet

- Do not claim experimental performance.
- Do not claim first-in-world absolute novelty.
- Do not claim dead-cell separation unless the simulated cell model is explicitly viable/nonviable and not only different size.
- Do not claim low thermal risk without Joule-heating estimation.

## Immediate Action Items

1. Build a `cell_properties.md` table from Elitas, Huang, Patel, and related references.
2. Write a small analytical script to plot `Re(CM)` vs frequency for live/dead cell models.
3. Choose one frequency where live/dead DEP response diverges strongly.
4. Build `design_v0` side-wall spiral DEP.
5. Run a coarse voltage/flow/turn sweep and compute SE/SP automatically.
