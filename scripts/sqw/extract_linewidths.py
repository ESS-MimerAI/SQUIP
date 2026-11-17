#!/usr/bin/env python3
"""Extract Gamma(q) from F_incoh(q,t) and estimate diffusion coefficient."""

import argparse
import numpy as np
from scipy.optimize import curve_fit

# Physical constant and unit factors used for the diffusion fit.
HBAR_MEV_PS = 0.6582119514          # hbar in meV*ps
A2_PER_PS_TO_CM2_PER_S = 1e-4       # 1 Angstrom^2/ps = 1e-4 cm^2/s
A2_PER_PS_TO_M2_PER_S = 1e-8        # 1 Angstrom^2/ps = 1e-8 m^2/s
CM2_PER_S_TO_M2_PER_S = 1e-4        # 1 cm^2/s = 1e-4 m^2/s


def single_exponential(t, a, gamma):
    return a * np.exp(-gamma * t)


def extract_linewidths(npz_path, fit_range_ps=(0.1, 30.0)):
    data = np.load(npz_path)
    q_norms = data["q_norms"]
    time_fs = data["time_fs"]
    fqt_incoh = data["Fqt_incoh"]

    time_ps = time_fs / 1000.0
    t_min, t_max = fit_range_ps
    mask = (time_ps >= t_min) & (time_ps <= t_max)
    t_fit = time_ps[mask]

    gamma_q = np.full(len(q_norms), np.nan)
    gamma_q_err = np.full(len(q_norms), np.nan)

    for iq in range(len(q_norms)):
        if np.isnan(q_norms[iq]):
            continue
        y = fqt_incoh[iq, mask]
        if np.any(np.isnan(y)):
            continue
        try:
            popt, pcov = curve_fit(
                single_exponential,
                t_fit,
                y.real,
                p0=[1.0, 0.1],
                bounds=([0.0, 0.0], [2.0, 100.0]),
                maxfev=10000,
            )
            gamma_q[iq] = popt[1]
            gamma_q_err[iq] = np.sqrt(pcov[1, 1])
        except (RuntimeError, ValueError):
            continue

    hbar_meV_ps = HBAR_MEV_PS
    gamma_meV = gamma_q * hbar_meV_ps
    gamma_meV_err = gamma_q_err * hbar_meV_ps

    return q_norms, gamma_meV, gamma_meV_err


def fit_diffusion_coefficient(q_norms, gamma_meV, q_max_fit=1.0):
    """Fit Gamma_E(q) = hbar * D * q^2 and return D in cm^2/s.

    q convention: Dynasor's ``q_norms`` are the angular wavevector
    |q| = 2*pi/lambda in 1/Angstrom (the Dynasor docs write this as
    "rad/Angstrom").  This is already the conventional neutron Q that enters
    exp(i q.r) and the Fickian linewidth Gamma_E = hbar * D * q^2, so it is
    used directly.  Do NOT divide by 2*pi: an earlier version did, which
    inflated D by (2*pi)^2 ~ 39.5 and shifted the q_max_fit cutoff.

    Parameters
    ----------
    q_norms   : |q| in 1/Angstrom, exactly as returned by Dynasor.
    gamma_meV : HWHM linewidths Gamma_E in meV.
    q_max_fit : only 0 < q < q_max_fit (1/Angstrom) enter the fit, to stay in
                the Fickian (Gamma ~ q^2) regime.

    Returns
    -------
    D in cm^2/s (multiply by CM2_PER_S_TO_M2_PER_S for m^2/s), or NaN if
    fewer than three valid points are available.
    """
    q = np.asarray(q_norms, dtype=float)
    gamma_meV = np.asarray(gamma_meV, dtype=float)
    valid = (~np.isnan(q)) & (~np.isnan(gamma_meV)) & (q < q_max_fit) & (q > 0)

    if np.sum(valid) < 3:
        return np.nan

    q2 = q[valid] ** 2
    g = gamma_meV[valid]
    slope = np.polyfit(q2, g, 1)[0]  # meV * Angstrom^2

    d_a2_per_ps = slope / HBAR_MEV_PS
    return d_a2_per_ps * A2_PER_PS_TO_CM2_PER_S


def main():
    parser = argparse.ArgumentParser(description="Extract Gamma(q) from F_incoh")
    parser.add_argument("npz", help="Path to _sqw_arrays.npz")
    args = parser.parse_args()

    q, gamma, gamma_err = extract_linewidths(args.npz)
    d_cm2 = fit_diffusion_coefficient(q, gamma)

    print(f"D = {d_cm2:.3e} cm^2/s = {d_cm2 * CM2_PER_S_TO_M2_PER_S:.3e} m^2/s")


if __name__ == "__main__":
    main()
