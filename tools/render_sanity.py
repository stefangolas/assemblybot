"""Render-output sanity checks.

This catches the common "viewer technically rendered, but the result is blank or
all black" failure before a project can be published.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, pstdev
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.project_status import canonical_path, load_json, resolve_project


def project_images(project_dir: Path) -> list[Path]:
    meta = load_json(project_dir / "project.json", {})
    canonical = canonical_path(project_dir, meta)
    out_dir = project_dir / "out"
    if not out_dir.exists():
        return []
    if canonical:
        stem = canonical.stem
        imgs = sorted(out_dir.glob(f"{stem}_*.png"))
        if imgs:
            return imgs
    return sorted(out_dir.glob("*.png"))


def analyze_image(path: Path) -> dict[str, Any]:
    try:
        from PIL import Image
    except Exception as exc:  # noqa: BLE001
        return {
            "path": str(path),
            "passed": path.exists() and path.stat().st_size > 4096,
            "error": f"PIL unavailable; used file-size fallback: {exc}",
        }

    with Image.open(path) as im:
        rgb = im.convert("RGB").resize((64, 64))
        raw = rgb.tobytes()
        pixels = list(zip(raw[0::3], raw[1::3], raw[2::3]))
    lum = [0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in pixels]
    channels = [v for px in pixels for v in px]
    lum_mean = mean(lum)
    lum_std = pstdev(lum)
    ch_std = pstdev(channels)
    lum_range = max(lum) - min(lum)
    passed = lum_mean > 8.0 and lum_range > 12.0 and (lum_std > 4.0 or ch_std > 8.0)
    return {
        "path": str(path),
        "passed": passed,
        "size_bytes": path.stat().st_size,
        "luminance_mean": round(lum_mean, 2),
        "luminance_std": round(lum_std, 2),
        "luminance_range": round(lum_range, 2),
        "channel_std": round(ch_std, 2),
    }


def check_project(project: str | Path) -> dict[str, Any]:
    project_dir = resolve_project(project)
    images = project_images(project_dir)
    reports = [analyze_image(p) for p in images]
    passed = bool(reports) and all(r.get("passed") for r in reports)
    return {
        "project": project_dir.name,
        "passed": passed,
        "image_count": len(reports),
        "images": reports,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check project render images for blank/all-black output.")
    parser.add_argument("target", help="project id/dir or one or more PNGs", nargs="+")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    if len(args.target) == 1 and not str(args.target[0]).lower().endswith(".png"):
        report = check_project(args.target[0])
    else:
        image_reports = [analyze_image(Path(t)) for t in args.target]
        report = {
            "project": None,
            "passed": bool(image_reports) and all(r.get("passed") for r in image_reports),
            "image_count": len(image_reports),
            "images": image_reports,
        }

    if args.as_json:
        print(json.dumps(report, indent=2))
    else:
        print(f"render_sanity: {'PASS' if report['passed'] else 'FAIL'} ({report['image_count']} image(s))")
        for image in report["images"]:
            flag = "PASS" if image.get("passed") else "FAIL"
            print(f"  {flag}: {image.get('path')}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
