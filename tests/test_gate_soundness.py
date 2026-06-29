import json
from pathlib import Path
import unittest

from assembly.verify_canonical import (
    _expected_engagement_issues,
    _fastener_pattern_count_issues,
    _unattached_contact_issues_from_depths,
)
from ontology.ports import PortGroup
from ontology.schema_v2 import PartDefinition
from ontology.templates import TEMPLATES


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


def part(part_number, *, group_count=0, expected_ports=None):
    return PartDefinition(
        part_number,
        {"catalog_family": "test_part"},
        port_groups=[
            PortGroup("mount_pattern", "repeated_ports", [{"port": f"h{i}"} for i in range(1, group_count + 1)])
        ] if group_count else [],
        annotation_status={"overall": "confirmed", "expected_ports": expected_ports or {}},
    )


class GateSoundnessTests(unittest.TestCase):
    def test_b2_pattern_count_is_derived_from_bound_port_group(self):
        fx = fixture("under_instantiated_pattern.json")
        lib = {
            "holder": part("holder", group_count=4),
            "plate": part("plate"),
            "f1": part("f1"),
        }
        inst = [
            TEMPLATES["fastened_face_mount"].bind({
                "mounted": "holder:mount_pattern",
                "support": "plate.bottom_face",
                "fastener": "f1.thread",
                "receiver": "plate.thread_1",
            })
        ]

        self.assertEqual(_fastener_pattern_count_issues(inst, lib), [fx["expected_issue"]])

    def test_b3_expected_mount_must_be_realized(self):
        fx = fixture("missing_expected_engagement.json")
        lib = {
            "holder": part("holder", expected_ports={
                "primary_mount": {
                    "port": "mount_face",
                    "template": "fastened_face_mount",
                    "required": True,
                }
            }),
            "shaft": part("shaft"),
        }
        inst = [
            TEMPLATES["journal_supported_by_bearing"].bind({
                "journal": "shaft.journal",
                "bearing": "holder.bearing_bore",
            })
        ]

        self.assertEqual(_expected_engagement_issues(inst, lib), [fx["expected_issue"]])

    def test_b4_structural_contact_without_attachment_fails(self):
        fx = fixture("unattached_contact.json")
        depths = {("holder", "plate"): 0.25}

        self.assertEqual(
            _unattached_contact_issues_from_depths(
                depths,
                structural_refs={"holder", "plate"},
                non_structural=set(),
                attached_ref_pairs=set(),
            ),
            [fx["expected_issue"]],
        )

    def test_b4_structural_contact_with_attachment_passes(self):
        depths = {("holder", "plate"): 0.25}

        self.assertEqual(
            _unattached_contact_issues_from_depths(
                depths,
                structural_refs={"holder", "plate"},
                non_structural=set(),
                attached_ref_pairs={("holder", "plate")},
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
