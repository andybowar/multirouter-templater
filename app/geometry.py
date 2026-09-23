"""The geometric model: desired tenon -> required template profile.

Derivation
----------
The Multi-Router linkage is 1:1, so the bit centerline path is a pure
translation of the stylus centerline path. Therefore:

    stylus center path = template edge offset OUTWARD by r_stylus
    tenon surface      = bit center path offset INWARD  by r_bit

Composing the two:

    tenon    = template offset outward by (r_stylus - r_bit)
    template = tenon    offset outward by (r_bit - r_stylus)

In dimensions (each dimension changes by twice the per-side offset):

    template_dim = tenon_dim + (bit_dia - stylus_dia)

Validated against a factory template: a 1/2" x 2" tenon cut with a 1/2" bit
uses a template measuring 0.625" x 2.125".

    0.500 + (0.500 - 0.375) = 0.625  OK
    2.000 + (0.500 - 0.375) = 2.125  OK

The mortise is cut in a single pass at full bit width, so it is a stadium:
width = mortising bit diameter, end radius = half that. The tenon has to match
the mortise, so the tenon is a stadium of the same width with end radius
tenon_width / 2 - and that is true whatever bit is in the router for this cut.

The router bit and the mortising bit are independent. Tenon width is therefore
an input in its own right (it is dictated by the mortise), while bit_dia is
simply the router bit being used here.

A uniform offset of a stadium is still a stadium, so the template's end radius
comes out to exactly half the template width and the profile is always a
stadium too.

Taper
-----
The profile layer is a frustum: full size where it meets layer 2, tapering
inward toward its free face. That direction is forced, not chosen. A
cylindrical bearing riding a drafted face contacts at whatever point of the
engaged span is LARGEST. If the profile were largest at its free top face the
bearing would always contact that top edge and the depth setting would do
nothing. Tapering inward puts the contact at the bearing's deepest engaged
circle, so bearing depth selects the cross-section.

The stylus bearing is flush with its rod and the same diameter (no protruding
stud), so the deepest engaged circle is always the bearing's front edge: there
is nothing ahead of it to bottom out, and nothing behind it wide enough to
touch the profile at a shallower setting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import atan, degrees
from typing import Any

from . import config as C


@dataclass
class Issue:
    level: str  # "error" | "warning"
    message: str


@dataclass
class Spec:
    """Everything derived from the user inputs."""

    # --- inputs -----------------------------------------------------------
    bit_dia: float  # the router bit used for this cut
    tenon_width: float  # dictated by the mortise = the MORTISING bit diameter
    tenon_length: float
    stylus_dia: float = C.STYLUS_DIA
    taper_range: float = C.TAPER_RANGE
    profile_thk: float = C.PROFILE_THK
    machine: str = "multirouter"  # "multirouter" | "pantorouter"
    linkage_ratio: float = 1.0

    # --- derived ----------------------------------------------------------
    offset: float = field(init=False)
    prof_len_nom: float = field(init=False)
    prof_wid_nom: float = field(init=False)
    prof_len_base: float = field(init=False)
    prof_wid_base: float = field(init=False)
    prof_len_top: float = field(init=False)
    prof_wid_top: float = field(init=False)
    draft_deg: float = field(init=False)
    travel_per_5thou: float = field(init=False)
    reduction_ratio: float = field(init=False)
    base_len: float = field(init=False)
    base_wid: float = field(init=False)
    base_thk: float = field(init=False)
    mid_len: float = field(init=False)
    mid_wid: float = field(init=False)
    mid_thk: float = field(init=False)
    tab_wid: float = field(init=False, default=0.0)
    tab_thk: float = field(init=False, default=0.0)
    hole_dia: float = field(init=False, default=0.0)
    cbore_dia: float = field(init=False, default=0.0)
    cbore_depth: float = field(init=False, default=0.0)
    hole_offset_x: float = field(init=False, default=0.0)
    total_thk: float = field(init=False)
    issues: list[Issue] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        norm_machine = str(self.machine).lower().strip()
        if norm_machine in ("pantorouter", "panto") or self.linkage_ratio == 2.0:
            self.machine = "pantorouter"
            self.linkage_ratio = 2.0
            # PantoRouter template body with T-slot mounting interface
            self.base_thk = C.PANTO_BASE_THK
            self.mid_len = 0.0
            self.mid_wid = 0.0
            self.mid_thk = 0.0
            self.tab_wid = C.PANTO_TAB_WID
            self.tab_thk = C.PANTO_TAB_THK
            self.hole_dia = C.PANTO_HOLE_DIA
            self.cbore_dia = C.PANTO_CBORE_DIA
            self.cbore_depth = C.PANTO_CBORE_DEPTH
        else:
            self.machine = "multirouter"
            self.linkage_ratio = 1.0
            self.base_len = C.BASE_LEN
            self.base_wid = C.BASE_WID
            self.base_thk = C.BASE_THK
            self.mid_len = C.MID_LEN
            self.mid_wid = C.MID_WID
            self.mid_thk = C.MID_THK
            self.tab_wid = 0.0
            self.tab_thk = 0.0
            self.hole_dia = 0.0
            self.cbore_dia = 0.0
            self.cbore_depth = 0.0
            self.hole_offset_x = 0.0

        self.offset = self.linkage_ratio * self.bit_dia - self.stylus_dia

        self.prof_len_nom = (
            self.linkage_ratio * (self.tenon_length + self.bit_dia) - self.stylus_dia
        )
        self.prof_wid_nom = (
            self.linkage_ratio * (self.tenon_width + self.bit_dia) - self.stylus_dia
        )

        # Nominal sits at mid-depth so the operator can adjust either way from
        # a test cut. To achieve taper_range change on the cut tenon, the
        # template profile variation is scaled by linkage_ratio.
        half_template = (self.linkage_ratio * self.taper_range) / 2.0
        self.prof_len_base = self.prof_len_nom + half_template
        self.prof_wid_base = self.prof_wid_nom + half_template
        self.prof_len_top = self.prof_len_nom - half_template
        self.prof_wid_top = self.prof_wid_nom - half_template

        if self.machine == "pantorouter":
            # PantoRouter mounting base adapts to enclose the profile + M5 mounting holes
            self.base_len = max(3.50, self.prof_len_base + 1.50)
            self.base_wid = max(C.PANTO_MIN_BASE_WID, self.prof_wid_base + 0.50)
            self.hole_offset_x = (self.prof_len_base / 2.0) + 0.450

        # Per-side rise over the profile depth.
        self.draft_deg = degrees(atan(half_template / self.profile_thk))

        self.travel_per_5thou = 0.005 / self.taper_range * self.profile_thk
        self.reduction_ratio = self.profile_thk / self.taper_range

        self.total_thk = self.base_thk + self.mid_thk + self.profile_thk

        self._validate()

    # -- validation --------------------------------------------------------

    def _err(self, msg: str) -> None:
        self.issues.append(Issue("error", msg))

    def _warn(self, msg: str) -> None:
        self.issues.append(Issue("warning", msg))

    def _validate(self) -> None:
        # Fundamental checks first. If the shape cannot exist at all, the
        # downstream fit-and-clearance advice is just noise.
        if self.tenon_length <= self.tenon_width:
            self._err(
                f'Tenon length ({self.tenon_length:.3f}") must be greater than '
                f'tenon width ({self.tenon_width:.3f}"). A tenon is a slot, '
                f"not a circle."
            )
            return

        # The template is derived from linkage_ratio * (tenon + bit) - stylus.
        if self.prof_wid_nom <= 0:
            min_bit = (self.stylus_dia / self.linkage_ratio) - self.tenon_width
            self._err(
                f'A {self.bit_dia:.4f}" bit is too small to cut a '
                f'{self.tenon_width:.4f}" tenon on this machine: the template '
                f"would have to be "
                f'{self.prof_wid_nom:.4f}" wide. With a {self.stylus_dia:.4f}" '
                f'stylus the bit must exceed {min_bit:.4f}".'
            )
            return

        if self.prof_wid_top <= C.MIN_PROFILE_WID_ERROR:
            self._err(
                f'Guide profile would be only {self.prof_wid_top:.3f}" wide at '
                f"its narrow end. Too fragile to print or to survive a bearing. "
                f"Use a larger bit."
            )
        elif self.prof_wid_top < C.MIN_PROFILE_WID_WARN:
            self._warn(
                f'Guide profile is narrow ({self.prof_wid_top:.3f}" at the top, '
                f'{self.prof_wid_base:.3f}" at the base). It will print, but it '
                f"will deflect under bearing load. Feed lightly and expect the "
                f"tenon to run a touch fat."
            )

        if self.machine == "multirouter":
            if self.prof_len_base > self.base_len:
                max_tenon = (
                    self.base_len
                    + self.stylus_dia
                    - (self.linkage_ratio * self.taper_range) / 2.0
                ) / self.linkage_ratio - self.bit_dia
                self._err(
                    f'Guide profile would be {self.prof_len_base:.3f}" long, which '
                    f'overhangs the {self.base_len:.3f}" base plate. Maximum tenon '
                    f'length for this bit is '
                    f'{max_tenon:.3f}".'
                )
            elif self.prof_len_base > self.mid_len:
                self._warn(
                    f"Guide profile is longer than the middle step, so it will "
                    f"overhang layer 2 at both ends. Prints fine, but check "
                    f"clearance in the holder."
                )

            # Clearance advice is only meaningful for a part that can actually be
            # made, so hold it back if anything above already failed.
            if not self.ok:
                return

            if self.prof_wid_base > self.mid_len or self.prof_wid_base > self.mid_wid:
                max_bit = (
                    self.mid_wid
                    + self.stylus_dia
                    - (self.linkage_ratio * self.taper_range) / 2.0
                ) / self.linkage_ratio - self.tenon_width
                self._err(
                    f'Guide profile would be {self.prof_wid_base:.3f}" wide, which '
                    f'overhangs the {self.mid_wid:.3f}" middle layer. With a '
                    f'{self.tenon_width:.3f}" tenon the bit must stay under '
                    f'{max_bit:.4f}".'
                )
        else:
            if self.tenon_length > 6.0:
                self._warn(
                    f'Tenon length ({self.tenon_length:.3f}") approaches the limit of '
                    f"standard PantoRouter pantograph reach."
                )
            if self.prof_len_base > 14.0:
                self._err(
                    f'Guide profile ({self.prof_len_base:.3f}") exceeds the template holder capacity.'
                )

    @property
    def ok(self) -> bool:
        return not any(i.level == "error" for i in self.issues)

    @property
    def errors(self) -> list[str]:
        return [i.message for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[str]:
        return [i.message for i in self.issues if i.level == "warning"]

    # -- adjustment table --------------------------------------------------

    def tenon_delta(self, bearing_depth: float) -> float:
        """Change in tenon dimensions for a given bearing depth.

        `bearing_depth` is measured from the profile's free top face, so 0 is
        the bearing edge flush with the top of the template and
        `profile_thk` is fully inserted to the profile base.
        """
        frac = bearing_depth / self.profile_thk
        return -self.taper_range / 2.0 + frac * self.taper_range

    def adjustment_table(self, steps: int = 4) -> list[dict]:
        rows = []
        for i in range(steps + 1):
            depth = self.profile_thk * i / steps
            delta = self.tenon_delta(depth)
            rows.append(
                {
                    "depth": depth,
                    "depth_label": _frac_label(depth),
                    "delta": delta,
                    "tenon_width": self.tenon_width + delta,
                    "tenon_length": self.tenon_length + delta,
                    "is_nominal": abs(delta) < 1e-9,
                }
            )
        return rows

    def as_dict(self) -> dict:
        return {
            "machine": self.machine,
            "machine_name": "PantoRouter" if self.machine == "pantorouter" else "Multi-Router",
            "linkage_ratio": self.linkage_ratio,
            "bit_dia": self.bit_dia,
            "tenon_length": self.tenon_length,
            "tenon_width": self.tenon_width,
            "stylus_dia": self.stylus_dia,
            "offset": self.offset,
            "prof_len_nom": self.prof_len_nom,
            "prof_wid_nom": self.prof_wid_nom,
            "prof_end_radius_nom": self.prof_wid_nom / 2.0,
            "prof_len_base": self.prof_len_base,
            "prof_wid_base": self.prof_wid_base,
            "prof_len_top": self.prof_len_top,
            "prof_wid_top": self.prof_wid_top,
            "draft_deg": self.draft_deg,
            "taper_range": self.taper_range,
            "profile_thk": self.profile_thk,
            "travel_per_5thou": self.travel_per_5thou,
            "reduction_ratio": self.reduction_ratio,
            "total_thk": self.total_thk,
            "base_len": self.base_len,
            "base_wid": self.base_wid,
            "base_thk": self.base_thk,
            "mid_len": self.mid_len,
            "mid_wid": self.mid_wid,
            "mid_thk": self.mid_thk,
            "tab_wid": self.tab_wid,
            "tab_thk": self.tab_thk,
            "hole_dia": self.hole_dia,
            "cbore_dia": self.cbore_dia,
            "cbore_depth": self.cbore_depth,
            "hole_offset_x": self.hole_offset_x,
        }


# Sanity limits on the raw form input, before any geometry runs. These are
# not shop advice - they only keep a typo or a hostile URL from reaching the
# CAD kernel. `Spec._validate` is where the real judgement lives.
INPUT_BOUNDS: dict[str, tuple[float, float]] = {
    "bit_dia": (0.0, 2.0),
    "tenon_width": (0.0, 10.0),
    "tenon_length": (0.0, 10.0),
    "stylus_dia": (0.0, 2.0),
    "taper_range": (0.0, 0.25),
    "profile_thk": (0.0, 2.0),
}


def spec_from_inputs(values: dict) -> Spec:
    """Build a Spec from untrusted input, raising ValueError on nonsense."""
    kwargs: dict[str, Any] = {}
    for name, (low, high) in INPUT_BOUNDS.items():
        if name not in values or values[name] is None:
            continue
        try:
            v = float(values[name])
        except (TypeError, ValueError):
            raise ValueError(f"{name} is not a number") from None
        if not v == v or v in (float("inf"), float("-inf")):
            raise ValueError(f"{name} is not a number")
        if not low < v <= high:
            raise ValueError(
                f'{name} must be greater than {low:g}" and at most {high:g}", '
                f'got {v:g}"'
            )
        kwargs[name] = v

    if "machine" in values and values["machine"] is not None:
        m = str(values["machine"]).lower().strip()
        if m in ("pantorouter", "panto", "2:1", "2"):
            kwargs["machine"] = "pantorouter"
            kwargs["linkage_ratio"] = 2.0
        elif m in ("multirouter", "multi-router", "multi", "1:1", "1"):
            kwargs["machine"] = "multirouter"
            kwargs["linkage_ratio"] = 1.0
        else:
            raise ValueError(f"unknown machine: {values['machine']}")
    elif "linkage_ratio" in values and values["linkage_ratio"] is not None:
        try:
            r = float(values["linkage_ratio"])
        except (TypeError, ValueError):
            raise ValueError("linkage_ratio is not a number")
        if r not in (1.0, 2.0):
            raise ValueError("linkage_ratio must be 1.0 (Multi-Router) or 2.0 (PantoRouter)")
        kwargs["linkage_ratio"] = r
        kwargs["machine"] = "pantorouter" if r == 2.0 else "multirouter"

    is_panto = kwargs.get("machine") == "pantorouter" or kwargs.get("linkage_ratio") == 2.0
    if "stylus_dia" not in kwargs:
        kwargs["stylus_dia"] = C.STYLUS_DIA_PANTOROUTER if is_panto else C.STYLUS_DIA_MULTI_ROUTER
    if "taper_range" not in kwargs:
        kwargs["taper_range"] = C.PANTO_TAPER_RANGE if is_panto else C.TAPER_RANGE
    if "profile_thk" not in kwargs:
        kwargs["profile_thk"] = C.PANTO_PROFILE_THK if is_panto else C.PROFILE_THK

    missing = [n for n in ("bit_dia", "tenon_width", "tenon_length") if n not in kwargs]
    if missing:
        raise ValueError(f"missing input: {', '.join(missing)}")

    return Spec(**kwargs)


_SIXTEENTHS = {
    0: "0",
    1: "1/16",
    2: "1/8",
    3: "3/16",
    4: "1/4",
    5: "5/16",
    6: "3/8",
    7: "7/16",
    8: "1/2",
}


def _frac_label(x: float) -> str:
    """Render a depth as a shop fraction when it lands on a sixteenth."""
    sixteenths = x * 16.0
    n = round(sixteenths)
    if abs(sixteenths - n) < 1e-6 and n in _SIXTEENTHS:
        return _SIXTEENTHS[n] + '"'
    return f'{x:.3f}"'


def file_stem(spec: Spec) -> str:
    prefix = "pantorouter" if spec.machine == "pantorouter" else "multirouter"
    return (
        f"{prefix}_tenon_{spec.tenon_width:.3f}x{spec.tenon_length:.3f}"
        f"_bit{spec.bit_dia:.3f}".replace(".", "p")
    )
