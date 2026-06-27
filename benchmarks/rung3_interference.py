"""Rung-3 interference config + standalone runner.

The general static+swept overlap gate lives in assembly/interference.py and runs as part of
the main verification set (see benchmarks/rung3_assembly.py). This file holds only the rung-3
KNOWLEDGE the generic gate needs -- which refs form the rotating output group (for the swept
check) and which contacts are BY DESIGN -- and exposes them so the canonical build reuses them.
"""
from __future__ import annotations
import json
from pathlib import Path

from assembly import interference as IF

ROOT = Path(__file__).resolve().parent.parent
ASM = ROOT / "projects" / "rung3_rotary" / "out" / "rung3_assembly.json"
if not ASM.exists():
    ASM = ROOT / "out" / "rung3_assembly.json"

# the rotating OUTPUT group (orbits the Z output axis); everything else is fixed for the sweep
ROT_PREFIX = ("p_adp", "p_72", "p_cap", "p_top", "fi", "fcap", "ft")


def rotating(ref: str) -> bool:
    return any(ref == p or ref.startswith(p) for p in ROT_PREFIX)


def _fastener(ref: str) -> bool:
    return ref.startswith(("fi", "fo", "fcap", "ft", "fa", "tn"))


def designed(a: str, b: str) -> bool:
    """True when these two are MEANT to touch (mesh overlap expected, not a fault)."""
    s = {a, b}
    if _fastener(a) or _fastener(b):
        return True                                  # a screw / T-nut sits inside its hole/slot
    designed_pairs = [
        {"p_base", "p_brg"}, {"p_brg", "p_adp"},      # bearing seated between base + adapter
        {"p_adp", "p_72"}, {"p_72", "p_cap"},         # pulley on pilot; cap on pulley
        {"p_cap", "p_top"},                            # tabletop on cap
        {"p_18", "p_belt"}, {"p_72", "p_belt"},        # belt wraps both pulleys
        {"p_18", "p_motor"}, {"p_motor", "p_mmount"},  # idler on the motor shaft; motor on its bridge
    ]
    if s in designed_pairs:
        return True
    if a.startswith("p_fr") and b.startswith("p_fr"):
        return True                                  # frame extrusions butt at the corners
    if ("p_base" in s or "p_mmount" in s) and (a.startswith("p_fr") or b.startswith("p_fr")):
        return True                                  # base / motor bridge bolt onto the frame
    return False


def run(asm: dict | None = None, *, verbose: bool = True):
    """Run the rung-3 interference gate. Returns assembly.interference.InterferenceReport."""
    if asm is None:
        asm = json.loads(ASM.read_text())
    meshes = IF.load_placed(asm, ROOT)
    return IF.interference_gate(meshes, designed=designed, rotating=rotating,
                                axis=tuple(asm.get("_axis", [0, 0, 1])), verbose=verbose)


if __name__ == "__main__":
    import sys
    print(f"placement source: {ASM.relative_to(ROOT)}")
    rep = run()
    sys.exit(0 if rep.passed else 1)
