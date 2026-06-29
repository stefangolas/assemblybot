"""Catalog provenance gate for AssemblyBot projects.

This gate enforces the "catalog-first before canonical" rule at the project-role
level. It intentionally does not try to prove that a selected catalog part is the
right engineering choice; it checks that each physical role has a recorded source
path before the project can be published as canonical.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"


@dataclass
class ProvenanceIssue:
    role: str
    severity: str
    message: str

    def to_json(self) -> dict[str, str]:
        return {"role": self.role, "severity": self.severity, "message": self.message}


@dataclass
class ProvenanceReport:
    passed: bool
    issues: list[ProvenanceIssue] = field(default_factory=list)
    role_count: int = 0

    def to_json(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "role_count": self.role_count,
            "issues": [i.to_json() for i in self.issues],
        }

    def summary(self) -> str:
        if self.passed:
            return f"PASS ({self.role_count} role(s) checked)"
        return f"FAIL ({len([i for i in self.issues if i.severity == FAIL])} blocking issue(s))"


def load_roles(project_dir: Path) -> list[dict[str, Any]]:
    path = project_dir / "roles.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        roles = data.get("roles", [])
        return roles if isinstance(roles, list) else []
    return []


def _role_id(role: dict[str, Any], index: int) -> str:
    return str(role.get("id") or role.get("role_id") or role.get("name") or f"role_{index}")


def _source(role: dict[str, Any]) -> str:
    return str(
        role.get("source")
        or role.get("source_type")
        or role.get("kind")
        or role.get("classification")
        or ""
    ).lower()


def _status(role: dict[str, Any]) -> str:
    return str(role.get("status") or role.get("state") or "").lower()


def _has_evidence(role: dict[str, Any]) -> bool:
    for key in ("evidence", "evidence_refs", "evidence_paths", "candidate_evidence", "catalog_evidence"):
        value = role.get(key)
        if isinstance(value, list) and value:
            return True
        if isinstance(value, dict) and value:
            return True
        if isinstance(value, str) and value.strip():
            return True
    return bool(role.get("part_number") and role.get("source_uri"))


def _custom_license(role: dict[str, Any]) -> dict[str, Any]:
    lic = role.get("custom_license") or role.get("license") or {}
    return lic if isinstance(lic, dict) else {}


def _license_complete(lic: dict[str, Any]) -> bool:
    if not lic:
        return False
    searched = lic.get("searched") or lic.get("vendors_searched") or lic.get("vendors") or []
    rejected = lic.get("candidates_rejected") or lic.get("rejections") or []
    configurable = lic.get("configurable_options_rejected") or lic.get("configurable_rejections") or []
    licensed = lic.get("licensed_custom")
    if licensed is None:
        licensed = lic.get("approved") or lic.get("accepted")
    return bool(searched) and (bool(rejected) or bool(configurable)) and bool(licensed)


def check_roles(roles: list[dict[str, Any]]) -> ProvenanceReport:
    issues: list[ProvenanceIssue] = []
    physical_roles = [
        r for r in roles
        if not r.get("non_physical") and not r.get("ignore_provenance")
    ]

    if not physical_roles:
        issues.append(ProvenanceIssue(
            "project",
            FAIL,
            "roles.json is missing or contains no physical roles",
        ))
        return ProvenanceReport(False, issues, 0)

    for i, role in enumerate(physical_roles, 1):
        rid = _role_id(role, i)
        source = _source(role)
        status = _status(role)
        generated = bool(role.get("generated"))

        if status in {"prototype", "scratch", "unverified"}:
            issues.append(ProvenanceIssue(rid, FAIL, "role is still marked prototype/scratch/unverified"))
            continue

        if source in {"standard", "standard_generated", "generated_standard"}:
            continue

        if source in {"generated_flexible", "belt_generated", "generated_belt"}:
            if not _has_evidence(role):
                issues.append(ProvenanceIssue(rid, FAIL, "generated flexible role lacks catalog parameters/evidence"))
            continue

        if source in {"catalog", "configurable_catalog", "misumi", "mcmaster"}:
            if not _has_evidence(role):
                issues.append(ProvenanceIssue(rid, FAIL, "catalog role lacks evidence reference"))
            if status and status not in {"accepted", "resolved", "confirmed", "selected"}:
                issues.append(ProvenanceIssue(rid, FAIL, f"catalog role status is not accepted/resolved: {status}"))
            continue

        if source in {"custom", "custom_machined", "custom_rigid"} or generated:
            lic = _custom_license(role)
            if not _license_complete(lic):
                issues.append(ProvenanceIssue(
                    rid,
                    FAIL,
                    "custom/generated rigid role lacks complete catalog-search license",
                ))
            continue

        issues.append(ProvenanceIssue(rid, FAIL, "role lacks recognized provenance source"))

    return ProvenanceReport(not any(i.severity == FAIL for i in issues), issues, len(physical_roles))


def check_project(project_dir: Path) -> ProvenanceReport:
    return check_roles(load_roles(Path(project_dir)))


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Check project catalog provenance.")
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    report = check_project(args.project_dir)
    if args.as_json:
        print(json.dumps(report.to_json(), indent=2))
    else:
        print(f"catalog_provenance: {report.summary()}")
        for issue in report.issues:
            print(f"  {issue.severity}: {issue.role}: {issue.message}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
