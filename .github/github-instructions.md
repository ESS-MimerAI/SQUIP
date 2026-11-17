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

- `docs/README.md` is the documentation index. Every doc is labelled current, reference, or historical.
- `docs/guide/RUNNING.md` is the best end-to-end operational guide; `docs/guide/STEP3.md` covers the S(q,w) stage in depth.
- `docs/plan/FULL_PROJECT_SCOPE_AND_PLAN.md` is the living project plan.
- `docs/design/` holds decision records and measured numbers (box sizes, NVE, timestep, disk footprint, timings, cost, prior art).
- `docs/history/` holds completed step plans and status logs (`STEP1*.md`, `STEP2.md`, `STEPS_1.4-1.7_IMPLEMENTATION.md`, `SYSTEM_VERIFICATION.md`), the resolved `pdb2gmx` topology problem and custom `ZGLY` residue (`ISSUE_TO_SOLVE.md`), and the finished TIP3P→TIP4P-Ew migration (`MOVING_TO_TIP4P.md`). Paths inside these files reflect the layout at the time they were written.
- `inputs/mdp/` contains canonical GROMACS parameter files for minimization, equilibration, NVE tests, and production.
- `inputs/structures/` contains starting PDB structures, including force-field-specific zwitterion inputs.
- `amber99sb-ildn.ff/`, `residuetypes.dat`, and `posre.itp` stay at the repository root because GROMACS resolves them relative to the directory it is run from. `amber99sb-ildn.ff/` is a local modified force-field copy with the custom single-glycine `ZGLY` residue and TIP4P-Ew support. Treat it as source data, not disposable generated output.
- `topologies/` is the system-build working directory (pdb2gmx → insert-molecules → solvate → genion). The topologies and solvated boxes in `systems/` were copied from here.
- `systems/` is the structured output tree for prepared systems, equilibration, production, and analysis.
- `results/` holds small committed evidence: the NVE energy-conservation test and trajectory validation reports.
- `scripts/prep/` has system-preparation helpers. `generate_topologies.py` (hand-written CHARMM36m topologies) and `regenerate_topologies.py` are superseded by the `pdb2gmx` route in `docs/guide/RUNNING.md`.
- `scripts/trajectory_processing/` has bash/GROMACS scripts for PBC repair, centering, hydrogen/solute extraction, windowing, first-frame box extraction, and processing verification.
- `scripts/trajectory_validation/` has bash/Python scripts for production trajectory validation.
- `scripts/sqw/` contains the Dynasor analysis code, including the custom GROMACS trajectory wrapper and `build_element_groups.py`.
- `tests/` contains the pytest suite, including the planted-truth gate.
- `workflow/taskblaster/` contains a TaskBlaster automation workflow for a single-system pipeline and a Windows-compatible `run_tb.py` shim.

## Environment And Dependencies

- OS in active development may be Windows/PowerShell, but several trajectory scripts are bash-oriented and expected to run on a Linux workstation.
- External tools: GROMACS (`gmx`), Python 3, Dynasor, MDAnalysis, NumPy, SciPy, Matplotlib, h5py, RDKit, and TaskBlaster for `workflow/taskblaster` automation.
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
5. Energy minimize with `inputs/mdp/em.mdp`; expected pass criterion is `Fmax < 1000 kJ/mol/nm`.
6. Run NVT equilibration at the target temperature, then NPT at 1 bar.
7. Run production MD using the compact production MDP files, usually `inputs/mdp/prod_300K_compact.mdp` or `inputs/mdp/prod_350K_compact.mdp`.
8. Post-process production trajectories: make molecules whole, center/compact, and create `prod_nvt_fixed.xtc` because Dynasor assumes a constant simulation cell.
9. Compute `S(q,w)` with `scripts/sqw/compute_sqw.py`.
10. Validate outputs with `scripts/sqw/validate_sqw.py`, linewidth extraction, plots, and trajectory validation scripts.

## Important Scientific/Technical Constraints

- Dynasor assumes a fixed simulation cell. Prefer `prod_nvt_fixed.xtc` over raw NPT trajectories. Use `--allow-npt` only as an explicit approximation.
- Dynasor q values are the angular wavevector |q| = 2π/λ in Å⁻¹ (the Dynasor docs write this as rad/Angstrom). This is already the conventional neutron Q, so use it directly in the diffusion fit Γ = ħ D q². Do **not** divide by `2*pi`; doing so inflates D by (2π)² ≈ 39.5.
- MDAnalysis reads GROMACS coordinates in Angstrom. GROMACS command-line box dimensions are in nm. Be precise about unit conversions.
- `dt` passed to Dynasor should be the original inter-frame timestep in fs. Do not multiply by `frame_step`; the custom wrapper exposes `frame_step` separately.
- TIP4P-Ew virtual sites (`M`, `MW`, similar zero-mass sites) must be excluded from scattering groups. Use `scripts/sqw/build_element_groups.py` rather than ad hoc atom-name parsing.
- Hydrogen incoherent scattering dominates QENS. Hydrogen-only or solute-hydrogen selections may be useful for performance and targeted analysis.
- Production trajectories are huge. Avoid regenerating, copying, or committing large `.xtc`, `.trr`, `.tpr`, `.edr`, and `.npz` artifacts unless the task explicitly requires it.

