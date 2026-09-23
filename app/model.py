"""Solid model generation and CAD export.

All geometry is built in MILLIMETERS (inches * 25.4) so that STEP carries
correct units into Fusion 360 and STL/3MF land correctly in a slicer.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from build123d import (
    Align,
    ExportDXF,
    Mesher,
    Plane,
    Pos,
    Rectangle,
    Sketch,
    SlotOverall,
    Text,
    Unit,
    export_step,
    export_stl,
    extrude,
    loft,
    mirror,
    scale,
)

from . import config as C
from .geometry import Spec

MM = C.IN_TO_MM

FONT_CANDIDATES = ["Arial", "Helvetica", "DejaVu Sans", "Verdana"]

# Font files to try before the fonts installed on the machine, best first. The
# browser build has no system fonts at all, so it appends a bundled TTF here
# before asking for an engraving. Empty everywhere else.
FONT_PATHS: list[str] = []


# ---------------------------------------------------------------------------
# Solid
# ---------------------------------------------------------------------------


def build_part(spec: Spec, engrave: bool = True):
    """Build the three-layer template as a single fused solid.

    Layer 1 sits on z=0 (the print bed, and the face that seats in the
    holder). The tapered guide profile points up in +Z.
    """
    base_thk = spec.base_thk * MM
    mid_thk = spec.mid_thk * MM
    prof_thk = spec.profile_thk * MM

    # Layer 1 - base plate, square corners.
    part = extrude(Rectangle(spec.base_len * MM, spec.base_wid * MM), base_thk)

    # Engrave into the z=0 face before fusing anything else onto it: the
    # boolean is cheaper against a plain slab.
    if engrave:
        pocket = _engraving_solid(spec)
        if pocket is not None:
            part -= pocket

    # Layer 2 - middle step, stadium.
    mid_sk = Plane.XY.offset(base_thk) * SlotOverall(
        spec.mid_len * MM, spec.mid_wid * MM
    )
    part += extrude(mid_sk, mid_thk)

    # Layer 3 - the tapered guide profile. A ruled loft between two concentric
    # stadiums is exactly a uniform inward offset at every height: the flats
    # interpolate to planes, and the end arcs share a center so they
    # interpolate to cones.
    z0 = base_thk + mid_thk
    bottom = Plane.XY.offset(z0) * SlotOverall(
        spec.prof_len_base * MM, spec.prof_wid_base * MM
    )
    top = Plane.XY.offset(z0 + prof_thk) * SlotOverall(
        spec.prof_len_top * MM, spec.prof_wid_top * MM
    )
    part += loft([bottom, top], ruled=True)

    # Optional mortise slot: the stepped pin drops in here so the table stops
    # can be set against its travel. Sunk from the free top face to the base of
    # the profile and no further - layers 1 and 2 are the holder interface.
    # The cut overshoots upward only, where there is nothing left to cut.
    if spec.mortise_slot:
        slot_sk = Plane.XY.offset(z0) * SlotOverall(
            spec.slot_len * MM, spec.slot_wid * MM
        )
        part -= extrude(slot_sk, spec.slot_depth * MM + 1.0)

    return part


# ---------------------------------------------------------------------------
# Engraving
# ---------------------------------------------------------------------------


def engraving_lines(spec: Spec) -> list[str]:
    """Just the two facts you need to pick the right template off the shelf."""
    return [
        f"ROUTER BIT {spec.bit_dia:.3f}",
        f"TENON SIZE {spec.tenon_width:.3f} x {spec.tenon_length:.3f}",
    ]


def _text_sketch(spec: Spec) -> Sketch | None:
    """Text block laid out for reading, before mirroring."""
    lines = engraving_lines(spec)
    font_size = C.ENGRAVE_FONT * MM
    line_pitch = font_size * 1.55
    top = (len(lines) - 1) / 2.0 * line_pitch

    for kwargs in _font_kwargs():
        try:
            block = None
            for i, line in enumerate(lines):
                glyphs = Text(
                    line,
                    font_size=font_size,
                    align=(Align.CENTER, Align.CENTER),
                    **kwargs,
                )
                placed = Pos(0, top - i * line_pitch) * glyphs
                block = placed if block is None else block + placed
            if block is not None and block.area > 0:
                return block
        except Exception:
            continue
    return None


def _font_kwargs() -> list[dict]:
    """Ways to ask build123d for a font, best first, then let it default."""
    return [
        *({"font_path": p} for p in FONT_PATHS),
        *({"font": f} for f in FONT_CANDIDATES),
        {},
    ]


def _engraving_solid(spec: Spec):
    """A solid to subtract from the base plate, recessing the text."""
    block = _text_sketch(spec)
    if block is None:
        return None

    # Fit the block inside the base plate with a margin.
    avail_x = (spec.base_len - 2 * C.ENGRAVE_MARGIN) * MM
    avail_y = (spec.base_wid - 2 * C.ENGRAVE_MARGIN) * MM
    bbox = block.bounding_box()
    # Fit to the plate, but cap the growth so a two-line label does not blow up
    # to fill the whole face.
    factor = min(
        avail_x / bbox.size.X,
        avail_y / bbox.size.Y,
        C.ENGRAVE_MAX_FONT / C.ENGRAVE_FONT,
    )
    if factor < 0.999 or factor > 1.001:
        block = scale(block, by=factor)
        bbox = block.bounding_box()
    block = Pos(-bbox.center().X, -bbox.center().Y) * block

    # The engraved face is the z=0 face, read while looking along +Z. In that
    # view global +X points left, so the text has to be mirrored about the YZ
    # plane to read correctly on the physical part.
    block = mirror(block, about=Plane.YZ)

    return extrude(block, C.ENGRAVE_DEPTH * MM)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

FORMATS = {
    "stl": ("model/stl", ".stl"),
    "step": ("application/step", ".step"),
    "3mf": ("model/3mf", ".3mf"),
    "dxf": ("image/vnd.dxf", ".dxf"),
}


def export(spec: Spec, fmt: str, path: Path, engrave: bool = True) -> Path:
    fmt = fmt.lower()
    if fmt not in FORMATS:
        raise ValueError(f"unsupported format: {fmt}")

    if fmt == "dxf":
        _export_dxf(spec, path)
        return path

    part = build_part(spec, engrave=engrave)

    if fmt == "stl":
        export_stl(
            part,
            str(path),
            tolerance=C.STL_LINEAR_TOL * MM,
            angular_tolerance=C.STL_ANGULAR_TOL,
        )
    elif fmt == "step":
        export_step(part, str(path))
    elif fmt == "3mf":
        mesher = Mesher()
        mesher.add_shape(part, linear_deflection=C.STL_LINEAR_TOL * MM)
        mesher.write(str(path))

    return path


def export_bytes(spec: Spec, fmt: str, engrave: bool = True) -> bytes:
    """`export` straight to memory, for callers with nowhere to put a file.

    The browser has no user-visible filesystem, so the page writes into
    Pyodide's in-memory one and hands the bytes to a download.
    """
    fmt = fmt.lower()
    if fmt not in FORMATS:
        raise ValueError(f"unsupported format: {fmt}")

    _, ext = FORMATS[fmt]
    with tempfile.TemporaryDirectory(prefix="mrtt_") as tmp:
        out = Path(tmp) / f"part{ext}"
        export(spec, fmt, out, engrave=engrave)
        return out.read_bytes()


def _export_dxf(spec: Spec, path: Path) -> None:
    """Flat outlines for reference / laser work / CAD tracing."""
    exporter = ExportDXF(unit=Unit.MM)

    layers = [
        ("base_plate", Rectangle(spec.base_len * MM, spec.base_wid * MM)),
        ("middle_step", SlotOverall(spec.mid_len * MM, spec.mid_wid * MM)),
        (
            "profile_base",
            SlotOverall(spec.prof_len_base * MM, spec.prof_wid_base * MM),
        ),
        (
            "profile_nominal",
            SlotOverall(spec.prof_len_nom * MM, spec.prof_wid_nom * MM),
        ),
        ("profile_top", SlotOverall(spec.prof_len_top * MM, spec.prof_wid_top * MM)),
        ("tenon_nominal", SlotOverall(spec.tenon_length * MM, spec.tenon_width * MM)),
    ]

    if spec.mortise_slot:
        layers.append(
            ("mortise_slot", SlotOverall(spec.slot_len * MM, spec.slot_wid * MM))
        )

    for name, sketch in layers:
        exporter.add_layer(name)
        for face in sketch.faces():
            for wire in face.wires():
                exporter.add_shape(wire, layer=name)

    exporter.write(str(path))
