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
    # We use string names instead of numbers for robustness
    result = subprocess.run(
        ["gmx", "energy", "-f", edr],
        input="Temperature Pressure Density 0\n",
        capture_output=True,
        text=True
    )
    
    # Parse output
    lines = result.stdout.split('\n')
    stats = {}
    found_data = False
    
    for line in lines:
        parts = line.split()
        if not parts:
            continue
            
        # GROMACS energy output usually looks like:
        # Energy                      Average   Err.Est.       RMSD  Tot-Drift
        # Temperature                 299.885        0.6    1.89066   -0.03578  (K)
        
        # We check the first word to match our requested terms
        if parts[0] == 'Temperature':
            try:
                stats['T_avg'] = float(parts[1])
                stats['T_rmsd'] = float(parts[3]) # Index 3 is RMSD, Index 2 is Err.Est.
                found_data = True
            except (ValueError, IndexError):
                pass
        elif parts[0] == 'Pressure':
            try:
                stats['P_avg'] = float(parts[1])
                stats['P_rmsd'] = float(parts[3])
                found_data = True
            except (ValueError, IndexError):
                pass
        elif parts[0] == 'Density':
            try:
                stats['rho_avg'] = float(parts[1])
                stats['rho_rmsd'] = float(parts[3])
                found_data = True
            except (ValueError, IndexError):
                pass

    if not found_data and result.returncode == 0:
         print(f"  Warning: Could not parse expected data from {edr}")
         print("  Raw GROMACS output snippet:")
         print("\n".join(lines[:20])) # Print first 20 lines for debugging

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
