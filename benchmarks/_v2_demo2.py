"""v2 matchers on the REAL load-bearing joint (plate<->block) + T-slot capture.

Exercises the geometric matchers added for the existing parts:
  * pattern_correspondence  -- the 4x M4 plate-to-block bolt pattern (the real joint),
                               searched over permutations (not zipped); reports the
                               2-fold rectangle ambiguity honestly.
  * bounded_area_overlap    -- the plate seating flush on the block top (contact patch),
                               not infinite-plane coplanarity.
  * profile_containment     -- a T-nut section captured in a T-slot section (synthetic
                               pair; proves the swept_profile capture logic + a FAIL).

The plate seating pose (R = 180deg about Y, t=[100,24,0]) is the one the engine
solves in rung2_assemble.py from these same measured holes; here we apply it and
CHECK, so the look and the engine agree (Hard Rule 1b).
"""
from __future__ import annotations

import json
from pathlib import Path

from ontology.schema_v2 import PartDefinition
from ontology.ports import EngagementPort
from ontology import ports_match as M

ROOT = Path(__file__).resolve().parent.parent
LIBV2 = ROOT / "library_v2"
I3 = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
FLIP_Y = [[-1, 0, 0], [0, 1, 0], [0, 0, -1]]      # 180 deg about Y


def load(stem):
    return PartDefinition.from_json(json.loads((LIBV2 / f"{stem}.json").read_text()))


def main():
    block = load("SSEB20-220_block")
    plate = load("SL-TBLGS3M100-plate")
    place_block = {"R": I3, "t_mm": [0, 0, 0]}
    place_plate = {"R": FLIP_Y, "t_mm": [100, 24, 0]}

    print("=" * 70)
    print("v2 MATCHERS -- plate<->block joint (real measured geometry)")
    print("=" * 70)
    print(M.pattern_correspondence(plate, plate.port_groups[0], place_plate,
                                   block, block.port_groups[0], place_block))
    print(M.bounded_area_overlap(plate.port("mount_face"), block.port("top"),
                                 place_plate, place_block))

    print("-" * 70)
    print("T-SLOT CAPTURE (swept_profile) -- synthetic T-nut in a T-slot section")
    # receiver: a T-slot channel cross-section (u=width, v=depth); insert: a T-nut
    # that fits inside it; and a too-wide nut that must FAIL.
    def swept(pid, outer, polarity, s=(0.0, 304.8)):
        return EngagementPort(id=pid, family="swept_profile", polarity=polarity,
            geometry={"sweep_path": {"axis": {"origin": [0, 0, 0], "direction": [0, 0, 1]}},
                      "sweep_interval_mm": {"min": s[0], "max": s[1], "unit": "mm"},
                      "section_frame": {"origin": [0, 0, 0], "x_axis": [1, 0, 0], "y_axis": [0, 1, 0], "z_axis": [0, 0, 1]},
                      "section_profile_uv_mm": {"outer": outer, "holes": []},
                      "material_side": ("outside_profile" if polarity == "insert" else "inside_profile")})
    # proper T-slot: narrow throat at top (x +-4, y 0..-3), wide cavity below (x +-8, y -3..-12)
    slot = swept("slot", [[-4, 0], [4, 0], [4, -3], [8, -3], [8, -12], [-8, -12], [-8, -3], [-4, -3]], "receiver")
    # T-nut: neck through the throat (x +-3.5), body filling the cavity (x +-7.5, y -3..-11)
    tnut = swept("tnut", [[-3.5, 0], [3.5, 0], [3.5, -3], [7.5, -3], [7.5, -11], [-7.5, -11], [-7.5, -3], [-3.5, -3]], "insert")
    wide = swept("wide_nut", [[-9, -3.5], [9, -3.5], [9, -11], [-9, -11]], "insert")
    print(M.profile_containment(tnut, slot))
    print(M.profile_containment(wide, slot))

    print("-" * 70)
    print("Read: bolt pattern coincides (RMS ~0) under a permutation SEARCH, not a zip;")
    print("plate seats flush with a real contact patch (area, not infinite-plane);")
    print("the captured T-nut PASSES, the oversize nut FAILS containment -- the slot")
    print("capture logic actually bites.")


if __name__ == "__main__":
    main()
