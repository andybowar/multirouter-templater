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

Mortise slot
------------
Optional, and it cuts nothing. The stylus has a stepped-down pin on its far
end; you turn the stylus around, drop that pin into a slot in the template,
slide the table to each end of the slot and lock a stop collar there. The
slot's travel is therefore the mortise's travel.

The mortise has to accept the tenon, so it is `tenon_length` long, and it is
cut in one pass with a bit of `tenon_width` diameter (that is what makes it a
stadium of that width - the same fact that fixes the tenon's end radius). So
the bit centre has to travel:

    bit travel = tenon_length - tenon_width

and the linkage is 1:1, so the pin travels exactly as far. Inside a stadium
slot a pin of diameter `d` can move `slot_len - d` end to end, whatever the
slot's width - the end arcs and the pin are concentric at the limit. Hence:

    slot_len = (tenon_length - tenon_width) + pin_dia      exact, no slack
    slot_wid = pin_dia + SLOT_CLEARANCE                    fit only

Clearance goes on the width alone. Width slack costs a little centring; length
slack would run every mortise long, and there is nothing downstream to catch
it.
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
    """Everything derived from the user inputs."""

    # --- inputs -----------------------------------------------------------
    bit_dia: float  # the router bit used for this cut
    tenon_width: float  # dictated by the mortise = the MORTISING bit diameter
    tenon_length: float
    stylus_dia: float = C.STYLUS_DIA
    taper_range: float = C.TAPER_RANGE
    profile_thk: float = C.PROFILE_THK
    mortise_slot: bool = False  # cut the stop-collar slot for the stepped pin
    pin_dia: float = C.STYLUS_PIN_DIA

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
    total_thk: float = field(init=False)
    slot_len: float = field(init=False)
    slot_wid: float = field(init=False)
    slot_travel: float = field(init=False)
    slot_depth: float = field(init=False)
    slot_wall_side: float = field(init=False)
    slot_wall_end: float = field(init=False)
    issues: list[Issue] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        # The holder interface is fixed - it matches the factory template.
        self.base_len = C.BASE_LEN
        self.base_wid = C.BASE_WID
        self.base_thk = C.BASE_THK
        self.mid_len = C.MID_LEN
        self.mid_wid = C.MID_WID
        self.mid_thk = C.MID_THK

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

        self.total_thk = self.base_thk + self.mid_thk + self.profile_thk

        # Mortise slot. Always computed so the page can show what it would be;
        # only cut, and only validated, when it is asked for.
        self.slot_travel = self.tenon_length - self.tenon_width
        self.slot_len = self.slot_travel + self.pin_dia
        self.slot_wid = self.pin_dia + C.SLOT_CLEARANCE
        # Sunk through the profile layer and no further: layers 1 and 2 are the
        # holder interface and are not ours to cut into.
        self.slot_depth = self.profile_thk
        # Wall is measured at the top face, the smallest cross-section.
        self.slot_wall_side = (self.prof_wid_top - self.slot_wid) / 2.0
        self.slot_wall_end = (self.prof_len_top - self.slot_len) / 2.0

        self._validate()

    # -- validation --------------------------------------------------------

    def _err(self, msg: str) -> None:
        self.issues.append(Issue("error", msg))

    def _warn(self, msg: str) -> None:
        self.issues.append(Issue("warning", msg))

    def _validate(self) -> None:
        """At most ONE error, in order of how fundamental it is.

        These checks are not independent - one undersized profile trips
        several of them at once, each describing the same problem from a
        different angle, and each suggesting a different fix. Two banners
        reading "cannot build" is two problems as far as the reader is
        concerned. So every error path returns, and the first one to fire is
        the one that gets reported. Warnings may still accumulate: they
        describe a part that can actually be made.
        """
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
            min_bit = self.stylus_dia - self.tenon_width
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
            return
        elif self.prof_wid_top < C.MIN_PROFILE_WID_WARN:
            self._warn(
                f'Guide profile is narrow ({self.prof_wid_top:.3f}" at the top, '
                f'{self.prof_wid_base:.3f}" at the base). It will print, but it '
                f"will deflect under bearing load. Feed lightly and expect the "
                f"tenon to run a touch fat."
            )

        if self.prof_len_base > self.base_len:
            max_tenon = self.base_len - self.offset - self.taper_range / 2
            self._err(
                f'Guide profile would be {self.prof_len_base:.3f}" long, which '
                f'overhangs the {self.base_len:.3f}" base plate. Maximum tenon '
                f'length for this bit is '
                f'{max_tenon:.3f}".'
            )
            return
        elif self.prof_len_base > self.mid_len:
            self._warn(
                f"Guide profile is longer than the middle step, so it will "
                f"overhang layer 2 at both ends. Prints fine, but check "
                f"clearance in the holder."
            )

        if self.prof_wid_base > self.mid_len or self.prof_wid_base > self.mid_wid:
            max_bit = (
                self.mid_wid
                - self.tenon_width
                + self.stylus_dia
                - self.taper_range / 2
            )
            self._err(
                f'Guide profile would be {self.prof_wid_base:.3f}" wide, which '
                f'overhangs the {self.mid_wid:.3f}" middle layer. With a '
                f'{self.tenon_width:.3f}" tenon the bit must stay under '
                f'{max_bit:.4f}".'
            )
            return

        if self.mortise_slot:
            self._validate_slot()

    def _validate_slot(self) -> None:
        """The slot is cut out of the guide profile, so it spends its wall."""
        # Measured at the top face - the profile's smallest cross-section, and
        # the one the slot has to fit inside.
        if self.slot_wall_side <= C.MIN_SLOT_WALL_ERROR:
            max_pin = self.prof_wid_top - 2 * C.MIN_SLOT_WALL_ERROR - C.SLOT_CLEARANCE
            self._err(
                f'A {self.slot_wid:.4f}" mortise slot leaves only '
                f'{self.slot_wall_side:.3f}" of wall on each side of a '
                f'{self.prof_wid_top:.3f}" profile. The bearing rides that wall, '
                f"so it would fold up under load. Use a bigger router bit, or "
                f'turn the slot off - a pin under {max_pin:.4f}" would fit.'
            )
            return
        elif self.slot_wall_side < C.MIN_SLOT_WALL_WARN:
            self._warn(
                f'Mortise slot leaves {self.slot_wall_side:.3f}" of wall each '
                f"side of the guide profile. It prints, but treat the template "
                f"gently and check the profile width after a few tenons."
            )

        # The slot runs the length of the profile; if it runs past the end
        # there is no template left to guide anything.
        if self.slot_wall_end <= C.MIN_SLOT_WALL_ERROR:
            self._err(
                f'A {self.slot_len:.3f}" mortise slot leaves only '
                f'{self.slot_wall_end:.3f}" at each end of a '
                f'{self.prof_len_top:.3f}" profile. The slot is '
                f'(tenon length - tenon width) + the {self.pin_dia:.4f}" pin, so '
                f"it only fits when the bit is not much smaller than the stylus."
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
            "base_len": self.base_len,
            "base_wid": self.base_wid,
            "base_thk": self.base_thk,
            "mid_len": self.mid_len,
            "mid_wid": self.mid_wid,
            "mid_thk": self.mid_thk,
            "mortise_slot": self.mortise_slot,
            "pin_dia": self.pin_dia,
            "slot_len": self.slot_len,
            "slot_wid": self.slot_wid,
            "slot_travel": self.slot_travel,
            "slot_depth": self.slot_depth,
            "slot_wall_side": self.slot_wall_side,
            "slot_wall_end": self.slot_wall_end,
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
    "pin_dia": (0.0, 1.0),
}


def spec_from_inputs(values: dict) -> Spec:
    """Build a Spec from untrusted input, raising ValueError on nonsense."""
    kwargs: dict[str, float | bool] = {}
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

    if values.get("mortise_slot") is not None:
        kwargs["mortise_slot"] = bool(values["mortise_slot"])

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
    # The slot changes the part, so it has to change the filename - otherwise
    # two different templates for the same tenon land on top of each other in
    # the downloads folder.
    suffix = "_mslot" if spec.mortise_slot else ""
    return (
        f"multirouter_tenon_{spec.tenon_width:.3f}x{spec.tenon_length:.3f}"
        f"_bit{spec.bit_dia:.3f}".replace(".", "p") + suffix
    )
