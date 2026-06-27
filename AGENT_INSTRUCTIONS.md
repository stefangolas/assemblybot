# Assembly Agent

Compose working machines from **real catalog parts** (McMaster-Carr for generic hardware, Misumi for
factory-automation/motion parts) via a small geometry/attachment ontology. The verification that matters is
**looking at the rendered assembly**. Keep this file tight and honest.

---

# THE PIPELINE (this is the whole job)

A short loop. Go around it as many times as needed; most iterations change a *part choice*, not the ontology.

1. **Design** — decide what the machine does and its target DOF. Sketch the parts as functional classes
   (e.g. "rail", "pulley", "bearing that bolts to the frame"), and how each attaches to the next.
2. **Find the parts in the catalogs** — for every class, find a REAL catalog part and download its CAD
   (McMaster for generic hardware, Misumi for FA/motion parts). No part exists / nothing fits in one
   catalog? Check the other, then change the design or the part. (See Reference: driving the sites.)
3. **Model each part** — use the catalog category as an annotation prior; extract raw claims from the
   product page, configurator, 2-D drawing, and datasheet; normalize them into bounded numerical engagement
   ports in ONE immutable part frame; then reconcile those predicted ports to the CAD with one drawing→CAD
   frame transform. The drawing/spec defines engineering intent; CAD confirms correspondence and coordinates.
