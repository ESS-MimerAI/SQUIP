"""
Regenerate proper GROMACS topology files using pdb2gmx
This will use the force fields available in the GROMACS installation
"""

import subprocess
import os

GMX = r"c:\util\gromacs\bin\gmx.exe"

systems = [
    ('glycine', 'inputs/structures/glycine_zw.pdb', 'charmm27'),
    ('glycine', 'inputs/structures/glycine_zw.pdb', 'amber99sb-ildn'),
    ('glygly', 'inputs/structures/GlyGly_zw.pdb', 'charmm27'),
    ('glygly', 'inputs/structures/GlyGly_zw.pdb', 'amber99sb-ildn'),
]

def run_pdb2gmx(mol_name, pdb_file, force_field):
    """Run gmx pdb2gmx to generate proper topology"""
    
    ff_map = {
        'charmm27': ('charmm27', 'charmm'),
        'amber99sb-ildn': ('amber99sb-ildn', 'amber')
    }
    
    ff_name, ff_short = ff_map[force_field]
    output_prefix = f'topologies/{mol_name}_{ff_short}'
    
    print(f"\nGenerating topology for {mol_name} with {ff_name}...")
    print(f"  Input: {pdb_file}")
    print(f"  Output: {output_prefix}.gro, {output_prefix}.top")
    
    # Use TIP4P-Ew for AMBER, TIP3P for CHARMM
    water_model = 'tip4pew' if 'amber' in ff_name else 'tip3p'
    
    cmd = [
        GMX, 'pdb2gmx',
        '-f', pdb_file,
        '-o', f'{output_prefix}.gro',
        '-p', f'{output_prefix}.top',
        '-i', f'{output_prefix}_posre.itp',
        '-ff', ff_name,
        '-water', water_model,
        '-ignh'  # Ignore hydrogen atoms in input
    ]
    
    print(f"  Water model: {water_model}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"  ✓ Success")
            return True
        else:
            print(f"  ✗ Failed")
            print(f"  Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ✗ Exception: {e}")
        return False

def main():
    print("=" * 70)
    print("REGENERATING TOPOLOGY FILES WITH GMX PDB2GMX")
    print("=" * 70)
    
    os.makedirs('topologies', exist_ok=True)
    
    success_count = 0
    for mol_name, pdb_file, ff in systems:
        if run_pdb2gmx(mol_name, pdb_file, ff):
            success_count += 1
    
    print("\n" + "=" * 70)
    print(f"Completed: {success_count}/{len(systems)} systems generated successfully")
    print("=" * 70)

if __name__ == "__main__":
    main()
