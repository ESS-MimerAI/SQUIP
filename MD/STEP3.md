# Step 3: S(q,w) Calculation with Dynasor (MDAnalysis Reader) - Implementation Plan

## Overview
This document provides a revised implementation plan for Step 3: S(q,w) calculation. It uses the MDAnalysis reader only and addresses prior consistency issues with trajectory input, units, fixed-box handling, and q units. The goal is to compute dynamic structure factors S(q,w) from production trajectories generated in Step 2 using Dynasor, enabling direct comparison with experimental QENS data.

Timeline: Week 3-4
Input: 8 production trajectories from Step 2 (20 ns each, 30 fs resolution)
Output: S(q,w) datasets, intermediate scattering functions F(q,t), linewidth analysis Gamma(q), and comparison-ready spectra for all 8 systems

---

## Prerequisites

### Completed Systems from Step 2

| System | Force Field | Water Model | Temperature | Trajectory | Status |
|--------|-------------|-------------|-------------|------------|--------|
| Glycine | AMBER99SB-ILDN | TIP4P-Ew | 300 K | 20 ns @ 30 fs | Ready |
| Glycine | AMBER99SB-ILDN | TIP4P-Ew | 350 K | 20 ns @ 30 fs | Ready |
| Glycine | CHARMM27 | TIP3P | 300 K | 20 ns @ 30 fs | Ready |
| Glycine | CHARMM27 | TIP3P | 350 K | 20 ns @ 30 fs | Ready |
| Gly-Gly | AMBER99SB-ILDN | TIP4P-Ew | 300 K | 20 ns @ 30 fs | Ready |
| Gly-Gly | AMBER99SB-ILDN | TIP4P-Ew | 350 K | 20 ns @ 30 fs | Ready |
| Gly-Gly | CHARMM27 | TIP3P | 300 K | 20 ns @ 30 fs | Ready |
| Gly-Gly | CHARMM27 | TIP3P | 350 K | 20 ns @ 30 fs | Ready |

### Input Files Required (per system)

- systems/{molecule}/{forcefield}/{temp}K/production/prod.tpr
- systems/{molecule}/{forcefield}/{temp}K/production/prod_center.xtc
- Optional fixed-box trajectory if reimaged: prod_nvt_fixed.xtc

---

## Key Concepts for QENS Analysis

### Why Dynasor
Dynasor computes total and partial dynamic structure factors S(q,w) and intermediate scattering functions F(q,t) directly from MD trajectories. It supports:

- Coherent and incoherent dynamic structure factors
- Multi-component systems with partial correlation functions
- Spherical q-point averaging
- Neutron scattering length weighting
- MDAnalysis-based trajectory reading

### Constant-Volume Trajectories
Dynasor assumes fixed cell geometry. NPT trajectories violate this assumption. There are two acceptable options:

1) Preferred: reimage to a fixed box and use that trajectory for analysis.
2) PoC-only: use NPT directly if box fluctuations are negligible and you explicitly accept the approximation.

This plan uses option 1 by default and keeps option 2 as a documented fallback.

### Units and q Conventions

- Dynasor internal length unit: Angstrom
- Dynasor internal time unit: fs
- q points returned by Dynasor are in rad/Angstrom (include 2*pi)
- If you need q in 1/Angstrom for diffusion fits, use q_Ainv = q_rad_per_A / (2*pi)

---

## Substep 3.1: Install Dynasor and Dependencies

### Objective
Set up the Python environment with Dynasor and required analysis libraries.

### Steps

1) Install Dynasor (pip recommended)

```bash
pip install dynasor
```

2) Install dependencies

```bash
pip install MDAnalysis h5py scipy matplotlib
```

3) Verify installation

```python
import dynasor
import MDAnalysis as mda
print(dynasor.__version__)
print(mda.__version__)
```

---

## Substep 3.2: Prepare Trajectories for Dynasor

### Objective
Create a fixed-box trajectory and build element-based groups using MDAnalysis. This avoids reliance on GROMACS NDX parsing.

### Step A: Build a Fixed-Box Trajectory (Preferred)

1) Extract the box from the first frame (or compute an average box) using MDAnalysis:

```python
# scripts/get_box_from_first_frame.py
import MDAnalysis as mda

u = mda.Universe(
    'systems/glycine/amber99sb/300K/production/prod.tpr',
    'systems/glycine/amber99sb/300K/production/prod_center.xtc'
)

u.trajectory[0]
Lx, Ly, Lz = u.trajectory.ts.dimensions[:3]  # Angstrom
print(f"{Lx/10:.6f} {Ly/10:.6f} {Lz/10:.6f}")  # print in nm
```

## RESULT: 5.359701 5.359701 5.359701


2) Reimage and fix the box using GROMACS (PowerShell-friendly):

