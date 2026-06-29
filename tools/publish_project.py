"""Publish gate for AssemblyBot projects.

This command is intentionally stricter than "write project.json". It only marks
a project as published when canonical verification, catalog provenance, and
render sanity all pass.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from assembly.catalog_provenance import check_project
from assembly.verify_canonical import verify_canonical
from tools.project_status import canonical_path, load_json, resolve_project
from tools.render_sanity import check_project as check_render_sanity


def _skipped_verify_gates(status: Any) -> list[str]:
    if not isinstance(status, dict):
        return []
    return sorted(k for k, v in status.items() if v == "SKIP")


def append_event(project_dir: Path, event: dict[str, Any]) -> None:
    path = project_dir / "events.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")


def publish(project: str | Path, *, dry_run: bool = False) -> dict[str, Any]:
    project_dir = resolve_project(project)
    meta_path = project_dir / "project.json"
    meta = load_json(meta_path, {})
    canonical = canonical_path(project_dir, meta)
    results: dict[str, Any] = {
        "project": project_dir.name,
        "project_dir": str(project_dir),
        "canonical_assembly": str(canonical) if canonical else None,
        "passed": False,
        "gates": {},
        "blockers": [],
    }

    provenance = check_project(project_dir)
    results["gates"]["catalog_provenance"] = provenance.to_json()
    if not provenance.passed:
        results["blockers"].extend(
            f"catalog provenance: {i.role}: {i.message}"
            for i in provenance.issues
            if i.severity == "FAIL"
        )

    if not canonical or not canonical.exists():
        results["gates"]["canonical_verify"] = {"passed": False, "status": "missing_canonical"}
        results["blockers"].append("canonical assembly is missing")
    else:
        verify_passed, verify_status = verify_canonical(canonical, verbose=False)
        results["gates"]["canonical_verify"] = {"passed": verify_passed, "status": verify_status}
        if not verify_passed:
            results["blockers"].append(f"canonical verification failed: {verify_status}")
        skipped = _skipped_verify_gates(verify_status)
        if skipped:
            results["blockers"].append(
                "canonical verification skipped required gate(s): " + ", ".join(skipped)
            )

    render = check_render_sanity(project_dir)
    results["gates"]["render_sanity"] = render
    if not render["passed"]:
        results["blockers"].append("render sanity failed")

    results["passed"] = not results["blockers"]
    now = datetime.now(timezone.utc).isoformat()

    event = {
        "type": "publish_attempt",
        "timestamp": now,
        "passed": results["passed"],
        "gates": results["gates"],
        "blockers": results["blockers"],
    }

    if results["passed"] and not dry_run:
        meta["status"] = "published"
        meta["verification"] = "PASS: publish_project gates passed"
        meta["published_at"] = now
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        append_event(project_dir, event)
    elif not dry_run:
        append_event(project_dir, event)

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish a project only if all canonical gates pass.")
    parser.add_argument("project", help="project id, project dir, or project.json path")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    result = publish(args.project, dry_run=args.dry_run)
    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"publish_project: {'PASS' if result['passed'] else 'FAIL'} {result['project']}")
        for name, gate in result["gates"].items():
            passed = gate.get("passed") if isinstance(gate, dict) else None
            print(f"  {name}: {'PASS' if passed else 'FAIL'}")
        for blocker in result["blockers"]:
            print(f"  BLOCKER: {blocker}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
