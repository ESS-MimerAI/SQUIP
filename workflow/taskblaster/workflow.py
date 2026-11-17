"""SQUIP MD workflow for TaskBlaster.

Single-system workflow: glycine / AMBER99SB-ILDN / TIP4P-Ew / 300 K.

Usage::

    cd workflow/taskblaster
    tb init
    tb workflow workflow.py
    tb run .

The workflow chains Steps 1–3 of the SQUIP project:

  Step 1  prepare_system → energy_minimize → nvt_equilibrate → npt_equilibrate
  Step 2  production_md → center_trajectory
  Step 3  fix_box_trajectory → compute_sqw

Set *test_mode=True* (the default) for short simulations suitable for
verifying that the pipeline works end-to-end.  Set *test_mode=False* for
production-length runs (20 ns).
"""

import os

import taskblaster as tb


@tb.workflow
class SQUIPWorkflow:
    # --- inputs ---
    project_root = tb.var()
    molecule = tb.var()
    forcefield = tb.var()
    water_model = tb.var()
    temperature = tb.var()
    nmol = tb.var(default=50)
    box_size = tb.var(default=5.4)
    test_mode = tb.var(default=True)

    # ---- Step 1: System preparation ----------------------------------

    @tb.task
    def prepare_system(self):
        """Steps 1.1–1.4: pdb2gmx, insert-molecules, solvate."""
        return tb.node(
            "prepare_system",
            project_root=self.project_root,
            molecule=self.molecule,
            forcefield=self.forcefield,
            water_model=self.water_model,
            nmol=self.nmol,
            box_size=self.box_size,
        )

    @tb.task
    def energy_minimize(self):
        """Step 1.5: steepest-descent energy minimisation."""
        return tb.node(
            "energy_minimize",
            system=self.prepare_system,
            project_root=self.project_root,
            test_mode=self.test_mode,
        )

    @tb.task
    def nvt_equilibrate(self):
        """Step 1.6: NVT equilibration."""
        return tb.node(
            "nvt_equilibrate",
            em_result=self.energy_minimize,
            system=self.prepare_system,
            project_root=self.project_root,
            temperature=self.temperature,
            test_mode=self.test_mode,
        )

    @tb.task
    def npt_equilibrate(self):
        """Step 1.7: NPT equilibration."""
        return tb.node(
            "npt_equilibrate",
            nvt_result=self.nvt_equilibrate,
            system=self.prepare_system,
            project_root=self.project_root,
            temperature=self.temperature,
            test_mode=self.test_mode,
        )

    # ---- Step 2: Production MD ----------------------------------------

    @tb.task
    def production_md(self):
        """Step 2.1–2.3: production NPT MD."""
        return tb.node(
            "production_md",
            npt_result=self.npt_equilibrate,
            system=self.prepare_system,
            project_root=self.project_root,
            temperature=self.temperature,
            test_mode=self.test_mode,
        )

    @tb.task
    def center_trajectory(self):
        """Step 2.4: centre trajectory with PBC mol."""
        return tb.node(
            "center_trajectory",
            prod_result=self.production_md,
            project_root=self.project_root,
        )

    # ---- Step 3: S(q,w) analysis --------------------------------------

    @tb.task
    def fix_box_trajectory(self):
        """Step 3.2A: create fixed-box trajectory for Dynasor."""
        return tb.node(
            "fix_box_trajectory",
            center_result=self.center_trajectory,
            prod_result=self.production_md,
        )

    @tb.task
    def compute_sqw(self):
        """Step 3.3: compute S(q,w) with Dynasor."""
        return tb.node(
            "compute_sqw",
            fixed_traj=self.fix_box_trajectory,
            prod_result=self.production_md,
            project_root=self.project_root,
            molecule=self.molecule,
            forcefield=self.forcefield,
            temperature=self.temperature,
        )


# -----------------------------------------------------------------------
# Entry point called by  ``tb workflow workflow.py``
# -----------------------------------------------------------------------

def workflow(runner):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    runner.run_workflow(
        SQUIPWorkflow(
            project_root=project_root,
            molecule="glycine",
            forcefield="amber99sb",
            water_model="tip4p",
            temperature=300,
            nmol=50,
            box_size=5.4,
            test_mode=True,
        )
    )
