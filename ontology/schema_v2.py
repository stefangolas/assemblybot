"""v2 part schema (Section 8) -- immutable PartDefinition + placed PartInstance.

The hard separation the v1 library kept violating (`1277N16` had +-66 mm assembly
Z baked into "part" geometry): a PartDefinition is IMMUTABLE by part number /
configuration / revision and carries NO assembly placement. All poses live in a
PartInstance's single transform (Section 0, layer 3 vs 4; Hard Rule per migration
step A.5: "a part definition has no assembly placement").

Coexists with v1 ontology.schema.Part -- rungs 0/1 still load v1 until migrated.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .ports import EngagementPort, PortGroup


@dataclass
class EvidenceRecord:
    """Field-level provenance (Section 7). A single part-wide confidence score is
    insufficient; every normalized claim cites where it came from."""
    id: str
    source_type: str         # catalog_category|configurator|product_page|drawing|datasheet|cad|derived|inferred
    raw_value: object = None
    normalized_claim: dict = field(default_factory=dict)   # {target_path, value, unit}
    source_uri: str = ""
    locator: str = ""
    extraction_method: str = ""   # dom|vision|pdf_text|cad_measurement|formula|human
    confidence: float = 0.0
    notes: str = ""

    def to_json(self) -> dict:
        return {"id": self.id, "source_type": self.source_type, "raw_value": self.raw_value,
                "normalized_claim": self.normalized_claim, "source_uri": self.source_uri,
                "locator": self.locator, "extraction_method": self.extraction_method,
                "confidence": self.confidence, "notes": self.notes}

    @staticmethod
    def from_json(d: dict) -> "EvidenceRecord":
        return EvidenceRecord(id=d["id"], source_type=d["source_type"],
                              raw_value=d.get("raw_value"),
                              normalized_claim=d.get("normalized_claim", {}),
                              source_uri=d.get("source_uri", ""), locator=d.get("locator", ""),
                              extraction_method=d.get("extraction_method", ""),
                              confidence=d.get("confidence", 0.0), notes=d.get("notes", ""))


@dataclass
class PartDefinition:
    """Immutable catalog part (Section 8). Geometry is millimetres in ONE local
    frame; CAD is metres. No placement field exists by construction."""
    part_number: str
    classification: dict                    # {catalog_family, broader_families, aliases}
    source: dict = field(default_factory=dict)            # {url, retrieved_at}
    raw_spec: dict = field(default_factory=dict)
    normalized_parameters: dict = field(default_factory=dict)
    cad: dict = field(default_factory=dict)               # {source_uri, gltf_uri, units}
    part_frame: dict = field(default_factory=lambda: {"units": "millimetre", "drawing_to_cad": {}})
    ports: list = field(default_factory=list)             # list[EngagementPort]
    port_groups: list = field(default_factory=list)       # list[PortGroup]
    annotation_status: dict = field(default_factory=lambda: {"overall": "partial", "expected_ports": {}})
    evidence: list = field(default_factory=list)          # list[EvidenceRecord]
    provenance: dict = field(default_factory=dict)
    schema_version: int = 2

    def port(self, pid: str) -> EngagementPort:
        for p in self.ports:
            if p.id == pid:
                return p
        raise KeyError(f"part {self.part_number} has no port {pid!r}")

    def to_json(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "part_number": self.part_number,
            "classification": self.classification,
            "source": self.source,
            "raw_spec": self.raw_spec,
            "normalized_parameters": self.normalized_parameters,
            "cad": self.cad,
            "part_frame": self.part_frame,
            "ports": [p.to_json() for p in self.ports],
            "port_groups": [g.to_json() for g in self.port_groups],
            "annotation_status": self.annotation_status,
            "evidence": [e.to_json() for e in self.evidence],
            "provenance": self.provenance,
        }

    def save(self, path) -> None:
        with open(path, "w") as fh:
            json.dump(self.to_json(), fh, indent=2)

    @staticmethod
    def from_json(d: dict) -> "PartDefinition":
        if d.get("schema_version") != 2:
            raise ValueError(f"PartDefinition.from_json: expected schema_version 2, "
                             f"got {d.get('schema_version')!r} ({d.get('part_number')})")
        if "frame" in d and "part_frame" not in d:
            raise ValueError("this looks like a v1 Part (has `frame`); load via the v1 adapter")
        return PartDefinition(
            part_number=d["part_number"], classification=d["classification"],
            source=d.get("source", {}), raw_spec=d.get("raw_spec", {}),
            normalized_parameters=d.get("normalized_parameters", {}),
            cad=d.get("cad", {}), part_frame=d.get("part_frame", {}),
            ports=[EngagementPort.from_json(p) for p in d.get("ports", [])],
            port_groups=[PortGroup.from_json(g) for g in d.get("port_groups", [])],
            annotation_status=d.get("annotation_status", {"overall": "partial"}),
            evidence=[EvidenceRecord.from_json(e) for e in d.get("evidence", [])],
            provenance=d.get("provenance", {}),
        )


@dataclass
class PartInstance:
    """A reference to a PartDefinition + ONE assembly transform (Section 0 layer 4).
    Every assembly pose lives here, never in the definition. `transform` is the
    {R, t_mm} consumed identically by the math and the viewer (Section 3)."""
    ref: str
    part_number: str
    transform: dict = field(default_factory=lambda: {"R": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "t_mm": [0, 0, 0]})
    grounded: bool = False

    def to_json(self) -> dict:
        return {"ref": self.ref, "part_number": self.part_number,
                "transform": self.transform, "grounded": self.grounded}

    @staticmethod
    def from_json(d: dict) -> "PartInstance":
        return PartInstance(ref=d["ref"], part_number=d["part_number"],
                            transform=d.get("transform", {"R": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                                                          "t_mm": [0, 0, 0]}),
                            grounded=d.get("grounded", False))
