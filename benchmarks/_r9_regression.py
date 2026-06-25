"""r9 regression suite (directive Section 13): permanent invariants for the incident
where an M4 shoulder screw was reported attached to an M3-clearance bracket hole that
had been annotated 'M4 tapped' from a CAD diameter.

Invariants locked in:
  * thread semantics are a SEMANTIC claim -- a CAD cylinder cannot confirm them;
  * pose/fit does NOT imply attachment (no load-path edge from a kinematic fit);
  * UNKNOWN evidence cannot become PASS; CONTRADICTED blocks the interface;
  * a clearance hole needs a real NUT for closure; a tapped hole's tap is the closure;
  * UNKNOWN/CONTRADICTED edges cannot hold a body to ground.

Run: PYTHONPATH=. python benchmarks/_r9_regression.py  (exits nonzero on any failure)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from ontology.ports import EngagementPort
from ontology import ports_match as PM
from ontology import semantics as SEM
from ontology import load_path as LP
from ontology.templates import TEMPLATES
from ontology.schema_v2 import PartDefinition, EvidenceRecord

ROOT = Path(__file__).resolve().parent.parent
LIBV2 = ROOT / "lib".replace("lib", "library_v2")

_fails = []
def check(name, cond, got=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{('  -> ' + str(got)) if not cond else ''}")
    if not cond:
        _fails.append(name)


# ---- port builders ------------------------------------------------------------

def ext_thread(desig="M4x0.7", pitch=0.7, major=4.0, status="confirmed", source="catalog_field"):
    th = {"standard": "ISO_metric", "designation": desig, "pitch_mm": pitch,
          "handedness": "right", "major_diameter_mm": {"min": major - 0.2, "max": major}}
    return EngagementPort("scr", "threaded", "external",
                          {"axis": {"origin": [0, 0, 0], "direction": [0, 0, 1]},
                           "axial_interval_mm": {"min": 0, "max": 5}, "thread": th},
                          annotation_status=status,
                          evidence_refs=["ev1"] if status == "confirmed" else [])

def int_thread(desig="M4x0.7", pitch=0.7, status="confirmed", source="catalog_field"):
    th = {"standard": "ISO_metric", "designation": desig, "pitch_mm": pitch, "handedness": "right"}
    return EngagementPort("tap", "threaded", "internal",
                          {"axis": {"origin": [0, 0, 0], "direction": [0, 0, 1]},
                           "axial_interval_mm": {"min": 0, "max": 5}, "thread": th},
                          annotation_status=status,
                          evidence_refs=["ev1"] if status == "confirmed" else [])

def clearance(ir, status="confirmed"):
    return EngagementPort("hole", "cylindrical", "receiver",
                          {"axis": {"origin": [0, 0, 0], "direction": [0, 0, 1]},
                           "radial_interval_mm": {"min": ir, "max": ir},
                           "axial_interval_mm": {"min": 0, "max": 3.2}, "material_side": "inside"},
                          annotation_status=status,
                          evidence_refs=["ev1"] if status == "confirmed" else [])


# ---- predicate-level invariants -----------------------------------------------

def predicate_tests():
    print("predicate-level:")
    # 1. M4 external versus M3 clearance -> CONTRADICTED
    r = PM.clearance_pass_through(ext_thread(), clearance(1.7))
    check("m4_external_vs_m3_clearance -> FAIL/CONTRADICTED", r.verdict == "FAIL", r.verdict)

    # 2. M4 external versus unknown cylindrical hole -> UNKNOWN
    r = PM.clearance_pass_through(ext_thread(), clearance(2.5, status="unknown"))
    check("m4_external_vs_unknown_cyl_hole -> UNKNOWN", r.verdict == "UNKNOWN", r.verdict)

    # 3. M4 external versus M4 internal -> PASS
    r = PM.thread_match(ext_thread(), int_thread())
    check("m4_external_vs_confirmed_m4_internal -> PASS", r.verdict == "PASS", r.verdict)
    
    # 4. M4 external versus M4 clearance -> PASS
    r = PM.clearance_pass_through(ext_thread(), clearance(2.5, status="confirmed"))
    check("m4_external_vs_m4_clearance -> PASS", r.verdict == "PASS", r.verdict)




def preflight_tests():
    print("semantic preflight:")
    # UNKNOWN evidence cannot become PASS
    scr = _stub_with(ext_thread(), "A")
    tap = _stub_with(int_thread(status="nominal"), "B")
    inst = TEMPLATES["shoulder_screw_into_tapped_support"].bind({"screw": "A.scr", "support": "B.tap"})
    st, _ = SEM.preflight(inst, {"A": scr, "B": tap})
    check("unknown_thread_evidence -> not CONFIRMED", st != SEM.CONFIRMED, st)

    # CONTRADICTED semantic blocks the interface
    tap_c = _stub_with(int_thread(status="contradicted"), "B")
    inst_c = TEMPLATES["shoulder_screw_into_tapped_support"].bind({"screw": "A.scr", "support": "B.tap"})
    st_c, _ = SEM.preflight(inst_c, {"A": scr, "B": tap_c})
    check("contradicted_thread_evidence -> CONTRADICTED", st_c == SEM.CONTRADICTED, st_c)

# ---- load-path invariants -----------------------------------------------------

def _mini_eval(instances, library, extra_places=None):
    places = {"A": {"R": [[1,0,0],[0,1,0],[0,0,1]], "t_mm": [0,0,0]},
              "B": {"R": [[1,0,0],[0,1,0],[0,0,1]], "t_mm": [0,0,0]},
              "N": {"R": [[1,0,0],[0,1,0],[0,0,1]], "t_mm": [0,0,0]}}
    if extra_places:
        places.update(extra_places)
    return LP.evaluate(instances, library, places, ground=["B"])

def loadpath_tests():
    print("load-path:")
    # 6. a pose/fit instance (revolute_fit_on_journal) creates NO load-path edge
    fit = TEMPLATES["revolute_fit_on_journal"].bind({"rotor": "A.bore", "journal": "B.sh"})
    libfit = {"A": _stub_with(EngagementPort("bore","cylindrical","receiver",
                {"axis":{"origin":[0,0,0],"direction":[0,0,1]},"radial_interval_mm":{"min":2.5,"max":2.5},
                 "axial_interval_mm":{"min":-4.5,"max":4.5},"material_side":"inside"})),
              "B": _stub_with(EngagementPort("sh","cylindrical","insert",
                {"axis":{"origin":[0,0,0],"direction":[0,0,1]},"radial_interval_mm":{"min":2.5,"max":2.5},
                 "axial_interval_mm":{"min":-8,"max":8},"material_side":"outside"}))}
    rep = _mini_eval([fit], libfit)
    check("revolute_fit creates NO load-path edge", len(rep.edges) == 0, len(rep.edges))

    # 4. clearance hole WITHOUT a real nut -> closure missing -> screw UNHELD
    scr = _stub_with(ext_thread()); scr.part_number = "A"
    sup = _stub_with(clearance(2.5))                  # roomy clearance, but no nut modeled
    libno = {"A": scr, "B": sup}
    nonut = TEMPLATES["shoulder_screw_through_support_with_nut"].bind(
        {"screw": "A.scr", "support": "B.hole", "nut": "p_missing_nut.t"})
    rep = _mini_eval([nonut], libno)
    held = rep.bodies["A"].state
    check("clearance hole + NO nut -> screw UNHELD", held == LP.UNHELD, LP._NAME[held])

    # 5. clearance hole WITH a real modeled nut -> screw can be HELD_CONFIRMED
    sup_yes = _stub_with(clearance(2.5), ev=[EvidenceRecord(
        id="ev1", source_type="drawing", raw_value="M5 clearance", locator="x", source_uri="x",
        normalized_claim={"hole_type": "clearance", "bore_diameter": "5.0"}, extraction_method="human")])
    libyes = {"A": scr, "B": sup_yes, "N": _stub_with(int_thread(), pn="N")}
    withnut = TEMPLATES["shoulder_screw_through_support_with_nut"].bind(
        {"screw": "A.scr", "support": "B.hole", "nut": "N.tap"})
    rep = _mini_eval([withnut], libyes)
    held = rep.bodies["A"].state
    check("clearance hole + real nut -> screw HELD_CONFIRMED", held == LP.CONFIRMED, LP._NAME[held])
    if held != LP.CONFIRMED:
        print(rep.text())


def _stub_with(port, pn="X", ev=None):
    """Minimal PartDefinition holding one port (schema_v2 requires no placement)."""
    if ev is None and port.annotation_status == "confirmed":
        ev = [EvidenceRecord(id="ev1", source_type="catalog_field", source_uri="http", locator="row",
                             raw_value="M4", normalized_claim={"thread": "M4"}, extraction_method="human")]
    return PartDefinition(part_number=pn, classification={}, ports=[port], evidence=ev or [])


# ---- complete-chain invariant on the REAL parts -------------------------------

def chain_tests():
    print("complete chain (real library_v2 parts):")
    def load(stem):
        return PartDefinition.from_json(json.loads((LIBV2 / f"{stem}.json").read_text()))
    lib = {"p_idl": load("SHTF20S3M100-5"), "p_scr": load("96654A131"),
           "p_brk": load("FALBS-H40-bracket")}
    places = {"p_idl": {"R": [[0,0,-1],[0,1,0],[1,0,0]], "t_mm": [0,40,-7.5]},
              "p_scr": {"R": [[1,0,0],[0,1,0],[0,0,1]], "t_mm": [0,40,-0.5]},
              "p_brk": {"R": [[1,0,0],[0,1,0],[0,0,1]], "t_mm": [0,0,-11.7]}}
    # bearing rides shoulder: PASS (fit only)
    fit = TEMPLATES["revolute_fit_on_journal"].bind({"rotor": "p_idl.bore", "journal": "p_scr.shoulder"})
    fr = fit.evaluate(lib, places)
    check("bearing_on_shoulder fit -> PASS",
          all(r.verdict == "PASS" for r in fr.results), [str(r) for r in fr.results])
    # screw into the CURRENT (M4-tapped) bracket -> PASSES (used to be M3 clearance and contradict)
    sc = TEMPLATES["shoulder_screw_into_tapped_support"].bind(
        {"screw": "p_scr.thread", "support": "p_brk.axle_hole"})
    sr = sc.evaluate(lib, places)
    check("screw_to_current_bracket -> passes",
          all(r.verdict == "PASS" for r in sr.results), [str(r) for r in sr.results])
    # idler chain is now held to ground through this bracket
    rep = LP.evaluate([sc], lib, places, ground=["p_brk"])
    check("idler chain IS held (screw CONFIRMED)", rep.bodies["p_scr"].state == LP.CONFIRMED,
          LP._NAME[rep.bodies["p_scr"].state])
    if rep.bodies["p_scr"].state != LP.CONFIRMED:
        print(rep.text())


if __name__ == "__main__":
    predicate_tests()
    preflight_tests()
    loadpath_tests()
    chain_tests()
    print()
    if _fails:
        print(f"FAILED {len(_fails)}: {_fails}")
        sys.exit(1)
    print("ALL r9 REGRESSION INVARIANTS HOLD")
