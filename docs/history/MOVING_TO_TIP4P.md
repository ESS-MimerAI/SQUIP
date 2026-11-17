# Migration Plan: AMBER99SB + TIP3P → AMBER99SB + TIP4P-Ew

## Overview

This document describes the comprehensive plan for converting the AMBER99SB-ILDN systems from TIP3P water model to TIP4P-Ew while keeping CHARMM27 systems with TIP3P unchanged.

**Date Created:** 2026-01-30  
**Status:** Complete - All AMBER systems migrated to TIP4P-Ew

---

## Background

### Why TIP4P-Ew?

TIP4P-Ew (TIP4P-Ewald) is a 4-site water model optimized for use with Ewald summation methods (PME). It provides:
- Better reproduction of liquid-water thermodynamic properties
- Improved temperature-dependent density behavior
- More accurate water structure around solutes
- Designed specifically for long-range electrostatics (PME)

### Key Differences: TIP3P vs TIP4P-Ew

| Property | TIP3P | TIP4P-Ew |
|----------|-------|----------|
| Atoms per molecule | 3 (O, H, H) | 4 (O, H, H, MW) |
| Charge distribution | On O and H atoms | Virtual site (MW) + H atoms |
| O-H distance | 0.09572 nm | 0.09572 nm |
| H-O-H angle | 104.52° | 104.52° |
| Charge on H | +0.417 e | +0.52422 e |
| Charge on O | -0.834 e | 0.0 e |
| Charge on MW | N/A | -1.04844 e |
| Virtual site | No | Yes (0.0125 nm from O) |
| Atom types | OW, HW | OW_tip4pew, HW_tip4pew, MW |

### Implications for System Size

- Each water molecule now has 4 atoms instead of 3
- For ~5,000 water molecules: +5,000 atoms (from ~15,000 to ~20,000 total)
- Box dimensions may need adjustment to stay within target range

---

## Scope

### IN SCOPE (AMBER99SB-ILDN only)
- Glycine + AMBER99SB-ILDN at 300 K and 350 K
- Gly-Gly + AMBER99SB-ILDN at 300 K and 350 K

### OUT OF SCOPE (Keep as-is with TIP3P)
- Glycine + CHARMM27 at 300 K and 350 K
- Gly-Gly + CHARMM27 at 300 K and 350 K

---

## Phase 1: Backup Existing Data

### 1.1 Create Backup Directory Structure

```bash
mkdir -p backup/tip3p_amber/topologies
mkdir -p backup/tip3p_amber/npt
mkdir -p backup/tip3p_amber/nvt
```

### 1.2 Files to Backup

#### Topology Files (backup/tip3p_amber/topologies/)
- `topologies/glycine_amber.gro`
- `topologies/glycine_amber.top`
- `topologies/glycine_amber99sb.gro`
- `topologies/glycine_amber99sb.top`
- `topologies/glycine_amber_50mol.gro`
- `topologies/glycine_amber_solvated.gro`
- `topologies/glygly_amber.gro`
- `topologies/glygly_amber.top`
- `topologies/glygly_amber99sb.gro`
- `topologies/glygly_amber99sb.top`
- `topologies/glygly_amber_50mol.gro`
- `topologies/glygly_amber_solvated.gro`

#### NVT Equilibration Files (backup/tip3p_amber/nvt/)
- `nvt/glycine_amber_300K_nvt.gro`
- `nvt/glycine_amber_300K_nvt.cpt`
- `nvt/glycine_amber_350K_nvt.gro`
- `nvt/glycine_amber_350K_nvt.cpt`
- `nvt/glygly_amber_300K_nvt.gro`
- `nvt/glygly_amber_300K_nvt.cpt`
- `nvt/glygly_amber_350K_nvt.gro`
- `nvt/glygly_amber_350K_nvt.cpt`

#### NPT Equilibration Files (backup/tip3p_amber/npt/)
- `npt/glycine_amber_300K_npt.gro`
- `npt/glycine_amber_300K_npt.cpt`
- `npt/glycine_amber_300K_npt_prev.cpt`
- `npt/glycine_amber_350K_npt.gro`
- `npt/glycine_amber_350K_npt.cpt`
- `npt/glygly_amber_300K_npt.gro`
- `npt/glygly_amber_300K_npt.cpt`
- `npt/glygly_amber_350K_npt.gro`
- `npt/glygly_amber_350K_npt.cpt`

### 1.3 Backup Commands

