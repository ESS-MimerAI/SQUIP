# Step 2: Production MD Simulations - Implementation Plan

## Overview
This document provides a detailed implementation plan for **Step 2: Production MD** from the SQUIP Proof of Concept workflow. The goal is to run production molecular dynamics simulations and generate trajectories suitable for QENS (Quasi-Elastic Neutron Scattering) analysis.

**Timeline**: Week 2-3  
**Input**: 8 fully equilibrated systems from Step 1 (NPT equilibrated)  
**Output**: Production trajectories with 30 fs time resolution for S(q,ω) calculation

---

## Prerequisites

### Verified Systems from Step 1

| System | Force Field | Water Model | Temperature | Status |
|--------|-------------|-------------|-------------|--------|
| Glycine | AMBER99SB-ILDN | TIP4P-Ew | 300 K | ✅ Ready |
| Glycine | AMBER99SB-ILDN | TIP4P-Ew | 350 K | ✅ Ready |
| Glycine | CHARMM27 | TIP3P | 300 K | ✅ Ready |
| Glycine | CHARMM27 | TIP3P | 350 K | ✅ Ready |
| Gly-Gly | AMBER99SB-ILDN | TIP4P-Ew | 300 K | ✅ Ready |
| Gly-Gly | AMBER99SB-ILDN | TIP4P-Ew | 350 K | ✅ Ready |
| Gly-Gly | CHARMM27 | TIP3P | 300 K | ✅ Ready |
| Gly-Gly | CHARMM27 | TIP3P | 350 K | ✅ Ready |

### System Specifications

| Property | AMBER (TIP4P-Ew) | CHARMM (TIP3P) |
|----------|------------------|----------------|
| Solute molecules | 50 | 50 |
| Total atoms | ~20,500-21,000 | ~15,500-16,500 |
| Box size | ~5.4 nm | ~5.4 nm |
| Concentration | ~1 M | ~1 M |

### Input Files Required (per system)
- `systems/{molecule}/{forcefield}/{temp}K/npt/npt.gro` - Equilibrated structure
- `systems/{molecule}/{forcefield}/{temp}K/npt/npt.cpt` - Checkpoint for velocity continuation
- `systems/{molecule}/{forcefield}/topology.top` - Topology file

---

## Substep 2.1: Create Production MDP Files

### Objective
Create simulation parameter files optimized for QENS-relevant trajectory output.

### Key Parameters for QENS Analysis

1. **Trajectory Saving Frequency**: Every 20 fs (reduced-frequency) or 30 fs (compact) for PoC storage limits
2. **Simulation Length**: 10-20 ns (balance between statistics and storage)
3. **Ensemble**: NPT (matches experimental conditions)
4. **Thermostat**: V-rescale (minimal dynamic perturbation)
5. **Barostat**: Parrinello-Rahman (proper NPT ensemble)

### Implementation Steps

1. **Create Production MDP for 300 K (Reduced Frequency)**
   ```bash
   cat > mdp/prod_300K.mdp << 'EOF'
   ; prod_300K.mdp - Production MD at 300 K for QENS analysis
    ; Reduced-frequency trajectory output for PoC S(q,ω) calculation
   
   ; Run parameters
   integrator  = md            ; Leap-frog integrator
   dt          = 0.002         ; 2 fs timestep
   nsteps      = 10000000      ; 20 ns (10,000,000 × 2 fs)
   
   ; Output control - CRITICAL for QENS
   nstlog      = 5000          ; Log every 10 ps
   nstenergy   = 5000          ; Energy every 10 ps
   nstxout     = 0             ; No full-precision coordinates (use compressed)
   nstvout     = 0             ; No velocities to main trajectory
    nstxout-compressed = 10     ; Compressed coords every 20 fs (10 × 2 fs)
   compressed-x-grps = System  ; Save all atoms
   
   ; Neighbor searching
   cutoff-scheme = Verlet
   nstlist     = 20            ; Update neighbor list every 40 fs
   rlist       = 1.2           ; nm
   
   ; Electrostatics (PME)
   coulombtype = PME
   rcoulomb    = 1.2           ; nm
   pme_order   = 4             ; Cubic interpolation
   fourierspacing = 0.12       ; nm
   
   ; Van der Waals
   vdwtype     = Cut-off
   vdw-modifier = Potential-shift
   rvdw        = 1.2           ; nm
   DispCorr    = EnerPres      ; Long-range dispersion correction
   
   ; Temperature coupling
   tcoupl      = V-rescale     ; Stochastic velocity rescaling
   tc-grps     = System        ; Single coupling group
   tau_t       = 0.5           ; Relaxed coupling (ps) - less perturbation
   ref_t       = 300           ; Target temperature (K)
   
   ; Pressure coupling
   pcoupl          = Parrinello-Rahman
   pcoupltype      = isotropic
   tau_p           = 2.0       ; Time constant (ps)
   ref_p           = 1.0       ; Target pressure (bar)
   compressibility = 4.5e-5    ; Water compressibility (bar^-1)
   refcoord_scaling = com      ; Scale reference coordinates
   
   ; Velocity generation
   gen_vel     = no            ; Continue from NPT equilibration
   
   ; Periodic boundary conditions
   pbc         = xyz
   
   ; Constraints
   constraints          = h-bonds
   constraint_algorithm = LINCS
   lincs_iter           = 2     ; Increased for better energy conservation
   lincs_order          = 4
   
   ; Center of mass motion removal
   comm-mode   = Linear
   nstcomm     = 100           ; Remove COM motion every 200 fs
   EOF
   ```

