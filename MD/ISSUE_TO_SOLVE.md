# Issue: Proper pdb2gmx Usage for Single Amino Acid Parameterization

## Resolution: Using Available Force Fields

The original issue was that CHARMM36m and AMBER ff19SB force fields were not available in the GROMACS installation. This has been **resolved** by using the available force fields:

| Requested Force Field | Available Substitute | Status |
|----------------------|---------------------|--------|
| CHARMM36m | **CHARMM27** | ✅ Works natively |
| AMBER ff19SB | **AMBER99SB-ILDN** | ✅ Works (with custom ZGLY residue) |

### Working Solutions

#### 1. CHARMM27 (Direct Support for Zwitterions)

CHARMM27 natively supports zwitterionic amino acids through terminal patches:
- **N-terminus**: GLY-NH3+ (protonated amine)
- **C-terminus**: COO- (deprotonated carboxylate)

**Usage:**
```bash
# Generate glycine topology (select "0" for both terminal options: GLY-NH3+ and COO-)
echo "0
0" | gmx pdb2gmx -f structures/glycine_zw_charmm.pdb -o topologies/glycine_charmm27.gro -p topologies/glycine_charmm27.top -ff charmm27 -water tip3p -ter

# Generate Gly-Gly topology
echo "0
0" | gmx pdb2gmx -f structures/glygly_zw_charmm.pdb -o topologies/glygly_charmm27.gro -p topologies/glygly_charmm27.top -ff charmm27 -water tip3p -ter
```

#### 2. AMBER99SB-ILDN (Custom ZGLY Residue for Single Amino Acid)

AMBER force fields handle termini as separate residue definitions (NGLY, CGLY) and don't support standalone zwitterions by default. A custom **ZGLY** residue was created in the local force field copy.

**For Gly-Gly dipeptide**: Works natively (first residue uses NGLY, second uses CGLY)
```bash
gmx pdb2gmx -f structures/glygly_zw_charmm.pdb -o topologies/glygly_amber99sb.gro -p topologies/glygly_amber99sb.top -ff amber99sb-ildn -water tip3p
```

**For single glycine**: Use the custom ZGLY residue
```bash
gmx pdb2gmx -f structures/glycine_zw_amber.pdb -o topologies/glycine_amber99sb.gro -p topologies/glycine_amber99sb.top -ff amber99sb-ildn -water tip3p
```

### Files Created

**PDB Structures (properly formatted for pdb2gmx):**
- `structures/glycine_zw_charmm.pdb` - Glycine for CHARMM27
- `structures/glygly_zw_charmm.pdb` - Gly-Gly for CHARMM27
- `structures/glycine_zw_amber.pdb` - Glycine with ZGLY residue for AMBER

**Custom AMBER Force Field:**
- `amber99sb-ildn.ff/` - Local copy with custom ZGLY residue
  - `aminoacids.rtp` - Added ZGLY residue definition
  - `aminoacids.hdb` - Added hydrogen database entry
  - `aminoacids.arn` - Added atom renaming rules
  - `aminoacids.r2b` - Added residue mapping
- `residuetypes.dat` - Added ZGLY as Protein type

**Generated Topologies:**
- `topologies/glycine_charmm27.gro/.top` - CHARMM27 glycine
- `topologies/glygly_charmm27.gro/.top` - CHARMM27 Gly-Gly
- `topologies/glycine_amber99sb.gro/.top` - AMBER99SB-ILDN glycine
- `topologies/glygly_amber99sb.gro/.top` - AMBER99SB-ILDN Gly-Gly

---

## Original Problem Description

When trying to use `gmx pdb2gmx` on our glycine and Gly-Gly structures, we encountered errors because the tool expects PDB files formatted according to specific force field conventions. The phrase "proper pdb2gmx usage" refers to providing input files that meet these requirements.

## What pdb2gmx Expects

### 1. Correct Atom Naming Conventions

