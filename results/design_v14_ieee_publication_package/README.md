# V14 IEEE Publication Package

V14 repackages the validated V12/V13 reduced-order results with device-level publication figures and an IEEE-style two-column DOCX draft.

## What changed

- Replaced centerline-only main figures with finite-width channel ribbons.
- Added side-wall electrode traces, inlet arrow, two-outlet splitter, and dimension inset.
- Added a larger formula-defined geometry library with clearance screening metadata.
- Built a two-column IEEE-style DOCX manuscript draft.
- Kept the scientific claim bounded: this is still a reduced-order numerical design candidate.

## Final validated operating point

- target correct: `0.940 +/- 0.013`
- live recovery: `0.880`
- dead removal: `1.000`
- wall loss: `0.000`
- topology gain vs same-length straight DEP: `0.131`
- flow rate: `0.547 uL/min`
- active Joule-power proxy: `2.86 mW`

## Artifacts

- DOCX: `output/doc/spiral_dep_v14_ieee_publication_draft.docx`
- rendered PDF: `results/design_v14_ieee_publication_package/docx_render/spiral_dep_v14_ieee_publication_draft.pdf`
- rendered pages: `4`
- geometry library metadata: `results/design_v14_ieee_publication_package/v14_geometry_library.csv`
- figures: `results/design_v14_ieee_publication_package/figures/`

## Figures
- `workflow`: `results/design_v14_ieee_publication_package/figures/ref_workflow.png`
- `pareto`: `results/design_v14_ieee_publication_package/figures/ref_pareto.png`
- `thermal`: `results/design_v14_ieee_publication_package/figures/ref_thermal.png`
- `feature_importance`: `results/design_v14_ieee_publication_package/figures/ref_feature_importance.png`
- `device`: `results/design_v14_ieee_publication_package/figures/fig01_final_device_schematic.png`
- `library`: `results/design_v14_ieee_publication_package/figures/fig02_geometry_library_panel.png`
- `trajectory`: `results/design_v14_ieee_publication_package/figures/fig03_device_trajectory_overlay.png`
- `results_plate`: `results/design_v14_ieee_publication_package/figures/fig04_ieee_results_plate.png`
- `distribution`: `results/design_v14_ieee_publication_package/figures/fig05_outlet_distribution.png`

## Honesty note

The figures are publication-style, but publication readiness of the science still depends on a higher-fidelity electric-field/thermal validation stage. V14 is a strong manuscript draft, not final experimental proof.
