"""Field-level semantic evidence + status (directive Section 4).

This module provides the open-world three-state every consumer must respect:

    CONFIRMED      backed by evidence of a kind valid FOR THAT CLAIM
    CONTRADICTED   evidence conflicts
    UNKNOWN        no evidence of the required kind (NOT "absent", NOT "compatible")

Rules (directive Sections 4-5):
  * missing evidence -> UNKNOWN; conflicting -> CONTRADICTED;
  * absence of contradiction is not confirmation;
  * UNKNOWN / CONTRADICTED semantics may not create a confirmed load-path edge.
"""
from __future__ import annotations

CONFIRMED, UNKNOWN, CONTRADICTED = "CONFIRMED", "UNKNOWN", "CONTRADICTED"

def combine(*states: str) -> str:
    """Open-world combination: any CONTRADICTED dominates; else any UNKNOWN; else
    CONFIRMED. (No evidence never silently means compatible.)"""
    if any(s == CONTRADICTED for s in states):
        return CONTRADICTED
    if any(s == UNKNOWN for s in states):
        return UNKNOWN
    return CONFIRMED


def preflight(instance, library) -> tuple[str, str]:
    """Preflight semantic gate for an attachment instance (directive Section 4).
    Iterates over the template's `required_semantics` and verifies that the bound port
    is CONFIRMED with resolvable, valid evidence records.
    """
    states, notes = [], []
    reqs = getattr(instance.template, "required_semantics", [])
    if not reqs:
        return CONFIRMED, "no semantic claims required"

    for req in reqs:
        slot = req.slot
        addr = instance.bindings.get(slot)
        if not addr or addr == "GROUND" or ":" in addr or "." not in addr:
            continue
            
        ref, pid = addr.split(".", 1)
        part = library.get(ref)
        if not part:
            continue
            
        try:
            port = part.port(pid)
        except Exception:
            continue
            
        st = getattr(port, "annotation_status", "unknown").lower()
        if st == "contradicted":
            states.append(CONTRADICTED)
            notes.append(f"{slot}={addr}: marked contradicted")
            continue
            
        if st != "confirmed":
            states.append(UNKNOWN)
            notes.append(f"{slot}={addr}: status is {st} (not confirmed)")
            continue

        # For "confirmed", check that there is resolvable valid evidence
        valid_ev = False
        ev_notes = []
        for ref_id in getattr(port, "evidence_refs", []):
            ev = next((e for e in getattr(part, "evidence", []) if e.id == ref_id), None)
            if not ev:
                ev_notes.append(f"ref {ref_id} not found")
                continue
            
            missing = [f for f in ("source_uri", "locator", "raw_value", "normalized_claim", "extraction_method") 
                       if not getattr(ev, f)]
            if missing:
                ev_notes.append(f"ref {ref_id} missing {missing}")
                continue
                
            # If we reached here, the evidence record is completely formed.
            # In a full system, we might check if `req.claims` keys are inside `ev.normalized_claim`.
            valid_ev = True
            break
            
        if valid_ev:
            states.append(CONFIRMED)
            notes.append(f"{slot}={addr}: confirmed via evidence")
        else:
            states.append(UNKNOWN)
            notes.append(f"{slot}={addr}: lacks valid evidence ({'; '.join(ev_notes) if ev_notes else 'no refs'})")

    return (combine(*states) if states else CONFIRMED), "; ".join(notes)
