# CLAUDE.md — context for AI agents working on this repo

Read this before changing anything in `app/`. Most of the non-obvious decisions
here are forced by physics or by a measurement, not by taste, and several of
them look wrong until you know why.

## What this is

A **static web page**, deployed to GitHub Pages, that generates 3D-printable
tenon templates for a **JDS Multi-Router**. The user enters a desired tenon;
the app computes the template profile that will cause the machine's stylus to
produce it, adds a PantoRouter-style taper for fit adjustment, and exports
STL/STEP/3MF/DXF.

There is no server. The whole thing — geometry, OpenCascade, the exporters —
runs in the browser under PyScript/Pyodide. `app/` is the same package in both
places: it is copied into the site at build time, never forked. **Do not add a
second implementation of any of the math in JavaScript.**

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

## Four things that look like bugs but are not

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
stud) *on the tenon-cutting end*, which is why nothing can bottom out ahead of
the bearing and nothing behind it is wide enough to touch the profile at a
shallower setting. The stepped-down pin is on the opposite end — you turn the
stylus around to use it — so it is never between the bearing and the template.

### 4. The mortise slot's clearance is applied to the length too

```
slot_wid = pin_dia + SLOT_CLEARANCE
slot_len = (tenon_length - tenon_width) + pin_dia + SLOT_CLEARANCE
```

Putting clearance on the length looks like slop that will run every mortise
long. It does — by exactly `SLOT_CLEARANCE`, and that is the point.

The slot **guides** the cut; it does not set stop collars. So the pin is free
to wander by the clearance on *both* axes, and all of it lands in the
workpiece: the mortise comes out `SLOT_CLEARANCE` oversize in width and in
length. The tenon is then dialled up to meet it, and **the taper is a uniform
offset** — it moves both tenon dimensions by the same delta. A mortise that is
`+c` wide and `+0` long could not be matched at any bearing depth. A uniformly
oversize one is matched exactly, at `slot_match_depth`.

An earlier revision clearanced the width alone and documented the opposite
rule. That was correct while the slot only set stop collars. The moment the
slot became the guide it was wrong. `check_geometry.py` asserts the mortise is
uniformly oversize and that `tenon_delta(slot_match_depth) == SLOT_CLEARANCE`.

## Measured constants

All in `app/config.py`. Everything there is either measured off the machine /
a factory template, or a stated design decision. **Nothing is assumed
silently** — the project brief explicitly required that.

| Constant | Value | Source |
|---|---|---|
| `STYLUS_DIA` | 0.375" | measured with calipers; bearing flush with rod |
| `STYLUS_PIN_DIA` | 0.1920" | measured with calipers; the stepped-down end |
| linkage | 1:1 | machine design (not 2:1 like a PantoRouter) |
| layer 1 | 3.500 × 1.000 × 0.250" | factory template, rectangle |
| layer 2 | 3.250 × 0.750 × 0.125" | factory template, stadium |
| layer 3 | 0.250" thick | design decision — hosts the taper |
| `TAPER_RANGE` | 0.045" total | design decision |

Layers 1 and 2 are the holder interface and are **fixed**. Only layer 3 is
computed. Overall thickness is 0.625"; the factory template is 0.500".

Taper defaults give **±0.0225" of tenon over 0.250" of bearing travel**: 5.14°
of draft as `draft_deg` reports it, a 5.56:1 reduction, and 0.0278" of bearing
travel per 0.005" of tenon.

Nominal sits at mid-depth, but **the operator is told to start fully
inserted**, at the widest part of the profile — `is_start` in
`adjustment_table()`. Wood only comes off: a tenon that is still fat can be
recut, one that has gone under size is scrap. So the workflow creeps *down*
onto the fit and nominal is a reference point, not a starting point. Earlier
revisions told the operator to begin at nominal; that was wrong and it is the
kind of advice that reads as harmless. Do not put it back.

`TAPER_RANGE` has been raised twice — 0.020" to 0.040" in `6abdf75`, then to
0.045". **Every one of the figures above is derived from it**, so raising it
again means re-deriving the draft angle, the reduction ratio, the travel per
0.005", the profile-at-base dimension quoted in the README, and the expected
values in `check_geometry.py`. The 0.040" bump changed the constant alone and
left this file and the README stating half the real numbers for a while; don't
repeat that.

