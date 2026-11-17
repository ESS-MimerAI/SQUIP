"""SQUIP MD simulation tasks for TaskBlaster.

Each task function is called by TaskBlaster in its own working directory
under ``tree/<task_name>/``.  Tasks communicate via return values (dicts
of absolute path strings for file-producing tasks).  GROMACS commands are
run via subprocess; the force-field include paths in the topology are
rewritten to absolute paths so that ``gmx grompp`` works from any CWD.
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("squip_tasks")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_gmx():
    """Locate the GROMACS ``gmx`` executable."""
    import shutil
    gmx = shutil.which("gmx")
    if gmx:
        return gmx
    # Common Windows installation paths
    for candidate in [
        r"C:\util\gromacs\bin\gmx.exe",
        r"C:\Program Files\GROMACS\bin\gmx.exe",
    ]:
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(
        "Cannot find GROMACS 'gmx' executable. "
        "Make sure it is on PATH or installed in a standard location."
    )


_GMX = None  # cached path

def _gmx():
    global _GMX
    if _GMX is None:
        _GMX = _find_gmx()
    return _GMX


def _run_gmx(args, input_text=None):
    """Run a GROMACS command in the current working directory."""
    cmd = [_gmx()] + [str(a) for a in args]
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        input=input_text,
        text=True,
        capture_output=True,
    )
    if result.stdout:
        logger.debug("STDOUT:\n%s", result.stdout[-2000:])
    if result.returncode != 0:
        raise RuntimeError(
            f"GROMACS failed (rc={result.returncode}): gmx {' '.join(args)}\n"
            f"STDERR (last 3000 chars):\n{result.stderr[-3000:]}"
        )
    return result


def _write_file(path, content):
    with open(path, "w") as fh:
        fh.write(content)


def _fix_topology_includes(top_file, ff_abs_dir):
    """Rewrite ``#include "./amber99sb-ildn.ff/…"`` to absolute paths."""
    abs_ff = ff_abs_dir.replace("\\", "/")
    with open(top_file) as fh:
        content = fh.read()
    content = content.replace("./amber99sb-ildn.ff/", abs_ff + "/")
    content = content.replace('"amber99sb-ildn.ff/', f'"{abs_ff}/')
    with open(top_file, "w") as fh:
        fh.write(content)


def _update_topology_mol_count(top_file, mol_name, count):
    """Update the molecule count in a GROMACS topology [ molecules ] section."""
    import re
    with open(top_file) as fh:
        content = fh.read()
    pattern = rf'^(\s*{re.escape(mol_name)}\s+)\d+'
    content = re.sub(pattern, rf'\g<1>{count}', content, flags=re.MULTILINE)
    with open(top_file, "w") as fh:
        fh.write(content)


_WATERMODELS_DAT = """\
spc     SPC simple point charge
spce    SPC/E extended simple point charge
tip3p   TIP3P TIP 3-point
tip4p   TIP4P TIP 4-point
tip4pew TIP4P-Ew TIP 4-point Ewald
tip5p   TIP5P TIP 5-point
"""

# ---------------------------------------------------------------------------
# Step 1 tasks
# ---------------------------------------------------------------------------