```powershell
# Create backup directories
New-Item -ItemType Directory -Path "backup\tip3p_amber\topologies" -Force
New-Item -ItemType Directory -Path "backup\tip3p_amber\npt" -Force
New-Item -ItemType Directory -Path "backup\tip3p_amber\nvt" -Force

# Backup topologies (AMBER files only)
Copy-Item "topologies\glycine_amber*" "backup\tip3p_amber\topologies\"
Copy-Item "topologies\glygly_amber*" "backup\tip3p_amber\topologies\"

# Backup NVT files
Copy-Item "nvt\*amber*" "backup\tip3p_amber\nvt\"

# Backup NPT files  
Copy-Item "npt\*amber*" "backup\tip3p_amber\npt\"
```

---

## Phase 2: Update Force Field Configuration

### 2.1 Verify TIP4P-Ew Support in Force Field

The `amber99sb-ildn.ff/` directory already contains:
- ✅ `tip4pew.itp` - TIP4P-Ew water topology
- ✅ `watermodels.dat` - Lists tip4pew as available
- ✅ `ffnonbonded.itp` - Contains OW_tip4pew, HW_tip4pew atom types
- ✅ `atomtypes.atp` - Contains tip4pew atom types and MW virtual site

**No changes needed to force field files.**

---

## Phase 3: Modify Python Scripts

### 3.1 Update `regenerate_topologies.py`

**Current (line 38-41):**
```python
'-ff', ff_name,
'-water', 'tip3p',
'-ignh'
```

**Change to:**
```python
'-ff', ff_name,
'-water', 'tip4pew' if 'amber' in ff_name else 'tip3p',
'-ignh'
```

### 3.2 Update `calculate_box_dimensions.py`

**Current (lines 50-51):**
```python
# Total atoms
atoms_per_water = 3  # H2O
```

**Change to conditional logic:**
```python
# Total atoms - TIP3P has 3 atoms, TIP4P-Ew has 4 atoms (includes virtual site)
# Use water_model parameter to determine atom count
def estimate_total_atoms(n_solute, atoms_per_solute, box_side_nm, water_model='tip3p'):
    ...
    atoms_per_water = 4 if water_model == 'tip4pew' else 3
```

Add separate calculations for:
- CHARMM27 systems: TIP3P (3 atoms/water)
- AMBER systems: TIP4P-Ew (4 atoms/water)

### 3.3 Update `verify_systems.py`

**Current (line 78):**
```python
water_atoms = n_water * 3
```

**Change to detect water model from topology:**
```python
# Detect water model from topology file
water_model = detect_water_model(top_file)
atoms_per_water = 4 if 'tip4p' in water_model else 3
water_atoms = n_water * atoms_per_water
```

Add function to detect water model from topology include statement.

---

## Phase 4: Regenerate AMBER Topologies

### 4.1 Single Molecule Topologies

```bash
# Glycine with AMBER99SB-ILDN + TIP4P-Ew
gmx pdb2gmx -f structures/glycine_zw_amber.pdb \
    -o topologies/glycine_amber99sb.gro \
    -p topologies/glycine_amber99sb.top \
    -ff amber99sb-ildn -water tip4pew

# Gly-Gly with AMBER99SB-ILDN + TIP4P-Ew  
gmx pdb2gmx -f structures/glygly_zw_charmm.pdb \
    -o topologies/glygly_amber99sb.gro \
    -p topologies/glygly_amber99sb.top \
    -ff amber99sb-ildn -water tip4pew
```

### 4.2 Multi-Molecule Systems (50 molecules)

```bash
# Insert 50 glycine molecules
gmx insert-molecules -ci topologies/glycine_amber99sb.gro \
    -nmol 50 -box 5.5 5.5 5.5 \
    -o topologies/glycine_amber_50mol.gro

# Solvate with TIP4P-Ew (use tip4p.gro as coordinate source)
gmx solvate -cp topologies/glycine_amber_50mol.gro \
    -cs tip4p.gro \
    -o topologies/glycine_amber_solvated.gro \
    -p topologies/glycine_amber99sb.top
```

Repeat for Gly-Gly system.

### 4.3 Expected Topology Changes

**Before (TIP3P):**
```
; Include water topology
#include "./amber99sb-ildn.ff/tip3p.itp"
```

**After (TIP4P-Ew):**
```
; Include water topology
#include "./amber99sb-ildn.ff/tip4pew.itp"
```

---

## Phase 5: Recalculate Box Dimensions

### 5.1 System Size Impact Analysis

With TIP4P-Ew (4 atoms per water) vs TIP3P (3 atoms per water):

| System | TIP3P Atoms | TIP4P-Ew Atoms | Status |
|--------|-------------|----------------|--------|
| Glycine (5.5 nm box) | ~15,800 | ~20,900 | Exceeds target |
| Gly-Gly (5.5 nm box) | ~15,800 | ~20,800 | Exceeds target |

### 5.2 Adjusted Box Size Recommendation

To maintain ~15,000-20,000 atoms with TIP4P-Ew:
- Consider reducing box size to ~5.0-5.2 nm
- Or accept slightly larger systems (~21,000 atoms)

