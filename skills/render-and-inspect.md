# Skill: Render and Inspect (the real verification)

**Looking at the rendered assembly is the verification that matters.** A green numerical predicate proves only
what it encodes; vision catches the wrong part, a float, an interpenetration, a wrong scale, a fake joint.

## Rules

- **Render and LOOK after every part you add** — never wait until the end. Highlight the new part.
- Inspect from multiple angles (iso + axis views). Ask: is each part real catalog geometry? does each bounded
  engagement region actually overlap its counterpart? is every part HELD? is anything floating, interpenetrating,
  or wrong-scale?
- Say **"I looked at it"** only after actually inspecting the image. Report which numerical predicates were
  checked **separately** from what the look established.
- **Units:** everything is **metres at the glTF boundary** (cascadio writes metres; STEP is mm). Any mesh you
  generate must export in metres. A part authored in mm renders 1000× too big and flies off-screen. If a part
  isn't visible at sane scale, its units/placement are wrong — fix that first. Camera ~0.03–0.2.

## Tools

- **`benchmarks/_attach_check.py`** — renders ONE mating pair in isolation with dimension overlays (bore Ø vs
  shaft Ø, pattern span, seating gap, reach/overhang, tooth pitch/engagement). Use it the moment you assign an
  attachment: confirm the two parts are physically held by a real feature, not just numerically coincident.
- **`benchmarks/_shot.py <placements.json> <prefix> [new] [angles]`** + `_shot_incremental.py` — full-assembly
  / part-by-part shots via `web/incr.html` (and interactive `web/index.html`). Renderer is vendored offline at
  `web/vendor/` (three 0.160) — no network needed.
- **`benchmarks/_clamp_measure.py`** — example mesh-measurement: `trimesh.load(path, force='scene')` to keep
  sub-bodies, scale metres→mm, section with a plane and read small closed loops as holes (centroid + radius).
  Reuse this pattern to measure any mating feature; never assume geometry from the part name.

## Gotchas

- Headless hardware GL races on pixel readback → BLANK frames; the shooters launch chromium with
  `--use-gl=swiftshader --enable-unsafe-swiftshader`.
- One placement source per part instance (`out/<name>_placements.json`) feeds both the math and the viewer —
  never compute a pose twice.
- Meshes are centred on their geometric centre, not a datum. Record reconciliation (seat offsets, axis mapping)
  in `part_frame.drawing_to_cad`; never hardcode it in a benchmark/viewer. Catalog meshes are simplified, so a
  mesh boolean overlaps at designed engagements (press fits, seats) — mesh-overlap is a poor gate; judge by
  looking + spec clearances.
