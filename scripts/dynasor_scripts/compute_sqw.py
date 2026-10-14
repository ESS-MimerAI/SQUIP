#!/usr/bin/env python3
"""
compute_sqw.py - Compute S(q,w) using Dynasor with MDAnalysis reader.

Usage:
    python scripts/compute_sqw.py <molecule> <forcefield> <temperature>

Example:
    python scripts/compute_sqw.py glycine amber99sb 300K
"""

import argparse
import logging
import os
import sys
import numpy as np
import MDAnalysis as mda

SCRIPT_DIR = os.path.dirname(__file__)
SCRIPTS_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if SCRIPTS_ROOT not in sys.path:
    sys.path.insert(0, SCRIPTS_ROOT)

from dynasor import compute_dynamic_structure_factors
from dynasor.qpoints import get_spherical_qpoints
from dynasor.post_processing import (
    get_spherically_averaged_sample_binned,
    get_weighted_sample,
    NeutronScatteringLengths,
)
from dynasor.units import radians_per_fs_to_meV

from gromacs_trajectory import GROMACSTrajectory
from build_element_groups import build_element_groups

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _build_neutron_sample_or_none(sample_averaged, particle_counts):
    atom_types = list(particle_counts.keys())
    try:
        neutron_weights = NeutronScatteringLengths(atom_types)
    except Exception as exc:
        unsupported = []
        for atom_type in atom_types:
            try:
                NeutronScatteringLengths([atom_type])
            except Exception:
                unsupported.append(atom_type)
        if unsupported:
            logger.warning(
                "Skipping neutron-weighted S(q,w): unsupported particle types: %s",
                ", ".join(sorted(unsupported)),
            )
            return None
        raise RuntimeError(f"Failed to build neutron weights for atom types {atom_types}: {exc}")

    return get_weighted_sample(sample_averaged, neutron_weights)


def _resolve_xtc(base, use_fixed_box, allow_npt):
    fixed = os.path.join(base, "prod_nvt_fixed.xtc")
    npt = os.path.join(base, "prod_center.xtc")

    if use_fixed_box and os.path.exists(fixed):
        return fixed
    if allow_npt and os.path.exists(npt):
        return npt

    if use_fixed_box:
        raise FileNotFoundError(f"Fixed-box trajectory not found: {fixed}")
    raise FileNotFoundError(f"Trajectory not found: {npt}")


def compute_and_save_sqw(
    traj,
    dt_fs,
    prefix,
    output_dir,
    q_max=2.5,
    max_q_points=5000,
    window_size=2000,
    window_step=200,
    num_q_bins=30,
):
    """Run Dynasor on an already-opened trajectory and write the npz outputs.

    This is the Dynasor-and-save stage of :func:`compute_sqw_for_system`,
    split out so that a synthetic trajectory (see
    ``test_planted_truth_diffusion.py``) goes through exactly the same
    q-point generation, spherical binning and ``*_sqw_arrays.npz`` layout
    as production data.

    Parameters
    ----------
    traj        : trajectory object with the Dynasor duck-typed interface
                  (``cell``, ``atomic_indices``, iteration), e.g.
                  :class:`GROMACSTrajectory`.
    dt_fs       : time between consecutive frames of the *original*
                  trajectory in fs (Dynasor multiplies by ``traj.frame_step``).
    prefix      : output file prefix, e.g. ``glycine_amber99sb_300K``.
    output_dir  : directory for the npz files (created if missing).

    Returns
    -------
    (sample_averaged, arrays_npz_path)
    """
    os.makedirs(output_dir, exist_ok=True)

    q_points = get_spherical_qpoints(
        traj.cell,
        q_max=q_max,
        max_points=max_q_points,
    )

    logger.info(f"  Generated {len(q_points)} q-points (q_max={q_max} rad/Angstrom)")
    logger.info("  Computing S(q,w) with:")
    logger.info(f"    dt = {dt_fs:.3f} fs")
    logger.info(f"    window_size = {window_size} frames = {window_size * dt_fs / 1000:.1f} ps")
    logger.info(f"    window_step = {window_step} frames = {window_step * dt_fs / 1000:.1f} ps")
    logger.info(
        "    Frequency resolution: "
        f"{2 * np.pi / (window_size * dt_fs) * radians_per_fs_to_meV:.4f} meV"
    )
    logger.info(f"    Nyquist frequency: {np.pi / dt_fs * radians_per_fs_to_meV:.1f} meV")

    sample_raw = compute_dynamic_structure_factors(
        traj,
        q_points=q_points,
        dt=dt_fs,
        window_size=window_size,
        window_step=window_step,
        calculate_incoherent=True,
    )

    sample_averaged = get_spherically_averaged_sample_binned(sample_raw, num_q_bins=num_q_bins)

    sample_neutron = _build_neutron_sample_or_none(
        sample_averaged,
        sample_raw.particle_counts,
    )

    omega_meV = sample_averaged.omega * radians_per_fs_to_meV

    sample_raw.write_to_npz(os.path.join(output_dir, f"{prefix}_sqw_raw.npz"))
    sample_averaged.write_to_npz(os.path.join(output_dir, f"{prefix}_sqw_averaged.npz"))
    if sample_neutron is not None:
        sample_neutron.write_to_npz(os.path.join(output_dir, f"{prefix}_sqw_neutron.npz"))

    arrays_path = os.path.join(output_dir, f"{prefix}_sqw_arrays.npz")
    np.savez(
        arrays_path,
        q_norms=sample_averaged.q_norms,
        omega_rad_per_fs=sample_averaged.omega,
        omega_meV=omega_meV,
        time_fs=sample_averaged.time,
        Sqw_coh=sample_averaged.Sqw_coh,
        Sqw_incoh=sample_averaged.Sqw_incoh,
        Fqt_coh=sample_averaged.Fqt_coh,
        Fqt_incoh=sample_averaged.Fqt_incoh,
    )

    logger.info(f"  Complete: {prefix}")
    return sample_averaged, arrays_path


