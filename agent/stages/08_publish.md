# Stage: Publish

Allowed:
- Run `tools/publish_project.py`.
- Confirm the project endpoint and index status.
- Report the URL and verification summary.

Forbidden:
- Manual project-index edits that bypass publish gates.
- Calling prototype output canonical.

Exit criteria:
- `publish_project.py` succeeds and the project index shows a passing status.
