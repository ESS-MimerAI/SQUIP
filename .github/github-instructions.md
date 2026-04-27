# SQUIP Project Instructions

SQUIP means `S(q,w) QUalitative Investigation of Peptides`. The project is a proof-of-concept molecular dynamics and QENS analysis workflow for small peptide systems. It prepares solvated glycine and Gly-Gly systems, runs GROMACS equilibration and production MD, post-processes trajectories, and computes dynamic structure factors with Dynasor.

## Project Scope

- Main scientific target: compute and validate `S(q,w)` / `F(q,t)` from MD trajectories for QENS-style analysis.
- Core systems: `glycine` and `glygly`.
- Core force-field/water combinations:
  - `amber99sb` / AMBER99SB-ILDN with TIP4P-Ew water.
  - `charmm27` / CHARMM27 with TIP3P water.
- Standard temperatures: `300K` and `350K`.
- Standard system size: 50 solute molecules in about a 5.4-5.5 nm cubic box, roughly 0.5-1 M depending on the document/version being followed.
- Production target: 20 ns at 2 fs timestep with compressed coordinates every 30 fs for compact QENS trajectories.

## Repository Layout

- `README.md` is minimal; use `RUNNING.md` as the best end-to-end operational guide.
- `ISSUE_TO_SOLVE.md` documents the resolved `pdb2gmx` topology problem and the AMBER custom `ZGLY` residue.
- `STEP1.md`, `STEP2.md`, `STEP3.md`, `STEP1_DONE.md`, `STEP1_4_STATUS.md`, `STEPS_1.4-1.7_IMPLEMENTATION.md`, and `SYSTEM_VERIFICATION.md` record the project plan and current workflow assumptions.
- `mdp/` contains canonical GROMACS parameter files for minimization, equilibration, NVE tests, and production.
- `amber99sb-ildn.ff/` is a local modified force-field copy. It includes the custom single-glycine `ZGLY` residue and TIP4P-Ew support. Treat it as source data, not disposable generated output.
- `structures/` contains starting PDB structures, including force-field-specific zwitterion inputs.
- `topologies/` contains generated topology/coordinate files.
- `systems/` is the structured output tree for prepared systems, equilibration, production, and analysis.
- `scripts/trajectory_processing/` has bash/GROMACS scripts for PBC repair, centering, hydrogen/solute extraction, windowing, and processing verification.
- `scripts/trajectory_validation/` has bash/Python scripts for production trajectory validation.
- `scripts/dynasor_scripts/` contains the Dynasor analysis code, including the custom GROMACS trajectory wrapper.
- `tb_squip/` contains a TaskBlaster automation workflow for a single-system pipeline and a Windows-compatible `run_tb.py` shim.

## Environment And Dependencies

- OS in active development may be Windows/PowerShell, but several trajectory scripts are bash-oriented and expected to run on a Linux workstation.
- External tools: GROMACS (`gmx`), Python 3, Dynasor, MDAnalysis, NumPy, SciPy, Matplotlib, h5py, RDKit, and TaskBlaster for `tb_squip` automation.
- Python dependencies are listed in `requirements.txt`: `dynasor`, `h5py`, `matplotlib`, `MDAnalysis`, `numpy`, `rdkit`, `scipy`.
- The current local workflow commonly uses a Conda environment named `squip`.
- GROMACS 2021.5 appears in generated binary metadata and code comments. Be cautious when changing commands for newer GROMACS versions.

## Canonical Workflow

1. Prepare topology and starting structures with `gmx pdb2gmx`.
   - AMBER single glycine uses custom `ZGLY` in the local `amber99sb-ildn.ff/`.
   - CHARMM27 supports zwitterionic termini through terminal selections.
   - AMBER + TIP4P-Ew may require `-water select` and selecting `tip4pew` from `watermodels.dat` in older GROMACS.
2. Insert 50 solute molecules into a roughly 5.4-5.5 nm cubic box with `gmx insert-molecules`.
3. Solvate with TIP4P-Ew for AMBER systems or TIP3P for CHARMM systems.
4. Neutralize/check charge with `grompp` + `genion`; zwitterionic systems should normally be neutral already.
5. Energy minimize with `mdp/em.mdp`; expected pass criterion is `Fmax < 1000 kJ/mol/nm`.
6. Run NVT equilibration at the target temperature, then NPT at 1 bar.
7. Run production MD using the compact production MDP files, usually `mdp/prod_300K_compact.mdp` or `mdp/prod_350K_compact.mdp`.
8. Post-process production trajectories: make molecules whole, center/compact, and create `prod_nvt_fixed.xtc` because Dynasor assumes a constant simulation cell.
9. Compute `S(q,w)` with `scripts/dynasor_scripts/compute_sqw.py`.
10. Validate outputs with `scripts/dynasor_scripts/validate_sqw.py`, linewidth extraction, plots, and trajectory validation scripts.

