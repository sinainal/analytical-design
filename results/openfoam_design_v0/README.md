# OpenFOAM Design V0 Result

## Why This Was Generated

This is the first OpenFOAM-backed device check for the project. The goal is to
verify that an Archimedean spiral DEP channel can be generated as a valid
OpenFOAM mesh and can support a first electric-potential solve between side-wall
electrodes.

## Generator

Run from the repository root:

```bash
python3 scripts/design_v0_geometry.py
source /usr/lib/openfoam/openfoam2312/etc/bashrc
./cases/design_v0/Allrun
```

## Compact Result

- Case directory: `cases/design_v0/`
- Mesh cells: `3840` hexahedra
- Boundary patches: inlet, inner outlet, outer outlet, inner electrode, outer
  electrode, top wall, bottom wall
- `checkMesh`: passed
- Electric potential proxy: `T`
- Electrode values: inner wall `8 V`, outer wall `0 V`
- `laplacianFoam`: solved one step
- Final residual for first potential correction: `3.3127437e-11`
- Potential range after solve: `0` to `8`

## ParaView

Open `cases/design_v0/design_v0.foam` in ParaView. The generated case includes
the valid mesh and, after running `Allrun`, local unversioned time output for the
solved potential field.

Automated rendering:

```bash
./scripts/render_design_v0_video.sh --frames 72 --width 1280 --height 720
```

Generated media:

- `results/openfoam_design_v0/paraview/design_v0_potential_still.png`
- `results/openfoam_design_v0/paraview/frames/frame_*.png`
- `results/openfoam_design_v0/design_v0_paraview_orbit.mp4`

On this workstation ParaView can write all frames but may return a GLX context
warning at shutdown. The wrapper treats this as non-fatal if the frames exist
and then encodes the video with OpenCV.

## Fixed-Camera Trajectory Animation

The first reduced-order live/dead particle animation is stored in:

- `results/openfoam_design_v0/trajectories/design_v0_trajectory_video.mp4`
- `results/openfoam_design_v0/trajectories/design_v0_trajectory_plot.png`

This animation uses a fixed camera. The spiral does not rotate; particles move
through the channel.

Current first-pass trajectory metric:

- live to inner outlet: `77 / 100`
- dead to outer outlet: `58 / 100`
- correct live-inner/dead-outer classification: `67.5%`

## Limitations

This is not yet a full live/dead cell separation simulation. It validates the
mesh and side-wall potential solve only. The next layer must add:

1. Electric-field and `grad(E^2)` post-processing.
2. DEP force calculation at the selected `455 kHz` frequency.
3. Live/dead particle trajectory tracking.
4. Outlet metrics and plots.