def compute_sqw_for_system(
    molecule,
    forcefield,
    temperature,
    q_max=2.5,
    max_q_points=5000,
    window_size=2000,
    window_step=200,
    frame_step=1,
    frame_stop=None,
    use_fixed_box=True,
    allow_npt=False,
    selection=None,
    output_dir=None,
):
    base = os.path.join("systems", molecule, forcefield, temperature, "production")
    tpr_file = os.path.join(base, "prod.tpr")
    xtc_file = _resolve_xtc(base, use_fixed_box, allow_npt)

    if output_dir is None:
        output_dir = os.path.join(base, "analysis")
    os.makedirs(output_dir, exist_ok=True)

    for fpath in [tpr_file, xtc_file]:
        if not os.path.exists(fpath):
            raise FileNotFoundError(f"Required file not found: {fpath}")

    logger.info(f"Processing {molecule}/{forcefield}/{temperature}")
    logger.info(f"  TPR: {tpr_file}")
    logger.info(f"  XTC: {xtc_file}")

    u = mda.Universe(tpr_file, xtc_file)
    dt_ps = u.trajectory.dt
    if dt_ps is None:
        dt_ps = 0.03
        logger.warning("Trajectory dt not found. Using default 0.03 ps.")

    # dt must be the time between consecutive frames in the *original*
    # trajectory (not multiplied by frame_step).  Dynasor computes
    # delta_t = traj.frame_step * dt internally.
    dt_fs = dt_ps * 1000.0

    element_groups = build_element_groups(u, selection=selection)

    traj = GROMACSTrajectory(
        topology=tpr_file,
        trajectory=xtc_file,
        atomic_indices=element_groups,
        frame_step=frame_step,
        frame_stop=frame_stop,
    )

    prefix = f"{molecule}_{forcefield}_{temperature}"
    sample_averaged, _ = compute_and_save_sqw(
        traj,
        dt_fs,
        prefix,
        output_dir,
        q_max=q_max,
        max_q_points=max_q_points,
        window_size=window_size,
        window_step=window_step,
    )
    return sample_averaged


def main():
    parser = argparse.ArgumentParser(description="Compute S(q,w) using Dynasor")
    parser.add_argument("molecule", nargs="?", help="glycine or glygly")
    parser.add_argument("forcefield", nargs="?", help="amber99sb or charmm27")
    parser.add_argument("temperature", nargs="?", help="300K or 350K")
    parser.add_argument("--frame-step", type=int, default=1)
    parser.add_argument("--frame-stop", type=int, default=None)
    parser.add_argument("--allow-npt", action="store_true")
    parser.add_argument("--selection", default=None, help="MDAnalysis atom selection")
    args = parser.parse_args()

    if args.molecule and args.forcefield and args.temperature:
        compute_sqw_for_system(
            args.molecule,
            args.forcefield,
            args.temperature,
            frame_step=args.frame_step,
            frame_stop=args.frame_stop,
            use_fixed_box=not args.allow_npt,
            allow_npt=args.allow_npt,
            selection=args.selection,
        )
        return

    if any([args.molecule, args.forcefield, args.temperature]):
        print(__doc__)
        sys.exit(1)

    for mol in ["glycine", "glygly"]:
        for ff in ["amber99sb", "charmm27"]:
            for temp in ["300K", "350K"]:
                try:
                    compute_sqw_for_system(
                        mol,
                        ff,
                        temp,
                        frame_step=args.frame_step,
                        frame_stop=args.frame_stop,
                        use_fixed_box=not args.allow_npt,
                        allow_npt=args.allow_npt,
                        selection=args.selection,
                    )
                except Exception as exc:
                    logger.error(f"Failed {mol}/{ff}/{temp}: {exc}")


if __name__ == "__main__":
    main()
