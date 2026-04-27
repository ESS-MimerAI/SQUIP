# Step 1: System Preparation - Implementation Plan

## Overview
This document provides a detailed implementation plan for **Step 1: System Preparation** from the SQUIP Proof of Concept workflow. The goal is to build solvated simulation boxes for glycine and glycine dipeptide (Gly-Gly) ready for MD simulations.

**Timeline**: Week 1  
**Target Systems**: Glycine (amino acid) and Gly-Gly (dipeptide)  
**Target Conditions**: 2 temperatures (300 K, 350 K) × 2 force fields

> **Note**: Originally specified CHARMM36m and AMBER ff19SB. These have been substituted with **CHARMM27** and **AMBER99SB-ILDN** which are available in the GROMACS installation and properly support zwitterionic amino acids.

> **Water Models**: CHARMM27 uses **TIP3P** (3-site, native to CHARMM). AMBER99SB-ILDN uses **TIP4P-Ew** (4-site Ewald-optimized) for improved accuracy with PME electrostatics. See [MOVING_TO_TIP4P.md](MOVING_TO_TIP4P.md) for migration details.

---

## Substep 1.1: Obtain and Prepare Initial Molecular Structures

### Objective
Generate starting PDB files for glycine and Gly-Gly in their appropriate protonation states.

### Implementation Steps

1. **Source Initial Structures**
   - Download glycine structure from PDB or PubChem
   - Build Gly-Gly dipeptide structure using molecular editor or builder tools
   - Alternative: Use GROMACS `pdb2gmx` or AmberTools `tleap` to build from sequence

2. **Determine Protonation States**
   - pH: Assume physiological pH ~7 (or neutral aqueous solution)
   - Glycine: Zwitterionic form (NH3+, COO-)
   - Gly-Gly: N-terminus protonated (NH3+), C-terminus deprotonated (COO-)

3. **Validate Geometry**
   - Check bond lengths and angles are chemically reasonable
   - Ensure no steric clashes or unrealistic geometries
   - Save as clean PDB files: `glycine.pdb`, `gly-gly.pdb`

### Tools
- PyMOL, Avogadro, or ChimeraX for visualization and basic editing
- GROMACS `pdb2gmx` or AmberTools for building from scratch
- RDKit or OpenBabel for structure conversion if needed

### Deliverables
- `glycine.pdb` - Initial glycine structure
- `gly-gly.pdb` - Initial Gly-Gly dipeptide structure
- Documentation of protonation states chosen

---

## Substep 1.2: Generate Topology Files for Both Force Fields

### Objective
Create GROMACS topology files (.top) for each molecule using CHARMM36m and AMBER ff19SB force fields.

### Implementation Steps

1. **CHARMM27 Topologies** (substitute for CHARMM36m)
   ```bash
   # For glycine - select "0" for GLY-NH3+ (N-term) and "0" for COO- (C-term)
   echo "0
   0" | gmx pdb2gmx -f structures/glycine_zw_charmm.pdb -o topologies/glycine_charmm27.gro \
        -p topologies/glycine_charmm27.top -ff charmm27 -water tip3p -ter
   
   # For Gly-Gly
   echo "0
   0" | gmx pdb2gmx -f structures/glygly_zw_charmm.pdb -o topologies/glygly_charmm27.gro \
        -p topologies/glygly_charmm27.top -ff charmm27 -water tip3p -ter
   ```

2. **AMBER99SB-ILDN Topologies** (substitute for ff19SB)
   ```bash
   # For glycine - uses custom ZGLY residue in local amber99sb-ildn.ff/
   # TIP4P-Ew selected interactively (option 3) via -water select
   echo "3" | gmx pdb2gmx -f structures/glycine_zw_amber.pdb -o topologies/glycine_amber99sb.gro \
        -p topologies/glycine_amber99sb.top -ff amber99sb-ildn -water select
   
   # For Gly-Gly - works natively (NGLY for first residue, CGLY for last)
   echo "3" | gmx pdb2gmx -f structures/glygly_zw_charmm.pdb -o topologies/glygly_amber99sb.gro \
        -p topologies/glygly_amber99sb.top -ff amber99sb-ildn -water select
   ```

3. **Force Field Configuration**
   - **CHARMM27**: Native zwitterion support via `-ter` flag (select GLY-NH3+ and COO-)
   - **AMBER99SB-ILDN**: Custom ZGLY residue created for single amino acids
   - Local force field copy at `amber99sb-ildn.ff/` with ZGLY additions
   - All topologies verified with total charge = 0.000 e

### Tools
- GROMACS `pdb2gmx`
- AmberTools (tleap, ParmEd) if needed for ff19SB
- CHARMM-GUI as alternative for CHARMM36m setup

