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
           WebAssembly build of OpenCascade, fetched in the background and
           cached by the browser afterwards.

The page is told about each through `window.MRTT`, and calls back in through
`window.mrttCompute` / `window.mrttExport`.
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


async def _load_cad() -> None:
    ui.status("Fetching the CAD kernel (~23 MB, cached after this)…")

    import ocp_wasm_bootstrap

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

    # The first solid pays for OpenCascade's own start-up. Do it here, in the
    # background, rather than on the first click where it reads as a hang.
    warmup = spec_from_inputs(
        {"bit_dia": 0.5, "tenon_width": 0.5, "tenon_length": 2.0}
    )
    model.build_part(warmup, engrave=False)


window.mrttCompute = compute
window.mrttExport = export
ui.coreReady()

try:
    await _load_cad()  # noqa: F704 - PyScript runs this with runPythonAsync
except Exception as exc:
    traceback.print_exc()
    ui.cadFailed(f"{type(exc).__name__}: {exc}")
else:
    ui.cadReady()
