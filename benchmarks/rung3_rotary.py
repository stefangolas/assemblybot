"""Rung 3 -- RU85 belt-driven rotary stage, CORE STACK on the v2 ontology.

Assembles the load-bearing heart of the stage from REAL CAD:
  frame ground -> ROTARY_BASE -> RU85 outer ring -[revolute]- inner ring
                  -> ROTARY_ADAPTER -> 72T S5M pulley
and verifies every interface with the v2 matchers + the rung-3 race-segregation check
+ the pass-through corridor, then writes ONE placement source and renders for the LOOK.

World frame: stage axis = world Z (up). Base top (Datum A) at Z=0; bearing spans Z=0..15
(outer ring on the base, inner ring up); adapter boss on the inner-ring top (Z=15); pulley
piloted+bolted on the adapter top (Z=27). The motor/belt/tabletop/standoffs extend this
(catalog parts staged separately); this script proves the rotary joint + driven pulley.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

from ontology.schema_v2 import PartDefinition
from ontology.templates import TEMPLATES
from ontology import ports_match as PM

ROOT = Path(__file__).resolve().parent.parent
OUT, LIBV2 = ROOT / "out", ROOT / "library_v2"

I = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
# CAD +X -> world +Z (bearing & pulley are X-native; custom parts are Z-native)
R_XZ = [[0, 0, -1], [0, 1, 0], [1, 0, 0]]


def load(stem):
    return PartDefinition.from_json(json.loads((LIBV2 / f"{stem}.json").read_text()))


def build():
    lib = {
        "p_base": load("ROTARY_BASE_RU85_REV_A"),
        "p_brg": load("RU85UUC0"),
        "p_adp": load("ROTARY_ADAPTER_RU85_S5M_REV_A"),
        "p_pul": load("HTPA72S5M150-A-H50-KFC85-K5.5"),
    }
    # analytic stack placement; every interface is then VERIFIED by the matchers (RMS/area/clearance)
    placements = {
        "p_base": {"R": I,    "t_mm": [0, 0, 0]},        # top Datum A at Z=0
        "p_brg":  {"R": R_XZ, "t_mm": [0, 0, 0]},        # X=0 face -> Z=0 (on base), X=15 -> Z=15
        "p_adp":  {"R": I,    "t_mm": [0, 0, 15.0]},     # boss bottom -> Z=15 (inner-ring top)
        "p_pul":  {"R": R_XZ, "t_mm": [0, 0, 27.0]},     # mount face -> Z=27 (adapter top), bore on pilot
    }
    return lib, placements


def main():
    OUT.mkdir(exist_ok=True)
    lib, pl = build()

    print("=== RUNG 3 -- RU85 ROTARY STAGE (core stack) ===\n")

    # 1) base -> bearing OUTER ring  (+ race-segregation vs inner ring)
    m1 = TEMPLATES["bearing_ring_mount"].bind(
        {"plate": "p_base.outer_ring_seat", "ring": "p_brg.outer_ring_base_face",
         "forbidden": "p_brg.inner_ring_base_face",
         "plate_group": "p_base:outer_ring_pattern", "ring_group": "p_brg:outer_ring_pattern",
         "screws": "p_base.outer_ring_thread_1"})
    print("[A] BASE -> RU85 OUTER ring (stationary):")
    for r in m1.evaluate(lib, pl).results:
        print("   ", r)

    # 2) adapter -> bearing INNER ring (+ race-segregation: boss vs outer ring)
    m2 = TEMPLATES["bearing_ring_mount"].bind(
        {"plate": "p_adp.inner_race_boss", "ring": "p_brg.inner_ring_adapter_face",
         "forbidden": "p_brg.outer_ring_adapter_face",
         "plate_group": "p_adp:inner_race_pattern", "ring_group": "p_brg:inner_ring_pattern",
         "screws": "p_brg.inner_thread_1"})
    print("\n[B] ROTARY ADAPTER -> RU85 INNER ring (rotating):")
    for r in m2.evaluate(lib, pl).results:
        print("   ", r)

    # 2b) the DECIDING relief check: adapter's relieved underside clears the outer ring by 0.5 mm (#3)
    relief = PM.annular_clearance(lib["p_adp"].port("relieved_underside"),
                                  lib["p_brg"].port("outer_ring_adapter_face"),
                                  pl["p_adp"], pl["p_brg"])
    print("    [relief #3]", relief)

    # 3) pulley piloted + bolted on the adapter (locate vs clamp)
    m3 = TEMPLATES["pilot_located_bolted_hub"].bind(
        {"hub": "p_pul.bore", "pilot": "p_adp.pulley_pilot",
         "hub_seat": "p_pul.mount_face", "seat": "p_adp.pulley_seat",
         "hub_group": "p_pul:mount_pattern", "seat_group": "p_adp:pulley_pattern"})
    print("\n[C] 72T PULLEY -> ADAPTER (pilot locates, bolts clamp):")
    for r in m3.evaluate(lib, pl).results:
        print("   ", r)

    # 4) the bearing's internal revolute = the one output DOF (#10)
    rev = TEMPLATES["crossed_roller_revolute"].bind(
        {"inner": "p_brg.bore", "outer": "p_brg.bore"})
    print(f"\n[D] RU85 internal joint: {rev.template.result.type.upper()} "
          f"(raceway closure) -> the stage's single rotary output DOF")

    # 5) pass-through corridor (#9): every part's central bore must clear Ø45 (R22.5), coaxial on Z
    print("\n[E] PASS-THROUGH corridor (>= Ø45):")
    ok = True
    for ref, pid in (("p_base", "pass_through"), ("p_brg", "bore"),
                     ("p_adp", "pass_through"), ("p_pul", "bore")):
        rin = lib[ref].port(pid).radial_interval().min
        clear = rin >= 22.5 - 1e-6
        ok = ok and clear
        print(f"    {ref:7s}.{pid:13s} IR={rin:5.1f} mm  Ø{2*rin:5.1f}  {'CLEAR' if clear else 'BLOCKED'}")
    print(f"    -> corridor {'UNOBSTRUCTED Ø45 through the whole stack' if ok else 'BLOCKED'}")

    # one placement source for math + viewer
    render = [
        ("p_base", "/cad/ROTARY_BASE_RU85_REV_A.glb",        0x8a9097),
        ("p_brg",  "/cad/RU85UUC0.glb",                       0xb5a642),
        ("p_adp",  "/cad/ROTARY_ADAPTER_RU85_S5M_REV_A.glb",  0xc0563f),
        ("p_pul",  "/cad/HTPA72S5M150.glb",                   0x4a7fb0),
    ]
    out = dict(pl)
    out["_render"] = [{"ref": r, "url": u, "color": c} for r, u, c in render]
    (OUT / "rung3_placements.json").write_text(json.dumps(out, indent=2))
    print("\nwrote out/rung3_placements.json")

    try:
        from benchmarks._shot import shoot
        imgs = shoot("out/rung3_placements.json", "out/rung3", "", ("iso", "x", "z"))
        print("rendered:", ", ".join(imgs))
    except Exception as e:  # noqa: BLE001
        print(f"(render skipped: {e})")


if __name__ == "__main__":
    main()
