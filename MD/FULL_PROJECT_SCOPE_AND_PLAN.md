# SQUIP — Project Scope and Plan

**S(q,ω) QUalitative Investigation of Peptides**

| | |
|---|---|
| Status | Draft v0.1 |
| Date | 2026-06-02 |
| Owner | rozyczko |

---

## 1. Vision

SQUIP is a proof-of-concept (PoC) workflow that computes dynamic structure factors `S(q,ω)` and intermediate scattering functions `F(q,t)` from peptide molecular-dynamics (MD) simulations, for direct comparison with quasi-elastic neutron scattering (QENS) experiments.

The actual goal of this project is to use the MD/QENS dataset as training data for a **machine-learning surrogate** that predicts `S(q,ω)` (and its derived observables: linewidths `Γ(q)`, self-diffusion coefficient `D`) directly from an amino-acid / peptide descriptor, a water-model choice, and a temperature — in milliseconds instead of the ~5 hours of compute + post-processing each MD state point currently costs.

In short: **the MD pipeline is the data generator; the ML model is the product.**

---

## 2. Objectives

| # | Objective | Type | Status |
|---|-----------|------|--------|
| O1 | Reproducible MD pipeline (prep → equilibration → production) for small peptides | MD | Done |
| O2 | Validated `S(q,ω)` / `F(q,t)` computation via Dynasor | QENS | Done (PoC) |
| O3 | `Γ(q)` and diffusion-coefficient extraction from `F_incoh(q,t)` | QENS | Done (PoC) |
| O4 | A structured, versioned **dataset** linking peptide/condition descriptors to QENS observables | ML data | **Not started** |
| O5 | A **surrogate model** `(descriptor, water model, T) → S(q,ω) / Γ(q) / D` with quantified uncertainty | ML | **Not started** |
| O6 | A data-expansion strategy that makes the surrogate trainable beyond the current 8 state points | ML | **Not started** |
| O7 | Validation of the surrogate against held-out MD and, ideally, experimental QENS | ML | **Not started** |

Objectives **O4–O7 are the focus of this document.** The MD/QENS workstream is summarized for completeness but is already covered in detail by the `MD/STEP*.md` documents.

---

## 3. Scope

### In scope
- Small peptides: glycine and Gly-Gly today; **the descriptor space must be designed to extend to longer/other peptides**, since sequence variation is the primary axis the ML model must generalize over.
- Two force-field / water-model families: AMBER99SB-ILDN / TIP4P-Ew and CHARMM27 / TIP3P.
- Temperatures 300 K and 350 K today; temperature is a **continuous input** to the surrogate, so intermediate/extrapolated temperatures are an explicit ML target.
- QENS-relevant observables: `S(q,ω)`, `F(q,t)`, `Γ(q)`, `D`, EISF.
- The full data path from trajectory to a model-ready feature/label store.

