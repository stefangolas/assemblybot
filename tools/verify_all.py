"""GLOBAL ENFORCEMENT: run the full gate set on EVERY assembly in the repo.

This is the single command that guarantees no assembly escapes validation. It discovers
every project's canonical assembly (projects/*/project.json -> canonical_assembly) and
runs assembly.verify_canonical on each. It exits non-zero if ANY gate fails on ANY
assembly, OR if any artifact lacks a `_verify` payload (an unverifiable assembly is a
failure, not a pass). Wire this into CI / a pre-publish hook so a benchmark physically
cannot ship an assembly that skipped a check.

  python -m tools.verify_all            # check every project
  python -m tools.verify_all <path>...  # check specific canonical .json files
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def discover() -> list[Path]:
    out = []
    for proj in sorted((ROOT / "projects").glob("*/project.json")):
        try:
            meta = json.loads(proj.read_text())
        except Exception:
            continue
        ca = meta.get("canonical_assembly")
        if not ca:
            continue
        p = (proj.parent / ca)
        if p.exists():
            out.append(p)
    return out


def main(argv=None):
    from assembly.verify_canonical import verify_canonical
    from assembly.catalog_provenance import check_project as check_catalog_provenance
    from tools.render_sanity import check_project as check_render_sanity
    argv = list(argv if argv is not None else sys.argv[1:])
    targets = [Path(a) for a in argv] if argv else discover()
    if not targets:
        print("verify_all: no canonical assemblies found")
        return 1

    results = []
    for path in targets:
        path = Path(path).resolve()
        print("=" * 78)
        project_dir = path.parent.parent if path.parent.name == "out" else path.parent
        meta_path = project_dir / "project.json"
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
            except Exception:
                meta = {}

        passed, status = verify_canonical(path, verbose=True)
        gates = dict(status)

        prov = check_catalog_provenance(project_dir)
        gates["catalog_provenance"] = "PASS" if prov.passed else "FAIL"
        if not prov.passed:
            passed = False
            print(f"  catalog_provenance: FAIL {prov.summary()}")
            for issue in prov.issues:
                if issue.severity == "FAIL":
                    print(f"    {issue.role}: {issue.message}")
        else:
            print(f"  catalog_provenance: PASS {prov.summary()}")

        render = check_render_sanity(project_dir)
        gates["render_sanity"] = "PASS" if render["passed"] else "FAIL"
        if not render["passed"]:
            passed = False
            print(f"  render_sanity: FAIL ({render['image_count']} image(s))")
        else:
            print(f"  render_sanity: PASS ({render['image_count']} image(s))")

        if meta.get("status") in {"prototype_unverified", "prototype", "failed", "blocked"}:
            passed = False
            gates["project_status"] = "FAIL"
            print(f"  project_status: FAIL ({meta.get('status')})")
        else:
            gates["project_status"] = "PASS"

        try:
            label = path.relative_to(ROOT)
        except ValueError:
            label = path
        results.append((label, passed, gates))

    print("=" * 78)
    print("VERIFY-ALL SUMMARY")
    any_fail = False
    for label, passed, status in results:
        flag = "PASS" if passed else "FAIL"
        any_fail |= not passed
        gates = "  ".join(f"{k}={v}" for k, v in status.items())
        print(f"  [{flag}] {label}   {gates}")
    print("=" * 78)
    print("RESULT:", "ALL ASSEMBLIES PASS" if not any_fail else "FAILURES PRESENT")
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
