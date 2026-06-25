"""Rung 1 -- bracket bolted to a T-slot extrusion (Section 11).

Target DOF 0 (rigid). New capabilities forced (and ratified in
out/ontology_log/rung1.md):
  * hole PATTERN whose coordinates come from the 2-D DWG, not a scalar spec
    (4844N135: 4 holes, 25.00 mm pitch, centred on the 100 mm length);
  * pattern-to-pattern mating via `bolt_pattern` -> 4 `bolt_joint`s;
  * intentional OVER-CONSTRAINT: 4 bolts on one face = 4 fixed joints between
    the same body pair; the mobility gate merges rigid bodies and reports the
    surplus as benign redundancy instead of a fault.

BOM (all retrieved live from mcmaster.com, no sign-in):
  rail    6575N368  25 mm single four-slot T-slotted rail (slot 6.5 mm)
  bracket 4844N135  flat 4-hole surface bracket, M6, 25 mm pitch
  screw   91290A320 M6x15 socket head cap screw  (fills `requires`)
  t-nut   M6 drop-in nut included with 4844N135   (fills `requires`)

The screw and T-nut are fasteners that *realize* each bolt_joint; they live in
the library and in `requires`, not in the kinematic body list.
"""
from __future__ import annotations

import json
from pathlib import Path

from ontology import Axis, Plane, Feature, Part, PartRef, Assembly
from ontology.interfaces import bolt_pattern
from data import normalize_spec
from assembly import validate

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "library"
OUT = ROOT / "out"
CAD = ROOT / "cad"

# hole pattern read off the 2-D drawing of 4844N135: 4 holes, 25.0 mm pitch,
# centred on the 100 mm length -> these Z offsets (mm).
HOLE_Z = [-37.5, -12.5, 12.5, 37.5]


def build_rail() -> Part:
    """6575N368 -- 25 mm single four-slot T-slotted framing rail."""
    raw = {"Rail Height": "25mm", "Rail Width": "25mm", "T-Slot Width": "6.5mm",
           "T-Slot Depth": "8.1mm", "Material": "6560 Aluminum", "Rail Construction": "Solid"}
    spec = normalize_spec(raw, {
        "Rail Height": ("height", "mm"), "Rail Width": ("width", "mm"),
        "T-Slot Width": ("slot_width", "mm"), "T-Slot Depth": ("slot_depth", "mm"),
        "Material": ("material", "str"),
    })
    spec["length"] = 304.8  # 12" representative length from the STEP

    # Frame: cross-section centre at origin, length along Z. The +X face carries
    # the slot we mount to (slot centred on the face per the cross-section DWG).
    face_x = spec["width"] / 2.0   # 12.5
    feats = [Feature(id="mount_face",
                     geometry=Plane(origin=(face_x, 0, 0), normal=(1, 0, 0)),
                     role="mounting_face", params={"face": "+X slot face"})]
    # 4 T-nut threaded holes at the bracket's hole positions along the slot.
    for i, z in enumerate(HOLE_Z):
        feats.append(Feature(
            id=f"tnut_{i}",
            geometry=Axis(origin=(face_x, 0, z), direction=(1, 0, 0)),
            role="threaded_hole", params={"diameter": 6.0, "thread": "M6"}))
    return Part(
        part_number="6575N368", cls="t_slot_extrusion",
        source_url="https://www.mcmaster.com/6575N368/", retrieved_at="2026-06-18",
        raw_spec=raw, spec=spec,
        cad={"dwg_uri": str(CAD / "6575N368.dwg"), "step_uri": str(CAD / "6575N368.step"),
             "gltf_uri": str(CAD / "6575N368.glb"), "variant": "as_modeled"},
        frame={"origin": [0, 0, 0], "handedness": "right",
               "datum": "cross-section centre, length +Z, mount on +X face",
               # frame reconciliation (Section 3): the +X mount face sits at
               # mesh X = +12.5 mm (half of the 25 mm width).
               "mount_face_mesh_x": 12.5},
        features=feats,
        provenance={"discovered_by": "playwright", "annotated_by": "manual", "confidence": 0.9,
                    "note": "25mm single 4-slot; slot centred on each face (cross-section DWG); "
                            "T-nut positions induced by the bracket pattern along the slot"})


