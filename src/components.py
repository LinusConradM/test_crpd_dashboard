import numpy as np
import pandas as pd
import streamlit as st

from src.colors import CATEGORICAL_PALETTE


@st.cache_data
def _cached_sort(df_json: str, sort_col: str, ascending: bool) -> "pd.DataFrame":
    """Sort a DataFrame with caching to avoid recomputation on rerun."""
    _df = pd.read_json(df_json, orient="split")
    return _df.sort_values(sort_col, ascending=ascending).reset_index(drop=True)


def render_accessible_table(
    df,
    caption="",
    column_rename=None,
    first_col_bold=True,
    max_height=None,
    page_size=0,
    page_key="",
    sortable=False,
    sort_key="",
    searchable=False,
    search_key="",
):
    """Render a WCAG-compliant HTML table with auto-detected alignment.

    Numeric columns (int/float) are right-aligned; text columns left-aligned.
    First column uses <th scope="row"> for accessibility.

    Parameters
    ----------
    df : pd.DataFrame
        Data to render. Missing values are replaced with em dash (—).
    caption : str
        Accessible caption shown above the table.
    column_rename : dict | None
        Map raw column names to plain-language headers.
    first_col_bold : bool
        Whether the first column cells are bold (row headers).
    max_height : int | None
        Optional max height in px with vertical scroll.
    page_size : int
        Rows per page. 0 = no pagination (show all rows).
    page_key : str
        Unique key for pagination state. Required when page_size > 0.
    sortable : bool
        Enable column sorting via clickable headers.
    sort_key : str
        Unique key prefix for sort session state. Required when sortable.
    searchable : bool
        Show a text search bar above the table.
    search_key : str
        Unique key for search session state. Required when searchable.

    Called by all dashboard pages for Tier 2 table rendering.
    """
    if df is None or df.empty:
        st.info("No data available for this table.")
        return

    _df = df.copy().reset_index(drop=True)

    # ── Sort + Search controls (compact row above table) ──
    _sort_col_key = f"{sort_key}_col" if sort_key else "table_sort_col"
    _sort_dir_key = f"{sort_key}_dir" if sort_key else "table_sort_dir"
    _active_sort_col = None
    _sort_ascending = True

    _has_controls = searchable or (sortable and len(_df) > 1)
    if _has_controls:
        # Build column layout: search | sort-by | direction
        _ctrl_parts = []
        if searchable:
            _ctrl_parts.append(3)  # search gets more space
        if sortable and len(_df) > 1:
            _ctrl_parts.extend([2, 0.8])  # sort-by + asc/desc toggle
        _ctrl_cols = st.columns(_ctrl_parts, gap="small")

        _ci = 0
        if searchable:
            with _ctrl_cols[_ci]:
                _sk = search_key or "table_search"
                _query = st.text_input(
                    "Filter table",
                    placeholder="Search by States Party, region, or keyword...",
                    key=_sk,
                    label_visibility="collapsed",
                )
            _ci += 1
        else:
            _query = ""

        if sortable and len(_df) > 1:
            _sort_options = ["—", *list(_df.columns)]
            if _sort_col_key not in st.session_state:
                st.session_state[_sort_col_key] = "—"
            if _sort_dir_key not in st.session_state:
                st.session_state[_sort_dir_key] = True
            with _ctrl_cols[_ci]:
                _sel_sort = st.selectbox(
                    "Sort by",
                    _sort_options,
                    index=_sort_options.index(st.session_state[_sort_col_key])
                    if st.session_state[_sort_col_key] in _sort_options
                    else 0,
                    key=f"{sort_key}_sel",
                    label_visibility="collapsed",
                )
            with _ctrl_cols[_ci + 1]:
                _sel_dir = st.selectbox(
                    "Direction",
                    ["A→Z", "Z→A"],
                    index=0 if st.session_state[_sort_dir_key] else 1,
                    key=f"{sort_key}_dir_sel",
                    label_visibility="collapsed",
                )
            # Update session state if changed
            if _sel_sort != st.session_state[_sort_col_key]:
                st.session_state[_sort_col_key] = _sel_sort
                # Reset pagination on sort change
                _page_reset_key = page_key or "table_page"
                if page_size > 0 and _page_reset_key in st.session_state:
                    st.session_state[_page_reset_key] = 0
            st.session_state[_sort_dir_key] = _sel_dir == "A→Z"

            _active_sort_col = (
                st.session_state[_sort_col_key] if st.session_state[_sort_col_key] != "—" else None
            )
            _sort_ascending = st.session_state[_sort_dir_key]
    else:
        _query = ""

    # Apply search filter
    if searchable and _query and _query.strip():
        _mask = _df.apply(
            lambda row: row.astype(str).str.contains(_query.strip(), case=False, na=False).any(),
            axis=1,
        )
        _df = _df[_mask].reset_index(drop=True)
        st.caption(f"Showing {len(_df)} of {len(df)} rows matching '{_query.strip()}'")

    # Apply cached sort
    if sortable and _active_sort_col and _active_sort_col in _df.columns and len(_df) > 1:
        _df = _cached_sort(
            _df.to_json(orient="split"),
            _active_sort_col,
            _sort_ascending,
        )

    # ── Pagination ──
    _total_rows = len(_df)
    if page_size > 0 and _total_rows > page_size:
        _total_pages = (_total_rows + page_size - 1) // page_size
        _pk = page_key or "table_page"
        if _pk not in st.session_state:
            st.session_state[_pk] = 0
        _current_page = st.session_state[_pk]
        _current_page = max(0, min(_current_page, _total_pages - 1))
        _start = _current_page * page_size
        _end = min(_start + page_size, _total_rows)
        _df = _df.iloc[_start:_end].reset_index(drop=True)
    else:
        _total_pages = 1
        _current_page = 0
        _start = 0
        _end = _total_rows
        _pk = None

    # Detect numeric columns BEFORE converting to object (preserves dtype info)
    _numeric_cols = set()
    for col in _df.columns:
        if _df[col].dtype in (np.int64, np.int32, np.float64, np.float32, int, float):
            _numeric_cols.add(col)
        elif hasattr(_df[col].dtype, "numpy_dtype"):
            # Handle pandas nullable types like Int64, Float64
            nd = _df[col].dtype.numpy_dtype
            if np.issubdtype(nd, np.integer) or np.issubdtype(nd, np.floating):
                _numeric_cols.add(col)

    # Convert all columns to object so fillna("—") works on nullable Int64/Float64
    _df = _df.astype(object)

    # Replace missing values with em dash (suppress FutureWarning)
    with pd.option_context("future.no_silent_downcasting", True):
        _df = _df.fillna("—")
        _df = _df.replace(["", "nan", "None", "NaN"], "—")

    # Apply column renaming
    if column_rename:
        _df = _df.rename(columns=column_rename)

    # Map pre-rename numeric columns to post-rename names
    if column_rename:
        _numeric_cols = {column_rename.get(c, c) for c in _numeric_cols}

    # Also detect string columns that look numeric (formatted numbers like "11,795")
    for col in _df.columns:
        if col not in _numeric_cols:
            sample = (
                _df[col]
                .astype(str)
                .str.replace(",", "")
                .str.replace(".", "")
                .str.replace("-", "")
                .str.replace("%", "")
            )
            try:
                if sample.str.isnumeric().mean() > 0.7 and len(_df) > 0:
                    _numeric_cols.add(col)
            except (ValueError, TypeError):
                pass

    # Build alignment map
    _align = {}
    for col in _df.columns:
        if col in _numeric_cols:
            _align[col] = "right"
        else:
            _align[col] = "left"

    # Style constants from colors.py
    _header_bg = CATEGORICAL_PALETTE[0]  # UN Blue
    _zebra_bg = "#f0f4f8"

    # Container — always scroll horizontally; optionally cap height
    _scroll_parts = ["overflow-x:auto;"]
    if max_height:
        _scroll_parts.append(f"max-height:{max_height}px;overflow-y:auto;")

    # Build HTML
    parts = []
    # Scroll container with a11y: role, label, keyboard focus
    _aria_label = caption if caption else "Data table"
    parts.append(
        f'<div role="region" aria-label="{_aria_label}" tabindex="0" '
        f'style="{"".join(_scroll_parts)}">'
    )

    parts.append(
        '<table role="table" class="crpd-table" '
        'style="width:100%;border-collapse:collapse;'
        'font-family:Inter,sans-serif;font-size:14px;">'
    )

    if caption:
        parts.append(
            f'<caption style="text-align:left;font-size:13px;'
            f'padding:6px 0;color:#555;caption-side:top;">'
            f"{caption}</caption>"
        )

    # Header row (with optional sort indicators)
    parts.append("<thead><tr>")
    for col in _df.columns:
        align = _align.get(col, "left")
        # Sort indicator and aria-sort
        _aria_sort = ""
        _sort_arrow = ""
        if sortable and _active_sort_col == col:
            if _sort_ascending:
                _aria_sort = ' aria-sort="ascending"'
                _sort_arrow = " &#9652;"  # ▴ small up triangle
            else:
                _aria_sort = ' aria-sort="descending"'
                _sort_arrow = " &#9662;"  # ▾ small down triangle
        _cursor = "cursor:pointer;" if sortable else ""
        parts.append(
            f'<th scope="col"{_aria_sort} style="text-align:{align};'
            f"padding:8px 10px;background:{_header_bg};"
            f"color:#fff;font-weight:600;{_cursor}"
            f"position:sticky;top:0;z-index:1;"
            f'font-size:13px;border-bottom:2px solid {_header_bg};">'
            f"{col}{_sort_arrow}</th>"
        )
    parts.append("</tr></thead><tbody>")

    # Data rows
    for i, (_, row) in enumerate(_df.iterrows()):
        row_bg = _zebra_bg if i % 2 == 1 else "#fff"
        parts.append(f'<tr style="background:{row_bg};">')
        for j, col in enumerate(_df.columns):
            _raw = row[col]
            # Global: cap float display at 2 decimal places
            if isinstance(_raw, float):
                # Use up to 2 decimals, strip trailing zeros
                cell = f"{_raw:.2f}".rstrip("0").rstrip(".")
            elif isinstance(_raw, int | np.integer):
                # Detect year values — skip comma formatting
                _col_lower = col.lower()
                _is_year = "year" in _col_lower or (1900 <= _raw <= 2100)
                cell = str(int(_raw)) if _is_year else f"{_raw:,}"
            else:
                cell = str(_raw)
            align = _align.get(col, "left")
            # nowrap on first column, numeric columns, and short-value
            # columns (year ranges, percentiles) that should never break
            _nowrap = (
                j == 0
                or col in _numeric_cols
                or "year" in col.lower()
                or "percentile" in col.lower()
            )
            wrap = "white-space:nowrap;" if _nowrap else ""
            if j == 0 and first_col_bold:
                parts.append(
                    f'<th scope="row" style="text-align:{align};'
                    f"padding:8px 10px;{wrap}font-weight:600;"
                    f'border-bottom:1px solid #e0e0e0;">'
                    f"{cell}</th>"
                )
            else:
                parts.append(
                    f'<td style="text-align:{align};'
                    f"padding:8px 10px;{wrap}"
                    f'border-bottom:1px solid #e0e0e0;">'
                    f"{cell}</td>"
                )
        parts.append("</tr>")

    parts.append("</tbody></table></div>")

    st.markdown("".join(parts), unsafe_allow_html=True)

    # ── Pagination controls (right-aligned) ──
    if _pk and _total_pages > 1:
        _p_cols = st.columns([3, 1, 1])
        with _p_cols[0]:
            st.markdown(
                f"<div style='text-align:left;padding:6px 0;"
                f"font-family:Inter,sans-serif;font-size:13px;color:#555;'>"
                f"Page {_current_page + 1} of {_total_pages}"
                f" &middot; Rows {_start + 1}–{_end} of {_total_rows}"
                f"</div>",
                unsafe_allow_html=True,
            )
        with _p_cols[1]:
            if st.button(
                "Previous",
                key=f"{_pk}_prev",
                disabled=_current_page == 0,
                width="stretch",
            ):
                st.session_state[_pk] = _current_page - 1
                st.rerun()
        with _p_cols[2]:
            if st.button(
                "Next",
                key=f"{_pk}_next",
                disabled=_current_page >= _total_pages - 1,
                width="stretch",
            ):
                st.session_state[_pk] = _current_page + 1
                st.rerun()


