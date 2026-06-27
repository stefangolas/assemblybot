"""Recognize the kinematic DOFs of an assembly from its attachment instances.

A joint (revolute/slider) in this ontology is the INTERNAL freedom of a bearing/guide
catalog part: `crossed_roller_revolute` binds inner==outer to one bearing ref. So the
bearing is ONE part but TWO kinematic bodies sharing an axis. To find what actually
moves when that joint turns, we:

  1. split every joint-bearing ref into two virtual nodes  ref#inner / ref#outer;
  2. build the RIGID graph from all non-joint instances' load_paths (a fastener/seat
     rigidly ties its two parts), routing a bearing endpoint to #inner or #outer by
     which ring port it binds (the `forbidden` slots are NOT load_paths, so they don't
     leak across the joint);
  3. for each joint, cut ONLY that joint's inner<->outer edge (keep the others), and
     take the component NOT containing ground as that joint's MOVING set. Keeping the
     distal joints' edges makes the moving sets nest correctly for a serial chain.

`extra_fixed` patches parts that are placed but never structurally instanced (e.g. a
drive pulley rigidly fixed to a hub): {ref: other_ref_or_addr}. Belts and other pure
couplings have empty load_paths, so they contribute no rigid edge and stay static.

Output (-> assembly JSON `_dofs`), consumed by the viewer slider:
  [{id, type, axis:[x,y,z], center:[x,y,z]_mm, moving:[render_refs], range:[lo,hi]}]
Bearing refs in `moving` use the split convention `<ref>_inner` / `<ref>_outer`, matching
the split glbs from tools/split_bearing.py.
"""
from __future__ import annotations

_JOINT_TYPES = {"revolute", "slider"}


def _mat_vec(R, v):
    return [sum(R[i][k] * v[k] for k in range(3)) for i in range(3)]


def _norm(v):
    m = sum(c * c for c in v) ** 0.5 or 1.0
    return [c / m for c in v]


def _node(addr, bearing_refs):
    """Resolve a binding address to a graph node, splitting bearing endpoints by ring."""
    ref, _, portid = addr.replace(":", ".", 1).partition(".")
    if ref in bearing_refs:
        if "inner" in portid:
            return f"{ref}#inner"
        if "outer" in portid:
            return f"{ref}#outer"
    return ref


def _render_ref(node):
    if node.endswith("#inner"):
        return node[:-6] + "_inner"
    if node.endswith("#outer"):
        return node[:-6] + "_outer"
    return node


def extract_dofs(instances, lib, placements, ground, *, extra_fixed=None,
                 slider_range=(-50.0, 50.0)) -> list:
    ground = set(ground)
    extra_fixed = extra_fixed or {}

    # 1. joints + the bearing each one lives in
    bearing_refs, joints = set(), []
    for inst in instances:
        if inst.template.result.type not in _JOINT_TYPES:
            continue
        refs = inst.part_refs()
        if len(refs) != 1:
            continue                       # only the internal one-bearing joint form
        ref = next(iter(refs))
        bearing_refs.add(ref)
        joints.append((inst, ref, inst.template.result.type))

    # 2. rigid edges (everything that is NOT a joint), via load_paths only
    rigid = []
    for inst in instances:
        if inst.template.result.type in _JOINT_TYPES:
            continue
        for e in inst.template.load_paths:
            if e.frm in inst.bindings and e.to in inst.bindings:
                rigid.append((_node(inst.bindings[e.frm], bearing_refs),
                              _node(inst.bindings[e.to], bearing_refs)))
    for ref, to in extra_fixed.items():
        rigid.append((ref, _node(to, bearing_refs)))

    joint_edges = [(f"{ref}#inner", f"{ref}#outer") for _, ref, _ in joints]

    nodes = set(ground)
    for a, b in rigid + joint_edges:
        nodes.add(a); nodes.add(b)

    def reachable(edges, seeds):
        adj = {}
        for a, b in edges:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
        seen, stack = set(seeds), list(seeds)
        while stack:
            n = stack.pop()
            for m in adj.get(n, []):
                if m not in seen:
                    seen.add(m); stack.append(m)
        return seen

    out = []
    for i, (inst, bref, jtype) in enumerate(joints):
        # cut ONLY this joint; keep rigid + the other joints
        edges = rigid + [e for k, e in enumerate(joint_edges) if k != i]
        stationary = reachable(edges, ground)
        moving_nodes = [n for n in nodes if n not in stationary]
        moving = sorted({_render_ref(n) for n in moving_nodes})

        # axis + center from the bearing's bound axis port, in world (mm)
        slot = inst.template.result.axis_slot
        addr = inst.bindings.get(slot) or next(iter(inst.bindings.values()))
        _, _, portid = addr.replace(":", ".", 1).partition(".")
        g = lib[bref].port(portid).geometry["axis"]
        R, t = placements[bref]["R"], placements[bref]["t_mm"]
        axis = _norm(_mat_vec(R, g["direction"]))
        center = [_mat_vec(R, g["origin"])[k] + t[k] for k in range(3)]
        rng = list(slider_range) if jtype == "slider" else [-180.0, 180.0]

        out.append({"id": f"J{i + 1}", "bearing": bref, "type": jtype,
                    "axis": [round(c, 6) for c in axis],
                    "center": [round(c, 4) for c in center],
                    "moving": moving, "range": rng})

    # name proximal (largest moving set) first: J1, J2, ...
    out.sort(key=lambda d: -len(d["moving"]))
    for i, d in enumerate(out):
        d["id"] = f"J{i + 1}"
    return out