Force fields use specific atom naming schemes. For example, in protein residues:
- **Cα (alpha carbon)**: Named `CA` (not just `C`)
- **Hydrogen atoms**: Named `HA1`, `HA2`, `HA3` (not just `H`)
- **Carbonyl carbon**: Named `C`
- **Carbonyl oxygen**: Named `O`
- **Nitrogen**: Named `N`
- **Amide hydrogen**: Named `H` or `HN`

Our current PDB files use generic names like `C`, `O`, `N`, `H` for all atoms, which don't match force field expectations.

### 2. Proper Residue Context

Force fields are designed for **protein chains**, not standalone amino acids. They expect:
- **N-terminus**: Special atom types and charges for the first residue
- **C-terminus**: Special atom types and charges for the last residue
- **Middle residues**: Different parameterization when part of a chain

A standalone glycine molecule is problematic because it's simultaneously:
- An N-terminus (has -NH3+ group)
- A C-terminus (has -COO- group)
- A complete zwitterion (not typical in force field design)

### 3. Force Field Database Files

GROMACS force fields include:
- **aminoacids.rtp**: Residue topology database with proper atom types, charges, and bonds
- **aminoacids.n.tdb/c.tdb**: Terminal database for N/C termini modifications
- **atomtypes.atp**: Atom type definitions
- **ffbonded.itp**: Bond, angle, and dihedral parameters
- **ffnonbonded.itp**: Van der Waals and electrostatic parameters

These files define how GLY behaves in a protein chain, not as a standalone molecule.

## Why Our Approach Failed

1. **Simplified Topologies**: We generated topology files manually without proper force field parameters
2. **Generic Atom Names**: Our PDB files don't use force field-specific naming
3. **No Force Field Context**: Single amino acids aren't parameterized the same way as residues in chains
4. **Missing CHARMM36m/ff19SB**: Our GROMACS installation has older force field versions

## Resolution Options

### Option 1: CHARMM-GUI (Recommended)
Use the CHARMM-GUI Solution Builder (https://www.charmm-gui.org/):
- Input: PDB structure of glycine or Gly-Gly
- Select: CHARMM36m or AMBER ff19SB force field
- Output: Complete topology files (.top, .itp) with proper parameterization
- Advantage: Industry-standard tool, handles zwitterions correctly
- Time: ~15-30 minutes per system

### Option 2: Manual PDB Preparation
Edit PDB files to match force field expectations:
1. Rename atoms according to force field conventions (CA, HA1, HA2, etc.)
2. Add proper residue identifiers (N-terminus, C-terminus flags)
3. Ensure atom ordering matches force field database
4. Run `gmx pdb2gmx -f corrected.pdb -o output.gro -p topol.top`

Challenges:
- Requires deep knowledge of force field atom naming
- Error-prone for zwitterionic standalone molecules
- May still fail if force field doesn't support standalone residues

### Option 3: Specialized Parameterization Tools
For small molecules and non-standard residues:
- **CGenFF** (CHARMM): General Force Field for small molecules
- **ACPYPE** (Amber): Automated topology generation
- **LigParGen**: Small molecule parameterization
- **SwissParam**: Automated topology generation service

These tools are designed for ligands and non-standard molecules but may still require manual adjustments for zwitterionic amino acids.

## Production Workflow Recommendation

For the SQUIP project to proceed:

1. **Use CHARMM-GUI** to generate proper topologies:
   - Submit glycine zwitterion structure
   - Submit Gly-Gly dipeptide structure
   - Select CHARMM36m force field
   - Select ff19SB force field (if available)
   - Download complete topology packages

2. **Replace simplified topologies** with CHARMM-GUI output

3. **Resume from Substep 1.4**: Ion addition using proper topologies

4. **Continue with Substeps 1.5-1.7**: Energy minimization and equilibration

## Key Takeaway

The phrase "proper pdb2gmx usage" means providing PDB files with:
- ✅ Force field-specific atom naming (CA, HA1, HA2, not generic C, H, H)
- ✅ Proper residue context (N-terminus, C-terminus, or chain middle)
- ✅ Compatible with force field residue definitions
- ✅ Correct atom ordering and connectivity

Our current structures violate these requirements, which is why `gmx pdb2gmx` fails. The recommended solution is to use CHARMM-GUI to generate production-ready topology files.