def build_bracket() -> Part:
    """4844N135 -- flat surface bracket, 4 holes @ 25 mm pitch, M6."""
    raw = {"For Rail Height": "25mm", "Number of Mounting Fasteners Included": "4",
           "Mounting Fastener Thread Size": "M6", "Length": "3.937 in"}
    spec = {
        "thread": "M6", "hole_dia": 6.5, "num_holes": 4, "hole_pitch": 25.0,
        "plate_length": 100.0, "plate_width": 25.3, "plate_thickness": 4.0,  # from DWG
    }
    # Frame: centre of the mounting (back) face; mounting normal +X (into rail),
    # plate length along Z. 4 clearance holes on the length, axis along +X.
    feats = [Feature(id="mount_face",
                     geometry=Plane(origin=(0, 0, 0), normal=(1, 0, 0)),
                     role="mounting_face", params={})]
    for i, z in enumerate(HOLE_Z):
        feats.append(Feature(
            id=f"hole_{i}",
            geometry=Axis(origin=(0, 0, z), direction=(1, 0, 0)),
            role="clearance_hole", params={"diameter": spec["hole_dia"]}))
    return Part(
        part_number="4844N135", cls="mounting_bracket",
        source_url="https://www.mcmaster.com/4844N135/", retrieved_at="2026-06-18",
        raw_spec=raw, spec=spec,
        cad={"dwg_uri": str(CAD / "4844N135.dwg"), "step_uri": str(CAD / "4844N135.step"),
             "gltf_uri": str(CAD / "4844N135.glb"), "variant": "as_modeled_with_fasteners"},
        frame={"origin": [0, 0, 0], "handedness": "right",
               "datum": "centre of mounting face, +X normal, length +Z",
               # frame reconciliation: in the STEP/mesh the plate normal is local
               # Z, the length is local Y, and the mounting (T-nut) face sits at
               # mesh Z = -2 mm (the 4 mm plate is centred at Z=0).
               "mount_face_mesh_z": -2.0},
        features=feats,
        provenance={"discovered_by": "playwright", "annotated_by": "manual", "confidence": 0.95,
                    "note": "hole pattern (4 holes @ 25.00 mm pitch, centred on 100 mm length) "
                            "read off the 2-D DWG -- the geometry authority (Section 3)"})


def build_screw() -> Part:
    """91290A320 -- M6 x 1, 15 mm socket head cap screw."""
    raw = {"Thread Size": "M6", "Thread Pitch": "1 mm", "Length": "15 mm",
           "Head Diameter": "10 mm", "Head Height": "6 mm"}
    spec = normalize_spec(raw, {"Thread Size": ("thread", "thread"), "Length": ("length", "mm"),
                                "Head Diameter": ("head_od", "mm")})
    spec["thread_major"] = 6.0
    feats = [Feature(id="axis", geometry=Axis(origin=(0, 0, 0), direction=(0, 0, 1)),
                     role="shaft_bore", params={"diameter": 6.0, "kind": "external", "thread": "M6"})]
    return Part(
        part_number="91290A320", cls="socket_head_screw",
        source_url="https://www.mcmaster.com/91290A320/", retrieved_at="2026-06-18",
        raw_spec=raw, spec=spec,
        cad={"dwg_uri": None, "step_uri": str(CAD / "91290A320.step"),
             "gltf_uri": str(CAD / "91290A320.glb"), "variant": "simplified_nonthreaded"},
        frame={"origin": [0, 0, 0], "handedness": "right"}, features=feats,
        provenance={"discovered_by": "playwright", "annotated_by": "manual", "confidence": 0.95,
                    "note": "M6x15 fills bolt_joint `requires`"})


