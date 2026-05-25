# Design V7 Geometry Feasibility

V7 compares geometry families using both separation metrics and device
feasibility proxies. It is intentionally stricter than V6: high accuracy
alone is not considered enough.

## Best Current Candidate

- family: `stepwise_late_dep_spiral`
- target correct: `0.914 +/- 0.014`
- topology gain vs same-length straight DEP: `0.239`
- wall loss: `0.000`
- live recovery: `0.875`
- dead removal: `0.953`
- live/dead outlet purity: `0.949` / `0.884`
- length: `64.4 mm`
- residence time: `36.9 s`
- pressure drop proxy: `0.65 kPa`
- active Joule power proxy: `5.90 mW`
- adiabatic temperature-rise proxy: `87.9 C`
- steady substrate temperature-rise proxy: `1.6 C`
- thermal risk: `low`
- passes V7 gate: `True`

## Interpretation

Two thermal proxies are reported. The adiabatic proxy is a no-cooling
upper-bound warning and should not be read as actual chip temperature.
The steady substrate proxy assumes first-order heat loss through a 1 mm
PDMS/glass support. A full thermal solve is still required before any
experimental safety claim.

## Literature/Device Comparison

| Reference/device class | Reported strength | V7 use |
|---|---|---|
| Nguyen et al. 2024 facing-electrode DEP, Scientific Reports | numerical SE/purity, high-efficiency cell enrichment; also reports wall/voltage trade-offs | benchmark for reporting SE, purity, voltage and geometry factors |
| Huang et al. 2025 ODEP live/dead | live recovery about 78.3%, live purity about 96.4% | live/dead experimental benchmark |
| Elitas et al. 2017 3D carbon DEP live/dead | dead-cell removal around 90% | mammalian live/dead DEP parameter benchmark |
| Circular OpenFOAM DEP, DOI 10.1016/j.apt.2023.104046 | public abstract reports 100% purity/efficiency in selected numerical cases | warning that deterministic DEP models can overstate performance |
| Stepwise multi-stage DEP + microfilter, DOI 10.1016/j.talanta.2024.126585 | staged electrodes and microfilter improve stability/purity | inspiration for non-smooth, staged V8 geometries |

## Files

- `v7_screening_rows.csv`: all geometry-screening runs
- `v7_validation_summary.csv`: held-out validation and controls
- `v7_control_rows.csv`: same-length straight, no-DEP, and unfocused controls
- `v7_accuracy_vs_joule_power.png`
- `v7_validation_controls.png`
- `v7_length_vs_validated_correct.png`
- `paraview/v7_best_particles.pvd`: ParaView particle animation source
- `paraview/v7_best_trajectories.vtp`: full particle trajectories
- `paraview/v7_best_paraview.mp4`: rendered V7 animation

The `stepwise` V7 candidate is currently modeled as late segmented DEP
activation, not as a serrated physical channel wall. The ParaView animation
therefore shows the spiral path and particle motion; electrode staging is
encoded in the force model and reported by `dep_start_fraction` /
`dep_end_fraction`.
