"""Generate simple sheet-stock panels from dimensions.

This is for geometrically parameterized sheet parts: guard panels, covers,
flat shims, and blank plates whose shape is fully defined by width, height,
thickness, material, and optional through-hole coordinates. Vendor CAD is not
needed for these stock sheets; catalog evidence is procurement/material proof.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cadquery as cq
from cadquery import exporters
import trimesh


def _panel(spec: dict) -> cq.Workplane:
    width = float(spec["width_mm"])
    height = float(spec["height_mm"])
    thickness = float(spec["thickness_mm"])
    corner_radius = float(spec.get("corner_radius_mm", 0.0))

    wp = cq.Workplane("XY")
    if corner_radius > 0:
        solid = wp.rect(width, height).vertices().fillet(corner_radius).extrude(thickness)
    else:
        solid = wp.box(width, height, thickness, centered=(True, True, False))

    holes = spec.get("holes", [])
    if holes:
        solid = solid.faces(">Z").workplane()
        for hole in holes:
            solid = solid.pushPoints([(float(hole["x_mm"]), float(hole["y_mm"]))]).hole(float(hole["diameter_mm"]))
    return solid


def generate(spec: dict, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    part_number = spec["part_number"]
    step_path = out_dir / f"{part_number}.step"
    stl_path = out_dir / f"{part_number}.stl"
    glb_path = out_dir / f"{part_number}.glb"
    json_path = out_dir / f"{part_number}.json"

    solid = _panel(spec)
    exporters.export(solid, str(step_path))
    exporters.export(solid, str(stl_path))
    mesh = trimesh.load_mesh(stl_path)
    mesh.export(glb_path)

    definition = {
        "schema_version": 2,
        "part_number": part_number,
        "classification": {
            "catalog_family": "parameterized_sheet_panel",
            "broader_families": ["sheet_stock", "guard_panel"],
            "aliases": spec.get("aliases", []),
        },
        "source": {
            "url": spec.get("source_url", "generated:sheet-panel-template"),
            "retrieved_at": spec.get("retrieved_at", ""),
            "note": "Generated from sheet-stock dimensions; vendor sheet CAD is not used.",
        },
        "raw_spec": spec,
        "normalized_parameters": {
            "width_mm": float(spec["width_mm"]),
            "height_mm": float(spec["height_mm"]),
            "thickness_mm": float(spec["thickness_mm"]),
            "material": spec.get("material", "unspecified sheet stock"),
            "hole_count": len(spec.get("holes", [])),
        },
        "cad": {
            "source_uri": str(step_path).replace("\\", "/"),
            "gltf_uri": str(glb_path).replace("\\", "/"),
            "units": "metre",
        },
        "part_frame": {
            "units": "millimetre",
            "drawing_to_cad": {"scale": 1.0, "rotation": "identity", "translation": [0, 0, 0]},
            "note": "Panel local frame: width along X, height along Y, thickness extrudes from Z=0 to +thickness.",
        },
        "ports": [
            {
                "id": "front_face",
                "family": "planar",
                "polarity": "contact",
                "geometry": {
                    "plane": {"origin": [0, 0, float(spec["thickness_mm"])], "normal": [0, 0, 1]},
                    "boundary_uv_mm": {
                        "outer": [
                            [-float(spec["width_mm"]) / 2, -float(spec["height_mm"]) / 2],
                            [float(spec["width_mm"]) / 2, -float(spec["height_mm"]) / 2],
                            [float(spec["width_mm"]) / 2, float(spec["height_mm"]) / 2],
                            [-float(spec["width_mm"]) / 2, float(spec["height_mm"]) / 2],
                        ],
                        "holes": [],
                    },
                    "material_side": "negative_normal",
                },
                "semantic_aliases": ["panel_face", "guard_face"],
                "annotation_status": "confirmed",
                "evidence_refs": ["ev_params"],
            }
        ],
        "port_groups": [],
        "annotation_status": {"overall": "partial", "expected_ports": {"mount_holes": "from spec holes when supplied"}},
        "evidence": [
            {
                "id": "ev_params",
                "source_type": "derived",
                "raw_value": spec,
                "normalized_claim": {"target_path": "normalized_parameters", "value": "see normalized_parameters"},
                "source_uri": spec.get("source_url", "generated:sheet-panel-template"),
                "extraction_method": "formula",
                "confidence": 1.0,
                "notes": "Geometry is fully determined by explicit sheet dimensions and optional hole coordinates.",
            }
        ],
        "provenance": {
            "generated_by": "tools/generate_sheet_panel.py",
            "policy": "parameterized sheet-stock geometry; do not fetch vendor sheet CAD",
        },
    }
    json_path.write_text(json.dumps(definition, indent=2), encoding="utf-8")
    return {"step": str(step_path), "stl": str(stl_path), "glb": str(glb_path), "definition": str(json_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate parameterized sheet panel CAD and library JSON.")
    parser.add_argument("spec_json", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("cad/generated_sheets"))
    args = parser.parse_args()
    spec = json.loads(args.spec_json.read_text(encoding="utf-8"))
    print(json.dumps(generate(spec, args.out_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
