# V12 Final Optimization Package

## Selected Design

- family: `monotone_curvature_spiral`
- target correct: `0.940 +/- 0.013`
- topology gain vs same-length straight DEP: `0.131`
- flow rate: `0.547 uL/min`
- voltage: `20.36 V`
- electrode gap: `72.9 um`
- active Joule power proxy: `2.86 mW`
- steady substrate delta-T proxy: `3.89 C`
- passes final gate: `True`

## Produced Artifacts

- DOCX report: `output/doc/spiral_dep_v12_final_optimization_report.docx`
- Tables: `v12_operating_screen.csv`, `v12_final_validation_replicates.csv`, `v12_final_validation_summary.csv`
- Figures: `figures/`

## Honest Limitation

V12 is a manuscript-facing reduced-order design package. The selected geometry should be rebuilt with electrode-resolved OpenFOAM/FEM fields before final publication claims.

## Figure List

- `geometry`: `results/design_v12_final_package/figures/fig01_final_geometry.png`
- `geometry_controls`: `results/design_v12_final_package/figures/fig02_geometry_controls.png`
- `evolution`: `results/design_v12_final_package/figures/fig03_design_evolution.png`
- `ml_importance`: `results/design_v12_final_package/figures/fig04_ml_feature_importance.png`
- `pareto_power`: `results/design_v12_final_package/figures/fig05_operating_pareto_power.png`
- `flow_tradeoff`: `results/design_v12_final_package/figures/fig06_flowrate_tradeoff.png`
- `thermal_map`: `results/design_v12_final_package/figures/fig07_thermal_map.png`
- `hydraulics`: `results/design_v12_final_package/figures/fig08_hydraulic_envelope.png`
- `metrics`: `results/design_v12_final_package/figures/fig09_final_metrics.png`
- `controls`: `results/design_v12_final_package/figures/fig10_final_controls.png`
- `final_table`: `results/design_v12_final_package/figures/fig11_selected_operating_point.png`
- `workflow`: `results/design_v12_final_package/figures/fig12_workflow.png`
