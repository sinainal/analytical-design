# OpenFOAM Design V2 Population DOE

V2 tests whether the V1 spiral DEP concept still looks promising when cells are
not represented by a single deterministic live/dead particle. It samples cell
diameter, membrane thickness, dielectric properties, and inlet position, then
evaluates design seeds separately from held-out validation seeds.

## How To Reproduce

```bash
python3 scripts/design_v2_population_sim.py
./scripts/render_design_v2_paraview_video.sh --skip-sim --width 960 --height 720
```

Run the wrapper without `--skip-sim` to regenerate the DOE before rendering.

## DOE Scope

- 105 design points: 3 turn counts x 7 voltages x 5 flow velocities.
- 6 stochastic replicates per design point.
- 3 design seeds and 3 held-out validation seeds.
- 150 live and 150 dead cells per replicate.

## Best Validation Case

- case: `turns_4_voltage_8_velocity_3000um_s`
- correct outlet assignment: `0.429`
- live recovery: `0.342`
- dead removal: `0.516`
- live outlet purity: `0.451`
- dead outlet purity: `0.503`
- wall loss: `0.109`

## Interpretation

This is not a strong separation result. It is a useful failure mode: once
population variability and wall loss are introduced, the earlier deterministic
V1 optimum no longer survives. The present geometry/field proxy is therefore
not ready to support publication-level claims.

The next modeling step is to replace the side-wall analytical DEP proxy with an
OpenFOAM-interpolated `grad(E^2)` field, then rerun the same held-out
validation protocol. If the metrics remain low, the design should move toward
segmented or facing electrodes instead of simply increasing voltage or spiral
length.

## Outputs

- `population_doe/v2_replicates.csv`: all replicate-level metrics.
- `population_doe/v2_design_summary.csv`: design-seed aggregate metrics.
- `population_doe/v2_validation_summary.csv`: held-out validation metrics.
- `population_doe/v2_selection.json`: selected design and validation summary.
- `population_doe/v2_*_heatmaps.png`: screening plots.
- `paraview/best_validation_trajectories.vtp`: full best-case trajectories.
- `paraview/best_validation_particles.pvd`: animated particle state index.
- `paraview/design_v2_best_validation_paraview.mp4`: ParaView-rendered video.
- `paraview/render/design_v2_best_validation_trajectories_still.png`: still render.

## Limitation

The current V2 particle dynamics still use a reduced-order channel and
side-wall field-gradient proxy. The outputs are ParaView-readable and
OpenFOAM-project organized, but the DEP force is not yet interpolated from the
OpenFOAM electric-field solution.
