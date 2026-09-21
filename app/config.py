"""Machine and part constants.

Every number in here is either measured off the physical machine / a factory
template, or a deliberate design decision. Nothing is assumed silently.
"""

# ---------------------------------------------------------------------------
# Machine (measured)
# ---------------------------------------------------------------------------

# Outer diameter of the JDS Multi-Router stylus bearing. Measured with calipers.
# This is THE critical machine constant: the template-to-tenon offset is
# (bit_dia - STYLUS_DIA), so an error here transfers 1:1 to every tenon.
STYLUS_DIA = 0.375

# The bearing is the same diameter as the rod it sits on, with no protruding
# stud. Two consequences the taper model relies on:
#   * nothing sticks out past the bearing to foul layer 2, so insertion depth
#     is limited only by the profile itself;
#   * the rod behind the bearing is not oversize, so it cannot contact the
#     profile at shallow settings. Contact is always the bearing's front edge.
STYLUS_BEARING_FLUSH = True

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
# top face. Nominal sits at mid-depth, so the usable range is +/- half of this.
TAPER_RANGE = 0.020

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
