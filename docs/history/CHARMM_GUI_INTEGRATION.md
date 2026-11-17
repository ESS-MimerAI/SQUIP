# CHARMM-GUI Integration Guide

## After Downloading CHARMM-GUI Files

### Directory Structure to Create
```
topologies/
├── charmm_gui_files/
│   ├── glycine_charmm/
│   ├── glycine_amber/
│   ├── glygly_charmm/
│   └── glygly_amber/
```

### For Each System

1. **Extract CHARMM-GUI files:**
   ```powershell
   # Extract the downloaded charmm-gui.tgz
   tar -xzf charmm-gui.tgz -C topologies/charmm_gui_files/glycine_charmm/
   ```

2. **Navigate to GROMACS directory:**
   ```powershell
   cd topologies/charmm_gui_files/glycine_charmm/gromacs/
   ```

3. **The files you need:**
   - `step3_input.gro` - Initial solvated structure (replaces your current .gro)
   - `topol.top` - Complete topology (replaces your current .top)
   - `toppar/` directory - Force field parameters (needed for GROMACS)
   - `step4.0_minimization.mdp` - Energy minimization parameters
   - `step4.1_equilibration.mdp` - NVT/NPT equilibration parameters

## Continuing with Step 1.4: Ion Addition

### Option A: Use CHARMM-GUI's Built-in Neutralization
If you specified ion concentration in CHARMM-GUI, the system is already neutralized.
**Check the .gro file for ions:**
```powershell
grep -E "NA|CL|K" step3_input.gro
```

### Option B: Add Ions Using GROMACS (if not done by CHARMM-GUI)

1. **Generate TPR file:**
   ```bash
   gmx grompp -f ../../../mdp/ions.mdp -c step3_input.gro -p topol.top -o ions.tpr
   ```

2. **Add ions:**
   ```bash
   # For neutralization only
   gmx genion -s ions.tpr -o glycine_charmm_ions.gro -p topol.top -neutral

   # For neutralization + concentration
   gmx genion -s ions.tpr -o glycine_charmm_ions.gro -p topol.top -neutral -conc 0.15
   ```

3. **When prompted, select water group** (usually group 13 or "SOL")

## Step 1.5: Energy Minimization

Use CHARMM-GUI's minimization MDP or your own:

```bash
# If using CHARMM-GUI's MDP
gmx grompp -f step4.0_minimization.mdp -c glycine_charmm_ions.gro -p topol.top -o em.tpr

# Run minimization
gmx mdrun -v -deffnm em
```

## Step 1.6: NVT Equilibration

```bash
gmx grompp -f step4.1_equilibration.mdp -c em.gro -p topol.top -o nvt.tpr
gmx mdrun -v -deffnm nvt
```

## Step 1.7: NPT Equilibration

```bash
gmx grompp -f step4.2_equilibration.mdp -c nvt.gro -p topol.top -o npt.tpr
gmx mdrun -v -deffnm npt
```

## Verification Steps

After each step:

1. **Check structure:**
   ```bash
   gmx check -f em.gro  # or nvt.gro, npt.gro
   ```

2. **Check energy:**
   ```bash
   gmx energy -f em.edr -o potential.xvg
   # Select "Potential" when prompted
   ```

3. **Check temperature (NVT):**
   ```bash
   gmx energy -f nvt.edr -o temperature.xvg
   # Select "Temperature"
   ```

4. **Check pressure (NPT):**
   ```bash
   gmx energy -f npt.edr -o pressure.xvg
   # Select "Pressure"
   ```

## Important Notes

### Force Field Files
- Keep the `toppar/` directory from CHARMM-GUI
- Reference it in your topology files
- Don't mix force field parameters from different sources

### Topology Files
- The `.top` file from CHARMM-GUI is complete and ready to use
- It includes all molecular parameters
- No need for `pdb2gmx` - that's already done

### Box Size Verification
CHARMM-GUI might create boxes slightly different from your target 5.5 nm:
```bash
gmx editconf -f step3_input.gro -box 5.5 5.5 5.5 -o step3_input_resized.gro
```

### System Information
Check atom counts and composition:
```bash
gmx check -f step3_input.gro
tail -n 2 step3_input.gro  # Shows total atoms and box vectors
```

## What Makes CHARMM-GUI Different

**vs. Your Current Approach:**
- Your approach: PDB → pdb2gmx → manual topology
- CHARMM-GUI: SDF → parameterization → complete topology

**Key Advantages:**
- ✅ Proper force field parameters for small molecules
- ✅ Correct atom types and charges
- ✅ Zwitterionic forms handled correctly
- ✅ Multiple molecules packed efficiently
- ✅ Ready-to-use MDP files
- ✅ No missing parameters or atom type errors

## Troubleshooting

### If TPR generation still fails:
1. Check for missing force field files in `toppar/`
2. Verify the `#include` statements in `topol.top`
3. Ensure GROMACS can find the force field directory

### If system is not neutralized:
```bash
# Check total charge
gmx grompp -f ions.mdp -c step3_input.gro -p topol.top -o test.tpr 2>&1 | grep "total charge"
```

### If water model mismatch:
- Ensure TIP3P is consistently used
- Check in topology file: `#include "toppar/tip3p.itp"`

## Expected Timeline

- CHARMM-GUI job: 5-15 minutes per system
- Ion addition: 1-2 minutes per system
- Energy minimization: 5-10 minutes per system
- NVT equilibration: 15-30 minutes per system
- NPT equilibration: 15-30 minutes per system

**Total: ~2 hours for all 4 systems**
