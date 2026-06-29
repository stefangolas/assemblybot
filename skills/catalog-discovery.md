# Skill: Catalog Discovery (parallel evidence gathering)

The goal: make part discovery fast by running independent searches **concurrently**, without letting parallel
workers create conflicting ontology or assembly truth. Workers gather evidence; the **lead** interprets.

## Default behavior

**Parallelize discovery whenever ≥2 independent part roles or candidate searches exist.** Do not investigate
independent missing parts serially. Independent Rung 2 jobs, for example: replacement bracket; bracket/rail
T-slot nut; rail mounting hardware; exact S3M-10 belt; idler spacers.

## Vendor default: STRONGLY prefer MISUMI

**Default every part search to MISUMI first.** Only fall back to McMaster when MISUMI genuinely does not
carry the part, or the role is intrinsically a McMaster item (e.g. the `6575N203` extrusion itself). This is
a standing default, not a per-job toggle.

Why MISUMI is preferred:
- Its classic detail pages render and read cleanly under the headless/raw-CDP scout flow; **McMaster's
  catalog grids are virtualized and come back blank headless**, so discovery there is slow and fumbles.
- MISUMI CAD is retrievable **hands-off** via the in-page fetch (`fetch_misumi_cad`); no clicking, no
  trusted-input dance. McMaster CAD needs the warm-tab trusted-click flow and frequently stalls.
- Keeping the whole BOM on one vendor keeps every part's CAD retrievable the same way.

