"""Mobility analysis (Section 9, primary "is this a machine" gate).

Kutzbach/Grueber spatial mobility, but computed on the graph *after* rigid
bodies are merged -- this is what lets intentional over-constraint (Rung 1's
4 bolts on a face) resolve to the right DOF instead of a spurious negative.

Procedure:
  1. Union-find over `fixed` joints -> rigid groups (a set of bodies bolted
     solidly together is one rigid body).
  2. Reduced links = number of rigid groups. Reduced joints = the non-fixed
     joints whose endpoints fall in *different* groups (a non-fixed joint inside
     one rigid group is itself locked out and counted as redundant).
  3. M = 6*(L - 1 - j) + sum(f_i) - couplings   over the reduced graph.

Redundancy is reported, not punished: to tie n_bodies into n_groups you need
exactly (n_bodies - n_groups) fixed joints; any extra fixed joints are benign
intentional redundancy (e.g. the 4th, 3rd, 2nd bolt on a face).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MobilityResult:
    n_bodies: int
    n_rigid_groups: int
    n_joints_total: int
    n_joints_reduced: int
    sum_f: int
    n_couplings: int
    redundant_fixed: int
    redundant_locked: int
    computed_dof: int
    note: str = ""

    def to_json(self) -> dict:
        return {
            "n_bodies": self.n_bodies,
            "n_rigid_groups": self.n_rigid_groups,
            "n_joints_total": self.n_joints_total,
            "n_joints_reduced": self.n_joints_reduced,
            "sum_f": self.sum_f,
            "n_couplings": self.n_couplings,
            "redundant_fixed": self.redundant_fixed,
            "redundant_locked": self.redundant_locked,
            "computed_dof": self.computed_dof,
            "note": self.note,
        }


def mobility(bodies: list[str], jointspecs: list[tuple], couplings: int = 0) -> MobilityResult:
    """bodies: list of part refs. jointspecs: list of (a_body, b_body, Joint)."""
    parent = {b: b for b in bodies}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    # 1. merge rigid groups over fixed joints
    n_fixed = 0
    for a, b, jt in jointspecs:
        if jt.type == "fixed":
            n_fixed += 1
            union(a, b)
    groups = {find(b) for b in bodies}
    n_groups = len(groups)

    # 2. reduced (mobile) joints: non-fixed joints across distinct groups
    reduced = []
    redundant_locked = 0
    for a, b, jt in jointspecs:
        if jt.type == "fixed":
            continue
        if find(a) == find(b):
            redundant_locked += 1   # a revolute/slider inside a welded group is dead
        else:
            reduced.append(jt)

    j = len(reduced)
    sum_f = sum(jt.dof for jt in reduced)
    m = 6 * (n_groups - 1 - j) + sum_f - couplings

    fixed_needed = len(bodies) - n_groups
    redundant_fixed = n_fixed - fixed_needed

    return MobilityResult(
        n_bodies=len(bodies),
        n_rigid_groups=n_groups,
        n_joints_total=len(jointspecs),
        n_joints_reduced=j,
        sum_f=sum_f,
        n_couplings=couplings,
        redundant_fixed=redundant_fixed,
        redundant_locked=redundant_locked,
        computed_dof=m,
    )
