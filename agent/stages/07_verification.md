# Stage: Verification

Allowed:
- Run canonical verification, catalog provenance, render sanity, and swept checks.
- Diagnose failures and return to earlier stages as needed.

Forbidden:
- Treating advisory or skipped gates as pass.
- Publishing with blockers.

Exit criteria:
- All blocking gates pass.
