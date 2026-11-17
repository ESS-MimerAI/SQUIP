# SQUIP TaskBlaster Workflow

## What is TaskBlaster?

[TaskBlaster](https://gitlab.com/taskblaster/taskblaster) is a Python workflow
framework for orchestrating multi-step computational tasks. It handles:

- **Dependency tracking** – tasks declare which upstream results they need;
  TaskBlaster resolves the execution order automatically.
- **State management** – each task runs in its own directory under `tree/`.
  Completed tasks are cached; re-running the workflow skips them.
- **Failure recovery** – failed tasks can be reset with `unrun` and re-executed
  without repeating successful upstream tasks.

Key concepts:

| Concept | Description |
|---------|-------------|
| `@tb.workflow` | Decorator on a class that groups related tasks |
| `@tb.task` | Decorator on a method defining a single step |
| `tb.var()` | Declares a workflow input variable |
| `tb.node()` | Binds a task method to a concrete function in `tasks.py` |
| `tree/` | Directory where each task stores its inputs/outputs/state |

## Prerequisites

```
conda activate squip          # or whichever env has the packages below
pip install taskblaster
```

Required Python packages (already in the squip environment):

- `taskblaster` (workflow engine)
- `MDAnalysis` (trajectory analysis in `fix_box_trajectory`)
- `dynasor` (S(q,w) computation in `compute_sqw`)
- `numpy`

GROMACS must be installed. The workflow auto-discovers `gmx` from `PATH` or
from `C:\util\gromacs\bin\gmx.exe`. If your GROMACS is elsewhere, update the
search paths in `_find_gmx()` inside `tasks.py`.

## Files

| File | Role |
|------|------|
| `workflow.py` | Workflow definition – 8 tasks chained via dependencies |
| `tasks.py` | Task implementations – GROMACS calls, MDAnalysis, Dynasor |
| `run_tb.py` | Windows-compatible CLI wrapper (patches `signal.SIGCONT`) |

## Workflow Tasks

```
prepare_system          Steps 1.1–1.4: pdb2gmx, insert-molecules, solvate
  └─ energy_minimize    Step 1.5:  steepest-descent minimisation
       └─ nvt_equilibrate  Step 1.6: NVT equilibration
            └─ npt_equilibrate  Step 1.7: NPT equilibration
                 └─ production_md     Step 2: production MD
                      └─ center_trajectory   PBC centering (trjconv)
                           └─ fix_box_trajectory  Fixed-box trajectory for Dynasor
                                └─ compute_sqw      Step 3: S(q,w) with Dynasor
```

## Running the Workflow

### On Windows

Use `run_tb.py` instead of bare `tb` to work around the `signal.SIGCONT`
issue on Windows. It accepts the same subcommands.

```powershell
cd workflow/taskblaster

# 1. Initialise the TaskBlaster repository (first time only)
python run_tb.py init

# 2. Register the workflow (re-run after editing workflow.py)
python run_tb.py workflow workflow.py

# 3. Execute all tasks
python run_tb.py run .

# 4. Check status
python run_tb.py ls
```

### On Linux / macOS

The native `tb` CLI works directly:

```bash
cd workflow/taskblaster
tb init
tb workflow workflow.py
tb run .
tb ls
```

## Test Mode vs Production

The workflow has a `test_mode` flag (set in `workflow.py` → `workflow()` function):

| Parameter | Test mode (`True`) | Production (`False`) |
|-----------|--------------------|----------------------|
| EM steps | 5 000 | 50 000 |
| NVT steps | 5 000 (10 ps) | 50 000 (100 ps) |
| NPT steps | 5 000 (10 ps) | 50 000 (100 ps) |
| Production steps | 5 000 (10 ps) | 10 000 000 (20 ns) |
| Output frequency | every 15 steps (30 fs) | every 15 steps (30 fs) |
| S(q,w) window | 100 frames | 2 000 frames |

To switch modes, edit the `test_mode=True` line in `workflow.py`:

```python
runner.run_workflow(
    SQUIPWorkflow(
        ...
        test_mode=False,   # ← change to False for production
    )
)
```

Then re-register and run:

```powershell
python run_tb.py workflow workflow.py
python run_tb.py run .
```

## Re-running After Failures

```powershell
# See which task failed
python run_tb.py ls

# Reset a specific task and everything downstream
python run_tb.py unrun tree\<task_name> --force

# Re-run
python run_tb.py run .
```

## Changing the System

Edit the `workflow()` function at the bottom of `workflow.py` to change the
molecule, force field, temperature, number of solute molecules, or box size:

```python
runner.run_workflow(
    SQUIPWorkflow(
        project_root=project_root,
        molecule="glycine",       # glycine | glygly
        forcefield="amber99sb",   # amber99sb
        water_model="tip4p",      # tip4p (TIP4P-Ew)
        temperature=300,          # 300 | 350
        nmol=50,                  # number of solute molecules
        box_size=5.4,             # cubic box edge in nm
        test_mode=True,
    )
)
```

After changing parameters, reset and re-run:

```powershell
python run_tb.py unrun tree\prepare_system --force   # resets all 8 tasks
python run_tb.py workflow workflow.py
python run_tb.py run .
```
