#!/usr/bin/env python3
"""Print box dimensions (nm) from the first frame of a GROMACS trajectory."""

import argparse
import MDAnalysis as mda


def main():
    parser = argparse.ArgumentParser(description="Get box from first frame")
    parser.add_argument("tpr", help="Path to prod.tpr")
    parser.add_argument("xtc", help="Path to prod_center.xtc or fixed trajectory")
    args = parser.parse_args()

    u = mda.Universe(args.tpr, args.xtc)
    u.trajectory[0]
    lx, ly, lz = u.trajectory.ts.dimensions[:3]  # Angstrom
    print(f"{lx/10:.6f} {ly/10:.6f} {lz/10:.6f}")


if __name__ == "__main__":
    main()
