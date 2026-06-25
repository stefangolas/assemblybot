# Refactor plan: app/pipeline vs project workspaces + visualizer overhaul

Status: PROPOSAL for the next agent. Written 2026-06-24 from a code survey. Three independent
work items; do them in the order below (A unblocks the server routing that B/C use for pathing,
but B/C can also proceed against the current layout if A slips).

---

## Goals (user's directions, verbatim intent)

1. **Separation of concerns — application/pipeline layer vs project layer.** Today the repo root
   IS the application *and* a dumping ground for one project's artifacts. Establish **project
   workspaces** (one dir per project) that are **git-ignored**, so the committed tree is just the
   reusable engine/pipeline/viewer.
2. **Project-scoped serving.** `localhost:8000/<project_name>` opens that project in the viewer;
   `localhost:8000/` (base) returns a clean **list of projects**. Today the base index is the
   cluttered repo root (plain `python -m http.server`).
3. **Visualizer overhaul.** On-page **UI for configurable parameters** (exploded view, etc.);
   **unobtrusive floating leader callouts** (annotations with leader lines, not baked-in text);
   **cel/toon shading with pastel colors + good lighting**; **sepia/light-tan paper background**.

---

## Current state (survey)

**Engine / pipeline (reusable, project-agnostic) — KEEP committed:**
- `ontology/` — the v2 attachment ontology (ports, templates, load_path, manufacturability,
  pose_solve, schema_v2, ports_match, semantics, …). The core asset.
- `assembly/` — mate_solver, belt, mobility, interference, validate.
- `data/` — catalog-fetch pipeline (misumi_fetch, mcmaster_fetch, rawcdp, misumi_validate, …).
- `schematics/` — parametric matplotlib schematic renderer (primitives + rotary_stage).
- `web/` — the 3D viewer: `incr.html` (data-driven) + `index.html` (redirect) + `vendor/`
  (three 0.160 module + addons, vendored OFFLINE because the headless browser egress is sandboxed).
- `benchmarks/` — MIXED. App tools: `_shot.py` (headless screenshotter; spins its own
  `SimpleHTTPRequestHandler` on :8762 serving repo root), `_attach_check.py`, `observe.py`,
  `_shot_incremental.py`, the `_*_demo.py` ontology demos. Project builders: `rung0/1/2/3*.py`.

**One project's artifacts (RU85 rotary stage) — currently strewn at root:**
- `cad/` (172 STEP/glTF — generic-fetched + project-custom), `library_v2/` (30 v2 defs) + `library/`
  (33 v1), `out/` (417 renders + placements + the canonical `out/rung3_assembly.json` + ontology_log),
  `drawings/`, `decisions/`, `candidate_evidence/`, `status/`, `tasks/`.
- Project scripts at root: `build_rev_b.py`, `build_rotary_custom.py`, `author_custom_v2.py`,
  `author_ru85_v2.py`, `generate_v2_custom.py`, `scout_*.py`, `find_holes.py`, `check.py`.
- Pure scratch at root: `out_*.txt` (11 files), `jl.json`, `*.output`.
- Historical: `ontology_v1_snapshot/`, `archive/`.

**Pathing facts that constrain the design:**
- `web/incr.html` importmap is absolute: `/web/vendor/three.module.js`, `/web/vendor/addons/`.
- The canonical assembly JSON (`out/rung3_assembly.json`) carries `_render: [{ref,url,color,explode,
  state}, …]` where `url` is an ABSOLUTE server path like `/cad/ROTARY_…glb`, plus `_axis` and a
  per-ref `{R, t_mm}` placement. The viewer does `fetch(SRC)` (the `?src=` query) then
  `loader.load(part.url)`.
- `.gitignore` currently ignores only Python caches/build — NONE of out/, cad/, project scratch.

---

## A. Layer separation + project workspaces

