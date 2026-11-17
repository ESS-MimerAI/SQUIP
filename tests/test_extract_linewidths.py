#!/usr/bin/env python3
"""
Unit test for the diffusion-coefficient fit in extract_linewidths.py.

Builds a synthetic Fickian linewidth curve Gamma_E(q) = hbar * D * q^2 with
q given exactly as Dynasor returns it (angular wavevector in 1/Angstrom, no
2*pi conversion) and checks that fit_diffusion_coefficient recovers D.

With D = 0.1 Angstrom^2/ps the expected result is
    D = 1.0e-5 cm^2/s = 1.0e-9 m^2/s.
The old implementation divided q by 2*pi before fitting and would have
returned a value (2*pi)^2 ~ 39.5 times too large; this test guards against
that regression.

Usage:
    python -m pytest tests/test_extract_linewidths.py      (from the repository root)
"""

import os
import sys
import numpy as np

# Make the S(q,w) modules in scripts/sqw importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "sqw"))

from extract_linewidths import (
    fit_diffusion_coefficient,
    HBAR_MEV_PS,
    CM2_PER_S_TO_M2_PER_S,
)

Q_AINV = np.array([0.1, 0.2, 0.3, 0.4, 0.5])  # 1/Angstrom, Dynasor convention
D_A2_PER_PS = 0.1                              # Angstrom^2/ps
D_EXPECTED_CM2_PER_S = 1.0e-5
D_EXPECTED_M2_PER_S = 1.0e-9
RTOL = 1e-9


def _synthetic_gamma_meV(q, d_a2_per_ps=D_A2_PER_PS):
    """Gamma_E = hbar * D * q^2 in meV."""
    return HBAR_MEV_PS * d_a2_per_ps * q ** 2


# ---------------------------------------------------------------
# Test 1: D is recovered from a synthetic Gamma(q) with q in 1/Angstrom
# ---------------------------------------------------------------
def test_fit_recovers_synthetic_diffusion_coefficient():
    gamma_meV = _synthetic_gamma_meV(Q_AINV)

    d_cm2_per_s = fit_diffusion_coefficient(Q_AINV, gamma_meV)
    d_m2_per_s = d_cm2_per_s * CM2_PER_S_TO_M2_PER_S

    assert np.isclose(d_cm2_per_s, D_EXPECTED_CM2_PER_S, rtol=RTOL, atol=0.0), (
        f"D = {d_cm2_per_s:.6e} cm^2/s, expected {D_EXPECTED_CM2_PER_S:.1e} "
        f"(ratio {d_cm2_per_s / D_EXPECTED_CM2_PER_S:.4f}; (2*pi)^2 = "
        f"{(2 * np.pi) ** 2:.4f} would indicate the old 2*pi division)"
    )
    assert np.isclose(d_m2_per_s, D_EXPECTED_M2_PER_S, rtol=RTOL, atol=0.0), (
        f"D = {d_m2_per_s:.6e} m^2/s, expected {D_EXPECTED_M2_PER_S:.1e}"
    )
    print("PASS  test_fit_recovers_synthetic_diffusion_coefficient")


# ---------------------------------------------------------------
# Test 2: the q_max_fit cutoff is applied to the un-divided q
# ---------------------------------------------------------------
def test_q_max_fit_cutoff_uses_undivided_q():
    # Add a point just above the default cutoff with a wildly wrong linewidth.
    # Under the old (q / 2*pi) convention q = 1.2 would have passed the
    # q < 1.0 cutoff and corrupted the fit.
    q = np.append(Q_AINV, 1.2)
    gamma_meV = np.append(_synthetic_gamma_meV(Q_AINV), 100.0)

    d_cm2_per_s = fit_diffusion_coefficient(q, gamma_meV, q_max_fit=1.0)

    assert np.isclose(d_cm2_per_s, D_EXPECTED_CM2_PER_S, rtol=RTOL, atol=0.0), (
        f"D = {d_cm2_per_s:.6e} cm^2/s, expected {D_EXPECTED_CM2_PER_S:.1e}; "
        f"point at q = 1.2 1/Angstrom should have been excluded"
    )
    print("PASS  test_q_max_fit_cutoff_uses_undivided_q")


# ---------------------------------------------------------------
# Test 3: NaN handling and too-few-points guard
# ---------------------------------------------------------------
def test_nan_points_are_ignored_and_too_few_points_gives_nan():
    q = np.append(Q_AINV, np.nan)
    gamma_meV = np.append(_synthetic_gamma_meV(Q_AINV), np.nan)
    d_cm2_per_s = fit_diffusion_coefficient(q, gamma_meV)
    assert np.isclose(d_cm2_per_s, D_EXPECTED_CM2_PER_S, rtol=RTOL, atol=0.0)

    d_few = fit_diffusion_coefficient(Q_AINV[:2], _synthetic_gamma_meV(Q_AINV[:2]))
    assert np.isnan(d_few), f"expected NaN for < 3 points, got {d_few}"
    print("PASS  test_nan_points_are_ignored_and_too_few_points_gives_nan")


if __name__ == "__main__":
    test_fit_recovers_synthetic_diffusion_coefficient()
    test_q_max_fit_cutoff_uses_undivided_q()
    test_nan_points_are_ignored_and_too_few_points_gives_nan()
    print("\nAll tests passed.")
