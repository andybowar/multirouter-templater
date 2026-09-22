#!/usr/bin/env python3
"""The factory calibration point, as a script.

A 0.500" x 2.000" tenon cut with a 0.500" bit uses a factory template
measuring 0.625" x 2.125". That is a measurement off a real part, not a
convention, so it is the one thing every change has to keep true.

Pure arithmetic - no build123d - so CI can run it on a bare Python.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.geometry import Spec, spec_from_inputs  # noqa: E402

FAILURES: list[str] = []


def check(label: str, got: float, want: float, tol: float = 1e-9) -> None:
    ok = abs(got - want) <= tol
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}: {got:.4f} (want {want:.4f})")
    if not ok:
        FAILURES.append(label)


print("factory template, 1/2\" tenon cut with a 1/2\" bit")
s = Spec(bit_dia=0.5, tenon_width=0.5, tenon_length=2.0)
check("profile width at nominal", s.prof_wid_nom, 0.6250)
check("profile length at nominal", s.prof_len_nom, 2.1250)

print("mismatched bit - 1/4\" bit, 1/2\" mortise")
m = Spec(bit_dia=0.25, tenon_width=0.5, tenon_length=2.0)
check("profile width at nominal", m.prof_wid_nom, 0.3750)
check("profile length at nominal", m.prof_len_nom, 1.8750)
check("tenon end radius follows the mortise", m.tenon_width / 2, 0.2500)

print("taper endpoints bracket nominal")
check("tenon delta, bearing flush", s.tenon_delta(0.0), -0.010)
check("tenon delta, fully inserted", s.tenon_delta(s.profile_thk), +0.010)

print("input bounds are enforced")
for bad in ({"bit_dia": 0}, {"tenon_width": -1}, {"taper_range": 9}):
    values = {"bit_dia": 0.5, "tenon_width": 0.5, "tenon_length": 2.0, **bad}
    try:
        spec_from_inputs(values)
    except ValueError as exc:
        print(f"  ok    rejected {bad}: {exc}")
    else:
        print(f"  FAIL  accepted {bad}")
        FAILURES.append(f"bounds {bad}")

if FAILURES:
    sys.exit(f"\n{len(FAILURES)} check(s) failed: {', '.join(FAILURES)}")
print("\nall checks passed")