```bash
# Replace Lx Ly Lz with values printed above (in nm)
0 | gmx trjconv -f prod_center.xtc -s prod.tpr -o prod_nvt_fixed.xtc -pbc mol -ur compact -box Lx Ly Lz
```

Note: If you choose the average box instead of first-frame, compute Lx, Ly, Lz as the mean over frames and use those values.

### Step B: Build Element Groups with MDAnalysis

Dynasor needs particle type groups. We build them in Python to keep it MDAnalysis-only and reproducible on Windows.

```python
# scripts/build_element_groups.py
import MDAnalysis as mda

WATER_RESNAMES = {"SOL", "WAT", "HOH", "TIP3", "TIP3P", "TIP4", "TIP4P", "T4E"}


def guess_element(atom):
    # Use MDAnalysis element when available; fallback to first letter of name
    if atom.element:
        return atom.element.capitalize()
    return atom.name[0].upper()


def build_element_groups(tpr_path, xtc_path):
    u = mda.Universe(tpr_path, xtc_path)
    groups = {}
    for atom in u.atoms:
        elem = guess_element(atom)
        groups.setdefault(elem, []).append(atom.index)  # 0-based indices
    return groups
```

You will use this function directly in the analysis script, so no intermediate file is required.

### Deliverables (per system)

- prod_nvt_fixed.xtc (preferred)
- Element groups built on the fly from MDAnalysis (no NDX required)

---

## Substep 3.3: Compute Dynamic Structure Factors

### Objective
Calculate S(q,w) and F(q,t) for all 8 systems using Dynasor with the MDAnalysis reader.

### Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| q_max | 2.5 rad/Angstrom | Covers QENS range 0.3 to 2.0 1/Angstrom with margin |
| max_points | 5000 | Sufficient q-point sampling for spherical average |
| window_size | 2000 | 60 ps time window -> about 0.07 meV resolution |
| window_step | 200 | Step windows by 6 ps for good statistics |
| calculate_incoherent | True | Required for QENS (H dominates) |

### Implementation: compute_sqw.py

```python
#!/usr/bin/env python3
"""
compute_sqw.py - Compute S(q,w) using Dynasor with the MDAnalysis reader.

Usage:
    python scripts/compute_sqw.py <molecule> <forcefield> <temperature>

Example:
    python scripts/compute_sqw.py glycine amber99sb 300K
"""

import os
import sys
import numpy as np
import logging
import MDAnalysis as mda

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def compute_sqw_for_system(molecule, forcefield, temperature,
                           q_max=2.5, max_q_points=5000,
                           window_size=2000, window_step=200,
                           frame_step=1, frame_stop=None,
                           use_fixed_box=True, output_dir=None):
    base = os.path.join('systems', molecule, forcefield, temperature, 'production')
    tpr_file = os.path.join(base, 'prod.tpr')
    xtc_file = os.path.join(base, 'prod_nvt_fixed.xtc' if use_fixed_box else 'prod_center.xtc')

    if output_dir is None:
        output_dir = os.path.join(base, 'analysis')
    os.makedirs(output_dir, exist_ok=True)

    for f in [tpr_file, xtc_file]:
        if not os.path.exists(f):
            raise FileNotFoundError(f"Required file not found: {f}")

    logger.info(f"Processing {molecule}/{forcefield}/{temperature}")
    logger.info(f"  TPR: {tpr_file}")
    logger.info(f"  XTC: {xtc_file}")

    # MDAnalysis read for dt and element groups
    u = mda.Universe(tpr_file, xtc_file)
    element_groups = build_element_groups(u)

    # dt is the time between consecutive frames in the *original*
    # trajectory.  Do NOT multiply by frame_step — Dynasor handles
    # that internally (delta_t = traj.frame_step * dt).
    dt_ps = u.trajectory.dt
    dt_fs = dt_ps * 1000.0

    # Dynasor's built-in Trajectory class cannot load GROMACS
    # .tpr + .xtc pairs (its MDAnalysis reader only accepts a single
    # filename).  GROMACSTrajectory is a thin MDAnalysis wrapper that
    # exposes the same duck-typed interface Dynasor expects.
    traj = GROMACSTrajectory(
        topology=tpr_file,
        trajectory=xtc_file,
        atomic_indices=element_groups,
        frame_step=frame_step,
        frame_stop=frame_stop,
    )

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
    logger.info(f"    Frequency resolution: {2 * np.pi / (window_size * dt_fs) * radians_per_fs_to_meV:.4f} meV")
    logger.info(f"    Nyquist frequency: {np.pi / dt_fs * radians_per_fs_to_meV:.1f} meV")

    sample_raw = compute_dynamic_structure_factors(
        traj,
        q_points=q_points,
        dt=dt_fs,
        window_size=window_size,
        window_step=window_step,
        calculate_incoherent=True,
    )

    num_q_bins = 30
    sample_averaged = get_spherically_averaged_sample_binned(sample_raw, num_q_bins=num_q_bins)

    atom_types_in_sample = list(sample_raw.particle_counts.keys())
    neutron_weights = NeutronScatteringLengths(atom_types_in_sample)
    sample_neutron = get_weighted_sample(sample_averaged, neutron_weights)

    omega_meV = sample_averaged.omega * radians_per_fs_to_meV

    prefix = f"{molecule}_{forcefield}_{temperature}"
    sample_raw.write_to_npz(os.path.join(output_dir, f"{prefix}_sqw_raw.npz"))
    sample_averaged.write_to_npz(os.path.join(output_dir, f"{prefix}_sqw_averaged.npz"))
    sample_neutron.write_to_npz(os.path.join(output_dir, f"{prefix}_sqw_neutron.npz"))

    np.savez(
        os.path.join(output_dir, f"{prefix}_sqw_arrays.npz"),
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
    return sample_averaged


def main():
    if len(sys.argv) == 4:
        compute_sqw_for_system(sys.argv[1], sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 1:
        for mol in ['glycine', 'glygly']:
            for ff in ['amber99sb', 'charmm27']:
                for temp in ['300K', '350K']:
                    try:
                        compute_sqw_for_system(mol, ff, temp)
                    except Exception as exc:
                        logger.error(f"Failed {mol}/{ff}/{temp}: {exc}")
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
```

