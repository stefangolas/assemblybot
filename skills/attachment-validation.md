# Skill: Attachment Validation (LEAD OWNS interpretation)

The attachment ontology is the application's core asset: it both verifies a valid assembly and collapses the
design space (catalog parts have baked-in attachment logic). Each attachment must be **right**, not merely
residual-green. Workers may report isolated geometry observations; the **lead** owns all attachment
interpretation, binding, and load-path edges.

## Verify every attachment IN ISOLATION, ANNOTATED, as you assign it

The moment you assign how a part attaches, LOOK at just that mating pair in isolation (the inserted part + its
acceptor, nothing else) and annotate the render with the deciding measurements (bore Ø vs shaft Ø,
hole-pattern span, seating gap, reach/overhang, tooth pitch & engagement). Ask: are these two parts *physically
held by a real feature*, or just numerically coincident? A green residual with parts floating apart is the
canonical failure (a pulley "coaxial" to an abstract axis with no screw; a belt "coplanar" to a plate it never
touches; a clamp reaching into space to a belt it doesn't grip). Do not proceed until the isolated annotated
picture shows a real joint with a real fastener/feature carrying the load. Then repeat the look in the FULL
assembly. Tool: `benchmarks/_attach_check.py`.

## Hard rules

- Only **accepted canonical parts** may participate in final attachment instances.
- Every required hardware participant must EXIST. Missing nuts/screws/spacers cannot be bypassed (decisions/003).
- **A pose is not an attachment.** A fit may produce a candidate pose without producing a load path.
- **Clearance and thread closure are separate conditions.** A clearance pass-through is not a hold; the closing
  thread/nut/feature must be a real modeled part or confirmed integral geometry.
- Missing/`UNKNOWN`/`CONTRADICTED` evidence creates **no** confirmed load-bearing edge.
- Bracket and rail are grounded only through explicit hardware chains (e.g. foot → T-nut → extrusion slot).
- **Belt capture must include the selected real belt participant** (decisions/005).
- Never fudge a fit. If a fastener/mate fails, change the *part*, never the numbers. (Both sides are
  first-class measured ports authored independently from evidence.)

## How the engine encodes this

- `ontology/templates.py` — typed declarative `AttachmentTemplate`s (participants by port family+polarity;
  `enforce` pose relations; `checks` predicates; `closure` = a real fastener part OR named integral geometry;
  `load_paths`). `bind()` BANS free world-axis/plane endpoints — "coaxial to an abstract axle" is inexpressible.
- `ontology/pose_solve.py` — solves a moving body's pose ONLY from `enforce` (coaxial; oppose_and_seat WITH a
  bolt-pattern group). Unsolvable enforce raises rather than placing something plausible.
- `ontology/load_path.py` — three-state closure gate: `HELD_CONFIRMED` (continuous chain of instantiated,
  geometry-checked edges to ground, each closed by a real fastener/confirmed integral geometry),
  `HELD_PROVISIONAL` (some check UNKNOWN or closure inferred/nominal), `UNHELD` (no path / a check FAILs /
  closure missing). Final validation requires CONFIRMED for every body.
- Gate entry: `benchmarks/_rung2_v2_gate.py`. A green result is `valid_under_encoded_model`, never universal proof.
