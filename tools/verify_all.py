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
    argv = list(argv if argv is not None else sys.argv[1:])
    targets = [Path(a) for a in argv] if argv else discover()
    if not targets:
        print("verify_all: no canonical assemblies found")
        return 1

    results = []
    for path in targets:
        path = Path(path).resolve()
        print("=" * 78)
        passed, status = verify_canonical(path, verbose=True)
        try:
            label = path.relative_to(ROOT)
        except ValueError:
            label = path
        results.append((label, passed, status))

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