2. **Create Production MDP for 350 K (Reduced Frequency)**
   ```bash
   cat > mdp/prod_350K.mdp << 'EOF'
    ; prod_350K.mdp - Production MD at 350 K for QENS analysis
    ; Reduced-frequency trajectory output for PoC S(q,ω) calculation
   
   ; Run parameters
   integrator  = md
   dt          = 0.002         ; 2 fs timestep
   nsteps      = 10000000      ; 20 ns
   
   ; Output control - CRITICAL for QENS
   nstlog      = 5000
   nstenergy   = 5000
   nstxout     = 0
   nstvout     = 0
    nstxout-compressed = 10     ; Every 20 fs
   compressed-x-grps = System
   
   ; Neighbor searching
   cutoff-scheme = Verlet
   nstlist     = 20
   rlist       = 1.2
   
   ; Electrostatics
   coulombtype = PME
   rcoulomb    = 1.2
   pme_order   = 4
   fourierspacing = 0.12
   
   ; Van der Waals
   vdwtype     = Cut-off
   vdw-modifier = Potential-shift
   rvdw        = 1.2
   DispCorr    = EnerPres
   
   ; Temperature coupling
   tcoupl      = V-rescale
   tc-grps     = System
   tau_t       = 0.5
   ref_t       = 350           ; Higher temperature
   
   ; Pressure coupling
   pcoupl          = Parrinello-Rahman
   pcoupltype      = isotropic
   tau_p           = 2.0
   ref_p           = 1.0
   compressibility = 4.5e-5
   refcoord_scaling = com
   
   ; Velocity generation
   gen_vel     = no
   
   ; PBC
   pbc         = xyz
   
   ; Constraints
   constraints          = h-bonds
   constraint_algorithm = LINCS
   lincs_iter           = 2
   lincs_order          = 4
   
   ; COM motion
   comm-mode   = Linear
   nstcomm     = 100
   EOF
   ```

