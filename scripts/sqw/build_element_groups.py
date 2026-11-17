#!/usr/bin/env python3
"""Build element-based atom index groups using MDAnalysis."""

import MDAnalysis as mda

WATER_RESNAMES = {"SOL", "WAT", "HOH", "TIP3", "TIP3P", "TIP4", "TIP4P", "T4E"}

# Virtual-site / dummy atom names that should be excluded from
# scattering calculations (e.g. TIP4P-Ew "MW" or "M" sites).
VIRTUAL_SITE_NAMES = {"M", "MW", "LP", "EP", "VS"}


def guess_element(atom):
    try:
        if atom.element:
            return atom.element.capitalize()
    except Exception:
        pass
    return atom.name[0].upper()


def _is_virtual_site(atom):
    """Return True for virtual sites (zero-mass dummy atoms)."""
    atom_name = str(atom.name).upper()
    if atom_name in VIRTUAL_SITE_NAMES:
        return True
    # Some topologies label water dummy sites as M, M1, M2, etc.
    # Restrict this pattern to known water residues to avoid filtering
    # real non-water atoms that may start with "M".
    if str(atom.resname).upper() in WATER_RESNAMES and atom_name.startswith("M"):
        return True
    try:
        if atom.mass < 0.1:
            return True
    except Exception:
        pass
    return False


def build_element_groups(universe, selection=None):
    if selection:
        atoms = universe.select_atoms(selection)
    else:
        atoms = universe.atoms

    groups = {}
    for atom in atoms:
        if _is_virtual_site(atom):
            continue
        elem = guess_element(atom)
        groups.setdefault(elem, []).append(atom.index)  # 0-based
    return groups


def build_solute_h_groups(universe):
    solute_sel = "not resname " + " ".join(sorted(WATER_RESNAMES))
    solute_h_sel = f"({solute_sel}) and name H*"
    return build_element_groups(universe, selection=solute_h_sel)
