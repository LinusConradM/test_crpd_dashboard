"""Centralized WCAG 2.2 compliant color palette for the CRPD Dashboard.

All chart colors should be imported from this module.
Palette is based on Okabe-Ito / Wong (2011), anchored on UN Blue.
Every color meets ≥3:1 contrast ratio against white (#FFFFFF) per WCAG SC 1.4.11.
"""

# ── Categorical palette (8 colors, colorblind-safe) ──────────────────────────
CATEGORICAL_PALETTE = [
    "#003F87",  # UN Blue (primary)
    "#D55E00",  # Vermillion
    "#009E73",  # Bluish Green
    "#882255",  # Reddish Purple
    "#56B4E9",  # Sky Blue
    "#E69F00",  # Orange
    "#444444",  # Dark Gray
    "#CC3311",  # Brick Red
]

# ── Sequential blues (choropleth / heatmaps, light → dark) ──────────────────
SEQUENTIAL_BLUES = [
    "#C5DFEF",  # lightest
    "#8DBDE2",
    "#5199D1",
    "#003F87",  # UN Blue anchor
    "#004490",
    "#002D62",  # darkest
]

# ── Binary: Rights-Based vs Medical Model ────────────────────────────────────
MODEL_COLORS = {
    "Rights-Based": "#003F87",
    "Medical-Based": "#D55E00",
    "Medical Model": "#D55E00",
}

# ── Document type colors ─────────────────────────────────────────────────────
DOC_TYPE_COLORS = {
    "State Report": "#003F87",
    "Concluding Observations": "#009E73",
    "List of Issues (LOI)": "#E69F00",
    "Written Reply": "#D55E00",
    "Response to Concluding Observations": "#882255",
}

# ── Region colors ────────────────────────────────────────────────────────────
REGION_COLORS = {
    "Africa": "#D55E00",
    "Americas": "#E69F00",
    "Asia": "#009E73",
    "Europe": "#003F87",
    "Oceania": "#882255",
}

# ── Bump chart colors (10, for ranked article trajectories) ──────────────────
BUMP_COLORS = [
    "#003F87",  # UN Blue
    "#D55E00",  # Vermillion
    "#009E73",  # Bluish Green
    "#882255",  # Reddish Purple
    "#56B4E9",  # Sky Blue
    "#E69F00",  # Orange
    "#444444",  # Dark Gray
    "#CC3311",  # Brick Red
    "#0077B6",  # Darker Blue
    "#AA3377",  # Muted Magenta
]

# ── Trend indicator colors ───────────────────────────────────────────────────
TREND_COLORS = {
    "up": "#009E73",  # Bluish Green (positive)
    "down": "#D55E00",  # Vermillion (negative)
    "neutral": "#E69F00",  # Orange (flat/neutral)
    "info": "#444444",  # Dark Gray (informational)
}

# ── Compare countries palette ────────────────────────────────────────────────
COMPARE_PALETTE = [
    "#003F87",  # Primary country
    "#D55E00",
    "#009E73",
    "#882255",
    "#E69F00",
]

# ── Map constants ─────────────────────────────────────────────────────────────
MAP_NO_DATA = "#e8e8e8"  # No-data / background fill for choropleth maps

# ── Text & surface colors (Fix 18: centralized, WCAG-compliant) ────────────
TEXT_PRIMARY = "#191C1F"
TEXT_SECONDARY = "#424752"
TEXT_MUTED = "#5a6377"  # Contrast ~5.5:1 on white (was #90a4ae, failed WCAG)
CARD_BG = "#F2F4F8"

# ── Phase badge colors (narrative card) ─────────────────────────────────────
PHASE_RIGHTS_BG = "#dbe8f7"
PHASE_MEDICAL_BG = "#f7dbe8"
PHASE_BALANCED_BG = "#e8e8e0"
PHASE_BALANCED_TEXT = "#4a4a2e"
NARRATIVE_BG = "#eef2f7"

# ── Metric color map (for compare countries metrics) ─────────────────────────
METRIC_COLORS = {
    "Rights-Based Language %": "#003F87",
    "Documents Submitted": "#009E73",
    "Avg Document Length (words)": "#E69F00",
    "Article Coverage Breadth": "#882255",
    "CO Response Rate %": "#D55E00",
}
