# Literature Index

Date: 2026-05-23

## Core Papers Collected

| File | Topic | Why it matters |
|---|---|---|
| `betyar_ramiar_2026_spiral_dep.pdf` | OpenFOAM spiral DEP separation of RBC and MDA-MB-231 cells | Closest OpenFOAM precedent for spiral DEP biological particle separation. |
| `patel_2011_curvature_induced_dep_spiral.pdf` | Curvature-induced DEP in double-spiral microchannels | Establishes spiral/curved-channel DEP as a continuous separation principle. |
| `yilmaz_2010_spiral_channel_dep_separator_thesis.pdf` | Spiral DEP separator with concentric electrodes | Useful for compact spiral electrode geometry and MEMS fabrication logic. |
| `choi_2018_nonviable_cell_removal_spiral_inertial.pdf` | Spiral inertial removal of small nonviable mammalian cells and debris | Connects spiral microchannels directly to nonviable-cell removal. |
| `patel_2012_reservoir_dep_live_dead_yeast.pdf` | Live/dead yeast separation using reservoir-based DEP | Gives viability-dependent DEP behavior and modeling context. |
| `elitas_2017_3d_carbon_dep_live_dead_monocytes.pdf` | Live/dead U937 monocyte separation using 3D carbon DEP | Mammalian live/dead DEP benchmark; useful voltage/frequency/flow ranges. |
| `shafiee_2010_cdep_live_dead_cells.html` | Contactless DEP live/dead leukemia cell isolation | Source page saved because direct PDF access returned HTML; still important for cDEP benchmark. |
| `martel_2012_inertial_focusing_spiral_microchannels_download_page.html` | Spiral inertial focusing | Download challenge page saved; use web/DOI source for reading until PDF is fetched manually or through browser. |

## Recent Additions

| File | Topic | Why it matters |
|---|---|---|
| `huang_2025_odep_live_dead_separation.pdf` | Optically induced DEP live/dead cell separation | Recent live/dead separation benchmark; reports live-cell recovery and purity targets. |
| `nguyen_2024_facing_electrode_dep_cell_separation.pdf` | Facing-electrode DEP numerical design for biological cell separation | Useful for electrode placement, trajectory modeling, and fabrication-simplifying electrode ideas. |
| `tian_2024_on_chip_dep_single_cell_manipulation_review.pdf` | DEP single-cell manipulation review | Useful for positioning, terminology, force scales, and modern DEP device taxonomy. |
| `altmann_2025_viable_legionella_dep_selection_download_page.html` | Video-quantified DEP selection of viable bacterial cells | Recent viability-selective DEP; PDF endpoint is protected, but the source is important for quantifiable response metrics. |

## Recent Sources To Fetch/Track

- Facing-electrode DEP cell separation, Scientific Reports 2024: https://doi.org/10.1038/s41598-024-78722-7
- On-chip DEP single-cell manipulation review, Microsystems & Nanoengineering 2024: https://doi.org/10.1038/s41378-024-00750-0
- Spiral inertial cell sorting review, Micromachines 2024: https://doi.org/10.3390/mi15091135
- Combined DEP and AC electrothermal flow numerical simulation, Micromachines 2024: https://doi.org/10.3390/mi15030345
- Viable Legionella DEP selection, Biomedical Microdevices 2025: https://doi.org/10.1007/s10544-025-00762-1
- High-efficiency ODEP live/dead separation, JAUSMT source page: https://www.jausmt.org/index.php/jausmt/article/view/342

## Source Links

- Betyar and Ramiar 2026: https://doi.org/10.5829/ijee.2026.17.01.13
- Curvature-induced DEP spiral paper: https://xcxuan.people.clemson.edu/BMF%285%29024111-2011.pdf
- Reservoir-based DEP live/dead yeast: https://xcxuan.people.clemson.edu/BMF%286%29034102-2012.pdf
- 3D carbon DEP live/dead monocytes: https://cecas.clemson.edu/~rodrigm/wp-content/uploads/2016/02/DEP-separation-of-live-and-dead-monocytes-using-3D-C-electrodes-Meltem.pdf
- Spiral DEP separator thesis: http://etd.lib.metu.edu.tr/upload/12612695/index.pdf
- Nonviable cell removal in spiral inertial microfluidics: https://doi.org/10.1039/C8LC00250A
- Contactless DEP live/dead isolation: https://doi.org/10.1039/B920590J
- Inertial focusing in spiral microchannels: https://pmc.ncbi.nlm.nih.gov/articles/PMC3311666/

## Immediate Reading Targets

1. Extract viable/dead dielectric parameter ranges.
2. Extract operating frequency and voltage windows.
3. Compare electrode strategies: side-wall electrodes, concentric electrodes, cDEP, iDEP, and 3D carbon DEP.
4. Identify what metrics are consistently reported: removal efficiency, recovery, purity, throughput, residence time, and viability after sorting.
5. Convert literature constraints into a first analytical design envelope.
6. Add Joule-heating and AC electrothermal-flow checks before claiming low-voltage operation is gentle.
7. Compare continuous deflection designs with trapping/release designs; choose one for the first device.

## Working Position

The new device should not be a direct copy of any single paper. It should combine:

- Spiral residence-time and compactness advantage.
- DEP tunability for viability-based sorting.
- Outlet geometry designed around purity/recovery metrics.
- OpenFOAM-based reproducible simulation workflow.