def prepare_system(project_root, molecule, forcefield, water_model, nmol, box_size):
    """Steps 1.1–1.4: topology, box, solvation.

    Returns dict with absolute paths *gro* and *top*.
    """
    cwd = os.getcwd()
    ff_src = os.path.join(project_root, "amber99sb-ildn.ff")

    # Copy force field so pdb2gmx finds it locally
    ff_dst = os.path.join(cwd, "amber99sb-ildn.ff")
    if os.path.exists(ff_dst):
        shutil.rmtree(ff_dst)
    shutil.copytree(ff_src, ff_dst)

    # Ensure watermodels.dat exists (needed for -water tip4pew)
    wm_path = os.path.join(ff_dst, "watermodels.dat")
    if not os.path.exists(wm_path):
        _write_file(wm_path, _WATERMODELS_DAT)

    # Determine input structure
    if molecule == "glycine":
        input_pdb = os.path.join(project_root, "inputs", "structures", "glycine_zw_amber.pdb")
    elif molecule == "glygly":
        input_pdb = os.path.join(project_root, "inputs", "structures", "glygly_zw_charmm.pdb")
    else:
        input_pdb = os.path.join(project_root, "inputs", "structures", f"{molecule}_zw_amber.pdb")

    if not os.path.isfile(input_pdb):
        raise FileNotFoundError(f"Input structure not found: {input_pdb}")

    # 1.2  Generate topology  (TIP4P-Ew via interactive water selection)
    # GROMACS 2021.5 -water enum doesn't include "tip4pew", so we use
    # -water select and pipe in the selection number from watermodels.dat
    # (tip4pew is typically entry 3 in the AMBER99SB-ILDN watermodels.dat)
    wm_dat = os.path.join(ff_dst, "watermodels.dat")
    water_idx = None
    with open(wm_dat) as f:
        for i, line in enumerate(f, 1):
            if line.strip().startswith("tip4pew"):
                water_idx = i
                break
    if water_idx is None:
        raise RuntimeError("tip4pew not found in watermodels.dat")
    _run_gmx([
        "pdb2gmx",
        "-f", input_pdb,
        "-o", "peptide.gro",
        "-p", "topol.top",
        "-ff", "amber99sb-ildn",
        "-water", "select",
    ], input_text=f"{water_idx}\n")

    # 1.3  Insert solute molecules into cubic box
    _run_gmx([
        "insert-molecules",
        "-ci", "peptide.gro",
        "-nmol", str(nmol),
        "-box", str(box_size), str(box_size), str(box_size),
        "-o", "box.gro",
    ])

    # insert-molecules doesn't update the topology molecule count
    _update_topology_mol_count("topol.top", "Other", nmol)

    # 1.4  Solvate with TIP4P water
    _run_gmx([
        "solvate",
        "-cp", "box.gro",
        "-cs", "tip4p",
        "-o", "solvated.gro",
        "-p", "topol.top",
    ])

    # Rewrite topology includes to absolute paths so downstream tasks work
    _fix_topology_includes("topol.top", ff_src)

    logger.info("System prepared: %d %s molecules in %.1f nm box", nmol, molecule, box_size)
    return {
        "gro": os.path.join(cwd, "solvated.gro"),
        "top": os.path.join(cwd, "topol.top"),
    }


def energy_minimize(system, project_root, test_mode):
    """Step 1.5: steepest-descent energy minimisation."""
    cwd = os.getcwd()
    nsteps = 5000 if test_mode else 50000

    _write_file("em.mdp", f"""\
; Energy minimization
integrator  = steep
nsteps      = {nsteps}
emtol       = 1000.0
emstep      = 0.01
nstxout     = 0
nstvout     = 0
nstenergy   = 500
nstlog      = 500
cutoff-scheme = Verlet
nstlist       = 10
rlist         = 1.2
coulombtype   = PME
rcoulomb      = 1.2
fourierspacing = 0.16
vdwtype       = Cut-off
rvdw          = 1.2
DispCorr      = EnerPres
pbc           = xyz
""")

    _run_gmx([
        "grompp",
        "-f", os.path.join(cwd, "em.mdp"),
        "-c", system["gro"],
        "-p", system["top"],
        "-o", os.path.join(cwd, "em.tpr"),
        "-maxwarn", "1",
    ])

    _run_gmx(["mdrun", "-v", "-deffnm", os.path.join(cwd, "em")])

    logger.info("Energy minimization complete")
    return {
        "gro": os.path.join(cwd, "em.gro"),
        "top": system["top"],
    }


def nvt_equilibrate(em_result, system, project_root, temperature, test_mode):
    """Step 1.6: NVT equilibration."""
    cwd = os.getcwd()
    nsteps = 5000 if test_mode else 50000

    _write_file("nvt.mdp", f"""\
; NVT equilibration at {temperature} K
integrator  = md
dt          = 0.002
nsteps      = {nsteps}
nstlog      = 500
nstenergy   = 500
nstxout-compressed = 500
cutoff-scheme = Verlet
nstlist     = 10
rlist       = 1.2
coulombtype = PME
rcoulomb    = 1.2
pme_order   = 4
fourierspacing = 0.12
vdwtype     = Cut-off
rvdw        = 1.2
DispCorr    = EnerPres
tcoupl      = V-rescale
tc-grps     = System
tau_t       = 0.1
ref_t       = {temperature}
pcoupl      = no
gen_vel     = yes
gen_temp    = {temperature}
gen_seed    = -1
pbc         = xyz
constraints = h-bonds
constraint_algorithm = LINCS
""")

    _run_gmx([
        "grompp",
        "-f", os.path.join(cwd, "nvt.mdp"),
        "-c", em_result["gro"],
        "-p", em_result["top"],
        "-o", os.path.join(cwd, "nvt.tpr"),
        "-maxwarn", "1",
    ])

    _run_gmx(["mdrun", "-v", "-deffnm", os.path.join(cwd, "nvt")])

    logger.info("NVT equilibration complete (T=%d K)", temperature)
    return {
        "gro": os.path.join(cwd, "nvt.gro"),
        "cpt": os.path.join(cwd, "nvt.cpt"),
        "top": em_result["top"],
    }


