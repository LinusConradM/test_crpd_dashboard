import streamlit as st

from src.analysis import count_phrases
from src.data_loader import get_custom_organizations, get_dataset_stats


# ── Filter panel CSS ─────────────────────────────────────────────────────────

FILTER_PANEL_CSS = """
<style>
    /* ── Font consistency for all filter widgets ── */
    [data-testid="stSelectbox"] label,
    [data-testid="stMultiSelect"] label,
    [data-testid="stSlider"] label,
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stMultiSelect"] > div > div,
    [data-testid="stMultiSelect"] span[data-baseweb="tag"],
    [data-testid="stSelectbox"] span,
    [data-testid="stSelectbox"] div[data-baseweb="select"] * {
        font-family: 'Inter', Arial, sans-serif !important;
    }

    /* ── Uppercase micro-labels — muted primary ── */
    [data-testid="stSelectbox"] label,
    [data-testid="stMultiSelect"] label,
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] p {
        font-size: 11px !important;
        font-weight: 700 !important;
        color: rgba(0, 30, 64, 0.55) !important;
        margin-bottom: 6px !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
    }

    /* ── Dropdown inputs — taller, light gray bg ── */
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stMultiSelect"] > div > div {
        font-size: 0.875rem !important;
        min-height: 48px !important;
        padding-top: 6px !important;
        padding-bottom: 6px !important;
        background: #F2F4F6 !important;
        border: none !important;
        border-radius: 0.5rem !important;
    }
    [data-testid="stSelectbox"] > div > div:hover,
    [data-testid="stMultiSelect"] > div > div:hover {
        background: #ECEEF0 !important;
    }
    [data-testid="stSelectbox"] > div > div:focus-within,
    [data-testid="stMultiSelect"] > div > div:focus-within {
        background: #ECEEF0 !important;
        box-shadow: 0 0 0 2px rgba(0, 63, 135, 0.12) !important;
    }

    /* ── All filter widget labels — black, compact spacing ── */
    [data-testid="stSelectbox"] label,
    [data-testid="stMultiSelect"] label,
    [data-testid="stSlider"] label {
        margin-bottom: 6px !important;
        padding: 0 !important;
    }
    [data-testid="stSelectbox"] label p,
    [data-testid="stMultiSelect"] label p,
    [data-testid="stSlider"] label p {
        color: #000000 !important;
        font-weight: 700 !important;
        font-size: 11px !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.2 !important;
    }

    /* ── Multiselect tag pills — UN Blue ── */
    [data-testid="stMultiSelect"] span[data-baseweb="tag"] {
        background: linear-gradient(135deg, #003F87, #0056B3) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 4px !important;
    }
    [data-testid="stMultiSelect"] span[data-baseweb="tag"] span {
        color: #ffffff !important;
    }
    [data-testid="stMultiSelect"] span[data-baseweb="tag"] svg {
        fill: #ffffff !important;
    }

    /* ── Region popover — align with native Streamlit widget labels ── */
    [data-testid="stPopover"] {
        margin-top: -4px !important;
    }
    [data-testid="stPopover"] button {
        font-family: 'Inter', Arial, sans-serif !important;
        font-size: 0.875rem !important;
        font-weight: 400 !important;
        min-height: 48px !important;
        background: #F2F4F6 !important;
        border: none !important;
        border-radius: 0.5rem !important;
    }
    [data-testid="stPopover"] button:hover {
        background: #ECEEF0 !important;
    }

    /* ── Active-state blue fill for Region popover ── */
    .region-active [data-testid="stPopover"] button {
        background: linear-gradient(135deg, #003F87, #0056B3) !important;
        color: #ffffff !important;
        font-weight: 500 !important;
    }
    .region-active [data-testid="stPopover"] button:hover {
        background: linear-gradient(135deg, #002D6B, #004A9E) !important;
    }
    .region-active [data-testid="stPopover"] button svg {
        fill: #ffffff !important;
    }

    /* ── Active-state blue fill for Country selectbox ── */
    .country-active [data-testid="stSelectbox"] > div > div {
        background: linear-gradient(135deg, #003F87, #0056B3) !important;
        color: #ffffff !important;
        font-weight: 500 !important;
    }
    .country-active [data-testid="stSelectbox"] > div > div:hover {
        background: linear-gradient(135deg, #002D6B, #004A9E) !important;
    }
    .country-active [data-testid="stSelectbox"] span,
    .country-active [data-testid="stSelectbox"] div[data-baseweb="select"] * {
        color: #ffffff !important;
    }
    .country-active [data-testid="stSelectbox"] svg {
        fill: #ffffff !important;
    }
    [data-testid="stRadio"] label p,
    [data-testid="stRadio"] p {
        white-space: nowrap !important;
        overflow: visible !important;
    }

    /* ── Slider styling — UN Blue track and thumbs ── */
    [data-testid="stSlider"] [data-testid="stTickBarMin"],
    [data-testid="stSlider"] [data-testid="stTickBarMax"] {
        display: none !important;
    }
    [data-testid="stSlider"] [role="slider"] {
        background: #003F87 !important;
        border-color: #003F87 !important;
    }
    [data-testid="stSlider"] [data-testid="stThumbValue"] {
        color: #003F87 !important;
        font-weight: 700 !important;
    }

    /* ── Vertically align all filter columns ── */
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-end !important;
    }

    /* ── Filter panel container — light gray background, spacious ── */
    [data-testid="stVerticalBlockBorderWrapper"] {
        padding: 24px 28px !important;
        background: #FFFFFF !important;
        border: 1px solid rgba(194, 198, 212, 0.2) !important;
        border-radius: 1rem !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    }

    /* ── Filter panel header ── */
    .filter-panel-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        margin-bottom: 10px;
        padding-bottom: 12px;
        border-bottom: 1px solid rgba(194, 198, 212, 0.25);
    }
    .filter-panel-title {
        font-family: 'Inter', Arial, sans-serif;
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #003F87;
        line-height: 1.3;
    }
    .filter-panel-subtitle {
        font-family: 'Inter', Arial, sans-serif;
        font-size: 13px;
        font-weight: 500;
        color: #43474F;
        margin-top: 4px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .coverage-badge {
        font-family: 'Inter', Arial, sans-serif;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #001E40;
        background: #E0E3E5;
        padding: 3px 10px;
        border-radius: 9999px;
        white-space: nowrap;
    }
</style>
"""

