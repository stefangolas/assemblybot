"""Project status and blocker detection for AssemblyBot agent runs.

This is the machine-readable source for prompt packets and publish decisions.
It is deliberately conservative: a missing artifact is a blocker, not an
implicit pass.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from assembly.catalog_provenance import check_project

PROJECTS = ROOT / "projects"


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def resolve_project(project: str | Path) -> Path:
    p = Path(project)
    candidates = []
    if p.exists():
        candidates.append(p)
    candidates.append(PROJECTS / str(project))
    candidates.append(ROOT / str(project))
    for cand in candidates:
        if cand.is_dir() and (cand / "project.json").exists():
            return cand.resolve()
        if cand.is_file() and cand.name == "project.json":
            return cand.parent.resolve()
    raise FileNotFoundError(f"could not resolve AssemblyBot project: {project}")


def canonical_path(project_dir: Path, meta: dict[str, Any]) -> Path | None:
    rel = meta.get("canonical_assembly")
    if not rel:
        return None
    return (project_dir / rel).resolve()


def _assembly_has_verify(path: Path | None) -> bool:
    if not path or not path.exists():
        return False
    try:
        data = json.loads(path.read_text())
    except Exception:
        return False
    return isinstance(data, dict) and "_verify" in data


def _skipped_verify_gates(status: Any) -> list[str]:
    if not isinstance(status, dict):
        return []
    return sorted(k for k, v in status.items() if v == "SKIP")


def _render_candidates(project_dir: Path, canonical: Path | None) -> list[Path]:
    out_dir = project_dir / "out"
    if not out_dir.exists():
        return []
    if canonical:
        stem = canonical.stem
        candidates = sorted(out_dir.glob(f"{stem}_*.png"))
        if candidates:
            return candidates
    return sorted(out_dir.glob("*.png"))


def _stage(meta: dict[str, Any], blockers: list[str], has_roles: bool, canonical: Path | None, has_verify: bool) -> str:
    if not has_roles:
        return "part_roles"
    if any("catalog" in b.lower() or "role" in b.lower() for b in blockers):
        return "catalog_discovery"
    if not canonical or not canonical.exists() or not has_verify:
        return "assembly"
    if blockers:
        return "verification"
    if meta.get("status") == "published":
        return "publish"
    return "verification"


def collect_status(project: str | Path, *, run_verify: bool = False) -> dict[str, Any]:
    project_dir = resolve_project(project)
    meta_path = project_dir / "project.json"
    meta = load_json(meta_path, {})
    state = load_json(project_dir / "state.json", {})
    roles_path = project_dir / "roles.json"
    roles_data = load_json(roles_path, None)
    has_roles = bool(roles_data and (roles_data if isinstance(roles_data, list) else roles_data.get("roles")))

    blockers: list[str] = []
    warnings: list[str] = []
    gates: dict[str, Any] = {}

    if meta.get("status") in {"prototype_unverified", "prototype", "blocked", "failed"}:
        blockers.append(f"project status is {meta.get('status')}")
    if meta.get("verification", "").upper().startswith("FAIL"):
        blockers.append(meta["verification"])

    if not has_roles:
        blockers.append("roles.json is missing or contains no roles")

    prov = check_project(project_dir)
    gates["catalog_provenance"] = prov.to_json()
    if not prov.passed:
        blockers.extend(f"catalog provenance: {i.role}: {i.message}" for i in prov.issues if i.severity == "FAIL")

    canonical = canonical_path(project_dir, meta)
    if not canonical:
        blockers.append("project.json lacks canonical_assembly")
    elif not canonical.exists():
        blockers.append(f"canonical assembly does not exist: {canonical}")

    has_verify = _assembly_has_verify(canonical)
    if canonical and canonical.exists() and not has_verify:
        blockers.append("canonical assembly lacks _verify payload")
    gates["artifact"] = {"passed": bool(canonical and canonical.exists() and has_verify)}

    render_files = _render_candidates(project_dir, canonical)
    if not render_files:
        blockers.append("no project render PNGs found under out/")
    gates["render_artifacts"] = {
        "passed": bool(render_files),
        "files": [str(p.relative_to(project_dir)) for p in render_files],
    }

    if run_verify and canonical and canonical.exists():
        from assembly.verify_canonical import verify_canonical

        passed, verify_status = verify_canonical(canonical, verbose=False)
        gates["canonical_verify"] = {"passed": passed, "status": verify_status}
        if not passed:
            blockers.append(f"canonical verification failed: {verify_status}")
        skipped = _skipped_verify_gates(verify_status)
        if skipped:
            blockers.append("canonical verification skipped required gate(s): " + ", ".join(skipped))
    elif canonical and canonical.exists() and has_verify:
        gates["canonical_verify"] = {"passed": None, "status": "not_run"}
    else:
        gates["canonical_verify"] = {"passed": False, "status": "unverifiable"}

    stage = _stage(meta, blockers, has_roles, canonical, has_verify)
    status = "blocked" if blockers else ("published" if meta.get("status") == "published" else "ready")

    return {
        "project_id": project_dir.name,
        "project_dir": str(project_dir),
        "project_json": str(meta_path),
        "name": meta.get("name", project_dir.name),
        "stage": state.get("stage") or stage,
        "status": status,
        "metadata_status": meta.get("status", ""),
        "canonical_assembly": str(canonical) if canonical else None,
        "blockers": sorted(set(blockers)),
        "warnings": warnings,
        "gates": gates,
    }


def human_report(status: dict[str, Any]) -> str:
    lines = [
        f"PROJECT: {status['project_id']}",
        f"NAME: {status['name']}",
        f"CURRENT STAGE: {status['stage']}",
        f"STATUS: {status['status']}",
    ]
    if status.get("canonical_assembly"):
        lines.append(f"CANONICAL: {status['canonical_assembly']}")
    blockers = status.get("blockers") or []
    if blockers:
        lines.append("BLOCKERS:")
        lines.extend(f"- {b}" for b in blockers)
    else:
        lines.append("BLOCKERS: none")
    warnings = status.get("warnings") or []
    if warnings:
        lines.append("WARNINGS:")
        lines.extend(f"- {w}" for w in warnings)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report AssemblyBot project status.")
    parser.add_argument("project", help="project id, project dir, or project.json path")
    parser.add_argument("--human", action="store_true", help="print a compact text report")
    parser.add_argument("--run-verify", action="store_true", help="run canonical verification if possible")
    args = parser.parse_args(argv)

    status = collect_status(args.project, run_verify=args.run_verify)
    if args.human:
        print(human_report(status))
    else:
        print(json.dumps(status, indent=2))
    return 0 if not status["blockers"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
