# V6 Decision Summary

## Main Finding

V6 produced a high-accuracy candidate, but the max-accuracy design is not the
best scientific story.

- max-accuracy candidate: target correct `0.999`, tolerance target correct
  `0.920`, same-length straight DEP control `0.937`, synergy `0.062`
- balanced candidate: target correct `0.945`, tolerance target correct
  `0.922`, same-length straight DEP control `0.737`, synergy `0.178`

For a paper or project report, the balanced candidate is the stronger result
because it keeps performance above the `0.8` target while showing a clearer
spiral contribution.

## Selected V6 Candidate

- stage: `segmented_spiral`
- sample id: `164`
- frequency: `1388.6 kHz`
- voltage: `22.45 V`
- flow velocity: `2460 um/s`
- turns: `8.30`
- channel width: `194.5 um`
- inlet offset/spread: `-0.625` / `0.309`
- DEP active segment: `0.542` to `0.921`

## Validation Result

- nominal held-out target correct: `0.945 +/- 0.007`
- tolerance-perturbed target correct: `0.922 +/- 0.083`
- live recovery: `0.937`
- dead removal: `0.954`
- live outlet purity: `0.954`
- dead outlet purity: `0.938`
- wall loss: `0.000` in nominal held-out validation

## Controls

- same-length straight DEP: `0.737`
- spiral without DEP: `0.508`
- spiral DEP with unfocused inlet: `0.561`

Interpretation: DEP and inlet focusing are essential. The spiral contributes,
but it is not the sole mechanism. This is a defensible result if reported as a
compact spiral DEP design with segmented forcing and inlet focusing, not as a
pure spiral-only separator.

## Files

- optimization report: `README.md`
- balanced validation report: `balanced_synergy_validation/README.md`
- validation summary: `balanced_synergy_validation/posthoc_summary.csv`
- ParaView source: `balanced_synergy_validation/paraview/best_validation_particles.pvd`
- ParaView video: `balanced_synergy_validation/paraview/v6_balanced_paraview.mp4`
- trajectory still: `balanced_synergy_validation/paraview/render/v6_balanced_trajectories_still.png`

## Remaining Limitation

The current model is still a reduced-order particle model anchored by the
OpenFOAM electric-field statistics. It is not yet a full native OpenFOAM
Lagrangian DEP solver, and it does not model deformable cells or
cell-cell interactions. For this school-project scope, the current validation is
acceptable if the limitations and controls above are reported explicitly.
