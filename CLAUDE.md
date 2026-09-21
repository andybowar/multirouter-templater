# CLAUDE.md — context for AI agents working on this repo

Read this before changing anything in `app/`. Most of the non-obvious decisions
here are forced by physics or by a measurement, not by taste, and several of
them look wrong until you know why.

## What this is

A local web app that generates 3D-printable tenon templates for a **JDS
Multi-Router**. The user enters a desired tenon; the app computes the template
profile that will cause the machine's stylus to produce it, adds a
PantoRouter-style taper for fit adjustment, and exports STL/STEP/3MF/DXF.

The hard part is not the CAD. It is the transformation
`desired tenon -> required template`. Get that wrong and the app confidently
produces a part that cuts the wrong joint.

## The ground truth — do not break this

The Multi-Router linkage is **1:1**, so the bit centerline path is a pure
translation of the stylus centerline path:

```
stylus center path = template edge offset OUTWARD by r_stylus
tenon surface      = bit center path   offset INWARD  by r_bit

=> template_dim = tenon_dim + (bit_dia - stylus_dia)
```

This is **validated against a physical factory template**. A 0.500" × 2.000"
tenon cut with a 0.500" bit uses a factory template measuring
0.625" × 2.125", and the formula reproduces both numbers exactly.

**That measurement is the regression test.** Any change to `geometry.py` or
`model.py` must keep this true:

```
bit 0.500, tenon_width 0.500, tenon_length 2.000
  -> profile at nominal == 0.6250" x 2.1250"
```

If a refactor breaks that, the refactor is wrong. Do not "fix" the expected
value.

## Three things that look like bugs but are not

### 1. Tenon width is an input, not `bit_dia`

An earlier version collapsed these — it assumed the tenon is always cut with
the same bit that cut the mortise. **It is not.** The user may cut a 0.500"
mortise with a 0.500" bit and then cut the tenon with a 0.250" bit.

The consequence is the part that actually matters:

```
tenon end radius = tenon_width / 2      <-- NOT bit_dia / 2
```

The mortise is a single-pass stadium, so its ends have radius
`mortise_bit / 2 = tenon_width / 2`. The tenon must match *the mortise*,
whatever bit is in the router for the tenon cut. Using `bit_dia / 2` puts the
wrong radius on the tenon ends and the joint will not close.

A uniform offset of a stadium is still a stadium, so the template's end radius
works out to exactly half the template width. The profile is **always** a
stadium. `SlotOverall(length, width)` is therefore always the right primitive.

### 2. A bit smaller than the stylus makes the template smaller than the tenon

With `bit_dia < stylus_dia` the offset goes negative. A 0.500" tenon cut with a
0.250" bit needs a **0.375" × 1.875"** profile — smaller than the finished
tenon. In the plan preview the green tenon outline then sits *outside* the
orange template outline. Correct, not inverted.

### 3. The taper direction is forced by contact physics

Layer 3 is a frustum: **full size where it meets layer 2, tapering inward
toward its free top face.** Do not flip this.

A cylindrical bearing riding a drafted face contacts wherever the engaged span
is *largest*. If the profile were largest at its free top face, the bearing
would always contact that top edge and the depth setting would do nothing at
all. Tapering inward puts contact at the bearing's deepest engaged circle, so
bearing depth selects the cross-section.

The stylus bearing is flush with its rod and the same diameter (no protruding
stud), which is why nothing can bottom out ahead of the bearing and nothing
behind it is wide enough to touch the profile at a shallower setting.

## Measured constants

All in `app/config.py`. Everything there is either measured off the machine /
a factory template, or a stated design decision. **Nothing is assumed
silently** — the project brief explicitly required that.

| Constant | Value | Source |
|---|---|---|
| `STYLUS_DIA` | 0.375" | measured with calipers; bearing flush with rod |
| linkage | 1:1 | machine design (not 2:1 like a PantoRouter) |
| layer 1 | 3.500 × 1.000 × 0.250" | factory template, rectangle |
| layer 2 | 3.250 × 0.750 × 0.125" | factory template, stadium |
| layer 3 | 0.250" thick | design decision — hosts the taper |
| `TAPER_RANGE` | 0.020" total | design decision |

Layers 1 and 2 are the holder interface and are **fixed**. Only layer 3 is
computed. Overall thickness is 0.625"; the factory template is 0.500".

Taper defaults give ±0.010" over 0.250", i.e. 2.29° draft, 12.5:1 reduction,
**1/16" of bearing travel = 0.005" of tenon**. Nominal sits at mid-depth so the
operator can correct in either direction after a test cut.

## Units

