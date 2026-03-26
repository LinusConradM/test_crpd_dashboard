# Chart Theme Reference — WCAG 2.2 Compliant Colors

**Consulted by:** data-scientist, software-engineer, ux-designer

## Rule: Always use centralized colors from `src/colors.py`

When creating or modifying ANY chart in this project, you MUST import and use colors
from `src/colors.py`. Never hardcode hex color values directly in chart code.

## Available palettes (import from `src/colors.py`)

```python
from src.colors import (
    CATEGORICAL_PALETTE,  # 8-color colorblind-safe sequence
    SEQUENTIAL_BLUES,     # 6-step light→dark for choropleth/heatmaps
    DOC_TYPE_COLORS,      # dict: doc type name → hex
    MODEL_COLORS,         # dict: "Rights-Based" / "Medical-Based" → hex
    REGION_COLORS,        # dict: region name → hex
    BUMP_COLORS,          # 10-color list for ranked trajectories
    TREND_COLORS,         # dict: "up"/"down"/"neutral"/"info" → hex
    COMPARE_PALETTE,      # 5-color list for country comparisons
    METRIC_COLORS,        # dict: metric name → hex
)
```

## Color assignments (DO NOT change these)

| Palette | Colors |
|---------|--------|
| Categorical | `#005BBB` `#D55E00` `#009E73` `#882255` `#56B4E9` `#E69F00` `#444444` `#CC3311` |
| Rights-Based | `#005BBB` (UN Blue) |
| Medical-Based | `#D55E00` (Vermillion) |
| Sequential Blues | `#C5DFEF` → `#8DBDE2` → `#5199D1` → `#005BBB` → `#004490` → `#002D62` |

## Rules

1. **Never hardcode colors** — always reference `src/colors.py` constants
2. **Rights vs Medical** — always use `MODEL_COLORS` dict. Rights = UN Blue, Medical = Vermillion
3. **Document types** — always use `DOC_TYPE_COLORS` dict
4. **Multi-series charts** — use `CATEGORICAL_PALETTE` or `color_discrete_sequence=CATEGORICAL_PALETTE`
5. **Choropleth maps** — use `SEQUENTIAL_BLUES` or Altair `scheme="blues"`
6. **Global Plotly template** already sets `colorway=CATEGORICAL_PALETTE` in `app.py`, so charts without explicit colors will use the correct palette automatically
7. **Contrast requirement** — all colors meet ≥3:1 against white (#FFF) per WCAG SC 1.4.11
8. **Do not use** Plotly built-in palettes like `Set2`, `Pastel`, `Plotly` — they are not WCAG compliant

## Example usage

```python
from src.colors import CATEGORICAL_PALETTE, MODEL_COLORS, DOC_TYPE_COLORS

# Multi-series bar chart
fig = px.bar(df, x="year", y="count", color="category",
             color_discrete_sequence=CATEGORICAL_PALETTE)

# Rights vs Medical
fig = px.area(df, x="year", y=["Rights-Based", "Medical-Based"],
              color_discrete_map=MODEL_COLORS)

# Document type chart
fig = px.bar(df, x="count", y="country", color="doc_type",
             color_discrete_map=DOC_TYPE_COLORS)
```
