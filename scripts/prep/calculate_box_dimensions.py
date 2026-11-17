"""
Calculate box dimensions for solvated systems
Target: 1 M aqueous solution with ~50 molecules
"""

import math

def calculate_box_dimensions(n_molecules, concentration_M):
    """
    Calculate cubic box dimensions for a given concentration
    
    Parameters:
    -----------
    n_molecules : int
        Number of solute molecules
    concentration_M : float
        Target concentration in mol/L (M)
    
    Returns:
    --------
    dict with volume (nm³) and box side length (nm)
    """
    # Avogadro's number
    N_A = 6.022e23  # molecules/mol
    
    # Convert concentration to molecules/nm³
    # 1 M = 1 mol/L = 1 mol / 1000 cm³
    # 1 cm³ = 10⁷ nm³
    conc_molecules_per_nm3 = concentration_M * N_A / (1000 * 1e21)  # molecules/nm³
    
    # Calculate volume needed
    volume_nm3 = n_molecules / conc_molecules_per_nm3
    
    # Calculate side length for cubic box
    side_length_nm = volume_nm3 ** (1/3)
    
    return {
        'volume_nm3': volume_nm3,
        'side_length_nm': side_length_nm,
        'volume_L': volume_nm3 * 1e-24,  # Convert nm³ to L
    }

def estimate_total_atoms(n_solute, atoms_per_solute, box_side_nm, water_model='tip3p'):
    """
    Estimate total number of atoms in solvated system
    
    Parameters:
    -----------
    n_solute : int
        Number of solute molecules
    atoms_per_solute : int
        Atoms per solute molecule
    box_side_nm : float
        Box side length in nm
    water_model : str
        Water model: 'tip3p' (3 atoms) or 'tip4pew' (4 atoms, includes virtual site)
    
    Returns:
    --------
    dict with atom counts
    """
    # Water density at 300K: approximately 33.4 molecules/nm³
    # (calculated from 997 kg/m³ bulk water)
    water_molecules_per_nm3 = 33.4
    
    # Box volume
    box_volume_nm3 = box_side_nm ** 3
    
    # Total water molecules that would fit (rough estimate)
    # Assuming solute takes negligible volume for first approximation
    n_water_total = int(box_volume_nm3 * water_molecules_per_nm3)
    
    # Subtract approximate volume for solute molecules
    # Rough estimate: each solute molecule displaces ~2-3 water molecules
    water_displaced = n_solute * 2
    n_water = n_water_total - water_displaced
    
    # Total atoms - TIP3P has 3 atoms, TIP4P-Ew has 4 atoms (includes virtual site MW)
    atoms_per_water = 4 if water_model == 'tip4pew' else 3
    solute_atoms = n_solute * atoms_per_solute
    water_atoms = n_water * atoms_per_water
    total_atoms = solute_atoms + water_atoms
    
    return {
        'n_solute_molecules': n_solute,
        'n_water_molecules': n_water,
        'solute_atoms': solute_atoms,
        'water_atoms': water_atoms,
        'total_atoms': total_atoms,
        'box_volume_nm3': box_volume_nm3,
        'water_model': water_model,
        'atoms_per_water': atoms_per_water
    }