### Deliverables
- `topologies/glycine_charmm27.top`, `topologies/glycine_charmm27.gro` ✅
- `topologies/glycine_amber99sb.top`, `topologies/glycine_amber99sb.gro` ✅
- `topologies/glygly_charmm27.top`, `topologies/glygly_charmm27.gro` ✅
- `topologies/glygly_amber99sb.top`, `topologies/glygly_amber99sb.gro` ✅

---

## Substep 1.3: Build Solvated Boxes with ~50 Molecules

### Objective
Create simulation boxes containing ~50 solute molecules (glycine or Gly-Gly) to achieve ~1 M concentration, solvated with TIP3P water.

### Implementation Steps

1. **Calculate Box Dimensions**
   - Target: 1 M aqueous solution (~50 molecules)
   - Estimate box size for 15,000-20,000 total atoms
   - Typical box size: ~5-6 nm cubic box for this system size

2. **Insert Multiple Molecules**
   ```bash
   # Use gmx insert-molecules to add 50 solute molecules
   gmx insert-molecules -ci glycine_charmm.gro -nmol 50 -box 6 6 6 -o glycine_50mol.gro
   ```

3. **Solvate with Water**
   ```bash
   # Add water molecules to fill the box
   # For CHARMM27 (TIP3P): use spc216.gro
   gmx solvate -cp glycine_50mol.gro -cs spc216.gro -o glycine_solvated.gro -p glycine_charmm.top
   
   # For AMBER99SB-ILDN (TIP4P-Ew): use tip4p.gro from GROMACS share
   gmx solvate -cp glycine_50mol.gro -cs $GMXDATA/top/tip4p.gro -o glycine_solvated.gro -p glycine_amber.top
   ```

4. **Verify System Size**
   - Check total atom count is in 15,000-20,000 range
   - Adjust box size if needed to meet target
   - Document actual concentration achieved

5. **Repeat for All Combinations**
   - Glycine + CHARMM36m
   - Glycine + AMBER ff19SB
   - Gly-Gly + CHARMM36m
   - Gly-Gly + AMBER ff19SB

### Tools
- GROMACS `insert-molecules`
- GROMACS `solvate`
- GROMACS `editconf` for box adjustments

### Deliverables
- Solvated structure files (.gro) for all 4 combinations
- Updated topology files (.top) with correct water molecule counts
- System statistics: box dimensions, atom counts, actual concentrations

---

## Substep 1.4: Add Counter-ions and Neutralize Systems

### Objective
Add Na+ and Cl- ions to neutralize the system charge and achieve electroneutrality.

### Implementation Steps

1. **Create Ion Addition MDP File**
   ```mdp
   ; ions.mdp - minimal parameters for ion addition
   integrator  = steep
   nsteps      = 0
   ```

2. **Generate TPR File for Ion Addition**
   ```bash
   gmx grompp -f ions.mdp -c glycine_solvated.gro -p glycine_charmm.top -o ions.tpr
   ```

3. **Add Counter-ions**
   ```bash
   # Add ions to neutralize (replace SOL molecules)
   gmx genion -s ions.tpr -o glycine_neutral.gro -p glycine_charmm.top -pname NA -nname CL -neutral
   ```

4. **Verify Neutrality**
   - Check topology file for ion counts
   - Confirm total charge = 0
   - Document ion numbers added

5. **Repeat for All Systems**
   - All 4 molecule/force-field combinations

### Tools
- GROMACS `grompp`
- GROMACS `genion`

### Deliverables
- Neutralized structure files (.gro) for all 4 combinations
- Final topology files with ion counts
- Charge verification report

---

## Substep 1.5: Energy Minimization

### Objective
Remove steric clashes and relax the initial structure to a local energy minimum.

### Implementation Steps

1. **Create Energy Minimization MDP File**
   ```mdp
   ; em.mdp - steepest descent minimization
   integrator  = steep
   nsteps      = 50000
   emtol       = 1000.0  ; kJ/mol/nm
   emstep      = 0.01    ; nm
   
   cutoff-scheme = Verlet
   nstlist       = 10
   ns_type       = grid
   rlist         = 1.2
   
   coulombtype   = PME
   rcoulomb      = 1.2
   
   vdwtype       = Cut-off
   rvdw          = 1.2
   
   pbc           = xyz
   ```

2. **Run Energy Minimization**
   ```bash
   # Generate TPR file
   gmx grompp -f em.mdp -c glycine_neutral.gro -p glycine_charmm.top -o em.tpr
   
   # Run minimization
   gmx mdrun -v -deffnm em
   ```

3. **Verify Convergence**
   - Check that maximum force < 1000 kJ/mol/nm
   - Plot energy vs. step to confirm convergence
   - Inspect `em.log` for any warnings

4. **Repeat for All Systems**
   - All 4 molecule/force-field combinations at this stage

