#!/usr/bin/env python3
"""Validate computed S(q,w) arrays."""

import argparse
import numpy as np


def validate_sqw(npz_path, label):
    data = np.load(npz_path)
    q_norms = data["q_norms"]
    omega_meV = data["omega_meV"]
    sqw_coh = data["Sqw_coh"]
    sqw_incoh = data.get("Sqw_incoh", None)
    fqt_coh = data["Fqt_coh"]
    fqt_incoh = data.get("Fqt_incoh", None)
    time_fs = data["time_fs"]

    print("=" * 60)
    print(f"Validation: {label}")
    print("=" * 60)

    min_sqw = np.nanmin(sqw_coh)
    print(f"Min S_coh(q,w): {min_sqw:.6f}")

    if sqw_incoh is not None:
        min_sqw_inc = np.nanmin(sqw_incoh)
        print(f"Min S_incoh(q,w): {min_sqw_inc:.6f}")

    sq_from_fqt = fqt_coh[:, 0]
    print(f"S(q) from F(q,0): [{np.nanmin(sq_from_fqt):.4f}, {np.nanmax(sq_from_fqt):.4f}]")

    if fqt_incoh is not None:
        fincoh_t0 = fqt_incoh[:, 0]
        print(f"F_incoh(q,0) range: [{np.nanmin(fincoh_t0):.4f}, {np.nanmax(fincoh_t0):.4f}]")

    q_valid = q_norms[~np.isnan(q_norms)]
    print(f"q-range (rad/Angstrom): [{np.min(q_valid):.3f}, {np.max(q_valid):.3f}]")
    print(f"Number of q-bins: {len(q_norms)}")

    print(f"Energy range (meV): [{np.min(omega_meV):.3f}, {np.max(omega_meV):.3f}]")
    print(f"Energy resolution (meV): {omega_meV[1] - omega_meV[0]:.4f}")

    print(f"Time range (ps): [0, {np.max(time_fs)/1000.0:.1f}]")


def main():
    parser = argparse.ArgumentParser(description="Validate S(q,w) arrays")
    parser.add_argument("npz", nargs="+", help="Path(s) to _sqw_arrays.npz")
    args = parser.parse_args()

    for path in args.npz:
        validate_sqw(path, path)


if __name__ == "__main__":
    main()
