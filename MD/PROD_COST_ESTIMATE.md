# Production Run Cost Estimate

## Measured Benchmark Results (Glycine 300K, 20 ns)

| Metric | AMBER (TIP4P-Ew) | CHARMM (TIP3P) |
|--------|------------------|----------------|
| Atoms | 20,740 | 15,812 |
| Wall time | 4h 44m (4.74 h) | 3h 32m (3.53 h) |
| Performance | 101.4 ns/day | 135.8 ns/day |
| Trajectory size | 140.7 GB | 112.6 GB |

**Hardware**: Intel Xeon W-2265 (12 cores @ 3.5 GHz), AVX-512, CPU-only

---

## Time Estimates (Sequential)

| System | Atoms | Time/run | Runs (2 temps) | Total Time |
|--------|-------|----------|----------------|------------|
| Glycine AMBER | 20,740 | **4.74 h** ✓ | 2 | 9.5 h |
| Glycine CHARMM | 15,812 | **3.53 h** ✓ | 2 | 7.1 h |
| GlyGly AMBER | 21,086 | ~4.8 h | 2 | 9.6 h |
| GlyGly CHARMM | 16,070 | ~3.6 h | 2 | 7.2 h |
| **Total** | | | **8** | **~33 hours** |

✓ = measured values

### Time Scaling Notes
- CHARMM (TIP3P, 3-site water) runs **34% faster** than AMBER (TIP4P-Ew, 4-site water)
- Performance scales roughly linearly with atom count for systems of this size
- GlyGly estimates based on atom count scaling from measured glycine runs

---

## Storage Estimates

| System | Atoms | Size/run | Runs (2 temps) | Total |
|--------|-------|----------|----------------|-------|
| Glycine AMBER | 20,740 | **141 GB** ✓ | 2 | 282 GB |
| Glycine CHARMM | 15,812 | **113 GB** ✓ | 2 | 226 GB |
| GlyGly AMBER | 21,086 | ~143 GB | 2 | 286 GB |
| GlyGly CHARMM | 16,070 | ~115 GB | 2 | 230 GB |
| **Total** | | | **8** | **~1.0 TB** |

✓ = measured values

### Storage Breakdown per Run
| File | Size |
|------|------|
| prod.xtc | ~140 GB (trajectory @ 10 fs) |
| prod.edr | ~1.3 MB (energy) |
| prod.gro | ~1.4 MB (final structure) |
| prod.log | ~1.3 MB (log) |
| prod.cpt | ~0.5 MB (checkpoint) |

---

## Summary

| Resource | Estimate |
|----------|----------|
| **Total compute time** | ~33 hours (1.4 days) sequential |
| **Total storage** | ~1.0 TB |
| **With 2 concurrent runs** | ~16.5 hours |
| **With 4 concurrent runs** | ~8 hours |

### Measured Performance Summary
| Force Field | Performance | Speedup vs AMBER |
|-------------|-------------|------------------|
| AMBER (TIP4P-Ew) | 101.4 ns/day | 1.0× |
| CHARMM (TIP3P) | 135.8 ns/day | **1.34×** |

---

## Parallelization Options

### Option 1: Sequential (single job at a time)
- Time: ~34 hours
- Simple, lowest memory usage

### Option 2: 2 concurrent jobs (saturate 24 cores)
- Time: ~17 hours
- Each job uses 12 threads: `gmx mdrun -ntomp 12`

### Option 3: 4 concurrent jobs (if memory allows)
- Time: ~8.5 hours
- Each job uses 6 threads: `gmx mdrun -ntomp 6`
- Requires ~8 GB RAM per job

---

## Notes

1. **Ensemble**: Production runs use NPT (constant pressure, temperature) as configured in `mdp/prod_300K.mdp` and `mdp/prod_350K.mdp`

2. **Output frequency**: Trajectories saved every 10 fs (critical for QENS analysis), which is the main driver of the large file sizes

3. **Trajectory compression**: `.xtc` format is already compressed; further compression yields minimal benefit

4. **Data retention**: After analysis, trajectories can be downsampled or deleted to reduce storage

---

## Date of Estimate
January 31, 2026
