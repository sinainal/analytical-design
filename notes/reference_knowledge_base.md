# Reference Knowledge Base

Date: 2026-05-23

This file assigns stable reference numbers for later manuscript drafting. Use these numbers consistently in outlines, figure captions, and draft paragraphs.

## Reference List

| Ref | Source | Local file/status | Main use |
|---|---|---|---|
| R1 | Betyar and Ramiar, "Numerical Simulation of Biological Particle Separation in a Spiral Microchannel Using the Dielectrophoresis Mechanism", 2026. DOI: https://doi.org/10.5829/ijee.2026.17.01.13 | `papers/betyar_ramiar_2026_spiral_dep.pdf` | OpenFOAM spiral DEP precedent; voltage/turn/velocity sweep logic. |
| R2 | Patel and Xuan, curvature-induced DEP in spiral/curved microchannels, 2011. Source: https://xcxuan.people.clemson.edu/BMF%285%29024111-2011.pdf | `papers/patel_2011_curvature_induced_dep_spiral.pdf` | Spiral/curved-channel DEP principle. |
| R3 | Yilmaz, "Spiral Channel Dielectrophoretic Separator", thesis, 2010. Source: http://etd.lib.metu.edu.tr/upload/12612695/index.pdf | `papers/yilmaz_2010_spiral_channel_dep_separator_thesis.pdf` | Spiral DEP geometry/electrode precedent. |
| R4 | Kwon/Choi et al., "Continuous removal of small nonviable suspended mammalian cells and debris from bioreactors using inertial microfluidics", Lab on a Chip, 2018. DOI: https://doi.org/10.1039/C8LC00250A | `papers/choi_2018_nonviable_cell_removal_spiral_inertial.pdf` | Spiral dead/nonviable-cell handling and benchmark metrics. |
| R5 | Elitas et al., "Dielectrophoretic Separation of Live and Dead Monocytes Using 3D Carbon-Electrodes", Sensors, 2017. | `papers/elitas_2017_3d_carbon_dep_live_dead_monocytes.pdf` | Mammalian live/dead DEP parameters and benchmark. |
| R6 | Patel et al., reservoir-based DEP live/dead yeast separation, Biomicrofluidics, 2012. Source: https://xcxuan.people.clemson.edu/BMF%286%29034102-2012.pdf | `papers/patel_2012_reservoir_dep_live_dead_yeast.pdf` | Live/dead DEP phase-window logic. |
| R7 | Shafiee et al., "Selective isolation of live/dead cells using contactless dielectrophoresis", Lab on a Chip, 2010. DOI: https://doi.org/10.1039/B920590J | `papers/shafiee_2010_cdep_live_dead_cells.html` | cDEP live/dead benchmark. |
| R8 | Martel and Toner, inertial focusing in spiral microchannels, 2012. PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC3311666/ | `papers/martel_2012_inertial_focusing_spiral_microchannels_download_page.html` | Spiral hydrodynamics and inertial focusing background. |
| R9 | Huang et al., "Label-free Live and Dead Cell Separation Method Using a High-Efficiency Optically-Induced Dielectrophoretic Force-based Microfluidic Platform", 2025 local copy. | `papers/huang_2025_odep_live_dead_separation.pdf` | Recent ODEP live/dead recovery/purity target. |
| R10 | Nguyen et al., facing-electrode DEP cell separation, Scientific Reports, 2024. DOI: https://doi.org/10.1038/s41598-024-78722-7 | `papers/nguyen_2024_facing_electrode_dep_cell_separation.pdf` | DEP numerical modeling workflow, SE/SP metrics, electrode variables. |
| R11 | Tian et al., on-chip DEP single-cell manipulation review, Microsystems & Nanoengineering, 2024. DOI: https://doi.org/10.1038/s41378-024-00750-0 | `papers/tian_2024_on_chip_dep_single_cell_manipulation_review.pdf` | Modern DEP taxonomy, electrode design, risks/limitations. |
| R12 | Altmann et al., viable Legionella DEP selection, Biomedical Microdevices, 2025. DOI: https://doi.org/10.1007/s10544-025-00762-1 | `papers/altmann_2025_viable_legionella_dep_selection_download_page.html` | Recent viability-selective DEP quantification. |
| R13 | Huang 2014 DLD review, Lab on a Chip. DOI: https://doi.org/10.1039/C4LC00939H | `papers/huang_2014_dld_particle_separation_review.html` | Non-DEP passive separation background. |
| R14 | DLD viable/nonviable cell separation conference paper, 2015. Source: https://www.rsc.org/images/LOC/2015/PDFs/Papers/0404_M.025a.pdf | `papers/dld_2015_viable_nonviable_cells_conference.pdf` | Non-DEP, non-spiral viable/nonviable comparison. |
| R15 | DEP + AC electrothermal numerical simulation, Micromachines, 2024. DOI: https://doi.org/10.3390/mi15030345 | to fetch/track | Thermal and AC electrothermal risk. |
| R16 | Spiral inertial cell sorting review, Micromachines, 2024. DOI: https://doi.org/10.3390/mi15091135 | to fetch/track | Spiral geometry review and bioprocess positioning. |

