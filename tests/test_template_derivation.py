import unittest

from ontology.templates import TEMPLATES


def summarize(template_id):
    t = TEMPLATES[template_id]
    return {
        "participants": {
            name: {
                "family": p.family,
                "polarity": p.polarity,
                "is_fastener": p.is_fastener,
                "optional": p.optional,
            }
            for name, p in t.participants.items()
        },
        "enforce": [(r.type, r.a, r.b) for r in t.enforce],
        "checks": [(c.predicate, c.a, c.b, c.severity) for c in t.checks],
        "closure": [(c.kind, c.mechanism, c.detail) for c in t.closure],
        "load_paths": [(e.frm, e.to, tuple(e.via_checks)) for e in t.load_paths],
        "result": (t.result.type, t.result.axis_slot),
    }


SNAPSHOTS = {
    "radial_screw_against_cylindrical_target": {
        "participants": {
            "target": {"family": "cylindrical", "polarity": "insert", "is_fastener": False, "optional": False},
            "body_bore": {"family": "cylindrical", "polarity": "receiver", "is_fastener": False, "optional": False},
            "screw": {"family": "threaded", "polarity": "external", "is_fastener": True, "optional": False},
            "thread": {"family": "threaded", "polarity": "internal", "is_fastener": False, "optional": False},
        },
        "enforce": [("coaxial", "target.axis", "body_bore.axis"), ("coaxial", "screw.axis", "thread.axis")],
        "checks": [
            ("radial_fit", "target", "body_bore", "hard_geometry"),
            ("axial_overlap", "target", "body_bore", "hard_geometry"),
            ("thread_match", "screw", "thread", "hard_geometry"),
            ("thread_engagement", "screw", "thread", "hard_geometry"),
            ("tip_or_clamp_contact", "screw", "target", "hard_geometry"),
        ],
        "closure": [("fastener", "screw", "radial screw threads through body and contacts target")],
        "load_paths": [
            ("body_bore", "target", ("radial_fit", "axial_overlap", "thread_match", "thread_engagement", "tip_or_clamp_contact")),
            ("screw", "thread", ("thread_match", "thread_engagement")),
            ("screw", "target", ("tip_or_clamp_contact",)),
        ],
        "result": ("fixed", ""),
    },
    "clamp_keyed_hub_on_journal": {
        "participants": {
            "journal": {"family": "cylindrical", "polarity": "insert", "is_fastener": False, "optional": False},
            "hub": {"family": "cylindrical", "polarity": "receiver", "is_fastener": False, "optional": False},
            "clamp_fastener": {"family": "threaded", "polarity": "external", "is_fastener": True, "optional": False},
        },
        "enforce": [("coaxial", "journal.axis", "hub.axis")],
        "checks": [
            ("radial_fit", "journal", "hub", "hard_geometry"),
            ("axial_overlap", "journal", "hub", "hard_geometry"),
            ("tip_or_clamp_contact", "clamp_fastener", "journal", "hard_geometry"),
        ],
        "closure": [("fastener", "clamp_fastener", "clamp/keyed hub fastener provides torque-retaining closure")],
        "load_paths": [
            ("hub", "journal", ("radial_fit", "axial_overlap", "tip_or_clamp_contact")),
            ("clamp_fastener", "journal", ("tip_or_clamp_contact",)),
        ],
        "result": ("fixed", ""),
    },
    "pilot_clamped_hub_to_carrier": {
        "participants": {
            "pilot": {"family": "cylindrical", "polarity": "insert", "is_fastener": False, "optional": False},
            "hub": {"family": "cylindrical", "polarity": "receiver", "is_fastener": False, "optional": False},
            "hub_seat": {"family": "planar", "polarity": "contact", "is_fastener": False, "optional": False},
            "seat": {"family": "planar", "polarity": "contact", "is_fastener": False, "optional": False},
            "clamp_fastener": {"family": "threaded", "polarity": "external", "is_fastener": True, "optional": False},
        },
        "enforce": [("coaxial", "pilot.axis", "hub.axis"), ("oppose_and_seat", "hub_seat.face", "seat.face")],
        "checks": [
            ("radial_fit", "pilot", "hub", "hard_geometry"),
            ("axial_overlap", "pilot", "hub", "hard_geometry"),
            ("bounded_area_overlap", "hub_seat", "seat", "hard_geometry"),
            ("head_seat", "clamp_fastener", "hub_seat", "hard_geometry"),
        ],
        "closure": [("fastener", "clamp_fastener", "pulley is clamped to the carrier flange by real screws")],
        "load_paths": [
            ("hub", "pilot", ("radial_fit", "axial_overlap", "head_seat")),
            ("hub_seat", "seat", ("bounded_area_overlap", "head_seat")),
            ("clamp_fastener", "hub_seat", ("head_seat",)),
        ],
        "result": ("fixed", ""),
    },
    "fastened_face_mount": {
        "participants": {
            "mounted": {"family": "planar", "polarity": "contact", "is_fastener": False, "optional": False},
            "support": {"family": "planar", "polarity": "contact", "is_fastener": False, "optional": False},
            "fastener": {"family": "threaded", "polarity": "external", "is_fastener": True, "optional": False},
            "receiver": {"family": "threaded", "polarity": "internal", "is_fastener": False, "optional": False},
        },
        "enforce": [("oppose_and_seat", "mounted.face", "support.face"), ("coaxial", "fastener.axis", "receiver.axis")],
        "checks": [
            ("bounded_area_overlap", "mounted", "support", "hard_geometry"),
            ("thread_match", "fastener", "receiver", "hard_geometry"),
            ("thread_engagement", "fastener", "receiver", "hard_geometry"),
            ("head_seat", "fastener", "mounted", "hard_geometry"),
        ],
        "closure": [("fastener", "fastener", "modeled mounting fastener provides closure")],
        "load_paths": [
            ("mounted", "support", ("bounded_area_overlap", "thread_match", "thread_engagement", "head_seat")),
            ("fastener", "receiver", ("thread_match", "thread_engagement")),
            ("fastener", "mounted", ("head_seat",)),
        ],
        "result": ("fixed", ""),
    },
}


APPROVED_DELTAS = {
    "fastened_face_mount": [
        "requires modeled receiver thread via THREAD_MATE",
        "mount load path includes thread_match/thread_engagement as well as head_seat",
    ],
    "clamp_keyed_hub_on_journal": [
        "requires explicit tip_or_clamp_contact instead of a magic clamp_fastener token",
    ],
}


class TemplateDerivationTests(unittest.TestCase):
    def test_derived_templates_match_approved_snapshots(self):
        for template_id, expected in SNAPSHOTS.items():
            with self.subTest(template_id=template_id):
                self.assertEqual(summarize(template_id), expected)

    def test_intentional_deltas_are_recorded(self):
        self.assertIn("fastened_face_mount", APPROVED_DELTAS)
        self.assertTrue(APPROVED_DELTAS["fastened_face_mount"])


if __name__ == "__main__":
    unittest.main()
