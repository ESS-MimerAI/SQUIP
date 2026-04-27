# Running the SQUIP Pipeline: Glycine + AMBER99SB-ILDN @ 300 K

End-to-end walkthrough for a **single system** — glycine with the AMBER99SB-ILDN force field, TIP4P-Ew water, at 300 K — from the starting PDB in `structures/` all the way to the Dynasor S(q,ω) output files.

All paths are relative to the SQUIP project root.

---

## 0. Prerequisites

| Tool | Purpose |
|------|---------|
| GROMACS (gmx) | MD engine — topology, solvation, equilibration, production |
| Python 3 | Analysis scripts |
| MDAnalysis | Trajectory I/O for Dynasor helper scripts |
| Dynasor | S(q,ω) / F(q,t) calculation |
| scipy, numpy, matplotlib, h5py | Post-processing, fitting, plotting |

Local force field directory: `amber99sb-ildn.ff/` (includes custom **ZGLY** residue for zwitterionic single glycine).

---

## 1. Generate Topology (Substep 1.2)

Starting structure: `structures/glycine_zw_amber.pdb` (zwitterionic glycine, NH₃⁺/COO⁻).

```powershell
# pdb2gmx with the local amber99sb-ildn.ff
# Interactive prompt: select TIP4P-Ew water (option 3)
echo 3 | gmx pdb2gmx `
    -f structures/glycine_zw_amber.pdb `
    -o topologies/glycine_amber99sb.gro `
    -p topologies/glycine_amber99sb.top `
    -ff amber99sb-ildn -water select
```

**Outputs:** `topologies/glycine_amber99sb.gro`, `topologies/glycine_amber99sb.top`

Verify total charge is **0.000 e** in the gmx output.

---

## 2. Build Solvated Box with ~50 Molecules (Substep 1.3)

### 2a. Insert 50 glycine copies

Target concentration ≈ 1 M → box ≈ 5.4 nm cubic.

```powershell
gmx insert-molecules `
    -ci topologies/glycine_amber99sb.gro -nmol 50 `
    -box 5.4 5.4 5.4 `
    -o topologies/glycine_amber_50mol.gro
```

### 2b. Solvate with TIP4P-Ew water

```powershell
gmx solvate `
    -cp topologies/glycine_amber_50mol.gro `
    -cs tip4p.gro `
    -o topologies/glycine_amber_solvated.gro `
    -p topologies/glycine_amber99sb.top
```

System size should land around **20,500–21,000 atoms** (TIP4P-Ew has 4 sites per water, including the virtual M site).

---

## 3. Neutralise with Counter-ions (Substep 1.4)

Zwitterions are already neutral, so `genion` should report no ions needed. Run anyway to confirm:

```powershell
gmx grompp -f mdp/ions.mdp `
    -c topologies/glycine_amber_solvated.gro `
    -p topologies/glycine_amber99sb.top `
    -o topologies/glycine_amber_ions.tpr -maxwarn 1

echo 15 | gmx genion `
    -s topologies/glycine_amber_ions.tpr `
    -o topologies/glycine_amber_neutral.gro `
    -p topologies/glycine_amber99sb.top `
    -pname NA -nname CL -neutral
```

**Output:** `topologies/glycine_amber_neutral.gro` (identical to solvated if charge was already zero).

---

## 4. Energy Minimisation (Substep 1.5)

MDP file: `mdp/em.mdp` (steepest descent, 50 000 steps, emtol = 1000 kJ/mol/nm).

```powershell
gmx grompp -f mdp/em.mdp `
    -c topologies/glycine_amber_neutral.gro `
    -p topologies/glycine_amber99sb.top `
    -o systems/glycine/amber99sb/300K/minimization/em.tpr

gmx mdrun -v -deffnm systems/glycine/amber99sb/300K/minimization/em
```

Verify: `Fmax < 1000 kJ/mol/nm` in the log.

**Output:** `systems/glycine/amber99sb/300K/minimization/em.gro`

---

## 5. NVT Equilibration — 100 ps @ 300 K (Substep 1.6)

MDP file: `mdp/nvt_300K.mdp` (V-rescale thermostat, τ_T = 0.1 ps, gen_vel = yes, dt = 2 fs, nsteps = 50 000).

```powershell
gmx grompp -f mdp/nvt_300K.mdp `
    -c systems/glycine/amber99sb/300K/minimization/em.gro `
    -p topologies/glycine_amber99sb.top `
    -o systems/glycine/amber99sb/300K/nvt/nvt.tpr

gmx mdrun -v -deffnm systems/glycine/amber99sb/300K/nvt/nvt
```

Verify: temperature stabilises around 300 K (±5–10 K fluctuations OK).

**Outputs:** `nvt.gro`, `nvt.cpt` in `systems/glycine/amber99sb/300K/nvt/`

---

## 6. NPT Equilibration — 100 ps @ 300 K, 1 bar (Substep 1.7)

