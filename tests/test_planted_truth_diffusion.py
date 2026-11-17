#!/usr/bin/env python3
"""
Planted-truth gate for the self-diffusion pipeline (end to end).

The pipeline under test is the production route

    trajectory  ->  GROMACSTrajectory  ->  compute_sqw.compute_and_save_sqw
                ->  *_sqw_arrays.npz    ->  validate_sqw.validate_sqw
                ->  extract_linewidths.extract_linewidths
                ->  extract_linewidths.fit_diffusion_coefficient  ->  D

Nothing in that chain has a known right answer when fed real MD data, so
this test feeds it an input whose answer is known exactly: non-interacting
Brownian particles in a fixed cubic box with a planted D.  For free
diffusion the self-intermediate scattering function is analytic,

    F_incoh(q, t) = exp(-D q^2 t),

so the pipeline must return the planted D.  The gate is "recovered D within
10 % of planted D".

A positive control proves the gate can fail: the same npz with q_norms
rescaled by 2*pi (exactly the historical (2*pi)^2 unit error in
extract_linewidths.py) must trip the gate.  A control that cannot fail
tests nothing.

Units
-----
Dynasor q_norms are the angular wavevector |q| = 2*pi/lambda in 1/Angstrom
(the Dynasor docs write this as rad/Angstrom); Fickian linewidth
Gamma_E = hbar * D * q^2.  Lengths in Angstrom, times in fs inside Dynasor;
extract_linewidths works in ps and reports D in cm^2/s.

Runtime is about 20-30 s (dominated by Dynasor).

Usage:
    python -m pytest tests/test_planted_truth_diffusion.py -v      (from the repository root)
"""

import contextlib
import io
import os
import sys

import numpy as np
import pytest
import MDAnalysis as mda

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts", "sqw"))

from build_element_groups import build_element_groups  # noqa: E402
from gromacs_trajectory import GROMACSTrajectory  # noqa: E402
from compute_sqw import compute_and_save_sqw  # noqa: E402
from validate_sqw import validate_sqw  # noqa: E402
from extract_linewidths import (  # noqa: E402
    extract_linewidths,
    fit_diffusion_coefficient,
    HBAR_MEV_PS,
)

# ---------------------------------------------------------------------------
# Planted truth
# ---------------------------------------------------------------------------
D_PLANTED_CM2_PER_S = 2.0e-5          # water-like self-diffusion at ~300 K
CM2_PER_S_TO_A2_PER_FS = 10.0         # 1 cm^2/s = 1e16 A^2/s = 10 A^2/fs
D_PLANTED_A2_PER_FS = D_PLANTED_CM2_PER_S * CM2_PER_S_TO_A2_PER_FS  # 2.0e-4
D_PLANTED_A2_PER_PS = D_PLANTED_A2_PER_FS * 1000.0                   # 0.2
GATE_TOLERANCE = 0.10                 # relative

# ---------------------------------------------------------------------------
# Synthetic trajectory and analysis settings (kept small for runtime)
# ---------------------------------------------------------------------------
N_PARTICLES = 500
BOX_A = 40.0                          # Angstrom, fixed cubic cell
DT_FS = 100.0                         # frame spacing
N_FRAMES = 600                        # 60 ps of trajectory
WINDOW_SIZE = 300                     # 30 ps correlation window (matches the
                                      # 0.1-30 ps fit range in extract_linewidths)
WINDOW_STEP = 75
Q_MAX = 1.2                           # 1/Angstrom; fit uses q < 1.0
MAX_Q_POINTS = 300
NUM_Q_BINS = 12
SEED = 20261014

PREFIX = "planted_brownian_300K"


# ---------------------------------------------------------------------------
# Synthetic input: free Brownian particles written as .gro + .xtc
# ---------------------------------------------------------------------------
def _write_gro(path, positions_a, box_a):
    """Minimal .gro (nm units) with one 'H' atom per particle."""
    n = len(positions_a)
    lines = ["Planted-truth Brownian particles", f"{n:5d}"]
    for i, (x, y, z) in enumerate(positions_a / 10.0):
        k = i % 99999 + 1
        lines.append(f"{k:5d}{'BRW':<5s}{'H':>5s}{k:5d}{x:8.3f}{y:8.3f}{z:8.3f}")
    b = box_a / 10.0
    lines.append(f"  {b:.5f}  {b:.5f}  {b:.5f}")
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


