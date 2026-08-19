<picture>
  <source media="(prefers-color-scheme: dark)"
          srcset="docs/branding/squip-logo-dark.svg">
  <img src="docs/branding/squip-logo-light.svg"
       alt="SQUIP: S(q,ω) qualitative investigation of peptides"
       width="480">
</picture>


SQUIP is a proof-of-concept workflow for computing dynamic structure factors from peptide molecular dynamics simulations, with a planned extension toward fitting machine-learning-based potentials that can rapidly estimate `S(q,w)` from amino-acid profiles across related water models and temperatures.

The name stands for **S(q,w) QUalitative Investigation of Peptides**. The repository prepares small peptide systems, runs GROMACS molecular dynamics, post-processes production trajectories, and computes `S(q,w)` / `F(q,t)` for QENS-style analysis with Dynasor.

## What This Repository Contains

SQUIP currently focuses on two small peptide systems across two force-field families and two temperatures:

| Molecule | Force field | Water model | Temperatures |
| --- | --- | --- | --- |
| Glycine | AMBER99SB-ILDN | TIP4P-Ew | 300 K, 350 K |
| Glycine | CHARMM27 | TIP3P | 300 K, 350 K |
| Gly-Gly | AMBER99SB-ILDN | TIP4P-Ew | 300 K, 350 K |
| Gly-Gly | CHARMM27 | TIP3P | 300 K, 350 K |

The intended end-to-end flow is:

1. Generate peptide topologies from zwitterionic input structures.
2. Build solvated boxes with 50 solute molecules.
3. Run minimization, NVT equilibration, and NPT equilibration.
4. Run production MD with trajectory output suitable for QENS analysis.
5. Repair periodic-boundary artifacts and create a fixed-cell trajectory.
6. Compute and validate `S(q,w)` and `F(q,t)` with Dynasor.
7. Extract linewidths and estimate diffusion coefficients from `F_incoh(q,t)`.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `MD/` | Project notes, runbook, step plans, timing/cost notes, and topology background. Start with `MD/RUNNING.md` for the detailed single-system walkthrough. |
| `mdp/` | GROMACS MDP files for minimization, equilibration, NVE checks, and production runs. |
| `amber99sb-ildn.ff/` | Local AMBER99SB-ILDN force-field copy with project-specific modifications, including custom single-glycine support. |
| `structures/` | Starting peptide structures for `pdb2gmx`. |
| `topologies/` | Generated topology and coordinate files. |
| `systems/` | Structured simulation tree for prepared systems, equilibration, production, and analysis outputs. |
| `scripts/` | Python and shell utilities for topology generation, validation, trajectory processing, and Dynasor analysis. |
| `scripts/dynasor_scripts/` | Main `S(q,w)` calculation, plotting, validation, linewidth extraction, and a custom GROMACS trajectory wrapper for Dynasor. |
| `scripts/trajectory_processing/` | Bash/GROMACS tools for making molecules whole, centering trajectories, extracting hydrogens/solute atoms, and windowing trajectories. |
| `scripts/trajectory_validation/` | Bash/Python tools for checking production trajectory length, frame spacing, thermodynamic properties, warnings, and file integrity. |
| `tb_squip/` | TaskBlaster automation for a single-system test/prototype workflow. |
| `.github/github-instructions.md` | Development notes for future feature work and bug fixes. |

## Requirements

External tools:

- GROMACS, available as `gmx` on `PATH`.
- Python 3.
- A working shell environment. PowerShell examples are used on Windows; several trajectory processing scripts are bash-oriented and are best run on Linux or WSL.

Python packages are listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

The analysis scripts use:

- Dynasor
- MDAnalysis
- NumPy
- SciPy
- Matplotlib
- h5py
- RDKit

The TaskBlaster workflow under `tb_squip/` also requires `taskblaster`, which is not listed in `requirements.txt`.

## Quick Start: Analyze A Completed Production Run

The shortest useful path is to run Dynasor on a production directory that already contains:

- `prod.tpr`
- `prod_nvt_fixed.xtc` preferred, or `prod_center.xtc` only when accepting the NPT approximation

Example for glycine / AMBER99SB-ILDN / 300 K:

```powershell
python scripts/dynasor_scripts/compute_sqw.py glycine amber99sb 300K
```

This writes analysis files under:

```text
systems/glycine/amber99sb/300K/production/analysis/
```

Expected outputs include:

- `glycine_amber99sb_300K_sqw_raw.npz`
- `glycine_amber99sb_300K_sqw_averaged.npz`
- `glycine_amber99sb_300K_sqw_neutron.npz`, when neutron weighting is supported for the atom types
- `glycine_amber99sb_300K_sqw_arrays.npz`

For a quick smoke test on a large trajectory, limit the frames:

```powershell
python scripts/dynasor_scripts/compute_sqw.py glycine amber99sb 300K --frame-step 10 --frame-stop 10000
```

To use the centered NPT trajectory directly, explicitly opt in:

```powershell
python scripts/dynasor_scripts/compute_sqw.py glycine amber99sb 300K --allow-npt
```

Prefer fixed-box trajectories for real analysis because Dynasor assumes a constant simulation cell.

## Validate And Post-Process Results

