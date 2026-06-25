"""Prove the enforce->pose bridge (ontology.pose_solve), migration step A.8.

Until now the v2 demos PLACED each pair by hand to exercise the CHECKS. This one
SOLVES the moving body's pose straight from the template `enforce` relations, then
runs the very same checks at the solved pose -- the engine now produces the layout,
not just grades a given one.

Two solves, exactly what the rung-2 moving group needs:
  1. coaxial revolute  -- idler bore seated onto the shoulder-screw axle (free spin).
  2. bolt-pattern seat -- the SL-TBLG plate fastened onto the SSEB20 block's 4x M4
     top pattern, the 4-hole correspondence SEARCHED (not zipped).

No render here (that's the rung-2 rebuild's LOOK); this is the numeric bridge proof.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ontology.schema_v2 import PartDefinition
from ontology.templates import TEMPLATES
from ontology import pose_solve as PS

ROOT = Path(__file__).resolve().parent.parent
LIBV2 = ROOT / "library_v2"
I3 = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
R_ZX = [[0, 0, 1], [1, 0, 0], [0, 1, 0]]      # screw local Z (axis) -> world X


def load(stem):
    return PartDefinition.from_json(json.loads((LIBV2 / f"{stem}.json").read_text()))


def main():
    lib = {
        "p_idl": load("SHTF20S3M100-5"),
        "p_scr": load("90263A239"),
        "p_blk": load("SSEB20-220_block"),
        "p_plt": load("SL-TBLGS3M100-plate"),
    }

    print("=" * 72)
    print("1. COAXIAL revolute seat -- idler bore SOLVED onto the screw axle")
    print("=" * 72)
    # the screw (axle) is the fixed, already-placed body; its shoulder axis is world X
    placements = {"p_scr": {"R": R_ZX, "t_mm": [16.5, 0.0, 0.0]}}
    revolute = TEMPLATES["retained_revolute_on_journal"].bind(
        {"rotor": "p_idl.bore", "journal": "p_scr.shoulder", "support": "p_blk.top"})
    res = PS.solve_pose(revolute, "p_idl", lib, placements, spin_rad=0.0)
    print("  " + res.text())
    print(f"  solved t_mm = {np.round(placements['p_idl']['t_mm'], 3).tolist()}")
    rep = revolute.evaluate(lib, placements)
    print("  CHECKS at the solved pose:")
    for r in rep.results:
        print("    " + str(r))

    # the free DOF is real: spin the idler, the seat is unchanged but a rim point moves
    res_spin = PS.solve_pose(revolute, "p_idl", lib, placements, spin_rad=np.pi / 2)
    rep_spin = revolute.evaluate(lib, placements)
    same_seat = all(r.verdict == s.verdict for r, s in zip(rep.results, rep_spin.results))
    print(f"  free-DOF check: +90 deg spin keeps every check verdict identical: {same_seat}")

    print("\n" + "=" * 72)
    print("2. BOLT-PATTERN seat -- SL-TBLG plate SOLVED onto the SSEB20 block top")
    print("=" * 72)
    placements2 = {"p_blk": {"R": I3, "t_mm": [0.0, 0.0, 0.0]}}
    seat = TEMPLATES["bounded_bolt_pattern_seat"].bind(
        {"plate": "p_plt.mount_face", "seat": "p_blk.top",
         "plate_group": "p_plt:guide_mount", "seat_group": "p_blk:mount_pattern"})
    res2 = PS.solve_pose(seat, "p_plt", lib, placements2)
    print("  " + res2.text())
    print(f"  solved t_mm = {np.round(placements2['p_plt']['t_mm'], 3).tolist()}")
    print(f"  correspondence = {res2.extra['correspondence']}")
    rep2 = seat.evaluate(lib, placements2)
    print("  CHECKS at the solved pose:")
    for r in rep2.results:
        print("    " + str(r))


if __name__ == "__main__":
    main()
