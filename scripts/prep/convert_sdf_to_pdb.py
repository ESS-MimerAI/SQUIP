"""
Simple SDF to PDB converter for glycine
"""
import sys
import os

def sdf_to_pdb(sdf_file, pdb_file):
    with open(sdf_file, 'r') as f:
        lines = f.readlines()
    
    # Find atom block
    atom_count_line = lines[3]
    atom_count = int(atom_count_line.split()[0])
    
    # Parse atoms (starting from line 4)
    atoms = []
    for i in range(4, 4 + atom_count):
        parts = lines[i].split()
        x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
        element = parts[3]
        atoms.append((element, x, y, z))
    
    # Write PDB file
    with open(pdb_file, 'w') as f:
        f.write("TITLE     Glycine (zwitterionic form)\n")
        f.write("REMARK    Downloaded from PubChem\n")
        f.write("REMARK    Converted from SDF format\n")
        
        for i, (element, x, y, z) in enumerate(atoms, 1):
            # PDB format: ATOM serial name resName chainID resSeq x y z occupancy tempFactor element
            f.write(f"ATOM  {i:5d}  {element:<3s} GLY A   1    {x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00          {element:>2s}\n")
        
        f.write("END\n")
    
    print(f"Converted {sdf_file} to {pdb_file}")
    print(f"Total atoms: {len(atoms)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_sdf_to_pdb.py <sdf_file>")
        sys.exit(1)
    
    sdf_file = sys.argv[1]
    basename = os.path.splitext(sdf_file)[0]
    pdb_file = f"{basename}.pdb"
    
    sdf_to_pdb(sdf_file, pdb_file)
