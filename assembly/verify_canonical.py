"""Self-contained, bypass-proof verification of a canonical assembly artifact.

THE RULE (global, programmatic): every assembly that is written to disk carries a
`_verify` payload, and every assembly is checked by running EXACTLY the same full gate
set over that payload -- load_path (with placed-part accounting), cad_fidelity, and
interference (static + swept). A benchmark cannot "forget" a gate or hand-pick a subset:
the gates are driven off the artifact, not off whatever the benchmark felt like calling.
`tools/verify_all.py` runs this over every project; CI fails if any gate fails OR if any
assembly lacks a `_verify` payload (an unverifiable artifact is itself a failure).

`embed_verification(asm, ...)` writes the payload (called once by each builder, via the
shared writer below). `verify_canonical(path)` rebuilds the library + attachment
instances from it and runs `verify_assembly`, deriving the interference predicates:
  designed(a,b)  -> the two parts share an attachment (intentional contact) / are split
                    halves of one bearing / are the same part.
  rotating(ref)  -> the part is in some DOF's moving set (`_dofs`), so swept-interference
                    sweeps it about that joint axis.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBV2 = ROOT / "library_v2"


def embed_verification(asm: dict, *, lib: dict, instances: list, ground, placements: dict,
                       non_structural=None, part_numbers: dict = None) -> dict:
    """Attach the everything-needed-to-verify payload to the assembly dict (in place).

    `part_numbers`: {ref -> library_v2 stem} so the def can be reloaded. Defaults to each
    PartDefinition's part_number (true when the file is named <part_number>.json)."""
    pn = dict(part_numbers or {})
    for ref, pdef in lib.items():
        pn.setdefault(ref, getattr(pdef, "part_number", None))
    asm["_verify"] = {
        "lib": {ref: pn[ref] for ref in lib},
        "instances": [{"template": i.template.id, "bindings": i.bindings} for i in instances],
        "ground": list(ground),
        "non_structural": sorted(non_structural or []),
        "placements": {ref: {"R": placements[ref]["R"],
                             "t_mm": [float(v) for v in placements[ref]["t_mm"]]}
                       for ref in lib if ref in placements},
    }
    return asm


def _load_def(stem: str):
    from ontology.schema_v2 import PartDefinition
    return PartDefinition.from_json(json.loads((LIBV2 / f"{stem}.json").read_text()))


def _bearing_base(ref: str) -> str:
    for suf in ("_inner", "_outer"):
        if ref.endswith(suf):
            return ref[:-len(suf)]
    return ref


def _slot(addr: str) -> str:
    return addr.split(".", 1)[0]


