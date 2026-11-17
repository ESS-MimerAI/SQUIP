# Reducing Disk Usage: 140 GB → 50 GB per Production Run

## Current Setup

| Parameter | Value |
|-----------|-------|
| Simulation length | 20 ns |
| Output frequency | 10 fs (`nstxout-compressed = 5`) |
| Trajectory size | ~140 GB |

**Target**: ~50 GB per run (factor of ~2.8 reduction)

## Proof-of-Concept Science Goal (Scope)

Primary objective: preserve QENS features in the **0.01–10 meV** energy transfer range for pipeline validation. High-energy modes above this range can be partially degraded without blocking the PoC.

---

## Scaling Assumptions

Disk usage scales approximately with:

- **Total simulation time**
- **Output frequency** (`nstxout-compressed`)
- **Atom count** and **compression efficiency** (minor variations with temperature and water model)

---

## Option A: Reduce Simulation Length Only

| Parameter | Current | Modified | 
|-----------|---------|----------|
| Simulation time | 20 ns | **7 ns** |
| nsteps | 10,000,000 | **3,500,000** |
| Output frequency | 10 fs | 10 fs |
| Trajectory size | 140 GB | **~49 GB** |

### What You Lose

- Reduced **statistical sampling** of slow dynamics
- Harder to capture rare conformational transitions
- S(q,ω) resolution in the low-frequency domain (0.01-0.1 meV) degrades
- Loss of long-timescale decorrelation (affects dynamics > ~1 ns)

---

## Option B: Reduce Output Frequency Only

| Parameter | Current | Modified |
|-----------|---------|----------|
| Simulation time | 20 ns | 20 ns |
| Output frequency | 10 fs | **28 fs** |
| nstxout-compressed | 5 | **14** |
| Trajectory size | 140 GB | **~50 GB** |

### What You Lose

- High-frequency dynamics (librations, bond vibrations) become **undersampled**
- S(q,ω) at high energy transfers (> ~10 meV) becomes less accurate  
- Nyquist limit shifts from ~50 THz to ~18 THz
- Less suitable for analyzing fast hydrogen dynamics

**Nyquist reminder**: $f_{\mathrm{Nyq}} = 1/(2\,\Delta t_{\mathrm{out}})$

---

## Option C: Combined Approach (Recommended for Proof-of-Concept)

### Aggressive (~35 GB)

| Parameter | Current | Modified |
|-----------|---------|----------|
| Simulation time | 20 ns | **10 ns** |
| nsteps | 10,000,000 | **5,000,000** |
| Output frequency | 10 fs | **20 fs** |
| nstxout-compressed | 5 | **10** |
| Trajectory size | 140 GB | **~35 GB** |

### Moderate (~50 GB)

| Parameter | Current | Modified |
|-----------|---------|----------|
| Simulation time | 20 ns | **12 ns** |
| nsteps | 10,000,000 | **6,000,000** |
| Output frequency | 10 fs | **15 fs** |
| nstxout-compressed | 5 | **7-8** |
| Trajectory size | 140 GB | **~50 GB** |

### Tradeoffs

- Moderate loss in both statistical sampling and high-frequency resolution
- Still captures main QENS features (diffusion, rotations, librational modes)
- Nyquist limit at ~33 THz still covers most molecular motions

**Nyquist reminder**: $f_{\mathrm{Nyq}} = 1/(2\,\Delta t_{\mathrm{out}})$

---

## QENS Impact Summary

| Frequency Range | Motion Type | 10 fs | 15 fs | 20 fs | 28 fs |
|-----------------|-------------|-------|-------|-------|-------|
| < 0.1 meV | Diffusion | ✓ | ✓ | ✓ | ✓ |
| 0.1-1 meV | Rotations | ✓ | ✓ | ✓ | ✓ |
| 1-10 meV | Librations | ✓ | ✓ | ✓ | ~ |
| 10-50 meV | H-bond vibrations | ✓ | ✓ | ~ | ✗ |
| > 50 meV | Intramolecular | ✓ | ~ | ✗ | ✗ |

Legend: ✓ = well-resolved, ~ = partially resolved, ✗ = undersampled

---

## Recommendation for Proof-of-Concept

Use **Option C (Aggressive)** with 10 ns @ 20 fs output:

- Produces **~35 GB** per run
- Maintains good QENS accuracy for the typical 0.01-10 meV energy transfer range
- Sufficient for validating the analysis pipeline
- Can run full 20 ns @ 10 fs for publication-quality results later

## Risks and Caveats

- If output cadence approaches the timescale of a target mode, time-correlation functions and S(q,ω) may be biased.
- Shorter trajectories reduce statistical convergence, especially for slow diffusion or rare events.
- Comparisons across force fields remain valid, but absolute spectra at the high-frequency edge may diverge.

## Sanity-Check Validation Plan

1. Run a short 1–2 ns segment at **10 fs** and **20 fs** output.
2. Compare S(q,ω) in the target 0.01–10 meV range.
3. If deviations are within tolerance, proceed with the reduced-footprint production.

### MDP Changes Required

```mdp
; Modified for proof-of-concept (reduced disk footprint)
nsteps      = 5000000       ; 10 ns (5,000,000 × 2 fs)
nstxout-compressed = 10     ; Compressed coords every 20 fs (10 × 2 fs)
```

---

## Updated Cost Estimates (Option C Aggressive)

| System | Atoms | Time/run | Storage/run | Runs | Total Time | Total Storage |
|--------|-------|----------|-------------|------|------------|---------------|
| Glycine AMBER | 20,740 | ~2.4 h | ~35 GB | 2 | 4.8 h | 70 GB |
| Glycine CHARMM | 15,812 | ~1.8 h | ~28 GB | 2 | 3.6 h | 56 GB |
| GlyGly AMBER | 21,086 | ~2.4 h | ~36 GB | 2 | 4.8 h | 72 GB |
| GlyGly CHARMM | 16,070 | ~1.8 h | ~29 GB | 2 | 3.6 h | 58 GB |
| **Total** | | | | **8** | **~17 hours** | **~256 GB** |

**Comparison to full production:**
- Time: 17 h vs 33 h (48% reduction)
- Storage: 256 GB vs 1.0 TB (75% reduction)

---

## Date of Analysis
February 2, 2026
