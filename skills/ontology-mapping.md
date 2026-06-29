# Skill: Ontology & 3D Mapping (LEAD ONLY)

Mapping manufacturer evidence + CAD into canonical `PartDefinition` ports is **lead-only**. A worker's
candidate report may accelerate this but never replaces lead review. Every part's ontology is **audited
periodically against source evidence** — author it as if it will be re-checked against the drawing, because it
will. Mark anything unverifiable `unknown`/`nominal` explicitly; never assert it.

## The four sources — keep them distinct

```
Manufacturer drawing / exact configurator : what a feature MEANS (hole type, thread, function)
CAD                                        : WHERE it is + what shape/extent it has (geometry, axes, frame)
Engineering standard                       : standard-derived dimensions / compatibility
Lead interpretation                        : the ontology mapping + assembly use
```

CAD geometry alone never proves a thread, tolerance, material, or function. The **drawing is the single most
important source of truth** — fetch it for every part and confirm every claim against it.

## Lead mapping procedure (after accepting a candidate)

1. Verify the exact PN + configuration. 2. Review the raw manufacturer evidence (drawing first). 3. Review the
actual CAD artifact (`trimesh.load(force='scene')` — a STEP "part" is often an assembly of bodies; merging
hides sub-parts). 4. Establish the immutable local part frame (mm, one frame, no assembly placement).
5. Identify the relevant CAD features. 6. Map manufacturer semantics onto those features. 7. Create ports +
port groups. 8. Assign field-level provenance/evidence. 9. Run per-part checks. 10. Render + inspect the
mapped part (`skills/render-and-inspect.md`). 11. Only then bind it into the assembly.

## The six universal engagement-port families (numerical forms, not part classes)

`cylindrical` (shafts/bores/journals/races/rails), `planar` (seats/faces/flanges/jaws), `swept_profile`
(T-slots/dovetails/keyways/guide profiles), `threaded` (machine threads — generate from the callout, reconcile
axis/span to CAD), `periodic` (timing/gear teeth, splines — pitch + active region, no per-tooth geometry),
`flexible_path` (belts/cables — material + cross-section; the routed loop lives on the part *instance*, not the
definition). Each port is a **bounded** affordance with required numerical geometry + polarity. Named concepts
(bearing seat, T-slot nut, counterbore, keyed bore) are **recipes** that compile to ports/groups, NOT new
classes. Bolt patterns / paired faces / repeated holes are `PortGroup`s (exact composition, symmetry-aware
correspondence — never zip hole lists).

## Code is the executable schema (source of truth)

T-slot extrusion rule: do not create fake evenly spaced nut stations. Each usable slot is a `swept_profile`
receiver plus a `continuous_domain` port group along the extrusion axis. Bound the placement interval so the
nut or bracket center coordinate remains at least half of the inserted footprint from each rail end, or the
manufacturer-specified end clearance if larger. Discrete attachment ports are only valid when the drawing shows
actual discrete holes.

- `ontology/ports.py` — the 6 `EngagementPort` families + `PortGroup`, strict per-family validation.
- `ontology/schema_v2.py` — immutable `PartDefinition` (rejects a baked frame/placement), `PartInstance`
  (the only place a pose lives), field-level `EvidenceRecord`.
- `ontology/ports_match.py` — the predicates (radial_fit, axial_overlap, thread_match, clearance_pass_through,
  pitch_profile_match, active_width_overlap, bounded_area_overlap, profile_containment, pattern_correspondence)
  → PASS/FAIL/UNKNOWN + severity + measurements.
- Author a part: `library_v2/<pn>.json` (schema_version 2, mm in one local frame, CAD metres, NO placement).
- Per the manual's full normative v2 spec (value types, evidence schema, family geometry model, drawing→CAD
  similarity transform with reported residuals): see `archive/rung2/CLAUDE_v1_full.md` "THE ATTACHMENT
  ONTOLOGY v2 (NORMATIVE)" + "EVIDENCE AND AI ANNOTATION SCHEMA".

## Drawing→CAD reconciliation

Predict ports in the drawing frame, then fit ONE similarity transform `x_CAD = scale·R·x_drawing + t` from
several features; report position RMS + max axis-angle + per-port residuals. If one transform can't reconcile,
STOP and diagnose (wrong configured part, misread dim, wrong datum, unit error, CAD simplification, bad family
model). Never repair the assembly by editing part-local coordinates. Expected CAD simplifications (omitted
thread helices/counterbores) are explicit reconciliation policies, not silent exceptions.
