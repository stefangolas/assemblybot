"""Generic assembly verification harness -- the ONE place every rung runs its gates.

A rung calls verify_assembly(...) with whatever it has; each gate runs if its inputs are
present and is reported uniformly (SKIP when a rung's data can't support it -- e.g. v1 parts
carry no v2 ports, so cad_fidelity skips). The three gates:

  load_path     every load-bearing part is fastened through real parts to ground
                (needs v2 attachment `instances` + `ground` + `lib`).
  cad_fidelity  every declared internal void physically exists in the part mesh
                (needs the v2 part defs `lib`).
  interference  no unintended volume overlap, STATIC or SWEPT through rotation
                (needs `urls` -> placed meshes; `designed`/`rotating` predicates optional).

This keeps the validation set identical across rungs instead of hand-wiring each one.
"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _part_no(p):
    return getattr(p, "part_number", None) or (p.get("part_number") if isinstance(p, dict) else None)


def verify_assembly(name, placements, urls=None, *, lib=None, instances=None, ground=None,
                    designed=None, rotating=None, axis=(0, 0, 1), root=ROOT, verbose=True,
                    non_structural=None, structural_refs=None):
    """Run every gate whose inputs are supplied; print a uniform report; return (passed, status).

      placements : {ref: {"R": 3x3, "t_mm": [x,y,z]}}  (all rendered parts)
      urls       : {ref: "/cad/<part>.glb"}            (for the interference meshes)
      lib        : {ref: PartDefinition}               (v2 defs -> cad_fidelity + load_path)
      instances  : [AttachmentInstance]  + ground : [ref,...]   -> load_path
      designed(a,b)->bool / rotating(ref)->bool        -> interference predicates (optional)
    """
    from ontology import load_path as LP
    from ontology import cad_sync as CS
    from assembly import interference as IF

    status = {}

    # --- load_path -----------------------------------------------------------
    if instances and ground and lib:
        # ACCOUNT FOR EVERY PLACED PART: any placed ref absent from the structural graph
        # (and not a declared coupling) is UNACCOUNTED and fails -- never silently skipped.
        placed = set(structural_refs) if structural_refs is not None else set(placements)
        rep = LP.evaluate(instances, lib, placements, ground=list(ground), mode="discovery",
                          placed=placed, non_structural=non_structural)
        unheld = [r for r, b in rep.bodies.items()
                  if r not in rep.ground and (b.state == LP.UNHELD or not b.accounted)]
        unacc = rep.unaccounted
        status["load_path"] = "PASS" if not unheld else "FAIL"
        if verbose and unacc:
            print(f"  load_path: UNACCOUNTED (placed, no structural instance) {unacc}")
        if verbose and [r for r in unheld if r not in unacc]:
            print(f"  load_path: UNHELD {[r for r in unheld if r not in unacc]}")
    else:
        status["load_path"] = "SKIP"
        if verbose:
            print("  load_path: !! SKIPPED -- missing "
                  + ", ".join(n for n, v in [("instances", instances), ("ground", ground),
                                             ("lib", lib)] if not v))

    # --- cad_fidelity --------------------------------------------------------
    if lib:
        uniq = list({_part_no(p): p for p in lib.values()}.values())
        ok, _ = CS.gate(uniq, verbose=verbose)
        status["cad_fidelity"] = "PASS" if ok else "FAIL"
    else:
        status["cad_fidelity"] = "SKIP"
        if verbose:
            print("  cad_fidelity: !! SKIPPED -- missing lib")

    # --- interference --------------------------------------------------------
    if urls:
        asm = {r: {"R": placements[r]["R"], "t_mm": placements[r]["t_mm"]}
               for r in urls if r in placements}
        asm["_render"] = [{"ref": r, "url": u} for r, u in urls.items() if r in placements]
        meshes = IF.load_placed(asm, root)
        rep = IF.interference_gate(meshes, designed=designed, rotating=rotating,
                                   axis=tuple(axis), verbose=verbose)
        status["interference"] = "PASS" if rep.passed else "FAIL"
    else:
        status["interference"] = "SKIP"
        if verbose:
            print("  interference: !! SKIPPED -- missing urls (no meshes to check)")

    passed = all(v != "FAIL" for v in status.values())
    if verbose:
        print(f"  VERIFY {name}: " + "  ".join(f"{k}={v}" for k, v in status.items())
              + f"   => {'PASS' if passed else 'FAIL'}")
    return passed, status
