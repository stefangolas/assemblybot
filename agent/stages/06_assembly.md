# Stage: Assembly

Allowed:
- Compose placed part instances.
- Bind attachment templates.
- Embed `_verify` using the canonical helper.
- Render incremental looks after meaningful additions.

Forbidden:
- Hosting raw placement JSON as canonical.
- Skipping fastener instances or load-path attachments.
- Treating physical `_render` entries as decorative context.
- Rendering load-bearing parts that are absent from `_verify.lib`.

Exit criteria:
- Canonical assembly JSON has `_verify` and render entries.
- Every physically depicted render ref is either in `_verify.lib` with verified
  attachments/load path, or explicitly listed in `_verify.non_structural`.
- `verify_canonical` passes `load_path`, `cad_fidelity`, `interference`, and
  `render_accounting`.
