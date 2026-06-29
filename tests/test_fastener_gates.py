import unittest

from assembly.verify_canonical import _fastener_pattern_count_issues
from ontology.schema_v2 import PartDefinition
from ontology.templates import TEMPLATES


def part(part_number, *, mount_fastener_count=1):
    return PartDefinition(
        part_number,
        {"catalog_family": "test_part"},
        normalized_parameters={"mount_fastener_count": mount_fastener_count},
    )


class FastenerPatternGateTests(unittest.TestCase):
    def test_single_placeholder_cannot_satisfy_declared_four_fastener_mount(self):
        lib = {
            "holder": part("holder", mount_fastener_count=4),
            "plate": part("plate"),
            "f1": part("f1"),
        }
        inst = [
            TEMPLATES["fastened_face_mount"].bind({
                "mounted": "holder.mount_face",
                "support": "plate.bottom_face",
                "fastener": "f1.thread",
            })
        ]

        issues = _fastener_pattern_count_issues(inst, lib)

        self.assertEqual(
            issues,
            ["fastened_face_mount on ['holder', 'plate']: 1/4 fasteners instantiated"],
        )

    def test_full_sibling_fastener_set_satisfies_declared_mount_count(self):
        lib = {
            "holder": part("holder", mount_fastener_count=4),
            "plate": part("plate"),
            **{f"f{i}": part(f"f{i}") for i in range(1, 5)},
        }
        inst = [
            TEMPLATES["fastened_face_mount"].bind({
                "mounted": "holder.mount_face",
                "support": "plate.bottom_face",
                "fastener": f"f{i}.thread",
            })
            for i in range(1, 5)
        ]

        self.assertEqual(_fastener_pattern_count_issues(inst, lib), [])


if __name__ == "__main__":
    unittest.main()
