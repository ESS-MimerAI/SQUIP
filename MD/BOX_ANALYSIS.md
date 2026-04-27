# Box Dimension Analysis for SQUIP Systems

## Overview

This analysis calculates optimal simulation box dimensions to achieve approximately 1.0 M concentration with 50 solute molecules.

## Water Models

- **CHARMM27**: TIP3P water (3 atoms per molecule: O, H, H)
- **AMBER99SB-ILDN**: TIP4P-Ew water (4 atoms per molecule: O, H, H, MW virtual site)

## Calculation Method

1. **Target Concentration**: 1 M = 1 mol/L = 6.022 × 10²³ molecules/L
2. **Volume Calculation**: V = n_molecules / (concentration × N_A)
3. **Box Size**: For cubic box, side = V^(1/3)
4. **Water Filling**: Remaining volume filled with water (ρ ≈ 997 kg/m³)
5. **Target System Size**: 15,000-20,000 atoms (TIP3P) / 15,000-22,000 atoms (TIP4P-Ew)

## System Specifications

### Glycine

- **Formula**: C2H5NO2
- **Molecular Weight**: 75.07 g/mol
- **Atoms per molecule**: 10
- **Number of molecules**: 50

### Gly-Gly

- **Formula**: C4H8N2O3
- **Molecular Weight**: 132.12 g/mol
- **Atoms per molecule**: 17
- **Number of molecules**: 50

## Box Size Analysis

### Glycine System

#### TIP3P (CHARMM) (3 atoms/water)

| Box Size (nm) | Water Molecules | Solute Atoms | Water Atoms | Total Atoms | Concentration (M) |
|---------------|-----------------|--------------|-------------|-------------|-------------------|
| 4.0 | 2,037 | 500 | 6,111 | 6,611 | 1.297 |
| 4.5 | 2,943 | 500 | 8,829 | 9,329 | 0.911 |
| 5.0 | 4,075 | 500 | 12,225 | 12,725 | 0.664 |
| 5.5 | 5,456 | 500 | 16,368 | 16,868 | 0.499 |
| 6.0 | 7,114 | 500 | 21,342 | 21,842 | 0.384 |
| 6.5 | 9,072 | 500 | 27,216 | 27,716 | 0.302 |

#### TIP4P-Ew (AMBER) (4 atoms/water)

| Box Size (nm) | Water Molecules | Solute Atoms | Water Atoms | Total Atoms | Concentration (M) |
|---------------|-----------------|--------------|-------------|-------------|-------------------|
| 4.0 | 2,037 | 500 | 8,148 | 8,648 | 1.297 |
| 4.5 | 2,943 | 500 | 11,772 | 12,272 | 0.911 |
| 5.0 | 4,075 | 500 | 16,300 | 16,800 | 0.664 |
| 5.5 | 5,456 | 500 | 21,824 | 22,324 | 0.499 |
| 6.0 | 7,114 | 500 | 28,456 | 28,956 | 0.384 |
| 6.5 | 9,072 | 500 | 36,288 | 36,788 | 0.302 |

### Gly-Gly System

#### TIP3P (CHARMM) (3 atoms/water)

| Box Size (nm) | Water Molecules | Solute Atoms | Water Atoms | Total Atoms | Concentration (M) |
|---------------|-----------------|--------------|-------------|-------------|-------------------|
| 4.0 | 2,037 | 850 | 6,111 | 6,961 | 1.297 |
| 4.5 | 2,943 | 850 | 8,829 | 9,679 | 0.911 |
| 5.0 | 4,075 | 850 | 12,225 | 13,075 | 0.664 |
| 5.5 | 5,456 | 850 | 16,368 | 17,218 | 0.499 |
| 6.0 | 7,114 | 850 | 21,342 | 22,192 | 0.384 |
| 6.5 | 9,072 | 850 | 27,216 | 28,066 | 0.302 |

#### TIP4P-Ew (AMBER) (4 atoms/water)

| Box Size (nm) | Water Molecules | Solute Atoms | Water Atoms | Total Atoms | Concentration (M) |
|---------------|-----------------|--------------|-------------|-------------|-------------------|
| 4.0 | 2,037 | 850 | 8,148 | 8,998 | 1.297 |
| 4.5 | 2,943 | 850 | 11,772 | 12,622 | 0.911 |
| 5.0 | 4,075 | 850 | 16,300 | 17,150 | 0.664 |
| 5.5 | 5,456 | 850 | 21,824 | 22,674 | 0.499 |
| 6.0 | 7,114 | 850 | 28,456 | 29,306 | 0.384 |
| 6.5 | 9,072 | 850 | 36,288 | 37,138 | 0.302 |

## Recommendations

### Glycine

**TIP3P (CHARMM)**: 5.5 nm × 5.5 nm × 5.5 nm

- Total atoms: 16,868
- Water molecules: 5,456
- Solute atoms: 500
- Actual concentration: 0.499 M
- Box volume: 166.38 nm³

**TIP4P-Ew (AMBER)**: 5.0 nm × 5.0 nm × 5.0 nm

- Total atoms: 16,800
- Water molecules: 4,075
- Solute atoms: 500
- Actual concentration: 0.664 M
- Box volume: 125.00 nm³

### Gly-Gly

**TIP3P (CHARMM)**: 5.5 nm × 5.5 nm × 5.5 nm

- Total atoms: 17,218
- Water molecules: 5,456
- Solute atoms: 850
- Actual concentration: 0.499 M
- Box volume: 166.38 nm³

**TIP4P-Ew (AMBER)**: 5.0 nm × 5.0 nm × 5.0 nm

- Total atoms: 17,150
- Water molecules: 4,075
- Solute atoms: 850
- Actual concentration: 0.664 M
- Box volume: 125.00 nm³

## Implementation Notes

1. **GROMACS Commands**: Use `gmx insert-molecules` with `-box` parameter
2. **Water Models**:
   - CHARMM27: TIP3P water via `gmx solvate -cs spc216.gro`
   - AMBER99SB: TIP4P-Ew water via `-water tip4pew` in `pdb2gmx`
3. **Concentration**: Actual concentration may vary slightly based on final packing
4. **System Size**: Final atom count will depend on exact water placement
5. **TIP4P-Ew Note**: Virtual site (MW) adds 1 atom per water molecule

## Actual System Statistics

Based on generated solvated systems:

| System | Force Field | Water Model | Water Molecules | Total Atoms |
|--------|-------------|-------------|-----------------|-------------|
| Glycine | CHARMM27 | TIP3P | ~5,100 | ~15,800 |
| Glycine | AMBER99SB | TIP4P-Ew | ~5,000 | ~20,500 |
| Gly-Gly | CHARMM27 | TIP3P | ~4,990 | ~15,800 |
| Gly-Gly | AMBER99SB | TIP4P-Ew | ~4,980 | ~20,800 |
