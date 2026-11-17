#!/usr/bin/env python3
"""GROMACS trajectory wrapper compatible with Dynasor's compute functions.

Dynasor's built-in ``Trajectory`` class passes only a single *filename*
to its internal MDAnalysis reader, which does not work for GROMACS
XTC/TRR files that require a separate topology file (.tpr, .gro, .pdb).

This module provides :class:`GROMACSTrajectory` — a lightweight wrapper
around an MDAnalysis ``Universe`` that exposes the same duck-typed
interface consumed by :func:`dynasor.compute_dynamic_structure_factors`
and other Dynasor compute functions.
"""

import warnings
from itertools import chain, islice
from typing import Optional, Union

import numpy as np
from numpy.typing import NDArray

import MDAnalysis as mda
from dynasor.trajectory.trajectory_frame import TrajectoryFrame
from dynasor.logging_tools import logger


class GROMACSTrajectory:
    """Read GROMACS trajectories for use with Dynasor compute functions.

    Parameters
    ----------
    topology : str
        Path to a GROMACS topology file (.tpr, .gro, .pdb).
    trajectory : str
        Path to a GROMACS trajectory file (.xtc, .trr).  May also be
        ``None``, in which case only the topology coordinates are used
        (single-frame mode, mostly for testing).
    atomic_indices : dict[str, list[int]]
        Mapping of atom-type labels to 0-based atom indices.
        Keys must not contain underscores (Dynasor convention).
    frame_start : int
        First frame to read (default 0).
    frame_stop : int or None
        Stop *before* this frame (default ``None`` = read all).
    frame_step : int
        Read every *frame_step*-th frame (default 1).
    check_cell : bool
        When ``True`` (default), warn if the cell changes between the
        first two frames (NPT trajectory).
    """

    def __init__(
        self,
        topology: str,
        trajectory: Optional[str] = None,
        atomic_indices: Optional[dict[str, list[int]]] = None,
        frame_start: int = 0,
        frame_stop: Optional[int] = None,
        frame_step: int = 1,
        check_cell: bool = True,
    ):
        if frame_start < 0:
            raise ValueError("frame_start must be >= 0")
        if frame_step < 1:
            raise ValueError("frame_step must be >= 1")

        # --- Load MDAnalysis Universe ---------------------------------
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            if trajectory is not None:
                self._universe = mda.Universe(topology, trajectory)
            else:
                self._universe = mda.Universe(topology)

        self._n_atoms = self._universe.atoms.n_atoms
        self._filename = trajectory or topology

        # --- Cell (Angstrom) from the first frame ---------------------
        ts0 = self._universe.trajectory[0]
        self._cell: NDArray[float] = ts0.triclinic_dimensions.copy()

        if check_cell and len(self._universe.trajectory) > 1:
            ts1 = self._universe.trajectory[1]
            if not np.allclose(
                ts0.triclinic_dimensions, ts1.triclinic_dimensions, atol=0.05
            ):
                logger.warning(
                    "Cell changes between frames (NPT trajectory). "
                    "Dynasor assumes constant volume — using first-frame cell."
                )
            # Reset iterator position
            self._universe.trajectory[0]

        # --- Atomic indices -------------------------------------------
        if atomic_indices is None:
            atomic_indices = {"X": np.arange(self._n_atoms)}
        self._atomic_indices: dict[str, NDArray[int]] = {
            k: np.asarray(v, dtype=int) for k, v in atomic_indices.items()
        }

        for key, indices in self._atomic_indices.items():
            if "_" in key:
                raise ValueError(
                    f'Underscore "_" not allowed in atom type name "{key}".'
                )
            if len(indices) > 0 and np.max(indices) >= self._n_atoms:
                raise ValueError(
                    f"Max index in atomic_indices[{key}] ({np.max(indices)}) "
                    f">= number of atoms ({self._n_atoms})"
                )

        # --- Frame slicing parameters ---------------------------------
        self._frame_start = frame_start
        self._frame_stop = frame_stop
        self._frame_step = frame_step

        self.number_of_frames_read: int = 0
        self.current_frame_index: int = 0

        # --- Log summary ----------------------------------------------
        logger.info(f"Trajectory file: {self._filename}")
        logger.info(f"Topology file:   {topology}")
        logger.info(f"Total number of particles: {self._n_atoms}")
        logger.info(f"Number of atom types: {len(self.atom_types)}")
        for atype in self.atom_types:
            logger.info(
                f"Number of atoms of type {atype}: "
                f"{len(self._atomic_indices[atype])}"
            )
        logger.info(f"Simulation cell (in Angstrom):\n{self._cell}")

    # ------------------------------------------------------------------
    # Properties required by Dynasor compute functions
    # ------------------------------------------------------------------

    @property
    def cell(self) -> NDArray[float]:
        """Simulation cell metric (3×3, Angstrom)."""
        return self._cell.copy()

    @property
    def n_atoms(self) -> int:
        return self._n_atoms

    @property
    def filename(self) -> str:
        return self._filename

    @property
    def atomic_indices(self) -> dict[str, NDArray[int]]:
        return {k: v.copy() for k, v in self._atomic_indices.items()}

    @property
    def atom_types(self) -> list[str]:
        return sorted(self._atomic_indices.keys())

    @property
    def frame_step(self) -> int:
        return self._frame_step

    # ------------------------------------------------------------------
    # Iterator — yields TrajectoryFrame objects
    # ------------------------------------------------------------------

    def __iter__(self):
        mdtraj = self._universe.trajectory
        n_frames = len(mdtraj)

        stop = self._frame_stop if self._frame_stop is not None else n_frames
        stop = min(stop, n_frames)

        for i in range(self._frame_start, stop, self._frame_step):
            ts = mdtraj[i]
            # MDAnalysis converts GROMACS nm → Angstrom by default
            frame = TrajectoryFrame(
                self._atomic_indices,
                i,
                ts.positions.copy(),
                ts.velocities.copy() if ts.has_velocities else None,
            )
            self.number_of_frames_read += 1
            self.current_frame_index = i
            yield frame

    def __repr__(self) -> str:
        return (
            f"GROMACSTrajectory(file={self._filename!r}, "
            f"n_atoms={self._n_atoms}, "
            f"atom_types={self.atom_types})"
        )