def verify_canonical(path, *, verbose=True):
    """Run the FULL gate set on a canonical assembly file. Returns (passed, status).

    A missing `_verify` payload is a hard failure -- an assembly that did not record how
    to check it is unverifiable, which is not allowed."""
    from ontology.templates import TEMPLATES
    from assembly.verify import verify_assembly

    path = Path(path)
    asm = json.loads(path.read_text())
    name = path.stem
    if "_verify" not in asm:
        if verbose:
            print(f"VERIFY {name}: !! NO _verify PAYLOAD -- unverifiable artifact => FAIL")
        return False, {"_artifact": "FAIL"}

    v = asm["_verify"]
    lib = {ref: _load_def(stem) for ref, stem in v["lib"].items()}
    instances = [TEMPLATES[i["template"]].bind(i["bindings"]) for i in v["instances"]]
    struct_place = v["placements"]
    ground = v["ground"]
    non_structural = set(v.get("non_structural", []))

    # render meshes (for interference) -- every render part + its pose from the artifact
    urls = {r["ref"]: r["url"] for r in asm.get("_render", [])}
    render_place = {ref: {"R": asm[ref]["R"], "t_mm": asm[ref]["t_mm"]}
                    for ref in urls if ref in asm and isinstance(asm[ref], dict)}
    placements = {**render_place, **struct_place}   # struct poses authoritative for shared refs

    # Hard accounting rule: a physical render entry is part of the assembly contract.
    # It must be promoted into the structural verification library, or be explicitly
    # declared non-structural (for example a generated flexible belt). "Context" meshes
    # are not allowed to bypass load-path accounting.
    render_refs = set(urls)
    exempt_refs = set(non_structural)
    unverified_render_refs = sorted(render_refs - set(lib) - exempt_refs)
    non_rendered_structural = set(v.get("non_rendered_structural", []))
    hidden_structural_refs = sorted(set(lib) - render_refs - non_rendered_structural)

    # designed(a,b): intentional shared volume = parts bolted into the SAME RIGID BODY
    # (a screw seated in its tapped hole, a seated face, a pulley on its hub all overlap
    # by design), or directly joined by a pose-enforcing relation, or two render-halves
    # of one bearing, or the same part. Crossed-roller bearings are split into inner/outer
    # rigid nodes here; otherwise fixed ring mounts can accidentally hide collisions
    # across the joint.
    JT = {"revolute", "slider"}
    bearing_refs = set()
    for inst in instances:
        if inst.template.result.type in JT and len(inst.part_refs()) == 1:
            bearing_refs.add(next(iter(inst.part_refs())))

    def node_from_addr(addr):
        ref, _, portid = addr.replace(":", ".", 1).partition(".")
        if ref in bearing_refs:
            if "inner" in portid:
                return f"{ref}#inner"
            if "outer" in portid:
                return f"{ref}#outer"
        return ref

    def node_from_ref(ref):
        for suf in ("_inner", "_outer"):
            if ref.endswith(suf):
                base = ref[:-len(suf)]
                if base in bearing_refs:
                    return f"{base}#{suf[1:]}"
        return ref

    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        parent[find(a)] = find(b)
    attached = set()
    for inst in instances:
        for rel in inst.template.enforce:
            a = inst.bindings.get(_slot(rel.a))
            b = inst.bindings.get(_slot(rel.b))
            if a and b:
                na, nb = node_from_addr(a), node_from_addr(b)
                attached.add((min(na, nb), max(na, nb)))
        if inst.template.result.type not in JT:
            for edge in inst.template.load_paths:
                if edge.frm in inst.bindings and edge.to in inst.bindings:
                    union(node_from_addr(inst.bindings[edge.frm]),
                          node_from_addr(inst.bindings[edge.to]))

    def designed(a, b):
        if a == b or _bearing_base(a) == _bearing_base(b):
            return True
        na, nb = node_from_ref(a), node_from_ref(b)
        def is_belt(ref):
            return "belt" in ref.lower()
        def is_timing_pulley(ref):
            p = lib.get(ref)
            fam = (p.classification.get("catalog_family", "") if p else "").lower()
            return "timing_pulley" in fam or "pul" in ref.lower() or ref in {"p_18", "p_72"}
        if (is_belt(a) and is_timing_pulley(b)) or (is_belt(b) and is_timing_pulley(a)):
            return True
        if (min(na, nb), max(na, nb)) in attached:
            return True
        return find(na) == find(nb)

    # rotating(ref): part participates in some DOF's moving set
    moving = set()
    for d in asm.get("_dofs", []):
        moving.update(d.get("moving", []))
    rotating = (lambda ref: ref in moving) if moving else None
    axis = asm.get("_axis", (0, 0, 1))

    fastener_primitive_issues: list[str] = []
    for inst in instances:
        for closure in inst.template.closure:
            if closure.kind != "fastener":
                continue
            slot = closure.mechanism
            if slot not in inst.template.participants:
                continue
            has_primitive_check = any(chk.a == slot or chk.b == slot for chk in inst.template.checks)
            if not has_primitive_check:
                fastener_primitive_issues.append(
                    f"{inst.template.id}.{slot}: fastener closure has no primitive check involving the fastener"
                )

    if verbose:
        print(f"VERIFY {name}  ({len(lib)} structural parts, {len(instances)} attachments, "
              f"{len(urls)} meshes)")
        if unverified_render_refs:
            print(f"  render_accounting: UNVERIFIED physical render refs {unverified_render_refs}")
        if hidden_structural_refs:
            print(f"  structural_visibility: HIDDEN structural refs {hidden_structural_refs}")
        if fastener_primitive_issues:
            print(f"  fastener_primitives: UNDER-SPECIFIED fastener closures {fastener_primitive_issues}")

    passed, status = verify_assembly(name, placements, urls, lib=lib, instances=instances, ground=ground,
                                     designed=designed, rotating=rotating, axis=axis,
                                     non_structural=non_structural, structural_refs=None,
                                     verbose=verbose)
    status["render_accounting"] = "FAIL" if unverified_render_refs else "PASS"
    status["structural_visibility"] = "FAIL" if hidden_structural_refs else "PASS"
    status["fastener_primitives"] = "FAIL" if fastener_primitive_issues else "PASS"
    return (
        passed
        and not unverified_render_refs
        and not hidden_structural_refs
        and not fastener_primitive_issues
    ), status
