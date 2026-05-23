# Design V0 OpenFOAM Status

Date: 2026-05-23

## What Was Built

The first OpenFOAM-backed `design_v0` case has been generated in
`cases/design_v0/`.

It uses an Archimedean spiral channel matching the first design specification:

- turns: `3`
- inner radius: `1000 um`
- channel width: `120 um`
- channel height: `50 um`
- pitch: `180 um`
- inlet: `1`
- outlets: inner and outer split
- inner side-wall electrode: `8 V`
- outer side-wall electrode: `0 V`

The mesh is generated directly as OpenFOAM `polyMesh` by
`scripts/design_v0_geometry.py`.

## OpenFOAM Validation

Command:

```bash
source /usr/lib/openfoam/openfoam2312/etc/bashrc
./cases/design_v0/Allrun
```

Validation result:

- `checkMesh`: passed
- cells: `3840`
- cell type: all hexahedra
- boundary patches: `7`
- max aspect ratio: `7.0084028`
- max non-orthogonality: `1.1531408`
- max skewness: `0.098276062`
- mesh status: `Mesh OK`

## First Electric Solve

The case currently uses OpenFOAM `laplacianFoam` with scalar field `T` as the
first electric-potential proxy.

Reason:

- `laplacianFoam` is already available in the local OpenFOAM installation.
- It lets us validate the electrode boundary conditions immediately.
- A later custom `phiE` workflow can replace this without changing the geometry.

Result:

- inner electrode: fixed `8`
- outer electrode: fixed `0`
- potential range after solve: `0` to `8`
- first solver residual: from `1` to `3.3127437e-11` in `17` iterations

## Current Scientific Meaning

This proves that the spiral geometry can be represented as a valid OpenFOAM
case and that a side-wall potential solve can run on it. It does not yet prove
cell separation.

The next scientifically meaningful result will come from computing the electric
field gradient and tracking live/dead cells using the selected `455 kHz`
Clausius-Mossotti values.

## Next Step

Add a trajectory layer:

1. Read OpenFOAM mesh and potential output.
2. Compute `E = -grad(T)`.
3. Compute a DEP proxy from `Re(CM) * grad(E^2)`.
4. Track live/dead particles through the spiral.
5. Report outlet assignment, recovery, purity, and stalling count.
