"""Rung 0 -- screw + washer, washer seated under the head (Section 11).

Forces the pipeline itself: spec -> feature annotation, one coaxial + face-seat
mate, frame reconciliation, mobility readout. Residual 1 DOF (the washer is
free to spin about the screw axis) is the correct, hand-checkable answer for an
unclamped washer.

Data was retrieved live from mcmaster.com via Playwright (Section 3): spec
tables read off the rendered page, plus the 2-D DWG and the simplified
non-threaded 3-D STEP pulled from the CAD-download widget (no sign-in needed),
then tessellated STEP -> glTF. Provenance records the path.
"""
from __future__ import annotations

import json
from pathlib import Path

from ontology import Axis, Plane, Feature, Part, Mate, PartRef, Assembly
from ontology.interfaces import seated_revolute
from data import normalize_spec
from assembly import validate

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "library"
OUT = ROOT / "out"
CAD = ROOT / "cad"


def build_screw() -> Part:
    """91290A232 -- Black-Oxide Alloy Steel Socket Head Screw, M5 x 0.8, 16 mm."""
    raw = {
        "Thread Size": "M5",
        "Thread Pitch": "0.8 mm",
        "Length": "16 mm",
        "Head Diameter": "8.5 mm",
        "Head Height": "5 mm",
        "Threading": "Fully Threaded",
        "Material": "Black-Oxide Alloy Steel",
        "Fastener Strength Grade/Class": "Class 12.9",
    }
    spec = normalize_spec(raw, {
        "Thread Size": ("thread", "thread"),
        "Length": ("length", "mm"),
        "Head Diameter": ("head_od", "mm"),
        "Head Height": ("head_height", "mm"),
        "Material": ("material", "str"),
    })
    spec["thread_major"] = 5.0  # M5 nominal major diameter (mm)

    # Frame: origin at the centre of the under-head bearing face; +Z runs along
    # the screw axis from head toward tip (datum reconciled to this single frame).
    features = [
        Feature(
            id="axis",
            geometry=Axis(origin=(0, 0, 0), direction=(0, 0, 1)),
            role="shaft_bore",  # cylindrical shaft-engagement role; external side
            params={"diameter": spec["thread_major"], "kind": "external",
                    "thread": spec["thread"]},
        ),
        Feature(
            id="head_seat",
            geometry=Plane(origin=(0, 0, 0), normal=(0, 0, -1)),  # faces back toward head
            role="mounting_face",
            params={"od": spec["head_od"], "feature": "under_head_bearing_face"},
        ),
    ]
    return Part(
        part_number="91290A232",
        cls="socket_head_screw",
        source_url="https://www.mcmaster.com/91290A232/",
        retrieved_at="2026-06-18",
        raw_spec=raw,
        spec=spec,
        cad={
            "dwg_uri": str(CAD / "91290A232.dwg"),
            "step_uri": str(CAD / "91290A232.step"),
            "gltf_uri": str(CAD / "91290A232.glb"),
            "variant": "simplified_nonthreaded",  # '3-D STEP no threads'
            "step_href": "/mvC/Library/CAD2/.../91290A232_NO THREADS_....STEP",
        },
        # Frame reconciliation (Section 3): the annotation datum is the under-head
        # face; in the STEP/mesh that face sits at Z = +5.5 mm. mesh_seat_z records
        # the offset so the mesh can be expressed in this part frame.
        frame={"origin": [0, 0, 0], "handedness": "right",
               "datum": "centre of under-head bearing face, +Z head->tip",
               "mesh_seat_z": 5.5},
        features=features,
        provenance={"discovered_by": "playwright", "annotated_by": "manual",
                    "confidence": 0.95,
                    "note": "specs + DWG + STEP retrieved live off mcmaster.com (no sign-in); "
                            "mesh bbox 8.5x8.5x21mm confirms head Ø and 21mm overall length"},
    )