def build_tnut() -> Part:
    """M6 drop-in T-nut included with bracket 4844N135 (fits the 6.5 mm slot)."""
    return Part(
        part_number="4844N135-TNUT", cls="t_slot_nut",
        source_url="https://www.mcmaster.com/4844N135/", retrieved_at="2026-06-18",
        raw_spec={"included_with": "4844N135", "Thread Size": "M6"},
        spec={"thread": "M6", "fits_slot": 6.5, "fits_rail": 25.0},
        cad={"dwg_uri": None, "step_uri": None, "gltf_uri": None, "variant": "none"},
        frame={"origin": [0, 0, 0], "handedness": "right"}, features=[],
        provenance={"discovered_by": "manual", "annotated_by": "manual", "confidence": 0.8,
                    "note": "M6 T-nut included with 4844N135 (qty 4); sized for the 25mm/6.5mm "
                            "slot by design -- fills bolt_joint `requires`"})


def main() -> bool:
    LIB.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
    rail, bracket, screw, tnut = build_rail(), build_bracket(), build_screw(), build_tnut()
    library = {"p_rail": rail, "p_bracket": bracket, "p_screw": screw, "p_tnut": tnut}
    for part in library.values():
        with open(LIB / f"{part.part_number}.json", "w") as fh:
            json.dump(part.to_json(), fh, indent=2)

    # pattern-to-pattern: 4 bolt_joints, bracket holes -> rail T-nuts
    mates = bolt_pattern(
        holes=[f"p_bracket.hole_{i}" for i in range(4)],
        threaded_holes=[f"p_rail.tnut_{i}" for i in range(4)],
        face_a="p_bracket.mount_face", face_b="p_rail.mount_face",
        requires=["p_screw", "p_tnut"],
    )
    asm = Assembly(
        name="rung1_bracket_extrusion",
        parts=[PartRef(ref="p_rail", part_number="6575N368", grounded=True),
               PartRef(ref="p_bracket", part_number="4844N135", grounded=False)],
        mates=mates, intended_dof=0, open_functions=[],
    )

    report = validate(asm, library)
    asm.save(OUT / "rung1_assembly.json")
    with open(OUT / "rung1_report.json", "w") as fh:
        json.dump(report.to_json(), fh, indent=2)
    # placements consumed by the viewer (same solve the interference gate used)
    with open(OUT / "rung1_placements.json", "w") as fh:
        json.dump(report.placements, fh, indent=2)

    print("=" * 68)
    print("RUNG 1 -- bracket bolted to T-slot extrusion")
    print("=" * 68)
    print(f"  rail    : {rail.part_number}   {rail.source_url}")
    print(f"  bracket : {bracket.part_number}   {bracket.source_url}")
    print(f"  pattern : {len(mates)} x bolt_joint  (holes @ 25mm pitch from 2-D DWG)")
    print(f"  fasteners: {screw.part_number} (M6x15) + {tnut.part_number}")
    print("-" * 68)
    for g in report.gates:
        mark = "PASS" if g.passed else "FAIL"
        tag = "" if g.blocking else " (advisory)"
        print(f"  [{mark}] {g.name}{tag}: {g.detail}")
    print("-" * 68)
    m = report.mobility
    print(f"  mobility: merge {m.n_bodies} bodies over fixed joints -> {m.n_rigid_groups} rigid group(s); "
          f"M = 6*({m.n_rigid_groups}-1-{m.n_joints_reduced}) + {m.sum_f} = {m.computed_dof}")
    print(f"  redundancy: {m.redundant_fixed} extra bolt(s) = intentional over-constraint (benign)")
    print(f"  RESULT: {'ALL BLOCKING GATES PASS' if report.passed else 'FAILED'} "
          f"(computed DOF {m.computed_dof} == intended {asm.intended_dof})")
    print("=" * 68)
    return report.passed


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
