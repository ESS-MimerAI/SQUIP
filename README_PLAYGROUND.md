# SQUIP Playground: A Minimal Run for Pipeline Validation and Benchmarking

## Purpose

Before committing compute time and storage to the full SQUIP systems matrix, this document proposes a **single, minimal end-to-end run** of the pipeline: one peptide, one water model, one temperature. Its purpose is to let evaluate the project on a working, measurable example.

Concretely, the playground run answers three questions:

1. **Does the pipeline work end-to-end**, from a starting structure file to a scientific result, without manual intervention?
2. **What does one state point actually cost** in wall-clock time, storage, and operator effort?
3. **Is the scientific output sane**: does it reproduce known water/peptide dynamics well enough to justify scaling up?

This is deliberately the smallest slice of the project that still involves every stage of the workflow. It is not a scientific deliverable on its own.

## Scope

| Parameter | Choice | Rationale |
| --- | --- | --- |
| Peptide | Glycine (zwitterionic) | Simplest amino acid; smallest, fastest-equilibrating system in the target set |
| Force field | AMBER99SB-ILDN | One of the two force-field families in the full project scope |
| Water model | TIP4P-Ew | Higher-cost of the two water models (4-site), so the benchmark is a conservative (upper-bound) estimate for the AMBER family |
| Temperature | 300 K | Room temperature; the reference condition against which 350 K and other future conditions will be compared |
| System size | ~50 solute molecules in a ~5.4 nm cubic box (~20,700 atoms, ~0.5 M) | Matches the concentration and box-size targets already validated for this system |
| Production length | 20 ns, frames saved every 30 fs | The length judged necessary to resolve the quasi-elastic linewidths of interest |

This single combination: **glycine / AMBER99SB-ILDN / TIP4P-Ew / 300 K** is already the system used as the project's reference walkthrough.

The full project scope (multiple peptides, force-field/water families, several temperatures) is described in the main [README.md](README.md); this document only covers the first of those 8 points, run in isolation.

## Workflow

The playground exercises the same seven stages as the full pipeline, applied to one system:

### Stage 1: Topology generation
The zwitterionic glycine structure is converted into a GROMACS-compatible topology and coordinate file using a locally maintained AMBER99SB-ILDN force-field copy with a custom residue definition for a standalone glycine amino acid (rather than a mid-chain residue). Output is verified to carry zero net charge.

### Stage 2: Solvated box construction
Fifty copies of the glycine topology are packed into a cubic simulation box and solvated with TIP4P-Ew water to reach approximately 0.5 M concentration and roughly 20,000–22,000 total atoms, matching a size previously verified as adequate for scattering statistics while remaining computationally tractable.

### Stage 3: Neutralization
The system is checked for net charge and neutralized with counter-ions if required. For zwitterionic glycine the system is already neutral; this stage is a verification step rather than a correction.

### Stage 4: Energy minimization
A steepest-descent minimization removes steric clashes introduced during packing and solvation, producing a numerically stable starting configuration for dynamics.

### Stage 5: Equilibration
Two short equilibration stages bring the system to the target thermodynamic state:
- **NVT (100 ps):** the system is brought to 300 K at fixed volume.
- **NPT (100 ps):** pressure coupling is enabled to relax the box to the correct density at 1 bar.

### Stage 6: Production molecular dynamics
A 50 ns production run in the NPT ensemble generates the trajectory used for analysis, with coordinates saved every 20 fs. The frame density required to resolve the quasi-elastic energy window of interest. This is the computationally dominant stage of the pipeline.

### Stage 7: Trajectory conditioning
Raw output requires two corrections before analysis: molecules split across periodic boundaries are stitched back together and re-centered in the box, and the fluctuating NPT box is re-imaged onto a single fixed cell, since the downstream scattering calculation assumes a constant simulation volume.

### Stage 8: Dynamic structure factor calculation
The conditioned trajectory is passed through a Dynasor-based analysis that computes the coherent and incoherent dynamic structure factor `S(q,ω)` and intermediate scattering function `F(q,t)`, spherically averaged over momentum-transfer bins spanning the QENS-relevant q-range, with hydrogen atoms and force-field virtual sites (TIP4P-Ew's M-site) correctly handled.

### Stage 9: Validation and scientific outputs
The computed spectra are checked for physical correctness (non-negativity, correct short-time limits, expected q-range coverage), then used to extract quasi-elastic linewidths `Γ(q)` and a self-diffusion coefficient `D` by fitting the incoherent intermediate scattering function. Heatmap and decay-curve plots are produced as the human-readable summary of the run.

A fully worked, command-level version of this same walkthrough already exists at [MD/RUNNING.md](MD/RUNNING.md); this playground document expresses it as a standalone deliverable.

## Resource Requirements (Measured)

The core cost is Stage 6 (production MD). Benchmarks already collected on this exact system give some idea about the expected cost:

| Resource | Measured value |
| --- | --- |
| Hardware | 12-core workstation CPU (Intel Xeon W-2265), no GPU |
| Production wall time (20 ns) | ~12h |
| Simulation throughput | ~101 ns/day |
| Trajectory storage | ~200 GB (raw), before conditioning-stage copies |


## Success Criteria

The playground run is considered successful, and a basis for approving the full 8-state-point matrix, if:

1. All nine stages complete without manual patching of the pipeline.
2. The validation step passes its physical sanity checks (non-negative spectra, correct `F_incoh(q,t→0) ≈ 1` limit).
3. The extracted self-diffusion coefficient and linewidths fall in a physically reasonable range for an aqueous amino acid solution at 300 K.
4. Measured time/storage costs are consistent with the estimates above, confirming they can be safely multiplied out to plan the remaining state points.

## What This De-Risks for the Full Project

A successful playground run validates the "data generator" half of the project (see [MD/FULL_PROJECT_SCOPE_AND_PLAN.md](MD/FULL_PROJECT_SCOPE_AND_PLAN.md)) at minimum cost, before the committee is asked to approve:
- the remaining production runs (~10 TB total storage, ~330 hours total compute, sequential),
- and the downstream machine-learning surrogate workstream, which depends entirely on having a trustworthy, reproducible per-state-point pipeline like the one this playground exercises.

In short: this is the smallest experiment that proves the pipeline before scaling the pipeline.
