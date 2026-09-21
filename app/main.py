"""Local web app for the Multi-Router tapered tenon template generator."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

from . import config as C
from .geometry import Spec, file_stem
from .model import FORMATS, export
from .report import build_report

app = FastAPI(title="Multi-Router Tenon Template Generator")

STATIC = Path(__file__).parent / "static"


class Request(BaseModel):
    bit_dia: float = Field(0.5, gt=0, le=2.0)
    tenon_width: float = Field(0.5, gt=0, le=10.0)
    tenon_length: float = Field(2.0, gt=0, le=10.0)
    stylus_dia: float = Field(C.STYLUS_DIA, gt=0, le=2.0)
    taper_range: float = Field(C.TAPER_RANGE, gt=0, le=0.25)
    profile_thk: float = Field(C.PROFILE_THK, gt=0, le=2.0)
    engrave: bool = True

    def to_spec(self) -> Spec:
        return Spec(
            bit_dia=self.bit_dia,
            tenon_width=self.tenon_width,
            tenon_length=self.tenon_length,
            stylus_dia=self.stylus_dia,
            taper_range=self.taper_range,
            profile_thk=self.profile_thk,
        )


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC / "index.html").read_text(encoding="utf-8")


@app.get("/api/defaults")
def defaults() -> dict:
    return {
        "stylus_dia": C.STYLUS_DIA,
        "taper_range": C.TAPER_RANGE,
        "profile_thk": C.PROFILE_THK,
        "base_len": C.BASE_LEN,
        "base_wid": C.BASE_WID,
        "base_thk": C.BASE_THK,
        "mid_len": C.MID_LEN,
        "mid_wid": C.MID_WID,
        "mid_thk": C.MID_THK,
        "formats": sorted(FORMATS),
    }


@app.post("/api/compute")
def compute(req: Request) -> dict:
    spec = req.to_spec()
    return {
        "ok": spec.ok,
        "errors": spec.errors,
        "warnings": spec.warnings,
        "dims": spec.as_dict(),
        "table": spec.adjustment_table(),
        "report": build_report(spec) if spec.ok else "",
        "stem": file_stem(spec),
    }


@app.post("/api/export/{fmt}")
def export_file(fmt: str, req: Request) -> FileResponse:
    if fmt not in FORMATS:
        raise HTTPException(400, f"unsupported format: {fmt}")

    spec = req.to_spec()
    if not spec.ok:
        raise HTTPException(400, "; ".join(spec.errors))

    media_type, ext = FORMATS[fmt]
    out_dir = Path(tempfile.mkdtemp(prefix="mrtt_"))
    name = file_stem(spec) + ext
    export(spec, fmt, out_dir / name, engrave=req.engrave)

    return FileResponse(out_dir / name, media_type=media_type, filename=name)


@app.post("/api/report", response_class=PlainTextResponse)
def report_file(req: Request) -> PlainTextResponse:
    spec = req.to_spec()
    if not spec.ok:
        raise HTTPException(400, "; ".join(spec.errors))
    return PlainTextResponse(
        build_report(spec),
        headers={
            "Content-Disposition": f'attachment; filename="{file_stem(spec)}.txt"'
        },
    )
