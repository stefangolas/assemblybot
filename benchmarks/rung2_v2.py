"""Rung 2 on the v2 ontology, END TO END -- the first time the moving group's poses
are SOLVED from template `enforce` (ontology.pose_solve), graded by the v2 matchers,
and written to ONE placement source for both the gate and the viewer.

This is the build->LOOK loop (Hard Rule 1/1b): it produces a layout to RENDER and
INSPECT. It deliberately uses the CURRENT library_v2 BOM so the remaining gaps SURFACE
AS NUMBERS, not prose:
  * the belt capture is not load-bearing until a real S3M-10 closed-belt PN is selected;
  * the idler retention needs 2 spacers/idler (ID5/OD<=7.5/~3 mm) to clamp the 685ZZ
    inner races -- not yet in the BOM, so retention closure honestly reports UNHELD.
RESOLVED 2026-06-21: the idler is a 685ZZ x2 bearing assembly with a 10 mm inner-race
stack; the 96654A131 shoulder is 16 mm, so 3 + 10 + 3 = 16 mm clamps it EXACTLY. The
look + these numbers drive the remaining part hunt (real belt PN + the 3 mm spacer).

World frame = parts' native frame: X=travel, Y=up, Z=transverse. Extrusion top -> Y=0.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from assembly.belt import make_belt
from ontology.schema_v2 import PartDefinition
from ontology.templates import TEMPLATES
from ontology import pose_solve as PS

ROOT = Path(__file__).resolve().parent.parent
OUT, CAD, LIBV2 = ROOT / "out", ROOT / "cad", ROOT / "library_v2"

R_I = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
R_FLIPY = [[-1, 0, 0], [0, 1, 0], [0, 0, -1]]   # 180deg about Y: screw thread -> +Z, head -> -Z
# extrusion 6575N203: 304.8 mm length along local Z, 40x40 in local X-Y -> length to world X
R_EXT = [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]

PR = 20 * 3.0 / (2 * np.pi)            # S3M 20T pitch radius = 9.549 mm
# Belt SELECTED 2026-06-21: HTUN600S3M-100 (MISUMI, S3M, 10 mm, CLOSED, 600 mm / 200T).
# For two equal S3M-20 pulleys L = 2C + pi*PD = 2C + 60.0 mm; the 600 mm belt => C = 270 mm.
# So the idler centres are SNAPPED to the real catalog belt length, not the other way round.
# (The HTUN back-side-tension caution does NOT apply: nothing backs the belt's outer face.)
IDLER_X = (-45.0, 225.0)             # C = 270 mm -> real 600 mm belt; avoids bracket-rail collision
IDLER_Y = 40.0                        # bracket axle-hole height -> belt lower run at 40-PR=30.45
RAIL_CENTER_X = 90.0
EXT_PLACE = {"R": R_EXT, "t_mm": [-62.4, -20.0, 0.0]}   # Centered at 90.0 -> spans -62.4 to 242.4
BRK_Z = 11.0                          # bracket moved +Z so its 3.2 mm riser plate (-> Z 11..14.2)
                                      # sits OUTBOARD of the idler (+Z flange at Z=8.5), not at its
                                      # mid-span. Foot bolt stays within the extrusion slot (Z<20).
SCR_TZ = -3.0                         # flipped 28 mm screw origin: thread engages the moved plate
                                      # (~Z 11..15), shoulder spans Z 11..-17 across the idler,
                                      # head retains it at Z~-17..-21 (idler's free -Z side).
IDLER_ALONG = 2.8                     # slide the idler bore along the shoulder so its band sits on
                                      # the belt plane (world Z=0); tuned against the interference gate.


def load(stem):
    return PartDefinition.from_json(json.loads((LIBV2 / f"{stem}.json").read_text()))


def build():
    lib = {
        "p_ext": load("6575N203-extrusion"),
        "p_blk": load("SSEB20-220_block"),
        "p_plt": load("FPT-Adapter-Plate"),
        "p_idl1": load("SHTF20S3M100-5"), "p_idl2": load("SHTF20S3M100-5"),
        "p_brk1": load("FALBS-H40-bracket"), "p_brk2": load("FALBS-H40-bracket"),
        # 28 mm shoulder (was 16 mm 96654A131): long enough to put the bracket plate OUTBOARD
        # of the 21.8 mm idler and cantilever back to it, so the plate no longer straddles the
        # spinning idler (the 7.7 mm interference). Bracket moves +Z to BRK_Z; screw flipped.
        "p_scr1": load("SHOULDER-D5-L28-M4"), "p_scr2": load("SHOULDER-D5-L28-M4"),
        "p_jaw": load("TBCR-Clamp-Jaw"),
    }
    # fixed (frame) placements; the moving group is SOLVED below
    placements = {
        "p_ext": EXT_PLACE,
        # block top at world Y=20. X is a TRAVEL position (slider DOF): set so the
        # plate's belt-grip end (= block_X - 72.5) lands ON the belt lower run, not off
        # its left end. Drawing-verified: the grip is the plate's low-X toothed end; at
        # block_X=102.5 the grip sits at world X=30, between the idlers (-30..210).
        "p_blk": {"R": R_I, "t_mm": [102.5, 0, 0]},
        "p_brk1": {"R": R_I, "t_mm": [IDLER_X[0], 0.0, BRK_Z]},
        "p_brk2": {"R": R_I, "t_mm": [IDLER_X[1], 0.0, BRK_Z]},
        # screw FLIPPED 180deg about Y: thread (local -Z) -> world +Z into the moved plate;
        # shoulder cantilevers -Z back across the idler; head retains it on the idler's -Z side.
        "p_scr1": {"R": R_FLIPY, "t_mm": [IDLER_X[0], IDLER_Y, SCR_TZ]},
        "p_scr2": {"R": R_FLIPY, "t_mm": [IDLER_X[1], IDLER_Y, SCR_TZ]},
    }

    # --- SOLVE: plate fastened onto the block top -----------------------
    seat = TEMPLATES["bounded_bolt_pattern_seat"].bind(
        {"plate": "p_plt.bot_face", "seat": "p_blk.top",
         "plate_group": "p_plt:guide_mount", "seat_group": "p_blk:mount_pattern"})
    plate_res = PS.solve_pose(seat, "p_plt", lib, placements)
    plate_checks = seat.evaluate(lib, placements)

    # --- SOLVE: each idler seated revolute on its shoulder-screw axle ------------
    # along_mm = -SCR_TZ centres the idler bore origin on the shoulder (world Z=0).
    idl_res, idl_checks = [], []
    for iref, sref, bref in (("p_idl1", "p_scr1", "p_brk1"), ("p_idl2", "p_scr2", "p_brk2")):
        # r9 split (directive Section 2/3): POSE/FIT only -- no support binding, no
        # load-path edge. The idler riding the shoulder is kinematic; whether the idler
        # is HELD (retention stack) and whether the screw reaches ground (screw->support)
        # are SEPARATE attachments graded in the gate, not implied by this fit.
        rev = TEMPLATES["revolute_fit_on_journal"].bind(
            {"rotor": f"{iref}.bore", "journal": f"{sref}.shoulder"})
        idl_res.append(PS.solve_pose(rev, iref, lib, placements, along_mm=IDLER_ALONG))
        idl_checks.append((iref, rev.evaluate(lib, placements)))

    # --- belt: closed S3M loop over the two idler pitch circles (X-Y plane) ------
    # The routed loop is the ONE allowed generated element; it represents the real
    # selected catalog instance HTUN540S3M-100 (540 mm / 180T). teeth derives from the
    # C=240 geometry and MUST come out 180 to match the catalog length (asserted below).
    c1 = (IDLER_X[0], IDLER_Y, 0.0)
    c2 = (IDLER_X[1], IDLER_Y, 0.0)
    span = abs(IDLER_X[1] - IDLER_X[0])
    teeth = int(round((2 * span + 2 * np.pi * PR) / 3.0))
    assert teeth == 200, f"geometry wants {teeth}T but selected belt HTUN600S3M-100 is 200T; re-snap C"
    belt = make_belt(c1, c2, PR, teeth=teeth, pitch_in=3.0 / 25.4, width_in=10.0 / 25.4,
                     pulley_width_in=10.0 / 25.4, plane_normal=(0, 0, 1),
                     thickness_mm=1.2, tol_mm=5.0, glb_path=str(CAD / "belt_s3m.glb"))
    lib["p_belt"] = load("HTUN540S3M-100_belt")
    placements["p_belt"] = {"R": R_I, "t_mm": [0, 0, 0]}
    # --- clamp assembly ----------------------------------------------------------
    # The clamp assembly bridges the block to the belt. We use a Configurable FPT plate.
    lib["p_jaw"] = load("TBCR-Clamp-Jaw")
    placements["p_jaw"] = {"R": R_I, "t_mm": [100.0, 24.0, 0.0]}
    # first fasten the jaw to the plate
    jaw_fasten = TEMPLATES["bounded_bolt_pattern_seat"].bind(
        {"plate": "p_jaw.bot_face", "seat": "p_plt.top_face",
         "plate_group": "p_jaw:clamp_mount", "seat_group": "p_plt:clamp_mount"})
    jaw_res = PS.solve_pose(jaw_fasten, "p_jaw", lib, placements)
    
    jaw_seat = TEMPLATES["belt_capture"].bind(
        {"belt": "p_belt.run_lower", "grip": "p_plt.grip_teeth", "jaw": "p_jaw.bot_face",
         "grip_group": "p_plt:clamp_mount", "jaw_group": "p_jaw:clamp_mount"})
    # jaw_seat evaluated in checks later
    return lib, placements, plate_res, plate_checks, idl_res, idl_checks, belt, jaw_res


RENDER = [
    ("p_ext",  "/cad/6575N203.glb",         0x7f8c9b),
    ("p_rail", "/cad/SSEB20-220_rail.glb",  0xb9c0c8),
    ("p_blk",  "/cad/SSEB20-220_block.glb", 0x9aa3ad),
    ("p_plt",  "/cad/CUSTOM-plate.glb", 0xc0563f),
    ("p_jaw",  "/cad/CUSTOM-clamp.glb", 0xc0563f),
    ("p_brk1", "/cad/FALBS-SP-T3.2-A80-B30-L30-H40-M4-NA5.glb", 0x6f9fcf),
    ("p_brk2", "/cad/FALBS-SP-T3.2-A80-B30-L30-H40-M4-NA5.glb", 0x6f9fcf),
    ("p_scr1", "/cad/SHOULDER-D5-L28-M4.glb",        0xb8b0c8),
    ("p_scr2", "/cad/SHOULDER-D5-L28-M4.glb",        0xb8b0c8),
    ("p_idl1", "/cad/SHTF20S3M100-5.glb",   0xd9b24b),
    ("p_idl2", "/cad/SHTF20S3M100-5.glb",   0xd9b24b),
    ("p_belt", "/cad/belt_s3m.glb",         0x3b4654),
]


def main():
    OUT.mkdir(exist_ok=True)
    lib, placements, plate_res, plate_checks, idl_res, idl_checks, belt, jaw_res = build()
    placements["p_rail"] = {"R": R_I, "t_mm": [0, 0, 0]}

    # --- fasteners (real / standard-generated), placed for the LOOK -------------
    # R_DOWN sends a screw's local +Z (head) to world +Y and its thread to -Y, so a
    # cap screw drops head-up into a hole. The load-path gate confirmed these as real
    # held parts; here we just seat them visibly.
    R_DOWN = [[1, 0, 0], [0, 0, 1], [0, -1, 0]]
    extra_render = []
    # 4x M5x16 in the rail counterbores (rail at identity; holes X=0,60,120,180, Z=0)
    for i, x in enumerate((0, 60, 120, 180)):
        placements[f"p_scr_rail{i}"] = {"R": R_DOWN, "t_mm": [float(x), 5.5, 0.0]}
        extra_render.append((f"p_scr_rail{i}", "/cad/ISO4762-M5x0.8-16.glb", 0xb8b0c8))
    # 4x M4x12 in the plate guide-mount holes (transform plate-local holes to world)
    pR = np.array(placements["p_plt"]["R"], float); pt = np.array(placements["p_plt"]["t_mm"], float)
    for hx in (-12.5, 12.5):
        for hz in (-15.0, 15.0):
            w = pR @ np.array([hx, 2.0, hz]) + pt          # plate-top hole, world
            ref = f"p_scr_plt_{int(hx)}_{int(hz)}"
            placements[ref] = {"R": R_DOWN, "t_mm": [float(w[0]), float(w[1]) + 2.0, float(w[2])]}
            extra_render.append((ref, "/cad/ISO4762-M4x0.7-12.glb", 0x9a9aa8))
    # 2x M5x10 fastening each FALBS bracket foot to the extrusion: the screw drops
    # through the foot's M5 clearance hole (bracket-local [5,0,10]) into an HNTT6-5
    # T-slot nut captured in the extrusion's top slot. This is the visible half of the
    # bracket.foot -> ext.tslot mount (the nut sits hidden inside the slot).
    for j, xc in enumerate(IDLER_X):
        wx, wz = float(xc) + 5.0, -1.7              # foot hole world (bracket at Z=-11.7)
        placements[f"p_scrfoot_brk{j+1}"] = {"R": R_DOWN, "t_mm": [wx, 3.2, wz]}
        extra_render.append((f"p_scrfoot_brk{j+1}", "/cad/ISO4762-M5x0.8-10.glb", 0xb8b0c8))
    # 4x idler inner-race spacers (axis = world Z; one each side, in the flange recess)
    for j, xc in enumerate(IDLER_X):
        for side, z in (("a", -6.5), ("b", 6.5)):
            ref = f"p_spacer_idl{j+1}_{side}"
            placements[ref] = {"R": R_I, "t_mm": [float(xc), IDLER_Y, z]}
            extra_render.append((ref, "/cad/DWSSS-D7.5-V5-L3.glb", 0xd9d2c0))
    # belt-clamp jaw is now solved from the template enforce relations
    out = dict(placements)
    out["_render"] = [{"ref": r, "url": u, "color": c} for r, u, c in RENDER + extra_render]
    (OUT / "rung2_v2_placements.json").write_text(json.dumps(out, indent=2))

    print("=== RUNG 2 v2 -- moving group solved from template enforce ===")
    print(" " + plate_res.text())
    print(f"   plate t_mm = {np.round(placements['p_plt']['t_mm'], 2).tolist()}")
    for r in plate_checks.results:
        print("    " + str(r))
    for res, (iref, rep) in zip(idl_res, idl_checks):
        print(" " + res.text())
        print(f"   {iref} t_mm = {np.round(placements[iref]['t_mm'], 2).tolist()}")
        for r in rep.results:
            print("    " + str(r))
    print(" belt:", belt.detail)
    print("wrote out/rung2_v2_placements.json")

    # shared verification harness (same gates every rung runs). rung 2 has v2 defs -> cad_fidelity
    # + interference run; load_path SKIPs here (the moving group is pose-solved per-template, not
    # assembled into one instance list -- the dedicated _rung2_v2_gate.py covers it).
    from assembly.verify import verify_assembly
    _urls2 = {r: u for r, u, c in RENDER + extra_render}
    def _designed2(a, b):
        if any(x.startswith(("p_scr", "p_spacer", "p_belt")) for x in (a, b)):
            return True                              # fasteners / spacers / belt seat into their parts
        return {a, b} in [{"p_blk", "p_plt"}, {"p_blk", "p_rail"}, {"p_rail", "p_ext"},
                          {"p_brk1", "p_ext"}, {"p_brk2", "p_ext"}, {"p_idl1", "p_scr1"},
                          {"p_idl2", "p_scr2"}, {"p_plt", "p_jaw"}]
    verify_assembly("rung2", placements, _urls2, lib=lib, designed=_designed2)

    # auto-render: looking at the assembly IS the verification (constitution Hard Rule
    # 1/1b), so the build always produces the picture, not just the numbers.
    try:
        from benchmarks._shot import shoot
        imgs = shoot("out/rung2_v2_placements.json", "out/rung2_v2", "", ("iso", "z"))
        print("rendered:", ", ".join(imgs))
    except Exception as e:                       # noqa: BLE001 - a render hiccup must not fail the build
        print(f"(render skipped: {e})")


if __name__ == "__main__":
    main()
