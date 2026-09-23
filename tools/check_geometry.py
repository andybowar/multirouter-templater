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

print("taper endpoints bracket nominal - half of the 0.045\" default range")
check("tenon delta, bearing flush", s.tenon_delta(0.0), -0.0225)
check("tenon delta, fully inserted", s.tenon_delta(s.profile_thk), +0.0225)

print("mortise slot - the slot IS the guide, so it is the pin's swept path")
ms = Spec(bit_dia=0.5, tenon_width=0.5, tenon_length=2.0, mortise_slot=True)
CLR = ms.slot_clearance
# slot = mortise offset inward by (tenon_width - pin_dia)/2, opened up by the
# fit clearance uniformly.
check("slot width = pin + clearance", ms.slot_wid, 0.1920 + CLR)
check("slot length = (L - W) + pin + clearance", ms.slot_len, 1.5 + 0.1920 + CLR)
check("slot sunk through the profile only", ms.slot_depth, 0.2500)
check("slot leaves wall in the profile", ms.slot_wall, 0.2013, tol=1e-3)
# One wall, not two: the profile and the slot are stadiums on the same core
# segment, so the gap is uniform and the end wall is not a separate number.
check("profile core segment", ms.prof_len_top - ms.prof_wid_top, 1.5000)
check("slot core segment", ms.slot_len - ms.slot_wid, 1.5000)
check("wall at the ends equals wall at the sides",
      (ms.prof_len_top - ms.slot_len) / 2.0, ms.slot_wall, tol=1e-12)
assert ms.ok, ms.errors

# What it actually cuts: the pin roams the slot offset inward by pin/2, the bit
# centre follows 1:1, and the mortise is that offset outward by tenon_width/2.
check("mortise width it cuts", (ms.slot_wid - ms.pin_dia) + ms.tenon_width, 0.5 + CLR)
check("mortise length it cuts", (ms.slot_len - ms.pin_dia) + ms.tenon_width, 2.0 + CLR)
check("...which is what Spec reports", ms.mortise_wid, 0.5 + CLR)
check("...and likewise", ms.mortise_len, 2.0 + CLR)

# The clearance has to be UNIFORM: the taper moves both tenon dimensions by the
# same delta, so a mortise oversize in one direction only could never be met.
check("mortise is uniformly oversize", ms.mortise_len - 2.0, ms.mortise_wid - 0.5)
check("bearing depth that grows the tenon to match", ms.tenon_delta(ms.slot_match_depth), CLR)

print("mortise slot - refuses to eat the guide profile")
narrow = Spec(bit_dia=0.2, tenon_width=0.5, tenon_length=2.0, mortise_slot=True)
if any("mortise slot" in e.lower() for e in narrow.errors):
    print("  ok    rejected a slot that would leave no wall")
else:
    print(f"  FAIL  accepted {narrow.slot_wall:.4f}\" of wall")
    FAILURES.append("narrow slot wall")

off = Spec(bit_dia=0.2, tenon_width=0.5, tenon_length=2.0)
if not any("mortise slot" in e.lower() for e in off.errors):
    print("  ok    same template without the slot is not blocked by it")
else:
    print("  FAIL  slot errors leak into an unslotted template")
    FAILURES.append("slot error leak")

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