3. **Create Compact Production MDP for 300 K (PoC)**
    ```bash
    cat > mdp/prod_300K_compact.mdp << 'EOF'
    ; prod_300K_compact.mdp - Production MD at 300 K with reduced trajectory size
    ; Output every 30 fs instead of 10 fs to reduce storage by ~3x
    ; Target: ~50 GB trajectory instead of ~140 GB
   
    ; Run parameters
    integrator  = md            ; Leap-frog integrator
    dt          = 0.002         ; 2 fs timestep
    nsteps      = 10000000      ; 20 ns (10,000,000 × 2 fs)
   
    ; Output control - REDUCED FREQUENCY for smaller files
    nstlog      = 5000          ; Log every 10 ps
    nstenergy   = 5000          ; Energy every 10 ps
    nstxout     = 0             ; No full-precision coordinates
    nstvout     = 0             ; No velocities
    nstxout-compressed = 15     ; Compressed coords every 30 fs (15 × 2 fs)
    compressed-x-grps = System  ; Save all atoms
   
    ; Neighbor searching
    cutoff-scheme = Verlet
    nstlist     = 20            ; Update neighbor list every 40 fs
    rlist       = 1.2           ; nm
   
    ; Electrostatics (PME)
    coulombtype = PME
    rcoulomb    = 1.2           ; nm
    pme_order   = 4             ; Cubic interpolation
    fourierspacing = 0.12       ; nm
   
    ; Van der Waals
    vdwtype     = Cut-off
    vdw-modifier = Potential-shift
    rvdw        = 1.2           ; nm
    DispCorr    = EnerPres      ; Long-range dispersion correction
   
    ; Temperature coupling
    tcoupl      = V-rescale     ; Stochastic velocity rescaling
    tc-grps     = System        ; Single coupling group
    tau_t       = 0.5           ; Relaxed coupling (ps)
    ref_t       = 300           ; Target temperature (K)
   
    ; Pressure coupling
    pcoupl          = Parrinello-Rahman
    pcoupltype      = isotropic
    tau_p           = 2.0       ; Time constant (ps)
    ref_p           = 1.0       ; Target pressure (bar)
    compressibility = 4.5e-5    ; Water compressibility (bar^-1)
    refcoord_scaling = com      ; Scale reference coordinates
   
    ; Velocity generation
    gen_vel     = no            ; Continue from NPT equilibration
   
    ; Periodic boundary conditions
    pbc         = xyz
   
    ; Constraints
    constraints          = h-bonds
    constraint_algorithm = LINCS
    lincs_iter           = 2     ; Increased for better energy conservation
    lincs_order          = 4
   
    ; Center of mass motion removal
    comm-mode   = Linear
    nstcomm     = 100           ; Remove COM motion every 200 fs
    EOF
    ```

4. **Create Compact Production MDP for 350 K (PoC)**
    ```bash
    cat > mdp/prod_350K_compact.mdp << 'EOF'
    ; prod_350K_compact.mdp - Production MD at 350 K with reduced trajectory size
    ; Output every 30 fs instead of 10 fs to reduce storage by ~3x
    ; Target: ~50 GB trajectory instead of ~140 GB
   
    ; Run parameters
    integrator  = md            ; Leap-frog integrator
    dt          = 0.002         ; 2 fs timestep
    nsteps      = 10000000      ; 20 ns (10,000,000 × 2 fs)
   
    ; Output control - REDUCED FREQUENCY for smaller files
    nstlog      = 5000          ; Log every 10 ps
    nstenergy   = 5000          ; Energy every 10 ps
    nstxout     = 0             ; No full-precision coordinates
    nstvout     = 0             ; No velocities
    nstxout-compressed = 15     ; Compressed coords every 30 fs (15 × 2 fs)
    compressed-x-grps = System  ; Save all atoms
   
    ; Neighbor searching
    cutoff-scheme = Verlet
    nstlist     = 20            ; Update neighbor list every 40 fs
    rlist       = 1.2           ; nm
   
    ; Electrostatics (PME)
    coulombtype = PME
    rcoulomb    = 1.2           ; nm
    pme_order   = 4             ; Cubic interpolation
    fourierspacing = 0.12       ; nm
   
    ; Van der Waals
    vdwtype     = Cut-off
    vdw-modifier = Potential-shift
    rvdw        = 1.2           ; nm
    DispCorr    = EnerPres      ; Long-range dispersion correction
   
    ; Temperature coupling
    tcoupl      = V-rescale     ; Stochastic velocity rescaling
    tc-grps     = System        ; Single coupling group
    tau_t       = 0.5           ; Relaxed coupling (ps)
    ref_t       = 350           ; Target temperature (K)
   
    ; Pressure coupling
    pcoupl          = Parrinello-Rahman
    pcoupltype      = isotropic
    tau_p           = 2.0       ; Time constant (ps)
    ref_p           = 1.0       ; Target pressure (bar)
    compressibility = 4.5e-5    ; Water compressibility (bar^-1)
    refcoord_scaling = com      ; Scale reference coordinates
   
    ; Velocity generation
    gen_vel     = no            ; Continue from NPT equilibration
   
    ; Periodic boundary conditions
    pbc         = xyz
   
    ; Constraints
    constraints          = h-bonds
    constraint_algorithm = LINCS
    lincs_iter           = 2     ; Increased for better energy conservation
    lincs_order          = 4
   
    ; Center of mass motion removal
    comm-mode   = Linear
    nstcomm     = 100           ; Remove COM motion every 200 fs
    EOF
    ```