### A.1 Target tree
```
<repo root>  = APPLICATION (committed)
  ontology/            engine
  assembly/            engine
  data/                pipeline (catalog fetch)
  schematics/          pipeline (schematic renderer)
  viewer/              the 3D viewer  (rename of web/: index.html, viewer.js, vendor/, styles)
  server.py            NEW: project-routing dev server (see B)
  tools/               app CLIs: render.py (was _shot), observe.py, attach_check.py, demos
  benchmarks/          capability ladder rung0..4 (app tests that WRITE INTO a project workspace)
  docs/                this plan + docs/decisions/ (the promoted 001-005 general principles)
  # ---- SHARED part catalog (referenced by every project; served at /cad /library /drawings) ----
  cad/                 SHARED STEP + glTF (fetched + generated). NOT per-project.
  library/             SHARED v2 part defs (the reusable part catalog)
  drawings/  evidence/ SHARED custom-part drawings + part sourcing
  # ---- projects = COMPOSITIONS of shared parts into a machine ----
  projects/            <-- GIT-IGNORED workspaces (EXCEPT projects/_example, committed)
    _example/          rung-0 screw+washer template + minimal README.md
    <project>/
      project.json     {name, description, canonical_assembly: "out/<x>.json", created, notes}
      out/             canonical assembly json + *_placements.json + renders + ontology_log/
      decisions/       project-specific decisions (general principles -> docs/decisions/)
      scripts/         the project's ASSEMBLY/build scripts (compose shared parts)
  _archive/            ontology_v1_snapshot, archive, old scratch (committed or ignored, your call)
```

### A.2 Decisions to make (flag to user — see "Open decisions")
- **CAD is SHARED, not project-owned.** `cad/` + the catalog (`library/`, `drawings/`, `evidence/`) are
  shared app-level resources served at absolute mounts (`/cad/`, `/library/`). A project is a COMPOSITION
  of those parts. Consequence: **the assembly JSON `url` fields STAY absolute `/cad/...`** (no
  project-relative rewrite). Only the assembly JSON itself (`?src=`) is project-scoped, under
  `/<project>/out/`. Viewer/three assets served from a stable `/_app/` (or keep `/viewer/vendor/`).
- **Binary policy (cad/ is 172 files).** cad/ is shared, so NOT under the `projects/` ignore. Decide
  separately: commit the binaries, git-lfs them, or .gitignore `cad/*.glb`/`cad/*.step` and treat cad/ as
  a regenerable shared cache (generated parts regenerate; catalog-fetched parts need refetch -- note in a
  cad/ README).
- **benchmarks/ rungs.** Keep the rung scripts as the app-level capability ladder, but they take a
  `--project <name>` (or write into `projects/<name>/out/`). The RU85 builders (`rung3_*.py`,
  `build_*`, `author_*`) move to `projects/rung3_rotary/scripts/`.

### A.3 .gitignore additions
```
projects/*           # all workspaces (artifacts) ...
!projects/_example/  # ...EXCEPT the committed rung-0 template
out_*.txt
*.output
jl.json
out/                 # legacy root artifacts (delete after migrating into projects/<name>/out/)
# cad/ and library/ are SHARED (not ignored here) -- set a binary policy separately
# (commit / git-lfs / or ignore cad/*.glb cad/*.step as a regenerable shared cache).
```
(`projects/_example/` = the rung-0 screw+washer assembly + a minimal README.md, committed so the layout
is discoverable. The general principles `decisions/001-005` are PROMOTED to committed `docs/decisions/`;
project-specific decisions stay under `projects/<name>/decisions/`.)

### A.4 Migration (low-risk, incremental)
1. Create `projects/rung3_rotary/{cad,library,out,drawings,scripts,evidence,decisions}` + `project.json`
   (`canonical_assembly: "out/rung3_assembly.json"`).
