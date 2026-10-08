#!/usr/bin/env python3
"""Run Step 3 analysis pipeline for all systems."""

import argparse
import logging
import os
import time

from compute_sqw import compute_sqw_for_system
from extract_linewidths import (
    extract_linewidths,
    fit_diffusion_coefficient,
    CM2_PER_S_TO_M2_PER_S,
)
from plot_sqw import plot_sqw_heatmap, plot_fqt_decay
from export_hdf5 import export_to_hdf5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[logging.FileHandler("step3_analysis.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def get_all_systems():
    systems = []
    for mol in ["glycine", "glygly"]:
        for ff in ["amber99sb", "charmm27"]:
            for temp in ["300K", "350K"]:
                systems.append((mol, ff, temp))
    return systems


def run_analysis(systems, test_mode=False, allow_npt=False):
    frame_stop = 33333 if test_mode else None
    results = {}

    logger.info("Phase 1: Compute S(q,w)")
    for mol, ff, temp in systems:
        t0 = time.time()
        try:
            compute_sqw_for_system(
                mol,
                ff,
                temp,
                frame_stop=frame_stop,
                use_fixed_box=not allow_npt,
                allow_npt=allow_npt,
            )
            dt = time.time() - t0
            logger.info(f"  {mol}/{ff}/{temp}: {dt/60:.1f} min")
        except Exception as exc:
            logger.error(f"  {mol}/{ff}/{temp}: FAILED - {exc}")

    logger.info("Phase 2: Extract linewidths")
    for mol, ff, temp in systems:
        prefix = f"{mol}_{ff}_{temp}"
        npz = f"systems/{mol}/{ff}/{temp}/production/analysis/{prefix}_sqw_arrays.npz"
        try:
            q, gamma, gamma_err = extract_linewidths(npz)
            d = fit_diffusion_coefficient(q, gamma)
            results[prefix] = {"q": q, "gamma": gamma, "gamma_err": gamma_err, "D": d}
            logger.info(
                f"  {prefix}: D = {d:.2e} cm^2/s = {d * CM2_PER_S_TO_M2_PER_S:.2e} m^2/s"
            )
        except Exception as exc:
            logger.error(f"  {prefix}: FAILED - {exc}")

    logger.info("Phase 3: Plots")
    os.makedirs("analysis/plots", exist_ok=True)
    for mol, ff, temp in systems:
        prefix = f"{mol}_{ff}_{temp}"
        base = f"systems/{mol}/{ff}/{temp}/production/analysis"
        npz = f"{base}/{prefix}_sqw_arrays.npz"
        try:
            plot_sqw_heatmap(npz, prefix, f"analysis/plots/{prefix}_heatmap.png")
            plot_fqt_decay(npz, prefix, f"analysis/plots/{prefix}_fqt.png")
        except Exception as exc:
            logger.warning(f"  Plot failed for {prefix}: {exc}")

    logger.info("Phase 4: HDF5 export")
    for mol, ff, temp in systems:
        prefix = f"{mol}_{ff}_{temp}"
        npz = f"systems/{mol}/{ff}/{temp}/production/analysis/{prefix}_sqw_arrays.npz"
        hdf5 = f"systems/{mol}/{ff}/{temp}/production/analysis/{prefix}_sqw.h5"
        metadata = {
            "molecule": mol,
            "forcefield": ff,
            "temperature_K": int(temp.replace("K", "")),
            "water_model": "TIP4P-Ew" if ff == "amber99sb" else "TIP3P",
            "concentration_M": 0.5,
            "n_solute": 50,
            "trajectory_length_ns": 20,
            "frame_interval_fs": 30,
        }
        try:
            export_to_hdf5(npz, hdf5, metadata)
        except Exception as exc:
            logger.warning(f"  HDF5 export failed for {prefix}: {exc}")

    if results:
        print("\nDiffusion Coefficients:")
        print(f"{'System':<35} {'D (10^-5 cm^2/s)':<20}")
        print("-" * 55)
        for key in sorted(results.keys()):
            d = results[key]["D"]
            print(f"{key:<35} {d*1e5:.3f}")


def main():
    parser = argparse.ArgumentParser(description="Run Step 3 analysis pipeline")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--allow-npt", action="store_true")
    parser.add_argument("--systems", nargs="+", help="e.g. glycine/amber99sb/300K")
    args = parser.parse_args()

    if args.systems:
        systems = [tuple(s.split("/")) for s in args.systems]
    else:
        systems = get_all_systems()

    run_analysis(systems, test_mode=args.test, allow_npt=args.allow_npt)


if __name__ == "__main__":
    main()
