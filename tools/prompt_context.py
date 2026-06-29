"""Emit the active AssemblyBot prompt packet for a project.

This is the bridge between natural-language agent control and repo-enforced
project state. Claude/Codex should read this before doing build work; a future
web worker can pass the same packet to its subprocess agent.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.project_status import collect_status, human_report

AGENT = ROOT / "agent"


STAGE_FILES = {
    "intake": "01_intake.md",
    "requirements": "02_requirements.md",
    "part_roles": "03_part_roles.md",
    "catalog_discovery": "04_catalog_discovery.md",
    "part_authoring": "05_part_authoring.md",
    "assembly": "06_assembly.md",
    "verification": "07_verification.md",
    "publish": "08_publish.md",
}


ALLOWED = {
    "intake": ["create/identify project", "record user brief", "ask product-level questions"],
    "requirements": ["refine measurable requirements", "record constraints", "ask tradeoff questions"],
    "part_roles": ["define roles", "mark likely provenance source", "update roles/status"],
    "catalog_discovery": ["search catalogs", "record evidence", "reject candidates", "license custom only with recorded search"],
    "part_authoring": ["author part definitions from evidence", "generate licensed custom parts", "generate flexible belt meshes"],
    "assembly": ["place parts", "bind attachments", "embed _verify", "make prototype renders"],
    "verification": ["run gates", "diagnose blockers", "return to earlier stages"],
    "publish": ["run publish_project", "report hosted endpoint", "record final verification"],
}


FORBIDDEN = {
    "intake": ["publish", "claim build complete"],
    "requirements": ["publish", "treat inferred dimensions as catalog facts"],
    "part_roles": ["publish", "author canonical CAD for unresolved roles"],
    "catalog_discovery": ["publish", "claim completion", "generate canonical custom rigid CAD without a license"],
    "part_authoring": ["publish", "omit real attachment features", "put assembly placement into part definitions"],
    "assembly": ["host raw placement JSON as canonical", "skip fastener/load-path instances", "claim verified"],
    "verification": ["treat skipped gates as pass", "publish with blockers"],
    "publish": ["manual index edits that bypass publish_project", "publish prototypes as canonical"],
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def stage_prompt(stage: str) -> str:
    name = STAGE_FILES.get(stage, "07_verification.md")
    return read_text(AGENT / "stages" / name)


def packet(project: str, *, as_json: bool = False) -> str:
    status = collect_status(project, run_verify=False)
    stage = status["stage"]
    data = {
        "project": status["project_id"],
        "name": status["name"],
        "current_stage": stage,
        "status": status["status"],
        "canonical_assembly": status["canonical_assembly"],
        "blockers": status["blockers"],
        "allowed_actions": ALLOWED.get(stage, []),
        "forbidden_actions": FORBIDDEN.get(stage, []),
    }
    if as_json:
        return json.dumps(data, indent=2)

    lines = [
        "# AssemblyBot Active Prompt Packet",
        "",
        read_text(AGENT / "constitution.md"),
        "",
        "## Project State",
        human_report(status),
        "",
        "## Allowed Actions",
        *[f"- {a}" for a in data["allowed_actions"]],
        "",
        "## Forbidden Actions",
        *[f"- {a}" for a in data["forbidden_actions"]],
        "",
        "## Active Stage Instructions",
        stage_prompt(stage),
    ]

    if stage == "catalog_discovery":
        lines.extend([
            "",
            "## Vendor Notes",
            read_text(AGENT / "vendors" / "misumi.md"),
            "",
            read_text(AGENT / "vendors" / "mcmaster.md"),
        ])

    lines.extend([
        "",
        "## Known Failure Modes",
        read_text(AGENT / "failure_modes.md"),
        "",
        "## Completion Contract",
        read_text(AGENT / "completion_contract.md"),
    ])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit a project-specific AssemblyBot agent prompt packet.")
    parser.add_argument("project", help="project id, project dir, or project.json path")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    print(packet(args.project, as_json=args.as_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