### Tools
- GROMACS `grompp`, `mdrun`
- Analysis: `gmx energy` for potential energy plotting

### Deliverables
- `em.gro` - minimized structure for each system
- `em.edr` - energy file
- Energy convergence plots
- Verification that all systems converged successfully

---

## Substep 1.6: NVT Equilibration (Temperature Equilibration)

### Objective
Equilibrate the system at target temperature (300 K or 350 K) while keeping volume constant.

### Implementation Steps

1. **Create NVT Equilibration MDP File**
   ```mdp
   ; nvt.mdp - NVT equilibration
   integrator  = md
   dt          = 0.002    ; 2 fs
   nsteps      = 50000    ; 100 ps
   
   tcoupl      = V-rescale
   tc-grps     = Protein Non-Protein  ; or System
   tau_t       = 0.1 0.1
   ref_t       = 300 300  ; or 350 350 for high-T runs
   
   pcoupl      = no
   
   gen_vel     = yes
   gen_temp    = 300  ; or 350
   gen_seed    = -1
   
   cutoff-scheme = Verlet
   nstlist       = 10
   rlist         = 1.2
   
   coulombtype   = PME
   rcoulomb      = 1.2
   
   vdwtype       = Cut-off
   rvdw          = 1.2
   
   pbc           = xyz
   
   constraints   = h-bonds
   constraint_algorithm = LINCS
   ```

2. **Run NVT Equilibration for Both Temperatures**
   ```bash
   # For 300 K
   gmx grompp -f nvt_300K.mdp -c em.gro -p glycine_charmm.top -o nvt_300K.tpr
   gmx mdrun -v -deffnm nvt_300K
   
   # For 350 K
   gmx grompp -f nvt_350K.mdp -c em.gro -p glycine_charmm.top -o nvt_350K.tpr
   gmx mdrun -v -deffnm nvt_350K
   ```

3. **Verify Temperature Equilibration**
   ```bash
   # Extract and plot temperature
   gmx energy -f nvt_300K.edr -o temperature_300K.xvg
   # Select temperature from the menu
   ```
   - Temperature should stabilize around target value
   - Check for reasonable fluctuations (±5-10 K)

4. **Repeat for All Systems**
   - Now expanding to 8 systems: 2 molecules × 2 force fields × 2 temperatures

### Tools
- GROMACS `grompp`, `mdrun`, `energy`
- Plotting tools (xmgrace, Python matplotlib)

### Deliverables
- `nvt_300K.gro` and `nvt_350K.gro` for each molecule/force-field combination
- Temperature equilibration plots
- Verification report for all 8 systems

---

## Substep 1.7: NPT Equilibration (Pressure and Density Equilibration)

### Objective
Equilibrate the system at target pressure (1 bar) to achieve proper density before production runs.

### Implementation Steps

1. **Create NPT Equilibration MDP File**
   ```mdp
   ; npt.mdp - NPT equilibration
   integrator  = md
   dt          = 0.002    ; 2 fs
   nsteps      = 50000    ; 100 ps
   
   tcoupl      = V-rescale
   tc-grps     = Protein Non-Protein
   tau_t       = 0.1 0.1
   ref_t       = 300 300  ; or 350 350
   
   pcoupl      = Parrinello-Rahman
   pcoupltype  = isotropic
   tau_p       = 2.0
   ref_p       = 1.0
   compressibility = 4.5e-5
   
   gen_vel     = no  ; Continue from NVT
   
   cutoff-scheme = Verlet
   nstlist       = 10
   rlist         = 1.2
   
   coulombtype   = PME
   rcoulomb      = 1.2
   
   vdwtype       = Cut-off
   rvdw          = 1.2
   
   pbc           = xyz
   
   constraints   = h-bonds
   constraint_algorithm = LINCS
   ```

2a. **Run NPT Equilibration**
   ```bash
   # For 300 K system
   gmx grompp -f npt_300K.mdp -c nvt_300K.gro -p glycine_charmm.top -t nvt_300K.cpt -o npt_300K.tpr
   gmx mdrun -v -deffnm npt_300K
   ```
2b. **Run NVE Equilibration** (Optional - for dynamics validation, see [NVE_EQUILIBRATION.md](NVE_EQUILIBRATION.md))
   ```bash
   # For 300 K system - short NVE test after NVT to verify energy conservation
   gmx grompp -f nve_300K.mdp -c nvt_300K.gro -p glycine_charmm.top -t nvt_300K.cpt -o nve_300K.tpr
   gmx mdrun -v -deffnm nve_300K
   
   # Verify energy conservation (Total-Energy drift should be < 1 kJ/mol over 10 ps)
   echo "12 0" | gmx energy -f nve_300K.edr -o nve_300K_energy.xvg
   ```

