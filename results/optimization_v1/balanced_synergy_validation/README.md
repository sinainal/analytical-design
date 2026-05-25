# Balanced Synergy Candidate Validation

This run validates the best candidate selected by positive spiral synergy
under a useful accuracy constraint, rather than by maximum accuracy alone.

## Candidate

- stage: `segmented_spiral`
- sample id: `164`
- optimizer target correct: `0.947`
- optimizer wall loss: `0.000`
- synergy score in screening: `0.178`
- spiral DEP on / straight DEP on: `0.931` / `0.753`
- voltage: `22.45 V`
- frequency: `1388.6 kHz`
- flow velocity: `2460 um/s`
- turns: `8.30`
- channel width: `194.5 um`
- inlet offset/spread: `-0.625` / `0.309`
- DEP segment: `0.542` to `0.921`

## Held-out Results

- nominal held-out target correct: `0.945` +/- `0.007`
- tolerance-perturbed target correct: `0.922` +/- `0.083`
- same-length straight DEP target correct: `0.737`
- spiral without DEP target correct: `0.508`
- spiral DEP with unfocused inlet target correct: `0.561`

## ParaView Outputs

- animation source: `paraview/best_validation_particles.pvd`
- full trajectories: `paraview/best_validation_trajectories.vtp`
- rendered video: `paraview/v6_balanced_paraview.mp4`
- still render: `paraview/render/v6_balanced_trajectories_still.png`

The pvpython render completed all 110 frames, then the local ParaView process
reported a shutdown-time X/GL segmentation fault. The rendered files were
verified after the crash and the MP4 was encoded from the saved frames.

## Interpretation

This is a better paper-facing candidate than the max-accuracy design if
we want to argue that the spiral contributes beyond residence time. It
still depends strongly on DEP and inlet focusing, but the straight-channel
control is lower, so the spiral-specific contribution is more defensible.