def create_metric_card(
    icon, value, label, trend=None, color="#0056B3", trend_direction="default", sparkline=""
):
    """Create a styled metric card with icon, value, label, and optional trend.

    trend_direction: 'default' (up=green, down=red),
                     'inverse' (up=red, down=green),
                     'neutral' (always muted gray)
    """
    trend_html = ""
    if trend and str(trend).strip():
        _trend_text = str(trend)
        if trend_direction == "neutral":
            trend_class = "trend-neutral-info"
        elif trend_direction == "inverse":
            trend_class = (
                "trend-down"
                if "\u2191" in _trend_text
                else "trend-up"
                if "\u2193" in _trend_text
                else "trend-neutral"
            )
        else:
            trend_class = (
                "trend-up"
                if "\u2191" in _trend_text
                else "trend-down"
                if "\u2193" in _trend_text
                else "trend-neutral"
            )
        # Sanitize text content only (not the wrapper tag)
        _safe = _trend_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        trend_html = (
            f'<span class="metric-trend {trend_class}" '
            f'style="display:block;font-size:0.875rem;font-weight:600;'
            f"margin-top:8px;padding:6px 8px;background:#F2F4F8;"
            f'border-radius:0.5rem;width:100%;">'
            f"{_safe}</span>"
        )

    # ARIA role and label for accessibility
    _aria_label = f"{value} {label}".replace('"', "&quot;")
    return (
        f'<div class="metric-card" role="group" aria-label="{_aria_label}">'
        f'<div class="metric-icon">{icon}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-label">{label}</div>'
        f"{sparkline}{trend_html}</div>"
    )