So in every job packet set `"vendor_priority": ["MISUMI", "McMaster"]` and tell the scout: **try MISUMI
first; only use McMaster if MISUMI has no equivalent, and STOP+report fast if McMaster rendering stalls**
(don't burn time re-trying a blank McMaster grid — kick it back to the lead, who can redirect to MISUMI).
If a McMaster-targeted scout is observed fumbling on rendering, the lead STOPs it and re-dispatches on MISUMI.
Filter MISUMI listings to Brand = MISUMI (MSM1) so CAD is retrievable (third-party brands often 504 on CAD).

## Lead orchestration procedure

1. Identify all currently missing catalog roles (from `status/rung2.md` + `tasks/current.md`).
2. Resolve any upstream design variable a search depends on first (e.g. lock the foot thread = M5 before the
   nut search). A worker can't choose a design variable for you.
3. Write one normalized **job packet** per independent role (below). Put ALL hard constraints in the packet —
   workers do not inherit conversation context.
4. Spawn background evidence subagents (`part-evidence-scout`, Sonnet) for the independent jobs.
5. While they run, keep working: assembly review, existing-part integration, prior-result review.
6. Receive structured candidate reports.
7. Select the final candidate (lead-only).
8. Perform the canonical ontology + 3D mapping yourself (`skills/ontology-mapping.md`).

## Job packet format

```json
{
  "job_id": "rung2-bracket-t-nut",
  "mechanical_role": "T-slot nut securing the pulley bracket foot",
  "hard_requirements": {"extrusion_series": "6575N203 40 mm", "slot_width_mm": 8, "internal_thread": "M5"},
  "preferred_requirements": {"insertion_style": "drop-in if available", "vendor_priority": ["MISUMI", "McMaster"]},
  "known_geometry": {"bracket_foot_hole": "NA5 / nominal Ø5.5 clearance"},
  "required_evidence": ["exact part number", "exact compatibility statement or dimensions",
                         "manufacturer drawing or dimensional table", "CAD when available"],
  "allowed_output_root": "candidate_evidence/rung2-bracket-t-nut/",
  "forbidden_actions": ["modify canonical ontology", "edit assembly", "bind attachments"]
}
```

## Breadth-first discovery (each worker)

1. Find several plausible candidates cheaply. 2. Record visible hard-constraint matches. 3. Reject obvious
mismatches immediately. 4. Shortlist ≤3. 5. Retrieve deep evidence (drawing/CAD) only for the shortlist.
6. Return the strongest candidate + alternatives. **Do not spend CAD-generation time on a candidate already
contradicted by its drawing/spec.**

For McMaster specifically, treat category/facet pages as candidate-PN indexes, not proof. Confirm every selected
PN with the product page. Use product titles as a fast class/family rejection gate, and record likely-to-recur
near-matches so the next pass does not re-check the same wrong part.

## Parallel topology

One subagent per independent mechanical role (and per vendor / competing family when comparison matters).
Keep it flat:

```
Opus lead
├── Sonnet: exact S3M-10 belt
├── Sonnet: bracket/rail T-slot nut
├── Sonnet: rail mounting hardware
├── Sonnet: idler spacers
└── Sonnet: replacement-bracket verification
```

Workers should NOT spawn more agents unless their job has genuinely independent candidate branches with
non-conflicting output scopes.

## Concurrency target

~3–5 active evidence workers — and the lead should dispatch all the independent ones **in a single batch**,
not trickle them out. Avoid excessive concurrency that causes vendor throttling, browser instability,
shared-session corruption, CAD-generation congestion, or redundant searches.

**Shared warm Chrome (CDP port 9222):** there is normally ONE warm, logged-in Chrome (Misumi + McMaster
sessions). Concurrent scouts share its Akamai cookies/session — that part does NOT fork. So each scout MUST
operate on its **own page target/tab** (CDP `Target.createTarget`, or `data/rawcdp.py` / the vendor fetch
helpers scoped to its own tab) and never drive another scout's tab or the same React configurator from two
tasks at once. **Each scout MUST close the tab it created (`Target.closeTarget`) when finished — and in a
finally/cleanup path so a tab is closed even on error or early STOP** — so orphaned tabs don't pile up and
degrade the shared warm session. Only ever close the tab you created; never close another scout's tab or the
base logged-in Misumi/McMaster session tabs. Prefer the structured JSON/fetch endpoints (`fetch_misumi_cad`, `mcmaster_fetch`) over
rendering full pages. The lead MUST put the "use your own tab; do not relaunch Chrome; STOP+report on a
403/login wall" directive in every scout packet. If the shared session gets walled, scouts stop and the lead
re-warms once (browse a page in the tab) — never relaunch from a worker.

## Concurrent I/O inside one worker

Parallelize independent network/file ops without nesting reasoning agents. After identifying an exact
candidate, run concurrently: retrieve drawing; retrieve product/spec page; retrieve BOM; start CAD
generation; inspect cached family docs. **While CAD generation is pending, do useful work** — parse the
drawing, build the manifest, record option codes, identify required CAD measurements, inspect alternates,
prepare the report. Never wait idly in a poll loop. Never manipulate the same stateful React configurator
109: from two tasks at once. Use bounded polling with useful work between polls.
110: 
111: ## Design Advice: Configurable Adapter Plates
112: 
113: When a standard part's hole pattern (e.g. an inline belt clamp like the TBCR series) does not match the mounting pattern of a mating part (like an SSEB20 linear block), do not assume you are bottlenecked or must fabricate a custom part. 
114: 
115: Instead, look for **Misumi Configurable Plates** (e.g., the FPT series). These plates can be parametrically configured with specific dimensions (length, width, thickness) and completely arbitrary hole layouts (clearance, tapped, counterbored) to serve as exact drop-in adapter plates (carriage plates) between mismatched catalog parts.
116: 
117: Always consider using the Misumi Configurator space to bridge these gaps. Treat these parametrically configured plates as standard catalog parts, not "custom fabrication", and use them liberally to resolve hole pattern mismatches.
118: 
119: ## Design Advice: Orientation and Pose Constraints
120: 
121: When searching for parts like belt clamps or linear carriages, always include explicit **orientation or pose constraints** in the `hard_requirements` of your job packet. For example, a belt clamp can be "inline" (belt runs parallel to the mounting pattern) or "transverse" (belt runs perpendicular). Without this constraint, a scout may select a clamp that fits the belt but physically crashes into the carriage or routes the belt in the wrong direction. Be extremely explicit about the expected local coordinate frame and mounting orientation.