def main():
    """Main calculation and report generation"""
    
    print("=" * 70)
    print("BOX DIMENSION CALCULATIONS FOR SQUIP SYSTEMS")
    print("=" * 70)
    print()
    
    # System parameters
    target_concentration = 1.0  # M
    n_molecules = 50
    
    # Molecule data
    molecules = {
        'Glycine': {
            'atoms': 10,
            'formula': 'C2H5NO2',
            'molecular_weight': 75.07  # g/mol
        },
        'Gly-Gly': {
            'atoms': 17,
            'formula': 'C4H8N2O3',
            'molecular_weight': 132.12  # g/mol
        }
    }
    
    # Water models: CHARMM27 uses TIP3P, AMBER99SB uses TIP4P-Ew
    water_models = {
        'TIP3P (CHARMM)': 'tip3p',
        'TIP4P-Ew (AMBER)': 'tip4pew'
    }
    
    results = {}
    test_sizes = [4.0, 4.5, 5.0, 5.5, 6.0, 6.5]
    
    for mol_name, mol_data in molecules.items():
        print(f"\n{'='*70}")
        print(f"{mol_name} System")
        print("=" * 70)
        
        # Calculate box dimensions
        box_calc = calculate_box_dimensions(n_molecules, target_concentration)
        
        print(f"Target concentration: {target_concentration} M")
        print(f"Number of {mol_name} molecules: {n_molecules}")
        print(f"Atoms per molecule: {mol_data['atoms']}")
        print(f"\nCalculated box parameters:")
        print(f"  Volume needed: {box_calc['volume_nm3']:.2f} nm³ ({box_calc['volume_L']:.6e} L)")
        print(f"  Cubic box side: {box_calc['side_length_nm']:.3f} nm")
        
        for wm_name, wm_code in water_models.items():
            print(f"\n--- {wm_name} ---")
            atoms_per_water = 4 if wm_code == 'tip4pew' else 3
            print(f"Atoms per water molecule: {atoms_per_water}")
            
            print(f"\n{'Box (nm)':>10} {'Water Mol':>12} {'Total Atoms':>12} {'Actual Conc (M)':>16}")
            print("-" * 60)
            
            for box_size in test_sizes:
                atom_est = estimate_total_atoms(n_molecules, mol_data['atoms'], box_size, wm_code)
                
                # Calculate actual concentration
                volume_L = box_size**3 * 1e-24  # nm³ to L
                actual_conc = (n_molecules / 6.022e23) / volume_L
                
                print(f"{box_size:10.1f} {atom_est['n_water_molecules']:12d} "
                      f"{atom_est['total_atoms']:12d} {actual_conc:16.3f}")
                
                key = (box_size, mol_name, wm_code)
                results[key] = atom_est
    
    # Find optimal box size (closest to 15,000-22,000 atoms for TIP4P-Ew)
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    
    for mol_name in molecules.keys():
        print(f"\n{mol_name}:")
        for wm_name, wm_code in water_models.items():
            # TIP4P-Ew systems are larger, adjust target range
            if wm_code == 'tip4pew':
                target_min, target_max = 15000, 22000
            else:
                target_min, target_max = 15000, 20000
            
            best_box = None
            best_diff = float('inf')
            
            for box_size in test_sizes:
                key = (box_size, mol_name, wm_code)
                total = results[key]['total_atoms']
                if target_min <= total <= target_max:
                    diff = abs(total - (target_min + target_max) / 2)
                    if diff < best_diff:
                        best_diff = diff
                        best_box = box_size
            
            if best_box:
                key = (best_box, mol_name, wm_code)
                stats = results[key]
                volume_L = best_box**3 * 1e-24
                actual_conc = (n_molecules / 6.022e23) / volume_L
                print(f"  {wm_name}:")
                print(f"    Recommended box size: {best_box} nm")
                print(f"    Total atoms: {stats['total_atoms']:,}")
                print(f"    Water molecules: {stats['n_water_molecules']:,}")
                print(f"    Actual concentration: {actual_conc:.3f} M")
            else:
                print(f"  {wm_name}: No optimal box size found in range")
    
    # Write results to markdown file
    write_markdown_report(molecules, results, test_sizes, n_molecules, target_concentration, water_models)
    
    print("\n" + "=" * 70)
    print("Report saved to BOX_ANALYSIS.md")
    print("=" * 70)

