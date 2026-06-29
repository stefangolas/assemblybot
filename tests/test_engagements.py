import unittest

from ontology.engagements import (
    ENGAGEMENTS,
    EngagementUse,
    IntendedFreedom,
    IntegralClosure,
    TemplateComposition,
    derive_kinematics,
    derive_template,
)
from ontology.templates import TEMPLATES


def checks(template):
    return [(c.predicate, c.a, c.b, c.severity) for c in template.checks]


def relations(template):
    return [(r.type, r.a, r.b, r.value) for r in template.enforce]


def load_paths(template):
    return [(e.frm, e.to, tuple(e.via_checks)) for e in template.load_paths]


def closures(template):
    return [(c.kind, c.mechanism, c.detail) for c in template.closure]


class EngagementCatalogTests(unittest.TestCase):
    def test_engagements_keep_kinematics_and_loads_separate(self):
        raceway = ENGAGEMENTS["RACEWAY"]

        self.assertEqual(raceway.kinematics.frame_slot, "a")
        self.assertEqual(raceway.kinematics.constrained, ("tx", "ty", "rx", "ry"))
        self.assertEqual(raceway.kinematics.free, ("tz", "rz"))
        self.assertEqual(raceway.load.carries, ("radial_force", "bending_moment"))
        self.assertFalse(hasattr(raceway, "holds"))
        self.assertFalse(hasattr(raceway, "closure_role"))

    def test_planar_seat_relation_uses_face_features(self):
        seat = ENGAGEMENTS["PLANAR_SEAT"]

        self.assertEqual(seat.relation, "oppose_and_seat")
        self.assertEqual(seat.relation_features, ("face", "face"))

    def test_intended_open_freedoms_are_checked_in_composition_frame(self):
        comp = TemplateComposition(
            id="raceway_probe",
            engagements=(EngagementUse("RACEWAY", "journal", "bearing"),),
            closure=IntegralClosure("raceway"),
            intended_open=(IntendedFreedom("journal", ("rz",)),),
        )

        summary = derive_kinematics(comp)

        self.assertEqual(set(summary.constrained_by_frame["journal"]), {"tx", "ty", "rx", "ry"})
        self.assertEqual(summary.intended_open_violations, ())

    def test_intended_open_violation_blocks_template_derivation(self):
        comp = TemplateComposition(
            id="bad_raceway_probe",
            engagements=(EngagementUse("RACEWAY", "journal", "bearing"),),
            closure=IntegralClosure("raceway"),
            intended_open=(IntendedFreedom("journal", ("rx",)),),
        )

        with self.assertRaisesRegex(ValueError, "intended-open freedom violated"):
            derive_template(comp)


class DerivedTemplateGoldenTests(unittest.TestCase):
    def test_journal_supported_by_bearing_matches_legacy_template_shape(self):
        template = TEMPLATES["journal_supported_by_bearing"]

        self.assertEqual(set(template.participants), {"journal", "bearing"})
        self.assertEqual(template.participants["journal"].family, "cylindrical")
        self.assertEqual(template.participants["journal"].polarity, "insert")
        self.assertEqual(template.participants["journal"].role, "shaft journal")
        self.assertEqual(template.participants["bearing"].family, "cylindrical")
        self.assertEqual(template.participants["bearing"].polarity, "receiver")
        self.assertEqual(template.participants["bearing"].role, "bearing inner bore")

        self.assertEqual(relations(template), [("coaxial", "journal.axis", "bearing.axis", None)])
        self.assertEqual(
            checks(template),
            [
                ("radial_fit", "journal", "bearing", "hard_geometry"),
                ("axial_overlap", "journal", "bearing", "hard_geometry"),
            ],
        )
        self.assertEqual(
            closures(template),
            [("integral", "raceway", "bearing raceway supports the shaft radially")],
        )
        self.assertEqual(
            load_paths(template),
            [("journal", "bearing", ("radial_fit", "axial_overlap"))],
        )
        self.assertEqual(template.result.type, "revolute")
        self.assertEqual(template.result.axis_slot, "journal")


if __name__ == "__main__":
    unittest.main()
