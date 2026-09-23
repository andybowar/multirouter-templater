"""Machine and part constants.

Every number in here is either measured off the physical machine / a factory
template, or a deliberate design decision. Nothing is assumed silently.
"""

# ---------------------------------------------------------------------------
# Machine (measured)
# ---------------------------------------------------------------------------

# Outer diameter of the stylus / follower bearing.
# Multi-Router: 3/8" (0.375") brass/steel bearing rod.
# PantoRouter: 22mm (0.866") standard tenon guide bearing (10/12/15/22/26/35mm set).
STYLUS_DIA = 0.375
STYLUS_DIA_MULTI_ROUTER = 0.375
STYLUS_DIA_PANTOROUTER = 0.8661  # 22mm standard guide bearing

# The bearing is the same diameter as the rod it sits on, with no protruding
# stud. Two consequences the taper model relies on:
#   * nothing sticks out past the bearing to foul layer 2, so insertion depth
#     is limited only by the profile itself;
#   * the rod behind the bearing is not oversize, so it cannot contact the
#     profile at shallow settings. Contact is always the bearing's front edge.
STYLUS_BEARING_FLUSH = True

# Linkage ratios
RATIO_MULTI_ROUTER = 1.0
RATIO_PANTOROUTER = 2.0
LINKAGE_RATIO = 1.0


# ---------------------------------------------------------------------------
# Holder interface - Multi-Router (measured off a factory template)
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
# Holder interface - PantoRouter (T-slot extrusion mounting)
# ---------------------------------------------------------------------------

# PantoRouter templates mount to an extruded aluminum template holder with T-slots.
# The rear face features an alignment tab/key that indexes into the T-track,
# and M5 counterbored mounting holes secure the template with T-nuts.
PANTO_BASE_THK = 0.200       # Base flange thickness
PANTO_TAB_WID = 0.375        # Rear alignment tab width (fits T-slot)
PANTO_TAB_THK = 0.080        # Rear alignment tab projection height (2.0 mm)
PANTO_HOLE_DIA = 0.216       # M5 clearance hole (5.5 mm)
PANTO_CBORE_DIA = 0.375      # M5 socket/button screw counterbore (9.5 mm)
PANTO_CBORE_DEPTH = 0.120    # Counterbore depth
PANTO_MIN_BASE_WID = 2.000   # Template holder standard track height


# ---------------------------------------------------------------------------
# Tapered profile layer - design decisions
# ---------------------------------------------------------------------------

# Multi-Router: 0.250" profile thickness, 0.040" taper range (draft ~4.57 deg)
PROFILE_THK = 0.25
TAPER_RANGE = 0.040

# PantoRouter: 0.500" profile thickness (12.7 mm), 0.050" tenon taper range
# (0.100" template variation over 0.500" depth yields a 5.71 deg draft,
# matching official 5-6 deg PantoRouter factory templates).
PANTO_PROFILE_THK = 0.500
PANTO_TAPER_RANGE = 0.050

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