MDP file: `mdp/npt_300K.mdp` (Parrinello-Rahman barostat, τ_p = 2 ps, gen_vel = no, continues from NVT checkpoint).

```powershell
gmx grompp -f mdp/npt_300K.mdp `
    -c systems/glycine/amber99sb/300K/nvt/nvt.gro `
    -t systems/glycine/amber99sb/300K/nvt/nvt.cpt `
    -p topologies/glycine_amber99sb.top `
    -o systems/glycine/amber99sb/300K/npt/npt.tpr

gmx mdrun -v -deffnm systems/glycine/amber99sb/300K/npt/npt
```

Verify: pressure fluctuates around 1 bar (wide swings ±100 bar are normal), density ~1000 kg/m³.

**Outputs:** `npt.gro`, `npt.cpt` in `systems/glycine/amber99sb/300K/npt/`

---

## 7. Production MD — 20 ns @ 300 K (Step 2)

MDP file: `mdp/prod_300K_compact.mdp`

Key settings:
- dt = 2 fs, nsteps = 10 000 000 → **20 ns**
- `nstxout-compressed = 15` → trajectory frame every **30 fs**
- NPT ensemble (V-rescale + Parrinello-Rahman)
- LINCS h-bond constraints, lincs_iter = 2

### 7a. Generate TPR

```powershell
gmx grompp -f mdp/prod_300K_compact.mdp `
    -c systems/glycine/amber99sb/300K/npt/npt.gro `
    -t systems/glycine/amber99sb/300K/npt/npt.cpt `
    -p systems/glycine/amber99sb/topology.top `
    -o systems/glycine/amber99sb/300K/production/prod.tpr `
    -maxwarn 0
```

> **Note:** The production step references `systems/glycine/amber99sb/topology.top` (a copy/symlink of the working topology placed next to the system tree). This is the same topology used throughout, just relocated for the directory layout.

### 7b. Run production

```powershell
cd systems/glycine/amber99sb/300K/production
gmx mdrun -v -deffnm prod -ntomp 8
# or with GPU:
# gmx mdrun -v -deffnm prod -nb gpu -pme gpu -bonded gpu -update gpu
cd ../../../../../
```

**Outputs (in `systems/glycine/amber99sb/300K/production/`):**
- `prod.xtc` — compressed trajectory (~50 GB for 20 ns @ 30 fs)
- `prod.edr` — energy file
- `prod.log` — run log
- `prod.cpt` — checkpoint

---

## 8. Trajectory Post-Processing (Substep 2.5)

The raw `prod.xtc` needs PBC corrections before Dynasor analysis.

### 8a. Make molecules whole & centre

```bash
# On a Linux workstation (bash scripts):
scripts/trajectory_processing/process_trajectory.sh \
    systems/glycine/amber99sb/300K/production/
```

This runs three `gmx trjconv` passes:

1. `prod.xtc` → `prod_whole.xtc` (`-pbc whole` — stitch molecules broken across PBC)
2. `prod_whole.xtc` → `prod_center.xtc` (`-center -pbc mol -ur compact` — centre & compact)
3. `prod_center.xtc` → `prod_hydrogen.xtc` (hydrogen-only sub-trajectory for QENS)

On Windows/PowerShell you can run the underlying gmx commands directly:

```powershell
cd systems/glycine/amber99sb/300K/production

echo 0 | gmx trjconv -f prod.xtc -s prod.tpr -o prod_whole.xtc -pbc whole
echo "0 0" | gmx trjconv -f prod_whole.xtc -s prod.tpr -o prod_center.xtc -center -pbc mol -ur compact
```

### 8b. Create fixed-box trajectory for Dynasor

Dynasor assumes a **constant simulation cell**. Since the production run is NPT, we reimage the trajectory to a fixed box taken from the first frame.

```powershell
# Get first-frame box dimensions (in nm)
python scripts/get_box_from_first_frame.py `
    systems/glycine/amber99sb/300K/production/prod.tpr `
    systems/glycine/amber99sb/300K/production/prod_center.xtc
# Prints   5.366054 5.366054 5.366054

# Reimage to that fixed box (replace Lx Ly Lz with values above)
echo 0 | gmx trjconv `
    -f systems/glycine/amber99sb/300K/production/prod_center.xtc `
    -s systems/glycine/amber99sb/300K/production/prod.tpr `
    -o systems/glycine/amber99sb/300K/production/prod_nvt_fixed.xtc `
    -pbc mol -ur compact -box 5.366054 5.366054 5.366054
