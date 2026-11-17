<picture>
  <source media="(prefers-color-scheme: dark)"
          srcset="docs/branding/squip-logo-dark.svg">
  <img src="docs/branding/squip-logo-light.svg"
       alt="SQUIP: S(q,ω) qualitative investigation of peptides"
       width="480">
</picture>


SQUIP is a proof-of-concept workflow for computing dynamic structure factors from peptide molecular dynamics simulations, with a planned extension toward fitting machine-learning-based potentials that can rapidly estimate `S(q,w)` from amino-acid profiles across related water models and temperatures.

The name stands for **S(q,w) QUalitative Investigation of Peptides**. The repository prepares small peptide systems, runs GROMACS molecular dynamics, post-processes production trajectories, and computes `S(q,w)` / `F(q,t)` for QENS-style analysis with Dynasor.

## Start Here

| If you want to… | Read |
| --- | --- |
| Run the whole pipeline for one system, command by command | [docs/guide/RUNNING.md](docs/guide/RUNNING.md) |
| Understand the S(q,ω) stage in depth | [docs/guide/STEP3.md](docs/guide/STEP3.md) |
| Run the minimal benchmark deliverable | [docs/guide/PLAYGROUND.md](docs/guide/PLAYGROUND.md) |
| See where the project is going | [docs/plan/FULL_PROJECT_SCOPE_AND_PLAN.md](docs/plan/FULL_PROJECT_SCOPE_AND_PLAN.md) |
| Find out why something is set up the way it is | [docs/design/](docs/design/) |
| Browse everything, including the historical step logs | [docs/README.md](docs/README.md) |

## What This Repository Contains

SQUIP currently focuses on two small peptide systems across two force-field families and two temperatures:

| Molecule | Force field | Water model | Temperatures |
| --- | --- | --- | --- |
| Glycine | AMBER99SB-ILDN | TIP4P-Ew | 300 K, 350 K |
| Glycine | CHARMM27 | TIP3P | 300 K, 350 K |
| Gly-Gly | AMBER99SB-ILDN | TIP4P-Ew | 300 K, 350 K |
| Gly-Gly | CHARMM27 | TIP3P | 300 K, 350 K |

The end-to-end flow, and where each stage lives:

| # | Stage | Code / inputs |
| --- | --- | --- |
| 1 | Generate peptide topologies from zwitterionic input structures | `inputs/structures/`, `amber99sb-ildn.ff/`, `scripts/prep/` |
| 2 | Build solvated boxes with 50 solute molecules | `topologies/` (working directory) |
| 3 | Run minimization, NVT equilibration, and NPT equilibration | `inputs/mdp/`, `systems/` |
| 4 | Run production MD with trajectory output suitable for QENS analysis | `inputs/mdp/prod_*_compact.mdp` |
| 5 | Repair periodic-boundary artifacts and create a fixed-cell trajectory | `scripts/trajectory_processing/` |
| 6 | Validate the production trajectories | `scripts/trajectory_validation/` |
| 7 | Compute and validate `S(q,w)` and `F(q,t)` with Dynasor | `scripts/sqw/` |
| 8 | Extract linewidths and estimate diffusion coefficients from `F_incoh(q,t)` | `scripts/sqw/extract_linewidths.py` |

`workflow/taskblaster/` chains stages 1–8 for a single system.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `docs/` | All documentation; [docs/README.md](docs/README.md) is the index. Split into `guide/` (how to run), `plan/`, `design/` (decisions and measurements), and `history/` (completed step logs). |
| `inputs/mdp/` | GROMACS MDP files for minimization, equilibration, NVE checks, and production runs. |
| `inputs/structures/` | Starting peptide structures for `pdb2gmx`. |
| `amber99sb-ildn.ff/` | Local AMBER99SB-ILDN force-field copy with project-specific modifications, including custom single-glycine (`ZGLY`) support. |
| `residuetypes.dat`, `posre.itp` | GROMACS data files. They stay at the root because GROMACS looks them up relative to the directory it runs in. |
| `topologies/` | Working directory for system building (pdb2gmx → insert-molecules → solvate → genion). The finished files are copied into `systems/`. |
| `systems/` | Structured simulation tree: `systems/{molecule}/{forcefield}/{temperature}/{initial,minimization,nvt,npt,production}/`. |
| `results/` | Small committed evidence: NVE energy-conservation test and trajectory validation reports. |
| `scripts/prep/` | System-preparation helpers (box sizing, SDF→PDB, dipeptide builder, system verification, legacy topology generators). |
| `scripts/trajectory_processing/` | Bash/GROMACS tools for making molecules whole, centering, extracting hydrogens/solute atoms, windowing, and reading the first-frame box. |
| `scripts/trajectory_validation/` | Bash/Python tools for checking production trajectory length, frame spacing, thermodynamic properties, warnings, and file integrity. |
| `scripts/sqw/` | Main `S(q,w)` calculation, plotting, validation, linewidth extraction, HDF5 export, and a custom GROMACS trajectory wrapper for Dynasor. |
| `tests/` | pytest suite for the S(q,ω) pipeline, including the planted-truth diffusion gate. |
| `workflow/taskblaster/` | TaskBlaster automation for a single-system test/prototype workflow. |
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