## Foundational Claims For The Manuscript

### C1. Spiral channels are relevant to dead/nonviable-cell removal.

Evidence:

- R4 demonstrates continuous removal of small nonviable mammalian cells and debris in spiral inertial microfluidics.
- R8 and R16 support the broader physical basis of spiral inertial focusing and spiral channel design.

How to use:

> Spiral microchannels have already been explored for nonviable-cell/debris removal, but these approaches primarily exploit inertial focusing and size/deformability effects.

### C2. Inertial spiral separation alone is limited by size overlap.

Evidence:

- R4 reports that viable and nonviable cell size distributions can overlap, limiting single-pass dead-cell removal.

How to use:

> Because viable and nonviable populations may overlap in size, a viability-specific force mechanism is desirable.

### C3. DEP can distinguish live and dead cells through frequency-dependent polarizability.

Evidence:

- R5 explains that viable and nonviable cells polarize differently and uses crossover frequency as a dielectric descriptor.
- R6 demonstrates a live/dead operating window using AC/DC field ratios.
- R7, R9, and R12 support live/dead or viability-selective DEP as an established principle.

How to use:

> DEP provides an electrical contrast mechanism that is not purely size-based.

### C4. Spiral DEP exists, but not as exact live/dead spiral DEP in the current matrix.

Evidence:

- R1, R2, and R3 show spiral DEP devices or simulations.
- The local `paper_matrix/S1_D1_T1` exact-match folder is empty.

How to use:

> The current literature matrix indicates separate precedents for spiral DEP and live/dead DEP, but no exact continuous spiral DEP live/dead sorting paper has been identified.

### C5. Spiral geometry can lower voltage demand by increasing interaction length.

Evidence:

- R1 reports that increasing the number of spiral turns reduces the required potential difference for separation in a spiral DEP device.
- R2 and R3 support curved/spiral DEP interaction concepts.

How to use:

> We treat the spiral as a compact residence-time and interaction-length amplifier for DEP.

### C6. The manuscript should use explicit separation efficiency and purity metrics.

Evidence:

- R10 defines separation efficiency as target particles reaching their target outlet divided by target particles injected.
- R10 defines separation purity as target particles at an outlet divided by all particles collected at that outlet.
- R4, R5, and R9 report related recovery, purity, retention, and removal metrics.

How to use:

> We report outlet classification, recovery, purity, and separation efficiency rather than only trajectory plots.

### C7. Thermal and electrothermal risks must be addressed.

Evidence:

- R9 notes that AC electroosmosis and electrothermal forces can be neglected only under specific voltage/frequency conditions.
- R11 discusses DEP device limitations related to conductivity, heating, and electrode configuration.
- R15 is reserved for explicit thermal/ACET modeling support.

How to use:

> Low-voltage claims must be accompanied by at least a Joule-heating estimate.

## Quantitative Values To Reuse Carefully

### Live/dead mammalian DEP model seed

From R5:

