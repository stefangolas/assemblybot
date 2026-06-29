# Example Project Workspace

This is an example workspace for a project.
It demonstrates the standard layout:
- `project.json`: Configuration for the project (like `canonical_assembly`).
- `state.json`: Current agent-harness stage/status.
- `roles.json`: Physical part roles and provenance status.
- `events.jsonl`: Append-only audit log produced by publish/status tools.
- `out/`: Output artifacts (renders, assembly JSON).

Canonical publication must go through:

```bash
python tools/prompt_context.py <project_id>
python tools/project_status.py <project_id> --human
python tools/publish_project.py <project_id>
```

Prototype outputs may exist under `out/`, but they must not be treated as
canonical unless publish gates pass.
