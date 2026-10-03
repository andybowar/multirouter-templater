"""Machine and part constants.

Every number in here is either measured off the physical machine / a factory
template, or a deliberate design decision. Nothing is assumed silently.
"""

# ---------------------------------------------------------------------------
# Machine (measured)
# ---------------------------------------------------------------------------

# Outer diameter of the JDS / Woodpeckers Multi-Router stylus bearing. Measured
# with calipers. This is THE critical machine constant: the template-to-tenon
# offset is (bit_dia - STYLUS_DIA), so an error here transfers 1:1 to every
# tenon.
STYLUS_DIA = 0.375

# The bearing is the same diameter as the rod it sits on, with no protruding
# stud on the tenon-cutting end. Two consequences the taper model relies on:
#   * nothing sticks out past the bearing to foul layer 2, so insertion depth
#     is limited only by the profile itself;
#   * the rod behind the bearing is not oversize, so it cannot contact the
#     profile at shallow settings. Contact is always the bearing's front edge.
# The stepped-down pin is on the OTHER end - you turn the stylus around to use
# it - so it is never in the way while a tenon is being cut.
STYLUS_BEARING_FLUSH = True

# Diameter of the stepped-down end of the stylus pin. Measured with calipers.
# This end rides the mortise slot and guides the mortise cut, so it is what the
# slot is sized around - see geometry.Spec for the offset.
STYLUS_PIN_DIA = 0.1920

# The Multi-Router linkage is 1:1 (not 2:1 like a PantoRouter), so the bit
# centerline path is a pure translation of the stylus centerline path.
LINKAGE_RATIO = 1.0


# ---------------------------------------------------------------------------
# Holder interface (measured off a factory template; do not change)
# ---------------------------------------------------------------------------

# Layer 1 - the base plate. Plain rectangle, sharp corners.
BASE_LEN = 3.5
BASE_WID = 1.0
BASE_THK = 0.25

# Layer 2 - the middle step. Stadium (fully radiused ends, r = width/2).
MID_LEN = 3.25
MID_WID = 0.75
MID_THK = 0.125


# ---------------------------------------------------------------------------
# Tapered profile layer (layer 3) - design decisions
# ---------------------------------------------------------------------------

# Depth of the tapered guide profile. This is the taper's "gear ratio": the
# range is fixed at TAPER_RANGE, so a deeper profile means a shallower draft
# angle and finer control per unit of bearing travel.
PROFILE_THK = 0.25

# Total change in a tenon dimension from the base of the profile to its free
# top face, over 0.250" of bearing travel.
#
# Everything else about the taper falls out of this number: 7.97 deg of draft,
# a 3.6:1 reduction, and 0.0179" of bearing travel per 0.005" of tenon. Change
# it and all four have to be re-derived wherever they are quoted.
TAPER_RANGE = 0.070

# Where nominal sits in the profile, as a fraction of bearing depth measured
# from the free top face. 0.5 is mid-depth and splits the range evenly; LOWER
# values put nominal nearer the top and so leave MORE of the range on the
# deep/oversize side, which is the side that gets used.
#
#   up from nominal   = TAPER_RANGE * (1 - NOMINAL_DEPTH_FRAC)   = 0.0467"
#   down from nominal = TAPER_RANGE * NOMINAL_DEPTH_FRAC         = 0.0233"
#
# It is not 0.5 because the demand is not symmetric. Every known error pushes
# the same way: the profile prints under (so the tenon starts under), and with
# the slot in use the mortise is ALWAYS SLOT_CLEARANCE oversize, so the working
# point is always above nominal and range below it is close to dead space.
# Measured: at mid-depth and TAPER_RANGE 0.055 the bearing fully inserted left
# only 0.0095" of fat to shave after those two - near enough to no headroom
# that a printer running a few thou worse would arrive under size with nowhere
# to go, which is the one unrecoverable failure here.
#
# Note this does NOT change the draft angle - that is TAPER_RANGE over
# PROFILE_THK either way. It only moves which cross-section is labelled
# nominal, so the extra headroom is free in control resolution.
NOMINAL_DEPTH_FRAC = 1.0 / 3.0

# ---------------------------------------------------------------------------
# Mortise slot (optional) - design decisions
# ---------------------------------------------------------------------------

# Slip fit for the pin in the slot. The slot GUIDES the mortise cut, so the
# pin is free to wander by this much and the whole of it lands in the workpiece:
# the mortise comes out SLOT_CLEARANCE oversize in both dimensions.
# Tighten it for a closer joint; it cannot go to zero or the pin binds.
SLOT_CLEARANCE = 0.008

# Extra length in the slot, on top of the fit clearance. Deliberately NOT
# applied to the width, and that asymmetry is the whole point.
#
# A mortise and tenon glues on the cheeks - long grain to long grain. The ends
# of the tenon meet end grain, which contributes almost nothing. So the tenon
# THICKNESS (tenon_width) has to be dead on and its length does not.
#
# The taper moves both tenon dimensions together. If the mortise length were
# the tight dimension, the operator would have to shave the tenon until it fit
# length-wise and lose the identical amount off the thickness - spending the
# dimension that carries the joint to buy the one that does not. Slack here
# keeps the length from ever being the binding dimension, so the taper is left
# to serve the thickness alone.
#
# This is a DEFAULT, not a constant - it is exposed as an input, because the
# right value depends on the printer and on how hard the operator drives the
# pin into the ends of the slot.
#
# Sized from a measurement, not a guess. A 1.750" tenon was set up with the
# slack at 0.010"; the slot should have cut a 1.768" mortise and cut 1.740" -
# a 0.028" deficit, of which 0.018" was asymmetric, i.e. the length was binding
# 0.018" before the cheeks did and the operator was shaving that much thickness
# off to get the tenon in. 0.040" covers that 0.018" and leaves ~0.012" of real
# margin.
#
# Two mechanisms are known to feed it. The offset model assumes the pin reaches
# the true axial ends of the slot, which needs it centred within
# SLOT_CLEARANCE/2 at that instant; a pin driven along one side wall into the
# end arc loses that much axial reach at each end, so up to SLOT_CLEARANCE of
# mortise length goes missing by technique alone. The rest is the slot's end
# arcs printing tight - a small inner radius pulls in where a straight wall
# does not, which is why measuring the slot's WIDTH across the straights said
# the pocket was fine when its length was not.
#
# Overshooting is cheap: a mortise that is long only has more end-grain gap,
# which glues nothing anyway. It costs slack/2 of wall at the two ends.
SLOT_LENGTH_SLACK = 0.010

# Wall left between the slot and the guide edge. That wall works twice - the
# bearing rides its outside cutting the tenon, the pin rides its inside cutting
# the mortise - so this is what stops a slotted template folding up under load.
MIN_SLOT_WALL_ERROR = 0.060
MIN_SLOT_WALL_WARN = 0.100

# Engraved text on the base plate's back face. Recessed, never embossed - that
# face seats in the holder.
ENGRAVE_DEPTH = 0.012
ENGRAVE_MARGIN = 0.10
ENGRAVE_FONT = 0.075
ENGRAVE_MAX_FONT = 0.22


# ---------------------------------------------------------------------------
# Validation thresholds
# ---------------------------------------------------------------------------

# Below this the printed guide rib is too fragile to survive a bearing.
MIN_PROFILE_WID_ERROR = 0.060
# Below this it will print, but it will deflect under bearing load.
MIN_PROFILE_WID_WARN = 0.200

# Export tolerances (inches, converted to mm at build time).
STL_LINEAR_TOL = 0.0005
STL_ANGULAR_TOL = 0.1

IN_TO_MM = 25.4
