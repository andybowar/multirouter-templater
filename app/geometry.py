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

from . import config as C


@dataclass
class Issue:
    level: str  # "error" | "warning"
    message: str


@dataclass
class Spec:
    """Everything derived from the two user inputs."""

    # --- inputs -----------------------------------------------------------
    bit_dia: float  # the router bit used for this cut
    tenon_width: float  # dictated by the mortise = the MORTISING bit diameter
    tenon_length: float
    stylus_dia: float = C.STYLUS_DIA
    taper_range: float = C.TAPER_RANGE
    profile_thk: float = C.PROFILE_THK

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
    total_thk: float = field(init=False)
    issues: list[Issue] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        self.offset = self.bit_dia - self.stylus_dia

        self.prof_len_nom = self.tenon_length + self.offset
        self.prof_wid_nom = self.tenon_width + self.offset

        # Nominal sits at mid-depth so the operator can adjust either way from
        # a test cut.
        half = self.taper_range / 2.0
        self.prof_len_base = self.prof_len_nom + half
        self.prof_wid_base = self.prof_wid_nom + half
        self.prof_len_top = self.prof_len_nom - half
        self.prof_wid_top = self.prof_wid_nom - half

        # Per-side rise over the profile depth.
        self.draft_deg = degrees(atan(half / self.profile_thk))

        self.travel_per_5thou = 0.005 / self.taper_range * self.profile_thk
        self.reduction_ratio = self.profile_thk / self.taper_range

        self.total_thk = C.BASE_THK + C.MID_THK + self.profile_thk

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

        # The template is the tenon shifted by (bit - stylus) per dimension. A
        # bit much smaller than the stylus shrinks it away to nothing.
        if self.prof_wid_nom <= 0:
            self._err(
                f'A {self.bit_dia:.4f}" bit is too small to cut a '
                f'{self.tenon_width:.4f}" tenon on this machine: the template '
                f"would have to be "
                f'{self.prof_wid_nom:.4f}" wide. With a {self.stylus_dia:.4f}" '
                f'stylus the bit must exceed {self.stylus_dia - self.tenon_width:.4f}".'
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

        if self.prof_len_base > C.BASE_LEN:
            self._err(
                f'Guide profile would be {self.prof_len_base:.3f}" long, which '
                f'overhangs the {C.BASE_LEN:.3f}" base plate. Maximum tenon '
                f'length for this bit is '
                f'{C.BASE_LEN - self.offset - self.taper_range / 2:.3f}".'
            )
        elif self.prof_len_base > C.MID_LEN:
            self._warn(
                f"Guide profile is longer than the middle step, so it will "
                f"overhang layer 2 at both ends. Prints fine, but check "
                f"clearance in the holder."
            )

        # Clearance advice is only meaningful for a part that can actually be
        # made, so hold it back if anything above already failed.
        if not self.ok:
            return

        if self.prof_wid_base > C.MID_LEN or self.prof_wid_base > C.MID_WID:
            self._err(
                f'Guide profile would be {self.prof_wid_base:.3f}" wide, which '
                f'overhangs the {C.MID_WID:.3f}" middle layer. With a '
                f'{self.tenon_width:.3f}" tenon the bit must stay under '
                f"{C.MID_WID - self.tenon_width + self.stylus_dia - self.taper_range / 2:.4f}\"."
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
            "base_len": C.BASE_LEN,
            "base_wid": C.BASE_WID,
            "base_thk": C.BASE_THK,
            "mid_len": C.MID_LEN,
            "mid_wid": C.MID_WID,
            "mid_thk": C.MID_THK,
        }


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
    return (
        f"multirouter_tenon_{spec.tenon_width:.3f}x{spec.tenon_length:.3f}"
        f"_bit{spec.bit_dia:.3f}".replace(".", "p")
    )
