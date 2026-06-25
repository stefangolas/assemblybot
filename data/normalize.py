"""Spec-string normalization (Section 3, "Spec strings need normalization").

The spec table the VLM reads off the page is untyped attribute/value text:
a length arrives as the literal "16 mm", a thread as "M5 x 0.8 mm". This layer
sits between the raw read and the typed `params`. The raw read is ALWAYS kept
verbatim alongside the normalized form so every typed value is auditable.
"""
from __future__ import annotations

import re

_NUM = re.compile(r"[-+]?\d*\.?\d+")


def to_mm(s: str) -> float | None:
    """'8 mm' -> 8.0 ; '0.5"' / '1/2 in' -> mm. Returns None if unparseable."""
    if s is None:
        return None
    s = s.strip()
    # fraction inches e.g. '1/2"' or '1/2 in'
    frac = re.match(r"^\s*(\d+)\s*/\s*(\d+)\s*(in|\"|inch)?", s)
    if frac and ("in" in s or '"' in s):
        return round(float(frac.group(1)) / float(frac.group(2)) * 25.4, 4)
    m = _NUM.search(s)
    if not m:
        return None
    val = float(m.group())
    low = s.lower()
    if "mm" in low:
        return val
    if "in" in low or '"' in s or "inch" in low:
        return round(val * 25.4, 4)
    return val  # assume already mm if no unit


def thread_token(s: str) -> str | None:
    """'M5 x 0.8 mm' -> 'M5x0.8' ; '1/4"-20' -> '1/4-20'. A comparable token."""
    if s is None:
        return None
    s = s.strip()
    m = re.match(r"\s*M\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)", s)
    if m:
        return f"M{m.group(1)}x{m.group(2)}"
    m = re.match(r'\s*(\d+/\d+|\d+(?:\.\d+)?)\s*"?\s*-\s*(\d+)', s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return s.replace(" ", "") or None


def normalize_spec(raw: dict, mapping: dict[str, tuple[str, str]]) -> dict:
    """raw: verbatim {label: value}. mapping: {raw_label: (out_key, kind)} where
    kind is 'mm' | 'thread' | 'str' | 'float'. Unmapped labels are ignored."""
    out: dict = {}
    for label, (key, kind) in mapping.items():
        if label not in raw:
            continue
        v = raw[label]
        if kind == "mm":
            out[key] = to_mm(v)
        elif kind == "thread":
            out[key] = thread_token(v)
        elif kind == "float":
            m = _NUM.search(str(v))
            out[key] = float(m.group()) if m else None
        else:
            out[key] = v
    return out