- live U937 diameter: about `23 um`
- dead U937 diameter: about `22 um`
- membrane thickness: `7 nm`
- membrane permittivity: `12.5 epsilon0`
- live cytoplasm conductivity: `0.5 S/m`
- live cytoplasm permittivity: `50 epsilon0`
- live membrane conductivity: `1e-6 S/m`
- dead cytoplasm conductivity: `0.002 S/m`
- dead cytoplasm permittivity: `80 epsilon0`
- dead membrane conductivity: `0.01 S/m`
- medium conductivity: `0.002 S/m`
- medium permittivity: `80 epsilon0`
- effective experimental condition: `20 Vpp`, `300 kHz`, `1 uL/min`
- reported dead-cell removal: about `90%`

Use:

- Build the first CM-factor curve.
- Use near-equal live/dead diameters to avoid hidden size-only separation.

### ODEP benchmark values

From R9:

- voltage sweep: `2, 4, 6, 8 V`
- selected operating voltage: `8 V`
- live-cell manipulation force: about `49.4 pN`
- dead-cell manipulation force: about `-20.1 pN`
- live-cell recovery: about `78.3%`
- live-cell purity: about `96.4%`
- medium conductivity: `3.4 uS/cm`

Use:

- Benchmark force scale and reporting style.
- Support target purity/recovery metrics.

### Spiral DEP study structure

From R1:

- target biological particles: RBC and MDA-MB-231
- one inlet, two outlets
- side-wall electrodes
- channel width: `100 um`
- inner radius: `1000 um`
- outlet widths: `50 um`
- velocities: `1000, 3000, 5000 um/s`
- voltage increment: `1 V`
- OpenFOAM custom solver

Use:

- Borrow sweep structure, not target biology.
- Use voltage-threshold maps vs turns and velocity.

### Facing-electrode DEP numerical workflow

From R10:

- flow and electric field simulated numerically
- factors swept: voltage, velocity ratio, electrode angle, channel height, number of electrodes
- medium conductivity example: `55 mS/m`
- representative frequency: `1 kHz`
- reported ideal-condition separation efficiency: `99.4%`
- reported cell-type SE values include `80%`, `74%`, `100%`, and `86%` for different target classes in one configuration

Use:

- Define SE/SP formulas.
- Consider facing-electrode variant if side-wall spiral is too position-sensitive.

## Manuscript Paragraph Templates

### Intro gap template

Spiral microchannels have been used for label-free cell and particle handling, including nonviable-cell and debris removal, mainly through inertial focusing mechanisms [R4, R8, R16]. In parallel, DEP has been used to exploit viability-dependent dielectric differences between live and dead cells in non-spiral devices [R5-R7, R9, R12]. Spiral DEP has also been investigated for biological particle separation and has shown that longer spiral paths can reduce the required voltage for separation [R1-R3]. However, the current literature matrix did not identify an exact continuous spiral DEP design for viable/nonviable mammalian-cell sorting. This motivates the present analytical and numerical design study.

### Method template

The device is modeled as an Archimedean spiral microchannel with one inlet and two outlets. The electric field is solved to obtain the DEP-driving field gradient, while laminar flow and Lagrangian particle tracking are used to compute live and dead cell trajectories. DEP forces are computed using the Clausius-Mossotti formalism, and Stokes drag is used for the low-Reynolds-number particle motion [R5, R10]. Device performance is evaluated using outlet classification, recovery, purity, separation efficiency, and threshold voltage.

### Discussion template

The proposed design should be interpreted as combining two previously separate advantages: spiral-channel residence-time enhancement and DEP-based viability selectivity. Inertial spiral methods can process nonviable-cell mixtures at high throughput but are limited by size overlap [R4]. DEP methods can target viability-dependent electrical differences but are commonly implemented in non-spiral geometries [R5-R7, R9]. A spiral DEP architecture therefore has the potential to reduce the voltage required for continuous live/dead sorting by extending the interaction length in a compact footprint [R1-R3].

## Next Required Deliverables

1. `cell_properties.md`: structured table of live/dead dielectric parameters.
2. `cm_factor_model.py`: script to plot `Re(CM)` vs frequency.
3. `design_v0_spec.md`: exact geometry, electrodes, flow, frequency, and sweep ranges.
4. `metrics.md`: definitions for recovery, purity, dead-cell removal, SE, and SP.
