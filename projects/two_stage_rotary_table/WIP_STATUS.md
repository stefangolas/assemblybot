# Two-Stage Rotary Table WIP Status

Date: 2026-06-29

This document tracks the current work in progress at two levels:

- Application refactor: AssemblyBot ontology, verification, catalog/discovery, and publish guardrails.
- Assembly project: the THK RU85 two-stage 16:1 belt-driven rotary table.

## Current Verdict

The project is intentionally blocked. The current artifact is useful for inspection, but it is not publishable as a mechanically validated assembly.

Latest status command:

```powershell
python -m tools.project_status projects\two_stage_rotary_table --run-verify --human
```

Current gate state:

```text
load_path: FAIL
cad_fidelity: PASS
interference: FAIL
render_accounting: PASS
structural_visibility: PASS
fastener_primitives: PASS
```

The important improvement is that the previous false-positive pass has been removed. Rendered rigid parts are now accounted for, structural parts are visible, and fastener closures must be backed by primitive checks involving the fastener.

## Application Refactor WIP

### Completed

- Added project-status and publish-gate infrastructure so projects cannot be marked published by editing metadata alone.
- Added render sanity and canonical verification status reporting.
- Added catalog provenance checks and project prompt/context scaffolding.
- Fixed hosted project asset URL resolution in `assembly/interference.py`; project-local GLB assets now resolve from hosted URLs such as `/two_stage_rotary_table/out/assets/...`.
- Added `render_accounting` in `assembly/verify_canonical.py`: any physical `_render` ref must be in `_verify.lib` or explicitly exempted as non-structural.
- Added `structural_visibility` in `assembly/verify_canonical.py`: structural `_verify.lib` refs cannot be hidden from `_render` unless explicitly exempted.
- Added `fastener_primitives` in `assembly/verify_canonical.py`: fastener closures must include primitive checks involving the fastener.
- Removed `fastener_contact` as a canonical gate. It was a temporary proximity heuristic; the intended model is primitive checks inside composable templates.
- Added primitive check `tip_or_clamp_contact` in `ontology/ports_match.py`.
- Added generic composable `radial_screw_against_cylindrical_target` in `ontology/templates.py`.
- Tightened `fastened_face_mount` so it now requires `head_seat` rather than treating a fastener as a magic closure token.

### Architectural Direction

The application package should own:

- Port families.
- Primitive predicates.
- Gate policy.
- A small set of generic examples.

Projects should own:

- Project-local composables assembled from primitives.
- Mechanism-specific bundles that are still context-free enough to audit locally.

Avoid growing the global ontology into a catalog of assembly intentions such as "pulley on shaft." A pulley fixed to a shaft should be expressed as cylindrical fit plus a torque-retention primitive, such as radial screw contact, key/keyway, or split-clamp screw stack.

### Remaining Application Work

- Move broad composables out of the global registry or mark them as examples/provisional.
- Add a clean mechanism for project-local composable definitions.
- Improve failure reporting so load-path failures point directly to the failed primitive check and affected instance.
- Make publish/project-status aware of new canonical gate names without requiring ad hoc interpretation.

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

- Removed guard panels from the render because they occluded the mechanism.
- Split pulley definitions by role and bore:
  - Output 72T pulley with carrier pilot bore.
  - Countershaft 72T pulley with 15 mm bore.
  - Countershaft 18T pulley with 15 mm bore.
  - Motor 18T pulley with 14 mm bore.
- Replaced the bad countershaft pulley binding with a generic radial screw/cylindrical target primitive composition.
- Added radial threaded-hole ports for carrier and pulley clamp screws.
- Added rendered standoff fasteners at each standoff end; no hidden standoff screw placeholders remain.
- Blocked the project metadata instead of marking the assembly ready while verification is failing.

### Current Mechanical Blockers

The remaining failures are real assembly/geometry issues, not hidden-render accounting issues.

Primary `load_path` causes:

- Some face mounts still fail primitive `head_seat` checks because screw head placement is not seated on the mounted face.
- `pilot_clamped_hub_to_carrier` still needs to be decomposed or replaced with explicit face-seat plus bolt-pattern/thread primitives.
- Several carriage/standoff/bearing-holder mounts need real clearance/thread ports rather than simplified face mounts.
- The rotor hub/spindle and split-carrier region still contains a misplaced/floating M8 structural screw. The carrier clamp screw needs a real split-clamp ear/cross-screw geometry and primitive checks, not a visually approximate screw near the spindle.

Primary `interference` causes:

- Countershaft pulley and upper carriage plate overlap.
- Countershaft intersects carriage plates because the plate placeholders need center/bearing clearances.
- Motor belt intersects motor/standoff regions due to layout/clearance issues.
- Countershaft 72T pulley is too close to bearing/standoff hardware.
- Baseplate/countershaft clearance still shows a small overlap.

### Next Assembly Work

1. Finish carriage plate geometry:
   - Add central shaft/bearing clearance.
   - Add bearing-holder mounting hole pattern.
   - Add standoff hole pattern.
   - Update ports to match the geometry.

2. Replace remaining coarse face mounts:
   - Bearing holder to carriage plate.
   - Carriage plate to standoff.
   - Motor flange to slider.
   - Slider to baseplate.
   - Frame rail/column joints.

3. Decompose output pulley to carrier:
   - `cylindrical_fit` for pulley bore on carrier pilot.
   - `bounded_area_overlap` for pulley face on carrier flange.
   - Explicit bolt-circle fastener primitives for pulley-to-carrier screws.

4. Fix physical clearances:
   - Move pulley planes and carriage plates so the 72T countershaft pulley does not collide with the upper carriage plate or bearing holder.
   - Re-route or reposition motor belt plane relative to motor/standoffs.
   - Verify countershaft does not touch either carriage plate.

5. Re-run:

```powershell
python -m tools.build_two_stage_rotary_table
python -m tools.project_status projects\two_stage_rotary_table --run-verify --human
```

The project can only move back to ready when `load_path`, `cad_fidelity`, `interference`, `render_accounting`, `structural_visibility`, and `fastener_primitives` all pass.
