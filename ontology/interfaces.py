"""Functional interfaces (Section 4e).

Named bundles that expand to constraints we already have -- conveniences, not
ontology. We reason and report at this level; the solver works at the
constraint level.

PARSIMONY: only interfaces actually exercised by a built rung live here.
`bolt_joint` arrives with Rung 1, `bearing_mount`/`pulley_mount` with Rung 2.
Do not pre-build them.
"""
from __future__ import annotations

from .constraints import Constraint, Joint
from .schema import Mate


def seated_revolute(
    *,
    shaft_axis: str,
    bore_axis: str,
    seat_face: str,
    part_face: str,
) -> Mate:
    """A part seated coaxially on a shaft and resting against a face, free to
    spin about the axis (Rung 0: a washer under a screw head).

    = coaxial(shaft, bore) + coplanar(seat_face, part_face) + revolute(axis).
    The axial face contact removes translation along the axis; what remains is
    one rotational DOF -- a revolute joint.
    """
    return Mate(
        interface="seated_revolute",
        constraints=[
            Constraint(type="coaxial", a=shaft_axis, b=bore_axis),
            Constraint(type="coplanar", a=seat_face, b=part_face),
        ],
        joint=Joint(type="revolute", axis=shaft_axis),
        requires=[],
    )


def bolt_joint(
    *,
    clearance_hole: str,
    threaded_hole: str,
    face_a: str,
    face_b: str,
    requires: list[str],
) -> Mate:
    """A screw through a clearance hole into a threaded hole, faces seated, rigid
    (Section 4e). Ratified at Rung 1 (see out/ontology_log/rung1.md).

    = coaxial(clearance_hole, threaded_hole) + coplanar(faces) + fixed.
    `requires` names the BOM part refs that realize it (a screw, a T-nut).
    """
    return Mate(
        interface="bolt_joint",
        constraints=[
            Constraint(type="coaxial", a=clearance_hole, b=threaded_hole),
            Constraint(type="coplanar", a=face_a, b=face_b),
        ],
        joint=Joint(type="fixed"),
        requires=requires,
    )


def bearing_mount(*, shaft_axis: str, bore_axis: str, requires: list[str] | None = None) -> Mate:
    """Shaft running in a bearing -> revolute about the shaft axis (§4e).
    Ratified at Rung 2. = coaxial(shaft, bearing bore) + revolute."""
    return Mate(
        interface="bearing_mount",
        constraints=[Constraint(type="coaxial", a=shaft_axis, b=bore_axis)],
        joint=Joint(type="revolute", axis=shaft_axis),
        requires=requires or [],
    )


def pulley_mount(*, pulley_bore: str, shaft_axis: str, requires: list[str] | None = None) -> Mate:
    """Pulley fixed coaxially on a shaft (§4e). = coaxial(bore, shaft) + fixed
    (a set screw/key keeps it from spinning on the shaft)."""
    return Mate(
        interface="pulley_mount",
        constraints=[Constraint(type="coaxial", a=pulley_bore, b=shaft_axis)],
        joint=Joint(type="fixed"),
        requires=requires or [],
    )


def belt_drive(*, pitch_circle_a: str, pitch_circle_b: str, belt_path: str,
               clamp_anchor: tuple[str, str], clamp_face: str, belt_face: str,
               requires: list[str]) -> Mate:
    """Two pulleys engaged by a belt clamped to a carriage (Rung 2 bootstrap,
    out/ontology_log/rung2.md + rung2_clampfix.md). The `path`/`pitch_circle`
    extension handles the belt loop; the clamp tie is ordinary coaxial/coplanar.

    Imposes TWO kinematic couplings beyond the existing joints:
      1. pulley_a rotation <-> pulley_b rotation (same belt linear speed);
      2. belt linear travel <-> carriage translation (the clamp).
    So mobility subtracts 2.

    The CLAMP-TO-BELT tie is a FACE MATE, not a point. The original interface tied
    them with a single `coincident` anchor (`carriage_clamp`), which pins position
    but NOT orientation -- it let the toothed clamp sit 90 deg to the belt teeth and
    no constraint objected. The fix adds `coplanar(clamp_face, belt_face)`: the
    clamp's toothed face must lie in the same plane as the belt run's toothed face
    (opposed normals = teeth meshing). No new primitive -- `coplanar` already
    existed; the bug was not using it. `clamp_anchor` = (belt_path, clamp_grip)
    keeps the graph connected along the run.
    """
    return Mate(
        interface="belt_drive",
        constraints=[
            Constraint(type="coincident", a=belt_path, b=pitch_circle_a),
            Constraint(type="coincident", a=belt_path, b=pitch_circle_b),
            Constraint(type="coincident", a=clamp_anchor[0], b=clamp_anchor[1]),
            # the fix: toothed faces face-to-face, so the clamp can't be 90 deg off
            Constraint(type="coplanar", a=clamp_face, b=belt_face),
        ],
        joint=Joint(type="fixed", coupling={"belt": [pitch_circle_a, pitch_circle_b],
                                            "carriage": clamp_anchor[1]}),
        requires=requires,
        couplings=2,
    )


def bolt_pattern(
    *,
    holes: list[str],
    threaded_holes: list[str],
    face_a: str,
    face_b: str,
    requires: list[str],
) -> list[Mate]:
    """Pattern-to-pattern mating (Rung 1): expand a hole pattern + matching
    threaded-hole pattern into one `bolt_joint` per pair. A `pattern` is just a
    named list of like features -- NOT a new ontology primitive (rung1 log #2).
    Multiple bolt_joints between the same body pair are intentional
    over-constraint; the mobility gate recognizes the redundancy as benign.
    """
    if len(holes) != len(threaded_holes):
        raise ValueError("hole pattern and threaded-hole pattern must be equal length")
    return [
        bolt_joint(clearance_hole=h, threaded_hole=t,
                   face_a=face_a, face_b=face_b, requires=requires)
        for h, t in zip(holes, threaded_holes)
    ]
