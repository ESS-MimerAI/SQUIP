#!/usr/bin/env python3
"""
Smoke test for the S(q,w) pipeline using a tiny synthetic trajectory.

Creates a small box with a few TIP4P-Ew water molecules (O, H, H, MW) and
runs the full Dynasor computation.  Verifies that:
  - Virtual-site atoms (MW) are excluded from element groups
  - compute_dynamic_structure_factors runs without error
  - Neutron-weighted S(q,w) can be obtained (no "M" key error)

Usage:
    python -m pytest tests/test_compute_sqw.py      (from the repository root)
"""

import os
import sys
import tempfile
import numpy as np
import MDAnalysis as mda

# Make the S(q,w) modules in scripts/sqw importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "sqw"))

from build_element_groups import build_element_groups
from gromacs_trajectory import GROMACSTrajectory

from dynasor import compute_dynamic_structure_factors
from dynasor.qpoints import get_spherical_qpoints
from dynasor.post_processing import (
    get_spherically_averaged_sample_binned,
    get_weighted_sample,
    NeutronScatteringLengths,
)
from dynasor.units import radians_per_fs_to_meV


def _make_tip4p_gro(path, n_waters=10, box_len=15.0):
    """Write a minimal .gro with *n_waters* TIP4P-Ew molecules.

    Each molecule has OW, HW1, HW2, MW — 4 atoms.  Positions are random
    inside a cubic box of side *box_len* Angstrom.
    """
    n_atoms = n_waters * 4
    rng = np.random.default_rng(42)

    lines = ["Tiny TIP4P-Ew test system", f"{n_atoms:>5d}"]
    idx = 1
    for i in range(1, n_waters + 1):
        resname = "SOL"
        # nm for .gro format
        ox, oy, oz = rng.uniform(0, box_len / 10, size=3)
        for name in ("OW", "HW1", "HW2", "MW"):
            # slightly shift H and MW relative to O
            dx, dy, dz = rng.uniform(-0.02, 0.02, size=3)
            lines.append(
                f"{i:>5d}{resname:<5s}{name:>5s}{idx:>5d}"
                f"{ox + dx:8.3f}{oy + dy:8.3f}{oz + dz:8.3f}"
            )
            idx += 1
    bx = box_len / 10  # nm
    lines.append(f"  {bx:.5f}  {bx:.5f}  {bx:.5f}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return n_atoms


def _make_xtc(gro_path, xtc_path, n_frames=50, box_len=15.0):
    """Write a short XTC trajectory with random displacements."""
    u = mda.Universe(gro_path)
    rng = np.random.default_rng(123)
    with mda.Writer(xtc_path, n_atoms=u.atoms.n_atoms) as w:
        for i in range(n_frames):
            # Small random walk per frame
            u.atoms.positions += rng.normal(0, 0.05, size=u.atoms.positions.shape)
            # Wrap into box
            u.atoms.positions %= box_len
            u.trajectory.ts.time = i * 30.0  # 30 fs per frame
            w.write(u.atoms)


# ---------------------------------------------------------------
# Test 1: virtual-site filtering
# ---------------------------------------------------------------
def test_element_groups_exclude_virtual_sites():
    with tempfile.TemporaryDirectory() as tmp:
        gro = os.path.join(tmp, "test.gro")
        _make_tip4p_gro(gro, n_waters=5)
        u = mda.Universe(gro)
        groups = build_element_groups(u)
        assert "M" not in groups, f"'M' should be filtered out, got keys: {list(groups.keys())}"
        assert "O" in groups
        assert "H" in groups
        # Close handle so Windows can delete temp files
        u.trajectory.close()
        print("PASS  test_element_groups_exclude_virtual_sites")


# ---------------------------------------------------------------
# Test 2: full S(q,w) pipeline on a tiny trajectory
# ---------------------------------------------------------------
def test_full_pipeline():
    n_waters = 10
    box_len = 15.0  # Angstrom
    n_frames = 50

    output_dir = os.path.join(os.path.dirname(__file__), "test_output")
    os.makedirs(output_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        gro = os.path.join(tmp, "test.gro")
        xtc = os.path.join(tmp, "test.xtc")

        _make_tip4p_gro(gro, n_waters=n_waters, box_len=box_len)
        _make_xtc(gro, xtc, n_frames=n_frames, box_len=box_len)

        u = mda.Universe(gro, xtc)
        element_groups = build_element_groups(u)
        print(f"  Element groups: {list(element_groups.keys())} "
              f"(atom counts: {', '.join(f'{k}={len(v)}' for k, v in element_groups.items())})")

        traj = GROMACSTrajectory(
            topology=gro,
            trajectory=xtc,
            atomic_indices=element_groups,
            frame_step=1,
        )

        q_points = get_spherical_qpoints(traj.cell, q_max=2.0, max_points=200)
        print(f"  q_points: {len(q_points)}")

        dt_fs = 30.0  # must match the spacing used in _make_xtc

        # window_size must be < n_frames
        sample_raw = compute_dynamic_structure_factors(
            traj,
            q_points=q_points,
            dt=dt_fs,
            window_size=20,
            window_step=10,
            calculate_incoherent=True,
        )

        sample_avg = get_spherically_averaged_sample_binned(sample_raw, num_q_bins=5)

        atom_types = list(sample_raw.particle_counts.keys())
        neutron_weights = NeutronScatteringLengths(atom_types)
        sample_neutron = get_weighted_sample(sample_avg, neutron_weights)

        omega_meV = sample_avg.omega * radians_per_fs_to_meV

        # --- Save to persistent output directory ---
        arrays_file = os.path.join(output_dir, "test_sqw_arrays.npz")
        np.savez(
            arrays_file,
            q_norms=sample_avg.q_norms,
            omega_meV=omega_meV,
            Sqw_coh=sample_avg.Sqw_coh,
            Sqw_incoh=sample_avg.Sqw_incoh,
            Fqt_coh=sample_avg.Fqt_coh,
            Fqt_incoh=sample_avg.Fqt_incoh,
        )
        sample_avg.write_to_npz(os.path.join(output_dir, "test_sqw_averaged.npz"))
        sample_neutron.write_to_npz(os.path.join(output_dir, "test_sqw_neutron.npz"))

        # --- Print summary of results ---
        print(f"\n  === S(q,w) results ===")
        print(f"  q bins       : {len(sample_avg.q_norms)}")
        print(f"  q range      : {sample_avg.q_norms.min():.3f} .. {sample_avg.q_norms.max():.3f} 1/Angstrom")
        print(f"  omega points : {len(omega_meV)}")
        print(f"  omega range  : {omega_meV.min():.2f} .. {omega_meV.max():.2f} meV")
        print(f"  Sqw_coh shape: {sample_avg.Sqw_coh.shape}  (q_bins x omega)")
        print(f"  Sqw_coh max  : {sample_avg.Sqw_coh.max():.6f}")
        print(f"  Sqw_incoh max: {sample_avg.Sqw_incoh.max():.6f}")
        print(f"\n  Saved to: {output_dir}/")
        print(f"    test_sqw_arrays.npz   - q, omega, S(q,w) arrays")
        print(f"    test_sqw_averaged.npz - dynasor averaged sample")
        print(f"    test_sqw_neutron.npz  - neutron-weighted sample")
        print(f"\n  To inspect results:")
        print(f"    python -c \"import numpy as np; d=np.load('{arrays_file}'); "
              f"print(list(d.keys())); print('Sqw_coh:', d['Sqw_coh'].shape)\"")

        assert os.path.exists(arrays_file)
        data = np.load(arrays_file)
        assert "Sqw_coh" in data
        print("\nPASS  test_full_pipeline")

        # Close trajectory handles so Windows can delete temp files
        u.trajectory.close()
        traj._universe.trajectory.close()


if __name__ == "__main__":
    test_element_groups_exclude_virtual_sites()
    test_full_pipeline()
    print("\nAll tests passed.")
