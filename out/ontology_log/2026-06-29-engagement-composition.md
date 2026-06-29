# Engagement Composition Migration

Date: 2026-06-29

## Summary

This pass moves the attachment registry toward:

```text
primitive predicate -> framed engagement -> composition closure rule -> derived AttachmentTemplate
```

Converted templates:

- `journal_supported_by_bearing`
- `radial_screw_against_cylindrical_target`
- `clamp_keyed_hub_on_journal`
- `pilot_clamped_hub_to_carrier`
- `fastened_face_mount`

Approved stricter deltas:

- `fastened_face_mount` now requires a modeled threaded `receiver` through `THREAD_MATE`.
- `clamp_keyed_hub_on_journal` now requires explicit `TIP_CONTACT` instead of treating a clamp fastener as a magic closure token.
- Fastener-closure checks are projected onto non-fastener load edges so `head_seat`, `thread_engagement`, and `tip_or_clamp_contact` cannot drift away from the held-body edge.

## Remaining Hand-Authored Templates

Ratification candidates because they use predicates or closure structures not yet represented as concise engagement compositions:

- `retained_revolute_on_journal`
- `revolute_fit_on_journal`
- `fixed_hub_on_journal`
- `inner_race_axial_retention`
- `shoulder_screw_into_tapped_support`
- `shoulder_screw_through_support_with_nut`
- `screw_into_threaded_receiver`
- `bounded_bolt_pattern_seat`
- `through_bolted_plate`
- `profile_carriage_on_guide`
- `timing_belt_mesh`
- `tslot_captured_mount`
- `bearing_ring_mount`
- `pilot_located_bolted_hub`
- `pilot_located_through_bolted_hub`
- `crossed_roller_revolute`
- `belt_capture`

Next decision: each remaining entry should either be expressed with the current engagement catalog, ratify a new generic engagement, or move to a project-local binding.