DOC_TYPE_DISPLAY_MAP = {
    "State Report": "State Report",
    "List of Issues (LOI)": "List of Issues (LOI)",
    "Written Reply": "Written Reply",
    "Concluding Observations": "Concluding Observations",
    "Response to Concluding Observations": "Response to Concluding Observations",
}

DOC_TYPE_ORDER = [
    "State Report",
    "List of Issues (LOI)",
    "Written Reply",
    "Concluding Observations",
    "Response to Concluding Observations",
]


def filter_df(
    df, geo_region, org_region, country, doc_types, year_range, year_bounds=None, year_list=None
):
    d = df.copy()
    orgs = get_custom_organizations()
    if geo_region and geo_region != "All":
        d = d[d["region"] == geo_region]
    if org_region and org_region != "All":
        d = d[d["iso3"].isin(orgs.get(org_region, []))]

    if country and country != "All":
        d = d[d["country"] == country]
    if doc_types:
        d = d[d["doc_type"].isin(doc_types)]
    if "year" in d.columns:
        if year_list is not None:
            # Specific years selected — filter to exactly those years
            d = d[d["year"].isin(year_list)]
        elif year_range:
            ymin, ymax = year_range
            year_is_default = year_bounds is not None and year_range == year_bounds
            if year_is_default:
                d = d[d["year"].isna() | ((d["year"] >= ymin) & (d["year"] <= ymax))]
            else:
                d = d[(d["year"] >= ymin) & (d["year"] <= ymax)]
    return d


