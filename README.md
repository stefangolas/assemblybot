# Assembly Agent

Composes working mechanical devices out of **McMaster-Carr catalog parts** using
a deliberately small ontology (see the operating manual). The discipline is
**parsimony**: the ontology grows only when a concrete assembly forces it.

## Status

| Rung | Build | Intended DOF | State |
|------|-------|--------------|-------|
| **0** | socket-head screw + washer, seated under the head | 1 (washer spins) | **PASS** -- all gates green on live McMaster data |
| **1** | 4-hole bracket bolted to a 25 mm T-slot extrusion | 0 (rigid) | **PASS** -- hole pattern from 2-D DWG, 4-bolt over-constraint → DOF 0 |
| **2** | belt-driven linear axis (rail+carriage, 2 shafts/bearings, 2 pulleys, belt) | 1 (carriage translates) | **PASS** -- `path`/`pitch_circle` bootstrap, procedural belt, coupling → DOF 1 |
| 3 | Cartesian gantry | 3 | not started |

All three rungs render in the Three.js viewer (`web/index.html`, scene selector). Ontology
growth is logged in `out/ontology_log/`.

## Layout

```
ontology/      the small, ratified vocabulary (Section 4)
  primitives.py   Point, Axis, Plane  (Path deferred until belt/gear forces it)
  roles.py        the flat role vocabulary
  constraints.py  6 constraints + 4 kinematic joints
  schema.py       Part / Feature / Mate / Assembly (Section 4f, verbatim)
  interfaces.py   functional bundles (Section 4e) -- only built ones live here
data/          Phase-2 data layer (Section 3) -- Playwright, NO API
  browse.py       persistent Chromium context: navigate, screenshot, drive CAD widget
  normalize.py    untyped spec strings -> typed params (raw kept verbatim)
assembly/      Phases 3-4 (offline, against the cached library)
  mobility.py     Kutzbach/Grueber DOF count
  interference.py FCL mesh collision over tessellated glTF
  attachment.py   geometric physical-attachment check: every body reaches the anchor
  validate.py     the validation gates (Section 9)
library/       versioned Part entries -- single source of truth, provenance-linked
cad/           downloaded DWG + STEP + tessellated glTF
out/           solved assembly graphs + validation reports
benchmarks/    the rung ladder (Section 11)
```

## Run Rung 0

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m benchmarks.rung0_screw_washer        # offline: rebuilds from library + CAD
```

CAD/specs were already retrieved live; the benchmark itself runs offline against
the cached library (Section 3: discover once, then operate offline).

## The data path (Section 3)

`mcmaster.com` is server-rendered behind Akamai; a plain HTTP GET returns only a
"please enable JavaScript" shell, so a real browser is mandatory. We drive it with
Playwright. **The CAD-download widget requires no sign-in**: it is a combobox
(`aria-label="Select CAD file type"`) offering `2-D DWG`, `3-D STEP`,
`3-D STEP no threads` (preferred -- threads are a *role*, not geometry),
Parasolid, etc., plus a sibling `<a download>` whose href the combobox rewrites.

Authority hierarchy: **2-D DWG -> feature geometry**, **spec table ->
compatibility scalars + class**, **STEP/glTF -> render + collision + cross-check**.
The simplified non-threaded STEP models threads as a plain cylinder at *nominal
major diameter*, so bore<->thread clearance is judged from the **spec table**, not
a mesh boolean -- see `assembly/interference.py`.

## Rung 2 result

A belt-driven linear axis: extrusion base → rail+carriage (`slider`) on a sub-plate → standoffs →
carriage plate → belt clamp; two shafts in bearings (`bearing_mount` → `revolute`) on brackets beside
each pulley, two XL pulleys (`pulley_mount`), and a belt (`belt_drive`). The belt forced the first new
primitive — `path` — plus the `pitch_circle` role (logged in `out/ontology_log/rung2.md`). The belt is
**generated**, not downloaded: from the catalog spec of `1679K197` (XL, 67 T, 13.4") the toothed loop is
built around the two pitch circles and validated to fit the 132 mm centers (340.4 mm == 67×0.2").
Mobility is no longer a plain joint sum: 15 bodies → 4 rigid groups, `M = 6(4−1−3)+3 = 3`, minus the
**2 belt couplings** (pulley↔pulley, belt↔carriage) = **1** independent DOF. The **attachment** gate
roots at the extrusion anchor and confirms all 15 bodies have a geometrically-verified physical path to
ground (it first caught 9 floating parts — unmodeled standoffs and brackets that couldn't hold their
bearings — which were then fixed). Actuation source tracked in `open_functions`.

## Rung 1 result

`bolt_pattern` expands 4 holes (positions **±12.5, ±37.5 mm** read off the 2-D DWG of
4844N135, 25 mm pitch) into 4 `bolt_joint`s against M6 T-nuts in the rail slot. The
mobility gate **merges rigid bodies over fixed joints** (rail+bracket → 1 rigid group),
so `M = 6*(1-1-0) = 0`, and reports the 3 surplus bolts as **benign intentional
over-constraint** rather than a fault. No ontology primitives were added — only the
`bolt_joint`/`bolt_pattern` conveniences and the rigid-group merge in `mobility.py`
(see `out/ontology_log/rung1.md`). The parsimony hypothesis still holds.

## Rung 0 result

`seated_revolute` = `coaxial`(screw axis, washer bore) + `coplanar`(under-head
face, washer face) -> `revolute`. Mobility `M = 6*(2-1-1) + 1 = 1` -- the washer
is free to spin, the correct hand-checkable answer. Interference: FCL reports a
0.1 mm contact (washer ID vs the under-head fillet) within the 0.12 mm seating
tolerance -- contact, not interference.
