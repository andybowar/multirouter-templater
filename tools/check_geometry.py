#!/usr/bin/env python3
"""The factory calibration point, as a script.

A 0.500" x 2.000" tenon cut with a 0.500" bit uses a factory template
measuring 0.625" x 2.125". That is a measurement off a real part, not a
convention, so it is the one thing every change has to keep true.

Pure arithmetic - no build123d - so CI can run it on a bare Python.
"""

from __future__ import annotations

import sys
from math import atan, degrees
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.geometry import Spec, dim_label, file_stem, spec_from_inputs  # noqa: E402

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

print("taper endpoints bracket nominal - 1/3 below, 2/3 above, of 0.070\"")
check("tenon delta, bearing flush", s.tenon_delta(0.0), -0.070 / 3)
check("tenon delta, fully inserted", s.tenon_delta(s.profile_thk), +2 * 0.070 / 3)
check("tenon delta is zero at nominal depth", s.tenon_delta(s.nominal_depth), 0.0)
check("nominal depth", s.nominal_depth, 0.0833333, tol=1e-6)
check("range above nominal", s.taper_up, 0.0466667, tol=1e-6)
check("range below nominal", s.taper_down, 0.0233333, tol=1e-6)
check("up + down = the whole range", s.taper_up + s.taper_down, 0.070)
# The draft angle is base-to-top over the profile depth, so moving nominal
# inside the frustum must NOT change it. That is the whole reason the extra
# headroom is free in control resolution - if this ever couples, the trade has
# silently come back.
check("draft angle", s.draft_deg, 7.9696, tol=1e-3)
check("reduction ratio", s.reduction_ratio, 3.5714, tol=1e-3)
check("bearing travel per 0.005\" of tenon", s.travel_per_5thou, 0.017857, tol=1e-5)
off_centre = Spec(bit_dia=0.5, tenon_width=0.5, tenon_length=2.0)
check("draft is independent of where nominal sits",
      off_centre.draft_deg,
      degrees(atan(off_centre.taper_range / 2.0 / off_centre.profile_thk)),
      tol=1e-12)

# Nominal no longer lands on a sixteenth, so the table has to carry it as its
# own row or the marker vanishes while every number still looks right.
rows = s.adjustment_table()
nom = [r for r in rows if r["is_nominal"]]
start = [r for r in rows if r["is_start"]]
if len(nom) == 1 and abs(nom[0]["depth"] - s.nominal_depth) < 1e-9:
    print("  ok    adjustment table carries exactly one nominal row, at 0.083\"")
else:
    print(f"  FAIL  {len(nom)} nominal rows in the adjustment table")
    FAILURES.append("adjustment table nominal row")
if len(start) == 1 and abs(start[0]["depth"] - s.profile_thk) < 1e-9:
    print("  ok    ...and START HERE is still the deepest row")
else:
    print(f"  FAIL  START HERE is not the deepest row")
    FAILURES.append("adjustment table start row")
if rows == sorted(rows, key=lambda r: r["depth"]):
    print("  ok    ...and the rows are still in depth order")
else:
    print("  FAIL  adjustment table rows out of order")
    FAILURES.append("adjustment table order")

# The headroom this was raised for: at full insertion, after the profile prints
# 0.010" under and the slot cuts a mortise SLOT_CLEARANCE oversize, there has to
# be fat left to shave. It was 0.0095" before and that was too thin to trust.
PRINT_UNDER = 0.010
headroom = s.taper_up - PRINT_UNDER - s.slot_clearance
if headroom > 0.025:
    print(f"  ok    {headroom:.4f}\" of fat left at full insertion after a "
          f"{PRINT_UNDER:.3f}\" print error and the slot's clearance")
else:
    print(f"  FAIL  only {headroom:.4f}\" of headroom at full insertion")
    FAILURES.append("insufficient upward headroom")

print("mortise slot - the slot IS the guide, so it is the pin's swept path")
ms = Spec(bit_dia=0.5, tenon_width=0.5, tenon_length=2.0, mortise_slot=True)
CLR = ms.slot_clearance
SLACK = ms.slot_slack
# slot = mortise offset inward by (tenon_width - pin_dia)/2, opened up by the
# fit clearance in both directions and then given extra LENGTH on purpose.
check("slot width = pin + clearance", ms.slot_wid, 0.1920 + CLR)
check("slot length = (L - W) + pin + clearance + slack",
      ms.slot_len, 1.5 + 0.1920 + CLR + SLACK)
check("slot sunk through the profile only", ms.slot_depth, 0.2500)
#   end wall = (prof_len_top - slot_len)/2 = (2.10167 - 1.74000)/2
check("slot leaves wall in the profile", ms.slot_wall, 0.180833, tol=1e-5)
# The slack stretches the slot's core segment past the profile's, so the wall is
# no longer uniform. One number is still reported, and it must be the governing
# one - the thinnest, on the axis at the two ends.
check("profile core segment", ms.prof_len_top - ms.prof_wid_top, 1.5000)
check("slot core segment", ms.slot_len - ms.slot_wid, 1.5000 + SLACK)
check("reported wall is the wall at the ends",
      (ms.prof_len_top - ms.slot_len) / 2.0, ms.slot_wall, tol=1e-12)
check("...which is thinner than the wall at the sides, by half the slack",
      (ms.prof_wid_top - ms.slot_wid) / 2.0 - ms.slot_wall, SLACK / 2, tol=1e-12)
assert ms.ok, ms.errors

