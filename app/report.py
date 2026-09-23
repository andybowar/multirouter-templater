"""Human-readable setup sheet that ships alongside the model."""

from __future__ import annotations

from .geometry import Spec


def build_report(spec: Spec) -> str:
    d = spec
    lines: list[str] = []
    w = lines.append

    w("=" * 68)
    w("  JDS MULTI-ROUTER - TAPERED TENON TEMPLATE")
    w("=" * 68)
    w("")
    w("TARGET TENON")
    w(f'  Tenon width              {d.tenon_width:.4f}"   (= mortise width)')
    w(f'  Tenon length             {d.tenon_length:.4f}"')
    w(f'  End radius               {d.tenon_width / 2:.4f}"   (= half the width)')
    w("")
    w(f'  Router bit               {d.bit_dia:.4f}"')
    w(f'  Bit that cut the MORTISE {d.tenon_width:.4f}"   (implied by the width)')
    w("")
    w("  These two need not match. The mortise is a single-pass stadium, so")
    w("  its end radius is half its width, and the tenon must match that")
    w("  whatever bit is in the router for this cut.")
    w("")
    w("  Tenon depth (protrusion from the shoulder) is set by the machine's")
    w("  plunge, not by this template.")
    w("")
    w("MACHINE CONSTANTS USED")
    w(f'  Stylus bearing diameter  {d.stylus_dia:.4f}"')
    w("  Linkage ratio            1:1 (stylus travel = bit travel)")
    w("  Bearing form             flush with the rod, same diameter, no stud")
    w("")
    w("  Transfer function:  template_dim = tenon_dim + (bit_dia - stylus_dia)")
    w(f'                      offset per dimension = {d.offset:+.4f}"')
    w("")
    w("GUIDE PROFILE (layer 3)")
    w(f'  Depth                    {d.profile_thk:.4f}"')
    w(f'  Draft angle              {d.draft_deg:.2f} deg per side, tapering inward toward the top')
    w("")
    w(f'  At the base (deepest)    {d.prof_wid_base:.4f}" x {d.prof_len_base:.4f}"')
    w(f'  At nominal (mid-depth)   {d.prof_wid_nom:.4f}" x {d.prof_len_nom:.4f}"')
    w(f'  At the free top face     {d.prof_wid_top:.4f}" x {d.prof_len_top:.4f}"')
    w(f'  End radius at nominal    {d.prof_wid_nom / 2:.4f}"')
    w("")
    if d.mortise_slot:
        w("MORTISE SLOT (guides the cut - no stop collars needed)")
        w(f'  Slot                     {d.slot_wid:.4f}" x {d.slot_len:.4f}", stadium, '
          f'{d.slot_depth:.3f}" deep')
        w(f'  Pin                      {d.pin_dia:.4f}" - the stepped-down end of the stylus')
        w(f'  Pin travel               {d.slot_travel:.4f}"')
        w(f'  Wall left in the profile {d.slot_wall:.3f}" all round - the slot and the')
        w('                           profile are concentric stadiums, so it is uniform')
        w("")
        w("  Turn the stylus around so the stepped pin faces the template, fit a")
        w(f'  {d.tenon_width:.4f}" bit - the mortise width - and drop the pin into the')
        w("  slot. The slot bounds the cut in both directions, so run the table")
        w("  to the ends of the slot and let it stop you. No stop collars.")
        w("")
        w("MORTISE THIS SLOT CUTS")
        w(f'  Mortise                  {d.mortise_wid:.4f}" x {d.mortise_len:.4f}"')
        w(f'  Tenon at nominal         {d.tenon_width:.4f}" x {d.tenon_length:.4f}"')
        w(f'  Difference               +{d.slot_clearance:.4f}" in both directions')
        w("")
        w("  The slot is a slip fit, so the pin is free to wander by the fit")
        w("  clearance and all of it lands in the workpiece. It is applied to")
        w("  the length as well as the width on purpose: the taper moves both")
        w("  tenon dimensions together, so only a uniformly oversize mortise can")
        w("  be matched by dialling the tenon up to meet it.")
        w("")
        if d.slot_match_depth <= d.profile_thk:
            w(f'  So the tenon wants to finish around {d.slot_match_depth:.3f}" of bearing depth')
            w(f'  rather than the {d.profile_thk / 2:.3f}" nominal. Still start fully inserted at')
            w(f'  {d.profile_thk:.3f}" and creep down to it - that figure is where you are')
            w("  heading, not where you begin.")
        else:
            w("  WARNING: that is more than the taper can add back to the tenon.")
            w("  The joint will stay loose. Reduce the slot clearance.")
        w("")
    w("HOLDER INTERFACE (fixed - matches the factory template)")
    w(f'  Layer 1  base plate      {d.base_len:.3f}" x {d.base_wid:.3f}" x {d.base_thk:.3f}" thick, square corners')
    w(f'  Layer 2  middle step     {d.mid_len:.3f}" x {d.mid_wid:.3f}" x {d.mid_thk:.3f}" thick, stadium')
    w(f'  Layer 3  guide profile   see above, {d.profile_thk:.3f}" thick')
    if d.mortise_slot:
        w("                           slotted - see above")
    w(f'  Overall thickness        {d.total_thk:.3f}"')
    w("")
    w("FIT ADJUSTMENT")
    w("")
    w("  Set the bearing depth by how far its edge sits below the template's")
    w("  free top face. Flush = 0. Deeper = bigger tenon.")
    w("")
    w("  START FULLY INSERTED, against the widest part of the profile. That is")
    w("  the biggest tenon this template can cut, so the first one will be too")
    w("  fat - which is the point. Every correction from there takes wood off.")
    w("  Start at nominal instead and a tenon that comes out under size is")
    w("  scrap: you cannot put wood back.")
    w("")
    w("     bearing depth      tenon size        tenon W x L")
    w("     -------------      ----------        -----------")
    for row in spec.adjustment_table():
        if row["is_start"]:
            marker = "  <-- START HERE"
        elif row["is_nominal"]:
            marker = "  <-- nominal"
        else:
            marker = ""
        delta = "nominal" if row["is_nominal"] else f'{row["delta"]:+.4f}"'
        w(
            f'     {row["depth_label"]:>6}             {delta:>9}'
            f'         {row["tenon_width"]:.4f} x {row["tenon_length"]:.4f}{marker}'
        )
    w("")
    w(f'  {_travel_phrase(d)}')
    w(f'  Reduction ratio {_ratio(d.reduction_ratio)}:1 - a 0.010" error in setting')
    w(f'  the bearing is worth only {0.010 / d.reduction_ratio:.4f}" on the tenon.')
    w("")
    w("  Workflow: cut the first tenon with the bearing fully inserted, try it,")
    w("  then withdraw the bearing a little and recut the SAME tenon. Repeat")
    w("  until it goes. You are creeping down onto the fit from above, so a")
    w("  test piece is never wasted.")
    w("")
    w("  Once it fits, note the depth and leave the bearing there for the rest")
    w("  of the joints in that batch.")
    w("")

    if spec.warnings:
        w("NOTES AND CAUTIONS")
        for msg in spec.warnings:
            for i, seg in enumerate(_wrap(msg, 64)):
                w(("  * " if i == 0 else "    ") + seg)
            w("")

    w("PRINTING")
    w("  Orientation   Base plate (engraved face) flat on the bed, profile")
    w("                pointing up. The taper shrinks as it rises, so it is")
    w("                self-supporting. No supports anywhere.")
    w("  Nozzle        0.4 mm")
    w("  Layer height  0.12 mm")
    w("  Perimeters    5-6. The guide edge should be solid wall, not infill.")
    w("  Infill        40% minimum; 100% if the profile is under 0.30\" wide.")
    w("  Material      PETG to start. Tougher than PLA against a rolling")
    w("                bearing, and dimensionally stable enough at this size.")
    w("  Files         Exported in MILLIMETERS. STL/3MF drop straight into a")
    w("                slicer; STEP imports into Fusion 360 with units intact.")
    w("")
    w("  Before trusting the first template, print it and measure the guide")
    w("  profile across its base with calipers. It should read")
    w(f'  {d.prof_wid_base:.4f}" x {d.prof_len_base:.4f}". Any error there')
    w("  transfers 1:1 to the tenon, and is what the taper is for.")
    w("")
    w("=" * 68)
    return "\n".join(lines)


def _ratio(x: float) -> str:
    return f"{x:.1f}".removesuffix(".0")


def _travel_phrase(d: Spec) -> str:
    t = d.travel_per_5thou
    sixteenths = t * 16
    if abs(sixteenths - round(sixteenths)) < 1e-6:
        n = round(sixteenths)
        frac = {1: "1/16", 2: "1/8", 3: "3/16", 4: "1/4"}.get(n, f"{n}/16")
        return f'{frac}" of bearing travel = 0.005" of tenon size.'
    return f'{t:.4f}" of bearing travel = 0.005" of tenon size.'


def _wrap(text: str, width: int) -> list[str]:
    words, out, cur = text.split(), [], ""
    for word in words:
        if cur and len(cur) + 1 + len(word) > width:
            out.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        out.append(cur)
    return out
