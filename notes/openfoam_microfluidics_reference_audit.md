# OpenFOAM Microfluidics Reference Audit

Date: 2026-05-24

## Bottom Line

The current Design V2 workflow is more realistic than V1 because it adds
population variability, held-out seeds, wall loss, and multiple separation
metrics. It is still not a fully realistic microfluidic cell-device simulation.

The main missing layer is field-coupled particle tracking:

- solve `U` in OpenFOAM, not prescribe a centerline velocity
- solve electric potential in OpenFOAM
- compute `E = -grad(phiE)` and `grad(|E|^2)` from the OpenFOAM field
- interpolate `U` and `grad(|E|^2)` to each particle position
- integrate particles in the actual 3D channel geometry
- classify outlets and wall interactions from mesh patches

Until that layer exists, the model should be described as a reduced-order
screening model, not a publication-grade device simulator.

## GitHub / Open Source References Checked

### G1: `gregnordin/openfoam_for_microfluidics`

URL: https://github.com/gregnordin/openfoam_for_microfluidics

What it is:

- Educational OpenFOAM microfluidics repository.
- Uses `icoFoam` for low-Reynolds-number velocity fields.
- Uses `scalarTransportFoam` for time-dependent analyte diffusion after the
  velocity field exists.
- Uses ParaView plus Python/Jupyter for visualization and line/plane sampling.
- Includes a custom `parabolicVelocity` inlet boundary condition.

What we should borrow:

- A real inlet velocity profile instead of a uniform inlet value.
- A staged workflow: mesh, solve flow, solve field/transport, post-process,
  then analyze with Python.
- `postProcess` sampling and line/plane extraction as a standard part of each
  simulation run.
- A clean distinction between base cases and large generated run outputs.

Direct implication for Design V3:

- Replace the present uniform `U` initialization with either a parabolic inlet
  boundary condition or an explicitly generated fully developed inlet profile.
- Add centerline and cross-section sampling of `U`, `phiE`, `|E|^2`, and
  `grad(|E|^2)`.

### G2: `gerlero/porousMicroTransport`

URL: https://github.com/gerlero/porousMicroTransport

What it is:

- OpenFOAM solver/library set for paper-based microfluidics.
- Provides reproducible solver, test, Docker, tutorial, and CI organization.
- Supports multiple OpenFOAM.com versions including v2312.
- Uses small tests with `Allrun`, `Allclean`, Python checks, and explicit
  OpenFOAM dictionaries.

What we should borrow:

- Keep reusable OpenFOAM code separate from case-generation scripts.
- Add tests that run a minimal case and assert numerical behavior.
- Keep a Docker/container path in mind for reproducibility.
- Use `Allrun` and `Allclean` consistently for every real case.

Direct implication for Design V3:

- Add a minimal verification case before the spiral:
  1. straight channel flow
  2. analytical or simple side-wall electric field
  3. known-sign DEP migration
  4. outlet/wall classification check

### G3: OpenFOAM Lagrangian Particle Tracking

Source:

- OpenFOAM particle tracking release note:
  https://openfoam.org/release/2-0-0/particle-tracking/
- Local OpenFOAM tutorial:
  `/usr/lib/openfoam/openfoam2312/tutorials/lagrangian/icoUncoupledKinematicParcelFoam/hopper`

What it provides:

- Native OpenFOAM parcel injection files.
- Particle drag, gravity, patch interactions, and collision model structure.
- Field interpolation to particles, e.g. `U cellPoint`.

What we should borrow:

- Use OpenFOAM-style injection files or generate equivalent VTK/CSV files from
  the same particle specification.
- Treat wall contact as a real patch interaction, not only a lateral coordinate
  clipping rule.
- Use cell-point interpolation logic as the model target even if the first
  implementation remains Python-side.

Direct implication for Design V3:

- Either build a small custom OpenFOAM particle-force extension, or export
  OpenFOAM fields and use a Python tracker that interpolates fields from the
  actual mesh.
- The faster near-term route is Python field interpolation from VTK/OpenFOAM
  outputs. The longer-term route is a custom OpenFOAM Lagrangian force model.

## Literature Support Rechecked

### L1: DLD + DEP CFD-DEM paper

URL: https://www.mdpi.com/2674-0516/4/2/13

Relevant modeling structure:

- OpenFOAM solves velocity and electric fields.
- LIGGGHTS/CFDEM handles particle dynamics, particle-particle, and
  particle-wall interactions.
- DEP forces are transferred to particles from the calculated electric field.
- Reports partition curves and separation sharpness, not only single accuracy.

Implication:

- Our current V2 is weaker because it has no resolved particle-wall/contact
  mechanics and no field-coupled DEP force.
