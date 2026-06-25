"""Rung 2 -- belt-driven linear axis, SSEB20 single-vendor Misumi moving group.

REBUILD (2026-06-20 r2) after the clamp<->guide fit was solved honestly:
  * guide  SSEB20-220  (block W=40, top 4x M4 @ 25x30, measured X in {-5,20} Z in {+-15})
  * plate  SL-TBLGS3M100-50-80-20-30-25-4 (M4 clearance @ 25x30, measured X in {80,105} Z in {+-15})
  * idlers SHTF20S3M100-5 x2 (5 mm bore, integral centre bearing -> free-spinning)
  * belt   S3M, 3 mm pitch, 10 mm wide, generated to the pulley pitch circles

World frame = the parts' native frame: X = longitudinal (travel), Y = up,
Z = transverse. The plate bolts to the block with a PURE longitudinal offset
(both patterns are 25x30) -- the engine SOLVES that pose from the real measured
holes (acceptor-fit RMS -> 0, an honest coincident fit, NOT a fudged target).
Idlers are SEATED coaxial on their shoulder-screw axles by the revolute enforce
path (`enforce_coaxial_and_check`). Belt routing + frame extrusion + brackets are
the remaining work -- see STATE.

This file replaces the old TBCN/6709 box-era build entirely.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from assembly.belt import make_belt
from assembly.mate_solver import (enforce_and_check, enforce_coaxial_and_check,
                                  world_geom, residual, pitch_match)
from ontology.schema import Part

ROOT = Path(__file__).resolve().parent.parent
OUT, CAD, LIB = ROOT / "out", ROOT / "cad", ROOT / "library"

R_I = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
# extrusion 6575N203 ships with its 304.8 mm length along local Z, 40x40 section in
# local X-Y. Rotate length -> world X (travel): local z->+X, local x->-Z, local y->Y.
R_EXT = [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]


# ---- adapter: schema Part -> the {kind,o,d/n/p} dicts mate_solver expects -----
class _FeatPart:
    """Wrap a library Part so `.feat(fid)` yields a mate_solver geometry dict."""
    def __init__(self, part: Part):
        self.part = part

    def feat(self, fid: str) -> dict:
        g = self.part.feature(fid).geometry
        t = type(g).__name__.lower()
        if "axis" in t:
            return {"kind": "axis", "o": list(g.origin), "d": list(g.direction)}
        if "plane" in t:
            return {"kind": "plane", "o": list(g.origin), "n": list(g.normal)}
        if "point" in t:
            return {"kind": "point", "p": list(g.point)}
        raise TypeError(f"unmapped geometry {t} for {fid}")


def load(stem: str) -> _FeatPart:
    return _FeatPart(Part.from_json(json.loads((LIB / stem).read_text())))


# --- layout constants (mm) -----------------------------------------------------
PR = 20 * 3.0 / (2 * np.pi)            # S3M 20T pitch radius = 9.549 mm
BLOCK_TOP = 20.0                       # block-local top face Y (measured)
PLATE_TOP_Y = 30.0                     # plate top face in world after seating (block top 20 + plate 10)
# block sits on the rail in-register (split from one GLB); both at identity.
# the slider travel is along world X.

# The belt's GRIPPED run lies on the plate clamp-end top (Y=30); set the idler
# centres one pitch-radius above so that run is the belt's lower tangent. The
# idlers sit just past the rail ends so the run spans the whole travel + the clamp.
IDLER_Y = 40.0                         # = the FALBS bracket's measured axle-hole height (H=40);
                                       # belt lower run lands at 40-PR=30.45, on the plate top (30)
IDLER_X = (-34.0, 214.0)               # just past the rail ends (rail spans X -20..200)
BRK_TZ = -11.7                         # bracket leg +Z face -> Z=-8.5, i.e. 1mm clear of the idler flange (-7.5)
SCR_TZ = 9.0                           # shoulder screw: shoulder step at Z=-5, head at +5..9 -> clamps the
                                       # bearing inner race (Z -4.9..4.9) while the flanges spin free
# 40x40 T-slot extrusion 6575N203 (304.8 mm). Centre it under the rail (rail centre
# X=90) and drop its top face to Y=0 so the SSEB20 rail bottom seats on it.
RAIL_CENTER_X = 90.0
EXT_PLACE = {"R": R_EXT, "t_mm": [RAIL_CENTER_X, -20.0, 0.0]}   # top face -> Y=0


def build():
    block = load("SSEB20-220_p_block.json")
    plate = load("SL-TBLGS3M100_p_plate.json")
    idler = load("SHTF20S3M100-5_p_idler.json")
    brk = load("FALBS-SP-T3.2-A80-B30-L30-H40-N3_p_brk.json")
    scr = load("90263A239_p_screw.json")

    # idler-axle brackets + REAL shoulder-screw axles: foot on extrusion top (Y=0),
    # bracket hole at H=40; the shoulder screw threads into that hole and its 5mm
    # shoulder is the shaft the idler's bearing inner-race rides on.
    placements = {
        "p_ext":   EXT_PLACE,
        "p_rail":  {"R": R_I, "t_mm": [0, 0, 0]},
        "p_block": {"R": R_I, "t_mm": [0, 0, 0]},
        "p_brk1":  {"R": R_I, "t_mm": [IDLER_X[0], 0.0, BRK_TZ]},
        "p_brk2":  {"R": R_I, "t_mm": [IDLER_X[1], 0.0, BRK_TZ]},
        "p_scr1":  {"R": R_I, "t_mm": [IDLER_X[0], 40.0, SCR_TZ]},
        "p_scr2":  {"R": R_I, "t_mm": [IDLER_X[1], 40.0, SCR_TZ]},
    }
    lib = {"p_block": block, "p_plate": plate, "p_idl1": idler, "p_idl2": idler,
           "p_brk1": brk, "p_brk2": brk, "p_scr1": scr, "p_scr2": scr}

    # --- ENFORCE: plate fasten onto the block's 4 M4 tapped holes ---------------
    # FLIPPED correspondence (180 deg about Y): the plate's belt-clamp end then
    # points INTO the travel (+X) where the belt run is, instead of cantilevering
    # off the low-X end outside the belt. The same 25x30 pattern still coincides
    # (RMS->0); Kabsch recovers R=flip, t=[100,24,0] from these honest pairs.
    hole_pairs = [
        (plate.feat("c_a"), "p_block.h_d"),   # plate(80,15)  -> block(20,-15)
        (plate.feat("c_b"), "p_block.h_c"),   # plate(105,15) -> block(-5,-15)
        (plate.feat("c_c"), "p_block.h_b"),   # plate(80,-15) -> block(20,15)
        (plate.feat("c_d"), "p_block.h_a"),   # plate(105,-15)-> block(-5,15)
    ]
    plate_rep = enforce_and_check(
        "p_plate", hole_pairs,
        check_constraints=[("coplanar", "p_plate.mount_face", "p_block.top")],
        library=lib, placements=placements)

    # --- ENFORCE: idlers seated REVOLUTE on the real shoulder-screw shoulder -----
    # The revolute axis is a real part feature (the screw's shoulder), NOT an
    # abstract world axis. Chain: bracket -(thread,fixed)- screw -(shoulder,revolute)- idler.
    idl_reports = []
    for ref, sref in (("p_idl1", "p_scr1"), ("p_idl2", "p_scr2")):
        rep = enforce_coaxial_and_check(
            ref, ref + ".bore", sref + ".shoulder_axis",
            check_constraints=[("coaxial", ref + ".bore", sref + ".shoulder_axis")],
            library=lib, placements=placements, joint="revolute")
        idl_reports.append(rep)

    # --- CHECK: the load path is REAL -- screw thread into bracket hole (fixed),
    #     idler bore on screw shoulder (revolute). Both reference real part features.
    brk_checks = []
    for bref, sref in (("p_brk1", "p_scr1"), ("p_brk2", "p_scr2")):
        th = world_geom(scr.feat("thread_axis"), placements[sref])
        bh = world_geom(brk.feat("axle"), placements[bref])
        brk_checks.append(residual("coaxial", th, bh, sref + ".thread", bref + ".hole"))

    # --- belt: S3M loop over the two idler pitch circles (vertical X-Y plane) ----
    c1 = (IDLER_X[0], IDLER_Y, 0.0)
    c2 = (IDLER_X[1], IDLER_Y, 0.0)
    span = abs(IDLER_X[1] - IDLER_X[0])
    teeth = int(round((2 * span + 2 * np.pi * PR) / 3.0))
    belt = make_belt(c1, c2, PR, teeth=teeth, pitch_in=3.0 / 25.4, width_in=10.0 / 25.4,
                     pulley_width_in=10.0 / 25.4, plane_normal=(0, 0, 1),
                     thickness_mm=1.2, tol_mm=5.0, glb_path=str(CAD / "belt_s3m.glb"))

    # --- CHECK: belt-clamp mate (belt lower run gripped by the plate clamp end) --
    # The belt's LOWER run is its lower tangent line at Y = IDLER_Y - PR = PLATE_TOP_Y,
    # tooth ridges running transverse (Z). The plate grip face must be coplanar with
    # it and the tooth directions parallel + pitch equal -- the textbook belt clamp.
    pp = plate_rep.pose
    grip_w = world_geom(plate.feat("grip"), pp)
    tdir_w = world_geom(plate.feat("grip_tooth"), pp)
    run_face = {"kind": "plane", "o": (grip_w["o"][0], IDLER_Y - PR, 0.0), "n": (0, 1, 0)}
    run_tdir = {"kind": "axis", "o": (grip_w["o"][0], IDLER_Y - PR, 0.0), "d": (0, 0, 1)}
    clamp_checks = [
        residual("coplanar", grip_w, run_face, "plate.grip", "belt.lower_run"),
        residual("parallel", tdir_w, run_tdir, "plate.tooth_dir", "belt.tooth_dir"),
        pitch_match("plate.pitch", 3.0, "belt.pitch", belt.pitch_mm),
    ]
    return placements, plate_rep, idl_reports, belt, clamp_checks, brk_checks


RENDER = [
    ("p_ext",   "/cad/6575N203.glb",         0x7f8c9b),
    ("p_rail",  "/cad/SSEB20-220_rail.glb",  0xb9c0c8),
    ("p_block", "/cad/SSEB20-220_block.glb", 0x9aa3ad),
    ("p_plate", "/cad/SL-TBLGS3M100-50-80-20-30-25-4.glb", 0xc0563f),
    ("p_brk1",  "/cad/FALBS-SP-T3.2-A80-B30-L30-H40-N3.glb", 0x6f9fcf),
    ("p_brk2",  "/cad/FALBS-SP-T3.2-A80-B30-L30-H40-N3.glb", 0x6f9fcf),
    ("p_scr1",  "/cad/90263A239.glb",        0xb8b0c8),
    ("p_scr2",  "/cad/90263A239.glb",        0xb8b0c8),
    ("p_idl1",  "/cad/SHTF20S3M100-5.glb",   0xd9b24b),
    ("p_idl2",  "/cad/SHTF20S3M100-5.glb",   0xd9b24b),
    ("p_belt",  "/cad/belt_s3m.glb",         0x3b4654),
]


def main():
    OUT.mkdir(exist_ok=True)
    placements, plate_rep, idl_reports, belt, clamp_checks, brk_checks = build()
    placements["p_belt"] = {"R": R_I, "t_mm": [0, 0, 0]}
    out = {k: v for k, v in placements.items() if not k.startswith("_axle_")}
    out["_render"] = [{"ref": r, "url": u, "color": c} for r, u, c in RENDER]
    with open(OUT / "rung2_placements.json", "w") as fh:
        json.dump(out, fh, indent=2)

    print("=== MOVING GROUP, engine-solved (real measured CAD) ===")
    print(plate_rep.text())
    print(f"   plate pose t_mm = {np.round(plate_rep.pose['t_mm'], 3).tolist()}")
    for rep in idl_reports:
        print(rep.text())
    print("belt:", belt.detail)
    print("BELT-CLAMP mate (belt lower run <-> plate clamp end):")
    for c in clamp_checks:
        verdict = "REDUNDANT-OK" if c.satisfied() else "VIOLATED"
        print(f"   check {c.ctype:9s} {c.a} = {c.b}: {c.detail}  -> {verdict}")
    print("IDLER LOAD PATH (screw thread <-> bracket hole; idler rides screw shoulder):")
    for c in brk_checks:
        verdict = "OK" if c.satisfied() else "VIOLATED"
        print(f"   check {c.ctype:9s} {c.a} = {c.b}: {c.detail}  -> {verdict}")
    print("wrote out/rung2_placements.json")


if __name__ == "__main__":
    main()
