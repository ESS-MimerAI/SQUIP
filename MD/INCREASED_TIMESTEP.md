# Increased Trajectory Output Timestep Analysis

## Summary

Changed trajectory output frequency from **10 fs to 30 fs** to reduce storage requirements by ~3×.

| Parameter | Original | Modified |
|-----------|----------|----------|
| `nstxout-compressed` | 5 | 15 |
| Output interval | 10 fs | 30 fs |
| Frames per 20 ns | 2,000,000 | 666,667 |
| Estimated trajectory size (AMBER) | ~140 GB | **~47 GB** |
| Estimated trajectory size (CHARMM) | ~113 GB | **~38 GB** |

---

## Storage Impact

### Per-System Estimates

| System | Original (10 fs) | Modified (30 fs) | Reduction |
|--------|------------------|------------------|-----------|
| Glycine AMBER | 141 GB | ~47 GB | 3× |
| Glycine CHARMM | 113 GB | ~38 GB | 3× |
| GlyGly AMBER | ~143 GB | ~48 GB | 3× |
| GlyGly CHARMM | ~115 GB | ~38 GB | 3× |

### Total Storage

| Configuration | 8 Systems Total |
|---------------|-----------------|
| Original (10 fs) | ~1.0 TB |
| Modified (30 fs) | **~340 GB** |

---

## QENS Justification

### Timescales Probed by QENS

Quasi-Elastic Neutron Scattering (QENS) probes molecular dynamics on timescales of:
- **0.1 ps to 100 ps** (typical range)
- Energy resolution: ~1-100 μeV corresponds to ~10-1000 ps dynamics
- Fastest motions observed: ~0.1 ps (100 fs)

### Nyquist Sampling Criterion

To properly sample dynamics at timescale τ, the sampling interval Δt must satisfy:
$$\Delta t \leq \frac{\tau}{2}$$

| Fastest dynamics | Required Δt | 30 fs adequate? |
|------------------|-------------|-----------------|
| 100 fs (0.1 ps) | ≤ 50 fs | ✓ Yes |
| 1 ps | ≤ 500 fs | ✓ Yes |
| 10 ps | ≤ 5 ps | ✓ Yes |

**Conclusion**: 30 fs output satisfies Nyquist criterion for QENS-relevant dynamics (≥100 fs).

### Intermediate Scattering Function I(q,t)

For S(q,ω) calculation via Fourier transform of I(q,t):
- I(q,t) is computed at discrete time points
- 30 fs spacing provides excellent resolution for picosecond dynamics
- Correlation functions decay over ~1-100 ps → well sampled

### Literature Support

Typical MD trajectory output for QENS studies:
- 10-50 fs is common in published work
- Some studies use 100 fs with good results
- 30 fs is conservative and well within acceptable range

**Reference**: Bellissent-Funel et al. (2016) "Water Determines the Structure and Dynamics of Proteins" Chem. Rev. 116, 7673-7697.

---

## Modified MDP File

Created `mdp/prod_300K_compact.mdp` with key change:

```
; Original (10 fs output)
nstxout-compressed = 5      ; 5 × 2 fs = 10 fs

; Modified (30 fs output)  
nstxout-compressed = 15     ; 15 × 2 fs = 30 fs
```

All other parameters remain identical to ensure simulation fidelity.

---

## Commands to Run Modified Production

### Generate TPR with compact MDP

```bash
cd ~/SQUIP/systems/glycine/amber99sb/300K/production

gmx grompp -f ~/SQUIP/mdp/prod_300K_compact.mdp \
    -c ../npt/npt.gro \
    -t ../npt/npt.cpt \
    -p ../../topology.top \
    -o prod.tpr \
    -maxwarn 0
```

### Run Production

```bash
gmx mdrun -v -deffnm prod -ntomp 12
```

### One-liner for Background Execution

```bash
cd ~/SQUIP/systems/glycine/amber99sb/300K/production && \
gmx grompp -f ~/SQUIP/mdp/prod_300K_compact.mdp -c ../npt/npt.gro -t ../npt/npt.cpt -p ../../topology.top -o prod.tpr -maxwarn 0 && \
nohup gmx mdrun -v -deffnm prod -ntomp 12 > run.log 2>&1 &
```

---

## Comparison: 10 fs vs 30 fs Output

| Aspect | 10 fs | 30 fs |
|--------|-------|-------|
| Storage per 20 ns run | ~140 GB | ~47 GB |
| Total 8 systems | ~1.0 TB | ~340 GB |
| Nyquist limit | 20 fs dynamics | 60 fs dynamics |
| QENS adequate | ✓ | ✓ |
| Analysis speed | Slower (3× frames) | Faster |
| S(q,ω) quality | Excellent | Very good |

### Recommendation

**30 fs output is recommended** for this proof-of-concept because:
1. Storage reduced from 1 TB to 340 GB (manageable)
2. Still exceeds requirements for QENS analysis
3. Faster post-processing and analysis
4. Original 10 fs can be used later if higher resolution needed

---

## Alternative Options Considered

| Option | Storage | QENS Quality | Notes |
|--------|---------|--------------|-------|
| 10 fs | 1.0 TB | Excellent | Original, too large |
| 20 fs | 500 GB | Excellent | Moderate reduction |
| **30 fs** | **340 GB** | **Very good** | **Selected** |
| 50 fs | 200 GB | Good | Marginal for fast dynamics |
| 100 fs | 100 GB | Adequate | May miss fastest motions |

---

## Date

February 3, 2026