```

**Key output:** `prod_nvt_fixed.xtc` — the trajectory Dynasor will consume.

---

## 9. Compute S(q,ω) with Dynasor (Step 3)

Script: `scripts/dynasor_scripts/compute_sqw.py`

This script:
1. Loads `prod.tpr` + `prod_nvt_fixed.xtc` via MDAnalysis.
2. Builds element-based atom groups (H, C, N, O) on the fly, excluding TIP4P-Ew virtual sites (M/MW).
3. Wraps the trajectory in `GROMACSTrajectory` (duck-typed interface for Dynasor).
4. Generates spherical q-points up to q_max = 2.5 rad/Å.
5. Calls `compute_dynamic_structure_factors()` with `calculate_incoherent=True`.
6. Bins into 30 spherically-averaged q-shells.
7. Applies neutron scattering length weighting.
8. Saves results as `.npz` files.

### Run

```powershell
python scripts/dynasor_scripts/compute_sqw.py glycine amber99sb 300K
```

### Key Dynasor parameters (defaults in script)

| Parameter | Value | Meaning |
|-----------|-------|---------|
| q_max | 2.5 rad/Å | Covers QENS range 0.3–2.0 Å⁻¹ |
| max_q_points | 5000 | Sufficient sampling for spherical average |
| window_size | 2000 frames | 60 ps time window → ~0.07 meV energy resolution |
| window_step | 200 frames | Windows overlap by stepping 6 ps |
| dt | 30 fs | Inter-frame interval (from trajectory) |
| num_q_bins | 30 | Spherical averaging bins |

### Outputs (in `systems/glycine/amber99sb/300K/production/analysis/`)

| File | Contents |
|------|----------|
| `glycine_amber99sb_300K_sqw_raw.npz` | Raw (un-binned) S(q,ω) sample |
| `glycine_amber99sb_300K_sqw_averaged.npz` | Spherically averaged & q-binned |
| `glycine_amber99sb_300K_sqw_neutron.npz` | Neutron-weighted S(q,ω) |
| `glycine_amber99sb_300K_sqw_arrays.npz` | Convenience arrays: q_norms, omega_meV, Sqw_coh, Sqw_incoh, Fqt_coh, Fqt_incoh, time_fs |

---

## 10. Post-Processing & Validation

### 10a. Validate S(q,ω)

```powershell
python scripts/dynasor_scripts/validate_sqw.py `
    systems/glycine/amber99sb/300K/production/analysis/glycine_amber99sb_300K_sqw_arrays.npz
```

Checks: non-negativity, F_incoh(q,t=0) ≈ 1, q-range, energy resolution.

### 10b. Extract quasielastic linewidths Γ(q) & diffusion coefficient

```powershell
python scripts/dynasor_scripts/extract_linewidths.py `
    systems/glycine/amber99sb/300K/production/analysis/glycine_amber99sb_300K_sqw_arrays.npz
```

Fits F_incoh(q,t) to a single exponential → Γ(q) in meV.
Fits Γ vs q² (with q in Å⁻¹, **not** rad/Å) → self-diffusion coefficient D.

### 10c. Plot diagnostics

```powershell
# S(q,ω) heatmap
python scripts/dynasor_scripts/plot_sqw.py `
    systems/glycine/amber99sb/300K/production/analysis/glycine_amber99sb_300K_sqw_arrays.npz `
    --out sqw_heatmap.png --type heatmap

# F(q,t) decay curves
python scripts/dynasor_scripts/plot_sqw.py `
    systems/glycine/amber99sb/300K/production/analysis/glycine_amber99sb_300K_sqw_arrays.npz `
    --out fqt_decay.png --type fqt
```

---

## Summary: File Flow

```
structures/glycine_zw_amber.pdb          ← starting PDB (zwitterion)
        │
        ▼  gmx pdb2gmx
topologies/glycine_amber99sb.{gro,top}   ← topology + single-molecule coords
        │
        ▼  gmx insert-molecules
topologies/glycine_amber_50mol.gro       ← 50 copies in a box
        │
        ▼  gmx solvate
topologies/glycine_amber_solvated.gro    ← solvated with TIP4P-Ew
        │
        ▼  gmx genion
topologies/glycine_amber_neutral.gro     ← neutralised (ions if needed)
        │
        ▼  gmx grompp + mdrun (em.mdp)
systems/.../minimization/em.gro          ← energy-minimised
        │
        ▼  gmx grompp + mdrun (nvt_300K.mdp)
systems/.../nvt/nvt.{gro,cpt}           ← temperature-equilibrated
        │
        ▼  gmx grompp + mdrun (npt_300K.mdp)
systems/.../npt/npt.{gro,cpt}           ← pressure- & density-equilibrated
        │
        ▼  gmx grompp + mdrun (prod_300K_compact.mdp)
systems/.../production/prod.{xtc,tpr}   ← 20 ns production trajectory
        │
        ▼  gmx trjconv (whole → centre → fixed box)
systems/.../production/prod_nvt_fixed.xtc  ← constant-cell trajectory
        │
        ▼  python compute_sqw.py glycine amber99sb 300K
systems/.../production/analysis/
    glycine_amber99sb_300K_sqw_raw.npz
    glycine_amber99sb_300K_sqw_averaged.npz
    glycine_amber99sb_300K_sqw_neutron.npz
    glycine_amber99sb_300K_sqw_arrays.npz   ← final S(q,ω) data
```

Where `systems/.../` = `systems/glycine/amber99sb/300K/`.
