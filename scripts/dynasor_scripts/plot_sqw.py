#!/usr/bin/env python3
"""Plot S(q,w) and F(q,t) diagnostics."""

import argparse
import numpy as np
import matplotlib.pyplot as plt

RADIANS_PER_FS_TO_MEV = 0.6582119514


def _load_sqw_arrays(npz_path):
    data = np.load(npz_path, allow_pickle=True)
    files = set(data.files)

    # dynasor output sometimes stores results in a nested dict under 'data_dict'
    nested = None
    if "data_dict" in files:
        raw = data["data_dict"]
        if isinstance(raw, np.ndarray) and raw.shape == ():
            raw = raw.item()
        if isinstance(raw, dict):
            nested = raw

    def fallback(names, required=True):
        if nested is not None:
            for name in names:
                if name in nested:
                    return nested[name]
        for name in names:
            if name in files:
                return data[name]
        if required:
            raise KeyError(
                f"Missing required array. expected one of {names}, got {sorted(files)} in {npz_path}"
            )
        return None

    q_norms = fallback(["q_norms", "q_norm", "q", "q_values"])
    time_fs = fallback(["time_fs", "time", "t"])

    omega_meV = None
    omega_source = None
    for name in ["omega_meV", "omega", "omega_rad_per_fs"]:
        if nested is not None and name in nested:
            omega_source = name
            omega_meV = nested[name]
            break
        if name in files:
            omega_source = name
            omega_meV = data[name]
            break

    if omega_source is None:
        raise KeyError(
            f"Missing required omega array (omega_meV / omega / omega_rad_per_fs). available keys: {sorted(files)}"
        )

    if omega_source == "omega_rad_per_fs":
        omega_meV = omega_meV * RADIANS_PER_FS_TO_MEV

    sqw_incoh = fallback([
        "Sqw_incoh",
        "sqw_incoh",
        "S(q,w)_incoh",
        "S_incoh",
        "Sqw_incoherent",
    ], required=False)

    fqt_incoh = fallback([
        "Fqt_incoh",
        "fqt_incoh",
        "F_incoh",
        "Fqt_incoherent",
    ], required=False)

    return {
        "q_norms": q_norms,
        "time_fs": time_fs,
        "omega_meV": omega_meV,
        "sqw_incoh": sqw_incoh,
        "fqt_incoh": fqt_incoh,
    }


def plot_sqw_heatmap(npz_path, title, output_path, energy_max=5.0):
    arrays = _load_sqw_arrays(npz_path)
    q_norms = arrays["q_norms"]
    omega_meV = arrays["omega_meV"]
    sqw_incoh = arrays["sqw_incoh"]

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)

    mask_w = (omega_meV >= 0) & (omega_meV <= energy_max)
    mask_q = ~np.isnan(q_norms)

    im = ax.pcolormesh(
        q_norms[mask_q],
        omega_meV[mask_w],
        sqw_incoh[np.ix_(mask_q, mask_w)].T,
        cmap="hot_r",
        shading="auto",
    )
    ax.set_xlabel("|q| (rad/Angstrom)")
    ax.set_ylabel("hbar*omega (meV)")
    ax.set_title(title)
    plt.colorbar(im, ax=ax, label="S_incoh(q,w)")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_fqt_decay(npz_path, title, output_path, q_targets=None):
    if q_targets is None:
        q_targets = [0.5, 1.0, 1.5]

    arrays = _load_sqw_arrays(npz_path)
    q_norms = arrays["q_norms"]
    time_fs = arrays["time_fs"]
    fqt_incoh = arrays["fqt_incoh"]

    if fqt_incoh is None:
        raise KeyError(
            f"Could not find Fqt_incoh in NPZ file {npz_path}. available keys: {sorted(set(np.load(npz_path).files))}"
        )

    time_ps = time_fs / 1000.0

    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)

    for q_target in q_targets:
        idx = np.nanargmin(np.abs(q_norms - q_target))
        if np.isnan(q_norms[idx]):
            continue
        label = f"|q| = {q_norms[idx]:.2f} rad/Angstrom"
        ax.plot(time_ps, fqt_incoh[idx, :].real, label=label, alpha=0.8)

    ax.set_xlabel("Time (ps)")
    ax.set_ylabel("F_incoh(q,t)")
    ax.set_title(title)
    ax.set_xlim([0, 30])
    ax.set_yscale("log")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Plot S(q,w) diagnostics")
    parser.add_argument(
        "npz",
        help="Path to _sqw_arrays.npz (recommended) or _sqw_averaged.npz with compatible keys",
    )
    parser.add_argument("--out", required=True, help="Output PNG")
    parser.add_argument("--type", choices=["heatmap", "fqt"], default="heatmap")
    args = parser.parse_args()

    title = f"{args.type} plot: {args.npz}"

    if args.type == "heatmap":
        plot_sqw_heatmap(args.npz, title, args.out)
    else:
        plot_fqt_decay(args.npz, title, args.out)


if __name__ == "__main__":
    main()