## The mortise slot

Optional, off by default. The stylus has a stepped-down pin on its far end;
you turn the stylus around and **that pin rides the slot while you cut the
mortise**. The slot is the guide — it bounds the cut on both axes, so there
are no stop collars in the workflow. (It was specified as a collar-setting aid
first; that is not what it is.)

Because the pin is confined to the slot for the whole cut, the slot is exactly
the pin's swept path — which is the mortise run through the same kind of
offset as everything else here:

```
slot = mortise stadium offset INWARD by (tenon_width - pin_dia) / 2

mortise length = tenon_length      (the tenon has to fit it)
mortise bit    = tenon_width       (already an input; single-pass stadium)

  => slot_wid = pin_dia            + SLOT_CLEARANCE
     slot_len = (tenon_length - tenon_width) + pin_dia + SLOT_CLEARANCE
```

It reuses the ground truth above rather than adding a second model: the same
fact that fixes the tenon's end radius (`mortise_bit = tenon_width`) is what
makes the length term correct. Same `SlotOverall` primitive as everything else,
and a uniform offset of a stadium is still a stadium.

`slot_travel` is the pin *centre's* range, `slot_len - pin_dia`. `mortise_wid`
/ `mortise_len` are what actually gets cut. `slot_match_depth` is the bearing
depth that grows the tenon by `SLOT_CLEARANCE` to meet it — see #4 above.

The slot is sunk from the free top face to the **base of the profile and no
further** — 0.250" deep. Layers 1 and 2 are the holder interface and are not
ours to cut into. If the pin turns out to need more engagement than that, the
answer is a thicker layer 3, not a deeper hole.

It costs wall out of the guide profile, measured at the top face because that
is the smallest cross-section. That wall works twice — the bearing rides its
outside cutting the tenon, the pin rides its inside cutting the mortise —
hence `MIN_SLOT_WALL_ERROR` / `_WARN`.

There is **one** wall, `slot_wall`, not a side wall and an end wall. Both
stadiums are built on the same core segment:

```
prof_len_top - prof_wid_top = tenon_length - tenon_width
slot_len     - slot_wid     = tenon_length - tenon_width
```

so the slot is a uniform offset of the profile and the gap is identical at the
sides, at the ends and around the arcs. It was briefly modelled as two numbers
with a warning each, which produced two near-identical banners describing one
measurement. It also means the wall is independent of tenon length — the
`tenon_length` terms cancel — so a slot that fits at one length fits at every
length for that bit.

## Units

Geometry is built in **millimetres** (`inches * 25.4`) so STEP carries correct
units into Fusion 360 and STL/3MF land correctly in a slicer. The UI, the
`Spec` dataclass and the setup sheet are all in **inches**. `MM` in `model.py`
is the only conversion point — keep it that way.

## Traps that have already bitten

- **`Path.read_text()` needs `encoding="utf-8"`.** The default is the locale
  encoding, which is ASCII in some environments, and the UI contains UTF-8
  characters. This crashed page loads back when a server read `index.html`.
  The static build copies bytes and no longer decodes anything, but the rule
  still applies to any Python that reads project text.
- **`&times;` is invalid in standalone SVG.** It works in-browser (SVG inside
  HTML is parsed with HTML rules) but breaks strict XML parsers. Use numeric
  entities (`&#215;`, `&#176;`) in anything emitted into an SVG string.
- **Engraved text must be mirrored.** It sits on the z=0 face, which is read
  looking along +Z, and in that view global +X points *left*. `model.py`
  mirrors the text block about `Plane.YZ`. Verify visually after any change —
  backwards text is easy to ship and embarrassing.
- **The site is a copy, so edits need a rebuild.** `run.sh` assembles `_site/`
  and serves that. Editing `app/` or `web/` does nothing until you restart it.
  Hard-reload the page too — Pyodide caches aggressively.
- **The browser has no fonts.** OpenCascade in WebAssembly cannot find a
  system font and cannot ask fontconfig for one, so an engraving raised by
  name silently produces nothing. `model.FONT_PATHS` exists for this: the page
  appends the bundled `DejaVuSans.ttf` and build123d is given `font_path`.
  Keep `FONT_PATHS` ahead of `FONT_CANDIDATES`.
