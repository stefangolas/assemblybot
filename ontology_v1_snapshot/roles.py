"""Semantic roles (Section 4b).

Geometry is ambiguous; the role disambiguates it and carries the params that
drive compatibility. This is the catalog-specific layer (Section 5): the same
three geometric primitives are reused everywhere, while the part-specific
knowledge lives in (role + params), which is cheap and swappable.

PARSIMONY (Section 1, Section 10): grow this set ONLY when a concrete part
cannot be annotated with the existing roles, and only via a ratified failure
log. Proposing a tenth role in a week is a smell -- look for a composition you
are missing. `pitch_circle` is intentionally withheld until `Path` lands.
"""
from __future__ import annotations

# Roles ratified so far. Keep flat; do not pre-populate speculatively.
ROLES: set[str] = {
    "clearance_hole",
    "threaded_hole",
    "shaft_bore",
    "bearing_seat",
    "mounting_face",
    "slot",
    "shoulder",
    "pitch_circle",  # RATIFIED at Rung 2 once Path landed (out/ontology_log/rung2.md)
}


def assert_role(role: str) -> None:
    if role not in ROLES:
        raise ValueError(
            f"role {role!r} is not in the ratified ontology. Do not invent it "
            f"inline -- emit a failure record and ratify it (Section 10). "
            f"Current roles: {sorted(ROLES)}"
        )