4. **Attach** — compose parts with constraints/mates; place them; (optionally) compute DOF.
5. **LOOK** — render the placed assembly and inspect it from many angles. This is the real check, and it's
   where the real work is. It validates more than placement: seeing a part in context is how you discover
   you picked the *wrong part* (too big, wrong mount, doesn't reach) — something no spec field tells you. If
   it looks wrong, it is wrong — go back to step 2 (different part), 3 (re-model), or 4 (re-place).

---

# HARD RULES (this is where it went wrong before)

### 1. Numerical checks are necessary but scoped; vision detects an incomplete model.
A passed numerical predicate proves only the condition it encodes. It can prove that two measured patterns
coincide, that a shaft fits a bore nominally, or that a belt and pulley share a pitch. It cannot prove that
all necessary parts, load paths, access conditions, or engineering requirements were modeled. Earlier
bbox/FCL/coincidence gates passed assemblies that were visibly broken because the model omitted the deciding
condition. Therefore:
- **Run the numerical checks** and report exactly what they establish: geometry, nominal fit, closure, or DOF.
- **Render and look after every part you add** — never wait until the end. Highlight the new part.
- Inspect from multiple angles (iso + axis views). Ask: is each part real, does each bounded engagement region
  actually overlap its counterpart, is every part held, and is anything floating, interpenetrating, or wrong-scale?
- **★ MOVING ASSEMBLIES: a static render has a BLIND SPOT for swept/rotational interference.** A single
  assembled-pose frame shows NO collision when the colliding bodies are at different angles in that pose — yet
  they collide as the mechanism moves (rung-3: rotating standoffs at R78 swept THROUGH a fixed belt run; the
  static iso/top render looked clean). So "I looked at it" is necessary but NOT sufficient for anything that
  moves. You MUST additionally either (a) run a SWEPT-VOLUME numerical check (does any moving part's swept
  annulus/region intersect a fixed part across the full travel?), or (b) render the DELIBERATELY-CONSTRUCTED
  colliding pose / multiple poses across the travel. The math finds it; the rotated render makes it undeniable.
  This is the one place a numerical check BEATS a static look — use both.
- A green result is `valid_under_encoded_model`, never universal proof. Unknown or unmodeled engineering facts
  remain explicit review items.
- Say **"I looked at it"** only after inspection; say which numerical predicates were checked separately.

### 1b. The ATTACHMENT ONTOLOGY is the whole game — verify every attachment IN ISOLATION, ANNOTATED, as you assign it.
**★ EVERY PART'S ATTACHMENT ONTOLOGY WILL BE AUDITED PERIODICALLY — do not get it wrong.** Each part's ports,
hole types, thread callouts, spans, and patterns are reviewed against the source evidence (drawing first; see
[[drawings-are-truth]]). A port authored from inference, a guessed thread, a clearance-vs-tapped mix-up, or an
assembly coordinate leaked into a part frame is a defect that the audit will catch and that you are accountable
for. Author each part's ontology as if it will be re-checked against the manufacturer drawing — because it will.
Mark anything genuinely unverifiable `unknown`/`nominal` explicitly rather than asserting it.

The attachment ontology is the application's single most important asset: (1) it is how a valid assembly is
verified at all, and (2) it collapses the design space — almost every catalog part has *baked-in attachment
logic* (a bore goes on a shaft of its diameter; a toothed clamp sandwiches a belt of its pitch; a foot bolts
into a T-slot; a counterbored pattern lands on a matching tapped pattern). Exploiting that logic is the
strongest weapon for computing valid designs, so each attachment must be **right**, not merely residual-green.
Therefore, **the moment you assign how a part attaches, LOOK at just that mating pair in isolation** (the
inserted part + its acceptor, nothing else) and **annotate the render with the measurements that decide
validity** — bore Ø vs shaft Ø, hole-pattern span, seating gap, reach/overhang, tooth pitch & engagement.
Ask: are these two parts *physically held* by a real feature, or just numerically coincident? A green residual
with the parts floating apart is the canonical failure (a pulley "coaxial" to an abstract axis with NO screw
holding it; a belt "coplanar" to a plate it never touches; a clamp that reaches 67 mm into space to a belt it
doesn't grip — all shipped with residual 0.000 and all nonsense). Do NOT proceed to the next part until the
isolated, annotated picture shows a *real joint with a real fastener/feature carrying the load*. Then repeat
the isolation look in the FULL assembly. Tool: `benchmarks/_attach_check.py` (renders a pair + dim overlays).
**Ontology-correction loop** when a look reveals a bad attachment: diagnose which layer is wrong — (a) the
mechanism understanding (is this even how the part attaches? e.g. an idler needs shaft+bearing, not a fasten),
(b) the part choice (too long/short, wrong hole), (c) the placement/frame, (d) a MISSING part (the load needs
a fastener/jaw that isn't in the BOM yet) — fix that layer, re-look in isolation, then re-look in context.

### 2. Every physical part is a real catalog part with its real CAD.
Use McMaster or Misumi as appropriate. No fabricated boxes, no placeholder geometry, no "modelled as a box, as it would be in a real build." A box
has no holes, faces, or datum — nothing to mate against or to see — so it makes every check (and every
render) a lie. If a class seems to need a fabricated part, that's a signal: FIRST find the catalog part
(mounted bearings, standoffs/spacers, belt clamps, mounting plates, motor mounts, idlers all exist — and
Misumi **configurable plates** take arbitrary length/width/hole layouts, see [[catalog-discovery]]), or change
the design so a catalog part fits.

**Catalog-first is the default; a rigid structural part may be custom-made ONLY as a last resort, and only
after a RECORDED catalog search.** The gate for licensing a custom rigid part — ALL of:
  (a) no stock catalog part fits, checked on BOTH vendors (McMaster + Misumi); AND
  (b) no CONFIGURABLE catalog part (Misumi FPT/configurable plates, configured extrusions, etc.) fits; AND
  (c) no reasonable design change lets a catalog part fit.
Write that search — queries run, candidates found, why each was rejected — into the part's `evidence`/
`provenance`. **An unrecorded custom rigid part is a defect the audit rejects**, even if its ontology is
perfect. "Licensed" means *passed this gate*, nothing looser.

Two things are PRE-LICENSED and need no search: (1) the one genuinely flexible element (a belt loop), built
from its catalog spec and fitted to the assembly; (2) standardized commodity fasteners/spacers — screws,
washers, nuts, T-nuts, standoffs — which may be standard-generated (Hard Rule 6 / [[standard-fastener-generator]]).
A licensed custom part is then held to the SAME full attachment-ontology standard as a catalog part
(Hard Rule 6) — real holes/threads/seats in the CAD *and* the def, never a box.

### 3. Units: everything is METRES at the glTF boundary — and you verify it by looking.
cascadio writes glTF in metres; STEP is mm. ANY mesh you generate must be exported in metres too. A part
authored in mm renders 1000× too large and flies off-screen — which is exactly how broken parts hid from
view. If a part isn't visible at sane scale in the render, its units/placement are wrong; fix that before
judging anything else.

### 4. Keep the universal ontology small; put catalog diversity in evidence and recipes.
Do not create an ontology class for a catalog family such as `t_slot_nut`, `shoulder_screw`, `bearing_block`,
or `timing_pulley`. Those are discovery/annotation families that decompose into the universal bounded
engagement forms below. Add a new engagement family or relation only when a real attachment cannot be
represented as a composition of the existing forms, and log the minimal counterexample in
`out/ontology_log/`. New catalog aliases, extraction mappings, annotation recipes, and family formulas do
**not** expand the ontology.

### 5. The constraint/attachment engine is generated PRECISELY and INDEPENDENTLY of what you're building — NEVER fudge a fit.
This is the whole reason the engine exists (`assembly/mate_solver.py`). Every mating feature — hole pattern,
axis, face, tooth pitch/direction — is **MEASURED from the real part's CAD/drawing** and authored in that
part's own frame, *before and regardless of* the assembly you want. The engine then SOLVES a part's pose
from its `enforce` constraints and computes the real residual of every `check`. A mismatch must SURFACE as a
failure — you may not hand-pick target coordinates, loosen a pattern, or invent a "sliding plate" hole set
to make the number come out 0. (Caught red-handed: the Misumi TBCN2-6 belt clamp's clearance holes measure
**8.0 × 11.4 mm**; the McMaster 6709K211 carriage's threaded acceptor is **10 × 10 mm M2** — they do NOT
bolt together, acceptor-fit RMS = 1.22 mm. The honest engine FAILS this; the fix is to **find a real part
that actually fits**, not to massage the inputs.) If a fastener/mate fails, change the *part*, never the
numbers. Both sides are first-class bounded engagement ports and are authored independently from evidence.
A receiver is not an abstract axis or infinite plane: its diameter/profile, finite span/boundary, access,
and relevant periodic/thread parameters must be represented numerically before matching.

---

### 6. FASTENERS ARE REAL PARTS — a verified mate is NOT a fastened joint until the screws/nuts EXIST.
This is where a whole assembly slipped through: I built the RU85 stage with every bolt pattern coincident
(pattern RMS 0.000) and every thread matching, the load-path gate said HELD, and the renders looked plausible —
but there was NOT A SINGLE SCREW OR T-NUT in the BOM. "These two patterns coincide and the threads are
compatible" is **necessary but not sufficient**: it proves the joint *can* be fastened, not that it *is*.
A floating part above a matching hole pattern is the canonical lie (same family as the residual-0 floating pulley).
Therefore:
- **Every load-bearing attachment whose closure is a fastener MUST instantiate the actual fastener PART INSTANCES**
  (real catalog or standard-generated screws/nuts/T-nuts), placed in the assembly, **one per pattern member**.
  An N-hole bolt/bearing pattern needs N screw instances; a T-slot foot needs its T-nut + clamp screw.
- The load-path gate now ENFORCES this (`ontology/load_path.py`): a bolt/bearing-pattern closure counts the
  real `screw_into_threaded_receiver` (etc.) instances threading into the seat — **0 of N ⇒ UNHELD ("NOT
  FASTENED")**, partial ⇒ INCOMPLETE, N of N ⇒ confirmed. Final validation requires every load-bearing joint
  fully fastened. (A standalone bound fastener slot must be a real part in the BOM, not a port.)
- **The fasteners must also be PLACED so the LOOK shows them.** If a render of a bolted joint shows no screw
  bodies, the joint is not modeled — fix it before claiming the assembly is done. Standardized commodity
  fasteners (screws/washers/T-nuts/standoffs) may be standard-generated (see [[standard-fastener-generator]]),
  but they must be instantiated, not assumed.
- **Custom/generated parts are held to the SAME attachment-ontology standard as catalog parts — author their
  FULL ontology, in the CAD *and* the def** (and only AFTER the part passes the Hard Rule 2 catalog-first gate —
  a recorded search proving no stock or configurable catalog part fits; standard fasteners/belt are pre-licensed).
  Every real mounting hole, thread, pilot, counterbore, and seat must
  be both a bounded `EngagementPort` AND actually cut into the part's CAD geometry — not a stub, not "holes are a
  secondary op, omitted from the blank," not a single representative hole. A part fastened at N points needs N
  modeled holes (in CAD) + the matching port group + N fastener instances. (Caught: the rotary tabletop shipped
  as the BLANK Misumi plate with ZERO holes in its CAD, so it read as bolted in ONE place, not four; and the
  one-piece "drum" hid a part it physically traps. Generating a part is not a license to under-model it.)
- **Check the ASSEMBLY SEQUENCE / insertion access, not just the final fit.** Every part needs a feasible install
  order with a clear insertion route -- no part trapped by parts placed before it (a closed bore only goes onto a
  shaft AXIALLY; an integral feature larger than a bore traps whatever must slide through it). A green fit + green
  load path passed a physically un-buildable assembly (the one-piece drum trapped the pulley). When that bites,
  split the part (a bolt-on cap, added last) even at the cost of an extra custom part.
- **Run a PART-INTRINSIC manufacturability gate (DFM), separate from the assembly checks** (`ontology/
  manufacturability.py`). A hole hanging off a part's edge is a defect as real as a floating fastener, but NO
  assembly/attachment check sees it -- it is intrinsic to the part. Check hole-to-edge material (>= ~0.75-1xD)
  and hole-to-hole material on every authored part. (Caught: the Oe160 cap put M6 taps at R77.8 -> the hole ran
  OFF the R80 edge by 0.8 mm; pattern/engagement checks all passed.) Also judge FASTENER LENGTH numerically
  (`thread_engagement`): the screw's threaded span must REACH and ENGAGE its receiver's tapped span (>= ~0.8-1xD)
  at the placed poses -- a coincident pattern + matching pitch is NOT fastened if the screw is too short to
  bridge the stack (caught: M5x16/25 cap bolts ending inside the pulley, 16 mm short of the adapter tap).

# THE ATTACHMENT ONTOLOGY v2 (NORMATIVE)

## 0. Scope and separation

The ontology is the **numerical geometric annotation of how a real 3-D part can engage other numerically
annotated geometry**. It is not a taxonomy of all products and not a complete engineering simulation.

Keep these layers separate:

1. **Catalog/discovery family** — `timing_pulley`, `t_slot_nut`, `shoulder_screw`, `linear_guide_block`, etc.
   This supplies search vocabulary, expected fields, likely ports, complementary product families, and an
   annotation recipe. It is evidence/guidance, not a top-level attachment class.
2. **Evidence and family geometry model** — raw catalog claims, drawing dimensions, spec-sheet rules,
   configurator parameters, formulas/branches, CAD observations, provenance, confidence, and reconciliation.
3. **Immutable part definition** — one local frame, bounded numerical engagement ports, groups, and CAD URI.
4. **Part instance** — a reference to a part definition plus one assembly transform. Never put assembly
   placement into a library part definition.
5. **Attachment template** — a generic multi-part mechanism composed from ports, pose relations,
   compatibility predicates, closure, and a real load path.
6. **Attachment instance** — bindings from a template's participant slots to actual part-instance ports.

**Strict geometry, permissive decision policy:** annotate geometry as strongly as evidence allows. A known
contradiction fails. Missing tolerances, ratings, or closure facts produce `UNKNOWN`/`INCOMPLETE` and a human
review item; missing data never silently means incompatible.

---

## 1. Mathematical loci and bounded value types

Keep the existing loci:

- `point(position)`
- `axis(origin, direction)`
- `plane(origin, normal)`
- `path(points/analytic_definition, closed)`

They are idealized references, not physical engagement by themselves. The v2 schema also uses small value
types inside ports; these are not new top-level ontology classes:

- `interval(min, max, unit)`
- `polygon2d(vertices, holes=[])` in a declared local `(u,v)` frame
- `local_frame(origin, x_axis, y_axis, z_axis)`
- `transform(rotation, translation, scale=1)`
- `measurement(nominal | min/max, unit, evidence_refs)`

All library geometry is authored in **millimetres in the immutable part-local frame**. glTF remains metres at
the rendering boundary.

---

## 2. Universal bounded engagement families

There are six engagement families. They are numerical forms, not part classes. A catalog part usually emits
several ports and groups; named items such as `bearing_seat` or `T-slot nut` are compositions/recipes.

### 2.1 `cylindrical`

Covers shafts, journals, pins, bores, bushings, bearing races, shoulder regions, collars, and round rails.

Required:

```yaml
family: cylindrical
polarity: insert | receiver
geometry:
  axis: {origin: [x,y,z], direction: [dx,dy,dz]}
  radial_interval_mm: {min: r_min, max: r_max}
  axial_interval_mm: {min: s_min, max: s_max}   # coordinates along axis
  material_side: inside | outside
```

Optional: diameter tolerance interval, surface segments, insertion directions, adjacent stop faces,
key/flat/spline child ports, surface finish, and intended-motion hints. Generic matching checks axis
alignment, radial containment/clearance, finite axial overlap, and access. A shoulder journal is a
`cylindrical insert + adjacent planar stop`; it is not a separate universal class.

### 2.2 `planar`

Covers mounting seats, washer/head bearing faces, bracket faces, axial shoulders, flanges, and clamp jaws.

Required:

```yaml
family: planar
polarity: contact
geometry:
  plane: {origin: [x,y,z], normal: [nx,ny,nz]}
  boundary_uv_mm: {outer: [[u,v], ...], holes: [[[u,v], ...], ...]}
  material_side: positive_normal | negative_normal
```

Generic matching checks opposed normals, gap, **bounded projected overlap area**, and required support region.
Infinite-plane coplanarity alone is never proof of contact.

### 2.3 `swept_profile`

Covers T-slots, dovetails, tongues/grooves, keyways, extrusion channels, captured tracks, and guide profiles.

Required:

```yaml
family: swept_profile
polarity: insert | receiver
geometry:
  sweep_path: <axis or path reference>
  sweep_interval_mm: {min: s_min, max: s_max}
  section_frame: <local frame normal to sweep>
  section_profile_uv_mm: {outer: [[u,v], ...], holes: [...]}
  material_side: inside_profile | outside_profile
```

Generic matching checks profile containment under an allowed orientation, finite swept overlap, capturing
lip/undercut overlap where required, and a feasible insertion/removal route. `slot` is no longer a sufficient
annotation; the actual section profile is required when the profile carries attachment logic.

### 2.4 `threaded`

Covers internal/external machine threads and screw threads. CAD may omit helices; generate this port from the
catalog/drawing callout and reconcile its axis and span to the simplified CAD.

Required when known:

```yaml
family: threaded
polarity: internal | external
geometry:
  axis: <axis>
  axial_interval_mm: {min: s_min, max: s_max}
thread:
  standard: ISO_metric | Unified | other | unknown
  designation: M4x0.7 | 1/4-20_UNC | null
  pitch_mm: 0.7
  handedness: right | left
  starts: 1
  major_diameter_mm: {min: ..., max: ...} | null
  minor_diameter_mm: {min: ..., max: ...} | null
  pitch_diameter_mm: {min: ..., max: ...} | null
  flank_angle_deg: 60 | null
```

A designation may generate the numerical defaults, but preserve the designation and evidence. Matching checks
polarity, pitch, handedness, thread form, diameter compatibility when known, and engaged axial length/turns.

### 2.5 `periodic`

Covers timing teeth, gear/rack teeth, splines, sprockets/chains, and toothed clamp regions without requiring
per-tooth CAD geometry.

```yaml
family: periodic
subtype: rotary | linear
polarity: external | internal | opposing
geometry:
  support: <axis+radius+axial interval OR plane/path+bounded active region>
periodicity:
  pitch_mm: 3.0
  count: 20 | null
  phase: 0.0 | null
  active_width_mm: {min: ..., max: ...}
  direction: [dx,dy,dz] | null  # Denotes BELT TRAVEL DIRECTION, not physical tooth orientation
profile:
  family: S3M | GT2 | involute_20deg | unknown
  parameters: {}
```

Matching checks pitch/profile compatibility, active-width overlap, direction, tangency/center-distance where
applicable, and phase only when phase is physically constrained. A `pitch_circle` is now a derived support
for a rotary periodic port, not a standalone semantic role.

### 2.6 `flexible_path`

Covers belts, chains, cables, and routed flexible elements. The catalog part definition stores material and
cross-section/periodicity; the assembly instance stores or generates the routed path.

```yaml
family: flexible_path
geometry:
  center_path: <path reference or generated-path recipe>
  width_mm: {min: ..., max: ...}
  thickness_mm: {min: ..., max: ...} | null
  minimum_bend_radius_mm: ... | null
  interaction_sides:
    toothed: <bounded side reference> | null
    backing: <bounded side reference> | null
periodicity: <optional periodic decoration>
```

Do not embed an assembly-specific belt loop in the immutable catalog definition. Generate the loop from the
selected pulleys and catalog pitch length, then annotate that part instance's routed geometry.

---

## 3. Port schema

Every usable attachment affordance is a bounded `EngagementPort`:

```yaml
port:
  id: stable_part_local_id
  family: cylindrical | planar | swept_profile | threaded | periodic | flexible_path
  polarity: <family-specific value>
  geometry: <family-specific required numerical contract>
  access:
    insertion_directions: [[x,y,z], ...] | unknown
    removal_directions: [[x,y,z], ...] | unknown
    access_region: <optional bounded region>
  symmetry:
    continuous: [rotation_about_axis] | []
    discrete_transforms: []
  kinematic_signature:
    residual_motions: [translate_axis, rotate_axis, ...] | derived
  semantic_aliases: [shaft_bore, bearing_seat, mounting_face]  # search/display only
  evidence_refs: [evidence_id, ...]
  annotation_status: confirmed | nominal | inferred | partial | unknown
  unknowns: []
```

`semantic_aliases` and catalog family names never drive geometric acceptance. Acceptance is generated by
family/polarity plus numerical predicates. Do **not** store brittle lists such as
`can_accept: [shaft_journal, shoulder_journal, axle, pin]`.

### Measurements and tolerances

Prefer numerical intervals. If only nominal dimensions are available, preserve that distinction:

```yaml
nominal_diameter_mm: 6.35
tolerance: unknown
```

Do not promote fuzzy labels such as `close_running` into authoritative fit classes. Optional intent labels are
limited to `free_motion | sliding_motion | locating | fixed_interference | unspecified` and are ranking hints
only. Exact fit is computed from bore/insert intervals or a cited standard designation when available.

---

## 4. Groups, patterns, adjacency, and composition

A `PortGroup` is a first-class exact composition, not a new engagement family:

```yaml
port_group:
  id: block_mount_pattern
  kind: repeated_ports | composite_port | continuous_domain
  frame: <local frame>
  members:
    - {port: hole_1, transform: <member transform>}
    - {port: hole_2, transform: <member transform>}
  symmetry:
    allowed_permutations: []
    generators: [{rotation_deg: 180}]
  placement_domain: <optional path/interval>
  evidence_refs: []
```

Use groups for bolt patterns, paired bearing faces, repeated rail holes, continuous T-slot placement domains,
and other exact relationships. Pattern matching solves correspondence subject to declared symmetry; never zip
hole lists by accident.

Named engineering concepts remain **recipes**:

```text
clearance hole      = cylindrical receiver + through access
counterbore         = cylindrical receiver + larger shallow receiver + annular planar seat
bearing seat        = cylindrical receiver + axial planar stop
shoulder journal    = cylindrical insert + axial planar stop
T-slot nut          = swept-profile insert + planar bearing pair + internal threaded port
keyed pulley bore   = cylindrical receiver + swept-profile keyway receiver + hub faces
```

Recipes guide annotation and discovery but compile to ports/groups; they do not add top-level matcher classes.

---

## 5. Pose relations, compatibility predicates, and status

Separate **pose solving** from **fit/validity**.

### Pose relations

Keep a small set:

- `coincident(point, point)`
- `coaxial(axis, axis)`
- `coplanar(plane, plane)`
- `distance`
- `angle` (`parallel` is angle 0)
- `tangent(path/support)`

### Numerical compatibility predicates

Predicates are emitted by the port-family matcher or attachment template, not improvised in prompts:

- `radial_fit`
- `axial_overlap`
- `bounded_area_overlap`
- `profile_containment`
- `thread_match`
- `pitch_profile_match`
- `active_width_overlap`
- `pattern_correspondence`
- `insertion_access`
- `closure_present`
- `load_path_connected`

Every predicate returns `PASS | FAIL | UNKNOWN` plus measurements and evidence. Checks are classified:

- `hard_geometry`: a known failure rejects the candidate;
- `required_closure`: missing/unknown yields `INCOMPLETE` or review;
- `advisory_engineering`: ranks candidates but does not normally reject them.

Overall attachment states:

- `confirmed`
- `nominally_compatible`
- `compatible_with_assumption`
- `incomplete`
- `unknown`
- `contradicted`

Known mismatched thread/pitch/profile/pattern or impossible containment is `contradicted`. Missing tolerance,
load rating, or unmodeled access is not a contradiction.

---

## 6. Attachment templates and instances

An attachment is usually a small multi-body mechanism, not one binary mate. Replace opaque interface functions
and `requires: [part_names]` with declarative templates:

```yaml
attachment_template:
  id: retained_revolute_on_journal
  participants:
    rotating_body: {requires_port: {family: cylindrical, polarity: receiver}}
    journal:       {requires_port: {family: cylindrical, polarity: insert}}
    stop_a:        {requires_port: {family: planar}}
    stop_b:        {requires_port: {family: planar}}
    support:       {requires_connection_to_ground: true}
  enforce:
    - coaxial(rotating_body.axis, journal.axis)
    - oppose_and_seat(rotating_body.face_a, stop_a.face)
  checks:
    hard_geometry:
      - radial_fit(rotating_body, journal)
      - axial_overlap(rotating_body, journal)
    required_closure:
      - axial_motion_closed_by(stop_a, stop_b)
      - load_path_connected(rotating_body, journal, support)
  result:
    expected_joint: revolute
```

An `AttachmentInstance` binds every participant to a real `part_instance.port`. No template endpoint may be a
free world axis or plane. Closure says which additional engagements remove the residual motions of the bare
engagement. The load path is an explicit graph through real parts to ground.

The core mechanism verbs are compact and compile to relations/predicates:

- `insert`
- `seat`
- `thread`
- `capture`
- `retain`
- `clamp`
- `key`
- `mesh`
- `guide`
- `couple`

Joints remain `fixed`, `revolute`, `slider`, and `screw`; belt/gear relations are couplings between joint
coordinates, not extra joints.

Split the old monolithic `belt_drive` into composable templates:

1. `timing_belt_mesh`
2. `belt_route`
3. `belt_clamp_or_capture`
4. `rotary_to_linear_coupling`

A complete axis composes them. Each can be checked and rendered independently.

---

## 7. Evidence and AI annotation schema

Evidence guides the annotation agent; it is not geometry and must not leak into matcher semantics.

```yaml
evidence_record:
  id: unique_id
  source_type: catalog_category | configurator | product_page | drawing | datasheet | cad | derived | inferred
  source_uri: ...
  locator: breadcrumb / field label / drawing callout / CAD entity
  raw_value: ...
  normalized_claim:
    target_path: ports.bore.geometry.radial_interval_mm
    value: ...
    unit: mm
  extraction_method: dom | vision | pdf_text | cad_measurement | formula | human
  confidence: 0.0..1.0
  notes: ...
```

Use field-level evidence. A single part-wide confidence score is insufficient.

### Source responsibilities

- **Catalog hierarchy/category:** family prior, functions, aliases, expected ports, expected fields,
  complementary categories, likely attachment templates.
- **Family/configurator page:** valid parameter ranges, part-number grammar, option branches, family formulas.
- **Product detail page:** selected nominal values, compatibility claims, standards, material, ratings.
- **2-D drawing:** datums, exact feature locations/extents, hole patterns, thread callouts, tolerances.
- **Datasheet:** installation rules, recommended fits, load/environment limits, standard references.
- **CAD:** topology, local coordinate correspondence, measured surfaces/spans, unexpected or omitted geometry.
- **Rendered attachment:** interpretation, missing intermediaries, load path, gross scale, accessibility/context.

Preserve raw claims before normalization. `raw_spec` may not be empty merely because values were copied into
`spec`.

### Family geometry model and CAD reconciliation

For each catalog family, build a small model that maps enumerated/configuration parameters to expected ports in
the drawing frame. The mapping may be affine, formula-based, or conditional; do not assume everything is
linear:

```yaml
family_geometry_model:
  inputs: [A, B, C, bore_type]
  branches:
    - when: bore_type == keyed
      expect: [keyway_port]
  predictions:
    - port: hole_1
      center: {x: -C/2, y: -B/2, z: 0}
```

Then solve **one** drawing→CAD similarity transform:

```text
x_CAD = scale * R * x_drawing + t
```

Fit it from several independent features. Report position RMS, maximum axis-angle error, and per-port residuals.
If one transform cannot reconcile the predicted features, stop and diagnose: wrong configured part/CAD,
misread dimension, wrong datum, unit error, CAD simplification, or an incorrect family model. Never repair the
assembly by changing part-local coordinates.

Expected CAD simplifications (e.g. omitted thread helices) must be explicit reconciliation policies, not silent
exceptions.

### Required annotation workflow

For every new part:

1. Identify catalog family and breadcrumb; load/create its annotation recipe.
2. Extract and preserve raw category/configurator/product claims.
3. Normalize units, aliases, standards, and configured part-number fields.
4. Parse drawing/datums and produce a predicted bounded-port model.
5. Read datasheet rules relevant to fit, access, retention, and use.
6. Detect/measure candidate CAD geometry.
7. Fit the single drawing→CAD transform and reconcile every predicted port.
8. Emit confirmed/nominal/partial ports and groups; expected-but-unfound means `unknown`, not `absent`.
9. Propose generic attachment templates from the emitted ports and family recipe.
10. Run numerical checks, render each attachment in isolation with deciding dimensions, then render in context.

---

## 8. Normative v2 part-definition shape

```yaml
schema_version: 2
part_number: ...
classification:
  catalog_family: timing_pulley
  broader_families: [rotary_power_transmission]
  aliases: []
source:
  url: ...
  retrieved_at: YYYY-MM-DD
raw_spec: {...}
normalized_parameters: {...}
cad:
  source_uri: ...
  gltf_uri: ...
  units: metre
part_frame:
  units: millimetre
  drawing_to_cad: {scale: ..., rotation: ..., translation: ...}
ports: []
port_groups: []
annotation_status:
  overall: complete | partial | blocked
  expected_ports: {}
evidence: []
provenance: {...}
```

Part definitions are immutable by part number/configuration/revision. If the manufacturer changes geometry,
create a new revision. Assembly transforms live only in `PartInstance`/placements.

One placement source per part instance (`out/<name>_placements.json`) feeds both math and viewer; never compute a
pose twice.

---

# ONTOLOGY v1 → v2 IMPLEMENTATION AND LIBRARY MIGRATION

This migration is the next ontology task. Do not continue adding v1 `role` records or new hand-coded interface
functions while it is in progress.

> **MIGRATION STATUS (2026-06-20 r8): FOUNDATION + TEMPLATE/CLOSURE + ENFORCE→POSE BRIDGE LANDED, additively.**
> Steps A.1–A.8 (incl. pose-solve) are built and smoke-tested; v1 is untouched and rungs 0/1 still PASS. Modules:
> `ontology/ports.py`, `schema_v2.py`, `ports_match.py` (8 matchers), `templates.py` (typed registry, bans free
> endpoints), `load_path.py` (3-state closure), **`pose_solve.py` (solve a moving part's pose FROM template
> `enforce` via `mate_solver`)**. 6 parts in `library_v2/`. v1 snapshot at `ontology_v1_snapshot/`. See the r8
> STATE round and `out/ontology_log/v2_migration.md`. NOT yet done: rebuild rung2 on v2 end-to-end + LOOK,
> migrate remaining parts (rail, belt), `validate_library_v2.py`.

## A. Code migration order

1. **Freeze and snapshot.** Tag the current library/benchmarks as `ontology-v1`; keep a read-only copy. Add
   `schema_version` to every record before conversion.
2. **`primitives.py`.** Preserve `Point`, `Axis`, `Plane`, `Path`. Add typed helpers for `Interval`, `Polygon2D`,
   `LocalFrame`, and measurement intervals. These are bounded value types, not new semantic roles.
3. **Create `ports.py`.** Implement the six discriminated `EngagementPort` families with strict required-field
   validation and family-specific polarity. Reject giant untyped `params` bags.
4. **Replace `roles.py` gradually.** Move old role names to `semantic_aliases` and annotation recipes. Keep a
   temporary v1 adapter, but no matcher may make decisions from aliases.
5. **Revise `schema.py`.** Introduce `PartDefinition`, `PartInstance`, `PortGroup`, field-level `EvidenceRecord`,
   `AnnotationStatus`, and `schema_version=2`. Ensure a part definition has no assembly placement.
6. **Revise `constraints.py`.** Separate `PoseRelation` from `CompatibilityPredicate`; add
   `PASS/FAIL/UNKNOWN`, check severity (`hard_geometry/required_closure/advisory_engineering`), and measured
   result payloads.
7. **Replace `interfaces.py` with declarative templates.** Implement generic templates and explicit participant
   bindings/load paths. Keep old functions only as deprecation adapters that compile to v2 and warn.
8. **Revise `mate_solver.py`.** Solve pose only from `enforce`; evaluate bounded geometry/predicates after pose.
   Ban world-lambda/free-axis endpoints. Add family matchers for cylindrical, planar, swept-profile, threaded,
   periodic, and flexible-path ports.
9. **Add `scripts/migrate_ontology_v1_to_v2.py`.** It may mechanically preserve old data and propose ports, but
   must mark missing spans/boundaries/tolerances as `unknown`; it may not invent them.
10. **Add `scripts/validate_library_v2.py`.** Validate schema, immutable frames, evidence links, drawing→CAD
    residuals, required family fields, duplicate part definitions, and assembly-coordinate leakage.
11. **Rebuild attachment checks.** `_attach_check.py` overlays the same dimensions consumed by predicates:
    finite spans, diameters, bounded face overlap, profile containment, pattern residual, pitch, and closure.
12. **Re-run rungs 0–2.** A v1 PASS is historical only. Each rung passes v2 after its parts are migrated,
    attachment templates instantiate real load paths, numerical predicates are reported, and the result is
    looked at in isolation and context.

## B. Minimum v2 mechanism-template set

Implement only what the current rungs and their immediate neighbors require:

- screw through clearance port into threaded receiver
- screw through clearance ports into nut
- T-slot captured nut + screw clamp
- retained revolute on shoulder journal
- fixed hub on journal via explicit key/set-screw/clamp mechanism
- bearing inner race on journal + outer race in seat
- bounded bolt-pattern seat
- profile carriage on guide
- timing-belt periodic mesh
- belt capture/clamp
- rotary-to-linear belt coupling

Do not add catalog-specific templates. `T-slot nut` remains a part-family annotation recipe; the mechanism is
composed from profile containment, thread engagement, planar clamping, and load-path closure.

## C. Existing part-library revision plan

Every listed part must be re-opened against its category/product page, drawing/spec sheet, and CAD. Migration
is not a JSON rename; missing bounded geometry must be measured or marked unknown.

### `1277N16` timing pulley — merge the two erroneous definitions

- Delete the duplicate `pulley1/pulley2` part definitions after preserving them in the v1 snapshot.
- Create **one** immutable `1277N16` definition in its real CAD-local frame. The current `+66.036` and
  `-66.036` Z coordinates are assembly placements leaked into part geometry and must not survive.
- Convert `bore` to a `cylindrical receiver`: measured axis, radial interval from 6.35 mm nominal/tolerance,
  and measured finite hub/bore axial span.
- Convert `pitch` to a `periodic rotary` port: same local axis, pitch radius 12.13 mm, 15 teeth, pitch 5.08 mm,
  measured active axial width, profile family, and phase only if physically meaningful.
- Annotate set screw/key/clamping features only if found in product evidence and CAD/drawing.
- Add bounded hub/flange planar regions where they participate in seating or belt containment.
- Create two `PartInstance`s in any assembly that uses two pulleys; their transforms belong in placements.

### `1327K65-rail` round rail

- Add a `cylindrical insert` port with 6.35 mm nominal diameter and 152.4 mm finite axial span in the rail's
  local frame; add tolerance/surface evidence when available.
- Add end planar regions only if used for seating/retention.
- `cad.gltf_uri: null` and empty features mean `annotation_status: blocked/partial`, not that the rail has no
  ports. Fetch/reconcile CAD or explicitly preserve drawing-only geometry with unknown CAD transform.

### `1679K197` timing belt

- Store catalog properties in the immutable definition: pitch 5.08 mm, 67 teeth, pitch length 340.36 mm,
  width 6.35 mm, profile, thickness, and bend limits when available.
- Emit a `flexible_path` specification plus a `periodic linear` toothed-side port. Do not store an assembly loop
  in the part definition.
- Add a generated-geometry recipe; the assembly instance creates the routed path and verifies total pitch
  length against 67 × 5.08 mm.

### `90263A239` shoulder screw

- Emit an external `threaded` port for M4×0.7 with measured thread span.
- Emit a 5 mm-diameter `cylindrical insert` shoulder with **10 mm finite span**.
- Emit the head underside as a bounded `planar` stop; optionally annotate the drive interface for access.
- This record must make the existing idler mismatch visible through `axial_overlap`, not prose.

### `SHTF20S3M100-5` bearing idler

- Emit the 5 mm center-bore/bearing-inner-race `cylindrical receiver` with finite span.
- Emit the S3M `periodic rotary` port with pitch 3 mm, 20 teeth, measured active width, and pitch radius.
- Emit axial side/retention regions. Treat the catalog idler as a catalog subassembly; internal bearing motion
  may be represented by an internal revolute capability only when supported by manufacturer evidence.

### `SSEB20-220` rail and block

- Keep rail and block as separate immutable part definitions if they are separately instantiated, while
  recording that they came from one configured catalog assembly.
- Rail: emit the bounded guide `swept_profile insert`, travel interval, mounting planar region, and repeated
  mounting ports/groups.
- Block: emit the complementary guide receiver/profile to the extent visible/measurable; where internal ball
  geometry is omitted, preserve the manufacturer series compatibility as evidence and mark exact internal
  profile partial rather than inventing it.
- Block top: emit four M4 internal-thread ports and a 25×30 mm exact `PortGroup`, plus the bounded top seat.

### `SL-TBLGS3M100-50-80-20-30-25-4` plate/clamp component

- Emit the four guide-side clearance/counterbore composites and exact 25×30 pattern group.
- Emit bounded top/bottom mounting regions and the measured toothed `periodic linear` region.
- Do **not** label a single toothed plate as a complete belt clamp. A complete clamp template requires the
  opposing jaw/capture geometry and fasteners that produce closure; otherwise status is `incomplete`.

### `6575N203` 40 mm T-slot extrusion

- Emit each longitudinal slot as a measured `swept_profile receiver` with the real cross-section and finite
  304.8 mm sweep interval; use a continuous placement domain along the slot.
- Emit bounded exterior mounting regions and end regions as needed. `slot width 8 × depth 12.2` alone is not a
  complete profile annotation if lip capture matters.

### `19155A34` bracket

- Emit each usable mounting hole as its cylindrical/threaded composite, exact pattern groups, and bounded
  planar mounting regions on both legs. Preserve the measured bend-frame relation.
- Do not create an abstract axle at the bracket. An idler attachment must bind to a real shoulder screw/shaft
  port connected through a real threaded or nut-backed bracket mount.

## D. v1 field mapping (adapter only)

```text
clearance_hole -> cylindrical receiver (+ through access); add bounded span and optional head-seat composite
threaded_hole  -> threaded internal port
shaft_bore     -> cylindrical receiver
bearing_seat   -> cylindrical receiver + adjacent planar stop recipe
mounting_face  -> bounded planar port
slot           -> swept_profile insert/receiver after section measurement
shoulder       -> cylindrical insert + planar stop recipe
pitch_circle   -> periodic rotary port with derived pitch support
```

The adapter must flag every missing required v2 field. It may not infer finite spans, face boundaries, profile
sections, tolerances, or closure parts merely from the old role name.

---

# BENCHMARK LADDER (each forces one capability)

| Rung | Build | DOF | Forces | State |
|---|---|---|---|---|
| 0 | screw + washer seated | 1 | bounded cylindrical + planar engagement | **v1 PASS; v2 migration/revalidation pending** |
| 1 | bracket bolted to T-slot extrusion | 0 | bounded patterns + profile capture + clamp closure | **v1 PASS; v2 migration/revalidation pending** |
| 2 | belt-driven linear axis | 1 | guide, retained revolutes, periodic mesh, belt capture/coupling | **IN PROGRESS, NOT passing — v2 pipeline runs + pieces verified in isolation, but the load-path gate is all-UNHELD; see STATE** |
| 3 | RU85 belt-driven rotary stage | 1 | large crossed-roller bearing AS the joint; race-segregation (touch only the correct ring); custom parts authored from a drawing (real STEP/glTF, not boxes); concentric stacked bolt patterns; locating pilot vs clamping bolts; clearance pass-through corridor; 4:1 belt reduction + motor on the stationary frame + tensioning DOF | todo (RU85 task; see task file) |
| 4 | Cartesian gantry (3× rung-2) | 3 | nested moving frames; orthogonality | todo |

---

# REFERENCE (operational how-to — secondary to the rules above)

## ★★★ ROBUST CATALOG-FETCH PIPELINE (2026-06-20 — AUTHORITATIVE; supersedes the scattered notes below) ★★★
> This is the single source of truth for getting a part's CAD. It took HOURS once because of avoidable
> thrashing; followed in order, it's minutes. **Read all of §0 before touching a browser.** The older
> "FAST PART-FETCH PROTOCOL", "When the site walls the bot", "Driving mcmaster.com", and "WORKFLOW LESSONS"
> sections below are kept for detail but are SUBORDINATE to this — where they say "relaunch Chrome if degraded",
> they are WRONG (see §0).

### §0. THE HARD RULES (each one cost real time to learn — do not relearn them)
1. **ONE long-lived `cdp-chrome` instance. NEVER kill+relaunch reflexively to recover a wedged tab.** A burst of
   relaunches / deep-link cold-launches strips the Akamai sensor cookie and gets `us.misumi-ec.com` to return
   **403 "Access Denied" SITE-WIDE** for the instance — which ALSO kills the CAD fetch (same session) and does
   NOT clear on retries. If a tab wedges, **open a NEW TAB** (`Target.createTarget`), don't kill Chrome.
2. **A wedged/stalled CDP target ≠ a dead browser.** Recover by switching/opening targets, never by restarting.
3. **Screenshots are SLOW (up to ~60–75 s), not failed.** Retry `Page.captureScreenshot` with a long ws timeout
   before concluding anything. (A stall is a render delay, not a foreground problem — don't chase window focus.)
4. **`Runtime.evaluate` WEDGES on heavy React+Drift pages** (the Misumi `/vona2/selector/` SPA). It is fine on
   classic `/vona2/detail/` pages and on McMaster. So: prefer classic detail pages; on the selector, use
   screenshot + coordinate-click ONLY (its cards are shadow-DOM/image — there are no anchors to scrape).
5. **Raw CDP, never Playwright `connect_over_cdp`** (it attaches to Drift iframes/workers and hangs ~180 s).
   Use `data/rawcdp.py` `Page(...)` or a raw `websocket` with `suppress_origin=True`.
6. **CIRCUIT BREAKER.** On a CONFIRMED 403/Access-Denied, STOP all storefront traffic; recovery is a separate
   HUMAN-ASSISTED re-warm, NOT a retry loop. Never deep-link a cold launch (it trips Akamai); launch to the
   HOMEPAGE and let a real page load / human browse re-establish the sensor cookie.
7. **Never run two Chrome processes against the same profile.** Don't use the everyday Chrome profile.

### §1. SESSION LIFECYCLE
- **Check alive:** `GET http://127.0.0.1:9222/json`. If a page target exists, REUSE it (no launch).
- **If dead, launch ONCE** (PowerShell `Start-Process`, not a kill+relaunch):
  `chrome.exe --remote-debugging-port=9222 --user-data-dir=C:/Users/stefa/cdp-chrome --window-size=1400,1000 https://us.misumi-ec.com/`
  (login + cookies persist in that profile; the homepage URL re-warms Akamai — do NOT deep-link).
- **Browser endpoint** (for `Target.*`, `Browser.setDownloadBehavior`): `GET /json/version` → `webSocketDebuggerUrl`.
- **New tab:** `Target.createTarget{url}` on the browser endpoint, then `Target.activateTarget{targetId}`, then
  attach to that target's `webSocketDebuggerUrl` from `/json`.
- **HEALTH CHECK (circuit-breaker-safe, no clicking):** in-page fetch `cadFormatList` for an OWNED PN →
  `{status:200, body.formatlist:[...]}` = **WARM**; `403`/"access denied" = **SESSION_BLOCKED** (stop, re-warm).

### §2. MISUMI (FA parts) — clean structured fetch, hands-off
- **Reach the part by the CLASSIC detail URL:** `…/vona2/detail/<seriesCode>/?HissuCode=<exact-PN>`. AVOID the
  `/vona2/selector/` SPA (it's the wedge-prone one). Discovery: read the live PN template + CONSTRUCT the PN, or
  use PARTcommunity for family metadata (`misumi.partcommunity.com/3d-cad-models/misumi`, plain-HTTP reachable,
  server-rendered JSF — good for params/grammar, but CAD download there needs a CADENAS login).
- **CAD:** `data/misumi_fetch.py::fetch_cad(pn)` — runs the in-page `cadFormatList`→`cadDownload`→GET-zip flow
  (brand `MSM1`, `STEP_AP203`), bounded polling while the server builds, **circuit breaker** (raises
  `SessionBlocked` on 403, `CadUnavailable` otherwise). Reuses the warm tab; never launches. Saves `cad/<PN>_STEP.zip`.
- **MSM1 only** — 3rd-party brands return 504/empty CAD. `cadFormatList` (not a valid-looking page) is the
  authority for CAD availability.

### §3. McMASTER (generic hardware: shoulder screws, shims, washers, T-slot nuts) — from the SAME warm browser
McMaster is a DIFFERENT Akamai property, so a Misumi block does not affect it; guest CAD needs no login.
- **Plain HTTP is useless** (returns a JS shell: bare `McMaster-Carr` title, no specs). MUST use the rendered browser.
- **Steps (raw CDP):**
  1. Browser endpoint: `Browser.setDownloadBehavior{behavior:"allow", downloadPath:<abs cad>, eventsEnabled:true}`
     (it still tends to land the file in `~/Downloads` — just move it after).
  2. `Target.createTarget{url:"https://www.mcmaster.com/<PN>/"}` + `Target.activateTarget` → a FRESH ACTIVE tab.
     **The CAD widget lazy-renders ONLY on the active tab** — re-navigating a background tab never shows it.
  3. Read specs while waiting: `document.title` carries the full descriptive name (real name = valid PN; bare
     "McMaster-Carr" = walled/shell); `document.body.innerText` has the spec table.
  4. Poll ~30 s for `a[download]` whose href ends `.STEP`. The href is concrete BUT an in-page `fetch` of it
     **403s** and a synthetic `el.click()` does NOTHING.
  5. **TRUSTED click:** get the link's `getBoundingClientRect` centre, then `Input.dispatchMouseEvent`
     mousePressed+mouseReleased at those coords. The STEP saves to `~/Downloads/<PN>_<desc>.STEP`.
  6. `shutil.move` → `cad/<PN>.step`; `cascadio.step_to_glb` (metres); MEASURE.

### §4. PER-PART WORKFLOW (bounded — user's procedure)
Source order per part: **local cache → PARTcommunity metadata → classic Misumi detail → McMaster → selector SPA
(last resort).** Validate the PN before requesting CAD. Return one accepted candidate + ≤2 alternates with: exact
PN, source/family, required dims, catalog + drawing values, **CAD-availability STATE** (one of `AVAILABLE /
BUILDING / CAD_UNAVAILABLE / INVALID_PART_NUMBER / AUTH_REQUIRED / SESSION_BLOCKED / ENDPOINT_CHANGED` — never a
generic "failed"), compatibility checks, unresolved fields, accept/reject reason. STOP once a candidate meets the
hard geometry AND CAD is available.

### §4b. ★ LEAVE BREADCRUMBS ON DISK *AS YOU GO* — never hold results only in memory (2026-06-22) ★
Fetching a part is SLOW (PN validation → page/drawing read → server-side CAD build → download → measure), and an
agent can be cut off at ANY step — a session/usage limit, an Akamai 403, a wedged tab. When that happens, anything
held only in the agent's context is **lost**, and the lead must restart the part from zero. (This bit us hard: a
batch of part-scouts hit the session limit ~25 min in and left almost nothing on disk — one even had *confirmed*
the bearing CAD was buildable, but that fact died with it.) So **persist every intermediate result the moment you
have it**, incrementally, under `candidate_evidence/<lead-slug>/<SOURCE>/<PN>/`:
- the moment a PN validates: write `manifest.json` with `{pn, source_url, brand, STATE}` (STATE = the §4 code).
- the moment you read it: dump page innerText/spec tables (`source/product_page.txt`), the drawing
  (`source/drawing_*.png`), and a `cad_availability.json` (e.g. `cadFormatList` returned `formatlist:[...]` ⇒
  `STATE: AVAILABLE` — the single most valuable breadcrumb; write it BEFORE attempting the slow download).
- the moment CAD lands: `cad/<PN>.step` + `.glb`; then `measurements/cad_measurements.json`.
- update `report.json` (the running accept/reject + STATE) after each step, not once at the end.
A breadcrumb that says "AVAILABLE under brand X, formatlist=[…]" lets the lead (or a resumed agent) finish the
download in seconds instead of re-deriving everything. Treat the final summary message as a CONVENIENCE, not the
deliverable — the deliverable is the on-disk evidence tree. The lead VERIFIES from disk, not from the message
(especially when the safety classifier was unavailable to review the subagent).

### §4c. ★ GOOGLE FIRST — always start PN discovery with WebSearch, never the storefront SPA (2026-06-22) ★
**Every parts-discovery agent (and the lead) MUST begin with `WebSearch`, for ANY part, before opening a browser tab.**
The slow, flaky part of catalog fetch was never the CAD — it was *finding which series/PN* on the eval-hostile,
screenshot-only React SPA (this cost the r-? scouts ~25 min each with mostly nothing to show). Google indexes the
storefront's detail pages and **Google's crawler is allowlisted by Akamai**, so we read the index second-hand and
skip the wall entirely:
- Query `WebSearch: site:us.misumi-ec.com <spec keywords>` (or `site:mcmaster.com`). The SERP returns the exact
  **`/vona2/detail/<seriesCode>/` URL + a title/snippet** that names the series and often shows an example PN —
  in ONE ~3 s call. This is ~10–50× faster than the SPA and far more reliable. (Demonstrated: "6061 configurable
  plate" -> seriesCode 110302243870; "hex standoffs one end threaded" -> 110302672970, each in one query.)
- If the obvious query returns adjacent junk (e.g. the motor, not its bracket), REFINE the query — Google still
  surfaces the right *vocabulary* (and viable alt vendors) faster than brute-forcing the storefront.
- **`WebFetch` on a Misumi/McMaster page is Akamai-403 (don't bother)** — Google's INDEX is open, the live page is
  not. So Google gives you the seriesCode + example PN; the **grammar/specs/CAD still come through the warm CDP
  session** (classic `/vona2/detail/` eval works) OR are skipped by constructing candidate PNs and brute-checking
  with `validate_pns` (cadFormatList).
- Full pipeline: **WebSearch (seriesCode + example PN) -> grammar via CDP/breadcrumb (or skip) -> construct PN ->
  `data/misumi_validate.validate_pns` -> `misumi_fetch.fetch_cad`.** Cache `series->grammar->brand` locally so the
  next lookup is free. See [[misumi-cad-pipeline-and-discovery]].

### §5. CONVERT + VERIFY (always)
`cascadio.step_to_glb(stp, glb)` → metres. **`trimesh.load(path, force='scene')` to ENUMERATE bodies** — a STEP
"part" is often an ASSEMBLY (the SL-TBLG set is 6 bodies: plate + jaw + 4 screws); `force='mesh'` MERGES them and
HIDES sub-parts (that merge is exactly how the SL-TBLG opposing jaw got wrongly annotated "absent"). Then MEASURE
every mating feature by mesh-section; set assembly constants from the MEASURED values, never the part name.

### §6. WHAT GOOD LOOKS LIKE (the proven path, 2026-06-20)
Misumi `cadFormatList` 200 → `fetch_cad` hands-off; McMaster `96654A131` via fresh-active-tab + trusted mouse
click → STEP in `~/Downloads` → `cad/96654A131.glb` (validated 9×9×25). Reusable memory:
[[misumi-rawcdp-protocol]], [[mcmaster-cdp-download]], [[misumi-cad-handsoff]].

## ★★ FAST PART-FETCH PROTOCOL — do this, in this order; don't improvise ★★
The part hunt used to eat hours. It doesn't have to. The slowness was NEVER the catalog — it was (a) Playwright
`connect_over_cdp` hanging on Misumi's Drift-chat iframes + service workers, and (b) fighting the React
configurator UI. Both are solved. **Default to Misumi for FA parts** (more permissive, fully scriptable CAD).

**0. Ask the user to enable auto-approve** (Shift+Tab → "bypass permissions"). Approval latency masquerades as
   "hangs". Do this first or every step is 10× slower.

**1. Talk to Chrome with RAW CDP, never `connect_over_cdp`.** Use `data/rawcdp.py` → `Page("misumi")`. It opens
   a websocket to the ONE page target (`suppress_origin=True`), so it never touches the Drift iframes/workers
   that wedge Playwright. `pg.evaluate(js, await_promise=True)`, `pg.navigate(url)`, `pg.screenshot(path)`.
   Needs `pip install websocket-client`. **⚠ DANGER (do NOT do the old advice here): killing+relaunching Chrome
   to "recover" a wedged/degraded target is what 403'd the whole Misumi session site-wide and cost hours.** A
   wedged target ≠ dead browser — open a NEW TAB instead (see §0/§1 of the ROBUST pipeline above). Only launch
   when `GET /json` shows NO process at all, and then launch to the HOMEPAGE (never a deep link), ONCE.

**2. Find the part:** navigate to `…/vona2/result/?Keyword=<descr>` (raw CDP `pg.navigate`), screenshot, read
   as VLM, pick the product, `pg.navigate` to its `…/vona2/detail/<seriesCode>/`. (Filter Brand=MISUMI/MSM1 —
   3rd-party brands have no buildable CAD; see [misumi-thirdparty-no-cad].)

**3. Get the PN by READING THE FORMAT, not by driving the UI.** On the detail page the live header shows the
   PN TEMPLATE with valid ranges, e.g. `FALBS-SP-T[1.6,2.3,3.2,4.5,6]-A[20-300/1]-B[15-200/1]-L[20-200/1]-N3`.
   Read it via raw-CDP eval (grab the longest `^<SERIES>-` text). Then **CONSTRUCT the PN string yourself** by
   substituting valid values into the brackets → `FALBS-SP-T3.2-A80-B30-L30-N3`. Do NOT fight the React inputs
   (setting `input.value` does NOT commit to React state — the displayed PN stays a template; wasted ~10 calls).
   Picking a `type`/material first re-renders and RESETS numeric fields & changes valid thickness sets — that's
   why reading the template after a type pick is the reliable source of the format.

**4. Fetch CAD via raw CDP** (no UI): run `data.browse._MISUMI_FETCH_JS` through `pg.evaluate(expr,
   await_promise=True)` with `{base:MISUMI_CAD_BASE, brand:"MSM1", pn:<constructed>, fmt:"STEP_AP203"}`.
   First call usually returns `status:"1"` + EMPTY `outPutPath` (server building) → **loop ~8× with 6 s sleep**;
   it returns `{b64,size}` within a try or two. An EMPTY-outPutPath means the PN is VALID and building (good
   signal), not an error. Write `b64`→`cad/<PN>_STEP.zip`. (This is `fetch_misumi_cad` but over raw CDP.)

**5. Convert + MEASURE (never assume geometry).** `zipfile` extract → `cascadio.step_to_glb(stp, glb)` (metres).
   Then SECTION the mesh for every mating feature (Hard Rule 5) — e.g. FALBS-...-N3's center hole is at Y=10
   from the bend, NOT centered at A/2 as the name implies; only the measurement told the truth. Set assembly
   constants (axle height, etc.) from the MEASURED values, then LOOK.

McMaster fallback (only if a part is McMaster-only): its CAD widget needs the live tab and is flakier — length
is a `td.spec-search--value` cell (click → combobox enables → PN becomes the length variant, e.g. 6575N25→
6575N203); CAD option `li[id^='dropdown-3-D STEP/']`; download `a._downloadAnchor_kifon_247 > button`. Page
scroll container is `.jo` (`scrollTop`), wheel doesn't move it. Close stale McMaster tabs after — piled-up
heavy tabs are what degrade the CDP connection.

## Two suppliers: McMaster (MRO) + Misumi (FA) — pick by part type
McMaster is general MRO/fasteners; it does NOT stock factory-automation linear-motion parts (belt clamps,
belt holders, tension plates). **Misumi** is the FA specialist — use it for motion/FA parts, McMaster for
generic hardware, and lean toward Misumi as the assemblies get more FA-shaped.

**★ DEFAULT TO MISUMI for scraping.** For the data we extract (structured specs, dimensional drawings, CAD),
Misumi's classic `/vona2/detail/` pages are far easier than McMaster: `Runtime.evaluate` reads innerText +
spec TABLES + the PN template + drawing image URLs cleanly, and CAD is hands-off (`cadFormatList`/`cadDownload`).
McMaster's listing/category grids are VIRTUALIZED — PNs aren't in the DOM and the grid renders BLANK headless
(only facet labels), and `captureScreenshot` times out — so *discovery* (finding a PN from a category) is the
painful part. Use McMaster only for generic hardware Misumi lacks, or when Misumi can't be warmed; once you
HAVE a McMaster PN, its detail-page `read_specs` + CAD download are fine. (See [[catalog-scrapeability]].)
Caveats on Misumi: the `/vona2/selector/` React SPA wedges `Runtime.evaluate` (use classic detail), non-MSM1
brands have no buildable CAD, and the session is Akamai-fragile (no relaunch; homepage re-warm). Confirmed real on Misumi:
**"Timing Belt Clamp Plate"** (the belt-to-carriage clamp) — configurable, supports belt types MXL/XL/S2M/
S3M/**2GT**/3GT/5GT + nominal width. Don't conclude "the part doesn't exist / the design is wrong" from
McMaster alone — check Misumi.

## When the site walls the bot → drive the user's real Chrome over CDP (the reliable CAD path)
Both sites bot-detect. McMaster trips Akamai's login wall after a burst of headless hits (NOT an account
requirement; not fixable by spoofing `webdriver` — it's IP/sensor-cookie reputation; curl can't help, the
download URL is generated client-side). Misumi (`us.misumi-ec.com`) is a Next.js/React SPA behind Akamai
whose CAD-Download button fires no modal under real/JS/coordinate clicks. **The robust path for both: drive
the user's actual Chrome.** Launch once (separate profile so it gets its own debug port):
`chrome.exe --remote-debugging-port=9222 --user-data-dir=C:/Users/stefa/cdp-chrome <url>`, then
`p.chromium.connect_over_cdp("http://127.0.0.1:9222")` and use `b.contexts[0].pages[0]`. The user signs in
once in that window (Misumi needs a free account; McMaster guest CAD needs none). Relaunch if the window is
closed (the bg launcher "completes" immediately but Chrome keeps running). Screenshots stall on font-load on
Misumi → use a CDP session `Page.captureScreenshot`. Route downloads into `cad/` with CDP
`Browser.setDownloadBehavior {behavior:allow, downloadPath: <abs cad/>}`.

## Misumi: configuring a part + getting its CAD
- Reach a CONFIGURED part directly by URL: `…/vona2/detail/<detailCode>/?HissuCode=<PartNumber>` (e.g.
  `?HissuCode=TBCN2-6`) — far more reliable than driving the spec-table checkboxes.
- To FIND the part: search `/vona2/result/?Keyword=<series or descr>`, apply the top "belt type" filter +
  left-panel "Belt Series" (e.g. 2GT) checkboxes (`get_by_role('checkbox', name=...)`), click the product
  result to land on `/vona2/detail/<code>/`; the part number appears as you finish configuring.
- **CAD download is now HANDS-OFF (decoded 2026-06-19) — `data.browse.fetch_misumi_cad(page, "<PN>")`.**
  No clicking. The flow is 2 authenticated POSTs + 1 GET, all run as **in-page `fetch()`** (an out-of-page
  Playwright request context gets **403** on cadDownload — Akamai fingerprints it; a genuine in-page fetch on
  the signed-in tab passes). The chain (base = `us.misumi-ec.com/vona2/pc/system/api`):
    1. `POST /cadFormatList/`  `{brandCode:"MSM1", productCode:"<PN>"}` → `{formatlist:[{format:"STEP_AP203"},…]}`
    2. `POST /cadDownload/`  `{brandCode:"MSM1", productCode:"<PN>", formatType:"STEP_AP203", userId:""}`
       → blocks ~5 s while it builds, then `{status:"1", outPutPath:"https://rd-jp-caddata.misumi-ec.com/…/<PN>_STEP.zip"}`
    3. `GET <outPutPath>` → the STEP zip (auth = session cookie; `userId` can be empty, server keys off session).
  Brand `MSM1` = MISUMI. Works for configured PNs too — pass the full configured part number as `productCode`.
- **How this was learned (reusable): `data/capture_misumi.py`** — an all-tabs network capture. Connect over
  CDP, attach request/response/download/popup listeners to every page AND `ctx.on("page")` for new tabs, log
  to `out/misumi_capture.log`, route downloads to `cad/`. **TWO gotchas it bakes in:** (a) the Playwright
  *sync* API never dispatches `page.on` callbacks inside a bare `time.sleep` loop — you must call a Playwright
  API each tick (`page.wait_for_timeout`) to PUMP event delivery, else you capture nothing; (b) make sure
  you're watching the **debug Chrome on :9222**, not the user's everyday Chrome (zero events = wrong window
  or dead port — check `Get-NetTCPConnection -LocalPort 9222`; relaunch Chrome if closed).
- Unzip + convert: `zipfile` → `cascadio.step_to_glb(stp, glb)` (output metres, like all parts).
- Fallback only if the above breaks = capture-from-manual (user clicks CAD Download → 3D → STEP → Generate
  in the :9222 window; the harness saves `<PN>_STEP.zip`). CADENAS PARTcommunity / 3Dfindit API remains a
  research alternative (`webapi.partcommunity.com`; Misumi mirror `misumi.partcommunity.com`).

## McMaster note: reading the virtualized PN table
Family/listing pages render PNs in a lazy table `inner_text` can't read. JS-click the family tile (it's a
`<div>` with a click handler, no href) to load the config table, then read `inner_text`; or screenshot it
and read as the VLM. `data.browse.download_cad(ctx, page, pn, kind='step_full')` drives the widget (works
through the CDP page too).

## Driving mcmaster.com (Playwright, NO API) — see `data/browse.py`
- Headless Chromium gets full server-rendered HTML — no login/CAPTCHA. Go straight to `mcmaster.com/<PN>/`.
- Validate a part number by `page.title()`: descriptive title = real; bare "McMaster-Carr" = invalid/redirect.
- Family/listing pages render PNs in a virtualized table `inner_text` CANNOT read. To get part numbers:
  (a) **screenshot the config table and read it as the VLM** (most reliable); (b) the search box
  `input[name="SrchEntryWebPart_InpBox"]` + Enter often redirects to a faceted URL whose text has PNs;
  (c) probe a candidate PN and check `page.title()`. Don't burn calls clicking tiles.
- Facet URLs compose: `/products/<category>/<facet>~<value>/`, but filters are loose — always re-read the
  product's own "For …" fields (slot width, "for shaft diameter", "for belt width") for real fit.
- Read scalars from the spec table; read the **dimensioned 2-D drawing** (the geometry authority) from a
  screenshot or the rasterized 2-D PDF (PyMuPDF `Matrix(3,3)`), not the `.dwg`.

## CAD download widget (no sign-in)
`combobox[aria-label="Select CAD file type"]` → `role=option` → sibling `<a download>` (click its inner
button inside `page.expect_download()`). Prefer `3-D STEP no threads`; fall back to `3-D STEP`. Also grab
`2-D DWG`/`2-D PDF` for geometry. Convert STEP→glTF with cascadio (metres — see Hard Rule 3).

## Mesh ≠ datum
Meshes are centred on their geometric centre, not a datum. Record every reconciliation fact (seat offsets,
axis mapping) in `part_frame.drawing_to_cad`; never hardcode it in a benchmark or viewer. Catalog meshes are
simplified/contiguous, so a mesh boolean overlaps at *designed* engagements (press fits, seated faces) —
that's expected, and it's why mesh-overlap math is a poor gate. Judge fit by looking + spec clearances.

## Belts / flexible elements
Don't use the catalog belt mesh (it's a straight strip). GENERATE the loop from the spec, fitted to the
rotary periodic supports, export in METRES, and check it visually + numerically (loop length == teeth×pitch;
periodic profile/pitch and active width match). Model pulley mesh, belt route, belt capture, and motion coupling
as separate templates. Couplings relate existing joint coordinates; they are not joints themselves.

## Rendering to look (the important tool)
`web/index.html` is a data-driven Three.js viewer; `benchmarks/_shot_incremental.py` walks the assembly
part-by-part and screenshots each step from several angles with the new part highlighted — use it (or
extend it) as the primary verification. Meshes are metres → camera ~0.03–0.2.

## Environment (Windows)
Console is cp1252 → keep `print()` ASCII. Two Pythons → `python -m pip …` into the one that runs scripts.
Run scripts from the repo root with `PYTHONPATH=.`. `http.server` serves `.glb` fine.

---

# STATE (2026-06-25 r14) — TWO-JOINT ARM: drive-train instancing is a DRIVE-MOUNT DESIGN task, not wiring

Session goal (user-chosen): drive the **two-joint arm** toward green (Aims 1+2). `tools.verify_all` is RED on
both projects, matching r13: `rung3_assembly` = NO `_verify` payload (its builder never calls
`embed_verification`); `two_joint_arm_assembly` = all three gates FAIL. Diagnosed the arm's 5 UNACCOUNTED drive
parts (`p_motor17/23`, `p_pul18_j1/j2`, `p_pul72`) and found instancing them is **real rung-4 design**, not a
wiring fix. Two design decisions taken with the user; one new template landed; a catalog scout is mid-flight.

## ★ HEADLINE FINDING — the arm's motor-mounting subsystem is ENTIRELY UNMODELED ★
The 5 drive parts are placed by eye via `extra_fixed` (a viewer/DOF convenience) and joined only by belt
**couplings** (empty `load_paths`), so they are UNACCOUNTED — a belt can never be the sole load-bearing edge.
There is **nothing to instance them onto**: no motor-mount carrier exists for either joint.
- **J1 NEMA23** (`iCL57-23`): has 4 `mount_through` clearance holes (47.14 mm sq, M5, pilot Ø38.1) but the
  base plate has NO motor pattern (only the 8-bolt bearing ring + 4 ground holes). The motor axis sits at
  R≈95 mm — **beyond the Ø180 base edge** — so it must CANTILEVER on a bracket, not bolt flat.
- **J2 NEMA17** (`iCL42-06`): mounts to `LINK_1.nema17_seat` + `nema17_pattern` (= 4 `slot_through` M3
  clearances) — that pair IS matched and instanceable via `screw_into_threaded_receiver` ×4 M3. BUT the
  20 mm `p_link1↔p_motor17` clash is NOT a coordinate nudge: the motor seat (Z=70) is **44.5 mm** from the
  J2 belt plane (Z=25.5) and the NEMA17 shaft is only **24 mm** — it physically cannot span the gap on either
  side. The old pose hid this by burying the motor 20 mm into link1. Closing it needs the belt plane within
  shaft reach (raise the elbow belt plane / a standoff / shaft extension), i.e. real drive-mount geometry.
- **Pinions** (`p_pul18_j1/j2`): bore-on-shaft, fixed by a SET SCREW — a real fastener part (Hard Rule 6),
  not integral. The plain-bore HTPA18 catalog CAD likely lacks the radial tapped hole, so a set-screw pulley
  variant / radial tap + a generated grub-screw part must be authored before the pinions can close.
So "instance the 5 drive parts" = **design the drive-mount subsystem for BOTH joints** (brackets/standoffs +
a belt plane within shaft reach + pinion set-screw), then instance + swept-check. The NEMA23 bracket scout is
the first concrete piece.

## Decisions taken with the user this round
1. **72T output pulley → J1 hub** (`LOOK` done, `out`-scratch only): the 72T (`HTPA72…KFC85`, bore Ø50, PCD85
   4-bolt keyless flange) hangs below the base bolted to NOTHING — its PCD85 matches neither the inner-ring
   8×PCD65 nor the hub patterns. In rung3 a `ROTARY_ADAPTER` bridged this; here it's absent. **Decision: revise
   `J1_OUTPUT_HUB` → REV_B** with a Ø50 pilot boss + PCD85 (R42.5) 4-tap underside so the pulley bolts up into
   the rotating stack (hub+pulley clamped to the inner ring). One custom part revised, no new adapter.
2. **J2 motor packaging**: unify on the **"motor carried below the plate, shaft up to a belt plane near the
   plate"** idiom (J1's intended layout), re-package the J2 motor accordingly, then **swept-check the motor
   envelope vs link2's swing BEFORE finalizing** (Hard Rule 1 ★ — a hanging motor can clash with link2).
3. **NEMA23 mount**: add a REAL bracket (catalog-first), not a base revision.

## Built / in-flight this round
- **NEW template `fixed_hub_on_journal`** (`ontology/templates.py`): bore-on-shaft turning WITH the shaft
  (`result=fixed`), closure = a REAL `set_screw` fastener participant (radial, `is_fastener`), checks
  `radial_fit`+`axial_overlap`, load-path edge hub→journal. Registers + binds (smoke-tested). Pinions will
  read PROVISIONAL/UNHELD until a real set-screw part + radial tap exist — the truthful state.
- **NEMA23 bracket scout** (`part-evidence-scout`, background) — FOUND two real Misumi mounts, CAD confirmed
  buildable via `cadFormatList`: **`MSAA-23`** (MSA Motor Mount A NEMA23, detail 110302630360) and **`MSAB-23`**
  (B, detail 110302630720). Breadcrumbs: `candidate_evidence/nema23-bracket/MISUMI/MSA_Motor_Mount_{A,B}_NEMA23/`
  (manifest.json + cad/cad_availability.json are gold; the saved `drawing_*.png` are the MISUMI LOGO and
  `spec_tables.json` is empty — the configurable family page exposes no DOM drawing/specs). REDIRECTED it to
  abandon the scrape and finish: `fetch_cad` both STEPs, measure the NEMA23 face + base-side holes from the
  mesh, write `report.json` (A vs B for cantilevering). Awaiting completion. **Do not run a second CDP session
  while it's live** (one warm Akamai session).

## Open tasks (this session's tracker)
1. [done] 72T/hub design-intent LOOK → REV_B decision. 2. [done] `fixed_hub_on_journal` template.
3. [reframed, open] Drive-mount design BOTH joints (not "instance + nudge"): J1 bracket (from scout) +
   motor23/pinion/set-screw; J2 re-package (belt plane within shaft reach) + motor17 4×M3 + pinion; swept
   checks. 4. [in-flight] NEMA23 bracket scout (download+measure pending). 5. [open] 72T→hub REV_B CAD+def +
   Aim 2 `cad_fidelity` (phantom/oversize: base `ground_through`×4, HTPA72 mount+bore, LINK_1 slots,
   J2_CUSTOM_PULLEY `link2_thread`) — pure local mesh-vs-def work, no session needed.
6. Still pending from r13: rung3 builder needs `embed_verification`; residual J1-outer-screw↔p_pul72 ~7 mm
   clash; head-seat bearing-face rollout.

---

# STATE (2026-06-25 r13) — GLOBAL VERIFICATION ENFORCEMENT + interactive viewer (DOF slider, bearing split, select/wireframe) + head-seat ontology

Session focus shifted from rung-building to (a) making validation **un-bypassable across every
assembly** and (b) interactive inspection. Driven by the user catching real defects BY LOOKING that
the gates were not even running on. The two-joint arm (`projects/two_joint_arm_assembly`) was the test
bed and is now (correctly) RED on all three gates — it had been "green" only because checks weren't running.

## ★ GLOBAL ENFORCEMENT — every assembly runs EVERY gate, no benchmark can bypass (the headline) ★
Root cause found: benchmarks hand-rolled which gates they ran. The arm called ONLY `LP.evaluate`
(load_path) and NEVER ran interference or cad_fidelity, so a motor mesh penetrating link1 by 20 mm +
phantom CAD holes shipped unseen; and parts with ZERO structural instances (the drive motors/pinions/
72T pulley) were invisible to load_path entirely (the graph is built only from load-bearing edges, so a
part in no instance is neither held nor flagged — just absent). See [[global-verification-enforcement]].
- **`assembly/verify_canonical.py`** — every assembly JSON now carries a self-contained `_verify`
  payload (`embed_verification(asm, lib, instances, ground, placements, non_structural)` = lib(ref->
  part_number), instances([{template,bindings}]), ground, declared couplings, structural placements).
  `verify_canonical(path)` rebuilds lib (`PartDefinition.from_json`) + instances (`TEMPLATES[id].bind`)
  and runs the FULL set, **DERIVING** the interference predicates: `designed(a,b)` = same RIGID body
  (union-find over FIXED-template load_path edges, bearing halves `_inner/_outer` normalized to base)
  OR share an instance OR same part — overlaps ACROSS a joint or between unattached parts are real;
  `rotating(ref)` = ref in any `_dofs` moving set.
- **`tools/verify_all.py`** — discovers every `projects/*/project.json -> canonical_assembly`, runs
  verify_canonical, **EXITS NONZERO if any gate FAILs OR any artifact lacks `_verify`** (an
  unverifiable assembly IS a failure). Wire into CI. `python -m tools.verify_all`.
- **`assembly/verify.py verify_assembly`**: (a) **accounts for EVERY placed part** — `load_path` takes
  `placed=`/`structural_refs=`; a placed ref in no structural instance (and not a declared coupling) is
  **UNACCOUNTED -> FAIL**, never silently skipped (`ontology/load_path.py` BodyHold.accounted +
  `.unaccounted`); (b) every SKIP now prints a loud `!! SKIPPED -- missing X`.
- **RULE for all future builders:** call `embed_verification(...)` before writing the canonical JSON and
  pass `python -m tools.verify_all`. NEVER call a single gate ad-hoc and call it verified.

## Findings the enforcement surfaced (the arm is correctly RED — real defects, not gate bugs)
- `interference STATIC p_link1 <-> p_motor17: 20.00 mm` — the J2 motor body penetrates link1 (user caught
  it by looking; the arm never ran the interference gate).
- `load_path UNACCOUNTED: p_motor17, p_motor23, p_pul18_j1, p_pul18_j2, p_pul72` — the 5 drive parts have
  NO structural instance; their only modeled link was the belt (a coupling, empty load_paths). A belt can
  never be the sole load-bearing edge. Their defs HAVE the mount ports (motor `front_face`+`mount_thread`x4,
  pulley `mount_hole`x4, LINK_1 `nema17_seat`) -> the fix is real instancing, not faking. The `extra_fixed`
  pins for these were a VIEWER/DOF convenience masking the gap.
- `cad_fidelity FAIL` — phantom/oversize void ports in 4 defs (HTPA72 mount_holes, LINK_1 slots, base
  ground_through, J2_CUSTOM_PULLEY link2_threads): declared holes not physically in the mesh.
- `rung3_assembly: NO _verify PAYLOAD => FAIL` — its builder still needs the `embed_verification` call.

## HEAD-SEAT screw ontology (NEW predicate — wrong-length screws now catchable)
User insight: a screw fasten should enforce the **cap-underside plane seats flush on the clamped face**,
which pins the screw's AXIAL position so a wrong-length screw (cap proud / buried 5 mm in the hole) fails.
- **`ontology/ports_match.py head_seat`** — reuses the flush-seating math (`bounded_area_overlap`) between
  the screw's `head_seat` port (cap underside, already authored on the ISO4762 defs) and the clamped face;
  a gap > 0.5 mm is a **hard FAIL** with the exact offset. Proven: flush PASS, +/-5 mm FAIL, 0.3 mm PASS.
- Added an **OPTIONAL `bearing` participant** to `screw_into_threaded_receiver` (+ `Participant.optional` +
  `bind()`/`evaluate()` skip-when-unbound) so existing screw instances everywhere keep working; binding the
  clamped face turns enforcement on. `head_seat` is now a load_path via-check (mis-seated head -> UNHELD;
  provisional until a bearing is bound). Combined with `thread_engagement` (thread must REACH the tap), a
  wrong-length screw cannot satisfy both. **Rollout pending:** author + bind a bearing face per screw group.

## Interactive viewer (`viewer/incr.html`) — kinematics + inspection
- **DOF slider** (like the Explode slider): `assembly/dof_extract.py::extract_dofs(instances, lib,
  placements, ground, extra_fixed=)` recognizes revolute/slider DOFs from the joint graph by SPLITTING each
  joint-bearing into `ref#inner`/`ref#outer` virtual nodes, building the rigid graph from non-joint
  load_paths, and cutting ONE joint at a time -> the non-ground component is that joint's moving set
  (nested for serial chains). Emits `_dofs` [{id,type,axis,center,moving,range}] into the assembly JSON.
  Viewer reads `_dofs`, adds a slider per joint under a "Joints" folder, composes nested joints by
  pre-multiplying per-DOF generators (proximal-first). URL param `&dof=J1:50,J2:-70` sets poses for renders.
- **Bearing split** (`tools/split_bearing.py`) — a roller bearing is one fused glb but many connected
  components that partition by radius; bins them to `<PN>_inner.glb`/`_outer.glb` (RU85 r-split 43.75, RU66
  32.5). So the inner ring + its chain rotate while the outer ring stays — visual kinematic validation +
  the "split the bearing" sanity the user wanted. (Bearings are modeled as ONE unit; the inner/outer
  distinction otherwise lives only in ring-segregated PORTS + the `crossed_roller_revolute` self-loop.)
- **Belt-attachment fix** — a belt loop rides the FRAME both its pulleys share (`extra_fixed` pin: J1 belt
  -> base/static, J2 belt -> link1); it was being left behind during DOF manipulation.
- **Right-click** a part toggles wireframe on just that part; **left-click** single-selects (pastel pink +
  name in a bottom-right BOM-style panel; click empty to deselect). URL param `&select=ref1,ref2` for renders.

## REMAINING (the enforcement made the backlog explicit + tracked)
1. Instance the 5 drive parts on their real mount ports (clears UNACCOUNTED + most interference + lets
   motor17 be placed OUT of link1, fixing the 20 mm clash). 2. Residual real clashes (J1 outer screws <->
   p_pul72 ~7 mm). 3. Fix the phantom CAD holes (cad_fidelity). 4. Give rung3's builder `embed_verification`.
   5. head-seat rollout: bearing-face ports + bindings per screw group. 6. (deferred, see
   [[recursive-validation-parallel-scheduler-plan]]) recursive sub-assembly verify + parallel scheduler;
   kinematic transmission-RATIO solver (the 4:1 is asserted, not verified).

---

# STATE (2026-06-24 r12) — RUNG 3: rotating output REDESIGNED to be ASSEMBLABLE + fastener/DFM ontology hardened

Carries r11 (mechanism complete; #8 swept-interference fix). This session fixed real DESIGN + ONTOLOGY defects
the user caught by LOOKING (the gate was passing physically-wrong assemblies):

**Rotating output is now a 3-part ASSEMBLABLE stack** (was a one-piece "drum" that TRAPPED the pulley — a closed
Oe50 bore can't slide onto a stem capped at both ends by Oe180 discs; the user caught it, not the gate):
`ROTARY_ADAPTER_RU85_S5M_REV_A` (lower adapter) -> 72T pulley on its Oe50 pilot -> **BOLT-ON CAP**
`ROTARY_CAP_RU85_REV_A` (3rd licensed custom part) -> tabletop on the cap.
- Cap attaches at **PCD85 (R42.5, INSIDE the belt)** via **4x M5x35 SPANNING the pulley** (cap->pulley->adapter),
  heads recessed in a cap counterbore so the tabletop seats flat; cap fans to +-55 (ABOVE the belt) for the
  tabletop 4x M6. Payload load: tabletop->cap->bolts->adapter->inner ring (NOT through the pulley); #8 stays solved
  (cap above belt, attach inside belt); build order has no traps (each part added from above).
- Cap is **Oe180** (was Oe160 -> the +-55 taps ran OFF the R80 edge; user caught it; now 12 mm edge margin).
- Canonical `benchmarks/rung3_assembly.py` -> `out/rung3_assembly.json`: **53 parts, 40 fasteners, gate ALL HELD**.

**Ontology hardened (the gate was LYING three ways; all now caught as numbers):**
1. **FASTENER LENGTH/ENGAGEMENT** — `thread_engagement` (ontology/ports_match.py): the screw's threaded span must
   REACH + ENGAGE the receiver tap (>= ~0.8xD) at the placed poses, with a recommended length; wired into
   `screw_into_threaded_receiver`. (Caught the cap bolts ending 16 mm short, INSIDE the pulley.)
2. **RECEIVER-SCOPED fastener counting** (ontology/load_path.py): a joint's closure counts only fasteners
   threading into its RECEIVER side AND that actually engage. (Was miscounting the tabletop->cap screws toward
   the cap->adapter join, so the cap read 'fastened' with zero real bolts into the adapter.)
3. **THROUGH-STACK bolted joints** — `coaxial_pattern_correspondence` + `through_bolted_plate` template: patterns
   joined ALONG the bolt axis across a spacer (cap bolted to adapter through the pulley) match in the plane
   perpendicular to the axis (the axial offset = clamped-stack thickness).
4. **PART-INTRINSIC DFM gate** — `ontology/manufacturability.py::edge_distance`: hole-to-edge material (>= ~0.75xD,
   D capped at ~M12) per part, independent of any assembly. Catches the Oe160 cap; all 4 custom parts now PASS.

**Schematic renderer (pipeline step 1, NEW)** — `schematics/` (primitives.py + rotary_stage.py): a parametric
matplotlib CROSS-SECTION/CUTAWAY from ONE params dict that shows the INTERNAL bolts a solid render / the Three.js
viewer HIDE (e.g. the cap->adapter M5x35 bolts buried through the pulley). `out/rung3_cutaway.png`. **TODO:**
mplot3d ISOMETRIC + TOP-DOWN from the same params (the rest of #11).

**AGENT_INSTRUCTIONS.md Hard Rule 6 extended this session:** custom/generated parts carry FULL attachment ontology (holes in
CAD *and* def, no blank/stub); assemblies need a feasible build SEQUENCE / insertion route (no trapped parts);
run the DFM edge-distance + fastener-length gates. See [[fasteners-must-be-instantiated]].

REMAINING: real branded NEMA23 + adjustable mount; place the bearing/adapter/pulley/cap fastener BODIES in the
render; mplot3d iso/top schematic; formal revision-gate sign-off (incl. the REV-history of the drum->cap change).

# STATE (2026-06-24 r11) — RUNG 3 (RU85 belt-driven rotary stage): MECHANISM COMPLETE + LOOKED, ~80%

**Toolchain:** CadQuery + OCP installed (real B-rep STEP); pipeline CadQuery→STEP(mm)→cascadio→glTF(metres) proven.
**Custom parts (the licensed exception, both REAL not boxes):** `ROTARY_BASE_RU85_REV_A` + `ROTARY_ADAPTER_RU85_S5M_REV_A`
— drawings in `drawings/`, built by `build_rotary_custom.py`, v2 defs by `author_custom_v2.py`, every PCD/clocking/boss/
relief/pilot/pass-through section-verified + rendered.
**Catalog parts (all real CAD):** `RU85UUC0` THK bearing (manual CADENAS dl — Misumi THK-passthrough 504s; reconciled in
X-native frame by `author_ru85_v2.py`); `HTPA72S5M150-A-H50-KFC85-K5.5` 72T + `HTPA18S5M150-A-H6.35` 18T S5M pulleys;
`A6061FQM-200-200-10` tabletop; `6575N203` 40mm frame (from rung2). **Standard-generated (NMSA/ISO, like the ISO4762
screws):** `SCB6-30` standoff (real series, validated+fetched), `TNUT-M6-8mm` (gen), `NEMA23-MOTOR` (standard-frame stub).
**Belt:** generated S5M loop, 87T/435mm, 4:1 (72/18).
**Ontology added:** `annular_clearance` (race-segregation) predicate + `bearing_ring_mount`/`pilot_located_bolted_hub`/
`crossed_roller_revolute` templates (ontology/ports_match.py, templates.py).
**Assembly + verification (benchmarks/rung3_*.py):** core stack (rung3_rotary) → +belt drive (rung3_full) → +standoffs/
tabletop (rung3_complete) → **#8 FIX** (rung3_redesign) → +frame (rung3_machine) → +motor (rung3_motorized); sections
(rung3_section). LOOKED at every stage. Verifications #1-4,#6,#7,#9 PASS; #10 load-path/1-DOF confirmed.
**★ #8 — REAL DESIGN FINDING (caught analytically, NOT by static look):** the rotating tabletop standoffs at R≈78 swept
THROUGH the fixed belt run. A static render showed nothing (collide only at a rotation the assembled pose doesn't show);
caught by distrusting a false-green discrete check + a continuous swept check. ROOT CAUSE: for a 360° rotary output with a
top-side OFFSET belt, ANY rotating support spanning the belt Z-band must be at R<59.5 (hits pulley) or 59.5..109 (hits belt
run) — R>109 is outside the 200mm tabletop. **REV_B fix (verified):** tabletop carried on the pulley hub, entirely above
the belt plane → nothing rotates into the belt run. See [[swept-interference-static-look-blindspot]].
**Discovery pipeline proven (Google-first):** `WebSearch site:misumi-ec.com → seriesCode → validate_pns (cadFormatList,
data/misumi_validate.py) → fetch_cad → MEASURE`. Got the tabletop + standoff this way. WebFetch is Akamai-403 (use the index,
not the live page); content/CAD via the warm CDP session. Fixed two `misumi_fetch` bugs (uncalled-arrow {}; double body read).
See AGENT_INSTRUCTIONS.md §4b/§4c + [[misumi-cad-pipeline-and-discovery]].
**REMAINING ~20% (catalog-fetch tail + formalities, NOT novel work):** real NEMA23 motor + adjustable mount (Oriental Motor
BRANDED = non-MSM1 flaky pipeline → manual fetch; a standard-frame stub stands in for the LOOK); place the 8 frame-anchor
M6 T-nuts/screws + bearing/adapter/pulley screws as bodies; the formal revision-gate sign-off (incl. REV_B doc of the #8 fix
in the adapter drawing). Renders: out/rung3_{rotary,full,complete,redesign,machine,motorized,hero,section}_*.png.

# STATE (2026-06-21 r10) — Legacy SL-TBLG clamp replaced with configurable FPT Adapter Plate and TBCR Inline Clamp Jaw combo. The 80mm Z-offset on the idlers was eliminated by widening the belt loop to 600mm, allowing all L-brackets and belt elements to sit perfectly inline (Z=0.0) without colliding with the rail. **REMAINING to close rung 2:** While physical alignment is verified and correct, the positions of the rail, slider block, and T-slot brackets are still manually seeded in `rung2_v2.py`. **RUNG 2 IS PAUSED** pending an update to `pose_solve.py` to implement a `_solve_tslot` function. This will allow the attachment logic to natively solve 1-DOF continuous slider/T-slot joints via an `along_mm` parameter, eliminating the hardcoded coordinate offsets.

> **★ CURRENT STATUS (read THIS; the dated round-logs below are chronological history and contradict each other
> as the round evolved — trust this block + the STATE header over older bullets) ★**
> - **RUNG 2 IS PARTIALLY COMPLETE / PAUSED.** The pipeline runs and the assembly is physically and geometrically inline, but the programmatic constraint solver (`PS.solve_pose`) currently raises `NotImplementedError` for T-slot sliding joints. 
> - **DONE:** Swapped out the incompatible transverse SL-TBLG plate for the parametric **FPT Configurable Plate** and **TBCR Clamp Jaw**. Widened idler positions to `IDLER_X = -45.0, 225.0` to avoid rail-end collisions and set all mounting Z-offsets to `0.0`. Validated the assembly renders inline perfectly. Added `skills/catalog-discovery.md` guidelines for resolving mounting incompatibilities with Configurable plates.
> - **NEXT STEPS (PAUSED):** Upgrade `ontology/pose_solve.py` with `_solve_tslot` to enable mathematical solving of `tslot_captured_mount` instances. Remove all manual dictionary coordinate seeding (`p_blk`, `p_brk1`, `p_brk2`) from `rung2_v2.py` and replace with programmatic `PS.solve_pose` logic.
> - **DONE:** v2 ontology (ports/templates/load-path/`pose_solve`); `benchmarks/rung2_v2.py` solves the moving
>   group from `enforce` + one placement source + renders; renderer vendored offline (`web/vendor/`); rail
>   migrated to v2 + block `guide_channel` → **block↔rail slider CONFIRMED**; `tslot_captured_mount` template;
>   **SL-TBLG belt clamp understood as the full SET** (mounting plate + jaw + 4 M3 screws → `library_v2/SL-TBLG_*`,
>   `cad/SL-TBLG_*`); **catalog access RESTORED** (Misumi `fetch_cad` warm; McMaster via warm-tab trusted-click)
>   and the **ROBUST CATALOG-FETCH PIPELINE documented** in REFERENCE §0–§6 + memories; **shoulder screw
>   `96654A131` acquired** (`cad/96654A131.{step,glb}`, 5/16/M4).
> - **r9 PART DONE / PART CORRECTED (2026-06-20):**
>   - `96654A131` (16 mm shoulder) AUTHORED in `library_v2/96654A131.json` + swapped into `rung2_v2.py` for both
>     idler axles. It is the right axle for the idler RACE: shoulder Ø5 carries the Ø5 bore, `axial_overlap` PASS.
>     The idler bore was corrected to the MEASURED recessed race (Ø5 race local x=3..12 ≈ 9 mm, RECESSED ~3 mm
>     inside each Ø22 flange, opening Ø~10); added `race_face_near/far` ports. LOOKED `out/idler_axle_iso.png`.
>   - **BRACKET AUDIT (user-directed, the important correction):** vs the MISUMI drawing (`out/mis_falbs_dwg.png`)
>     + Hole Type Selection Chart (`out/falbs_cfg2.png`): N/NA=Bolt(clearance,counterbored), M/MA=Tapped,
>     D/DA=Through. PN suffix **`N3` = N-type, M3** → the axle hole is an **M3 CLEARANCE** hole (CAD Ø3.49
>     constant thru 3.2 mm, counterbore simplified out), NOT the "M4 tap" the JSON claimed. **So the 96654A131
>     M4 thread / Ø5 shoulder CANNOT anchor to this bracket — idler→bracket is CONTRADICTED.** Foot pattern is
>     UNKNOWN (drawing spec-2 = 2 centred holes spaced S; CAD shows ONE clean Ø3.49 hole at (5,0,10) + an
>     edge-clipped void with no wall). `FALBS-H40-bracket.json` CORRECTED (axle_hole=M3 clearance; foot_hole_1
>     only; status `blocked`; full reconciliation table in the json + the r9 round log). Gate prints BLOCKED for
>     the idler chain; no crash.
> - **DECISION NEEDED (design):** RECONFIGURE the FALBS bracket — hole① N3→**M (TAPPED) M4** so the shoulder
>   screw threads in; foot②→**NA clearance** sized to a real T-nut (prefer M5). Then refetch its CAD. (A cleaner
>   bracket = M4 tapped axle + M5 foot clearance, per user.)
> - **REMAINING (after the reconfigured bracket):** (1) idler shims — ID 5 mm, OD ~8 mm (< flange opening Ø10),
>   **~3.5 mm each** (16 = shim + 9 race + shim) so the clamp reaches the RECESSED race and the pulley SPINS.
>   (2) a T-slot nut PROVEN from ONE product record for `40 mm rail` AND `8 mm slot` AND the chosen foot thread —
>   do NOT combine category facets (McMaster lists M3..M8 and 40 mm as SEPARATE facets; that does not prove a
>   single SKU satisfies both). (3) rail mount-hole callouts (clean SSEB20 re-pull). Then wire block→rail /
>   rail→ext / bracket→ext, re-run gate, LOOK.
> - **PROCESS LESSON (r9):** do NOT infer "tapped"/thread size from a CAD hole diameter, and do NOT infer a
>   compatible part by combining category-wide facets. Recover hole semantics from the manufacturer drawing/spec;
>   prove a fastener's fit from one product record. Catalog session WARM (McMaster healthy) via `data/mcmaster_fetch.py`.

> **Historical-state note:** the state log below records v1 work and mistakes. The normative v2 ontology and
> migration plan above supersede older ontology proposals in this log. Do not copy old flat roles, abstract
> world-axis mates, or monolithic interfaces into new code merely because they appear below.


## ★ THIS ROUND (2026-06-20 r8) — v2 rung-2 pipeline BUILT + LOOKED; defects diagnosed as numbers; renderer fixed ★
Carried r8 win (enforce→pose bridge) already logged above. This round took rung 2 onto v2 end-to-end and LOOKED.
- **Renderer fixed + made offline (durable).** The headless browser's egress is sandboxed, so the viewer's
  jsdelivr `three.js` importmap hung `_shot.py`/`_attach_check`. VENDORED three 0.160 locally to `web/vendor/`
  (three.module.js + addons GLTFLoader/OrbitControls/BufferGeometryUtils); `web/incr.html` + `web/index.html`
  importmaps now point to `/web/vendor/`. All LOOKing works again with no network.
- **`benchmarks/rung2_v2.py`** — first v2 end-to-end rung 2. SOLVES the moving group from template `enforce`
  via `ontology.pose_solve`: plate fastened onto the block (bounded_bolt_pattern_seat, pattern RMS 0.000, flush
  1600 mm2) and both idlers seated revolute on their shoulder-screw axles. Generates the S3M closed loop. ONE
  placement source `out/rung2_v2_placements.json` feeds gate + viewer. Rendered `out/r2v2_{iso,x,z}.png`.
- **I LOOKED (iso + cross-section). The two real defects now show as NUMBERS + pictures:**
  1. **Idler retention BROKEN.** The 90263A239 shoulder is 10 mm (world Z −5..+5) but the idler is 15 mm
     (Z −7.5..+7.5): `axial_overlap = UNKNOWN (insert spans only 10 of 15 mm)`. The cross-section shows the
     shoulder floating mid-idler — it neither reaches the bracket face (~Z−10) nor lets the head retain the far
     face (Z+7.5). The idler is NOT clamped. -> need a longer shoulder screw.
  2. **Belt capture is FAKE.** The plate's toothed grip end has 4 belt-clamp holes (X{5,20}×Z{±7.5}) for an
     OPPOSING JAW that is not in the BOM; the belt just floats over the grip. -> need a cover/jaw.
  (Plate↔block seat is GOOD — flush, pattern coincident.)
- **Design decided (user, this round): CLOSED loop + SANDWICH clamp** — keep the closed S3M loop; the carriage
  traps the lower run between the SL-TBLG toothed base and a hunted cover jaw (compression clamp).
- **SHOPPING LIST for the next hunt (precise specs):**
  (a) **Longer shoulder screw** — 5 mm Ø shoulder, M4×0.7 thread, shoulder length ~16–20 mm (so it spans the
      15 mm idler bracket→idler and the head retains the far face). McMaster family `90263A2xx` (siblings of the
      10 mm `90263A239`) or a Misumi Ø5 hex-socket shoulder screw.
  (b) **Belt-clamp cover/jaw** — bolts to the plate's 4 belt-clamp holes `X{5,20}×Z{±7.5}` (15×15 pattern;
      MEASURE the clamp-hole Ø/thread from `cad/SL-TBLGS3M100-...-25-4.glb` first). A Misumi SL-TBLG companion
      clamp, or a small flat clamp plate with the matching pattern.
- **Catalog access THIS session — DON'T REPEAT MY MISTAKE:** The hunt mechanics DO work — with **screenshots +
  coordinate-clicks** (NOT DOM scraping: Misumi's `/vona2/selector/` cards are shadow-DOM/images with no anchors,
  and `Runtime.evaluate` WEDGES on the heavy React+Drift pages) I navigated selector -> "Hex Socket Shoulder
  Screws" configurator (standard-dim table: Shoulder Dia / Length / Thread). BUT I then KILLED+RELAUNCHED Chrome
  to recover a wedged tab, which (a) backgrounded the window so `Page.captureScreenshot` stalls (Windows blocks
  foregrounding from a bg process; minimize→restore via PowerShell foregrounds it ONCE), and (b) deep-link
  launching tripped **Akamai "Access Denied"**, then the whole instance got flagged **site-wide** (even the
  homepage 403s) — which ALSO blocks `fetch_misumi_cad` (same session). **Lesson (protocol already says it):
  drive the ALREADY-WARM tab, never relaunch; reach parts via classic `/vona2/detail/<series>/` not the selector
  SPA; if a tab wedges, open a NEW tab, don't kill Chrome.** Recovery now = let Akamai cool off / re-warm by
  REAL human browsing in that window. McMaster headless was also Akamai-walled (bare `McMaster-Carr` title).
- **CATALOG ACCESS RESTORED (2026-06-20, user re-warmed session).** Launching cdp-chrome to the Misumi HOMEPAGE
  (not a deep link) cleared the Akamai flag; `cadFormatList` returns 200 (session WARM, login cached) -> Misumi
  `fetch_cad` works. McMaster works from the SAME warm browser (different Akamai property): see
  `[[mcmaster-cdp-download]]` -- fresh ACTIVE tab (`Target.createTarget`+`activateTarget`; CAD widget lazy-renders
  only on the active tab) + a TRUSTED `Input.dispatchMouseEvent` click on the `a[download]` STEP link (synthetic
  `.click()` and in-page `fetch` both fail) -> STEP to `~/Downloads`. **Acquired Part B screw `96654A131`**
  (5 mm shoulder / 16 mm / M4, 18-8 SS threadlock) -> `cad/96654A131.{step,glb}` (9x9x25 = Oe9 head + 16 shoulder
  + thread). **REJECTED `5537T161`** (read its title: it's for a 20 mm rail, NOT our 40 mm 6575N203). Still
  needed: 2 precision shims (5 mm ID, ~2.5 + ~3.5 mm for the recessed 10 mm race), the RIGHT 40 mm/8 mm-slot
  T-nut, rail mount-hole callouts -> then model + close the gate.
- **Catalog-access infra built (judicious, NOT the full provider framework):** `data/misumi_fetch.py::fetch_cad(pn)`
  reuses the WARM CDP tab (never launches), drives the STRUCTURED in-page `cadFormatList`/`cadDownload`, and has a
  CIRCUIT BREAKER (`SessionBlocked` on 403/Access-Denied -> STOP, don't loop; bounded polling only for
  CAD-still-building). Breaker logic unit-checked. Use this instead of ad-hoc fetches.
- **Provider assessment (probed 2026-06-20):** PARTcommunity (`misumi.partcommunity.com`) + 3Dfindit are NOT
  Akamai-blocked (plain-HTTP reachable, server-rendered CADENAS JSF, MISUMI catalog at `/3d-cad-models/misumi`)
  — a real storefront bypass, BUT CAD download needs a CADENAS login + stateful JSF, and `webapi.partcommunity.com`
  is token-gated (401) — not worth fully cracking now. McMaster (different Akamai property, unaffected by the
  Misumi block; guest CAD, no login) is the better source for the GENERIC shoulder screw. Net plan: shoulder
  screw -> McMaster (healthy Chrome); belt-clamp cover -> Misumi storefront once cooled off, via `fetch_cad`.
- **Renderer offline fix:** vendored three 0.160 to `web/vendor/`; `incr.html`/`index.html` importmaps repointed.
- **Full v2 load-path gate run on the SOLVED poses** (`benchmarks/_rung2_v2_gate.py`): every body UNHELD at the
  real poses — the gate (correctly) won't close the chains because the bracket feet were placed at FIXED offsets,
  not SOLVED onto the extrusion, AND a FALBS-on-T-slot mount is a swept_profile + continuous placement domain,
  NOT a `bounded_bolt_pattern_seat`; the carriage has no path because the rail isn't v2 yet. So the rung-2
  rebuild needs MORE than the 2 hunted parts. Progress THIS round (all unblocked, done):
    - `library_v2/SSEB20-220_rail.json` migrated (measured 220x11x20, guide envelope; mount holes partial/unknown,
      not invented); added `guide_channel` swept_profile receiver to the block. BLOCK->RAIL **slider** now CONFIRMED
      (`profile_carriage_on_guide`: profile_containment PASS, 30 mm captured).
    - Added the **`tslot_captured_mount`** template (swept_profile nut capture in the slot's continuous domain;
      clamp screw is a separate `screw_into_threaded_receiver` instance). Registers/serializes/binds, rejects free
      endpoints. The extrusion already exposes `tslot_top` (swept_profile receiver, continuous domain along its slot).
  STILL catalog-gated (the only things left to close the gate): (1) idler shoulder-screw STACK, (2) ~~belt-clamp
  cover jaw~~ **RESOLVED -- never a hunt** (the SL-TBLG STEP has 6 bodies/3 parts: mounting plate + a real toothed
  JAW + 4 M3 cap screws; I'd merged them with `force='mesh'` and wrongly annotated "jaw absent". Split + authored
  `library_v2/SL-TBLG_{clamp_jaw,cap_screw}.json`; `pitch_profile_match(jaw,plate grip)` PASS). (3) a REAL T-slot
  NUT part with CAD to bind `tslot_captured_mount` for rail->extrusion + bracket->extrusion (don't fabricate -- Hard
  Rule 2). NB on (1): MEASURED the idler's inner race = 10 mm bore RECESSED 2.5 mm inside the 15 mm flanges -> NO
  standard shoulder length clamps it cleanly (12 mm head fouls the flange, 16 mm overshoots); needs a shoulder
  screw + precision shim per the SHTF datasheet. NB on (3): bracket-foot holes measure ~Oe3.5 (M3), rail mount
  holes still UNKNOWN (split mesh lost them; needs a clean SSEB20 STEP re-pull) -> rail & bracket T-nut threads
  likely DIFFER. (1) needs the SHTF datasheet (MISUMI, 403-blocked); McMaster CAD needs the browser (plain HTTP
  returns a JS shell). All gated on human-assisted session recovery; then `data/misumi_fetch.py::fetch_cad` /
  McMaster pull them.

## ★ THIS ROUND (2026-06-20 r7) — v2 ontology foundation + template/closure layer landed ★
Mission: scope + implement the v2 attachment ontology. Rated it (complete 8/10, robust 7/10, flexible 9/10,
sound 8/10) and confirmed contradictions with current parts are MILD/additive (v1 roles map cleanly to ports;
the two consumers split — rungs 0/1 use `validate.py`, live rung-2 work bypasses it and drives `mate_solver`
directly — so v2 lands alongside v1, no flag-day). Then BUILT it, additively, all smoke-tested:
- **Value types** (`ontology/primitives.py`): `Interval, Measurement, LocalFrame, Polygon2D` [A.2].
- **`ontology/ports.py`** [A.3]: six `EngagementPort` families (cylindrical/planar/swept_profile/threaded/
  periodic/flexible_path), strict per-family validation, family-specific polarity, `PortGroup`. Rejects the
  v1 untyped params bag. `semantic_aliases` carry old role names but NEVER drive acceptance.
- **`ontology/schema_v2.py`** [A.5]: immutable `PartDefinition` (`from_json` REJECTS a baked `frame`/placement
  — kills the `1277N16 ±66 mm` leak class structurally), `PartInstance` (the only place a pose lives),
  field-level `EvidenceRecord`.
- **`ontology/ports_match.py`** [A.6/A.8]: 8 matchers returning PASS/FAIL/UNKNOWN + severity + measurements:
  `radial_fit, axial_overlap, thread_match, pitch_profile_match, active_width_overlap, bounded_area_overlap`
  (shapely), `profile_containment` (shapely), `pattern_correspondence` (permutation SEARCH, not zip). Same
  numbers `_attach_check.py` overlays, so look == engine.
- **`ontology/templates.py`** [A.7]: USER-CHOSEN typed executable registry — serializable dataclasses
  (`JointSpec/Participant/Relation/Check/ClosureRequirement/LoadPathEdge/AttachmentTemplate.to_json/
  AttachmentInstance`), NO lambdas, fixed engine dispatch. `bind()` BANS free world-axis endpoints
  ("coaxial to an abstract axle" raises). 6 templates: retained_revolute_on_journal,
  screw_into_threaded_receiver, bounded_bolt_pattern_seat, profile_carriage_on_guide, timing_belt_mesh,
  belt_capture.
- **`ontology/load_path.py`** [A.8 closure]: USER-CHOSEN three-state closure = `HELD_CONFIRMED /
  HELD_PROVISIONAL / UNHELD`. A part is HELD only via a continuous chain of instantiated, geometry-checked
  edges to ground; closure is a modeled fastener PART or modeled INTEGRAL geometry (shoulder+head,
  captured_profile, press_fit, raceway, dovetail...) — "threaded hole nearby ⇒ retention implied" is NOT a
  pass. Edge state = min(via-check geometry, instance closure); body state = max-over-paths of min edge.
  Final validation requires CONFIRMED; discovery may keep PROVISIONAL.
- **`library_v2/`**: 6 parts migrated — `SHTF20S3M100-5` (idler), `90263A239` (shoulder screw),
  `SSEB20-220_block`, `SL-TBLGS3M100-plate`, `FALBS-H40-bracket`, `6575N203-extrusion`.
- **Demos** (run with `PYTHONPATH=.`): `benchmarks/_v2_demo.py` (cyl/threaded/periodic + the shoulder-span
  bug as a NUMBER), `_v2_demo2.py` (pattern/area/profile on the REAL plate↔block joint), `_v2_loadpath_demo.py`
  (UNHELD floating idler → abstract-axle bind() rejection → PROVISIONAL → CONFIRMED, 5 scenarios).
- **v1 snapshot**: `ontology_v1_snapshot/` (no git here, so a file copy = step A.1). Log:
  `out/ontology_log/v2_migration.md`. Memory: `[[v2-ontology-foundation]]`.

**The r6 bugs are now caught structurally / as numbers** (not residual-green): (1) the abstract-axle attachment
is INEXPRESSIBLE (bind rejects non-part endpoints); (2) the floating idler is UNHELD (no path to ground);
(3) the shoulder-too-short bug surfaces as `axial_overlap=UNKNOWN` (shoulder spans 10 of the bore's 15 mm) →
idler HELD_PROVISIONAL, NOT confirmed, until the bearing inner-race width is pinned (demo scenario 5 confirms a
10 mm race → all HELD_CONFIRMED).

### Next, in order (r7 → r8)
1. ~~**Wire pose-solving from template `enforce` through `mate_solver`.**~~ **DONE 2026-06-20 r8** —
   `ontology/pose_solve.py::solve_pose(instance, solve_ref, lib, placements, *, spin_rad, along_mm)` reads the
   template `enforce` relations and DRIVES `mate_solver` to PRODUCE the moving body's `{R,t_mm}`. Two forms (the
   rung-2 moving group): `coaxial(A.axis,B.axis)`→`solve_coaxial` (free on-axis DOF); `oppose_and_seat`+bound
   bolt-pattern groups→`solve_rigid` with the 1-1 hole correspondence SEARCHED (never zipped). Unsolvable enforce
   raises (no invented placement). Proven by `benchmarks/_v2_pose_demo.py` (idler coaxial onto screw axle
   residual 0.0000 + free-spin DOF real; plate onto block residual 0.0000, 4-hole correspondence, flush 1600 mm2);
   no demo regressions. **NOTE for the rebuild:** the coaxial `along_mm` (axial seat) is a real choice — at 0 the
   bore origin sits on the screw origin and `axial_overlap` reads partial; pick `along_mm` so the bore sits ON
   the shoulder span, then LOOK.
2. **Rebuild rung 2 on v2 end-to-end**: one placement source (`out/rung2_placements.json`), solve the moving
   group from templates, run the 8 matchers + the 3-state load-path gate on the WHOLE assembly, then **RENDER
   and LOOK** in isolation (`_attach_check.py`) + context (`_shot.py`). Nothing here is trusted until LOOKED at
   (Hard Rule 1/1b) — everything so far is numeric only.
3. **Migrate remaining parts** (rail `SSEB20-220_rail`, belt as flexible_path+periodic, rung-0/1 parts) and add
   `scripts/validate_library_v2.py` [A.10] (schema, immutable frames, evidence links, drawing→CAD residuals,
   assembly-coordinate leakage) as a guardrail before more parts depend on v2.
4. Then demote the "NORMATIVE v2" framing once rung 2 is green on v2, and proceed to Rung 3 (gantry).

### v2 module cheat-sheet (for a fresh session)
- Author a part: `PartDefinition` in `library_v2/<pn>.json` (schema_version 2; ports = the 6 families; mm in
  ONE local frame; CAD metres; NO placement in the def).
- Express an attachment: pick a template in `ontology.templates.TEMPLATES`, `.bind({slot: 'p_ref.port'})`
  (or `'p_ref:group'`); never a bare world axis.
- Check fit: `AttachmentInstance.evaluate(library_v2, placements)` → per-check PASS/FAIL/UNKNOWN.
- Check held-to-ground: `ontology.load_path.evaluate(instances, library_v2, placements, ground=[refs])`.
- `library_v2` for the gate = `{ref: PartDefinition}`; `placements` = `{ref: {"R":3x3,"t_mm":[..]}}`.


## ★ THIS ROUND (2026-06-20 r6) — caught: residual-green attachments that are physically broken ★
User design-review (correct): I shipped attachments that pass residuals but are nonsense; I must look at each
attachment IN ISOLATION, ANNOTATED with the deciding dims, as I assign it. Added **Hard Rule 1b** + tool
**`benchmarks/_attach_check.py`** (projected silhouettes + dimension overlays). Diagnoses (I LOOKED):
1. **idler <-> bracket = NOT HELD.** Seated "coaxial to an abstract world axle" with NO shaft part → idler
   floats with a gap (`out/j_idler_iso.png`). Worse, the real shoulder screw `90263A239` has a **5 mm shoulder
   only 10 mm long but the idler is 15 mm wide** → too short to carry it, head collides (`out/attach_idler.png`).
   Need: a longer 5 mm-Ø shoulder screw (shoulder >= 15 mm, M4 thread) AND the real chain bracket-(thread/fixed)-
   screw-(revolute, bore-on-shoulder)-idler. "enforce_coaxial to an abstract axis" is BANNED (see refactor).
2. **belt <-> clamp = NOT CLAMPED.** Belt loop just drapes over the flat plate top (0.45 mm gap), no jaw, no
   tooth engagement (`out/j_clamp_iso.png`). "coplanar grip = clamped" was fiction.
3. **clamp <-> block = wrong mechanism.** Bolt pattern is real (RMS 0) but the plate cantilevers ~67 mm into
   space to reach a belt it doesn't grip — transmits nothing. The belt must run LOW (near the rail) so the
   clamp is compact, or the belt subsystem is redesigned.

## ★ PROPOSED ONTOLOGY REFACTOR (parsimonious — no new primitives) ★
The attachment ontology is the core asset (verify-by-construction + design-space reduction via parts' baked-in
attachment logic). Make it carry its own validity:
- **Attachments bind two REAL parts' measured features — never an abstract axis.** `enforce_coaxial`'s target
  must be a placed part's feature (the shaft/screw), not a free `AXLE` lambda. (Discipline + a guard; the
  abstract-axle path in `rung2_assemble.py` is the bug.)
- **Every part must be HELD: a load path to ground.** Reuse `assembly/mobility.py`'s joint graph as a gate —
  every part must connect to ground through real intermediary parts (idler->screw->bracket->extrusion). A part
  with only a coaxial-to-axis "joint" and no carrying part is UNHELD and must fail.
- **Interfaces carry validity PREDICATES = the annotated dims.** e.g. `shaft_mount`: bore Ø == shaft Ø AND
  shaft bearing-length >= bore width (the span check that caught the short screw); `belt_clamp`: jaw teeth mesh
  belt teeth (pitch+phase) AND two faces sandwich the belt. Same numbers the `_attach_check` overlay shows, so
  the look and the engine check the same thing. Still just point/axis/plane + coaxial/coplanar/parallel/distance.

## ★ THIS ROUND (2026-06-20 r5) — belt-clamp mate DONE + Misumi part-fetch pipeline CRACKED ★
- **Belt routing / belt-clamp mate DONE + LOOKED** (`out/r2belt_{iso,x,z}.png`): flipped the plate (FLIPPED
  hole correspondence → pose t=[100,24,0], clamp end points INTO travel) so the S3M belt's lower run lies on
  the plate clamp-end top (Y=30); belt-clamp checks coplanar/parallel/pitch all REDUNDANT-OK (0.000). It reads
  as a real belt-driven linear axis. `benchmarks/rung2_assemble.py` regenerated; `out/rung2_placements.json`.
- **Misumi part-fetch pipeline cracked (raw CDP)** — see the new "★★ FAST PART-FETCH PROTOCOL ★★" in REFERENCE
  and [[misumi-rawcdp-protocol]]. `data/rawcdp.py` (raw websocket to one page target; immune to the Drift
  iframes/workers that hang `connect_over_cdp`). Used it to fetch a real bracket end-to-end.
- **Bracket fetched but height-mismatched:** `FALBS-SP-T3.2-A80-B30-L30-N3` (Misumi Configurable L-Bracket,
  `cad/FALBS-*.glb`, 30×80×30 mm). MEASURED: its center (axle) hole is at **Y=10 from the bend, NOT centered at
  A/2** — so base-mounted it puts the axle at 10 mm, but the belt needs the axle at **~Y=40** (extrusion top 0 +
  block top 20 + plate 10 + PR 9.55). NOT placed yet. Next: get a bracket whose hole sits ~40 above its base
  (FALBS hole height looks fixed by the N3 hole-spec; try a different hole-spec/type that exposes an H param, or
  a taller-hole / pedestal bracket) — FAST now via the protocol. Idlers currently solved on bare world axles.

## ★ THIS ROUND (2026-06-20 r4) — front A DONE: 40 mm extrusion fetched + integrated ★
Fetched the wider frame via CDP Chrome (McMaster T-slotted framing → rail-height 40 mm → Single Four Slot):
**`6575N25` family → configured 1 ft = `6575N203`** ("Single Four Slot Rail, Silver, 40 mm Square"), STEP
downloaded + cascadio→`cad/6575N203.glb`, verified **40×40×304.8 mm** metres-scale. Added to
`benchmarks/rung2_assemble.py` (`R_EXT` rotates length→world X; placed t=[90,−20,0] so top face=Y=0, rail
bottom seats on it, centred under the 220 mm rail). Library entry `library/6575N203_p_ext.json` (T-slot 8×12.2).
**LOOKED** `out/r2ext_{iso,x,z}.png`: 40×40 four-slot profile is the base, rail seats centred on top, both
idlers + plate sit within the extrusion footprint, correct scale. McMaster CDP how-to (reusable): length is a
`td.spec-search--value` cell (click it → CAD combobox enables → configured PN becomes the length variant);
CAD option is `li[id^='dropdown-3-D STEP/']`, download via `a._downloadAnchor_kifon_247 > button` (no
"no threads" variant for extrusions). The page's scroll container is `.jo` (set `.scrollTop`); wheel doesn't move it.

Rungs 0 & 1 PASS and are real (don't touch). **Rung 2 is NOT done** — read this whole section before touching it.

## ★ THIS ROUND (2026-06-20) — CAD all fetched + revolute/slider engine path built ★
Two carry-in wins from 2026-06-19 still hold: **Misumi CAD is hands-off** (`fetch_misumi_cad`, no clicking)
and **the clamp↔carriage blocker is RESOLVED** (single-vendor Misumi moving group). This round executed the
CAD-pull phase and closed the engine gap:
1. **All 4 moving-group GLBs fetched, verified metres-scale, and LOOKED at** — `SSEB13-220` (guide), `SL-TBLGS3M100-
   50-80-20-30-15-3` (clamp), `SHTF20S3M100-5` (bearing idler ×2), `HTPS20S3M100-A-P6` (spare drive pulley). See
   the BOM-REPLACE table for PNs/notes.
2. **The revolute/slider ENGINE GAP is RESOLVED** — `solve_coaxial`/`enforce_coaxial_and_check` added to
   `mate_solver.py`; proven by `benchmarks/_coaxial_demo.py`. See "ENGINE GAP — RESOLVED" below.
3. **Guide CAD split** — `SSEB13-220.glb` ships rail+block in ONE file; split to `SSEB13-220_rail.glb` /
   `_block.glb` so the block is independently placeable for the slider DOF (block is 27 mm transverse —
   **overhangs the 25 mm extrusion**, so the frame profile likely needs widening in the rebuild).

## ★ WORKFLOW LESSONS (reusable — read before driving Misumi or splitting CAD) ★
- **Misumi CAD only generates for MISUMI-brand (MSM1) parts.** 3rd-party-brand listings (e.g. Mitsuboshi
  Belting `MIB1`, like pulley `P20S3M0100CAL-H-4`) consistently **504 / return empty CAD lists** on BOTH
  `fetch_misumi_cad` AND the on-page CAD Download button, while MSM1 parts succeed instantly. **Always filter
  the search to Brand = MISUMI** (left-panel "Brand" facet → URL carries `Brand=MSM1`) when you need CAD.
  Don't waste time retrying a non-MSM1 part — switch parts. (How a working S3M pulley/idler was found.)
- **`fetch_misumi_cad` on a freshly-configured/non-cached PN often needs a retry.** First call returns
  `status:"1"` with an EMPTY `outPutPath` (server still building the CAD) → `{'error':'no outPutPath'}`. Just
  retry with a ~6 s backoff (loop ~6×); it succeeds on the 1st–2nd retry. A cached PN returns the zip URL
  immediately. (Not a bug — don't "fix" the fetch code over it.)
- **Driving the Misumi configurator (when you must click it):** the spec rows are `<li role="checkbox">`
  (unnamed; `.inner_text()` gives the value like `'20'`). **Re-fetch `page.get_by_role('checkbox').all()`
  after EVERY click** — selecting a value re-renders the panel and **shifts all indices**. Use `force=True`
  (the row is wider than the hit target). Values repeat across groups (belt width `10` vs bore `10`) → match
  the FIRST occurrence for the earlier group, or disambiguate by section order. **Read the configured PN from
  the DOM, not a screenshot:** regex the PN-summary span, e.g.
  `page.evaluate(() => [...document.querySelectorAll('span,div,td,b,a')].map(e=>e.textContent).find(t=>/HTP|SHTF|SL-TBLG/.test(t)))`.
  Then hand that PN to `fetch_misumi_cad` (far easier than clicking the CAD button). Direct configured URL:
  `…/vona2/detail/<seriesCode>/?HissuCode=<PN>`.
- **Splitting a multi-body GLB** (a Misumi linear guide ships rail+block in one file): the sub-geometries are
  already registered in a common frame. `s = trimesh.load(path, force='scene'); for nd in s.graph.nodes_geometry:
  tf,gname = s.graph[nd]; g = s.geometry[gname].copy(); g.apply_transform(tf); g.export(out)`. Keeps each piece
  metres-scale and in-register so you can place them independently.

## The clamp↔carriage resolution (user-approved — replaces the old OPEN BLOCKER)
Root cause was real: the Misumi TBCN belt clamp never bolts to the McMaster miniature carriage `6709K211`
(M2 @ **10×10**). Verified from the live Misumi table, NO TBCN2 size is 10×10 (TBCN2-4=9×9 M2; TBCN2-6=
**8×11.5** M2.5 — confirms the old "8.0×11.4" measurement; TBCN2-10=8×15.5 M2.5). McMaster has no FA belt
clamps, so Misumi-clamp↔McMaster-carriage patterns never coincide.
**Fix (user chose): go single-vendor Misumi for the moving group, using the purpose-built clamp**
`SL-TBLG` ("Timing Belt Clamp Plates - Linear Guide Mounting Plate", Misumi) — belt-clamp holes one end +
4 counterbored guide-mounting holes (B×C) the other, made to bolt onto a miniature linear-guide block. Its
B×C is configurable; user ruled (Hard Rule 5) that setting B×C to a guide block's REAL fixed pattern is
legit here (manufacturer's intended adaptability + solver still checks vs the guide's measured holes), NOT
the forbidden invented-hole fudge. `SL-TBLG` supports XL/L/S3M/S5M/S8M/T5 — **not GT2** — so the belt+pulleys
switch off 2GT (→ **S3M**, 10 mm wide, to match stock S3M pulleys).
- **★ CORRECTED 2026-06-20 (measured from CAD, replaces the wrong MX13 pairing below):** the SL-TBLG-S3M
  guide-mount holes are **NOT freely B×C — their transverse spread is FIXED at ±15 (30 mm pitch)** for the
  S3M belt type; only the **longitudinal** span follows the plate's C param. So the plate fits the guide whose
  block-top transverse mount pitch is **30 = MX20** (NOT MX13's 20). **Real matched set:** guide **SSEB20-220**
  (block W=40, top 4× **M4 @ B=30 transverse × C=25 longitudinal**, holes measured at X∈{−5,20} Z∈{±15}) ↔ plate
  **`SL-TBLGS3M100-50-80-20-30-25-4`** (set plate **C=25**, screw **Z=M4**; its M4 *clearance* holes measure
  X∈{80,105} Z∈{±15} = **25×30**, coincident with the block — acceptor-fit RMS→0 honestly). LOOKED: plate
  seats flush on block (`out/fit_{iso,x}.png`). **PN field order = `SL-TBLG`+`S3M`+`100`(belt w=10)+`-A-L-B-S-C-Z`**
  (working ex.: `-50-80-20-30-25-4` = A50,L80,B20,S30,C25,Z=M4). Block W=40 ⇒ extrusion MUST widen to ≥40 mm.
- Misumi miniature guide (SSEB series) block-top mount pattern, **authoritative from the live SSEB dim-table**
  (MX size → W(block width), B transverse pitch, C longitudinal pitch, screw): MX6 W12 B8 C– M2 · MX8 W17 B12
  C8 M2 · MX10 W20 B15 C10 M3 · **MX13 W27 B20 C15 M3** · MX16 W32 B25 C20 M3 · **MX20 W40 B30 C25 M4**.
  The belt MUST run along the block longitudinal (C/X) axis. SSEB20-220 ships rail+block in one GLB (split it).
- ~~OLD WRONG pairing:~~ "MX13 ↔ SL-TBLG-S3M B=20,C=15" — the plate's transverse is fixed 30, so it never
  bolts to MX13 (transverse 20). Do not use SSEB13-220 / the old `SL-TBLGS3M100-50-80-20-30-15-3` for the mate.
- Configurator is automation-hostile (164 unnamed checkboxes; `get_by_role("checkbox", name=…)` accessible
  names DO resolve, and the "checkbox" is a wide row → use force-click). Easier: get exact configured PNs,
  then `fetch_misumi_cad`.

## The constraint engine (`assembly/mate_solver.py`) — the heart of the project now
(ENFORCE/CHECK + teeth model built 2026-06-19; the revolute/slider `solve_coaxial` path added 2026-06-20 —
see "ENGINE GAP — RESOLVED" below.)
- **ENFORCE vs CHECK**: a part's pose is SOLVED from its `enforce` constraints (a fastener pattern = rigid
  Kabsch fit `solve_rigid`); every `check` constraint is then a geometric RESIDUAL at that pose, reported
  `redundant-OK` (≈0) or `VIOLATED`. Residuals for coincident/coaxial/coplanar/parallel + scalar `pitch_match`.
- **Teeth model** (no per-tooth geometry): a toothed face = `plane` + `tooth_direction` (ridge `axis`) +
  `pitch` scalar. Mesh = coplanar(faces) + **parallel(tooth_directions)** + pitch-equal [+ phase]. The
  parallel term is what catches a 90°-rotated clamp that bare coplanar passes (symmetric 4-bolt pattern is
  4-fold ambiguous; the teeth break the tie). Pulley teeth = `pitch_circle` + belt `path` tangency + pitch-equal.
- **Acceptor side is first-class**: `threaded_hole`/`shaft_bore`/`bearing_seat`/`mounting_face` are MEASURED
  from the part and matched against the inserted side; this is how the clamp/carriage misfit gets caught.
- Demo proving it (catches the 90° bug AND the hole misfit with NO render): `benchmarks/_mate_demo.py`.
- Ontology fix logged: `out/ontology_log/rung2_clampfix.md` (belt_drive gained `coplanar`; no new primitive).

## Carried-over architecture (still valid; only the moving group changes)
A 1-DOF belt-driven linear axis. Coords: extrusion centred at origin, travel=Z, up=Y, lateral=X.
`benchmarks/rung2_assemble.py` → `out/rung2_placements.json`; renders `out/r2eng_{iso,x,z}.png`. Belt loops in
the VERTICAL plane over the rail (pulley axis = X), LOWER run flat on the block top so the clamp seats flat
(clamp toothed face coplanar with belt toothed face — the fix logged in `out/ontology_log/rung2_clampfix.md`).
2 end idlers spin on a static shoulder-screw axle held by an end bracket (bracket—fixed—screw—revolute—idler).

## BOM — KEEP (real, in `cad/`)
| ref | part | source | note |
|---|---|---|---|
| 2× shoulder screw `90263A239` | McMaster | M4, 5 mm shoulder ×10 — static idler axle (re-fit to new pulley bore) |
| 2× pulley bracket `19155A34` | McMaster | 304 SS 90° end risers (rough fit; revisit) |

EXTRUSION RESOLVED (r4): old `6575N368` (25 mm) DROPPED (too narrow). New frame = **`6575N203`** (McMaster
40×40 mm Single Four Slot T-slot, 1 ft / 304.8 mm, family `6575N25`) — in `cad/6575N203.glb`, lib
`library/6575N203_p_ext.json`, integrated + LOOKED (rail seats on top, `out/r2ext_*`).

## BOM — REPLACE this rebuild (Misumi single-vendor moving group) — ★ MOVING-GROUP FIT NOW SOLVED (2026-06-20 r2) ★
| ref | configured PN (fetched into `cad/`, glb in metres) | note |
|---|---|---|
| guide rail+block | **`SSEB20-220`** | SSEB**20** (=MX20) miniature guide, 220 mm rail; block W=40, top 4× **M4 @ B=30×C=25** (X∈{−5,20} Z∈{±15}). Split → `SSEB20-220_{rail,block}.glb`. **Replaces SSEB13-220** (wrong size — see corrected matched set) |
| belt clamp | **`SL-TBLGS3M100-50-80-20-30-25-4`** | SL-TBLG S3M w10; A50/L80/B20/S30/**C25**/**Z=M4**. M4 *clearance* holes X∈{80,105} Z∈{±15} = **25×30** → coincident with SSEB20 block (LOOKED `out/fit_*.png`). **Replaces the `…-15-3` plate** (was MX13-pitch, didn't fit) |
| 2× idler pulley | **`SHTF20S3M100-5`** | MISUMI S3M **flanged toothed idler, CENTER BEARING** (free-spinning by design), 20T, 10 mm width, 304 SS, **5 mm bore** = exact fit on M4 shoulder-screw `90263A239` (5 mm shoulder). bbox 15×22×22 mm. **USE 2× of these** for both end idlers (design has no motor → both ends are idlers) |
| spare drive pulley | `HTPS20S3M100-A-P6` | plain Shape-A 6 mm-bore S3M pulley, 20T, 10 mm. Kept in `cad/` as a spare for a FUTURE driven/motor end; NOT used in this rung (its plain bore can't free-spin on a static axle — that's why the idler above was pulled) |
| belt | generated `assembly/belt.py` | **S3M**, 2 mm→**3 mm pitch**, 10 mm wide (belt.py already parametric — pass pitch_in=3/25.4, width_in=10/25.4) |

NOTE: the original S3M pulley search top-hit `P20S3M0100CAL-H-4` is **Mitsuboshi-branded (MIB1)** and its CAD
endpoint **consistently 504s / returns empty CAD lists** — Misumi has no generatable CAD for it. Filter the
pulley search to **Brand = MISUMI (MSM1)** to get a part whose CAD actually builds (that's how `HTPS20S3M100-A-P6`
was found). General lesson: 3rd-party-brand Misumi listings may have no CAD; prefer MSM1 when CAD is required.

DROP (no longer used): rail `6709K231` + carriage `6709K211` (M2 10×10, didn't fit), idlers `3693N11` (GT2),
clamp `TBCN2-6` (GT2, didn't fit), **`SSEB13-220` guide + `SL-TBLGS3M100-50-80-20-30-15-3` plate (wrong
size — plate transverse is fixed 30=MX20, not MX13)**, extrusion `6575N368` (too narrow for the 40 mm block).
Dead/superseded — do NOT reuse: `benchmarks/rung2_belt_axis.py` (old box fiction), `cad/CUSTOM-*.glb`, wrong
parts `7769N11`/`6483K51`; OLD renders `out/rung2_final_*`, `out/incr/*`.

**Render:** `benchmarks/_shot.py <placements.json> <prefix> [new] [angles]` + `_shot_incremental.py`, via
`web/incr.html` (and interactive `web/index.html`, scene `rung2`). **GOTCHA: headless hardware GL races on
pixel readback → BLANK frames; both shooters launch chromium with `--use-gl=swiftshader --enable-unsafe-swiftshader`.**

## Next, in order
1. ~~**Get exact configured PNs** + `fetch_misumi_cad` each into `cad/`.~~ **DONE 2026-06-20** — 4 GLBs in `cad/`
   (SSEB13-220, SL-TBLGS3M100-50-80-20-30-15-3, **SHTF20S3M100-5** [bearing idler ×2], HTPS20S3M100-A-P6 [spare]),
   all verified metres-scale and LOOKED at (`out/newparts_*.png`, `out/idlerlook_*.png`): real toothed
   pulley/idler + holed clamp + holed rail, correct relative scale; idler shows its center bearing. Idler-mount
   fork RESOLVED (user: use a bearing idler → SHTF20S3M100-5, 5 mm bore fits the shoulder screw). Remaining:
   the revolute/slider engine gap — user chose **build the engine path FIRST** (see "ENGINE GAP" below).
2. ~~**Build the `coaxial`-only revolute/slider enforce path in `mate_solver.py`**.~~ **DONE 2026-06-20** —
   `solve_coaxial` + `enforce_coaxial_and_check` added; proven by `benchmarks/_coaxial_demo.py`; fasten path
   unregressed. See "ENGINE GAP — RESOLVED" below.
3. ~~**Resolve the clamp↔guide fit honestly (measured from CAD).**~~ **DONE 2026-06-20 r2** — discovered the
   SL-TBLG-S3M guide-mount transverse is FIXED 30 (≠ MX13's 20); user chose "bigger guide + wider frame";
   switched to **SSEB20-220** (block M4 @ B30×C25) + reconfigured plate **`SL-TBLGS3M100-50-80-20-30-25-4`**
   (C=25, Z=M4). Measured both: plate M4 clearance 25×30 ≡ block 25×30 → **coincident, bolts honestly**.
   LOOKED `out/fit_{iso,x}.png` (plate seats flush). Hole-measure tool: section mesh at a Y plane, cluster
   loops via `networkx` connected-components on `sec.entities`, centroid+mean-radius (needs `shapely`,
   `networkx`, `rtree` — now pip-installed). See the corrected matched-set + BOM tables above.
4. ~~**Widen the extrusion**~~ **DONE 2026-06-20 r4** — fetched + integrated `6575N203` (40×40×304.8 mm
   four-slot, family `6575N25`); rail seats on its top, LOOKED (`out/r2ext_*`). Library: `6575N203_p_ext.json`.
   Pulley brackets to the new width still TODO (folded into front B below).
5. ~~**Model the new parts' features**~~ **DONE 2026-06-20 r2** — measured from the real meshes (mesh-section
   at a Y plane) and written as canonical library entries in their OWN frames (world = parts' native frame:
   X=travel, Y=up, Z=transverse): `library/SSEB20-220_p_block.json` (top M4 tapped @ X∈{−5,20} Z∈{±15}, topY=20),
   `library/SL-TBLGS3M100_p_plate.json` (guide-side M4 clearance @ X∈{80,105} Z∈{±15}, bottom mating face Y=−4,
   belt-clamp grip @ low X), `library/SHTF20S3M100-5_p_idler.json` (bore axis along local X, PR=9.549). Measured
   values CONFIRM STATE exactly (block r=1.62 M4 tap; plate r=4.0 counterbore — both 25×30).
6. ~~**Rebuild `rung2_assemble.py`** (moving group)~~ **DONE 2026-06-20 r2** — new `benchmarks/rung2_assemble.py`
   (old TBCN/6709 box-era version replaced). Loads the 3 library parts via a `_FeatPart` adapter; ENFORCE plate
   fasten onto block's 4 M4 holes → solved pose **t=[−85,24,0], RMS 0.000 mm** (HONEST coincident fit, patterns
   coincide, coplanar check redundant-OK); idlers SEATED coaxial via `enforce_coaxial_and_check` (RMS 0.000);
   S3M belt generated (588 mm loop = 196T×3 mm, fits). Writes `out/rung2_placements.json`.
7. ~~**LOOK** (moving-group seat)~~ **DONE 2026-06-20 r2** — `benchmarks/_shot.py` → `out/r2seat_{iso,x,z}.png`
   (seat-only) + `out/r2new_*` (full). **I looked:** rail along X, block on it, **plate seats FLUSH on block top**,
   holes aligned, plate overhangs block transversely (50 vs 40 mm, expected A=50) and cantilevers its belt-clamp
   end out to low X toward the belt. Correct. **OPEN — live front B (belt routing):** the generated belt's lower
   run (Y≈26 at IDLER_Y=36, PR=9.55) does NOT yet engage the plate's belt-clamp end — IDLER_Y and the clamp-jaw
   geometry are placeholders. Need to MEASURE the plate clamp-end teeth (low-X, screw holes X∈{5,20} Z∈{±7.5})
   and route the belt so its lower run meets the grip face; then add the belt↔clamp coplanar+parallel(teeth) check.
8. **Widen+wire**: fetch the ≥40 mm extrusion (front A), re-fit rail+brackets to it, finish belt routing
   (front B), wire the full mate graph through `mate_solver` + DOF; then Rung 3 (gantry).

## ENGINE GAP — ★ RESOLVED 2026-06-20 ★ (revolute/slider now engine-solved)
Was: `mate_solver.py`'s `enforce` path only did a rigid 6-DOF Kabsch fit (`solve_rigid`) of a bolt pattern —
it could only *fasten*, with no pose-solve for `revolute`/`slider`, so pulleys were hand-placed and `J(...)`
was DOF-count metadata only. **Now added** (`assembly/mate_solver.py`): `solve_coaxial(local_axis, world_axis,
spin_rad=0, along_mm=0)` + `enforce_coaxial_and_check(part, local_axis_addr, world_axis_addr, checks, lib,
placements, joint=...)`. It aligns the part's local axis onto the target axle's world axis (4 DOF solved by
the axis) and leaves the on-axis DOF FREE — `spin_rad` for a revolute, `along_mm` for a slider — so a pulley
is genuinely *solved* coaxial to its axle, not hand-placed. `MateReport` gained a `mode` field; the check-eval
loop was refactored to `_eval_checks` (shared with the fasten path; `enforce_and_check` unchanged in behavior).
Proven NO-render by **`benchmarks/_coaxial_demo.py`**: enforce residual 0.000 mm; spin +90 deg moves an
off-axis rim point 15.6 mm while the axis stays put (free DOF is real); slide +20 mm advances exactly along
the axle; coaxial CHECK redundant-OK throughout. `benchmarks/_mate_demo.py` (fasten path) still passes — no
regression. So in the rebuild, solve each idler with `enforce_coaxial_and_check(..., joint="revolute")` onto
its shoulder-screw axle, and the slider (clamp+block along the rail) is expressible the same way if wanted.
NOTE: `assembly/mobility.py` still uses joint types for DOF counting only — that's correct and unchanged.
