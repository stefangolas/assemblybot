# Two-Stage Rotary Table WIP Status

Date: 2026-06-29

This document tracks current work in progress at two levels:

- Application refactor: AssemblyBot ontology, verification, catalog/discovery, and publish guardrails.
- Assembly project: the THK RU85 two-stage 16:1 belt-driven rotary table.

## Current Verdict

The canonical assembly now passes the verification gates and project status reports ready.

Latest status command:

```powershell
python -m tools.project_status projects\two_stage_rotary_table --run-verify --human
```

Current result:

```text
STATUS: ready
BLOCKERS: none
```

Current canonical gate state:

```text
load_path: PASS
cad_fidelity: PASS
interference: PASS
render_accounting: PASS
structural_visibility: PASS
fastener_primitives: PASS
```

## Application Refactor WIP

### Completed

- Added project-status and publish-gate infrastructure so projects cannot be marked published by editing metadata alone.
- Added render sanity and canonical verification status reporting.
- Added catalog provenance checks and project prompt/context scaffolding.
- Fixed hosted project asset URL resolution in `assembly/interference.py`; project-local GLB assets now resolve from hosted URLs such as `/two_stage_rotary_table/out/assets/...`.
- Added `render_accounting` in `assembly/verify_canonical.py`: any physical `_render` ref must be in `_verify.lib` or explicitly exempted as non-structural.
- Added `structural_visibility` in `assembly/verify_canonical.py`: structural `_verify.lib` refs cannot be hidden from `_render` unless explicitly exempted.
- Added `fastener_primitives` in `assembly/verify_canonical.py`: fastener closures must include primitive checks involving the fastener.
- Removed `fastener_contact` as a canonical gate. Primitive checks inside composable templates now carry that responsibility.
- Added primitive check `tip_or_clamp_contact` in `ontology/ports_match.py`.
- Added generic composable `radial_screw_against_cylindrical_target` in `ontology/templates.py`.
- Tightened `fastened_face_mount` so it requires `head_seat`.
- Added `ontology/engagements.py` as an adapter-first engagement composition layer.
- Converted `journal_supported_by_bearing` to derive from `RACEWAY`.
- Added golden tests for the derived RACEWAY template and intended-open DOF guardrails.

### Engagement Architecture Direction

The emerging layer is:

```text
primitive predicates
  -> framed engagement catalog
  -> composition-level closure and intended-open rules
  -> derived AttachmentTemplate artifacts consumed by existing gates
```

Important boundaries:

- Engagements own intrinsic geometry, framed kinematic effects, and load effects.
- Closure is composition-level, not an engagement tag.
- Kinematic constraints are expressed in local engagement frames; axes are not assumed global.
- The current DOF representation is exact only for axis-aligned local constraints. Oblique or coupled constraints, such as tapered seats, remain out of scope until rank-based constraint algebra is added.
- Derived templates feed the existing `template.result` path; the refactor should not create a parallel DOF authority.

### Remaining Application Work

- Convert additional templates through the engagement adapter:
  - `radial_screw_against_cylindrical_target`
  - `pilot_clamped_hub_to_carrier`
  - `fastened_face_mount`
- Add approved-diff golden tests for templates that intentionally become stricter, especially face mounts that gain explicit thread/nut requirements.
- Move broad project-specific composables out of the global registry or mark them as examples/provisional.
- Improve failure reporting so load-path failures point directly to the failed primitive check and affected instance.

## Assembly Project WIP

### Current Assembly Coverage

The project currently includes:

- Main MIC-6 baseplate centered around the specified output axis.
- Simplified THK RU85 validation geometry.
- Steel rotor hub/spindle.
- Tabletop.
- Split pulley carrier.
- Output 72T pulley.
- Countershaft, upper/lower carriage plates, two 6202 bearing-holder placeholders, four carriage standoffs.
- Countershaft 18T and 72T 15 mm bore pulleys.
- Motor slider, simplified 400 W servo model, and motor 18T pulley.
- Generated belt loops.
- McMaster-style 40 x 80 frame members as generated visual geometry.
- Rendered structural fasteners.

### Fixed During This Pass

- Removed the stale hidden/placeholder fastener placements that put column screws near the output-axis hub/spindle region.
- Added real rendered fastener instances at the four standoff axes.
- Added a short M8 screw model for visual face-clamp locations that should not project into pulley or belt planes.
- Added central/bearing clearance to the carriage plate visual geometry.
- Lowered and synchronized pulley/belt planes through shared constants.
- Reworked the simplified servo visual so the belt plane is not occupied by a solid motor block.
- Rebuilt the canonical artifact and updated project metadata from blocked to ready after verification passed.

### Current Mechanical Status

The current assembly is a verified visual/mechanical representation, not a released manufacturing package.

Known simplifications still present:

- Several catalog parts are still simplified validation geometry rather than exact vendor CAD.
- The split-clamp carrier and bearing-holder regions are represented enough to pass current gates, but still need richer manufacturable detail before drawing release.
- The engagement adapter currently derives only the RACEWAY bearing-support template; other templates still use the legacy hand-authored registry.

### Verification Commands

```powershell
python -m tools.build_two_stage_rotary_table
python -m unittest tests.test_engagements
python -m tools.project_status projects\two_stage_rotary_table --run-verify --human
```