The TaskBlaster workflow under `workflow/taskblaster/` also requires `taskblaster`, which is not listed in `requirements.txt`.

All commands below are run from the repository root.

## Run The Tests

```bash
python -m pytest tests
```

`tests/test_planted_truth_diffusion.py` runs the whole S(q,ω) → Γ(q) → D chain on a synthetic trajectory with a known diffusion coefficient, and must pass before any fit on real data is trusted.

## Quick Start: Analyze A Completed Production Run

The shortest useful path is to run Dynasor on a production directory that already contains:

- `prod.tpr`
- `prod_nvt_fixed.xtc` preferred, or `prod_center.xtc` only when accepting the NPT approximation

Example for glycine / AMBER99SB-ILDN / 300 K:

```powershell
python scripts/sqw/compute_sqw.py glycine amber99sb 300K
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
python scripts/sqw/compute_sqw.py glycine amber99sb 300K --frame-step 10 --frame-stop 10000
```

To use the centered NPT trajectory directly, explicitly opt in:

```powershell
python scripts/sqw/compute_sqw.py glycine amber99sb 300K --allow-npt
```

Prefer fixed-box trajectories for real analysis because Dynasor assumes a constant simulation cell.

## Validate And Post-Process Results

Validate a computed `S(q,w)` arrays file:

```powershell
python scripts/sqw/validate_sqw.py systems/glycine/amber99sb/300K/production/analysis/glycine_amber99sb_300K_sqw_arrays.npz
```

Extract quasielastic linewidths and estimate a diffusion coefficient:

```powershell
python scripts/sqw/extract_linewidths.py systems/glycine/amber99sb/300K/production/analysis/glycine_amber99sb_300K_sqw_arrays.npz
```

Plot diagnostics:

```powershell
python scripts/sqw/plot_sqw.py systems/glycine/amber99sb/300K/production/analysis/glycine_amber99sb_300K_sqw_arrays.npz --out sqw_heatmap.png --type heatmap
python scripts/sqw/plot_sqw.py systems/glycine/amber99sb/300K/production/analysis/glycine_amber99sb_300K_sqw_arrays.npz --out fqt_decay.png --type fqt
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
python scripts/trajectory_processing/get_box_from_first_frame.py systems/glycine/amber99sb/300K/production/prod.tpr systems/glycine/amber99sb/300K/production/prod_center.xtc
```

Then reimage with `gmx trjconv -box Lx Ly Lz`, using those dimensions. Details: [scripts/trajectory_processing/README.md](scripts/trajectory_processing/README.md).

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

Details: [scripts/trajectory_validation/README.md](scripts/trajectory_validation/README.md).

## TaskBlaster Prototype Workflow

`workflow/taskblaster/` contains an automated single-system pipeline for glycine / AMBER99SB-ILDN / TIP4P-Ew / 300 K. It chains preparation, minimization, equilibration, production, centering, fixed-box conversion, and Dynasor analysis.

On Windows, use the compatibility runner:

```powershell
cd workflow/taskblaster
python run_tb.py init
python run_tb.py workflow workflow.py
python run_tb.py run .
```

The workflow defaults to `test_mode=True`, which keeps simulations short for end-to-end checks. Set `test_mode=False` in `workflow/taskblaster/workflow.py` for production-length runs. Details: [workflow/taskblaster/README.md](workflow/taskblaster/README.md).

## Scientific And Implementation Notes

- Dynasor q values are the angular wavevector |q| = 2π/λ in Å⁻¹ (the Dynasor docs write this as rad/Angstrom). This is already the conventional neutron Q, so use it directly in the diffusion fit Γ = ħ D q². Do **not** divide by `2*pi`; doing so inflates D by (2π)² ≈ 39.5.
- MDAnalysis reads GROMACS coordinates in Angstrom, while GROMACS command-line box dimensions are in nm.
- The `dt` passed to Dynasor should be the original inter-frame timestep in fs. Do not multiply it by `frame_step`; the custom trajectory wrapper handles `frame_step` separately.
- TIP4P-Ew virtual sites such as `M` and `MW` must be excluded from scattering groups. Use `scripts/sqw/build_element_groups.py` for this.
- Hydrogen incoherent scattering dominates QENS, so hydrogen-only trajectories and selections can be useful for performance and interpretation.
- Large MD outputs are expensive to regenerate and can be tens to hundreds of GB. `.xtc` and `.trr` files are gitignored; be deliberate before deleting, copying, or committing `.tpr`, `.edr`, `.cpt`, or large `.npz` files.

## License

See `LICENSE`.
