# Multi-Router Tapered Tenon Template Generator

Generates 3D-printable tenon templates for the **JDS / Woodpeckers
Multi-Router** (1:1 linkage), compatible with the factory template holder, with
a tapered guide profile so you can sneak up on a joint fit instead of printing a
new template every time.

It is a static web page. Open it, type a tenon, download a file — there is no
server, no account, and nothing you type leaves the tab. The geometry, the CAD
kernel and the exporters are Python compiled to WebAssembly, running in the
browser via [PyScript](https://pyscript.net).

## Running it

```sh
./run.sh
```

Builds the site into `_site/` and opens <http://127.0.0.1:8765>. Nothing to
install — the standard library is enough, because the page fetches its own
Python. It does have to be served over http; opening `index.html` off the disk
will not work.

The page itself is small and comes up in a second or two; the numbers, the
previews and the setup sheet are usable straight away. On a desktop the ~23 MB
OpenCascade build then downloads in the background and the 3D buttons light up
when it lands. The browser caches it, so later visits are quick. On a phone it
is not downloaded at all — see below.

To run the CAD code on a workstation instead — scripting exports, poking at a
solid:

```sh
python3.14 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Needs Python 3.11–3.14.

## Deploying it

Push to `main`. `.github/workflows/pages.yml` checks the geometry, assembles
the site and publishes it to GitHub Pages. Enable it once under
**Settings → Pages → Source → GitHub Actions**.

The site is `web/` with the `app` package copied in beside it — the browser
imports the same modules a workstation does, so there is no second
implementation to keep in step.

## Using it

The inputs:

| Input | What it is |
|---|---|
| **Tenon width** | The mortise width — i.e. the bit you cut the *mortise* with |
| **Tenon length** | The long dimension of the tenon |
| **Router bit diameter for tenon cut** | The bit you'll cut the *tenon* with. Need not match the mortising bit |
| **Add mortise slot** | Optional. Cuts a guide slot for the stepped end of the stylus pin, so the same template cuts the mortise — see below |

Tenon *depth* — how far it protrudes from the shoulder — is your plunge
setting, not template geometry, so it isn't an input.

Fields accept fractions (`1/2`, `1-1/2`) or decimals. Use *measured* bit
diameters, not nominal.

Then download **STL** or **3MF** for the slicer, **STEP** for Fusion 360, or
**DXF** for flat outlines. The **setup sheet** is a printable text file with
the dimensions, the adjustment table and print settings.

## Checking it before you print

**Render 3D preview** shows the part in the page — orbit it, zoom it, and jump
straight to the engraved face. It renders the *exact STL the download button
gives you*, not a second model drawn from the same numbers, so what you see is
what the slicer gets.

Mostly it is there to catch the engraving: that face sits on the print bed, so
the text is mirrored in the model on purpose, and "on purpose" is hard to
believe until you have looked at it. It also shows the mortise slot and which
way the taper runs.

It needs the CAD engine, so it follows the same rules as the 3D exports —
ready when the kernel has loaded on desktop, and an explicit opt-in on a phone.
The viewer itself is a pinned copy of three.js, about 430 KB, fetched only the
first time you open the preview.

## On a phone

The calculator is the app; the CAD kernel is an optional extra, and the page
is built so you never pay for it unless you want a solid.

| | What you get | What it costs |
|---|---|---|
| **Everything, everywhere** | validation, dimensions, taper maths, adjustment table, both previews, setup sheet | a normal web page |
| **3D export, desktop** | STL / STEP / 3MF / DXF | the kernel downloads in the background while you type; the buttons enable when it is ready |
| **3D export, phone or tablet** | the same | nothing is downloaded, and the buttons stay disabled with an explanation, because initialising OpenCascade can crash a mobile browser |

So an iPhone in the shop can work out the template it needs, read the
adjustment table and save the setup sheet without ever touching the 23 MB
download. If you want the STL on that phone anyway there is a **Load CAD
Export Engine** button — it just will not happen behind your back.

## Adjusting the fit

The guide profile is a shallow frustum — biggest where it meets the step below
it, tapering inward toward its free top face. Where the stylus bearing sits
along that taper decides the size of the tenon.

Set the bearing depth by how far its edge sits below the template's free top
face. Flush = 0. Deeper = bigger tenon.

| Bearing depth | Tenon | |
|---|---|---|
| flush | −0.0225" | |
| 1/16" | −0.01125" | |
| 1/8" | nominal | |
| 3/16" | +0.01125" | |
| **1/4"** | **+0.0225"** | **start here** |

**Start fully inserted**, against the widest part of the profile. That is the
biggest tenon the template can cut, so the first one comes out too fat — which
is the point. Withdraw the bearing a little, recut the same tenon, try it
again, and repeat until it goes.

Always come down onto the fit, never up to it. A tenon that is still fat can be
cut again; one that has gone under size is scrap, because you cannot put wood
back. Nominal is the size you asked for, not where to begin.

**0.028" of bearing travel = 0.005" of tenon.** That's a 5.6:1 reduction, so a
sloppy 0.010" error setting the bearing is worth 0.0018" on the tenon.

## The mortise slot (optional)

Tick **Add mortise slot** and the template gets a slot down the middle of the
guide profile, sized for the stepped-down end of the stylus pin (0.1920" on
this machine). It cuts the *other* half of the joint.

Turn the stylus around so the small pin faces the template, fit a bit the width
of the mortise you want — the same diameter you entered as tenon width — drop
the pin into the slot and cut. **The slot is the guide**: it bounds the cut in
both directions, so you run the pin out to the ends of the slot and let them
stop you. No stop collars.

The slot is derived, not copied — it is the mortise offset inward by
`(tenon width − pin) / 2`, which for the default 1/2" × 2" tenon is a
0.200" × 1.700" slot, 0.250" deep.

Because it guides, its slip fit lands in the work: the mortise comes out
0.008" oversize in *both* directions. That is deliberate — the taper moves both
tenon dimensions together, so a uniformly oversize mortise is one the tenon can
be dialled up to meet. The page and the setup sheet tell you the bearing depth
that does it (0.169" instead of the 0.125" nominal, on the defaults).

The slot spends wall out of the guide profile — the wall the bearing rides on
the outside and the pin rides on the inside — so on a small bit the app will
warn, and on a very small one it will refuse. Untick the box and you get the
plain template.

## The part

Three layers. The bottom two match the factory template and are fixed; only the
tapered guide profile is computed.

| Layer | Size | Thickness |
|---|---|---|
| base plate | 3.500 × 1.000" | 0.250" (square corners) |
| middle step | 3.250 × 0.750" | 0.125" (stadium) |
| guide profile | computed | 0.250" (~5.14° draft) |

Overall 0.625", against 0.500" for the factory template — the guide profile is
thicker to make room for the taper.

The back face is engraved with the router bit size and the resulting tenon
size, so you can identify a template on the shelf.

## Printing

Base plate (engraved face) flat on the bed, profile pointing up. The taper
shrinks as it rises, so it's self-supporting — **no supports anywhere**, and
the guide edge is built from perimeters on the printer's best axis.

- 0.4 mm nozzle, 0.12 mm layers
- 5–6 perimeters — the guide edge should be solid wall, not infill
- 40% infill minimum; 100% if the profile is under 0.30" wide
- PETG to start: tougher than PLA against a rolling bearing

Files export in millimetres.

## Before you trust it

Print the default configuration (0.500" tenon, 2.000" long, 0.500" bit) and
measure across the guide profile at its base. It should read
**0.6475" × 2.1475"** — the 0.6250" × 2.1250" nominal plus half the 0.045"
taper range.

That number transfers 1:1 to the tenon. Closing any gap is exactly what the
taper is for.

**Nothing here has cut wood yet.** The underlying math reproduces a measured
factory template exactly, which is a strong calibration point — but it is not
proof.

## How it works

The Multi-Router linkage is 1:1, so the bit centreline path is a pure
translation of the stylus centreline path. Working through the offsets:

```
template_dim = tenon_dim + (bit_dia − stylus_dia)
```

With the measured 0.375" stylus, a 0.500" × 2.000" tenon cut with a 0.500" bit
needs a 0.625" × 2.125" template — which is exactly what the factory template
measures.

For the full derivation, the reasoning behind the taper direction, and the
invariants to preserve when changing the code, see [CLAUDE.md](CLAUDE.md).

## Layout

```
app/          the geometry, the solid and the setup sheet. Runs both places.
web/          the page, its Python bridge, the bundled font, the OCP.wasm pin.
tools/        assemble the site, check the geometry, check the browser runtime.
```