2. `git mv`/move the RU85 ASSEMBLY artifacts (out/, scripts/, project decisions) in. Shared cad/ library/
   drawings/ STAY at root; assembly `url`s remain absolute `/cad/...` (no rewrite).
3. Add `.gitignore` entries; delete the `out_*.txt`/`jl.json`/`*.output` scratch.
4. Repoint `tools/render.py` + `observe.py` + `benchmarks/*` to the project workspace + the new server.
5. Verify a clean checkout has NO project artifacts and the engine still imports + benchmarks run into a
   fresh `projects/<name>/`.

---

## B. Project-routing dev server (`server.py`)

Replace `python -m http.server` with a small committed server (stdlib `http.server` subclass is enough;
Flask optional). Routes:
- `GET /` -> **HTML project index**: scan `projects/*/project.json`, render a clean card list
  (name, description, link to `/<project>/`). This is the "base url returns the list of projects."
- `GET /<project>/` -> serve `viewer/index.html` with the project bound (inject the canonical assembly
  path, e.g. `viewer/index.html?project=<project>` or a templated `<base>` tag). Viewer then fetches
  `/<project>/<project.json.canonical_assembly>`.
- `GET /<project>/<path>` -> static file under `projects/<project>/` (the cad/, out/ live here).
- `GET /_app/<path>` -> static app/viewer assets (three vendor, viewer.js, css). The importmap +
  viewer code reference `/_app/vendor/…` instead of `/web/vendor/…`.
- Keep one port (8000). **`tools/render.py` (the headless screenshotter) imports the SAME server** so
  "what the camera renders == what the user sees" (today `_shot.py` has its own root-serving handler on
  :8762 — unify it).

Pathing change summary: viewer resolves `part.url` (now relative `cad/…`) against the project base; app
assets via `/_app/…`; project data via `/<project>/…`. A project dir is then fully self-contained and
served read-only.

---

## C. Visualizer overhaul (`viewer/`)

Keep the **data-driven core** of `incr.html` (query params still drive headless renders, so screenshots
and the interactive UI share ONE code path — the UI just writes the same state the query params set).
Add four things; vendor every new dependency OFFLINE into `viewer/vendor/`.

### C.1 On-page UI control panel
- **lil-gui** (vendored into `viewer/vendor/`), styled to fit the pastel/paper theme. Controls:
  - **Explode** slider (0..1) -> the existing `EXPLODE` factor (per-part `explode` offset along `_axis`).
  - **View** buttons: iso / front(x) / side(y) / top(z) -> the existing camera dirs.
  - **Labels** toggle (on/off) + density.
  - **Gate color** toggle (own color vs UNHELD-red) -> existing `color=gate`.
  - **Parts** show/hide checklist (per ref) -> existing `hide`/`only`.
  - Reset view.
- The panel mutates a single `state` object; a `render()` reads it. Query params initialize `state` so
  `tools/render.py` headless paths keep working unchanged.

### C.2 Floating leader callouts (unobtrusive annotations)
- Use **CSS2DRenderer** (`three/addons/renderers/CSS2DRenderer.js` — vendor it). Each part gets a small
  DOM label anchored to its world-space centroid (compute from the loaded mesh bbox), with a thin
  **leader line** from the label to the part. Unobtrusive = small muted type, thin lines, optional
  fade/whow-on-hover, simple declutter (stack labels at screen edge or offset by index to avoid overlap;
  full auto-layout is out of scope initially — manual offset rules are fine).
- **Needs a human label per part.** Extend the assembly JSON `_render` entries with `label` (e.g.
  "72T pulley", "bolt-on cap") and optionally `group` ("stationary|rotating|pulley|payload|fastener").
  The assembly emitter (`…/scripts/rung3_assembly.py`) adds these. Fasteners probably default to no label
  (or grouped "4× M5×35") to avoid clutter.