### MDP Parameter Rationale

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `nstxout-compressed = 10` | 20 fs | Reduced-frequency output for PoC |
| `nstxout-compressed = 15` | 30 fs | Compact output (~50 GB per run) |
| `tau_t = 0.5` | 0.5 ps | Relaxed coupling reduces thermostat artifacts |
| `lincs_iter = 2` | 2 | Better energy conservation |
| `DispCorr = EnerPres` | On | Correct for LJ cutoff |
| `nsteps = 10000000` | 20 ns | Sufficient sampling for S(q,ω) |

### Deliverables
- `mdp/prod_300K.mdp` - Production parameters for 300 K
- `mdp/prod_350K.mdp` - Production parameters for 350 K
- `mdp/prod_300K_compact.mdp` - Compact production parameters for 300 K
- `mdp/prod_350K_compact.mdp` - Compact production parameters for 350 K

---

## Substep 2.2: Prepare TPR Files

### Objective
Generate binary run input files for all 8 production simulations.

### Implementation Steps

1. **Create Production Directory Structure**
   ```bash
   # Create production directories for all systems
   for mol in glycine glygly; do
       for ff in amber99sb charmm27; do
           for temp in 300K 350K; do
               mkdir -p systems/${mol}/${ff}/${temp}/production
           done
       done
   done
   ```

2. **Generate TPR Files - AMBER Systems**
   ```bash
   # Glycine AMBER 300K
    gmx grompp -f mdp/prod_300K_compact.mdp \
       -c systems/glycine/amber99sb/300K/npt/npt.gro \
       -t systems/glycine/amber99sb/300K/npt/npt.cpt \
       -p systems/glycine/amber99sb/topology.top \
       -o systems/glycine/amber99sb/300K/production/prod.tpr \
       -maxwarn 0
   
   # Glycine AMBER 350K
    gmx grompp -f mdp/prod_350K_compact.mdp \
       -c systems/glycine/amber99sb/350K/npt/npt.gro \
       -t systems/glycine/amber99sb/350K/npt/npt.cpt \
       -p systems/glycine/amber99sb/topology.top \
       -o systems/glycine/amber99sb/350K/production/prod.tpr \
       -maxwarn 0
   
   # Gly-Gly AMBER 300K
    gmx grompp -f mdp/prod_300K_compact.mdp \
       -c systems/glygly/amber99sb/300K/npt/npt.gro \
       -t systems/glygly/amber99sb/300K/npt/npt.cpt \
       -p systems/glygly/amber99sb/topology.top \
       -o systems/glygly/amber99sb/300K/production/prod.tpr \
       -maxwarn 0
   
   # Gly-Gly AMBER 350K
    gmx grompp -f mdp/prod_350K_compact.mdp \
       -c systems/glygly/amber99sb/350K/npt/npt.gro \
       -t systems/glygly/amber99sb/350K/npt/npt.cpt \
       -p systems/glygly/amber99sb/topology.top \
       -o systems/glygly/amber99sb/350K/production/prod.tpr \
       -maxwarn 0
   ```

3. **Generate TPR Files - CHARMM Systems**
   ```bash
   # Glycine CHARMM 300K
    gmx grompp -f mdp/prod_300K_compact.mdp \
       -c systems/glycine/charmm27/300K/npt/npt.gro \
       -t systems/glycine/charmm27/300K/npt/npt.cpt \
       -p systems/glycine/charmm27/topology.top \
       -o systems/glycine/charmm27/300K/production/prod.tpr \
       -maxwarn 0
   
   # Glycine CHARMM 350K
    gmx grompp -f mdp/prod_350K_compact.mdp \
       -c systems/glycine/charmm27/350K/npt/npt.gro \
       -t systems/glycine/charmm27/350K/npt/npt.cpt \
       -p systems/glycine/charmm27/topology.top \
       -o systems/glycine/charmm27/350K/production/prod.tpr \
       -maxwarn 0
   
   # Gly-Gly CHARMM 300K
    gmx grompp -f mdp/prod_300K_compact.mdp \
       -c systems/glygly/charmm27/300K/npt/npt.gro \
       -t systems/glygly/charmm27/300K/npt/npt.cpt \
       -p systems/glygly/charmm27/topology.top \
       -o systems/glygly/charmm27/300K/production/prod.tpr \
       -maxwarn 0
   
   # Gly-Gly CHARMM 350K
    gmx grompp -f mdp/prod_350K_compact.mdp \
       -c systems/glygly/charmm27/350K/npt/npt.gro \
       -t systems/glygly/charmm27/350K/npt/npt.cpt \
       -p systems/glygly/charmm27/topology.top \
       -o systems/glygly/charmm27/350K/production/prod.tpr \
       -maxwarn 0
   ```