**Recommendation:** Accept larger systems (~21,000 atoms) to maintain same concentration as CHARMM systems for valid comparison.

### 5.3 Update `BOX_ANALYSIS.md`

Add section for TIP4P-Ew calculations:

```markdown
## TIP4P-Ew Water Model (AMBER Systems)

### Important Note
TIP4P-Ew is a 4-site water model. Each water molecule contains:
- 1 oxygen (O)
- 2 hydrogens (H)  
- 1 virtual charge site (MW)

This results in 4 atoms per water molecule vs 3 for TIP3P.

### Glycine System (AMBER99SB + TIP4P-Ew)

| Box Size (nm) | Water Molecules | Total Atoms (4-site) | Concentration (M) |
|---------------|-----------------|----------------------|-------------------|
| 5.0 | 4,075 | 16,800 | 0.664 |
| 5.5 | 5,456 | 22,324 | 0.499 |

**Recommended:** 5.5 nm box for concentration consistency with CHARMM systems.
```

---

## Phase 6: Re-run Equilibration

### 6.1 MDP File Considerations

No changes needed to MDP files. TIP4P-Ew is compatible with:
- ✅ LINCS constraints (via SETTLE for water)
- ✅ PME electrostatics
- ✅ Verlet cutoff scheme
- ✅ V-rescale thermostat
- ✅ Parrinello-Rahman barostat

### 6.2 Equilibration Workflow

For each AMBER system (glycine_amber, glygly_amber) at each temperature (300K, 350K):

```bash
# 1. Energy Minimization
gmx grompp -f em.mdp -c glycine_amber_solvated.gro -p glycine_amber.top -o em.tpr
gmx mdrun -v -deffnm em

# 2. NVT Equilibration (100 ps)
gmx grompp -f mdp/nvt_300K.mdp -c em.gro -p glycine_amber.top -o nvt.tpr
gmx mdrun -v -deffnm nvt

# 3. NPT Equilibration (100 ps)  
gmx grompp -f mdp/npt_300K.mdp -c nvt.gro -t nvt.cpt -p glycine_amber.top -o npt.tpr
gmx mdrun -v -deffnm npt
```

### 6.3 Place Final Equilibrated Files

```bash
# Copy final structures to organized directories
cp glycine_amber_npt.gro npt/glycine_amber_300K_npt.gro
cp glycine_amber_npt.cpt npt/glycine_amber_300K_npt.cpt
# etc.
```

---

## Phase 7: Update Documentation

### 7.1 Files to Update

| File | Changes Required |
|------|------------------|
| `STEP1.md` | Update water model references, reset CHARMM status checkmarks |
| `BOX_ANALYSIS.md` | Add TIP4P-Ew section with 4-atom water calculations |
| `SYSTEM_VERIFICATION.md` | Update atom counts for AMBER systems |

### 7.2 STEP1.md Changes

1. **Substep 1.2**: Update AMBER command examples to use `-water tip4pew`
2. **Substep 1.3**: Note different water models for CHARMM vs AMBER
3. **Update Force Field Table**:
   ```markdown
   | Feature | CHARMM27 | AMBER99SB-ILDN |
   |---------|----------|----------------|
   | Water model | TIP3P | TIP4P-Ew |
   | Atoms per water | 3 | 4 |
   ```
4. **Reset CHARMM verification checkmarks** to indicate need for re-verification with new comparison

### 7.3 SYSTEM_VERIFICATION.md Expected Changes

Update verification criteria:
```markdown
- Water model: **TIP3P (CHARMM) / TIP4P-Ew (AMBER)**
- Target system size: **15,000 - 22,000 total atoms** (adjusted for TIP4P-Ew)
```

---

## Phase 8: Verification and Testing

### 8.1 Topology Verification

```bash
# Check water include in topology
grep -n "tip4pew\|tip3p" topologies/*.top

# Expected output:
# glycine_amber.top:XX:#include "./amber99sb-ildn.ff/tip4pew.itp"
# glycine_charmm.top:XX:#include "charmm27.ff/tip3p.itp"
```

### 8.2 System Charge Verification

```bash
# Verify all systems remain neutral
for top in topologies/*.top; do
    echo "=== $top ==="
    grep "qtot" $top | tail -1
done
```

### 8.3 Run verify_systems.py

After regeneration, run updated verification script:
```bash
python verify_systems.py
```

Expected changes in output:
- AMBER systems show 4 atoms per water
- AMBER systems have ~21,000-22,000 total atoms
- CHARMM systems unchanged (~15,800 atoms)

---

## Implementation Checklist

