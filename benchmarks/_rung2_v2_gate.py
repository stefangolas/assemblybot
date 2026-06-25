"""Run the v2 three-state load-path gate on the SOLVED rung-2 poses -- FULL CHAIN.

rung2_v2.build() solves the moving group (plate, idlers, belt) from template `enforce`.
This wires EVERY load-bearing edge to ground (p_ext) and asks the closure question for
every body. Chain (each edge geometry-checked):

  belt.run_lower --belt_capture(jaw, plate.grip)--> plate         (belt sandwiched)
  plate.mount_face --bounded_bolt_pattern_seat--> block.top
  block.guide_channel --profile_carriage_on_guide--> rail.guide   (slider)
  rail.bottom --tslot_captured_mount(HNTT6-5 nut)--> ext.tslot     (+ M5x16 clamp screw)
  bracket.foot --tslot_captured_mount(HNTT6-5 nut)--> ext.tslot    (+ M5x10 clamp screw)
  shoulder_screw.thread --shoulder_screw_into_tapped_support--> bracket.axle (M4 tap)
  idler.bore --inner_race_axial_retention(2x DWSSS spacers)--> shoulder_screw.shoulder

All parts are now real (T-slot nut HNTT6-5, spacer DWSSS-D7.5-V5-L3, M5 SHCS, belt
HTUN540S3M-100). Target: every body HELD_CONFIRMED.
"""
from __future__ import annotations

import json

from benchmarks.rung2_v2 import build, load, R_I, IDLER_X
from ontology.templates import TEMPLATES
from ontology import load_path as LP


def main():
    lib, placements, *_ = build()

    # ---- extra structural bodies (rail, fasteners, jaw, belt) -------------------
    lib["p_rail"] = load("SSEB20-220_rail")
    lib["p_nut_rail"] = load("HNTT6-5_tnut")
    lib["p_nut_brk1"] = load("HNTT6-5_tnut")
    lib["p_nut_brk2"] = load("HNTT6-5_tnut")
    lib["p_scr_rail"] = load("ISO4762-M5x0.8-16")
    lib["p_scr_brk1"] = load("ISO4762-M5x0.8-10")
    lib["p_scr_brk2"] = load("ISO4762-M5x0.8-10")
    lib["p_scr_plt"] = load("ISO4762-M4x0.7-12")    # plate->block guide-mount screws
    for iref in ("p_idl1", "p_idl2"):
        lib[f"p_shim_{iref}_a"] = load("DWSSS-D7.5-V5-L3_spacer")
        lib[f"p_shim_{iref}_b"] = load("DWSSS-D7.5-V5-L3_spacer")

    # placements: rail/belt in register with the native frame (identity); fasteners
    # at nominal stations (their checks -- thread_match / profile_containment /
    # pitch_profile_match -- are placement-independent, so nominal poses are honest here).
    placements["p_rail"] = {"R": R_I, "t_mm": [0, 0, 0]}
    placements["p_rail"] = {"R": R_I, "t_mm": [0, 0, 0]}
    placements["p_nut_rail"] = {"R": R_I, "t_mm": [0.0, 0.0, 0.0]}
    placements["p_nut_brk1"] = {"R": R_I, "t_mm": [IDLER_X[0], 0.0, -11.7]}
    placements["p_nut_brk2"] = {"R": R_I, "t_mm": [IDLER_X[1], 0.0, -11.7]}
    placements["p_scr_rail"] = {"R": R_I, "t_mm": [0.0, 5.5, 0.0]}
    placements["p_scr_brk1"] = {"R": R_I, "t_mm": [IDLER_X[0] + 5, 5.0, -11.7]}
    placements["p_scr_brk2"] = {"R": R_I, "t_mm": [IDLER_X[1] + 5, 5.0, -11.7]}
    placements["p_scr_plt"] = {"R": R_I, "t_mm": [80.0, 24.0, 15.0]}
    for iref, x in (("p_idl1", IDLER_X[0]), ("p_idl2", IDLER_X[1])):
        placements[f"p_shim_{iref}_a"] = {"R": R_I, "t_mm": [x, 40.0, -7.0]}
        placements[f"p_shim_{iref}_b"] = {"R": R_I, "t_mm": [x, 40.0, 7.0]}

    # ---- the full instance list -------------------------------------------------
    inst = []
    # belt sandwiched by the jaw against the plate's toothed grip (load-bearing backing).
    # belt_run_seated verifies the grip is actually ON the belt run in world space.
    inst.append(TEMPLATES["belt_capture"].bind(
        {"belt": "p_belt.run_lower", "grip": "p_plt.grip_teeth", "jaw": "p_jaw.clamp_teeth",
         "grip_group": "p_plt:belt_clamp_holes", "jaw_group": "p_jaw:clamp_holes"}))
    # plate fastened onto the block top by the 4x M4 guide-mount screws (the
    # bolt-pattern closure -- bind the real screw part so it is a confirmed fastener).
    inst.append(TEMPLATES["bounded_bolt_pattern_seat"].bind(
        {"plate": "p_plt.mount_face", "seat": "p_blk.top",
         "plate_group": "p_plt:guide_mount", "seat_group": "p_blk:mount_pattern",
         "screws": "p_scr_plt.thread"}))
    # block slides on the rail
    inst.append(TEMPLATES["profile_carriage_on_guide"].bind(
        {"carriage": "p_blk.guide_channel", "guide": "p_rail.guide"}))
    # rail + each bracket foot captured into the extrusion slot by a real HNTT6-5
    # T-slot nut. The tslot_captured_mount IS the modeled mount (its integral
    # captured-profile closure = the nut trapped by the slot lips); the real M5 clamp
    # screws (p_scr_rail / p_scr_brk*) physically realize the clamp and ship in the BOM,
    # but are not separate load-path edges -- modeling them as screw->nut edges only
    # created orphan fastener bodies double-counting this same joint.
    inst.append(TEMPLATES["tslot_captured_mount"].bind(
        {"mounted": "p_rail.bottom", "slot": "p_ext.tslot_top", "nut": "p_nut_rail.captured_profile"}))
    for bref, nut in (("p_brk1", "p_nut_brk1"), ("p_brk2", "p_nut_brk2")):
        inst.append(TEMPLATES["tslot_captured_mount"].bind(
            {"mounted": f"{bref}.foot", "slot": "p_ext.tslot_top", "nut": f"{nut}.captured_profile"}))
    # shoulder screw anchored to the bracket (M4 tap); idler retained on the shoulder
    for iref, sref, bref in (("p_idl1", "p_scr1", "p_brk1"), ("p_idl2", "p_scr2", "p_brk2")):
        inst.append(TEMPLATES["shoulder_screw_into_tapped_support"].bind(
            {"screw": f"{sref}.thread", "support": f"{bref}.axle_hole"}))
        inst.append(TEMPLATES["inner_race_axial_retention"].bind(
            {"rotor": f"{iref}.bore", "journal": f"{sref}.shoulder",
             "spacer_a": f"p_shim_{iref}_a.seat", "spacer_b": f"p_shim_{iref}_b.seat"}))

    rep = LP.evaluate(inst, lib, placements, ground=["p_ext"])
    print("=== RUNG 2 v2 LOAD-PATH GATE (FULL CHAIN, ground=p_ext) ===")
    print(rep.text())
    print("-" * 64)
    print(f"all bodies HELD_CONFIRMED? {rep.all_confirmed}")


if __name__ == "__main__":
    main()