4. **Verify TPR Generation**
   - Check for warnings in grompp output
    - Verify atom counts match equilibrated systems
    - Confirm trajectory output frequency is 30 fs

### Deliverables
- 8 TPR files: `systems/{mol}/{ff}/{temp}K/production/prod.tpr`

---

## Substep 2.3: Run Production Simulations

### Objective
Execute 20 ns production MD for all 8 systems with compact trajectory output.

### Implementation Steps

1. **Run Simulations Locally (Sequential)**
   ```bash
   # Run all 8 simulations sequentially
   for mol in glycine glygly; do
       for ff in amber99sb charmm27; do
           for temp in 300K 350K; do
               echo "Running ${mol}_${ff}_${temp}..."
               cd systems/${mol}/${ff}/${temp}/production
               gmx mdrun -v -deffnm prod -ntomp 8
               cd ../../../../../
           done
       done
   done
   ```

2. **Run Simulations with GPU Acceleration**
   ```bash
   # If GPU available
   gmx mdrun -v -deffnm prod -nb gpu -pme gpu -bonded gpu -update gpu
   ```

3. **Run Simulations on Cluster (SLURM)**
   ```bash
   #!/bin/bash
   #SBATCH --job-name=squip_prod
   #SBATCH --nodes=1
   #SBATCH --ntasks=1
   #SBATCH --cpus-per-task=16
   #SBATCH --time=48:00:00
   #SBATCH --partition=standard
   #SBATCH --array=0-7
   
   # Define system array
   SYSTEMS=(
       "glycine/amber99sb/300K"
       "glycine/amber99sb/350K"
       "glycine/charmm27/300K"
       "glycine/charmm27/350K"
       "glygly/amber99sb/300K"
       "glygly/amber99sb/350K"
       "glygly/charmm27/300K"
       "glygly/charmm27/350K"
   )
   
   SYSTEM=${SYSTEMS[$SLURM_ARRAY_TASK_ID]}
   cd systems/${SYSTEM}/production
   
   gmx mdrun -v -deffnm prod -ntomp ${SLURM_CPUS_PER_TASK}
   ```

4. **Monitor Progress**
   ```bash
   # Check simulation progress
   for mol in glycine glygly; do
       for ff in amber99sb charmm27; do
           for temp in 300K 350K; do
               log=systems/${mol}/${ff}/${temp}/production/prod.log
               if [ -f "$log" ]; then
                   echo "${mol}_${ff}_${temp}:"
                   tail -1 "$log" | grep -oP 'step \d+|time \d+\.\d+'
               fi
           done
       done
   done
   ```

### Estimated Runtime

| System Type | Atoms | GPU (ns/day) | CPU-only (ns/day) | 20 ns Runtime |
|-------------|-------|--------------|-------------------|---------------|
| AMBER TIP4P-Ew | ~20,500 | ~50-100 | ~5-10 | 0.2-0.4 days (GPU) |
| CHARMM TIP3P | ~16,000 | ~80-150 | ~8-15 | 0.1-0.3 days (GPU) |

**Total Estimated Time**:
- With GPU: ~2-4 days for all 8 systems (sequential) or ~0.5 days (parallel)
- CPU-only: ~2-4 weeks for all 8 systems (sequential)

### Deliverables (per system)
- `prod.xtc` - Compressed trajectory (30 fs resolution)
- `prod.edr` - Energy file
- `prod.log` - Log file
- `prod.cpt` - Checkpoint for continuation
- `prod.gro` - Final structure

---

## Substep 2.4: Trajectory Validation

### Objective
Verify production trajectories are suitable for QENS analysis.

### Implementation Steps

1. **Check Trajectory Completeness**
   ```bash
   # Verify trajectory duration for each system
   for mol in glycine glygly; do
       for ff in amber99sb charmm27; do
           for temp in 300K 350K; do
               xtc=systems/${mol}/${ff}/${temp}/production/prod.xtc
               if [ -f "$xtc" ]; then
                   echo "${mol}_${ff}_${temp}:"
                   gmx check -f "$xtc" 2>&1 | grep -E "Last frame|Coords|Step"
               fi
           done
       done
   done
   ```