- **The CAD kernel runs on the page's main thread**, so an export freezes the
  tab while it works. The UI paints its "Generating…" label and yields a frame
  before calling in. Do not remove that yield.
- **Nothing may load the CAD kernel implicitly.** See below.
- **Pin OCP.wasm.** `web/vendor/ocp_wasm_bootstrap.py` carries a pinned
  `OCP_WASM_VERSION`. It is third-party, it installs a patched `cadquery-ocp`
  from a GitHub release, and floating it would let a stranger's build change
  the geometry under you.
- **Sectioning exactly at a layer interface** picks up the wrong layer. Offset
  by a small epsilon when verifying cross-sections.
- **build123d drags in 88 MB of material tooling.** It imports `bd_materials`
  and `threejs_materials` at module scope, so they cannot be dropped — but it
  only uses them for appearance, which this app never sets.
  `_MATERIAL_STUBS` in `bridge.py` registers both as mock packages before the
  bootstrap runs and supplies the four names build123d imports. Cold start went
  from 147 MB to 60 MB; STL and STEP come out byte-identical.
  **The distribution names must be canonical (hyphenated).**
  `micropip.add_mock_package` stores the string verbatim while the resolver
  looks requirements up canonicalised, so `"bd_materials"` silently satisfies
  nothing and the wheel is fetched anyway — which is exactly the bug the first
  attempt shipped. Module names inside keep underscores.
- **The phone `@media` block must stay last in the stylesheet.** A media query
  carries no extra specificity, so it beats a base rule only by coming after
  it. The block was written near the top and nearly every override in it —
  table sizing, tap targets, `.derived`, `pre.report` — was silently dead
  while looking perfectly correct in the source.
- **Grid tracks are sized by their content's min-content width.** `1fr` is
  `minmax(auto, 1fr)`, and a `<pre>` that scrolls does *not* stop that
  propagating up unless the grid item itself has `min-width: 0`. The setup
  sheet widened the whole page to 618px at every viewport — but only after
  Python had rendered into it, so the page looked fine on load and broke a
  second later. `main > div { min-width: 0 }` is load-bearing.

## Three levels of capability

The page is a calculator that can also export solids, not a CAD app with a
calculator bolted on. Loading OpenCascade costs ~23 MB and a large amount of
memory, and on a phone it can take the tab down, so it is never loaded for a
visitor who has not asked for a solid.

| Level | What loads | When |
|---|---|---|
| 1. core | Python, `app.geometry`, `app.report` — validation, dimensions, taper, adjustment table, SVG previews, setup sheet | always, ~2 s |
| 2. desktop CAD | OpenCascade + build123d | in the background, as soon as the core is up |
| 3. mobile CAD | same | never on its own — only from the **Load CAD Export Engine** button |

**Do not move the desktop fetch to the first export click.** That was tried
and reverted: the 23 MB then lands *inside* the export, so the first STL takes
a minute with nothing but a "Generating…" label to show for it, and it reads
as a hang. Fetch early and gate the buttons instead — the download overlaps
with the user typing dimensions, which is free.

The rules that keep this true:

- `web/pyscript.toml` lists `micropip` and the `app` modules. **Nothing heavy
  goes in `packages`** — anything listed there is fetched before `bridge.py`
  runs, which is exactly what level 1 is avoiding.
- `bridge.py` imports `app.model` (and therefore build123d) **inside**
  `export()` and `_bring_up_cad()`, never at module scope. A top-level import
  would drag the kernel in for everyone.
- `bridge.py` has no top-level `await` and starts nothing on its own. **The
  page owns the policy**: it calls `window.mrttLoadCad()` from `coreReady()`
  on a desktop, and from a button press on a phone. `load_cad()` is idempotent
  and returns a bool.
- `export()` refuses solid formats unless `_cad_ready`, so a stale button gets
  a sentence instead of an `ImportError`.
- In `index.html`, `ensureCad()` is the only path to the kernel and is
  single-flight — a second call joins the in-flight load instead of starting
  another.
- `IS_MOBILE` prefers `navigator.userAgentData.mobile`, falls back to a UA
  sniff, and checks `maxTouchPoints` because **iPadOS 13+ claims to be a
  Mac** — the device most likely to run out of memory here is the one that
  denies being mobile.
- After a failed load the notice appears on desktop too, carrying the error
  and a retry. Nothing retries by itself — re-running an OOM is how you lose
  the tab.