### Run a Quick Test

```bash
python scripts/compute_sqw.py glycine amber99sb 300K
```

### Run All Systems (sequential)

```bash
python scripts/compute_sqw.py
```

If you want parallelism on Windows, use Python multiprocessing or a task runner. Avoid GNU parallel.

---

## Substep 3.4: Validate S(q,w) Results

### Objective
Verify that computed S(q,w) are physically reasonable and numerically stable.

### Validation Checks (key additions)

- Symmetry: S(q,w) should be approximately symmetric in w for coherent part (within noise).
- Normalization: F_incoh(q, t=0) ~ 1 for self-part.
- Non-negativity: Small negative noise is acceptable; large negative values are not.

---

## Substep 3.5: Extract Quasielastic Linewidths Gamma(q)

### Objective
Fit F_incoh(q,t) to extract Gamma(q) and estimate diffusion coefficients.

### Critical Fix: q Units
Dynasor returns q in rad/Angstrom. Convert to 1/Angstrom before using Gamma(q) = D * q^2.

### Implementation Notes

```python
q_rad_per_A = q_norms
q_Ainv = q_rad_per_A / (2 * np.pi)
q2 = q_Ainv ** 2
```

Then fit Gamma vs q2 and convert units carefully as before.

---

## Substep 3.6: Visualization

Same plot logic as the original plan, but keep axis labels explicit about q units (rad/Angstrom).

---

## Substep 3.7: Neutron Weighting and Solute-Only Signals

### Objective
Apply neutron weighting and optionally isolate solute hydrogen contributions.

### Solute-Only Selection (MDAnalysis)

```python
solute_sel = "not resname SOL WAT HOH TIP3 TIP3P TIP4 TIP4P T4E"
solute_h_sel = f"({solute_sel}) and name H*"
```

Use the selection to build element groups restricted to solute atoms. This avoids undefined helper functions and keeps everything MDAnalysis-based.

---

## Substep 3.8: Master Analysis Script

Update the orchestration script to:

- Use prod_nvt_fixed.xtc by default
- Respect frame_step in dt
- Avoid non-Windows tools for parallelism

---

## Expected Outputs

Per system:

- analysis/{prefix}_sqw_raw.npz
- analysis/{prefix}_sqw_averaged.npz
- analysis/{prefix}_sqw_neutron.npz
- analysis/{prefix}_sqw_arrays.npz
- analysis/{prefix}_sqw.h5

Global:

- analysis/plots/
- step3_analysis.log
- Diffusion coefficient summary

---

## Troubleshooting

1) NPT trajectory not supported
- Use prod_nvt_fixed.xtc (fixed box). Do not use prod_center.xtc for final results.

2) Memory errors
- Use frame_step to subsample. dt should always be the *original* interval between consecutive trajectory frames (e.g. 30 fs). Dynasor handles subsampling internally via delta_t = traj.frame_step * dt.

3) Atom type mapping errors
- Build element groups via MDAnalysis as shown. Do not rely on NDX parsing.

4) Negative S(q,w)
- Increase window_size or apply windowing. Small negative values near zero are acceptable.

---

## Notes

- QENS is dominated by incoherent H scattering; always compute incoherent part.
- q points are in rad/Angstrom; convert to 1/Angstrom for diffusion fits.
- If you must use NPT trajectories for PoC, document the approximation explicitly.

---

## Next Steps

- Step 4: Experimental comparison (resolution convolution, q-grid match)
- Step 5: Database schema and HDF5 integration