3. **Verify Pressure and Density and volume Equilibration**
   ```bash
   # Extract pressure
   gmx energy -f npt_300K.edr -o pressure_300K.xvg
   
   # Extract density
   gmx energy -f npt_300K.edr -o density_300K.xvg
   ```
   - Pressure should fluctuate around 1 bar (±100 bar fluctuations normal)
   - Density should stabilize (typical aqueous: ~1000 kg/m³)

4. **Repeat for All 8 Systems**
   - 2 molecules × 2 force fields × 2 temperatures

### Tools
- GROMACS `grompp`, `mdrun`, `energy`
- Plotting tools

### Deliverables
- `npt_300K.gro` and `npt_350K.gro` for each molecule/force-field combination (8 total)
- Pressure equilibration plots
- Density equilibration plots
- Final equilibrated structures ready for production MD

---

## Step 1 Summary and Checklist

### Expected Outputs (8 Fully Prepared Systems)

1. **Glycine + CHARMM27** at 300 K and 350 K
2. **Glycine + AMBER99SB-ILDN** at 300 K and 350 K
3. **Gly-Gly + CHARMM27** at 300 K and 350 K
4. **Gly-Gly + AMBER99SB-ILDN** at 300 K and 350 K

### Files per System
- Equilibrated structure: `npt_[temp]K.gro`
- Checkpoint file: `npt_[temp]K.cpt`
- Topology: `system.top`
- All MDP files used
- Equilibration analysis plots (temperature, pressure, density)

### Verification Checklist

**CHARMM27 Systems (TIP3P):**
- [ ] All CHARMM systems contain ~50 solute molecules
- [ ] CHARMM system sizes are 15,000-16,500 atoms each
- [ ] CHARMM systems are electrically neutral
- [ ] CHARMM energy minimization converged
- [ ] CHARMM temperature equilibration successful
- [ ] CHARMM pressure equilibration successful
- [ ] CHARMM density stabilized

**AMBER99SB-ILDN Systems (TIP4P-Ew):**
- [x] All AMBER systems contain 50 solute molecules
- [x] AMBER system sizes are ~20,500-21,000 atoms each (4-site TIP4P-Ew water)
- [x] AMBER systems are electrically neutral (zwitterions, no ions needed)
- [x] AMBER energy minimization converged (Fmax < 1000 kJ/mol/nm)
- [x] AMBER temperature equilibration successful (T within ±0.5 K of target)
- [x] AMBER pressure equilibration successful (P within ±12 bar of 1 bar target)
- [x] AMBER density stabilized to reasonable values

**General:**
- [x] No errors in GROMACS log files
- [x] Documentation complete for all parameter choices

**AMBER Step 1 Complete (TIP4P-Ew migration)** - AMBER systems ready for Step 2: Production MD
**CHARMM Step 1 Pending** - Awaiting verification after TIP4P-Ew migration

### Directory Structure Recommendation
```
SQUIP/
├── systems/
│   ├── glycine/
│   │   ├── charmm36m/
│   │   │   ├── 300K/
│   │   │   │   ├── initial/
│   │   │   │   ├── minimization/
│   │   │   │   ├── nvt/
│   │   │   │   └── npt/
│   │   │   └── 350K/
│   │   │       └── [same structure]
│   │   └── amber_ff19sb/
│   │       └── [same structure]
│   └── gly-gly/
│       └── [same structure as glycine]
└── scripts/
    ├── build_system.sh
    ├── run_minimization.sh
    ├── run_nvt.sh
    ├── run_npt.sh
    └── verify_equilibration.py
```

### Estimated Time and Resources
- **Walltime**: Each equilibration ~1-2 hours on modern hardware
- **Total for Step 1**: ~16-24 hours for all 8 systems (can be parallelized)
- **Storage**: ~5-10 GB for all equilibration trajectories and files
- **Compute**: Can run on local workstation or small cluster allocation

---

## Next Steps

Once all 8 systems are equilibrated and verified, proceed to:
- **Step 2**: Production MD simulations (10-20 ns with 10 fs sampling)

## Notes and Considerations

1. **Force Field Configuration**: CHARMM27 and AMBER99SB-ILDN are used (available in GROMACS). For AMBER, a local copy with custom ZGLY residue is required for single amino acids.

2. **Parallelization**: Systems can be prepared in parallel since they are independent.

3. **Checkpoint Files**: Keep checkpoint files (.cpt) from each equilibration stage for reproducibility and continuation.

4. **Quality Control**: Implement automated checks for equilibration quality before moving to production runs.

5. **Documentation**: Keep detailed notes on any issues encountered and solutions applied for reproducibility.

6. **Trajectory Retention**: Decide whether to keep full equilibration trajectories or just final structures/checkpoints (storage consideration).
