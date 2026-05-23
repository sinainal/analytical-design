# OpenFOAM Design V1 Results

Design V1 is the first DOE-oriented optimization layer.

## What Is In This Folder

| Path | Purpose |
|---|---|
| `doe/` | 27-condition, 5-seed reduced-order DOE results and plots. |
| `paraview/` | ParaView-readable trajectory files and rendered V1 video. |

## Main Result

Best robust condition:

- turns: `5`
- voltage: `12 V`
- inlet velocity: `1000 um/s`
- mean correct classification: `86.3%`
- standard deviation across seeds: `0.7%`
- minimum seed result: `85.5%`

Interpretation: this passes the screening target but does not yet pass the
publication-level robustness target.

## Targets

- screening: `>=80%` correct classification
- publication-level: mean `>=90%` and minimum replicate/seed result `>=90%`

## ParaView Outputs

Open directly in ParaView:

- `paraview/best_case_particles.pvd`
- `paraview/best_case_trajectories.vtp`

Rendered media:

- `paraview/design_v1_best_case_paraview.mp4`
- `paraview/render/design_v1_best_trajectories_still.png`

The V1 video is generated through ParaView/pvpython, then encoded from rendered
frames.
