# Completion Contract

Before ending an AssemblyBot build turn:
- Run or read `tools/project_status.py <project> --human`.
- Report the current stage and any blockers.
- If the user asked for a build/publish result, run `tools/publish_project.py <project>` or explain why it is blocked.
- Say "prototype" or "unverified" explicitly for any assembly that lacks a passing publish gate.
- Only call the project done when `publish_project.py` exits successfully.
