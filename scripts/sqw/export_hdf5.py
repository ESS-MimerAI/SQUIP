#!/usr/bin/env python3
"""Export S(q,w) arrays to HDF5 with metadata."""

import argparse
import h5py
import numpy as np


def export_to_hdf5(npz_path, hdf5_path, metadata):
    data = np.load(npz_path)

    with h5py.File(hdf5_path, "w") as f:
        meta = f.create_group("metadata")
        for key, val in metadata.items():
            meta.attrs[key] = val

        axes = f.create_group("axes")
        axes.create_dataset("q_norms", data=data["q_norms"])
        axes.attrs["q_units"] = "rad/Angstrom"
        axes.create_dataset("omega_meV", data=data["omega_meV"])
        axes.attrs["omega_units"] = "meV"
        axes.create_dataset("time_fs", data=data["time_fs"])
        axes.attrs["time_units"] = "fs"

        sqw = f.create_group("structure_factors")
        sqw.create_dataset("Sqw_coh", data=data["Sqw_coh"])
        sqw.create_dataset("Sqw_incoh", data=data["Sqw_incoh"])

        fqt = f.create_group("intermediate_scattering")
        fqt.create_dataset("Fqt_coh", data=data["Fqt_coh"])
        fqt.create_dataset("Fqt_incoh", data=data["Fqt_incoh"])


def main():
    parser = argparse.ArgumentParser(description="Export S(q,w) to HDF5")
    parser.add_argument("npz", help="Path to _sqw_arrays.npz")
    parser.add_argument("hdf5", help="Output .h5 path")
    args = parser.parse_args()

    export_to_hdf5(args.npz, args.hdf5, metadata={})


if __name__ == "__main__":
    main()
