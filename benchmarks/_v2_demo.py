"""v2 ontology foundation smoke-test (migration steps A.2-A.8, partial).

Loads two MIGRATED v2 parts (idler + shoulder screw) and runs the family matchers
on the idler<->screw revolute. The point: the engine SURFACES the shoulder-span
question (STATE r6's idler bug) as a NUMBER, not prose -- axial_overlap reports the
shoulder engages only 10 of the bore's 15 mm and asks for review (required_closure).

Also exercises threaded + periodic matchers against inline counterpart ports so all
four implemented families execute. Pure numbers, no render.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ontology.schema_v2 import PartDefinition
from ontology.ports import EngagementPort
from ontology import ports_match as M

ROOT = Path(__file__).resolve().parent.parent
LIBV2 = ROOT / "library_v2"
I3 = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def load(pn: str) -> PartDefinition:
    return PartDefinition.from_json(json.loads((LIBV2 / f"{pn}.json").read_text()))


def main():
    idler = load("SHTF20S3M100-5")
    screw = load("90263A239")
    bore = idler.port("bore")            # cylindrical receiver, world X axis at identity
    shoulder = screw.port("shoulder")    # cylindrical insert, local Z axis
    thread = screw.port("thread")        # threaded external M4x0.7

    # place idler at identity: bore axis runs world +X through (7.5,0,0), spans X 0..15.
    place_idler = {"R": I3, "t_mm": [0, 0, 0]}
    # place screw so its local-Z shoulder axis maps onto world +X, shoulder centred
    # on the bore (t_x=16.5 -> shoulder world X 2.5..12.5, inside bore 0..15).
    R_zx = [[0, 0, 1], [1, 0, 0], [0, 1, 0]]      # local Z -> world X
    place_screw = {"R": R_zx, "t_mm": [16.5, 0, 0]}

    print("=" * 70)
    print("v2 ENGINE -- idler<->shoulder-screw revolute (cylindrical family)")
    print("=" * 70)
    print(M.radial_fit(shoulder, bore, place_screw, place_idler))
    print(M.axial_overlap(shoulder, bore, place_screw, place_idler))

    # threaded: screw external M4x0.7 vs an inline bracket tapped M4 hole (internal)
    bracket_tap = EngagementPort(
        id="bracket_tap", family="threaded", polarity="internal",
        geometry={"axis": {"origin": [0, 40, 0], "direction": [0, 0, 1]},
                  "axial_interval_mm": {"min": 0, "max": 3.2, "unit": "mm"},
                  "thread": {"standard": "ISO_metric", "designation": "M4x0.7",
                             "pitch_mm": 0.7, "handedness": "right"}})
    print(M.thread_match(thread, bracket_tap))

    # periodic: idler S3M teeth vs an inline S3M belt toothed side -> should mesh;
    # also show a GT2 mismatch FAILS honestly (the old cross-pitch bug).
    teeth = idler.port("teeth")
    belt_s3m = EngagementPort(
        id="belt_s3m", family="periodic", polarity="opposing",
        geometry={"subtype": "linear",
                  "support": {"plane": {"origin": [0, 0, 0], "normal": [0, 1, 0]},
                              "active_region_mm": {"min": -100, "max": 100, "unit": "mm"}},
                  "periodicity": {"pitch_mm": 3.0, "count": None,
                                  "active_width_mm": {"min": 9, "max": 10, "unit": "mm"}},
                  "profile": {"family": "S3M", "parameters": {}}})
    belt_gt2 = EngagementPort(
        id="belt_gt2", family="periodic", polarity="opposing",
        geometry={"subtype": "linear",
                  "support": {"plane": {"origin": [0, 0, 0], "normal": [0, 1, 0]},
                              "active_region_mm": {"min": -100, "max": 100, "unit": "mm"}},
                  "periodicity": {"pitch_mm": 2.0, "count": None,
                                  "active_width_mm": {"min": 9, "max": 10, "unit": "mm"}},
                  "profile": {"family": "GT2", "parameters": {}}})
    print(M.pitch_profile_match(teeth, belt_s3m))
    print(M.pitch_profile_match(teeth, belt_gt2))

    print("-" * 70)
    print("Read: radial_fit PASS (coaxial, 0 clearance); axial_overlap UNKNOWN/")
    print("required_closure (shoulder spans 10 of 15 mm -> the STATE r6 bug, now a")
    print("NUMBER + review item); thread M4 matches; S3M meshes, GT2 fails honestly.")


if __name__ == "__main__":
    main()