def build_washer() -> Part:
    """93475A240 -- 18-8 SS General Purpose Washer, M5, 5.3 mm ID, 10 mm OD."""
    raw = {
        "For Screw Size": "M5",
        "ID": "5.3 mm",
        "OD": "10.0 mm",
        "Thickness": "0.9 mm to 1.1 mm",
        "Washer Type": "Flat",
        "Material": "18-8 Stainless Steel",
        "Specifications Met": "DIN 125, ISO 7089",
    }
    spec = normalize_spec(raw, {
        "ID": ("id", "mm"),
        "OD": ("od", "mm"),
        "Material": ("material", "str"),
    })
    spec["thickness"] = 1.0  # nominal mid of the 0.9-1.1 mm range

    # Frame: origin at the centre of the mating (top) face -- the face that meets
    # the head underside; +Z along the hole axis, pointing away from the head.
    features = [
        Feature(
            id="bore",
            geometry=Axis(origin=(0, 0, 0), direction=(0, 0, 1)),
            role="clearance_hole",
            params={"diameter": spec["id"]},
        ),
        Feature(
            id="top_face",
            geometry=Plane(origin=(0, 0, 0), normal=(0, 0, 1)),  # contacts head underside
            role="mounting_face",
            params={"od": spec["od"], "thickness": spec["thickness"]},
        ),
    ]
    return Part(
        part_number="93475A240",
        cls="flat_washer",
        source_url="https://www.mcmaster.com/93475A240/",
        retrieved_at="2026-06-18",
        raw_spec=raw,
        spec=spec,
        cad={
            "dwg_uri": str(CAD / "93475A240.dwg"),
            "step_uri": str(CAD / "93475A240.step"),
            "gltf_uri": str(CAD / "93475A240.glb"),
            "variant": "as_modeled_no_threads",  # washer has no threads; '3-D STEP'
        },
        frame={"origin": [0, 0, 0], "handedness": "right",
               "datum": "centre of mating face, +Z away from head"},
        features=features,
        provenance={"discovered_by": "playwright", "annotated_by": "manual",
                    "confidence": 0.95,
                    "note": "specs + DWG + STEP retrieved live off mcmaster.com (no sign-in); "
                            "mesh bbox 10x10x1.1mm confirms OD and thickness"},
    )


def main() -> bool:
    LIB.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)

    screw, washer = build_screw(), build_washer()
    library = {"p_screw": screw, "p_washer": washer}

    # version the library entries (single source of truth, checked-in data)
    for part in (screw, washer):
        with open(LIB / f"{part.part_number}.json", "w") as fh:
            json.dump(part.to_json(), fh, indent=2)

    # assemble: one seated_revolute mate (coaxial + face-seat -> revolute)
    mate = seated_revolute(
        shaft_axis="p_screw.axis",
        bore_axis="p_washer.bore",
        seat_face="p_screw.head_seat",
        part_face="p_washer.top_face",
    )

    asm = Assembly(
        name="rung0_screw_washer",
        parts=[
            PartRef(ref="p_screw", part_number="91290A232", grounded=True),
            PartRef(ref="p_washer", part_number="93475A240", grounded=False),
        ],
        mates=[mate],
        intended_dof=1,            # washer free to spin -- 1 DOF
        open_functions=[],
    )

    report = validate(asm, library)
    asm.save(OUT / "rung0_assembly.json")
    with open(OUT / "rung0_report.json", "w") as fh:
        json.dump(report.to_json(), fh, indent=2)
    with open(OUT / "rung0_placements.json", "w") as fh:
        json.dump(report.placements, fh, indent=2)

    # ---- human-readable readout --------------------------------------------
    print("=" * 66)
    print("RUNG 0 -- screw + washer")
    print("=" * 66)
    print(f"  screw : {screw.part_number}  {screw.source_url}")
    print(f"  washer: {washer.part_number}  {washer.source_url}")
    print(f"  mate  : {mate.interface}  ({', '.join(c.type for c in mate.constraints)} "
          f"-> {mate.joint.type})")
    print("-" * 66)
    for g in report.gates:
        mark = "PASS" if g.passed else "FAIL"
        tag = "" if g.blocking else " (advisory)"
        print(f"  [{mark}] {g.name}{tag}: {g.detail}")
    print("-" * 66)
    m = report.mobility
    print(f"  mobility: M = 6*(L-1-j) + Sf - couplings = "
          f"6*({m.n_rigid_groups}-1-{m.n_joints_reduced}) + {m.sum_f} - {m.n_couplings} = {m.computed_dof}")
    print(f"  RESULT: {'ALL BLOCKING GATES PASS' if report.passed else 'FAILED'} "
          f"(computed DOF {m.computed_dof} == intended {asm.intended_dof})")
    print("=" * 66)
    return report.passed


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
