# AssemblyBot Agent Entrypoint

`AGENT_INSTRUCTIONS.md` is the reference manual. Do not treat it as the active
stage prompt by itself.

Before doing AssemblyBot build work:

1. Identify the target project under `projects/<id>/`.
2. Run or read `python tools/prompt_context.py <project_id>`.
3. Treat the emitted `CURRENT STAGE`, blockers, allowed actions, forbidden
   actions, and completion contract as active instructions for the turn.
4. Before a final response, run or read `python tools/project_status.py <project_id> --human`.
5. Do not claim a build is complete unless `python tools/publish_project.py <project_id>` succeeds.

Prototype/scratch geometry is allowed only when clearly labelled as prototype.
Canonical hosted assemblies must pass publish gates.