def write_markdown_report(molecules, results, test_sizes, n_molecules, target_concentration, water_models):
    """Write detailed analysis to markdown file"""
    
    with open('BOX_ANALYSIS.md', 'w', encoding='utf-8') as f:
        f.write("# Box Dimension Analysis for SQUIP Systems\n\n")
        f.write("## Overview\n\n")
        f.write("This analysis calculates optimal simulation box dimensions to achieve ")
        f.write(f"approximately {target_concentration} M concentration with {n_molecules} solute molecules.\n\n")
        
        f.write("## Water Models\n\n")
        f.write("- **CHARMM27**: TIP3P water (3 atoms per molecule: O, H, H)\n")
        f.write("- **AMBER99SB-ILDN**: TIP4P-Ew water (4 atoms per molecule: O, H, H, MW virtual site)\n\n")
        
        f.write("## Calculation Method\n\n")
        f.write("1. **Target Concentration**: 1 M = 1 mol/L = 6.022 × 10²³ molecules/L\n")
        f.write("2. **Volume Calculation**: V = n_molecules / (concentration × N_A)\n")
        f.write("3. **Box Size**: For cubic box, side = V^(1/3)\n")
        f.write("4. **Water Filling**: Remaining volume filled with water (ρ ≈ 997 kg/m³)\n")
        f.write("5. **Target System Size**: 15,000-20,000 atoms (TIP3P) / 15,000-22,000 atoms (TIP4P-Ew)\n\n")
        
        f.write("## System Specifications\n\n")
        
        for mol_name, mol_data in molecules.items():
            f.write(f"### {mol_name}\n\n")
            f.write(f"- **Formula**: {mol_data['formula']}\n")
            f.write(f"- **Molecular Weight**: {mol_data['molecular_weight']} g/mol\n")
            f.write(f"- **Atoms per molecule**: {mol_data['atoms']}\n")
            f.write(f"- **Number of molecules**: {n_molecules}\n\n")
        
        f.write("## Box Size Analysis\n\n")
        
        for mol_name in molecules.keys():
            f.write(f"### {mol_name} System\n\n")
            
            for wm_name, wm_code in water_models.items():
                atoms_per_water = 4 if wm_code == 'tip4pew' else 3
                f.write(f"#### {wm_name} ({atoms_per_water} atoms/water)\n\n")
                f.write("| Box Size (nm) | Water Molecules | Solute Atoms | Water Atoms | Total Atoms | Concentration (M) |\n")
                f.write("|---------------|-----------------|--------------|-------------|-------------|-------------------|\n")
                
                for box_size in test_sizes:
                    key = (box_size, mol_name, wm_code)
                    stats = results[key]
                    volume_L = box_size**3 * 1e-24
                    actual_conc = (n_molecules / 6.022e23) / volume_L
                    
                    f.write(f"| {box_size:.1f} | {stats['n_water_molecules']:,} | ")
                    f.write(f"{stats['solute_atoms']:,} | {stats['water_atoms']:,} | ")
                    f.write(f"{stats['total_atoms']:,} | {actual_conc:.3f} |\n")
                
                f.write("\n")
        
        f.write("## Recommendations\n\n")
        
        for mol_name, mol_data in molecules.items():
            f.write(f"### {mol_name}\n\n")
            
            for wm_name, wm_code in water_models.items():
                # TIP4P-Ew systems are larger, adjust target range
                if wm_code == 'tip4pew':
                    target_min, target_max = 15000, 22000
                else:
                    target_min, target_max = 15000, 20000
                
                best_box = None
                best_diff = float('inf')
                
                for box_size in test_sizes:
                    key = (box_size, mol_name, wm_code)
                    total = results[key]['total_atoms']
                    if target_min <= total <= target_max:
                        diff = abs(total - (target_min + target_max) / 2)
                        if diff < best_diff:
                            best_diff = diff
                            best_box = box_size
                
                if best_box:
                    key = (best_box, mol_name, wm_code)
                    stats = results[key]
                    volume_L = best_box**3 * 1e-24
                    actual_conc = (n_molecules / 6.022e23) / volume_L
                    
                    f.write(f"**{wm_name}**: {best_box} nm × {best_box} nm × {best_box} nm\n\n")
                    f.write("- Total atoms: {:,}\n".format(stats['total_atoms']))
                    f.write("- Water molecules: {:,}\n".format(stats['n_water_molecules']))
                    f.write("- Solute atoms: {:,}\n".format(stats['solute_atoms']))
                    f.write(f"- Actual concentration: {actual_conc:.3f} M\n")
                    f.write(f"- Box volume: {best_box**3:.2f} nm³\n\n")
        
        f.write("## Implementation Notes\n\n")
        f.write("1. **GROMACS Commands**: Use `gmx insert-molecules` with `-box` parameter\n")
        f.write("2. **Water Models**:\n")
        f.write("   - CHARMM27: TIP3P water via `gmx solvate -cs spc216.gro`\n")
        f.write("   - AMBER99SB: TIP4P-Ew water via `-water tip4pew` in `pdb2gmx`\n")
        f.write("3. **Concentration**: Actual concentration may vary slightly based on final packing\n")
        f.write("4. **System Size**: Final atom count will depend on exact water placement\n")
        f.write("5. **TIP4P-Ew Note**: Virtual site (MW) adds 1 atom per water molecule\n\n")
        
        f.write("## Actual System Statistics\n\n")
        f.write("Based on generated solvated systems:\n\n")
        f.write("| System | Force Field | Water Model | Water Molecules | Total Atoms |\n")
        f.write("|--------|-------------|-------------|-----------------|-------------|\n")
        f.write("| Glycine | CHARMM27 | TIP3P | ~5,100 | ~15,800 |\n")
        f.write("| Glycine | AMBER99SB | TIP4P-Ew | ~5,000 | ~20,500 |\n")
        f.write("| Gly-Gly | CHARMM27 | TIP3P | ~4,990 | ~15,800 |\n")
        f.write("| Gly-Gly | AMBER99SB | TIP4P-Ew | ~4,980 | ~20,800 |\n")

if __name__ == "__main__":
    main()
