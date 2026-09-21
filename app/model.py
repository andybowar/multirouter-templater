"""Solid model generation and CAD export.

All geometry is built in MILLIMETERS (inches * 25.4) so that STEP carries
correct units into Fusion 360 and STL/3MF land correctly in a slicer.
"""

from __future__ import annotations
from fractions import Fraction

from pathlib import Path

from build123d import (
    Align,
    Axis,
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


# ---------------------------------------------------------------------------
# Solid
# ---------------------------------------------------------------------------


def build_part(spec: Spec, engrave: bool = True):
    """Build the three-layer template as a single fused solid.

    Layer 1 sits on z=0 (the print bed, and the face that seats in the
    holder). The tapered guide profile points up in +Z.
    """
    base_thk = C.BASE_THK * MM
    mid_thk = C.MID_THK * MM
    prof_thk = spec.profile_thk * MM

    # Layer 1 - base plate, square corners.
    part = extrude(Rectangle(C.BASE_LEN * MM, C.BASE_WID * MM), base_thk)

    # Engrave into the z=0 face before fusing anything else onto it: the
    # boolean is cheaper against a plain slab.
    if engrave:
        pocket = _engraving_solid(spec)
        if pocket is not None:
            part -= pocket

    # Layer 2 - middle step, stadium.
    mid_sk = Plane.XY.offset(base_thk) * SlotOverall(C.MID_LEN * MM, C.MID_WID * MM)
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

    for font in [*FONT_CANDIDATES, None]:
        try:
            block = None
            for i, line in enumerate(lines):
                kwargs = {"font": font} if font else {}
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


def _engraving_solid(spec: Spec):
    """A solid to subtract from the base plate, recessing the text."""
    block = _text_sketch(spec)
    if block is None:
        return None

    # Fit the block inside the base plate with a margin.
    avail_x = (C.BASE_LEN - 2 * C.ENGRAVE_MARGIN) * MM
    avail_y = (C.BASE_WID - 2 * C.ENGRAVE_MARGIN) * MM
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


def _export_dxf(spec: Spec, path: Path) -> None:
    """Flat outlines for reference / laser work / CAD tracing."""
    exporter = ExportDXF(unit=Unit.MM)

    layers = [
        ("base_plate", Rectangle(C.BASE_LEN * MM, C.BASE_WID * MM)),
        ("middle_step", SlotOverall(C.MID_LEN * MM, C.MID_WID * MM)),
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

    for name, sketch in layers:
        exporter.add_layer(name)
        for wire in sketch.faces()[0].wires():
            exporter.add_shape(wire, layer=name)

    exporter.write(str(path))