Validate a computed `S(q,w)` arrays file:

```powershell
python scripts/dynasor_scripts/validate_sqw.py systems/glycine/amber99sb/300K/production/analysis/glycine_amber99sb_300K_sqw_arrays.npz
```

Extract quasielastic linewidths and estimate a diffusion coefficient:

```powershell
python scripts/dynasor_scripts/extract_linewidths.py systems/glycine/amber99sb/300K/production/analysis/glycine_amber99sb_300K_sqw_arrays.npz
```

Plot diagnostics:

```powershell
python scripts/dynasor_scripts/plot_sqw.py systems/glycine/amber99sb/300K/production/analysis/glycine_amber99sb_300K_sqw_arrays.npz --out sqw_heatmap.png --type heatmap
python scripts/dynasor_scripts/plot_sqw.py systems/glycine/amber99sb/300K/production/analysis/glycine_amber99sb_300K_sqw_arrays.npz --out fqt_decay.png --type fqt
```

## Production Trajectory Preparation

Raw production trajectories need periodic-boundary repair before analysis. The processing pipeline creates:

```text
production/
├── prod.xtc
├── prod_whole.xtc
├── prod_center.xtc
├── prod_hydrogen.xtc
├── prod_solute.xtc
└── index.ndx
```

Run the full processing pipeline for one system on a bash-capable workstation:

```bash
scripts/trajectory_processing/process_trajectory.sh systems/glycine/amber99sb/300K/production/
```

For all systems:

```bash
scripts/trajectory_processing/process_all.sh systems/
```

After centering, create or use `prod_nvt_fixed.xtc` for Dynasor. The helper script prints the first-frame box dimensions in nm:

```powershell
python scripts/get_box_from_first_frame.py systems/glycine/amber99sb/300K/production/prod.tpr systems/glycine/amber99sb/300K/production/prod_center.xtc
```

Then reimage with `gmx trjconv -box Lx Ly Lz`, using those dimensions.

## Trajectory Validation

The validation tools check trajectory completeness, 30 fs frame spacing, temperature, pressure, density, warnings, and required files.

Quick check for one production run:

```bash
scripts/trajectory_validation/quick_check.sh systems/glycine/amber99sb/300K/production/
```

Full validation for one production run:

```bash
scripts/trajectory_validation/validate_trajectory.sh systems/glycine/amber99sb/300K/production/ glycine_amber_300K
```

Generate a consolidated report:

```bash
python scripts/trajectory_validation/generate_report.py --base-dir systems/ --output validation_report.txt
```

Successful 20 ns compact production runs should have roughly:

- Trajectory length near 20,000 ps.
- Frame count near 666,667 frames for 30 fs spacing.
- Temperature within about 5 K of target.
- Pressure fluctuating around 1 bar, with large instantaneous swings expected.
- Density near 1000 kg/m^3 for aqueous systems.

## TaskBlaster Prototype Workflow

`tb_squip/` contains an automated single-system pipeline for glycine / AMBER99SB-ILDN / TIP4P-Ew / 300 K. It chains preparation, minimization, equilibration, production, centering, fixed-box conversion, and Dynasor analysis.

On Windows, use the compatibility runner:

```powershell
cd tb_squip
python run_tb.py init
python run_tb.py workflow workflow.py
python run_tb.py run .
```

The workflow defaults to `test_mode=True`, which keeps simulations short for end-to-end checks. Set `test_mode=False` in `tb_squip/workflow.py` for production-length runs.

## Scientific And Implementation Notes

- Dynasor q values are in rad/Angstrom. Convert to 1/Angstrom by dividing by `2*pi` before diffusion fits.
- MDAnalysis reads GROMACS coordinates in Angstrom, while GROMACS command-line box dimensions are in nm.
- The `dt` passed to Dynasor should be the original inter-frame timestep in fs. Do not multiply it by `frame_step`; the custom trajectory wrapper handles `frame_step` separately.
- TIP4P-Ew virtual sites such as `M` and `MW` must be excluded from scattering groups. Use `scripts/build_element_groups.py` for this.
- Hydrogen incoherent scattering dominates QENS, so hydrogen-only trajectories and selections can be useful for performance and interpretation.
- Large MD outputs are expensive to regenerate and can be tens to hundreds of GB. Be deliberate before deleting, copying, or committing `.xtc`, `.trr`, `.tpr`, `.edr`, or large `.npz` files.

## Deeper Documentation

The most useful project documents are under `MD/`:

- `MD/RUNNING.md`: detailed end-to-end walkthrough for a representative single system.
- `MD/ISSUE_TO_SOLVE.md`: background on `pdb2gmx`, force-field availability, and custom glycine handling.
- `MD/MOVING_TO_TIP4P.md`: AMBER TIP4P-Ew migration notes.
- `MD/STEP1.md`, `MD/STEP2.md`, `MD/STEP3.md`: staged implementation plans.
- `MD/SYSTEM_VERIFICATION.md`: system-size verification and expected atom counts.
- `scripts/trajectory_processing/README.md`: trajectory processing details.
- `scripts/trajectory_validation/README.md`: production validation details.
- `.github/github-instructions.md`: contributor and agent guidance for future development.

## License

See `LICENSE`.