Geometry is built in **millimetres** (`inches * 25.4`) so STEP carries correct
units into Fusion 360 and STL/3MF land correctly in a slicer. The UI, the
`Spec` dataclass and the setup sheet are all in **inches**. `MM` in `model.py`
is the only conversion point — keep it that way.

## Traps that have already bitten

- **`Path.read_text()` needs `encoding="utf-8"`.** The default is the locale
  encoding, which is ASCII in some environments, and `index.html` contains
  UTF-8 characters. This crashed page loads until fixed. Reproduce with
  `LC_ALL=C LANG=C ./run.sh`.
- **`&times;` is invalid in standalone SVG.** It works in-browser (SVG inside
  HTML is parsed with HTML rules) but breaks strict XML parsers. Use numeric
  entities (`&#215;`, `&#176;`) in anything emitted into an SVG string.
- **Engraved text must be mirrored.** It sits on the z=0 face, which is read
  looking along +Z, and in that view global +X points *left*. `model.py`
  mirrors the text block about `Plane.YZ`. Verify visually after any change —
  backwards text is easy to ship and embarrassing.
- **The server has no autoreload.** `run.sh` runs plain uvicorn. Restart after
  editing Python; the browser will otherwise show stale behaviour.
- **Sectioning exactly at a layer interface** picks up the wrong layer. Offset
  by a small epsilon when verifying cross-sections.

## Why the loft is exact

`loft([stadium_base, stadium_top], ruled=True)` is a true uniform offset at
every height, not an approximation:

- the straight flanks interpolate linearly, giving planar drafted faces;
- both end arcs share the same centre (`±(L-W)/2` is invariant under a uniform
  offset), so they interpolate to cones.

So a cross-section at any height is exactly the nominal stadium offset inward
by `δ(z)`. This has been verified numerically; see below.

## Verifying a change

Run these after touching geometry. They are quick and they catch real errors.

```sh
# 1. Factory calibration - must print 0.6250 x 2.1250
.venv/bin/python -c "
from app.geometry import Spec
s = Spec(bit_dia=0.5, tenon_width=0.5, tenon_length=2.0)
print(s.prof_wid_nom, s.prof_len_nom)"
```

```sh
# 2. Cross-sections vs predicted tenon, at several heights.
#    section() the solid, subtract spec.offset, compare to spec.tenon_delta().
#    Include a MISMATCHED pair (bit 0.250 / width 0.500) - that case is the one
#    a naive refactor breaks.
```

```sh
# 3. Watertight check - parse the binary STL, every edge must appear exactly
#    twice, zero degenerate triangles.
```

```sh
# 4. Frontend logic without a browser: extract the inline <script>, stub
#    document/fetch, and drive refresh() under node. Check for NaN/undefined in
#    the generated SVG. `node --check` catches syntax errors.
```

Previews can be rasterised for visual inspection with
`qlmanage -t -s 1500 -o <dir> file.svg` on macOS. A headless Firefox screenshot
of the live page does **not** work in this sandbox.

## Layout

```
app/config.py     measured constants + design decisions. Single source of truth.
app/geometry.py   Spec: transfer function, taper math, validation. Pure, no CAD.
app/model.py      build123d solid, engraving, STL/STEP/3MF/DXF export.
app/report.py     the printable setup sheet.
app/main.py       FastAPI routes (compute / export / report).
app/static/       single-page UI, no external dependencies, no CDN.
```

`geometry.py` has no build123d import and should stay that way — it makes the
math testable without the CAD kernel.

## Scope discipline

The engraving on the back face is deliberately **two lines only** (router bit,
resulting tenon) so the template can be identified on a shelf. The full
adjustment table belongs on the setup sheet, not the part. It was previously
five lines and the user cut it back; do not re-expand it.

The preview diagram is deliberately dimensioned with **only** profile-at-base,
profile-at-top and resulting tenon. Holder-interface dimensions were removed on
request. The dimension stack sorts by size so the nesting stays correct when
the template comes out smaller than the tenon.

## State of validation

Verified in software: the factory calibration point, cross-sections at multiple
heights (including mismatched bits), STL watertightness, engraving mirroring,
every validation error path, and the frontend render logic.

**Not verified: nothing here has cut wood.** Reproducing the factory template
is a strong calibration point, not proof. The first printed template should be
measured across the profile base with calipers before it is trusted.

## Open hardware questions

- The part is 0.625" thick against the factory 0.500", so the bearing bracket
  needs 0.125" more protrusion than the user is used to.
- Bearing protrusion is currently set "by feel". At 12.5:1 that is survivable,
  but a caliper reading against a flat reference face on the bracket would make
  the adjustment table exact rather than advisory.
- When the profile is narrower than layer 2 (0.750"), over-inserting the
  bearing makes it contact **layer 2** instead and cut oversize. The app warns
  per-configuration; there is no physical stop on the part.