def make_sparkline(values, width=80, height=20, color="#003F87"):
    """Generate an inline SVG sparkline from a list of numeric values.

    Parameters
    ----------
    values : list[int | float]
        Ordered data points (e.g., yearly counts).
    width, height : int
        SVG dimensions in pixels.
    color : str
        Stroke color for the line.

    Returns
    -------
    str
        HTML string with an inline SVG sparkline, or "" if fewer than 2 values.
    """
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return ""
    _min = min(vals)
    _max = max(vals)
    _range = _max - _min if _max != _min else 1
    _pad = 2
    _w = width - _pad * 2
    _h = height - _pad * 2
    points = []
    for i, v in enumerate(vals):
        x = _pad + (_w * i / (len(vals) - 1))
        y = _pad + _h - (_h * (v - _min) / _range)
        points.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(points)
    return (
        f'<svg width="{width}" height="{height}" aria-hidden="true" '
        f'style="display:block;margin:4px auto 0 auto;">'
        f'<polyline points="{polyline}" fill="none" '
        f'stroke="{color}" stroke-width="1.5" stroke-linecap="round" '
        f'stroke-linejoin="round"/></svg>'
    )


def pct_trend(early_val, late_val, early_label="", n_early=None, n_late=None):
    """Calculate percentage trend between two period values.

    Parameters
    ----------
    n_early, n_late : int | None
        Sample sizes for early/late periods. Appended to trend text when provided.
    """
    if early_val and early_val > 0:
        pct = (late_val - early_val) / early_val * 100
        arrow = "\u2191" if pct > 0 else "\u2193" if pct < 0 else "\u2192"
        period = f"vs {early_label}" if early_label else "vs earlier period"
        text = f"{arrow} {abs(pct):.0f}% {period}"
        if n_early is not None and n_late is not None:
            text += f" (n={n_early}, {n_late})"
        return text
    return " "


def create_finding_stat(value, label, trend=None):
    """Create a compact stat highlight for use inside finding cards."""
    trend_html = f'<div class="owid-finding-stat-trend">{trend}</div>' if trend else ""
    return (
        f'<div class="owid-finding-stat">'
        f'<div class="owid-finding-stat-value">{value}</div>'
        f'<div class="owid-finding-stat-label">{label}</div>'
        f"{trend_html}</div>"
    )