### Phase 1: Backup ✅
- [x] Create backup directory structure
- [x] Backup AMBER topology files (12 files)
- [x] Backup AMBER NVT equilibration files (8 files)
- [x] Backup AMBER NPT equilibration files (9 files)
- [x] Verify backup completeness (29 total files)

### Phase 2: Force Field ✅
- [x] Verify TIP4P-Ew files exist in `amber99sb-ildn.ff/`
- [x] No modifications needed (confirmed)

### Phase 3: Update Scripts ✅
- [x] Update `regenerate_topologies.py` with conditional water model
- [x] Update `calculate_box_dimensions.py` for 4-site water
- [x] Update `verify_systems.py` for water model detection

### Phase 4: Regenerate Topologies ✅
- [x] Regenerate glycine AMBER topology with TIP4P-Ew
- [x] Regenerate glygly AMBER topology with TIP4P-Ew
- [x] Insert 50 molecules for glycine AMBER (500 atoms)
- [x] Insert 50 molecules for glygly AMBER (850 atoms)
- [x] Solvate glycine AMBER with TIP4P-Ew (5005 water molecules, 15515 total atoms)
- [x] Solvate glygly AMBER with TIP4P-Ew (4977 water molecules, 15781 total atoms)

### Phase 5: Box Analysis ✅
- [x] Run updated box dimension calculations
- [x] Update `BOX_ANALYSIS.md` with TIP4P-Ew section
- [x] Decide on final box size: **5.5 nm** (concentration consistency with CHARMM)
- [x] Actual system sizes:
  - Glycine AMBER: 5005 water, 20520 total atoms (with MW)
  - Gly-Gly AMBER: 4977 water, 20758 total atoms (with MW)

### Phase 6: Equilibration 🔄
- [x] Energy minimization for glycine AMBER (converged in 339 steps, Fmax=932)
- [x] Energy minimization for glygly AMBER (converged in 270 steps, Fmax=990)
- [x] NVT equilibration for all AMBER systems
- [x] NPT equilibration for all AMBER systems
- [x] Copy equilibrated files to `npt/` and `nvt/` directories

### Phase 7: Documentation ✅
- [x] Update `STEP1.md` with TIP4P-Ew commands
- [x] Update `STEP1.md` verification checklist for new atom counts
- [x] Reset CHARMM status checkmarks in `STEP1.md`
- [x] Update `BOX_ANALYSIS.md`
- [x] Update `SYSTEM_VERIFICATION.md`

### Phase 8: Verification ✅
- [x] Run `python verify_systems.py`
- [x] Verify water model includes in all topologies
- [x] Confirm system neutrality
- [x] Final documentation review

---

## Rollback Plan

If issues arise, restore from backup:

```powershell
# Restore topologies
Copy-Item "backup\tip3p_amber\topologies\*" "topologies\" -Force

# Restore NVT files
Copy-Item "backup\tip3p_amber\nvt\*" "nvt\" -Force

# Restore NPT files
Copy-Item "backup\tip3p_amber\npt\*" "npt\" -Force

# Revert script changes via git
git checkout -- regenerate_topologies.py
git checkout -- calculate_box_dimensions.py
git checkout -- verify_systems.py
```

---

## Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Backup | 5 min | None |
| Phase 2: Force Field Check | 5 min | None |
| Phase 3: Update Scripts | 30 min | None |
| Phase 4: Regenerate Topologies | 30 min | Phase 3 |
| Phase 5: Box Analysis | 15 min | Phase 4 |
| Phase 6: Equilibration | 4-8 hours | Phase 4, 5 |
| Phase 7: Documentation | 30 min | Phase 6 |
| Phase 8: Verification | 15 min | Phase 6, 7 |

**Total estimated time:** 6-10 hours (mostly equilibration)

---

## Technical Notes

### TIP4P-Ew Virtual Site

The MW (virtual mass site) in TIP4P-Ew:
- Has zero mass
- Carries the negative charge (-1.04844 e)
- Position computed from O and H positions
- Distance from O: 0.0125 nm along H-O-H bisector

### GROMACS Water Coordinate Files

When using `gmx solvate`, use appropriate coordinate file:
- TIP3P: `spc216.gro` (standard 3-site water box)
- TIP4P-Ew: `tip4p.gro` (if available) or GROMACS adds virtual sites automatically

### PME Considerations

TIP4P-Ew was specifically parameterized for Ewald summation:
- Ensure `coulombtype = PME` in MDP files (already set)
- PME is essential for proper TIP4P-Ew behavior

---

## References

1. Horn, H. W., et al. (2004). Development of an improved four-site water model for biomolecular simulations: TIP4P-Ew. *J. Chem. Phys.* 120, 9665-9678.
2. GROMACS Manual - Water Models
3. `amber99sb-ildn.ff/watermodels.dat` - Local force field configuration