2. **Verify Frame Spacing (30 fs)**
   ```bash
    # Check first few frames to confirm 30 fs interval
   gmx dump -f prod.xtc 2>&1 | head -50 | grep "time="
    # Should show: time= 0.000, time= 0.030, time= 0.060, ...
   ```

3. **Extract Temperature and Pressure**
   ```bash
   # Temperature stability check
   echo "16 0" | gmx energy -f prod.edr -o temperature.xvg
   # Pressure check
   echo "18 0" | gmx energy -f prod.edr -o pressure.xvg
   # Density check
   echo "24 0" | gmx energy -f prod.edr -o density.xvg
   ```

4. **Verify No Crashes or Warnings**
   ```bash
   # Check for LINCS warnings or other issues
   grep -i "warning\|error\|LINCS" prod.log
   ```

5. **Calculate Average Properties**
   ```bash
   # Create analysis script
   cat > scripts/analyze_production.py << 'EOF'
   #!/usr/bin/env python3
   """Analyze production MD trajectory properties."""
   
   import subprocess
   import os
   import sys
   
   def analyze_system(system_path):
       """Analyze a single production trajectory."""
       edr = os.path.join(system_path, "production", "prod.edr")
       
       if not os.path.exists(edr):
           print(f"  Not found: {edr}")
           return None
       
       # Extract averages using gmx energy
       result = subprocess.run(
           ["gmx", "energy", "-f", edr],
           input="16 18 24 0\n",
           capture_output=True,
           text=True
       )
       
       # Parse output
       lines = result.stdout.split('\n')
       stats = {}
       for line in lines:
           if 'Temperature' in line and 'K' not in line[:15]:
               parts = line.split()
               stats['T_avg'] = float(parts[1])
               stats['T_rmsd'] = float(parts[2])
           elif 'Pressure' in line:
               parts = line.split()
               stats['P_avg'] = float(parts[1])
               stats['P_rmsd'] = float(parts[2])
           elif 'Density' in line:
               parts = line.split()
               stats['rho_avg'] = float(parts[1])
               stats['rho_rmsd'] = float(parts[2])
       
       return stats
   
   def main():
       base = "systems"
       print("Production MD Analysis Summary")
       print("=" * 70)
       
       for mol in ["glycine", "glygly"]:
           for ff in ["amber99sb", "charmm27"]:
               for temp in ["300K", "350K"]:
                   path = os.path.join(base, mol, ff, temp)
                   print(f"\n{mol}/{ff}/{temp}:")
                   
                   stats = analyze_system(path)
                   if stats:
                       target_T = 300 if temp == "300K" else 350
                       print(f"  Temperature: {stats.get('T_avg', 'N/A'):.2f} ± "
                             f"{stats.get('T_rmsd', 'N/A'):.2f} K "
                             f"(target: {target_T} K)")
                       print(f"  Pressure: {stats.get('P_avg', 'N/A'):.2f} ± "
                             f"{stats.get('P_rmsd', 'N/A'):.2f} bar "
                             f"(target: 1.0 bar)")
                       print(f"  Density: {stats.get('rho_avg', 'N/A'):.2f} ± "
                             f"{stats.get('rho_rmsd', 'N/A'):.2f} kg/m³")
   
   if __name__ == "__main__":
       main()
   EOF
   ```

### Validation Criteria

| Property | Criterion | Tolerance |
|----------|-----------|-----------|
| Temperature | Target ± 2 K | 300 K → 298-302 K |
| Pressure | 1.0 bar average | ±100 bar fluctuations normal |
| Density | ~1000 kg/m³ (TIP3P) | ±10 kg/m³ |
| Trajectory length | 20 ns | ≥19.9 ns acceptable |
| Frame interval | 30 fs | Exact |
| No LINCS warnings | 0 | - |

### Deliverables
- Validation report for all 8 systems
- Temperature/pressure/density plots
- Confirmation of trajectory integrity

---

## Substep 2.5: Trajectory Processing for QENS Analysis

### Objective
Prepare trajectories for S(q,ω) calculation by centering, removing PBC artifacts, and creating analysis-ready subsets.

### Implementation Steps