### Out of scope (for now)
- Large proteins, membrane systems, non-aqueous solvents.
- Replacing the MD force field itself with an ML interatomic potential (MLIP). *Note: the README phrase "ML-based potentials" is interpreted here as an **`S(q,ω)` surrogate / emulator**, not an MLIP that replaces GROMACS. If an MLIP is genuinely intended, that is a substantially larger program and should be scoped separately — see [Open Questions](#10-open-questions).*
- Experimental data acquisition (we consume published/collaborator QENS where available).
- Production-grade serving infrastructure; a reproducible inference script is sufficient for the PoC.

---

## 4. Current State (Baseline)

What exists and works today:

- **Systems matrix**: 2 molecules × 2 FF/water × 2 temperatures = **8 state points**.
- **MD pipeline**: `pdb2gmx` → `insert-molecules` (50 solutes, ~5.4 nm box, ~1 M) → solvate → EM → NVT → NPT → 20 ns NPT production at 2 fs, frames every 30 fs. Custom `ZGLY` residue for single-glycine in AMBER. ([MD/RUNNING.md](MD/RUNNING.md))
- **Cost per state point**: ~3.5–4.8 h wall (CPU-only, Xeon W-2265), ~110–140 GB trajectory. (~33 h + ~1 TB for all 8.) ([MD/PROD_COST_ESTIMATE.md](MD/PROD_COST_ESTIMATE.md))
- **Analysis**: `scripts/dynasor_scripts/compute_sqw.py` (Dynasor + MDAnalysis wrapper), `validate_sqw.py`, `extract_linewidths.py`, `plot_sqw.py`. Outputs `*_sqw_arrays.npz` per system.
- **Automation**: `tb_squip/` TaskBlaster workflow chains the full single-system pipeline.

**Implication for ML:** the entire labeled dataset today is **8 rows**. This is the single most important fact shaping the ML plan below.

---

## 5. Workstream A — MD & QENS Pipeline (summary)

This workstream is essentially complete as a PoC and is documented elsewhere; it is included here only as it feeds Workstream B.

| Phase | Description | Reference | Status |
|-------|-------------|-----------|--------|
| A1 | System preparation & equilibration | [MD/STEP1.md](MD/STEP1.md) | Done (AMBER), CHARMM verification pending |
| A2 | Production MD (20 ns, 30 fs) | [MD/STEP2.md](MD/STEP2.md) | Done for benchmarked systems |
| A3 | Trajectory PBC repair + fixed-box conversion | [scripts/trajectory_processing/](scripts/trajectory_processing/) | Done |
| A4 | `S(q,ω)` / `F(q,t)` computation + validation | [MD/STEP3.md](MD/STEP3.md) | Done (PoC) |
| A5 | `Γ(q)`, `D`, EISF extraction | `extract_linewidths.py` | Done (PoC) |

**Carryover work feeding the ML workstream:**
- A6 — Confirm all 8 state points are computed *and validated* end-to-end (some CHARMM runs still pending verification).
- A7 — **Standardize analysis outputs** so every state point yields an identical, machine-readable record (same q-grid, same ω-grid, same derived scalars). This is a prerequisite for O4 and is currently *not* guaranteed across runs.

---

## 6. Workstream B — Machine Learning Surrogate (PRIMARY FOCUS)

### B.0 ML problem statement

Learn a function

```
f : (peptide descriptor x_p, water model w, temperature T, momentum transfer q) → QENS observable
```

with the **primary product** being a fast emulator of either:

- **(B-direct)** the full spectrum `S(q,ω)` / `F(q,t)` on a fixed grid, or
- **(B-physics)** a small set of physically-meaningful parameters — self-diffusion `D`, quasi-elastic linewidths `Γ(q)`, EISF — from which `S(q,ω)` is *reconstructed analytically* using the standard QENS model (delta + Lorentzian(s) ⊗ resolution).

**Recommendation:** pursue **B-physics first.** It collapses a high-dimensional 2-D spectral target into a handful of well-understood scalars/curves, which is the only tractable target given the dataset size, and it bakes in physics that a raw-spectrum regressor would have to rediscover from 8 examples.

### B.1 The central risk: data scarcity

The current dataset is **8 labeled points**, and each new point costs hours of compute and ~100+ GB. No amount of model sophistication overcomes this. **Everything in this workstream is organized around making the model trainable despite tiny data**, in this priority order:

1. **Reduce target dimensionality** (B-physics): predict `D` and `Γ(q)` parameters, not raw grids.
2. **Choose data-efficient models** with built-in uncertainty (Gaussian Processes first; trees/NNs only as data grows).
3. **Expand the dataset deliberately** via a data-generation campaign and active learning (B.6).
4. **Exploit multi-fidelity**: short/cheap trajectories as low-fidelity signal, full 20 ns as high-fidelity.

### B.2 Phase B1 — Dataset & feature store (foundation)

Goal: turn scattered `*.npz` analysis outputs into a single, versioned, model-ready dataset. This realizes "Step 5: Database schema and HDF5 integration" hinted at the end of [MD/STEP3.md](MD/STEP3.md).

- **Schema (one row per state point):**
  - Identifiers: molecule, force field, water model, temperature, run hash, trajectory provenance (length, dt, box, frame count).
  - **Features** (`x_p`, `w`, `T`) — see B.3.
  - **Labels**: `Γ(q)` curve on a canonical q-grid, `D`, EISF, and a downsampled `S(q,ω)` / `F(q,t)` array on a canonical (q, ω) grid.
  - **Quality flags**: validation pass/fail, fit `R²`, statistical error bars.
- **Storage**: HDF5 (`h5py`, already a dependency) or Parquet for the tabular features; keep large spectra in HDF5 with the scalars duplicated into a small tabular index for quick model iteration.
- **Canonicalization**: a single resampling step guarantees all rows share identical q- and ω-grids (addresses A7). Units fixed at this boundary: q in 1/Å (convert from Dynasor's rad/Å by dividing by 2π), ω in meV, D in m²/s.
- **Deliverables**: `scripts/ml/build_dataset.py`, `data/squip_dataset.h5`, a dataset card documenting columns, units, and provenance.

### B.3 Phase B2 — Featurization (descriptor design)

The model must generalize across *peptides*, so the descriptor is the make-or-break design choice. Start simple and physically interpretable; escalate only if data supports it.

- **Tier 1 — composition / scalar descriptors** (works with tiny data):
  - Amino-acid composition vector (counts/fractions per residue type).
  - Aggregate physicochemical descriptors via RDKit (already a dependency): MW, H-atom count, H-bond donors/acceptors, net charge, hydrophobicity, radius of gyration of the isolated solute.
  - Condition features: water-model one-hot (TIP3P/TIP4P-Ew), temperature (continuous, standardized), concentration.
- **Tier 2 — sequence descriptors** (when peptide library grows): position-aware encodings, learned embeddings.
- **Tier 3 — graph representations** (only with substantial data): molecular graph → GNN. Explicitly *deferred*; noted so the dataset schema keeps raw structures available.
- **Deliverables**: `scripts/ml/featurize.py`, a frozen feature spec, and a leakage audit (e.g., same molecule at 300/350 K must never straddle a train/test split blindly — see B.5).

### B.4 Phase B3 — Target representation & physics-informed reconstruction

- Define the canonical QENS forward model used for reconstruction: `S(q,ω) = R(ω) ⊗ [A(q)·δ(ω) + (1−A(q))·L(Γ(q), ω)]`, with `Γ(q) = D·q²` in the small-q diffusive regime.
- **Model targets** (B-physics): `D`, the `Γ(q)` curve (or just the diffusion slope + deviations), and EISF `A(q)`.
- Provide a `reconstruct_sqw()` utility that turns predicted parameters back into a full spectrum, so the surrogate's output is directly comparable to MD/experiment.
- Keep B-direct (raw-grid regression) as a documented fallback/benchmark, not the primary path.
- **Deliverables**: `scripts/ml/qens_model.py` (forward model + reconstruction), target extraction wired to the dataset builder.

### B.5 Phase B4 — Baseline models & honest validation

- **Model progression (data-efficiency first):**
  1. **Gaussian Process Regression** (scikit-learn / GPyTorch) — primary choice for ≤ tens of points; gives calibrated uncertainty, essential for active learning.
  2. Linear / ridge / kernel ridge baselines — sanity floor.
  3. Gradient-boosted trees — once the dataset reaches ~50+ rows.
  4. Small neural nets / GNNs — explicitly gated behind a dataset-size threshold (hundreds of rows).
- **Validation under tiny data:**
  - **Leave-one-out cross-validation** as the default metric.
  - **Grouped splits**: hold out an entire *molecule* (all its temperatures) to measure true generalization to unseen peptides, not just unseen temperatures.
  - Report uncertainty calibration, not just point error.
- **Metrics**: MAE/RMSE on `D` and `Γ(q)`; spectral error (e.g., integrated `|ΔS(q,ω)|`) for reconstructed spectra; coverage of predictive intervals.
- **Deliverables**: `scripts/ml/train.py`, `scripts/ml/evaluate.py`, a baseline results report with LOO and grouped-split numbers.

### B.6 Phase B5 — Data expansion & active learning

This phase closes the gap between "8 points" and "trainable model." It couples the ML model back to the MD pipeline (Workstream A) and `tb_squip/` automation.

- **Expansion axes** (cheapest generalization gains first):
  - More temperatures per existing molecule (cheap, reuses topology).
  - More peptides (Gly-Ala, Ala-Ala, tripeptides…) — the axis the model most needs.
  - Concentration variation.
- **Active learning loop**: use GP predictive variance to rank candidate (peptide, water, T) points by expected information gain, then dispatch the top candidates to the `tb_squip` workflow for automated MD + analysis, and fold results back into `data/squip_dataset.h5`.
- **Multi-fidelity option**: short (e.g., 2–5 ns) trajectories as a cheap low-fidelity tier; co-kriging / multi-fidelity GP to combine with the 20 ns high-fidelity runs. This can multiply effective dataset size per compute hour.
- **Deliverables**: `scripts/ml/active_learning.py`, an automated "propose → simulate → analyze → ingest" loop, and a running log of dataset growth vs. validation error (the key project-health curve).

### B.7 Phase B6 — Validation against MD and experiment

- Held-out MD state points (grouped by molecule) as the primary acceptance test.
- Where collaborator/published QENS exists for glycine/Gly-Gly in water, compare reconstructed `S(q,ω)` after resolution convolution and q-grid matching (this is the "Step 4: experimental comparison" noted in [MD/STEP3.md](MD/STEP3.md)).
- Sanity/physics checks: `D` increases with `T`; `Γ(q) ∝ q²` at low q; EISF bounded in [0, 1].

### B.8 Phase B7 — Packaging & inference

- A single inference entry point: `predict(descriptor, water_model, T) → {D, Γ(q), S(q,ω)}` with uncertainty.
- Model + feature spec + dataset version pinned together for reproducibility.
- Lightweight CLI mirroring the existing scripts' ergonomics (`python scripts/ml/predict.py glygly tip4pew 320K`).

### B.9 ML tooling & dependencies (new)

Additions beyond the current `requirements.txt` (`dynasor`, `h5py`, `matplotlib`, `MDAnalysis`, `numpy`, `rdkit`, `scipy`):

- `scikit-learn` (GP, KRR, trees, CV utilities) — core.
- `pandas` / `pyarrow` (tabular feature store).
- Optional, data-gated: `gpytorch` or `botorch` (scalable GPs + Bayesian active learning), `xgboost`/`lightgbm`, a NN framework (deferred).
- Experiment tracking: lightweight (CSV/JSON logs or MLflow) — decide in B4.

---

## 7. Phased Roadmap & Sequencing

```
Workstream A (data generator)                 Workstream B (the product)
─────────────────────────────                 ──────────────────────────
A1–A5  done/PoC ──┐
A6 verify 8 pts   │
A7 standardize ───┼──► B1 dataset/feature store
outputs           │       │
                  │       ▼
                  │    B2 featurization
                  │       │
                  │       ▼
                  │    B3 physics-informed targets + reconstruction
                  │       │
                  │       ▼
                  │    B4 baseline GP models + LOO/grouped validation
                  │       │
                  └──◄────┤  B5 active learning  (loops back into A via tb_squip)
                          ▼
                       B6 validation vs MD/experiment
                          ▼
                       B7 packaging & inference CLI
```

Indicative phasing (effort, not calendar — gated by compute for data expansion):

| Phase | Focus | Gate to next |
|-------|-------|--------------|
| A6–A7 | Verify + standardize all 8 outputs | Identical schema across all rows |
| B1 | Dataset & feature store | `data/squip_dataset.h5` builds reproducibly |
| B2–B3 | Features + physics-informed targets | `reconstruct_sqw()` round-trips MD within tolerance |
| B4 | Baseline GP + honest validation | LOO + grouped-split baseline reported |
| B5 | Data expansion / active learning | Dataset ≳ 30–50 points; error-vs-data curve trending down |
| B6 | Validation vs MD/experiment | Held-out molecule predicted within target tolerance |
| B7 | Packaging | `predict.py` reproduces a held-out point end-to-end |

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Too few data points to train any model** | Project-blocking | Physics-informed low-dim targets (B3); GP + LOO; active-learning data campaign (B5); multi-fidelity |
| Inconsistent analysis outputs across runs | Corrupts dataset | A7 canonicalization gate before any ML work |
| Descriptor doesn't generalize across peptides | Surrogate useless on new sequences | Grouped (leave-molecule-out) validation from day one; tiered descriptor escalation |
| Compute/storage cost of expansion (~5 h + ~100 GB/point) | Slows B5 | Multi-fidelity short runs; downsample/delete trajectories post-analysis (keep `*_sqw_arrays.npz`); prioritize via active learning |
| Unit/convention errors (rad/Å vs 1/Å, fs vs ps, nm vs Å) | Silent label corruption | Fix all units at the dataset boundary (B1); reuse existing conventions in [.github/github-instructions.md](.github/github-instructions.md) |
| Force-field-specific dynamics confound the model | Mixes two physical regimes | Treat water model/FF as an explicit categorical feature; consider per-family models |
| Scope creep into full MLIP | Multiplies project size | Explicitly out of scope here; re-scope separately if intended |

---

## 9. Success Criteria

**PoC-level (minimum viable surrogate):**
- A reproducible dataset linking descriptors/conditions to QENS observables for all available state points.
- A GP baseline that predicts `D` for a **held-out molecule** within a stated tolerance (e.g., within MD statistical error or a target % MAE), with calibrated uncertainty.
- A working `predict → reconstruct S(q,ω)` path that round-trips an MD-derived spectrum.

**Stretch:**
- Surrogate validated against experimental QENS after resolution convolution.
- Active-learning loop demonstrably reduces validation error per added MD run.
- Reasonable temperature interpolation (predict 325 K from 300/350 K training) and extrapolation to an unseen short peptide.

---

## 10. Open Questions

1. **"ML potential" interpretation** — Does the README's "ML-based potentials" mean an `S(q,ω)` **emulator/surrogate** (assumed here) or a true **ML interatomic potential** replacing the GROMACS force field? These are very different programs; the latter needs separate scoping.
2. **Compute budget for data expansion** — How much wall-time/storage can be committed to B5? This sets the ceiling on dataset size and therefore model class.
3. **Experimental reference data** — Is QENS data for these systems available for validation, and on what instrument resolution/q-grid?
4. **Target peptide library** — Which peptides beyond glycine/Gly-Gly define the generalization target (tripeptides? specific residues of interest)?
5. **Primary observable for stakeholders** — Is the deliverable the full `S(q,ω)` spectrum, or is `D` / `Γ(q)` sufficient for the intended use?

---

*This document supersedes the implicit, single-sentence ML plan in the README. The MD/QENS step documents (`MD/STEP1–3.md`) remain the authoritative operational references for Workstream A.*
