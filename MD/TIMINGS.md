# Production MD Timing Analysis

## Benchmark Summary

| Property | Value |
|----------|-------|
| **System** | Glycine AMBER99SB-ILDN 300K |
| **Atoms** | 15,680 atoms + 5,060 virtual sites (TIP4P-Ew) |
| **Benchmark Duration** | 10 ps (5,000 steps) |
| **Performance (CPU-only)** | **57.6 ns/day** |
| **Time per ns** | **0.417 hours** |
| **GPU Acceleration** | ❌ Not available (GROMACS built without GPU) |

---

## Hardware Configuration

| Component | Details |
|-----------|---------|
| CPU | Intel Core i7-11700K @ 3.60 GHz |
| Cores | 8 physical, 16 logical |
| MPI ranks | 2 (thread-MPI) |
| OpenMP threads | 8 per rank |
| SIMD | AVX2_256 (AVX_512 available but not used) |
| GPU | **Not available** (binary built without CUDA/OpenCL) |

---

## GPU Benchmark Attempt

```
Command: gmx mdrun -deffnm prod -nsteps 5000 -v -ntomp 8 -nb gpu -pme gpu -bonded gpu

Result: FAILED
Error: "Nonbonded interactions on the GPU were requested with -nb gpu, 
        but the GROMACS binary has been built without GPU support."
```

**Resolution**: To enable GPU acceleration, GROMACS must be recompiled with CUDA or OpenCL support. The current Windows installation uses CPU-only binaries.

---

## Projected Production Run Times

### Per-System (20 ns production run)

| System Type | Atoms | Est. Performance | Time for 20 ns |
|-------------|-------|------------------|----------------|
| AMBER TIP4P-Ew | ~20,500 | ~50-58 ns/day | **8-10 hours** |
| CHARMM TIP3P | ~16,000 | ~70-80 ns/day | **6-7 hours** |

### Total for All 8 Systems (Sequential)

| Scenario | Estimated Total Time |
|----------|---------------------|
| 8 × 20 ns (160 ns total) | **~60-70 hours** (2.5-3 days) |
| 8 × 10 ns (80 ns total) | **~30-35 hours** (1.3-1.5 days) |

---

## Performance Breakdown

### CPU Time Distribution

| Component | Wall Time (s) | Percentage |
|-----------|---------------|------------|
| **Force calculation** | 9.674 | 64.5% |
| **PME mesh** | 3.342 | 22.3% |
| **Write trajectory** | 0.498 | 3.3% |
| **Comm. energies** | 0.270 | 1.8% |
| **Comm. coord.** | 0.292 | 1.9% |
| **Neighbor search** | 0.208 | 1.4% |
| Other | 0.716 | 4.8% |
| **Total** | **15.000** | 100% |

### PME Mesh Breakdown

| PME Component | Wall Time (s) | Percentage |
|---------------|---------------|------------|
| PME redist. X/F | 1.065 | 7.1% |
| PME spread | 0.774 | 5.2% |
| 3D-FFT | 0.678 | 4.5% |
| PME gather | 0.489 | 3.3% |
| 3D-FFT Comm. | 0.204 | 1.4% |
| PME solve Elec | 0.122 | 0.8% |

---

## Load Balancing Analysis

| Metric | Value |
|--------|-------|
| DLB Status | Off (low imbalance) |
| Average load imbalance | 1.1% |
| Balanceable MD step fraction | 73% |
| Time lost to imbalance | 0.8% |

**Conclusion**: Load balancing is excellent; no intervention needed.

---

## Energy Conservation

| Metric | Value | Criterion |
|--------|-------|-----------|
| Conserved energy drift | 4.58×10⁻⁴ kJ/mol/ps/atom | < 0.01 ideal |

**Status**: ✅ Excellent energy conservation

---

## Trajectory Output Impact

**High-frequency output (10 fs) accounts for 3.3% of total runtime** - acceptable overhead for QENS analysis requirements.

| Output Rate | Est. Impact |
|-------------|-------------|
| 10 fs (current) | 3.3% of runtime |
| 100 fs | ~0.3% of runtime |
| 1 ps | ~0.03% of runtime |

---

## Storage Estimates

### Per System (20 ns @ 10 fs output)

| File | Estimated Size |
|------|----------------|
| prod.xtc | ~40 GB (AMBER) / ~30 GB (CHARMM) |
| prod.edr | ~200 MB |
| prod.log | ~10 MB |
| prod.cpt | ~50 MB |

### Total Storage Required

| Scenario | Storage |
|----------|---------|
| 8 systems × 20 ns | **~280-320 GB** |
| 8 systems × 10 ns | **~140-160 GB** |

---

## Optimization Recommendations

### 1. Enable AVX-512 (Potential 20-30% speedup)
Recompile GROMACS with `-DGMX_SIMD=AVX_512` for this CPU.

### 2. Use GPU Acceleration (Potential 5-10× speedup)
```bash
gmx mdrun -deffnm prod -nb gpu -pme gpu -bonded gpu
```
Expected: **200-400 ns/day** with modern GPU.

> ⚠️ **Note**: Current GROMACS installation (2021.5) was built **without GPU support**.
> GPU acceleration requires recompiling GROMACS with CUDA or OpenCL enabled:
> ```bash
> cmake .. -DGMX_GPU=CUDA -DCUDA_TOOLKIT_ROOT_DIR=/path/to/cuda
> ```

### 3. Reduce Trajectory Output for Testing
For initial validation, use 100 fs output:
```bash
# Temporary for testing
gmx mdrun -deffnm prod -nstxout-compressed 50
```

### 4. Parallel Execution
Run multiple systems simultaneously on different cores/nodes.

---

## Benchmark Command

```bash
cd systems/glycine/amber99sb/300K/production
gmx mdrun -deffnm prod -nsteps 5000 -v -ntomp 8
```

---

## System Details

```
GROMACS version: 2021.5
Precision: mixed (single for most, double for summation)
MPI: thread_mpi
OpenMP: enabled
FFT library: Intel MKL
Domain decomposition: 2 × 1 × 1
PME grid: 48 × 48 × 48
rlist: 1.332 nm (Verlet buffer)
```

---

## Conclusion

At **57.6 ns/day** (CPU-only), running all 8 production simulations (20 ns each) will take approximately **2.5-3 days** on this workstation.

**Current Status**: GPU acceleration unavailable (GROMACS built without GPU support).

For faster turnaround:
1. Reduce simulation length to 10 ns (~1.5 days total)
2. Recompile GROMACS with CUDA for GPU support (~0.3-0.5 days total)
3. Run on cluster with parallel jobs (~0.3 days total)
4. Use AVX-512 SIMD (recompile, ~20-30% speedup → ~2 days total)