## Important Scientific/Technical Constraints

- Dynasor assumes a fixed simulation cell. Prefer `prod_nvt_fixed.xtc` over raw NPT trajectories. Use `--allow-npt` only as an explicit approximation.
- Dynasor q values are in rad/Angstrom. Convert to 1/Angstrom by dividing by `2*pi` before diffusion fits.
- MDAnalysis reads GROMACS coordinates in Angstrom. GROMACS command-line box dimensions are in nm. Be precise about unit conversions.
- `dt` passed to Dynasor should be the original inter-frame timestep in fs. Do not multiply by `frame_step`; the custom wrapper exposes `frame_step` separately.
- TIP4P-Ew virtual sites (`M`, `MW`, similar zero-mass sites) must be excluded from scattering groups. Use `scripts/build_element_groups.py` rather than ad hoc atom-name parsing.
- Hydrogen incoherent scattering dominates QENS. Hydrogen-only or solute-hydrogen selections may be useful for performance and targeted analysis.
- Production trajectories are huge. Avoid regenerating, copying, or committing large `.xtc`, `.trr`, `.tpr`, `.edr`, and `.npz` artifacts unless the task explicitly requires it.

## Key Python Entry Points

- `scripts/dynasor_scripts/compute_sqw.py`: main CLI and library function for Dynasor calculation.
- `scripts/dynasor_scripts/gromacs_trajectory.py`: MDAnalysis-backed duck-typed trajectory wrapper for Dynasor because `.tpr + .xtc` pairs need a separate topology file.
- `scripts/build_element_groups.py`: builds element groups and filters TIP4P virtual sites.
- `scripts/get_box_from_first_frame.py`: extracts first-frame box dimensions for fixed-box reimaging.
- `scripts/dynasor_scripts/validate_sqw.py`: validates calculated `S(q,w)` arrays.
- `scripts/dynasor_scripts/extract_linewidths.py`: fits `F_incoh(q,t)` and estimates diffusion from linewidths.
- `tb_squip/workflow.py` and `tb_squip/tasks.py`: TaskBlaster workflow and task implementations.

## Development Guidance

- Prefer changing scripts and MDP files over editing generated GROMACS binary outputs.
- Preserve the existing file/path conventions: `systems/{molecule}/{forcefield}/{temperature}/production/` and analysis files under `analysis/`.
- Keep Windows and Linux usage in mind. PowerShell examples are common in docs; bash scripts live under `scripts/trajectory_*`.
- When adding a new molecule, force field, temperature, or analysis mode, update both the operational docs and any hard-coded loops/choices in Python or shell scripts.
- If changing `compute_sqw.py`, check frame slicing, units, virtual-site filtering, q conventions, output filenames, and neutron weighting behavior.
- If changing topology preparation, read `ISSUE_TO_SOLVE.md`, `MOVING_TO_TIP4P.md`, and the local `amber99sb-ildn.ff/` modifications first.
- Do not assume `README.md` is complete. Cross-check `RUNNING.md`, the step documents, and current scripts.
- Generated caches such as `__pycache__/` and TaskBlaster runtime folders should not be treated as source.

## Useful Commands

```powershell
# Compute S(q,w) for one completed system
python scripts/dynasor_scripts/compute_sqw.py glycine amber99sb 300K

# Compute with explicit fallback to NPT centered trajectory only when accepting the approximation
python scripts/dynasor_scripts/compute_sqw.py glycine amber99sb 300K --allow-npt

# Validate S(q,w) arrays
python scripts/dynasor_scripts/validate_sqw.py systems/glycine/amber99sb/300K/production/analysis/glycine_amber99sb_300K_sqw_arrays.npz

# Extract linewidths and diffusion estimate
python scripts/dynasor_scripts/extract_linewidths.py systems/glycine/amber99sb/300K/production/analysis/glycine_amber99sb_300K_sqw_arrays.npz

# Run TaskBlaster workflow from tb_squip on Windows through the compatibility shim
cd tb_squip
python run_tb.py init
python run_tb.py workflow workflow.py
python run_tb.py run .
```

## Verification Expectations

- For Python changes, prefer small targeted smoke tests where full MD data is not required.
- For trajectory analysis changes, test with `--frame-stop` or `--frame-step` to keep runtime manageable before using full production trajectories.
- For production trajectory validation, use `scripts/trajectory_validation/quick_check.sh`, `validate_trajectory.sh`, or the Python helpers where the target platform supports them.
- For system prep changes, verify total charge, expected atom counts, water model inclusion, and that `gmx grompp` succeeds before running long simulations.