The setup sheet is level 1: it is text from `app.report`, exports with no
kernel at all, and must stay that way.

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
# 4. Everything in 1, plus the input bounds, in one go:
python3 tools/check_geometry.py
```

```sh
# 5. The browser runtime, which is where the interesting failures live - a
#    wheel that will not resolve, an OpenCascade call missing from the WASM
#    build, an engraving with no font. Drives the real Pyodide:
npm install --prefix tools pyodide@314.0.3
node tools/check_browser.mjs
```

```sh
# 6. Frontend logic without a browser: extract the inline <script>, stub
#    document/fetch, and drive refresh() under node. Check for NaN/undefined in
#    the generated SVG. `node --check` catches syntax errors.
```

```sh
# 7. Real layout, which is where the responsive failures live. Serve the built
#    site, block PyScript, inject a state object and call refresh()/render()
#    yourself - no 23 MB Pyodide wait - then compare
#    documentElement.scrollWidth against clientWidth at 320/360/375/414 px.
#    A page that fits before render and overflows after is a min-content
#    problem in a grid track, not a media-query problem.
npm install --prefix tools puppeteer && npx --yes puppeteer browsers install chrome
```

Previews can be rasterised for visual inspection with
`qlmanage -t -s 1500 -o <dir> file.svg` on macOS. Headless Chrome via puppeteer
*does* drive the live page successfully, if you raise `protocolTimeout` — the
WASM work blocks the main thread for minutes and the default 180 s kills the
session mid-load.

## Layout

```
app/config.py     measured constants + design decisions. Single source of truth.
app/geometry.py   Spec: transfer function, taper math, validation. Pure, no CAD.
app/model.py      build123d solid, engraving, STL/STEP/3MF/DXF export.
app/report.py     the printable setup sheet.

web/index.html    the UI: inputs, SVG previews, tables. Plain JS, no framework.
web/bridge.py     what the page calls into. Exposes compute/export/loadCad on
                  window. Never starts the CAD kernel on its own.
web/pyscript.toml which files land in Pyodide's filesystem.
web/vendor/       pinned OCP.wasm bootstrap (third party).
web/fonts/        DejaVu Sans, for engraving in a browser with no fonts.

tools/build_site.py     web/ + app/ -> _site/. Also serves it (--serve).
tools/check_geometry.py the factory calibration point, as a script.
tools/check_browser.mjs the same exports, under real Pyodide.
```

The browser imports `app` unchanged. `web/` may import from `app`; `app` must
never import from `web`, and must never assume a browser.

`geometry.py` has no build123d import and should stay that way — it makes the
math testable without the CAD kernel.

## Scope discipline

The engraving on the back face is deliberately **two lines only** (router bit,
resulting tenon) so the template can be identified on a shelf. The full
adjustment table belongs on the setup sheet, not the part. It was previously
five lines and the user cut it back; do not re-expand it.

The preview diagram is deliberately dimensioned with **only** profile-at-base,
profile-at-top, resulting tenon, and — when the mortise slot is on — the slot
length, in both views. Holder-interface dimensions were removed on request.

The length stack sorts by size so the nesting stays correct when the template
comes out smaller than the tenon; the slot goes through the same sort rather
than being pinned to the inside. Adding a row grows the plan's top margin
**and its viewBox by the same amount**, so the part keeps its size instead of
shrinking to pay for the dimension. The side elevation does the same with its
top margin, which is otherwise a constant because nothing sits above the part.

There is deliberately **no advice about which router bit to use**. A prompt
recommending a particular bit was added and then removed on request. Any bit
produces a correct template — that is the whole point of
`offset = bit_dia - stylus_dia` and of the mismatched-bit case in
`check_geometry.py` — and the page states the consequences of the choice
through the dimensions it already shows. Do not reintroduce it.

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
- Bearing protrusion is currently set "by feel". At 5.56:1 that is survivable —
  0.010" of slop in the setting is 0.0018" on the tenon — but a caliper reading
  against a flat reference face on the bracket would make the adjustment table
  exact rather than advisory.
- When the profile is narrower than layer 2 (0.750"), over-inserting the
  bearing makes it contact **layer 2** instead and cut oversize. The app warns
  per-configuration; there is no physical stop on the part.