- If cell concentration is high enough for interactions, OpenFOAM-only plus
  Python may be insufficient; CFDEM/LIGGGHTS or a dilute-limit justification is
  needed.

### L2: Particle and cell separation modeling review

URL: https://www.mdpi.com/2227-9717/10/6/1226

Relevant modeling structure:

- Reviews Lagrangian particle trajectories under drag and active forces.
- Emphasizes mesh dependency studies.
- Notes OpenFOAM as an FVM tool, but DEP particle manipulation is not built in
  by default.

Implication:

- We should not expect stock OpenFOAM alone to make a realistic DEP cell sorter.
  We need project-specific DEP force coupling and validation.

### L3: OpenFOAM DEP separation papers with no open code found

Examples found:

- Circular microchannel DEP separation using an OpenFOAM-developed code:
  https://doi.org/10.1016/j.apt.2023.104046
- Wall-obstacle ternary DEP separation using an OpenFOAM-developed code:
  https://doi.org/10.1016/j.chroma.2023.464079

Implication:

- These papers support the method choice: OpenFOAM can be used for DEP
  microfluidic separation.
- But the developed solvers do not appear to be openly available from the
  sources checked, so we cannot honestly claim we are reusing an open DEP
  microfluidic solver.

## What "Fully Realistic" Should Mean For Our Project

For our next serious simulation version, "realistic" should mean:

1. Geometry realism
   - 3D channel height and width, not only a 2D centerline.
   - Real inlet and outlet patches.
   - Mesh quality checks including non-orthogonality and face-tet validity for
     particle tracking.

2. Flow realism
   - Low-Re laminar flow solved by OpenFOAM.
   - Inlet flow-rate or parabolic velocity boundary condition.
   - Outlet pressure/flow split measurement.
   - Dean-flow/secondary-flow relevance checked by Reynolds and Dean numbers.

3. Electric-field realism
   - `phiE` solved in OpenFOAM with real electrode/insulating patches.
   - `E`, `|E|^2`, and `grad(|E|^2)` computed from the mesh field.
   - Mesh-independence check for both field gradient and particle outlet.

4. Cell realism
   - Live/dead dielectric parameter distributions.
   - Diameter overlap.
   - Frequency-dependent CM factor.
   - Random inlet position and vertical position.
   - Dilute-limit assumption stated, or particle-particle interactions modeled.

5. Force realism
   - Hydrodynamic drag from local relative velocity.
   - DEP force from local `grad(|E|^2)`.
   - Near-wall loss or adhesion rule.
   - Optional Brownian motion can be omitted for 20 um mammalian cells but
     should be documented.

6. Device realism
   - Joule-heating/electrothermal risk estimate.
   - Residence time and throughput.
   - Voltage/frequency limits.
   - Outlet purity, recovery, dead removal, and wall loss reported together.

7. Validation realism
   - Mesh independence.
   - Held-out random seeds.
   - Sensitivity to fabrication tolerances.
   - Negative controls: no DEP, reversed DEP sign, shuffled cell labels.

## V3 Implementation Recommendation

Do not optimize yet. First build a realistic baseline pipeline:

1. `cases/design_v3_straight_validation`
   - straight rectangular channel
   - parabolic inlet
   - simple side-wall electrode pair
   - OpenFOAM flow + electric solve
   - field-exported particle tracking
   - verifies that pDEP/nDEP signs move correctly

2. `cases/design_v3_spiral_baseline`
   - spiral geometry with the same field-coupled tracker
   - 3D inlet distribution
   - two outlets
   - no optimization, only one defensible baseline condition

3. `results/openfoam_design_v3`
   - OpenFOAM field plots
   - particle trajectories
   - ParaView video
   - mesh/field/particle validation report

Only after V3 passes these checks should DOE optimization start.

## Immediate Changes To Make Before Optimization

- Add OpenFOAM post-processing for `grad(phiE)`, `magSqr(E)`, and
  `grad(magSqr(E))`.
- Export fields to VTK or sample them on a structured grid.
- Replace the analytical side-wall DEP proxy in `design_v2_population_sim.py`
  with interpolated OpenFOAM field values.
- Add vertical cell position distribution.
- Report whether particle trajectories ever leave the mesh, hit walls, or pass
  through invalid regions.
- Add a "no DEP" baseline to prove the observed separation is not only the
  outlet geometry.

## Current Confidence

Current confidence that V2 is a good screening model: medium.

Current confidence that V2 is a fully realistic cell-device simulation: low.

Current confidence that OpenFOAM can support a realistic next version: high,
provided we add field-coupled particle tracking and validation.
