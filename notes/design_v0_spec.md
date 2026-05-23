# Design V0 Simulation Specification

Date: 2026-05-23

## Purpose

The first simulation should answer one question:

> Can a spiral DEP microchannel convert live/dead dielectric contrast into measurable outlet separation under continuous flow?

This is not yet the final publication model. It is the smallest credible numerical prototype.

## Device Concept

### Geometry

Use a planar Archimedean spiral microchannel:

```text
r(theta) = r0 + b theta
b = pitch / (2*pi)
x(theta) = r(theta) cos(theta)
y(theta) = r(theta) sin(theta)
```

Initial baseline:

| Parameter | Value |
|---|---:|
| turns | `3` first, then `5` |
| inner radius | `1000 um` |
| channel width | `120 um` |
| channel height | `50 um` |
| pitch | `180 um` |
| inlet count | `1` |
| outlet count | `2` |
| outlet split | inner half / outer half |

Rationale:

- `50 um` height safely contains mammalian cells around `20-25 um` diameter.
- `120 um` width gives lateral migration room while remaining microfluidic.
- `3` turns keeps the first case fast; `5` turns tests the residence-time advantage.

### Electrodes

Baseline design:

- continuous side-wall electrodes
- inner wall: high potential
- outer wall: ground
- top/bottom: electrically insulated

Reason:

- This is simplest to implement in OpenFOAM.
- It matches the spiral DEP precedent style.
- It creates a mostly radial electric-field gradient, which maps naturally to inner/outer outlet separation.

Second design after V0:

- facing-electrode or segmented electrodes if side-wall DEP is too position-sensitive.

## Biological Model

Use a near-equal-size live/dead mammalian pair based on the U937 monocyte parameters from the reference knowledge base.

| Parameter | Live | Dead |
|---|---:|---:|
| diameter | `23 um` | `22 um` |
| membrane thickness | `7 nm` | `7 nm` |
| membrane relative permittivity | `12.5` | `12.5` |
| cytoplasm conductivity | `0.5 S/m` | `0.002 S/m` |
| cytoplasm relative permittivity | `50` | `80` |
| membrane conductivity | `1e-6 S/m` | `0.01 S/m` |
| medium conductivity | `0.002 S/m` | `0.002 S/m` |
| medium relative permittivity | `80` | `80` |

Rationale:

- The live/dead diameters are intentionally close.
- If separation occurs, it cannot be explained only by size.

## Physics

### First pass

- solve electric potential
- prescribe laminar spiral-aligned velocity field
- track Lagrangian particles
- compute DEP force from `Re(CM)` and `grad(E^2)`
- compute Stokes drag

### Publication pass

- solve laminar flow instead of prescribing velocity
- add mesh independence
- add Joule-heating estimate

## First Frequency Choice

Do not choose frequency manually.

Step 1:

- compute `Re(CM)` vs frequency for live and dead cells
- scan from `1 kHz` to `10 MHz`

Step 2:

- choose a frequency where the live/dead DEP response differs strongly
- preferred: opposite-sign response if available
- acceptable: same sign but clearly different magnitude

## First Simulation Matrix

Keep the first matrix deliberately small:

| Parameter | Values |
|---|---|
| turns | `3`, `5` |
| inlet velocity | `1000 um/s`, `3000 um/s` |
| voltage | `2, 4, 6, 8, 10, 12 V` |
| frequency | one selected from CM scan |
| particles per class | `100` |

Total cases:

```text
2 turns * 2 velocities * 6 voltages * 2 cell classes = 48 particle simulations
```

## Expected Outlet Logic

The outlet assignment depends on the selected CM signs:

- pDEP class moves toward high-field side
- nDEP class moves away from high-field side

If the inner wall is high-field:

- pDEP-dominant class should enrich at inner outlet
- nDEP-dominant class should enrich at outer outlet

If this direction is undesirable, swap electrode polarity or outlet labels.

## Metrics

For each run:

- number of live particles reaching live outlet
- number of dead particles reaching dead outlet
- live recovery
- dead-cell removal efficiency
- live purity
- dead fraction purity
- separation efficiency
- separation purity
- residence time
- mean final lateral position
- particle stalling count

## Acceptance Criteria For V0

V0 is successful if:

- particles traverse the spiral without stalling
- live/dead final lateral distributions differ clearly
- at least one condition achieves `>= 80%` correct outlet classification
- increasing turns improves separation or reduces voltage
- increasing velocity increases required voltage or reduces separation

The publication target should later be stricter:

- `>= 90%` correct outlet classification
- mesh independence
- solved laminar flow
- thermal-risk estimate

## Implementation Order

1. `cell_properties.md`
   - final table of live/dead dielectric properties.
2. `cm_factor_model.py`
   - compute and plot `Re(CM)` vs frequency.
3. `design_v0_geometry.py`
   - generate Archimedean spiral mesh/case.
4. `run_design_v0.py`
   - run voltage/turn/velocity matrix.
5. `audit_design_v0.py`
   - compute outlet metrics automatically.
6. ParaView state
   - show electric field, spiral mesh, and live/dead trajectories.

## First Figure Targets

1. Device schematic.
2. `Re(CM)` vs frequency for live/dead cells.
3. Electric potential and `grad(E^2)` map.
4. Trajectories for live/dead particles at a successful voltage.
5. Voltage threshold vs turn count.
6. Recovery/purity bar chart.
