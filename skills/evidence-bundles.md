# Skill: Evidence Bundles

Every exact configured catalog candidate is stored as a self-contained bundle so the lead can interpret it
without repeating the search. Keep **raw evidence**, **derived measurements**, and **interpretation** separate.

## Layout

```
candidate_evidence/
  <job-id>/
    <manufacturer>/
      <exact-or-candidate-pn>/
        manifest.json
        source/            product_page.*  drawing_original.*  specifications.*  bom.*  configurator_capture.*
        cad/               original.*  converted.*  bodies/
        measurements/      cad_features.json  notes.md
        renders/           iso.png  detail.png
        report.json
```

## Evidence categories

**Raw manufacturer evidence — never modify:** original drawing, original downloaded CAD, product-page
capture, specification table, BOM, configurator response.

**Derived — regenerable:** converted GLB, split bodies, screenshots, measured dimensions, rendered views,
extracted text.

**Candidate interpretation — not canonical:** likely feature meaning, likely compatibility, contradictions,
unresolved questions, confidence. (A worker reports these; only the lead promotes them to ontology.)

## Manifest (`manifest.json`)

Record: manufacturer; exact PN or candidate configuration; family; configuration tuple; source URLs;
retrieval time; file hashes; CAD status; drawing status; candidate status; known contradictions.

## Worker output contract (`report.json`, also returned to the lead)

```json
{
  "job_id": "",
  "status": "CANDIDATE_FOUND",
  "recommended_candidate": {"manufacturer": "", "part_number": "", "configuration": {}, "bundle_path": ""},
  "hard_requirements": {"confirmed": [], "contradicted": [], "unresolved": []},
  "evidence": {"drawing": "", "cad": "", "specification": "", "bom": ""},
  "cad_measurements": [],
  "alternatives": [],
  "risks": [],
  "recommended_next_action": ""
}
```

Allowed statuses: `CANDIDATE_FOUND`, `MULTIPLE_CANDIDATES`, `NO_MATCH`, `BLOCKED`, `RETRIEVAL_FAILED`.

- **Never return `CANDIDATE_FOUND` if a hard requirement is contradicted.**
- For any thread/hole interpretation, state which it is: **manufacturer-confirmed | CAD-measured |
  standard-derived | inferred | unresolved**. (CAD Ø alone is at most CAD-measured, never manufacturer-confirmed.)