1. **Center Trajectories on Solute Center of Mass**
   ```bash
   # Create index groups for analysis
   echo -e "keep 0\nsplitres 0\nname 1 Solute\nq" | gmx make_ndx -f prod.tpr -o index.ndx
   
   # Center trajectory on system COM
   echo "0 0" | gmx trjconv -f prod.xtc -s prod.tpr -o prod_center.xtc \
       -center -pbc mol -ur compact
   ```

2. **Create Solute-Only Trajectory (Optional)**
   ```bash
   # Extract only solute atoms for faster analysis
   echo "Solute" | gmx trjconv -f prod_center.xtc -s prod.tpr \
       -n index.ndx -o prod_solute.xtc
   ```

3. **Create Time-Windowed Subtrajectories**
   
   For QENS analysis, shorter trajectories with good statistics are often useful:
   ```bash
   # Create 1 ns windows for ensemble averaging
   for t in $(seq 0 1 19); do
       start=$((t * 1000))
       end=$(((t + 1) * 1000))
       gmx trjconv -f prod.xtc -s prod.tpr -b $start -e $end \
           -o prod_window_${t}ns.xtc
   done
   ```

4. **Calculate Hydrogen Positions (Critical for QENS)**
   
   QENS is dominated by incoherent scattering from hydrogen atoms:
   ```bash
   # Create hydrogen-only index
   echo -e "a H*\nq" | gmx make_ndx -f prod.tpr -o hydrogen.ndx
   
   # Extract hydrogen trajectory
   echo "H*" | gmx trjconv -f prod_center.xtc -s prod.tpr \
       -n hydrogen.ndx -o prod_hydrogen.xtc
   ```

5. **Verify Processed Trajectories**
   ```bash
   # Check processed trajectory
   gmx check -f prod_center.xtc
   ```

### Deliverables (per system)
- `prod_center.xtc` - Centered, PBC-corrected trajectory
- `prod_hydrogen.xtc` - Hydrogen-only trajectory for QENS
- `index.ndx` - Index file with analysis groups

---

## Substep 2.6: Storage Management and Backup

### Objective
Manage large trajectory files and ensure data preservation.

### Storage Estimates

| File Type | Size per System | Total (8 systems) |
|-----------|-----------------|-------------------|
| `prod.xtc` (20 ns @ 30 fs) | ~45-55 GB | ~360-440 GB |
| `prod.edr` | ~200 MB | ~1.6 GB |
| `prod.cpt` | ~50 MB | ~400 MB |
| `prod_hydrogen.xtc` | ~2-5 GB | ~16-40 GB |
| **Total** | ~50-60 GB | **~400-480 GB** |

### Implementation Steps

1. **Compress Trajectories (if needed)**
   ```bash
   # Already using compressed format (.xtc)
   # For additional compression, can reduce precision:
   gmx trjconv -f prod.xtc -o prod_lowprec.xtc -ndec 2
   ```

2. **Create Backup of Essential Files**
   ```bash
   # Essential files for reproducibility
   tar -czvf production_essential.tar.gz \
       mdp/prod_*.mdp \
       systems/*/topology.top \
       systems/*/*/production/*.tpr \
       systems/*/*/production/*.cpt \
       systems/*/*/production/*.gro
   ```

3. **Delete Intermediate Files (Optional)**
   ```bash
   # Remove unneeded files after validation
   rm -f systems/*/*/production/*#*  # Backup files
   rm -f systems/*/*/production/*.trr  # Full-precision (if created)
   ```

### Deliverables
- Backup archive of essential files
- Storage usage report
- Data retention policy documented

---

## Step 2 Summary and Checklist

### Expected Outputs

For each of 8 systems:
- `production/prod.xtc` - 20 ns trajectory at 30 fs resolution
- `production/prod.edr` - Energy data
- `production/prod_center.xtc` - Processed trajectory for analysis
- `production/prod_hydrogen.xtc` - Hydrogen trajectory for QENS

### Verification Checklist

**Trajectory Quality:**
- [ ] All 8 simulations completed 20 ns without crashes
- [ ] Frame interval is exactly 30 fs (0.030 ps)
- [ ] No LINCS warnings in log files
- [ ] Temperature stable at target (±2 K average)
- [ ] Pressure stable at 1 bar (±100 bar fluctuations)
- [ ] Density reasonable (~1000 kg/m³)

