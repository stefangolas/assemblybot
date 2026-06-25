"""Placement solver (one source of truth for pose).

Emits a single solved transform per part from the assembly's mates + the per-part
frame-reconciliation facts recorded during annotation (Section 3: the mesh origin
and the annotation datum differ, so each part frame stores how to map its mesh
into the part frame). BOTH the interference gate and the Three.js viewer consume
this output, so what we validate is exactly what we render -- the two can no
longer silently disagree (the bug that put the Rung-1 bracket 3 mm into the rail).

Transforms are returned as {ref: {"R": 3x3 list, "t_mm": [x,y,z]}} in millimetres.
The grounded part is identity. We deliberately keep this rung-aware and explicit
rather than building a general numerical constraint solver before a rung needs it.
"""
from __future__ import annotations

import numpy as np
import trimesh


def _mesh_bounds_mm(gltf_uri: str):
    m = trimesh.load(gltf_uri)
    if isinstance(m, trimesh.Scene):
        m = m.to_geometry()
    return m.bounds * 1000.0  # cascadio writes metres


# axis name -> column index, for building the rotation that carries a part's
# local axis onto a world axis.
_AX = {"x": 0, "y": 1, "z": 2}


def _basis_rotation(local_to_world: dict) -> np.ndarray:
    """local_to_world: {'z':'x','y':'z','x':'y'} means local Z -> world X, etc.
    Returns R such that world = R @ local."""
    R = np.zeros((3, 3))
    for la, wa in local_to_world.items():
        R[_AX[wa], _AX[la]] = 1.0
    return R


def solve_placements(assembly, library: dict) -> dict:
    placements: dict = {}
    grounded = next(p.ref for p in assembly.parts if p.grounded)
    placements[grounded] = {"R": np.eye(3), "t_mm": np.zeros(3)}

    interfaces = {m.interface for m in assembly.mates}

    if "seated_revolute" in interfaces:
        # Rung 0: washer seated under the screw head. Screw grounded; place the
        # washer so its mating face (mesh max-Z) lands on the under-head face,
        # which the screw frame records at mesh_seat_z.
        screw = library[grounded]
        seat_z = screw.frame.get("mesh_seat_z", 0.0)
        washer_ref = next(p.ref for p in assembly.parts if not p.grounded)
        wmax_z = _mesh_bounds_mm(library[washer_ref].cad["gltf_uri"])[1][2]
        placements[washer_ref] = {"R": np.eye(3), "t_mm": np.array([0, 0, seat_z - wmax_z])}

    if "bolt_joint" in interfaces:
        # Rung 1: flat bracket on the rail's +X face. The rail frame records the
        # mount face at mesh X = mount_face_mesh_x; the bracket frame records its
        # mounting face at mesh Z = mount_face_mesh_z, its plate normal as local
        # Z and its length as local Y. Carry plate normal -> +X (bolt axis) and
        # length -> +Z (rail axis), then offset so the faces coincide.
        rail = library[grounded]
        face_x = rail.frame["mount_face_mesh_x"]
        bracket_ref = next(p.ref for p in assembly.parts if not p.grounded)
        bracket = library[bracket_ref]
        R = _basis_rotation({"z": "x", "x": "y", "y": "z"})  # world=(local_z,local_x,local_y)
        tx = face_x - bracket.frame["mount_face_mesh_z"]
        placements[bracket_ref] = {"R": R, "t_mm": np.array([tx, 0, 0])}

    return placements


def placements_to_json(placements: dict) -> dict:
    return {ref: {"R": np.asarray(v["R"]).tolist(),
                  "t_mm": np.asarray(v["t_mm"]).tolist()}
            for ref, v in placements.items()}


def matrix4_mm(p: dict) -> np.ndarray:
    """{'R','t_mm'} -> 4x4 homogeneous (mm)."""
    M = np.eye(4)
    M[:3, :3] = np.asarray(p["R"])
    M[:3, 3] = np.asarray(p["t_mm"])
    return M
