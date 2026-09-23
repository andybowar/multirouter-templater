"""The page's Python half.

index.html keeps the rendering - inputs, SVG previews, tables - and this
module keeps everything that has to agree with the physical machine. It is the
same `app` package that runs on a workstation; nothing here reimplements the
geometry, and nothing here is allowed to.

Two things become usable at very different times, so they are announced
separately:

    core   the transfer function and the setup sheet. Pure arithmetic, ready
           as soon as Python boots (~2 s).
    cad    STL / STEP / 3MF / DXF. Needs build123d on top of a ~23 MB
           WebAssembly build of OpenCascade, cached by the browser afterwards.

This module never brings the CAD kernel up on its own; the page asks, through
`mrttLoadCad`, and the page owns the policy. A desktop asks as soon as the
core is up, so the download overlaps with the user typing rather than landing
inside their first export. A phone does not ask at all unless the user presses
the button for it: initialising OpenCascade costs far more memory than the
arithmetic does, and on a mobile browser it can take the tab down with it.

The page is told about each through `window.MRTT`, and calls back in through
`window.mrttCompute` / `window.mrttExport` / `window.mrttLoadCad`.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from js import Object, Uint8Array
from pyodide.ffi import to_js
from pyscript import window

from app.geometry import file_stem, spec_from_inputs
from app.report import build_report

# Bitstream Vera / DejaVu, bundled in the site. OpenCascade in the browser has
# no system fonts and no fontconfig to find them with, so the engraving needs
# an actual file handed to it. Fetched only when the CAD kernel is.
FONT_URL = "./fonts/DejaVuSans.ttf"
FONT_DEST = "/mrtt-fonts/DejaVuSans.ttf"

ui = window.MRTT

# Flipped once OpenCascade is up and `app.model` is importable. Until then the
# only export this module can serve is the setup sheet, which is pure text.
_cad_ready = False


def _js(obj: dict):
    return to_js(obj, dict_converter=Object.fromEntries)


# ---------------------------------------------------------------------------
# Compute - available immediately
# ---------------------------------------------------------------------------


def compute(payload_json: str) -> str:
    """Everything the page needs to redraw itself, as a JSON string."""
    values = json.loads(payload_json)
    try:
        spec = spec_from_inputs(values)
    except ValueError as exc:
        # Out of range or unreadable: there is no Spec to describe, so the
        # page has nothing to draw and says so.
        return json.dumps(
            {"ok": False, "fatal": True, "errors": [str(exc)], "warnings": []}
        )

    return json.dumps(
        {
            "ok": spec.ok,
            "fatal": False,
            "errors": spec.errors,
            "warnings": spec.warnings,
            "dims": spec.as_dict(),
            "table": spec.adjustment_table(),
            "report": build_report(spec) if spec.ok else "",
            "stem": file_stem(spec),
        }
    )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def export(fmt: str, payload_json: str):
    """Build the file and hand it back as {name, mime, data} for a download."""
    values = json.loads(payload_json)
    spec = spec_from_inputs(values)
    if not spec.ok:
        raise ValueError("; ".join(spec.errors))

    stem = file_stem(spec)

    if fmt == "report":
        blob = build_report(spec).encode("utf-8")
        name, mime = stem + ".txt", "text/plain"
    else:
        if not _cad_ready:
            # The page guards this too; reaching it means a stale button or a
            # console call, and a plain sentence beats an ImportError.
            raise RuntimeError(
                "The CAD engine is not loaded, so solid formats are "
                "unavailable. Load it first."
            )

        from app import model

        if fmt not in model.FORMATS:
            raise ValueError(f"unsupported format: {fmt}")
        mime, ext = model.FORMATS[fmt]
        name = stem + ext
        blob = model.export_bytes(spec, fmt, engrave=bool(values.get("engrave", True)))

    data = Uint8Array.new(len(blob))
    data.assign(blob)
    return _js({"name": name, "mime": mime, "data": data})


# ---------------------------------------------------------------------------
# Bringing up the CAD kernel
# ---------------------------------------------------------------------------


async def _fetch_font() -> str | None:
    from pyodide.http import pyfetch

    dest = Path(FONT_DEST)
    dest.parent.mkdir(parents=True, exist_ok=True)
    response = await pyfetch(FONT_URL)
    if response.status != 200:
        return None
    dest.write_bytes(await response.bytes())
    return str(dest)


# build123d imports these two at module scope, so they cannot simply be left
# out - but it only *uses* them for material appearance, which this app never
# touches. `threejs_materials` is an 87.7 MB wheel of texture tooling, nearly
# four times the OpenCascade build it rides in with, and micropip would fetch
# it on every cold start.
#
# So they are registered as already-installed mock packages before the
# bootstrap runs, satisfying the resolver, and the stub modules below supply
# the four names build123d actually imports:
#
#   bd_materials.FinishedMaterial   isinstance checks, and annotations that
#                                   are lazy in all three importers
#   bd_materials.resolve            only called when assigning a material
#   threejs_materials.PbrProperties isinstance checks only
#   threejs_materials.inject_materials  only reached inside export_gltf, and
#                                   only for nodes that carry PBR materials
#
# Nothing here is exercised unless someone gives a Shape a material or exports
# glTF. If build123d ever starts using these for real, the guards raise with a
# pointer back here rather than failing somewhere confusing.
#
# The distribution names below are the CANONICAL, hyphenated ones.
# `add_mock_package` stores whatever string it is given, verbatim, while the
# resolver looks the requirement up canonicalised - so registering
# "bd_materials" satisfies nothing and the wheel is fetched anyway. Verified
# under real Pyodide: hyphens satisfy, underscores do not. The module names
# inside keep their underscores, because that is what build123d imports.
_MATERIAL_STUBS: dict[str, tuple[str, str, str]] = {
    "bd-materials": (
        "bd_materials",
        "0.2.4",
        '''"""Stub. See _MATERIAL_STUBS in bridge.py."""


class FinishedMaterial:  # isinstance target; never instantiated here
    pass


def resolve(*args, **kwargs):
    raise RuntimeError(
        "bd_materials is stubbed out in this build - see _MATERIAL_STUBS "
        "in bridge.py. Materials are not supported in the browser app."
    )
''',
    ),
    "threejs-materials": (
        "threejs_materials",
        "1.2.3",
        '''"""Stub. See _MATERIAL_STUBS in bridge.py."""


class PbrProperties:  # isinstance target; never instantiated here
    pass


def inject_materials(*args, **kwargs):
    raise RuntimeError(
        "threejs_materials is stubbed out in this build - see _MATERIAL_STUBS "
        "in bridge.py. Only reachable from export_gltf, which this app does "
        "not use."
    )
''',
    ),
}


def _stub_material_packages() -> None:
    """Tell micropip the material packages are already here. Best effort.

    If this fails the only cost is the download it was avoiding, so it must
    never be allowed to take the CAD kernel down with it.
    """
    try:
        import micropip

        for dist, (module, version, source) in _MATERIAL_STUBS.items():
            micropip.add_mock_package(dist, version, modules={module: source})
    except Exception:
        traceback.print_exc()


async def _bring_up_cad() -> None:
    ui.status("Fetching the CAD kernel (~23 MB, cached after this)…")

    import ocp_wasm_bootstrap

    _stub_material_packages()
    await ocp_wasm_bootstrap.bootstrap()

    ui.status("Starting the CAD kernel…")
    from app import model

    try:
        font = await _fetch_font()
    except Exception:  # a missing font costs the label, not the part
        font = None
    if font:
        model.FONT_PATHS.append(font)
    else:
        ui.warn("Bundled font unavailable - parts will export without engraving.")

    # The first solid pays for OpenCascade's own start-up. Do it while the
    # page is still saying "starting the CAD kernel", not on the export that
    # follows, where the same seconds read as a hang.
    warmup = spec_from_inputs(
        {"bit_dia": 0.5, "tenon_width": 0.5, "tenon_length": 2.0}
    )
    model.build_part(warmup, engrave=False)


async def load_cad() -> bool:
    """Bring the CAD kernel up on request. Idempotent; True once usable.

    The page serialises calls, but this stays safe to call twice: a second
    request after a successful load is a no-op, and a request after a failure
    retries, which is what the retry button wants.
    """
    global _cad_ready
    if _cad_ready:
        return True

    try:
        await _bring_up_cad()
    except Exception as exc:
        traceback.print_exc()
        ui.cadFailed(f"{type(exc).__name__}: {exc}")
        return False

    _cad_ready = True
    ui.cadReady()
    return True


window.mrttCompute = compute
window.mrttExport = export
window.mrttLoadCad = load_cad
ui.coreReady()