**File Integrity:**
- [ ] All .xtc files pass `gmx check`
- [ ] Checkpoint files can restart simulation
- [ ] Processed trajectories created successfully

**Storage:**
- [ ] Total storage within budget (~400-480 GB)
- [ ] Essential files backed up
- [ ] Intermediate files cleaned up if needed

### Directory Structure After Step 2

```
SQUIP/
├── mdp/
│   ├── prod_300K.mdp
│   ├── prod_350K.mdp
│   ├── prod_300K_compact.mdp
│   └── prod_350K_compact.mdp
├── systems/
│   ├── glycine/
│   │   ├── amber99sb/
│   │   │   ├── 300K/
│   │   │   │   └── production/
│   │   │   │       ├── prod.tpr
│   │   │   │       ├── prod.xtc      (~50 GB)
│   │   │   │       ├── prod.edr
│   │   │   │       ├── prod.log
│   │   │   │       ├── prod.cpt
│   │   │   │       ├── prod.gro
│   │   │   │       ├── prod_center.xtc
│   │   │   │       ├── prod_hydrogen.xtc
│   │   │   │       └── index.ndx
│   │   │   └── 350K/
│   │   │       └── production/
│   │   │           └── [same structure]
│   │   └── charmm27/
│   │       └── [same structure]
│   └── glygly/
│       └── [same structure as glycine]
└── scripts/
    └── analyze_production.py
```

---

## Simulation Continuation and Restart

### Extending Simulations

If more sampling is needed:
```bash
# Extend by additional 10 ns
gmx convert-tpr -s prod.tpr -extend 10000 -o prod_extend.tpr
gmx mdrun -v -deffnm prod -cpi prod.cpt -noappend
```

### Restart from Crash

```bash
# Resume from checkpoint
gmx mdrun -v -deffnm prod -cpi prod.cpt -append
```

---

## Resource Estimates

### Computational Resources

| Resource | Requirement | Notes |
|----------|-------------|-------|
| CPU cores | 8-16 per simulation | OpenMP parallelization |
| GPU | Optional but recommended | 10-20× speedup |
| RAM | ~4 GB per simulation | For trajectory buffering |
| Storage | ~200-400 GB total | High-frequency output |
| Walltime | ~2-4 days (GPU) | All 8 systems sequential |

### Parallelization Strategy

```
Option 1: Sequential on single node
- Simplest setup
- Total time: ~4-8 days (GPU) or ~4-8 weeks (CPU)

Option 2: Parallel on cluster
- Submit 8 independent jobs
- Total time: ~0.5-1 day (GPU)

Option 3: Hybrid
- Run 2-4 simulations concurrently on multi-GPU node
- Total time: ~1-2 days
```

---

## Next Steps

After completing Step 2:

- **Step 3**: Trajectory Analysis and S(q,ω) Calculation
  - Calculate intermediate scattering functions I(q,t)
  - Compute dynamic structure factor S(q,ω)
  - Compare with experimental QENS data

---

## Notes and Considerations

1. **Trajectory Output Frequency**: The 30 fs output interval is suitable for PoC QENS analysis. Use 10 fs for full-resolution production runs.

2. **Storage Requirements**: Compact output generates ~45-55 GB trajectories per 20 ns simulation. Ensure adequate storage before starting.

3. **Thermostat Choice**: V-rescale with relaxed coupling (τ=0.5 ps) minimizes thermostat artifacts on picosecond dynamics while maintaining proper temperature control.

4. **Hydrogen Trajectories**: For QENS analysis, hydrogen atoms dominate the signal due to their large incoherent scattering cross-section. Pre-extracting hydrogen trajectories speeds up subsequent analysis.

5. **Checkpoint Frequency**: Default checkpoint saves every 15 minutes, allowing restart with minimal lost work.

6. **Ensemble Choice**: NPT matches experimental conditions (constant P, T) and is standard for solution simulations.

---

## References

1. GROMACS Manual - md and mdrun parameters
2. Bellissent-Funel, M.-C. et al. (2016). "Water Determines the Structure and Dynamics of Proteins." Chem. Rev. 116, 7673-7697.
3. Magazù, S. et al. (2011). "Mean Square Displacements from Elastic Incoherent Neutron Scattering Evaluated by Spectrometers Working with Different Energy Resolution." J. Phys. Chem. B 115, 7736-7743.