def npt_equilibrate(nvt_result, system, project_root, temperature, test_mode):
    """Step 1.7: NPT equilibration."""
    cwd = os.getcwd()
    nsteps = 5000 if test_mode else 50000

    _write_file("npt.mdp", f"""\
; NPT equilibration at {temperature} K, 1 bar
integrator  = md
dt          = 0.002
nsteps      = {nsteps}
nstlog      = 500
nstenergy   = 500
nstxout-compressed = 500
cutoff-scheme = Verlet
nstlist     = 10
rlist       = 1.2
coulombtype = PME
rcoulomb    = 1.2
pme_order   = 4
fourierspacing = 0.12
vdwtype     = Cut-off
rvdw        = 1.2
DispCorr    = EnerPres
tcoupl      = V-rescale
tc-grps     = System
tau_t       = 0.1
ref_t       = {temperature}
pcoupl      = Parrinello-Rahman
pcoupltype  = isotropic
tau_p       = 2.0
ref_p       = 1.0
compressibility = 4.5e-5
gen_vel     = no
pbc         = xyz
constraints = h-bonds
constraint_algorithm = LINCS
""")

    _run_gmx([
        "grompp",
        "-f", os.path.join(cwd, "npt.mdp"),
        "-c", nvt_result["gro"],
        "-t", nvt_result["cpt"],
        "-p", nvt_result["top"],
        "-o", os.path.join(cwd, "npt.tpr"),
        "-maxwarn", "1",
    ])

    _run_gmx(["mdrun", "-v", "-deffnm", os.path.join(cwd, "npt")])

    logger.info("NPT equilibration complete (T=%d K)", temperature)
    return {
        "gro": os.path.join(cwd, "npt.gro"),
        "cpt": os.path.join(cwd, "npt.cpt"),
        "tpr": os.path.join(cwd, "npt.tpr"),
        "top": nvt_result["top"],
    }


# ---------------------------------------------------------------------------
# Step 2 tasks
# ---------------------------------------------------------------------------

def production_md(npt_result, system, project_root, temperature, test_mode):
    """Step 2: production NPT MD with compressed trajectory output."""
    cwd = os.getcwd()
    nsteps = 5000 if test_mode else 10_000_000
    nstlog = 100 if test_mode else 5000
    nstenergy = 100 if test_mode else 5000

    _write_file("prod.mdp", f"""\
; Production MD at {temperature} K
integrator  = md
dt          = 0.002
nsteps      = {nsteps}
nstlog      = {nstlog}
nstenergy   = {nstenergy}
nstxout     = 0
nstvout     = 0
nstxout-compressed = 15
compressed-x-grps = System
cutoff-scheme = Verlet
nstlist     = 20
rlist       = 1.2
coulombtype = PME
rcoulomb    = 1.2
pme_order   = 4
fourierspacing = 0.12
vdwtype     = Cut-off
vdw-modifier = Potential-shift
rvdw        = 1.2
DispCorr    = EnerPres
tcoupl      = V-rescale
tc-grps     = System
tau_t       = 0.5
ref_t       = {temperature}
pcoupl      = Parrinello-Rahman
pcoupltype  = isotropic
tau_p       = 2.0
ref_p       = 1.0
compressibility = 4.5e-5
refcoord_scaling = com
gen_vel     = no
pbc         = xyz
constraints          = h-bonds
constraint_algorithm = LINCS
lincs_iter           = 2
lincs_order          = 4
comm-mode   = Linear
nstcomm     = 100
""")

    _run_gmx([
        "grompp",
        "-f", os.path.join(cwd, "prod.mdp"),
        "-c", npt_result["gro"],
        "-t", npt_result["cpt"],
        "-p", npt_result["top"],
        "-o", os.path.join(cwd, "prod.tpr"),
        "-maxwarn", "1",
    ])

    _run_gmx(["mdrun", "-v", "-deffnm", os.path.join(cwd, "prod")])

    logger.info("Production MD complete (%d steps)", nsteps)
    return {
        "gro": os.path.join(cwd, "prod.gro"),
        "xtc": os.path.join(cwd, "prod.xtc"),
        "tpr": os.path.join(cwd, "prod.tpr"),
        "cpt": os.path.join(cwd, "prod.cpt"),
        "edr": os.path.join(cwd, "prod.edr"),
        "top": npt_result["top"],
    }


def center_trajectory(prod_result, project_root):
    """Step 2 post-processing: centre trajectory (PBC mol)."""
    cwd = os.getcwd()
    out_xtc = os.path.join(cwd, "prod_center.xtc")

    #  "0\n0\n" selects System for both centering group and output group
    _run_gmx([
        "trjconv",
        "-f", prod_result["xtc"],
        "-s", prod_result["tpr"],
        "-o", out_xtc,
        "-pbc", "mol",
        "-center",
    ], input_text="0\n0\n")

    logger.info("Trajectory centred")
    return {
        "xtc": out_xtc,
        "tpr": prod_result["tpr"],
    }


