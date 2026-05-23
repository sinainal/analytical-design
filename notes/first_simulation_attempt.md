# First Simulation Attempt: Live/Dead DEP Frequency Window

Date: 2026-05-23

This is the first numerical design check for the proposed spiral-DEP
live/dead cell separator. It is not yet an OpenFOAM flow simulation. Its role is
to choose a defensible electric operating window before building the coupled
spiral channel model.

## Model

The scan uses the single-shell live/dead mammalian cell model recorded in
`notes/cell_properties.md`. The modeled output is the real part of the
Clausius-Mossotti factor:

`Re(CM) = Re((epsilon_cell_eff - epsilon_medium) / (epsilon_cell_eff + 2 epsilon_medium))`

The frequency range is 1 kHz to 10 MHz in a low-conductivity medium
(`0.002 S/m`).

## First Result

The strongest live/dead contrast in the current parameter set occurs at:

- Selected frequency: `455326 Hz`
- Live cell `Re(CM)`: `0.976616`
- Dead cell `Re(CM)`: `-0.000044`
- Dead minus live contrast: `-0.976660`

Interpretation: live cells are predicted to experience strong positive DEP,
while dead cells are close to DEP-neutral at this frequency. This supports a
first design strategy where live cells are pulled laterally toward the electrode
side and dead cells remain dominated by hydrodynamic/inertial transport.

## Generated Outputs

- `results/cm_factor/design_v0_cm_factor.csv`
- `results/cm_factor/design_v0_cm_summary.txt`
- `results/cm_factor/design_v0_cm_factor.png`

## Design Implication

For the first OpenFOAM-backed geometry run, use `455 kHz` as the baseline
frequency and treat voltage as the main sweep variable. The next simulation
should combine:

1. Spiral channel velocity field.
2. Electric potential field around sidewall electrodes.
3. Particle trajectory integration using Stokes drag plus DEP force.
4. Outlet classification for live/dead populations.

This keeps the first coupled simulation small enough to debug while still being
traceable to literature-derived material parameters.