## Key Python Entry Points

- `scripts/sqw/compute_sqw.py`: main CLI and library function for Dynasor calculation.
- `scripts/sqw/gromacs_trajectory.py`: MDAnalysis-backed duck-typed trajectory wrapper for Dynasor because `.tpr + .xtc` pairs need a separate topology file.
- `scripts/sqw/build_element_groups.py`: builds element groups and filters TIP4P virtual sites.
- `scripts/trajectory_processing/get_box_from_first_frame.py`: extracts first-frame box dimensions for fixed-box reimaging.
- `scripts/sqw/validate_sqw.py`: validates calculated `S(q,w)` arrays.
- `scripts/sqw/extract_linewidths.py`: fits `F_incoh(q,t)` and estimates diffusion from linewidths.
- `workflow/taskblaster/workflow.py` and `workflow/taskblaster/tasks.py`: TaskBlaster workflow and task implementations.

## Development Guidance

- Prefer changing scripts and MDP files over editing generated GROMACS binary outputs.
- Preserve the existing file/path conventions: `systems/{molecule}/{forcefield}/{temperature}/production/` and analysis files under `analysis/`.
- Keep Windows and Linux usage in mind. PowerShell examples are common in docs; bash scripts live under `scripts/trajectory_*`.
- When adding a new molecule, force field, temperature, or analysis mode, update both the operational docs and any hard-coded loops/choices in Python or shell scripts.
- If changing `compute_sqw.py`, check frame slicing, units, virtual-site filtering, q conventions, output filenames, and neutron weighting behavior.
- If changing topology preparation, read `docs/history/ISSUE_TO_SOLVE.md`, `docs/history/MOVING_TO_TIP4P.md`, and the local `amber99sb-ildn.ff/` modifications first.
- Do not assume `README.md` is complete. Cross-check `docs/guide/RUNNING.md`, the step documents, and current scripts.
- Generated caches such as `__pycache__/` and TaskBlaster runtime folders should not be treated as source.

## Useful Commands

```powershell
# Compute S(q,w) for one completed system
python scripts/sqw/compute_sqw.py glycine amber99sb 300K

# Compute with explicit fallback to NPT centered trajectory only when accepting the approximation
python scripts/sqw/compute_sqw.py glycine amber99sb 300K --allow-npt

# Validate S(q,w) arrays
python scripts/sqw/validate_sqw.py systems/glycine/amber99sb/300K/production/analysis/glycine_amber99sb_300K_sqw_arrays.npz

# Extract linewidths and diffusion estimate
python scripts/sqw/extract_linewidths.py systems/glycine/amber99sb/300K/production/analysis/glycine_amber99sb_300K_sqw_arrays.npz

# Run TaskBlaster workflow from workflow/taskblaster on Windows through the compatibility shim
cd workflow/taskblaster
python run_tb.py init
python run_tb.py workflow workflow.py
python run_tb.py run .
```

## Verification Expectations

- For Python changes, prefer small targeted smoke tests where full MD data is not required.
- For trajectory analysis changes, test with `--frame-stop` or `--frame-step` to keep runtime manageable before using full production trajectories.
- For production trajectory validation, use `scripts/trajectory_validation/quick_check.sh`, `validate_trajectory.sh`, or the Python helpers where the target platform supports them.
- For system prep changes, verify total charge, expected atom counts, water model inclusion, and that `gmx grompp` succeeds before running long simulations.

## Verification Protocols (BootLoops)

Analysis and ML work in this repository follows the BootLoops agent protocols (https://github.com/BootLoops-ai/skills, prose under CC BY 4.0, M. D. Schwartz / Anthropic 2026). They are installed as user-level Claude Code skills, not in the repo; the BootLoops numerical toolkit is for Feynman-integral physics and does not apply here, only the protocols do. Load `planted-truth` before running any fit, linewidth extraction or diffusion estimate on real data and whenever `scripts/sqw/` changes: the pipeline must first recover a known synthetic answer and a deliberately corrupted input must fail. The standing gate is `python -m pytest tests/test_planted_truth_diffusion.py tests/test_extract_linewidths.py`; it exists because a silent q/2π unit error once inflated every reported D by (2π)² ≈ 39.5. Load `acceptance-gate` before calling any number (D, Γ(q), a fitted model) done. Load `independence-bookkeeping` when setting up a reference value or second-route comparison. Load `timing-discipline` before launching a Dynasor run on a full production trajectory or a long MD/training job. Load `tool-stewardship` before writing a new script, to extend the existing ones instead.