# ---------------------------------------------------------------------------
# Step 3 tasks
# ---------------------------------------------------------------------------

def fix_box_trajectory(center_result, prod_result):
    """Step 3 prep: create fixed-box trajectory for Dynasor."""
    import MDAnalysis as mda

    cwd = os.getcwd()
    xtc_in = center_result["xtc"]
    tpr = center_result["tpr"]

    # Read box dimensions from the first frame (Angstrom → nm)
    u = mda.Universe(tpr, xtc_in)
    u.trajectory[0]
    dims = u.trajectory.ts.dimensions[:3]
    Lx, Ly, Lz = dims[0] / 10.0, dims[1] / 10.0, dims[2] / 10.0

    out_xtc = os.path.join(cwd, "prod_nvt_fixed.xtc")

    _run_gmx([
        "trjconv",
        "-f", xtc_in,
        "-s", tpr,
        "-o", out_xtc,
        "-pbc", "mol",
        "-ur", "compact",
        "-box", f"{Lx:.6f}", f"{Ly:.6f}", f"{Lz:.6f}",
    ], input_text="0\n")

    logger.info("Fixed-box trajectory created (box %.3f %.3f %.3f nm)", Lx, Ly, Lz)
    return {
        "xtc": out_xtc,
        "tpr": tpr,
        "box_nm": [float(Lx), float(Ly), float(Lz)],
    }


def compute_sqw(fixed_traj, prod_result, project_root,
                molecule, forcefield, temperature):
    """Step 3: compute S(q,w) with Dynasor (MDAnalysis reader)."""
    import sys
    import numpy as np
    import MDAnalysis as mda

    # Make project helper scripts importable
    for d in [
        os.path.join(project_root, "scripts", "sqw"),
    ]:
        if d not in sys.path:
            sys.path.insert(0, d)

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

    cwd = os.getcwd()
    tpr = fixed_traj["tpr"]
    xtc = fixed_traj["xtc"]

    # Build element groups (excluding virtual sites)
    u = mda.Universe(tpr, xtc)
    element_groups = build_element_groups(u)
    dt_fs = u.trajectory.dt * 1000.0  # ps → fs
    n_frames = len(u.trajectory)

    logger.info("Trajectory: %d frames, dt=%.1f fs", n_frames, dt_fs)

    # Dynasor trajectory wrapper
    traj = GROMACSTrajectory(
        topology=tpr,
        trajectory=xtc,
        atomic_indices=element_groups,
    )

    q_max = 2.5
    q_points = get_spherical_qpoints(traj.cell, q_max=q_max, max_points=2000)

    # Adapt window parameters to available frame count
    window_size = min(100, max(20, n_frames // 3))
    window_step = max(5, window_size // 5)
    logger.info(
        "S(q,w) params: window_size=%d, window_step=%d, q_points=%d",
        window_size, window_step, len(q_points),
    )

    sample_raw = compute_dynamic_structure_factors(
        traj,
        q_points=q_points,
        dt=dt_fs,
        window_size=window_size,
        window_step=window_step,
        calculate_incoherent=True,
    )

    num_q_bins = 15
    sample_avg = get_spherically_averaged_sample_binned(
        sample_raw, num_q_bins=num_q_bins,
    )

    atom_types = list(sample_raw.particle_counts.keys())
    neutron_weights = NeutronScatteringLengths(atom_types)
    sample_neutron = get_weighted_sample(sample_avg, neutron_weights)

    omega_meV = sample_avg.omega * radians_per_fs_to_meV

    # Persist results
    prefix = f"{molecule}_{forcefield}_{temperature}K"
    avg_path = os.path.join(cwd, f"{prefix}_sqw_averaged.npz")
    neu_path = os.path.join(cwd, f"{prefix}_sqw_neutron.npz")
    arr_path = os.path.join(cwd, f"{prefix}_sqw_arrays.npz")

    sample_avg.write_to_npz(avg_path)
    sample_neutron.write_to_npz(neu_path)
    np.savez(
        arr_path,
        q_norms=sample_avg.q_norms,
        omega_meV=omega_meV,
        Sqw_coh=sample_avg.Sqw_coh,
        Sqw_incoh=sample_avg.Sqw_incoh,
    )

    logger.info("S(q,w) computation complete → %s", prefix)
    return {
        "averaged_npz": avg_path,
        "neutron_npz": neu_path,
        "arrays_npz": arr_path,
        "n_frames": n_frames,
        "dt_fs": dt_fs,
        "window_size": window_size,
        "q_max": q_max,
    }
