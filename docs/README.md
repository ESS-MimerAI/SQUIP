# SQUIP documentation

All paths in commands are relative to the repository root unless a document says otherwise.

## guide/: how to run things (current)

| Document | What it covers |
| --- | --- |
| [RUNNING.md](guide/RUNNING.md) | **Start here.** Command-by-command walkthrough for one system (glycine, AMBER99SB-ILDN, TIP4P-Ew, 300 K), from the starting PDB to S(q,ω) files. |
| [STEP3.md](guide/STEP3.md) | The S(q,ω) stage in depth: Dynasor setup, fixed-box trajectories, units, q conventions, linewidth analysis. |
| [PLAYGROUND.md](guide/PLAYGROUND.md) | The minimal single-system run used as a benchmark and pipeline-validation deliverable, with measured resource needs and success criteria. |

Script-level detail lives next to the code: [trajectory processing](../scripts/trajectory_processing/README.md), [trajectory validation](../scripts/trajectory_validation/README.md), [TaskBlaster workflow](../workflow/taskblaster/README.md).

## plan/: where the project is going

| Document | What it covers |
| --- | --- |
| [FULL_PROJECT_SCOPE_AND_PLAN.md](plan/FULL_PROJECT_SCOPE_AND_PLAN.md) | Vision, objectives, current baseline, and the two workstreams (A: MD and QENS pipeline, B: dataset and ML). |

## design/: decisions and the numbers behind them (reference)

| Document | What it covers |
| --- | --- |
| [BOX_ANALYSIS.md](design/BOX_ANALYSIS.md) | Box dimensions for 50 solute molecules per water model and concentration. |
| [NVE_EQUILIBRATION.md](design/NVE_EQUILIBRATION.md) | Whether to add an NVE stage. Recommendation: go straight NVT → NPT → production; an optional 10 ps NVE run on one system serves as an energy-conservation check (results in `results/nve_test/`). |
| [INCREASED_TIMESTEP.md](design/INCREASED_TIMESTEP.md) | Why trajectory output moved from 10 fs to 30 fs: about 3× less storage, while still resolving the 0.1–100 ps dynamics QENS probes. |
| [SMALLER_DISK_FOOTPRINT.md](design/SMALLER_DISK_FOOTPRINT.md) | Options for cutting a production run from 140 GB to about 50 GB (shorter runs, sparser output, or both). |
| [TIMINGS.md](design/TIMINGS.md) | Measured production-MD benchmarks: hardware, CPU vs GPU, projected run times. |
| [PROD_COST_ESTIMATE.md](design/PROD_COST_ESTIMATE.md) | Time and storage estimates for all production runs, built from the benchmarks. |
| [UNIQUENESS.md](design/UNIQUENESS.md) | Prior art: existing MD → S(q,ω) tools (MDANSE, Sassena, LiquidLib, …) and what is new in SQUIP. |

## history/: completed work (archived)

These are the step plans and status logs written while the pipeline was being built. They are kept for provenance. **Paths and commands inside them reflect the repository layout at the time** (`MD/`, `mdp/`, `structures/`, `scripts/dynasor_scripts/`, `tb_squip/`, `backup/`) and are not updated; use `guide/` for anything you intend to run.

| Document | What it covers |
| --- | --- |
| [STEP1.md](history/STEP1.md) | Step 1 plan: system preparation, substeps 1.1–1.7. |
| [STEP1_DONE.md](history/STEP1_DONE.md) | Step 1 progress report: what was finished, system specifications, scripts created. |
| [SYSTEM_VERIFICATION.md](history/SYSTEM_VERIFICATION.md) | Substep 1.3 report: system sizes and atom counts checked against targets. |
| [ISSUE_TO_SOLVE.md](history/ISSUE_TO_SOLVE.md) | Resolved `pdb2gmx` problem for single glycine, and the custom `ZGLY` residue in `amber99sb-ildn.ff/`. **Still the reference for that residue.** |
| [STEP1_4_STATUS.md](history/STEP1_4_STATUS.md) | Substep 1.4 (counter-ions) status after the topology problem was unblocked. |
| [STEPS_1.4-1.7_IMPLEMENTATION.md](history/STEPS_1.4-1.7_IMPLEMENTATION.md) | Plan for ions → energy minimisation → NVT → NPT across all 8 systems. |
| [CHARMM_GUI_INTEGRATION.md](history/CHARMM_GUI_INTEGRATION.md) | An alternative CHARMM-GUI input route for steps 1.4 onward. |
| [MOVING_TO_TIP4P.md](history/MOVING_TO_TIP4P.md) | Migration plan for AMBER systems from TIP3P to TIP4P-Ew (completed; the pre-migration data was removed from the tree and remains in git history). |
| [STEP2.md](history/STEP2.md) | Step 2 plan: production MD and trajectory post-processing for the 8 systems. |

## Other

- [branding/](branding/): logo and icon SVGs.
- [../.github/github-instructions.md](../.github/github-instructions.md): conventions and constraints for contributors and coding agents.
