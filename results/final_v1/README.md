# Final Feasibility and Feature Analysis

This package defines a literature-bounded feasible envelope and a decision-tree feature-importance reality check for the next spiral DEP live/dead sorting optimization.

## Key conclusion

The current reduced-order data are useful for screening, but turn count and ellipticity must be isolated in a controlled experiment before claiming spiral-specific mechanism. Decision trees show that width, velocity/residence, field variables, inlet focusing, and geometry class dominate the current model.

## Outputs

- DOCX report: `output/doc/feasibility_feature_analysis_report.docx`
- rendered PDF: `results/final_v1/docx_render/feasibility_feature_analysis_report.pdf`
- rendered page count: `5`
- feasible ranges: `results/final_v1/literature_feasible_ranges.csv`
- equations: `results/final_v1/latex_equations.tex`
- feature catalogue: `results/final_v1/feature_catalog.csv`
- feature importance: `results/final_v1/decision_tree_feature_importance.csv`
- tree rules: `results/final_v1/decision_tree_rules_target_correct.txt`, `results/final_v1/decision_tree_rules_design_score.txt`
- model diagnostics: `results/final_v1/model_diagnostics.json`

## Diagnostics

- target_correct decision tree test R2: `0.373`
- target_correct decision tree test MAE: `0.077`
- design_score decision tree test R2: `0.648`
- design_score decision tree test MAE: `0.104`

## Figures
- `feasible_envelope`: `results/final_v1/figures/fig01_literature_feasible_envelope.png`
- `tree_importance`: `results/final_v1/figures/fig02_decision_tree_importance.png`
- `turn_ellipticity`: `results/final_v1/figures/fig03_turn_ellipticity_space.png`
- `reality_check`: `results/final_v1/figures/fig04_reality_check_accuracy_drivers.png`
- `tree_structure`: `results/final_v1/figures/fig05_decision_tree_structure.png`