def write_brownian_trajectory(gro_path, xtc_path, d_a2_per_fs, n_particles,
                              box_a, dt_fs, n_frames, seed):
    """Independent Gaussian random walks, wrapped into a fixed cubic box.

    Per-frame displacement per Cartesian component ~ N(0, 2 D dt).  Wrapping
    is harmless for Dynasor because its q-points lie on the reciprocal
    lattice, so exp(i q . L) = 1 for any box-vector jump.
    """
    rng = np.random.default_rng(seed)
    pos = rng.uniform(0.0, box_a, size=(n_particles, 3))
    _write_gro(gro_path, pos, box_a)

    sigma = np.sqrt(2.0 * d_a2_per_fs * dt_fs)
    u = mda.Universe(gro_path)
    try:
        with mda.Writer(xtc_path, n_atoms=n_particles) as w:
            for frame in range(n_frames):
                if frame:
                    pos += rng.normal(0.0, sigma, size=pos.shape)
                u.atoms.positions = pos % box_a
                u.trajectory.ts.time = frame * dt_fs / 1000.0  # ps
                w.write(u.atoms)
    finally:
        u.trajectory.close()


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------
def run_diffusion_gate(npz_path):
    """Run validate_sqw + extract_linewidths + fit on an npz; return D (cm^2/s).

    Also returns the per-bin q and linewidths so a failure message can show them.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        validate_sqw(npz_path, os.path.basename(npz_path))
    report = buf.getvalue()
    assert "q-range (rad/Angstrom)" in report, f"validate_sqw produced no report:\n{report}"

    q, gamma_meV, gamma_err = extract_linewidths(npz_path)
    d_cm2 = fit_diffusion_coefficient(q, gamma_meV)
    return d_cm2, q, gamma_meV


def assert_gate_passes(d_cm2, q=None, gamma_meV=None):
    detail = ""
    if q is not None:
        detail = (
            "\n  q (1/A)         : " + np.array2string(q, precision=3)
            + "\n  Gamma/hbar (1/ps): " + np.array2string(gamma_meV / HBAR_MEV_PS, precision=4)
            + "\n  planted D q^2    : " + np.array2string(D_PLANTED_A2_PER_PS * q ** 2, precision=4)
        )
    assert np.isfinite(d_cm2), f"recovered D is not finite: {d_cm2!r}{detail}"
    ratio = d_cm2 / D_PLANTED_CM2_PER_S
    assert abs(ratio - 1.0) <= GATE_TOLERANCE, (
        f"planted-truth gate FAILED: recovered D = {d_cm2:.3e} cm^2/s, "
        f"planted D = {D_PLANTED_CM2_PER_S:.3e} cm^2/s, ratio = {ratio:.3f} "
        f"(tolerance {GATE_TOLERANCE:.0%}; (2*pi)^2 = {(2 * np.pi) ** 2:.2f} "
        f"would indicate a q/2*pi unit error){detail}"
    )


# ---------------------------------------------------------------------------
# Fixture: run the production compute stage once on the synthetic input
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def planted_npz(tmp_path_factory):
    work = tmp_path_factory.mktemp("planted_truth")
    gro = str(work / "brownian.gro")
    xtc = str(work / "brownian.xtc")
    write_brownian_trajectory(
        gro, xtc, D_PLANTED_A2_PER_FS, N_PARTICLES, BOX_A, DT_FS, N_FRAMES, SEED
    )

    u = mda.Universe(gro, xtc)
    try:
        element_groups = build_element_groups(u)
    finally:
        u.trajectory.close()
    assert list(element_groups) == ["H"], element_groups
    assert len(element_groups["H"]) == N_PARTICLES

    traj = GROMACSTrajectory(
        topology=gro,
        trajectory=xtc,
        atomic_indices=element_groups,
        frame_step=1,
    )
    try:
        assert np.allclose(traj.cell, np.eye(3) * BOX_A), traj.cell
        _, arrays_path = compute_and_save_sqw(
            traj,
            DT_FS,
            PREFIX,
            str(work / "analysis"),
            q_max=Q_MAX,
            max_q_points=MAX_Q_POINTS,
            window_size=WINDOW_SIZE,
            window_step=WINDOW_STEP,
            num_q_bins=NUM_Q_BINS,
        )
    finally:
        traj._universe.trajectory.close()

    assert arrays_path.endswith(f"{PREFIX}_sqw_arrays.npz")
    return arrays_path


# ---------------------------------------------------------------------------
# Test 1: the npz has the production layout and F_incoh matches exp(-D q^2 t)
# ---------------------------------------------------------------------------
def test_compute_stage_reproduces_analytic_f_incoh(planted_npz):
    data = np.load(planted_npz)
    expected_keys = {
        "q_norms", "omega_rad_per_fs", "omega_meV", "time_fs",
        "Sqw_coh", "Sqw_incoh", "Fqt_coh", "Fqt_incoh",
    }
    assert expected_keys <= set(data.files), sorted(data.files)

    q = data["q_norms"]
    t_fs = data["time_fs"]
    f_incoh = data["Fqt_incoh"]
    assert f_incoh.shape == (len(q), len(t_fs))
    assert np.isclose(t_fs[1] - t_fs[0], DT_FS)
    # Dynasor returns lags 0..window_size inclusive (maximum_time_lag = dt * window_size).
    assert len(t_fs) == WINDOW_SIZE + 1
    assert np.isclose(t_fs[-1], WINDOW_SIZE * DT_FS)

    valid = ~np.isnan(q)
    # Self part is normalised per particle: F_incoh(q, 0) == 1 exactly.
    assert np.allclose(f_incoh[valid, 0], 1.0, atol=1e-6), f_incoh[valid, 0]

    # Point-wise planted truth at every bin that enters the diffusion fit.
    #
    # Dynasor labels each spherical bin by its bin CENTRE (q_norms), not by
    # the mean |q| of the reciprocal-lattice points it holds.  In sparsely
    # populated low-q bins the two differ (first bin here: label 0.108 1/A,
    # only shell present at 2*pi/40 = 0.157 1/A), which would show up as a
    # 0.07 deviation that is not the compute stage's fault.  So the analytic
    # curve is built from the actual q-points in each bin, read back from the
    # *_sqw_raw.npz that compute_and_save_sqw writes beside the arrays file.
    # The diffusion fit itself works from the labels; the few percent that
    # costs is averaged down by the linear fit over many bins and sits well
    # inside the 10 % gate (see test 2).
    raw = np.load(planted_npz.replace("_sqw_arrays.npz", "_sqw_raw.npz"), allow_pickle=True)
    q_points = np.asarray(raw["data_dict"].item()["q_points"])
    q_pt_norm = np.linalg.norm(q_points, axis=1)
    half_width = 0.5 * (q[1] - q[0])

    worst = 0.0
    for iq in np.flatnonzero(valid & (q > 0) & (q < 1.0)):
        in_bin = (q_pt_norm >= q[iq] - half_width) & (q_pt_norm < q[iq] + half_width)
        assert in_bin.any(), f"no raw q-points found for bin labelled {q[iq]:.3f} 1/A"
        analytic = np.exp(
            -D_PLANTED_A2_PER_FS * q_pt_norm[in_bin, None] ** 2 * t_fs[None, :]
        ).mean(axis=0)
        worst = max(worst, float(np.max(np.abs(f_incoh[iq] - analytic))))
    assert worst < 0.03, (
        f"F_incoh deviates from the bin average of exp(-D q^2 t) by up to {worst:.3f} "
        f"(statistical noise for {N_PARTICLES} particles should keep this < 0.03)"
    )


# ---------------------------------------------------------------------------
# Test 2: THE GATE - the full route recovers the planted D
# ---------------------------------------------------------------------------
def test_pipeline_recovers_planted_diffusion_coefficient(planted_npz):
    d_cm2, q, gamma_meV = run_diffusion_gate(planted_npz)
    print(
        f"\nplanted D = {D_PLANTED_CM2_PER_S:.3e} cm^2/s, "
        f"recovered D = {d_cm2:.3e} cm^2/s, ratio = {d_cm2 / D_PLANTED_CM2_PER_S:.4f}"
    )
    assert_gate_passes(d_cm2, q, gamma_meV)


# ---------------------------------------------------------------------------
# Test 3: POSITIVE CONTROL - the gate must fail when q is rescaled by 2*pi
# ---------------------------------------------------------------------------
def _corrupt_q(npz_path, factor, tag):
    data = dict(np.load(npz_path))
    data["q_norms"] = data["q_norms"] * factor
    out = os.path.join(os.path.dirname(npz_path), f"{PREFIX}_{tag}_sqw_arrays.npz")
    np.savez(out, **data)
    return out


@pytest.mark.parametrize(
    "factor, tag",
    [
        pytest.param(1.0 / (2.0 * np.pi), "q_over_2pi", id="q/2pi (historical bug)"),
        pytest.param(2.0 * np.pi, "q_times_2pi", id="q*2pi"),
    ],
)
def test_positive_control_q_rescaled_by_2pi_fails_gate(planted_npz, factor, tag):
    corrupted = _corrupt_q(planted_npz, factor, tag)
    d_cm2, q, gamma_meV = run_diffusion_gate(corrupted)
    ratio = d_cm2 / D_PLANTED_CM2_PER_S
    print(f"\n[{tag}] recovered D = {d_cm2:.3e} cm^2/s, ratio to planted = {ratio:.3f}")

    with pytest.raises(AssertionError, match="planted-truth gate FAILED|not finite"):
        assert_gate_passes(d_cm2, q, gamma_meV)

    if factor < 1.0:
        # Dividing q by 2*pi is exactly the old extract_linewidths bug: D must
        # come out inflated by ~(2*pi)^2 = 39.5 (modulo the gate's own ~5 %
        # bias), proving the control fails for the right reason.
        assert np.isfinite(d_cm2)
        assert abs(ratio / (2.0 * np.pi) ** 2 - 1.0) < 0.25, ratio


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "-s"]))
