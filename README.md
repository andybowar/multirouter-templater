# Multi-Router & PantoRouter Tapered Tenon Template Generator

Generates 3D-printable tenon templates for the **JDS / Woodpeckers Multi-Router** (1:1 linkage) and the **PantoRouter** (2:1 pantograph linkage), featuring a tapered guide profile so you can sneak up on a joint fit instead of printing a new template every time.

It is a static web page. Open it, select your machine, type a tenon, download a file — there is no
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

The first page load pulls down about 23 MB of OpenCascade and takes a minute or
two. The browser caches it, so later visits are quick. The numbers, the preview
and the setup sheet appear immediately; only the solid formats wait for the CAD
kernel.

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

Key inputs:

| Input | What it is |
|---|---|
| **Machine** | Multi-Router (1:1 ratio) or PantoRouter (2:1 ratio) |
| **Tenon width** | The mortise width — i.e. the bit you cut the *mortise* with |
| **Tenon length** | The long dimension of the tenon |
| **Router bit diameter** | The bit you'll cut the *tenon* with. Need not match the mortising bit |

Tenon *depth* — how far it protrudes from the shoulder — is your plunge
setting, not template geometry, so it isn't an input.

Fields accept fractions (`1/2`, `1-1/2`) or decimals. Use *measured* bit
diameters, not nominal.

Then download **STL** or **3MF** for the slicer, **STEP** for Fusion 360, or
**DXF** for flat outlines. The **setup sheet** is a printable text file with
the dimensions, the adjustment table and print settings.

## Adjusting the fit

The guide profile is a shallow frustum — biggest where it meets the step below
it, tapering inward toward its free top face. Where the stylus bearing sits
along that taper decides the size of the tenon.

Set the bearing depth by how far its edge sits below the template's free top
face. Flush = 0. Deeper = bigger tenon.

| Bearing depth | Tenon |
|---|---|
| flush | −0.010" |
| 1/16" | −0.005" |
| **1/8"** | **nominal** |
| 3/16" | +0.005" |
| 1/4" | +0.010" |

**1/16" of bearing travel = 0.005" of tenon.** That's a 12.5:1 reduction, so a
sloppy 0.010" error setting the bearing is worth 0.0008" on the tenon. Nominal
sits in the middle of the range, so you can go either way after a test cut:
tight, back the bearing out; loose, push it in.

Cut a test tenon, try it, move the bearing, cut again.

## The parts & holder interfaces

### Multi-Router (1:1)
Three-layer stepped solid designed to clamp into the Multi-Router fixture bed. The bottom two layers match the factory template:

| Layer | Size | Thickness |
|---|---|---|
| base plate | 3.500 × 1.000" | 0.250" (square corners) |
| middle step | 3.250 × 0.750" | 0.125" (stadium) |
| guide profile | computed (1:1) | 0.250" (~4.57° draft) |

### PantoRouter (2:1)
Direct T-slot mounted template designed for the extruded aluminum template holder:

| Feature | Dimension | Function |
|---|---|---|
| base mounting flange | adaptive × 2.000" | 0.200" thick base with rounded ends |
| rear alignment key | 0.375" wide × 0.080" high | Indexes into the template holder T-slot track |
| mounting holes | 2× ⌀ 0.216" (M5 clearance) | ⌀ 0.375" counterbores for M5 screws & T-nuts |
| guide profile | computed (2:1 scale) | 0.500" thick (5.71° draft, matching 5°–6° factory templates) |
| standard stylus | 22 mm (0.866") | Standard tenon guide bearing (10, 15, 22, 26, 35 mm set) |

The back/base face is engraved with the machine name, router bit size and resulting tenon size.

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
**0.6350" × 2.1350"**.

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