### C.3 Cel / toon shading + pastel palette
- Swap `MeshStandardMaterial` -> **`MeshToonMaterial`** with a 2–3 step **gradient map**
  (small DataTexture ramp). Define a **pastel palette by group** (stationary, rotating, pulley, payload,
  fastener) so the look is coherent and grayscale-legible; map the existing per-part hex to its pastel
  group color (or keep per-part but pastel-ize). Keep the UNHELD-red override for `color=gate`.
- Cel **outline**: cheapest is an inverted-hull outline (render back-faces slightly scaled in dark) or an
  `EdgesGeometry` overlay for crisp edges. A full `OutlinePass` (postprocessing) is heavier and needs
  EffectComposer vendored — start with EdgesGeometry/inverted-hull.

### C.4 Lighting + sepia paper background
- Lighting tuned for the toon ramp: a **HemisphereLight** (warm sky / tan ground) + one soft key
  **DirectionalLight** + a gentle fill. Avoid harsh speculars (toon has none anyway).
- `scene.background` = **light tan / sepia** (e.g. `#e9e1cf`–`#ece3d2`). Optionally a very subtle paper
  texture or a CSS radial vignette on the canvas container. Keep it light so pastel parts pop.
- Match `tools/render.py` headless renders to the same bg/lighting so screenshots look identical.

### C.5 Files
```
viewer/
  index.html      thin shell (importmap -> /_app/vendor/, mounts viewer.js)
  viewer.js       the data-driven core + state + UI + labels + toon + lighting
  ui.js           control panel (or inline)
  styles.css      panel + callout + paper-bg styling
  vendor/         three.module.js, addons/{GLTFLoader,OrbitControls,CSS2DRenderer}, lil-gui
```
Backward-compat: keep `?src=&dir=&explode=&hide=&only=&color=` working (headless contract).

---

## Resolved decisions (user, 2026-06-24)
1. **Dir names:** `viewer/`, `tools/`, `projects/` -- confirmed.
2. **CAD + generated files are SHARED, not project-owned** (`cad/`, `library/`, `drawings/`, `evidence/`).
   A project is a COMPOSITION of shared parts -> assembly `url`s stay absolute `/cad/...`; only the
   assembly JSON is project-scoped. (Settles pathing; no relative-url rewrite.)
3. **`decisions/001-005` -> promote to committed `docs/decisions/`** (general principles).
4. **Commit `projects/_example/`** = the rung-0 screw+washer assembly + a minimal README.md (layout + how
   to build/serve). Everything else under `projects/` is git-ignored.
5. **UI lib: lil-gui** (vendored), as long as the browser UI is clean.
6. **Cel outline: EdgesGeometry / inverted-hull (light)** -- no postprocessing/EffectComposer vendoring.
7. **cad/ binary policy: GIT-IGNORE** (regenerable/refetchable shared cache). `.gitignore` now ignores
   `cad/*.{glb,step,stp,zip}`, `out/`, scratch (`out_*.txt`, `*.output`, `jl.json`), and `projects/*`
   (except `projects/_example/`). The catalog DEFS in `library*/` stay COMMITTED; only heavy 3D model
   binaries are ignored. **81 cad binaries are already tracked** -> migration A must run
   `git rm -r --cached cad/*.glb cad/*.step cad/*.zip out/` to actually stop tracking them (ignoring
   alone does not untrack). Generated parts regenerate via their build scripts; catalog-fetched parts
   refetch via `data/` -- note this in a `cad/README`.

---

## Sequencing for the next agent
1. **A** (workspaces + .gitignore + migrate RU85 composition; cad/library stay shared) -- unblocks clean serving.
2. **B** (`server.py` project routing + unify `tools/render.py`) — `localhost:8000` clean index.
3. **C** (viewer: UI panel -> labels -> toon+palette -> lighting+paper bg), vendoring each addon.
Each step is independently verifiable (clean checkout test; base index lists projects; a render LOOKS
like the new pastel/paper style). Nothing here changes the ontology/engine.
```
