"""Rung 2 -- belt-driven linear axis (Section 11), COHERENT redesign. Target 1 DOF.

Reference design (OpenBuilds/Misumi style): extrusion base -> profile-rail guide on
a sub-plate -> carriage block -> carriage plate on standoffs (clears the belt plane)
-> belt clamp to one belt run -> two XL pulleys on shafts in bearings, on end-plate
brackets -> motor (open). The connection graph (this file's mates) is the assembly;
mobility merges rigid bodies and confirms DOF 1.

Real parts (live mcmaster.com CAD): 6575N368 extrusion, 6709K231 rail + 6709K211
carriage, 1277N16 XL pulley x2, 1327K65 shaft x2, 57155K324 R4 bearing x2.
Belt 1679K197 (XL 67T, 13.4") -> generated as a TOOTHED loop (assembly/belt.py).
Custom/fabricated (modelled as boxes, as they are in any real build): rail sub-plate
(resolves the rail's M3 holes vs the extrusion's M5 T-nuts -- fit-risk #1), 2 end-plate
brackets, carriage plate, standoffs, belt clamp.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import trimesh

from ontology import Axis, Plane, Feature, Part, PartRef, Assembly, Constraint, Joint, Mate
from ontology.interfaces import bearing_mount, pulley_mount, belt_drive
from assembly import validate
from assembly.belt import make_belt

ROOT = Path(__file__).resolve().parent.parent
LIB, OUT, CAD = ROOT / "library", ROOT / "out", ROOT / "cad"

# --- layout constants (mm): travel=Z, up=Y, lateral=X; extrusion centred at origin
TOP = 12.5                 # extrusion top face Y
PR = 12.13                 # pulley pitch radius (PD 0.955"/2)
BELT_TEETH = 67            # 1679K197
C = (BELT_TEETH * 0.2 * 25.4 - np.pi * 2 * PR) / 2     # center distance from belt length
ZP = C / 2                 # pulleys at +-ZP
XB = 25.0                  # belt plane offset in +X (clear of carriage)
YB = 13.0                  # pulley axis height -> upper run at YB+PR ~= 25.1
PLATE_Y = 27.0             # carriage plate underside (above upper run YB+PR=25.13)


def _box_glb(name, ext, color=(150, 150, 160)):
    # EXPORT IN METRES: glTF is unit-agnostic and the viewer/cascadio meshes are in
    # metres, so a box built with mm extents renders 1000x too large (it floated the
    # custom parts off-screen for an entire session). Normalize here at the boundary.
    m = trimesh.creation.box(extents=[e / 1000.0 for e in ext])
    m.visual.vertex_colors = color
    p = str(CAD / f"{name}.glb"); m.export(p); return p


def _p(pn, cls, spec, feats, gltf, **frame):
    return Part(part_number=pn, cls=cls, source_url=f"https://www.mcmaster.com/{pn}/"
                if not pn.startswith("CUSTOM") else "fabricated", retrieved_at="2026-06-18",
                raw_spec={}, spec=spec, cad={"gltf_uri": gltf},
                frame={"origin": [0, 0, 0], "handedness": "right", **frame}, features=feats,
                provenance={"discovered_by": "playwright" if not pn.startswith("CUSTOM") else "design",
                            "annotated_by": "manual", "confidence": 0.9})


def build():
    f = lambda fid, geo, role, pa=None: Feature(fid, geo, role, pa or {})
    ax = lambda o, d: Axis(origin=o, direction=d)
    pl = lambda o, n: Plane(origin=o, normal=n)

    lib, place = {}, {}
    R_I = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    R_ZX = [[0, 0, 1], [1, 0, 0], [0, 1, 0]]            # local Z -> world X (pulley/shaft axis)

    # base extrusion (ground)
    lib["p_ext"] = _p("6575N368", "t_slot_extrusion", {"len": 304.8},
                      [f("top", pl((0, TOP, 0), (0, 1, 0)), "mounting_face")],
                      str(CAD / "6575N368.glb"))
    place["p_ext"] = {"R": R_I, "t_mm": [0, 0, 0]}

    # rail sub-plate (custom) -- resolves M3 rail holes vs M5 extrusion T-nuts
    lib["p_subplate"] = _p("CUSTOM-subplate", "mount_plate",
                           {"note": "rail(M3) -> plate -> extrusion(M5 T-nut)"},
                           [f("bot", pl((0, TOP, 0), (0, -1, 0)), "mounting_face"),
                            f("top", pl((0, TOP + 4, 0), (0, 1, 0)), "mounting_face")],
                           _box_glb("CUSTOM-subplate", (34, 4, 290), (90, 95, 105)))
    place["p_subplate"] = {"R": R_I, "t_mm": [0, TOP + 2, 0]}

    # profile rail
    lib["p_rail"] = _p("6709K231", "linear_rail", {"width_mm": 8, "len_mm": 275},
                       [f("axis", ax((0, TOP + 4, 0), (0, 0, 1)), "shaft_bore", {"diameter": 8}),
                        f("bot", pl((0, TOP + 4, 0), (0, -1, 0)), "mounting_face")],
                       str(CAD / "6709K231.glb"))
    place["p_rail"] = {"R": R_I, "t_mm": [0, TOP + 4 + 3, 0]}      # rail centre Y = top+7

    # carriage block (rides rail -> slider). Its travel axis is COLLINEAR with the
    # rail axis (same line at Y=TOP+4); the block body centre sits 3 mm higher.
    RAILC = TOP + 4 + 3
    lib["p_carriage"] = _p("6709K211", "linear_carriage", {"for_rail_mm": 8},
                           [f("axis", ax((0, TOP + 4, 0), (0, 0, 1)), "shaft_bore", {"diameter": 8}),
                            f("top", pl((0, RAILC + 4.45, 0), (0, 1, 0)), "mounting_face",
                              {"pattern": "4x M2 @ 10x10"})],
                           str(CAD / "6709K211.glb"))
    place["p_carriage"] = {"R": R_I, "t_mm": [0, RAILC, 0]}

    # standoffs (custom) -- carry the carriage plate up over the belt plane. Modeled
    # as one part so the attachment chain carriage.top -> standoff -> plate.bot is
    # physically continuous (without them the plate floats 3 mm above the carriage).
    CTOP = RAILC + 4.45                # carriage top face Y = 23.95
    lib["p_standoff"] = _p("CUSTOM-standoff", "standoff", {"note": "4x posts, carriage->plate"},
                           [f("bot", pl((0, CTOP, 0), (0, -1, 0)), "mounting_face"),
                            f("top", pl((0, PLATE_Y, 0), (0, 1, 0)), "mounting_face")],
                           _box_glb("CUSTOM-standoff", (44, PLATE_Y - CTOP, 30), (120, 120, 130)))
    place["p_standoff"] = {"R": R_I, "t_mm": [0, (CTOP + PLATE_Y) / 2, 0]}

    # carriage plate (custom) on standoffs above the belt plane
    lib["p_plate"] = _p("CUSTOM-plate", "carriage_plate", {"note": "4x M2 to carriage; holds clamp"},
                        [f("bot", pl((0, PLATE_Y, 0), (0, -1, 0)), "mounting_face"),
                         f("clamp_face", pl((XB, PLATE_Y, 0), (1, 0, 0)), "mounting_face")],
                        _box_glb("CUSTOM-plate", (62, 4, 44), (200, 160, 70)))
    place["p_plate"] = {"R": R_I, "t_mm": [11, PLATE_Y + 2, 0]}

    # belt clamp (custom) bridging plate down to the upper belt run. Two distinct
    # faces: `mount` bolts to the plate's vertical clamp_face (normal +X, same x=XB
    # plane); `grip` pinches the belt's upper run (normal +Y) and feeds belt_drive.
    lib["p_clamp"] = _p("CUSTOM-clamp", "belt_clamp", {"note": "pinches belt to plate"},
                        [f("mount", pl((XB, (PLATE_Y + (YB + PR)) / 2, 0), (1, 0, 0)), "mounting_face"),
                         f("grip", pl((XB, YB + PR, 0), (0, 1, 0)), "mounting_face")],
                        _box_glb("CUSTOM-clamp", (10, 4, 16), (180, 70, 70)))
    place["p_clamp"] = {"R": R_I, "t_mm": [XB, (PLATE_Y + (YB + PR)) / 2, 0]}

    # bearing brackets (custom): each bridges from the extrusion top (foot, normal
    # +Y) over the +X edge to the bearing line at z=+-ZP (seat, a bore on the X
    # rotation axis -- coaxial with the bearing/shaft). The earlier Z-end plates
    # were geometrically incapable of holding an X-axis bearing (the attachment
    # gate caught it); these sit beside each pulley.
    for s, z in [("1", ZP), ("2", -ZP)]:
        lib[f"p_brk{s}"] = _p(f"CUSTOM-brk{s}", "bearing_bracket", {"note": "extrusion -> bearing seat"},
                              [f("seat", ax((XB, YB, z), (1, 0, 0)), "bearing_seat", {"diameter": 6.35}),
                               f("foot", pl((6, TOP, z), (0, 1, 0)), "mounting_face")],
                              _box_glb(f"CUSTOM-brk{s}", (24, 9, 10), (110, 110, 120)))
        place[f"p_brk{s}"] = {"R": R_I, "t_mm": [13, TOP + 4.5, z]}

    # shafts, bearings, pulleys (rotors)
    for s, z in [("1", ZP), ("2", -ZP)]:
        lib[f"p_bear{s}"] = _p("57155K324", "ball_bearing", {"bore_mm": 6.35},
                               [f("bore", ax((XB, YB, ZP if s == "1" else -ZP), (1, 0, 0)),
                                 "bearing_seat", {"diameter": 6.35})], None)
        lib[f"p_shaft{s}"] = _p("1327K65", "rotary_shaft", {"od_mm": 6.35},
                                [f("axis", ax((XB, YB, z), (1, 0, 0)), "shaft_bore",
                                  {"diameter": 6.35, "kind": "external"})], str(CAD / "1327K65.glb"))
        lib[f"p_pulley{s}"] = _p("1277N16", "timing_pulley",
                                 {"od_mm": 30.16, "pitch_in": 0.2, "teeth": 15, "pitch_radius_mm": PR,
                                  "belt_width_in": 0.31},
                                 [f("bore", ax((XB, YB, z), (1, 0, 0)), "shaft_bore", {"diameter": 6.35}),
                                  f("pitch", ax((XB, YB, z), (1, 0, 0)), "pitch_circle",
                                    {"radius_mm": PR, "teeth": 15, "pitch_in": 0.2})],
                                 str(CAD / "1277N16.glb"))
        place[f"p_pulley{s}"] = {"R": R_ZX, "t_mm": [XB, YB, z]}
        place[f"p_shaft{s}"] = {"R": R_ZX, "t_mm": [XB - 6, YB, z]}   # offset so it spans bracket->pulley

    # belt (generated toothed loop)
    lib["p_belt"] = _p("1679K197", "timing_belt",
                       {"pitch_in": 0.2, "teeth": BELT_TEETH, "width_in": 0.25}, [], None)
    return lib, place


def main() -> bool:
    LIB.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
    lib, place = build()
    for ref, part in lib.items():
        with open(LIB / f"{part.part_number}_{ref}.json", "w") as fh:
            json.dump(part.to_json(), fh, indent=2)

    co = lambda a, b: Constraint("coincident", a, b)
    cp = lambda a, b: Constraint("coplanar", a, b)
    fixed = lambda iface, a, b, req=None: Mate(iface, [cp(a, b)], Joint("fixed"), requires=req or [])

    mates = [
        fixed("bolted", "p_subplate.bot", "p_ext.top", ["m5_screw", "m5_tnut"]),
        fixed("bolted", "p_rail.bot", "p_subplate.top", ["m3_screw"]),
        Mate("linear_slide", [Constraint("coaxial", "p_carriage.axis", "p_rail.axis")],
             Joint("slider", axis="p_rail.axis"), requires=["p_rail"]),
        fixed("bolted", "p_standoff.bot", "p_carriage.top", ["m2_screw"]),
        fixed("bolted", "p_plate.bot", "p_standoff.top", ["m2_screw"]),
        fixed("bolted", "p_clamp.mount", "p_plate.clamp_face", ["m3_screw"]),
        fixed("bolted", "p_brk1.foot", "p_ext.top", ["m5_screw", "m5_tnut"]),
        fixed("bolted", "p_brk2.foot", "p_ext.top", ["m5_screw", "m5_tnut"]),
        fixed("press_fit", "p_bear1.bore", "p_brk1.seat"),
        fixed("press_fit", "p_bear2.bore", "p_brk2.seat"),
        bearing_mount(shaft_axis="p_shaft1.axis", bore_axis="p_bear1.bore", requires=["p_bear1"]),
        bearing_mount(shaft_axis="p_shaft2.axis", bore_axis="p_bear2.bore", requires=["p_bear2"]),
        pulley_mount(pulley_bore="p_pulley1.bore", shaft_axis="p_shaft1.axis", requires=["collar"]),
        pulley_mount(pulley_bore="p_pulley2.bore", shaft_axis="p_shaft2.axis", requires=["collar"]),
        belt_drive(pitch_circle_a="p_pulley1.pitch", pitch_circle_b="p_pulley2.pitch",
                   belt_path="p_belt.loop", carriage_clamp=("p_belt.loop", "p_clamp.grip"),
                   requires=["p_belt"]),
    ]
    # fastener stand-ins so `requires` are filled (spec-only library entries)
    for fn, th in [("m5_screw", "M5"), ("m5_tnut", "M5"), ("m3_screw", "M3"),
                   ("m2_screw", "M2"), ("collar", None)]:
        lib[fn] = _p(f"CUSTOM-{fn}", "fastener", {"thread": th} if th else {}, [], None)

    asm = Assembly(name="rung2_belt_axis",
                   parts=[PartRef("p_ext", "6575N368", grounded=True)] +
                         [PartRef(r, lib[r].part_number) for r in
                          ["p_subplate", "p_rail", "p_carriage", "p_standoff", "p_plate", "p_clamp",
                           "p_brk1", "p_brk2", "p_bear1", "p_bear2",
                           "p_shaft1", "p_shaft2", "p_pulley1", "p_pulley2"]],
                   mates=mates, intended_dof=1, open_functions=["actuation_source", "belt_tensioner"])
    asm.center_distance_mm = C

    c1 = (XB, YB, ZP); c2 = (XB, YB, -ZP)
    belt = make_belt(c1, c2, PR, teeth=BELT_TEETH, pitch_in=0.2, width_in=0.25,
                     pulley_width_in=0.31, plane_normal=(1, 0, 0),
                     glb_path=str(CAD / "belt_loop.glb"))

    report = validate(asm, lib, belt_fit=belt)
    asm.save(OUT / "rung2_assembly.json")
    with open(OUT / "rung2_report.json", "w") as fh:
        json.dump(report.to_json(), fh, indent=2)
    place["p_belt"] = {"R": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "t_mm": [0, 0, 0]}  # belt in world coords
    # render manifest for the data-driven viewer: ref -> glb + colour
    render = [
        ("p_ext", "/cad/6575N368.glb", 0x7f8c9b), ("p_subplate", "/cad/CUSTOM-subplate.glb", 0x5b626b),
        ("p_rail", "/cad/6709K231.glb", 0xb9c0c8), ("p_carriage", "/cad/6709K211.glb", 0x9aa3ad),
        ("p_standoff", "/cad/CUSTOM-standoff.glb", 0x787e88),
        ("p_plate", "/cad/CUSTOM-plate.glb", 0xc9a24b), ("p_clamp", "/cad/CUSTOM-clamp.glb", 0xc0563f),
        ("p_brk1", "/cad/CUSTOM-brk1.glb", 0x6f7882), ("p_brk2", "/cad/CUSTOM-brk2.glb", 0x6f7882),
        ("p_pulley1", "/cad/1277N16.glb", 0xd9b24b), ("p_pulley2", "/cad/1277N16.glb", 0xd9b24b),
        ("p_belt", "/cad/belt_loop.glb", 0x3b4654),
    ]
    place["_render"] = [{"ref": r, "url": u, "color": c} for r, u, c in render]
    with open(OUT / "rung2_placements.json", "w") as fh:
        json.dump(place, fh, indent=2)

    print("=" * 72)
    print(f"RUNG 2 -- belt-driven linear axis  (center distance {C:.1f} mm, stroke ~{2*ZP-60:.0f} mm)")
    print("=" * 72)
    for g in report.gates:
        print(f"  [{'PASS' if g.passed else 'FAIL'}] {g.name}"
              f"{'' if g.blocking else ' (adv)'}: {g.detail}")
    m = report.mobility
    print("-" * 72)
    print(f"  mobility: {m.n_bodies} parts -> {m.n_rigid_groups} rigid groups; "
          f"M = 6*({m.n_rigid_groups}-1-{m.n_joints_reduced})+{m.sum_f}-{m.n_couplings} = {m.computed_dof}")
    print(f"  open_functions: {asm.open_functions}")
    print(f"  RESULT: {'ALL BLOCKING GATES PASS' if report.passed else 'FAILED'}")
    print("=" * 72)
    return report.passed


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
