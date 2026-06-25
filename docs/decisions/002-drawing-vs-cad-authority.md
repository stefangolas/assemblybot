# 002 — Drawing establishes semantics; CAD establishes geometry

**Decision:** A manufacturer drawing or exact configurator establishes feature SEMANTICS (hole type, thread
designation, datums, function). CAD establishes modeled GEOMETRY (coordinates, axes, extents, shape). CAD
geometry alone does NOT prove a thread, tolerance, material, or intended function. **Always fetch and read the
drawing before authoring/claiming ontology geometry.**

**Why:** CAD omits counterbores and thread helices and can't distinguish a tapped hole from a clearance hole —
the diameter alone misleads. We mis-annotated the SL-TBLG jaw holes from CAD Ø before the drawing confirmed
M-tapped vs counterbored; the FALBS "N3" axle was an M3 clearance hole, not the tap the CAD Ø suggested. The
drawing is the single most important source of truth.

**Consequences:** Tie each authored port's deciding numbers to drawing evidence (`extraction_method=drawing`).
Mark a field `nominal`/`inferred` only when NO drawing exists, and say so explicitly. Never substitute a
question to the user for pulling the drawing. Every part's ontology is audited against the drawing periodically.
Mirrors memories [[drawings-are-truth]], [[misumi-hole-type-codes]].