def render_inline_filter_panel(df_all, ARTICLE_PRESETS):
    """Render a compact horizontal filter bar and return filtered DataFrame."""

    st.markdown(FILTER_PANEL_CSS, unsafe_allow_html=True)

    # Build region/org options — normalize legacy values and drop Unknown
    raw_regions = (
        df_all["region"]
        .dropna()
        .replace("America", "Americas")  # normalize legacy entries
        .unique()
    )
    geo_regions = ["All", *sorted(r for r in raw_regions if r != "Unknown")]
    orgs = get_custom_organizations()
    org_names = sorted(orgs.keys())

    # Doc type options (with "All Types" smart toggle)
    doc_types_raw = df_all["doc_type"].unique()
    doc_types_ordered = [dt for dt in DOC_TYPE_ORDER if dt in doc_types_raw]
    doc_types_individual = [DOC_TYPE_DISPLAY_MAP.get(dt, dt.title()) for dt in doc_types_ordered]
    doc_types_with_all = ["All Types", *doc_types_individual]

    # Year bounds
    if "year" in df_all.columns:
        ymin, ymax = int(df_all["year"].min()), int(df_all["year"].max())
    else:
        ymin, ymax = 0, 0

    # Article options
    article_list = [
        "All Articles",
        *sorted(list(ARTICLE_PRESETS.keys()), key=lambda x: int(x.split()[1])),
    ]

    # ── Smart Filter Panel ──
    _s = get_dataset_stats()
    with st.container(border=True):
        # Header row: title (left) + count badge placeholder (right)
        header_slot = st.empty()
        c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1.4, 1.2, 1.4])

        with c1:
            # Build a dynamic label showing active selection(s)
            geo_val = st.session_state.get("th_geo_region", "All")
            org_val = st.session_state.get("th_org_region", "All")
            active = [v for v in [geo_val, org_val] if v != "All"]
            btn_label = "Region: " + " + ".join(active) if active else "Region"

            region_active = "region-active" if active else ""
            st.markdown(
                f"<div class='{region_active}'>"
                "<div style='font-size:11px;font-weight:700;color:#000000;"
                "text-transform:uppercase;letter-spacing:1.5px;margin:0 0 6px 0;"
                "line-height:1.2;padding:0;"
                "font-family:Inter,Arial,sans-serif'>Region</div>",
                unsafe_allow_html=True,
            )
            with st.popover(btn_label, width="stretch"):
                gc, oc = st.columns(2, gap="small")
                with gc:
                    st.radio("Geographic", geo_regions, key="th_geo_region")
                with oc:
                    st.radio("Organization", ["All", *org_names], key="th_org_region")
            st.markdown("</div>", unsafe_allow_html=True)

            geo_region = st.session_state.get("th_geo_region", "All")
            org_region = st.session_state.get("th_org_region", "All")

        # Dynamic country list — narrowed by whichever region filters are active
        base = df_all.copy()
        if geo_region != "All":
            base = base[base["region"] == geo_region]
        if org_region != "All":
            base = base[base["iso3"].isin(orgs.get(org_region, []))]
        countries_list = ["All", *sorted(base["country"].dropna().unique())]

        _lbl = (
            "<div style='font-size:11px;font-weight:700;color:#000000;"
            "text-transform:uppercase;letter-spacing:1.5px;margin:0 0 6px 0;"
            "line-height:1.2;padding:0;font-family:Inter,Arial,sans-serif'>"
        )

        with c2:
            country_cls = (
                "country-active" if st.session_state.get("th_country", "All") != "All" else ""
            )
            st.markdown(
                f"<div class='{country_cls}'>{_lbl}Country</div>",
                unsafe_allow_html=True,
            )
            country = st.selectbox(
                "Country",
                countries_list,
                index=0,
                key="th_country",
                label_visibility="collapsed",
            )
            st.markdown("</div>", unsafe_allow_html=True)

        # Document Type (smart "All Types" toggle)
        with c3:
            st.markdown(f"{_lbl}Document Type</div>", unsafe_allow_html=True)
            selected_doc_raw = st.multiselect(
                "Document Type",
                doc_types_with_all,
                default=["All Types"],
                key="th_doc_types",
                label_visibility="collapsed",
            )

        # Smart toggle: "All Types" means all doc types
        reverse_map = {v: k for k, v in DOC_TYPE_DISPLAY_MAP.items()}
        if "All Types" in selected_doc_raw:
            doc_types = [reverse_map.get(dt, dt.lower()) for dt in doc_types_individual]
        else:
            doc_types = [reverse_map.get(dt, dt.lower()) for dt in selected_doc_raw]

        with c4:
            st.markdown(f"{_lbl}Years</div>", unsafe_allow_html=True)
            if "year" in df_all.columns:
                available_years = sorted(df_all["year"].dropna().unique().astype(int))
                year_range = st.select_slider(
                    "Years",
                    options=available_years,
                    value=(ymin, ymax),
                    key="th_years",
                    label_visibility="collapsed",
                )
                year_list = None
            else:
                year_range = None
                year_list = None

        with c5:
            st.markdown(f"{_lbl}Articles</div>", unsafe_allow_html=True)
            selected_articles = st.multiselect(
                "Articles",
                article_list,
                default=["All Articles"],
                key="th_articles",
                label_visibility="collapsed",
            )

        pass  # end of filter columns

        pass  # end of container

    if not selected_doc_raw:
        st.warning("No document types selected. Select at least one to see results.")

    # ── Apply filters ──
    df = filter_df(
        df_all,
        geo_region,
        org_region,
        country,
        doc_types,
        year_range,
        year_bounds=(ymin, ymax),
        year_list=year_list,
    )

    # Apply article filter
    if selected_articles and "All Articles" not in selected_articles:
        article_keywords = []
        for art in selected_articles:
            if art in ARTICLE_PRESETS:
                article_keywords.extend(ARTICLE_PRESETS[art])
        if article_keywords:
            mask = df["clean_text"].apply(lambda t: count_phrases(t, article_keywords) > 0)
            df = df[mask]

    # ── Render header (no count badge) ──
    with header_slot:
        st.markdown(
            "<div class='filter-panel-header'>"
            "<div class='filter-panel-title'>Filter Parameters</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    return df
