from rdkit import Chem
from rdkit.Chem import AllChem

seq = "GG"  # Gly-Gly

# Build peptide graph from sequence
mol = Chem.MolFromSequence(seq)
mol = Chem.AddHs(mol)

# 3D coordinates + quick optimization
AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
AllChem.UFFOptimizeMolecule(mol)

# Write outputs
Chem.MolToPDBFile(mol, "GlyGly.pdb")
w = Chem.SDWriter("GlyGly.sdf")
w.write(mol)
w.close()

print("Wrote GlyGly.pdb and GlyGly.sdf")