# What it actually cuts: the pin roams the slot offset inward by pin/2, the bit
# centre follows 1:1, and the mortise is that offset outward by tenon_width/2.
check("mortise width it cuts", (ms.slot_wid - ms.pin_dia) + ms.tenon_width, 0.5 + CLR)
check("mortise length it cuts",
      (ms.slot_len - ms.pin_dia) + ms.tenon_width, 2.0 + CLR + SLACK)
check("...which is what Spec reports", ms.mortise_wid, 0.5 + CLR)
check("...and likewise", ms.mortise_len, 2.0 + CLR + SLACK)

# The mortise is deliberately MORE oversize in length than in width. The taper
# moves both tenon dimensions by the same delta, so whichever dimension binds
# first sets the tenon; the slack makes sure that is never the length. The joint
# is glued on the cheeks - length is end grain and holds nothing - so the width
# is the dimension the bearing depth is kept free to serve.
check("mortise is slacker in length than in width",
      (ms.mortise_len - 2.0) - (ms.mortise_wid - 0.5), SLACK)
check("bearing depth that grows the tenon to meet the mortise WIDTH",
      ms.tenon_delta(ms.slot_match_depth), CLR)
# At that depth the tenon clears the mortise ends by the whole of the slack.
check("tenon still clears the mortise ends there",
      ms.mortise_len - (2.0 + ms.tenon_delta(ms.slot_match_depth)), SLACK)

# THE invariant this all exists for. The operator creeps DOWN from fully
# inserted, where the tenon is too fat in both directions. As the tenon shrinks,
# the length has to come free BEFORE the width does - otherwise the last of the
# shaving is being spent on the ends instead of the cheeks.
d_length_frees = CLR + SLACK   # tenon delta at which the tenon clears end to end
d_width_fits = CLR             # tenon delta at which the cheeks meet the mortise
if d_length_frees > d_width_fits:
    print("  ok    length comes free before the width does - the width binds last")
else:
    print(f"  FAIL  length still binding at the width's fit point")
    FAILURES.append("length binds before width")

# ...and it has to survive the real world, not just the model. A 1.750" tenon
# measured 0.028" of mortise-length deficit against prediction, 0.018" of it
# asymmetric. The default slack must still leave the width binding last after
# losing that much.
MEASURED_ASYM_LOSS = 0.018
if SLACK - MEASURED_ASYM_LOSS > 0:
    print(f"  ok    survives the measured {MEASURED_ASYM_LOSS:.3f}\" asymmetric loss "
          f"with {SLACK - MEASURED_ASYM_LOSS:.3f}\" to spare")
else:
    print(f"  FAIL  {SLACK:.3f}\" of slack does not cover a measured "
          f"{MEASURED_ASYM_LOSS:.3f}\" loss")
    FAILURES.append("slack under measured loss")

# The slack is an input now, and zero is a legal value for it - the one input
# where it is, because it is a margin rather than a size.
none = Spec(bit_dia=0.5, tenon_width=0.5, tenon_length=2.0, mortise_slot=True,
            slot_slack=0.0)
check("slack=0 reverts to a uniform offset", none.slot_len - none.slot_wid, 1.5000)
check("...and a uniformly oversize mortise",
      none.mortise_len - 2.0, none.mortise_wid - 0.5)
check("slack is honoured as an input",
      Spec(bit_dia=0.5, tenon_width=0.5, tenon_length=2.0,
           mortise_slot=True, slot_slack=0.02).mortise_len, 2.0 + CLR + 0.02)

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

print("dimension labels do not lie about the input")
# 1.1875 is 1-3/16" - an ordinary tenon length. At three decimals it renders
# "1.188", a different number, which reads as the app having changed the input.
for value, want in ((1.1875, "1.1875"), (0.5, "0.500"), (2.0, "2.000"),
                    (2.125, "2.125"), (1.03125, "1.03125"), (0.0625, "0.0625"),
                    (10.0, "10.000"), (-0.125, "-0.125")):
    got = dim_label(value)
    if got == want:
        print(f"  ok    {value!r} -> {got}")
    else:
        print(f"  FAIL  {value!r} -> {got}, want {want}")
        FAILURES.append(f"dim_label {value}")

# The filename is the one place rounding is worse than cosmetic: two different
# templates sharing a name land on top of each other in the downloads folder.
# The pairs that matter are shop fractions against their three-decimal
# roundings, which is what actually collided. Five decimals is the resolution
# by design - values closer together than that are not different templates.
near = [1.1875, 1.188, 1.21875, 1.219, 1.03125, 1.031]
stems = {file_stem(Spec(bit_dia=0.5, tenon_width=0.5, tenon_length=L))
         for L in near}
if len(stems) == len(near):
    print(f"  ok    {len(near)} fractions and their roundings give "
          f"{len(stems)} distinct filenames")
else:
    print(f"  FAIL  filename collision among {near}: {sorted(stems)}")
    FAILURES.append("file_stem collision")

# Round values must keep their old three-decimal form, or every existing
# filename churns for no reason.
check_stem = file_stem(Spec(bit_dia=0.5, tenon_width=0.5, tenon_length=2.0))
if check_stem == "multirouter_tenon_0p500x2p000_bit0p500":
    print("  ok    round values keep their existing filename")
else:
    print(f"  FAIL  filename churned: {check_stem}")
    FAILURES.append("file_stem churn")

print("input bounds are enforced")
for bad in ({"bit_dia": 0}, {"tenon_width": -1}, {"taper_range": 9},
            {"slot_slack": -0.01}, {"slot_slack": 9}):
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
