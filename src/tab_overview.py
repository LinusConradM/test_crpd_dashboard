from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.analysis import article_frequency, generate_smart_insights, model_shift_table
from src.colors import BUMP_COLORS, CATEGORICAL_PALETTE, MODEL_COLORS
from src.components import create_metric_card, make_sparkline, pct_trend
from src.data_loader import get_dataset_stats
from src.llm import (
    OLLAMA_MODEL,
    build_data_context,
    generate_insights_local,
    get_remaining_calls,
)


def _svg_icon(path_d, size=20, color="#003F87"):
    """Return a small inline SVG icon with aria-hidden for accessibility."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{path_d}</svg>'
    )


# Reusable SVG icon paths (Feather-style)
_ICON_DOCS = _svg_icon(
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>'
)
_ICON_GLOBE = _svg_icon(
    '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10A15.3 15.3 0 0 1 12 2z"/>'
)
_ICON_BOOK = _svg_icon(
    '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>'
)
_ICON_TEXT = _svg_icon(
    '<line x1="17" y1="10" x2="3" y2="10"/><line x1="21" y1="6" x2="3" y2="6"/><line x1="21" y1="14" x2="3" y2="14"/><line x1="17" y1="18" x2="3" y2="18"/>'
)
_ICON_SCALE = _svg_icon(
    '<path d="M12 3v18"/><path d="M5 6l7-3 7 3"/><path d="M2 12l3-6 3 6"/><path d="M16 12l3-6 3 6"/><circle cx="5" cy="12" r="3"/><circle cx="19" cy="12" r="3"/>',
    color="#003F87",
)
_ICON_RATIO = _svg_icon(
    '<circle cx="12" cy="12" r="10"/><line x1="8" y1="12" x2="16" y2="12"/><line x1="12" y1="8" x2="12" y2="16"/>'
)
_ICON_ALERT = _svg_icon(
    '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    color="#D55E00",
)


def render(df, df_all, ARTICLE_PRESETS):
    # Calculate metrics
    total_docs = len(df)
    total_countries = df["country"].nunique()
    # Active Reporting Cycle — States Parties with docs in last 3 years
    _current_year = datetime.now().year
    _3yr_recent = df[df["year"] >= _current_year - 3]["country"].nunique()
    _3yr_earlier = df[(df["year"] >= _current_year - 6) & (df["year"] < _current_year - 3)][
        "country"
    ].nunique()
    # --- Dynamic trend calculations (early vs late period split) ---
    if "year" in df.columns and len(df) >= 4:
        sorted_years = sorted(df["year"].dropna().unique())
        mid_year = sorted_years[len(sorted_years) // 2]
        df_early = df[df["year"] < mid_year]
        df_late = df[df["year"] >= mid_year]

        early_label = f"{int(sorted_years[0])}–{int(mid_year) - 1}"

        _n_early = len(df_early)
        _n_late = len(df_late)
        # Normalize to per-year rates to avoid misleading trends from unequal periods
        _n_years_early = max(df_early["year"].nunique(), 1)
        _n_years_late = max(df_late["year"].nunique(), 1)
        _rate_early = round(_n_early / _n_years_early, 1)
        _rate_late = round(_n_late / _n_years_late, 1)
        docs_trend = pct_trend(
            _rate_early,
            _rate_late,
            early_label,
            n_early=_n_early,
            n_late=_n_late,
        )

        early_countries = df_early["country"].nunique()
        late_countries = df_late["country"].nunique()
        diff = late_countries - early_countries
        if diff > 0:
            countries_trend = f"\u2191 {diff} more vs {early_label}"
        elif diff < 0:
            countries_trend = f"\u2193 {abs(diff)} fewer vs {early_label}"
        else:
            countries_trend = f"\u2192 Same across {early_label}"

        # Active Reporting Cycle trend (3-year windows)
        _active_diff = _3yr_recent - _3yr_earlier
        _prior_3yr = f"{_current_year - 6}–{_current_year - 4}"
        if _active_diff > 0:
            active_trend = f"↑ {_active_diff} more vs {_prior_3yr}"
            _active_direction = "up"
        elif _active_diff < 0:
            active_trend = f"↓ {abs(_active_diff)} fewer vs {_prior_3yr}"
            _active_direction = "down"
        else:
            active_trend = f"→ Same as {_prior_3yr}"
            _active_direction = "neutral"
    else:
        docs_trend = " "
        countries_trend = " "
        active_trend = " "
        _active_direction = "neutral"
        early_label = ""

    # Committee Response Rate — State Reports that received Concluding Observations
    _sr_countries = df[df["doc_type"] == "State Report"]["country"].unique()
    _co_countries = df[df["doc_type"] == "Concluding Observations"]["country"].unique()
    _responded = set(_sr_countries) & set(_co_countries)
    _response_rate = (
        round(len(_responded) / len(_sr_countries) * 100) if len(_sr_countries) > 0 else 0
    )

    if "year" in df.columns and len(df) >= 4:
        _early_range = f"{int(sorted_years[0])}–{int(mid_year) - 1}"
        _recent_range = f"{int(mid_year)}–{int(sorted_years[-1])}"

        _sr_early = df[(df["doc_type"] == "State Report") & (df["year"] < mid_year)][
            "country"
        ].unique()
        _co_early = df[(df["doc_type"] == "Concluding Observations") & (df["year"] < mid_year)][
            "country"
        ].unique()
        _rate_early = (
            round(len(set(_sr_early) & set(_co_early)) / len(_sr_early) * 100)
            if len(_sr_early) > 0
            else 0
        )

        _sr_recent = df[(df["doc_type"] == "State Report") & (df["year"] >= mid_year)][
            "country"
        ].unique()
        _co_recent = df[(df["doc_type"] == "Concluding Observations") & (df["year"] >= mid_year)][
            "country"
        ].unique()
        _rate_recent = (
            round(len(set(_sr_recent) & set(_co_recent)) / len(_sr_recent) * 100)
            if len(_sr_recent) > 0
            else 0
        )

        _rate_diff = _rate_recent - _rate_early
        if _rate_diff > 0:
            cr_trend = f"↑ {_rate_diff}pp vs {_early_range}"
            _cr_direction = "up"
        elif _rate_diff < 0:
            cr_trend = f"↓ {abs(_rate_diff)}pp vs {_early_range}"
            _cr_direction = "down"
        else:
            cr_trend = f"→ Same as {_early_range}"
            _cr_direction = "neutral"
    else:
        cr_trend = " "
        _cr_direction = "neutral"

    # Row 1: Data Coverage Metrics
    st.markdown(
        """
        <div style="
            font-size: 0.95rem;
            font-weight: 700;
            color: #003F87;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 20px;
            padding-bottom: 8px;
            border-bottom: 2px solid #003F87;
            width: 100%;
        ">
            AT A GLANCE
        </div>
    """,
        unsafe_allow_html=True,
    )

    # Data timestamp (year_max from full dataset; counts from filtered df)
    _stats = get_dataset_stats()
    st.caption(
        f"Data current through {_stats['year_max']} \u00b7 "
        f"Showing {total_countries} States Parties \u00b7 "
        f"{total_docs} documents"
    )

    # Fix 2: Methodology caveat
    st.markdown(
        "<div style='font-size:14px;color:#5a6377;font-family:Inter,sans-serif;"
        "margin-bottom:0.5rem;'>"
        "Metrics derived from keyword-based text analysis of UN treaty body documents. "
        "<a href='/about' style='color:#003F87;'>See methodology</a>."
        "</div>",
        unsafe_allow_html=True,
    )

    # Compute sparkline data for numeric metric cards
    _spark_docs = ""
    _spark_countries = ""
    if "year" in df.columns and len(df) >= 4:
        _yr_docs = df.groupby("year").size().sort_index().tolist()
        _spark_docs = make_sparkline(_yr_docs)
        _yr_countries = df.groupby("year")["country"].nunique().sort_index().tolist()
        _spark_countries = make_sparkline(_yr_countries)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            create_metric_card(
                _ICON_DOCS,
                f"{total_docs:,}",
                "Total Documents",
                trend=docs_trend,
            ),
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            create_metric_card(
                _ICON_GLOBE,
                f"{total_countries:,}",
                "States Parties",
                trend=countries_trend,
            ),
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            create_metric_card(
                "🔄",
                f"{_3yr_recent}",
                "Active Reporting Cycle",
                trend=active_trend,
                trend_direction=_active_direction,
            ),
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            create_metric_card(
                "📋",
                f"{_response_rate}%",
                "Committee Response Rate",
                trend=cr_trend,
                trend_direction=_cr_direction,
            ),
            unsafe_allow_html=True,
        )

    # Row 2: Implementation Insights
    col1, col2, col3, col4 = st.columns(4)

    # Calculate additional metrics
    if len(df):
        art_freq = article_frequency(df, ARTICLE_PRESETS)
        if not art_freq.empty:
            # Exclude Article 1 (Purpose) — universally mentioned, not insightful
            art_freq_filtered = art_freq[~art_freq["article"].str.startswith("Article 1")]
            if not art_freq_filtered.empty:
                top_article_full = art_freq_filtered.groupby("article")["count"].sum().idxmax()
            else:
                top_article_full = art_freq.groupby("article")["count"].sum().idxmax()
            top_article_short = top_article_full.split("—")[0].strip()

            # Least referenced article (excluding Article 1)
            least_article_full = art_freq_filtered.groupby("article")["count"].sum().idxmin()
            least_article_short = least_article_full.split("—")[0].strip()
        else:
            top_article_short = "N/A"
            least_article_full = "N/A"
            least_article_short = "N/A"

        mt = model_shift_table(df)
        if len(mt):
            rights_pct = mt["rights"].sum() / (mt["rights"].sum() + mt["medical"].sum()) * 100
        else:
            rights_pct = 0

        review_rate = f"{round(total_docs / total_countries)}" if total_countries > 0 else "N/A"

        # Dynamic trends for Row 2
        if "year" in df.columns and len(df) >= 4:
            mt_early = model_shift_table(df_early)
            mt_late = model_shift_table(df_late)
            if len(mt_early) and len(mt_late):
                early_r = mt_early["rights"].sum()
                early_m = mt_early["medical"].sum()
                late_r = mt_late["rights"].sum()
                late_m = mt_late["medical"].sum()
                early_rights_pct = (
                    (early_r / (early_r + early_m) * 100) if (early_r + early_m) > 0 else 0
                )
                late_rights_pct = (late_r / (late_r + late_m) * 100) if (late_r + late_m) > 0 else 0
                rights_trend = pct_trend(early_rights_pct, late_rights_pct, early_label)
            else:
                rights_trend = " "

            # Docs per country trend (whole numbers)
            early_rate = (
                round(len(df_early) / df_early["country"].nunique())
                if df_early["country"].nunique() > 0
                else 0
            )
            late_rate = (
                round(len(df_late) / df_late["country"].nunique())
                if df_late["country"].nunique() > 0
                else 0
            )
            diff_rate = late_rate - early_rate
            if diff_rate > 0:
                rate_trend = f"↑ {diff_rate} more per country vs {early_label}"
            elif diff_rate < 0:
                rate_trend = f"↓ {abs(diff_rate)} fewer per country vs {early_label}"
            else:
                rate_trend = "→ Same rate both periods"
        else:
            rights_trend = " "
            rate_trend = " "
    else:
        art_freq = None
        mt = None
        top_article_short = "N/A"
        top_article_full = "N/A"
        least_article_full = "N/A"
        least_article_short = "N/A"
        rights_pct = 0
        review_rate = "N/A"
        rights_trend = " "
        rate_trend = " "

    with col1:
        _article_trend = (
            top_article_full if len(top_article_full) <= 48 else top_article_full[:45] + "…"
        )
        st.markdown(
            create_metric_card(
                _ICON_BOOK,
                top_article_short,
                "Most Referenced Article",
                trend=_article_trend,
                trend_direction="neutral",
            ),
            unsafe_allow_html=True,
        )

    with col2:
        _least_trend = (
            least_article_full if len(least_article_full) <= 48 else least_article_full[:45] + "…"
        )
        st.markdown(
            create_metric_card(
                _ICON_ALERT,
                least_article_short,
                "Least Referenced Article",
                trend=_least_trend,
                trend_direction="neutral",
            ),
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            create_metric_card(
                _ICON_SCALE,
                f"{rights_pct:.1f}%",
                "Rights vs. Medical Keywords",
                trend=rights_trend,
            ),
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            create_metric_card(
                _ICON_RATIO,
                review_rate,
                "Documents per State Party",
                trend=rate_trend,
                trend_direction="neutral",
            ),
            unsafe_allow_html=True,
        )

    # "Find your country" CTA — moved to after first chart section (Fix 14)

    st.markdown(
        """
<style>
    /* ── OWID Hero stats row ── */
    .owid-hero-stats {
        display: flex;
        justify-content: center;
        gap: 2.5rem;
        margin: 0.5rem 0 2rem;
        flex-wrap: wrap;
    }
    .owid-stat {
        text-align: center;
    }
    .owid-stat-value {
        font-family: 'Inter', sans-serif;
        font-size: clamp(2rem, 4vw, 3rem);
        font-weight: 800;
        color: #191C1F;
        line-height: 1;
    }
    .owid-stat-label {
        font-size: 0.875rem;
        color: #424752;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-top: 0.3rem;
    }

    /* ── Section headers ── */
    .owid-section-title {
        font-family: 'Inter', Arial, sans-serif;
        font-size: 1.15rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #003F87;
        margin: 2.5rem 0 1.5rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #003F87;
    }

    /* ── Finding cards (narrative + chart) ── */
    .owid-finding {
        background: #ffffff;
        border-radius: 12px;
        padding: 2rem 2rem 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 24px rgba(100, 116, 145, 0.06);
        border: none;
    }
    .owid-finding-claim {
        font-family: 'Inter', Arial, sans-serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: #191C1F;
        line-height: 1.45;
        margin-bottom: 0.6rem;
    }
    .owid-finding-context {
        font-size: 0.95rem;
        color: #424752;
        line-height: 1.6;
        margin-bottom: 1.2rem;
    }
    .owid-finding-source {
        font-size: 0.875rem;
        color: #5a6377;
        margin-top: 0.8rem;
    }

    /* ── Article grid cards ── */
    .owid-article-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 12px;
        margin-top: 1rem;
    }
    .owid-article-card {
        background: #ffffff;
        border: none;
        border-radius: 10px;
        padding: 1.1rem 1rem;
        transition: box-shadow 0.15s, border-color 0.15s;
        cursor: default;
    }
    .owid-article-card:hover {
        box-shadow: 0 4px 24px rgba(100, 116, 145, 0.06);
        border-color: #003F87;
    }
    .owid-article-card-title {
        font-size: 0.875rem;
        font-weight: 700;
        color: #003F87;
        line-height: 1.35;
        margin-bottom: 0.4rem;
    }
    .owid-article-card-count {
        font-family: 'Inter', sans-serif;
        font-size: 1.3rem;
        font-weight: 800;
        color: #191C1F;
    }
    .owid-article-card-label {
        font-size: 0.875rem;
        color: #5a6377;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ── About expander override ── */
    .owid-about-section details {
        background: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
    }
    .owid-about-section details summary {
        font-weight: 600 !important;
        color: #003F87 !important;
    }
</style>
""",
        unsafe_allow_html=True,
    )
    # =====================================================================
    # 2. KEY FINDINGS — narrative-first with supporting charts
    # =====================================================================
    # Header row with AI Insights button
    _kf_left, _kf_right = st.columns([3, 1])
    with _kf_left:
        st.markdown(
            '<div class="owid-section-title" style="margin-bottom:0;">Key Findings</div>',
            unsafe_allow_html=True,
        )
    with _kf_right:
        # Initialize AI insights session state
        if "ai_insights_result" not in st.session_state:
            st.session_state.ai_insights_result = None
        if "ai_insights_generating" not in st.session_state:
            st.session_state.ai_insights_generating = False

        remaining = get_remaining_calls()
        if st.session_state.ai_insights_result:
            _ai_btn_label = "Regenerate (Beta)"
        else:
            _ai_btn_label = "Generate AI Insights (Beta)"

        _ai_clicked = st.button(
            _ai_btn_label,
            key="ai_insights_btn",
            type="secondary",
            disabled=remaining == 0,
            help=f"Generate AI-powered insights using Ollama (local). {remaining} calls remaining.",
        )

    # --- Fix 16: art_freq and mt already computed in Row 2 metrics block above ---

    # Initialize chart data variables (populated below if data is sufficient)
    _region_counts = None
    _yearly_counts = None
    _bump_data = None
    df_model = None

    # Prepare early/late split for trend analysis
    if "year" in df.columns and len(df) >= 4:
        sorted_years = sorted(df["year"].dropna().unique())
        mid_year = sorted_years[len(sorted_years) // 2]
        df_early = df[df["year"] < mid_year]
        df_late = df[df["year"] >= mid_year]
    else:
        df_early = df_late = None

    # Initialise variables used across sections (may not be set if data is sparse)
    af_yearly_pre = None
    _bump_data = None
    _region_counts = pd.DataFrame()
    _yearly_counts = None
    smart_insights = []
    df_model = None

    # ── Finding 1: Rights-Based Language ──
    if mt is not None and len(mt):
        rights_total = mt["rights"].sum()
        medical_total = mt["medical"].sum()
        rights_pct = (
            (rights_total / (rights_total + medical_total) * 100)
            if (rights_total + medical_total) > 0
            else 0
        )

        # Build yearly rights % for chart (reuse mt instead of per-year model_shift_table calls)
        if "year" in mt.columns:
            yearly_model = []
            for yr, grp in mt.groupby("year"):
                r = grp["rights"].sum()
                m = grp["medical"].sum()
                if (r + m) > 0:
                    yearly_model.append(
                        {
                            "year": int(yr),
                            "Rights-Based": round(r / (r + m) * 100, 1),
                            "Medical-Based": round(m / (r + m) * 100, 1),
                        }
                    )
            if yearly_model:
                df_model = pd.DataFrame(yearly_model).sort_values("year")

                # Pre-compute region counts + normalized docs-per-SP for lollipop AND insights
                _region_counts = (
                    df.groupby("region")
                    .size()
                    .reset_index(name="documents")
                    .sort_values("documents", ascending=True)
                )
                _countries_per_region = (
                    df.groupby("region")["country"].nunique().reset_index(name="n_countries")
                )
                _region_counts = _region_counts.merge(
                    _countries_per_region, on="region", how="left"
                )
                _region_counts["docs_per_sp"] = (
                    _region_counts["documents"] / _region_counts["n_countries"]
                ).round(1)
                _region_counts = _region_counts.sort_values("docs_per_sp", ascending=True)

                # Pre-compute yearly counts for bar chart AND insights
                _yearly_counts = (
                    df.groupby("year").size().reset_index(name="count").sort_values("year")
                    if "year" in df.columns and len(df) >= 2
                    else None
                )

                # Pre-compute bump chart data for insights
                _bump_data = None
                af_yearly_pre = (
                    article_frequency(df, ARTICLE_PRESETS, groupby="year") if len(df) else None
                )
                if (
                    af_yearly_pre is not None
                    and not af_yearly_pre.empty
                    and "group" in af_yearly_pre.columns
                ):
                    af_yearly_pre = af_yearly_pre.rename(columns={"group": "year"})
                    af_yearly_pre = af_yearly_pre[
                        ~af_yearly_pre["article"].str.startswith("Article 1 —")
                    ]
                    top_arts = af_yearly_pre.groupby("article")["count"].sum().nlargest(10).index
                    _bump_data = af_yearly_pre[af_yearly_pre["article"].isin(top_arts)].copy()
                    _bump_data["rank"] = (
                        _bump_data.groupby("year")["count"]
                        .rank(method="min", ascending=False)
                        .astype(int)
                    )

                # Generate smart insights
                smart_insights = generate_smart_insights(
                    df,
                    yearly_model_df=df_model,
                    region_counts_df=_region_counts if not _region_counts.empty else None,
                    yearly_counts_df=_yearly_counts,
                    bump_df=_bump_data,
                )

                # Side-by-side: insights (left) + charts (right)
                _col_insights, _col_charts = st.columns([1, 1.6], gap="large")

                with _col_insights:
                    # Key Insights as vertical stat cards
                    if smart_insights:
                        for ins in smart_insights:
                            st.markdown(
                                f'<div style="background:#F2F4F8;border-radius:10px;'
                                f'padding:0.8rem 1rem;margin-bottom:0.6rem;">'
                                f'<strong style="color:#003F87;font-size:0.85rem;">'
                                f"{ins['label']}</strong>"
                                f'<div style="font-size:0.82rem;color:#424752;'
                                f'margin-top:0.25rem;line-height:1.5;">'
                                f"{ins['text']}</div></div>",
                                unsafe_allow_html=True,
                            )
                    # CTA button below insight cards
                    st.markdown(
                        "<div style='text-align:center;margin:1rem 0;'>"
                        "<a href='/explore-profiles' "
                        "style='font-family:Inter,sans-serif;"
                        "font-size:15px;font-weight:600;color:#003F87;"
                        "text-decoration:none;padding:8px 24px;"
                        "border:2px solid #003F87;border-radius:8px;'>"
                        "Find Your Country\u2019s Reporting Status "
                        "\u2192</a></div>",
                        unsafe_allow_html=True,
                    )

                with _col_charts:
                    # Area chart
                    fig1 = go.Figure()
                    fig1.add_trace(
                        go.Scatter(
                            x=df_model["year"],
                            y=df_model["Rights-Based"],
                            name="Rights-Based",
                            stackgroup="one",
                            fillcolor="rgba(0, 63, 135, 0.7)",
                            line=dict(color=MODEL_COLORS["Rights-Based"], width=0),
                            hovertemplate="Year: %{x}<br>Rights-Based: %{y:.1f}%<extra></extra>",
                        )
                    )
                    fig1.add_trace(
                        go.Scatter(
                            x=df_model["year"],
                            y=df_model["Medical-Based"],
                            name="Medical-Based",
                            stackgroup="one",
                            fillcolor="rgba(213, 94, 0, 0.5)",
                            line=dict(color=MODEL_COLORS["Medical-Based"], width=0),
                            hovertemplate="Year: %{x}<br>Medical-Based: %{y:.1f}%<extra></extra>",
                        )
                    )
                    fig1.update_layout(
                        title=dict(
                            text="Rights-Based Vs. Medical Keyword Share Over Time",
                            x=0.5,
                            xanchor="center",
                        ),
                        height=340,
                        margin=dict(l=0, r=0, t=40, b=0),
                        plot_bgcolor="#ffffff",
                        paper_bgcolor="#ffffff",
                        font=dict(family="'Inter', Arial, Helvetica, sans-serif", size=13),
                        yaxis=dict(
                            title="Share (%)",
                            range=[0, 100],
                            ticksuffix="%",
                            gridcolor="#f0f0f0",
                        ),
                        xaxis=dict(
                            gridcolor="#f0f0f0",
                            range=[
                                df_model["year"].min() - 0.5,
                                df_model["year"].max() + 0.5,
                            ],
                        ),
                        legend=dict(
                            title="",
                            orientation="h",
                            yanchor="top",
                            y=-0.15,
                            xanchor="center",
                            x=0.5,
                        ),
                    )
                    st.plotly_chart(fig1, width="stretch", key="overview_fig1")
                    # sr-only alt text for area chart
                    st.markdown(
                        '<div class="sr-only" style="position:absolute;width:1px;height:1px;'
                        'overflow:hidden;clip:rect(0,0,0,0);">Stacked area chart showing the '
                        "share of rights-based versus medical-based framing keywords over time."
                        "</div>",
                        unsafe_allow_html=True,
                    )
                    # Absolute volume companion (use raw counts from mt, not percentages from df_model)
                    _total_model_kw = int(mt["rights"].sum() + mt["medical"].sum())
                    st.caption(
                        f"Total model-keyword volume across all years: "
                        f"{_total_model_kw:,} keyword matches"
                    )

                    # ── Lollipop chart (same right column, below area chart) ──
                    if _region_counts is not None and not _region_counts.empty:
                        _rc = _region_counts.copy()
                    else:
                        _rc = (
                            df.groupby("region")
                            .size()
                            .reset_index(name="documents")
                            .sort_values("documents", ascending=True)
                        )
                    if not _rc.empty:
                        if "docs_per_sp" not in _rc.columns:
                            _cpr = (
                                df.groupby("region")["country"]
                                .nunique()
                                .reset_index(name="n_countries")
                            )
                            _rc = _rc.merge(_cpr, on="region", how="left")
                            _rc["docs_per_sp"] = (_rc["documents"] / _rc["n_countries"]).round(1)
                        _rn = _rc.sort_values("docs_per_sp", ascending=True)

                        fig2 = px.scatter(
                            _rn,
                            x="docs_per_sp",
                            y="region",
                            text=_rn.apply(lambda r: f"{r['docs_per_sp']:.1f}", axis=1),
                            title="Documents Per State Party By Region",
                            labels={
                                "docs_per_sp": "Documents per State Party",
                                "region": "",
                            },
                            color_discrete_sequence=[CATEGORICAL_PALETTE[0]],
                            hover_data={
                                "documents": True,
                                "n_countries": True,
                                "docs_per_sp": False,
                            },
                        )
                        fig2.update_traces(
                            marker=dict(size=28),
                            textposition="middle center",
                            textfont=dict(
                                size=12,
                                color="#ffffff",
                                family="'Inter', Arial, Helvetica, sans-serif",
                            ),
                            hovertemplate=(
                                "%{y}<br>Docs per State Party: %{x:.1f}<br>"
                                "Raw count: %{customdata[0]}<br>"
                                "States Parties: %{customdata[1]}<extra></extra>"
                            ),
                            customdata=_rn[["documents", "n_countries"]].values,
                        )
                        for _i, row in _rn.iterrows():
                            fig2.add_shape(
                                type="line",
                                x0=0,
                                y0=row["region"],
                                x1=row["docs_per_sp"],
                                y1=row["region"],
                                line=dict(color=CATEGORICAL_PALETTE[0], width=3),
                                layer="below",
                            )
                        fig2.update_layout(
                            title=dict(x=0.5, xanchor="center"),
                            height=340,
                            margin=dict(l=0, r=40, t=40, b=0),
                            plot_bgcolor="#ffffff",
                            paper_bgcolor="#ffffff",
                            font=dict(
                                family="'Inter', Arial, Helvetica, sans-serif",
                                size=14,
                            ),
                            xaxis=dict(gridcolor="#f0f0f0"),
                            yaxis=dict(gridcolor="#f0f0f0"),
                        )
                        st.plotly_chart(fig2, width="stretch", key="overview_fig2")
                        st.caption(
                            "Document types have different submission triggers — "
                            "State Reports are government-initiated; Concluding "
                            "Observations are Committee-initiated."
                        )

    # ── AI Insights Panel (Phase 1) ──
    # Handle button click — generate insights using Ollama
    if _ai_clicked and len(df):
        st.session_state.ai_insights_generating = True
        data_context = build_data_context(
            df,
            yearly_model_df=df_model,
            region_counts_df=_region_counts,
            yearly_counts_df=_yearly_counts,
            bump_df=_bump_data,
        )
        with st.spinner(f"Analyzing documents with Ollama {OLLAMA_MODEL}..."):
            result = generate_insights_local(data_context)
        st.session_state.ai_insights_result = result
        st.session_state.ai_insights_generating = False

    # Display AI insights if available
    if st.session_state.get("ai_insights_result"):
        _ai = st.session_state.ai_insights_result
        if _ai["error"]:
            st.error(f"AI Insights error: {_ai['error']}")
        else:
            _ts = _ai["timestamp"][:19].replace("T", " ") + " UTC"
            st.markdown(
                f"""<div style="background: linear-gradient(135deg, rgba(0, 63, 135, 0.06) 0%, #F2F4F8 100%);
                    border: none; border-radius: 12px; padding: 1.5rem;
                    margin-top: 1rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem;
                    margin-bottom: 0.75rem; padding-bottom: 0.5rem;
                    border-bottom: none;">
                    <span style="font-size: 1.1rem; font-weight: 700; color: #003F87;">
                        AI Insights</span>
                    <span style="font-size: 0.875rem; color: #424752;
                        margin-left: auto;">powered by Ollama {OLLAMA_MODEL}</span>
                </div>
                <div style="font-size: 0.9rem; line-height: 1.7; color: #191C1F;">
                    {_ai["text"]}
                </div>
                <div style="font-size: 0.875rem; color: #5a6377; margin-top: 0.75rem;
                    padding-top: 0.5rem; border-top: 1px solid #d0dae8;">
                    Generated at {_ts} | {get_remaining_calls()} calls remaining
                </div>
                </div>""",
                unsafe_allow_html=True,
            )

    # ── Finding 3: Reporting Growth Over Time ──
    if "year" in df.columns and len(df) >= 4:
        yearly = df.groupby("year").size().reset_index(name="count").sort_values("year")
        st.caption("Reporting volume over time")
        fig3 = go.Figure()
        fig3.add_trace(
            go.Bar(
                x=yearly["year"],
                y=yearly["count"],
                marker_color=CATEGORICAL_PALETTE[0],
                width=0.5,
                hovertemplate="Year: %{x}<br>Documents: %{y}<extra></extra>",
            )
        )
        fig3.update_layout(
            height=200,
            margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            font=dict(family="'Inter', Arial, Helvetica, sans-serif", size=11),
            xaxis=dict(title="", gridcolor="#f0f0f0", dtick=1),
            yaxis=dict(title="", gridcolor="#f0f0f0"),
            showlegend=False,
        )
        st.plotly_chart(fig3, width="stretch", key="overview_fig3")
        # Fix 7: sr-only alt text for bar chart
        st.markdown(
            '<div class="sr-only" style="position:absolute;width:1px;height:1px;'
            'overflow:hidden;clip:rect(0,0,0,0);">Bar chart showing the number of '
            "CRPD documents submitted per year.</div>",
            unsafe_allow_html=True,
        )

        # ── Finding 4: Article Rankings Over Time (Bump Chart) ──
        st.markdown(
            '<div class="owid-section-title">Article Coverage</div>',
            unsafe_allow_html=True,
        )
        _exclude_art1_overview = st.toggle(
            "**Exclude Article 1 — Purpose (highest frequency article)**",
            value=True,
            key="overview_exclude_art1",
        )

        # Always compute fresh — af_yearly_pre has Article 1 pre-stripped for insights,
        # but the bump chart needs the full data so the toggle can control exclusion.
        af_yearly = article_frequency(df, ARTICLE_PRESETS, groupby="year")
        if not af_yearly.empty and ("group" in af_yearly.columns or "year" in af_yearly.columns):
            if "group" in af_yearly.columns:
                af_yearly = af_yearly.rename(columns={"group": "year"})

            # Conditionally exclude Article 1 (Purpose) based on toggle
            if _exclude_art1_overview:
                af_yearly = af_yearly[~af_yearly["article"].str.startswith("Article 1 —")]

            # Step 1: Identify top 10 articles by TOTAL count across all years
            top_articles = af_yearly.groupby("article")["count"].sum().nlargest(10).index
            af_yearly_top = af_yearly[af_yearly["article"].isin(top_articles)].copy()

            # Step 2: Re-rank WITHIN the top-10 group per year → ranks stay strictly 1–10
            af_yearly_top["rank"] = (
                af_yearly_top.groupby("year")["count"]
                .rank(method="min", ascending=False)
                .astype(int)
            )

            # Step 3: Drop sparse years (fewer than 5 of the top-10 articles present)
            year_counts = af_yearly_top.groupby("year")["article"].count()
            valid_years = year_counts[year_counts >= 5].index
            af_yearly_top = af_yearly_top[af_yearly_top["year"].isin(valid_years)]

            # Sort for correct line order
            af_yearly_top = af_yearly_top.sort_values(["article", "year"])

            # Step 4: WCAG 2.2 compliant color palette
            unique_articles = list(af_yearly_top["article"].unique())
            color_map = {
                art: BUMP_COLORS[i % len(BUMP_COLORS)] for i, art in enumerate(unique_articles)
            }

            fig4 = px.line(
                af_yearly_top,
                x="year",
                y="rank",
                color="article",
                markers=True,
                title="How the 10 most referenced CRPD articles have shifted in prominence",
                labels={"year": "", "rank": "Rank (1 = most mentioned)", "article": ""},
                line_shape="linear",  # honest discrete steps — spline misleads on rank data
                color_discrete_map=color_map,
            )

            # Fix Y-axis: explicit 1–10 range, rank 1 at top, no phantom rank-0
            fig4.update_yaxes(
                range=[10.5, 0.5],
                tickmode="linear",
                dtick=1,
                tick0=1,
                gridcolor="#f0f0f0",
                title_text="Rank (1 = most mentioned)",
            )

            fig4.update_traces(line=dict(width=2.5), marker=dict(size=7))

            # Direct labels at the right end of each line (sorted by final rank)
            if not af_yearly_top.empty:
                max_year = af_yearly_top["year"].max()
                end_points = af_yearly_top[af_yearly_top["year"] == max_year].sort_values("rank")

                # Nudge labels that share the same or adjacent ranks to avoid overlap
                prev_y = None
                min_gap = 0.45  # minimum rank-units between labels
                for _, row in end_points.iterrows():
                    short_label = (
                        row["article"].split(" — ", 1)[1]
                        if " — " in row["article"]
                        else row["article"]
                    )
                    # Fix 6: Cap label text to 25 characters with ellipsis
                    if len(short_label) > 25:
                        short_label = short_label[:22] + "..."
                    label_y = row["rank"]
                    if prev_y is not None and abs(label_y - prev_y) < min_gap:
                        label_y = prev_y + min_gap
                    prev_y = label_y

                    fig4.add_annotation(
                        x=row["year"],
                        y=label_y,
                        text=short_label,
                        showarrow=False,
                        xanchor="left",
                        xshift=12,
                        font=dict(
                            family="'Inter', Arial, Helvetica, sans-serif", size=11, color="#333333"
                        ),
                    )

            fig4.update_layout(
                title=dict(x=0.5, xanchor="center"),
                height=480,
                margin=dict(l=0, r=180, t=50, b=20),
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff",
                font=dict(family="'Inter', Arial, Helvetica, sans-serif", size=13),
                xaxis=dict(
                    gridcolor="#f0f0f0",
                    tickmode="linear",
                    dtick=1,
                    range=[af_yearly_top["year"].min() - 0.5, af_yearly_top["year"].max() + 0.5],
                ),
                showlegend=False,
            )
            st.plotly_chart(fig4, width="stretch", key="overview_fig4")
            # Fix 7: sr-only alt text for bump chart
            st.markdown(
                '<div class="sr-only" style="position:absolute;width:1px;height:1px;'
                'overflow:hidden;clip:rect(0,0,0,0);">Bump chart showing how the top 10 '
                "most referenced CRPD articles have shifted in rank over time.</div>",
                unsafe_allow_html=True,
            )
            st.caption(
                "Top 10 articles ranked by keyword mentions per year. "
                "Rank 1 = most mentioned. "
                "Years with fewer than 5 of the top 10 articles present are omitted."
            )

    # Data Sources & Coverage
    st.markdown("---")
    _src = df_all if df_all is not None and len(df_all) else df

    # Doc type counts
    _dt_order = [
        ("State Report", "State Party Reports"),
        ("List of Issues (LOI)", "List of Issues"),
        ("Written Reply", "Written Responses"),
        ("Concluding Observations", "Concluding Observations"),
        ("Response to Concluding Observations", "Responses to Concluding Observations"),
    ]
    _dt_counts = _src["doc_type"].value_counts().to_dict() if "doc_type" in _src.columns else {}
    _doc_rows = "".join(
        f"""<div style="display:flex;align-items:center;justify-content:space-between;
                        padding:9px 12px;background:#FFFFFF;border-radius:8px;margin-bottom:6px;">
            <span style="font-size:14px;font-weight:500;color:#191C1F;">{label}</span>
            <span style="font-size:14px;font-weight:700;background:#D5E0F7;color:#003F87;
                         padding:2px 10px;border-radius:9999px;">{_dt_counts.get(key, 0):,}</span>
        </div>"""
        for key, label in _dt_order
    )

    with st.expander("Data Sources & Coverage", expanded=False):
        st.html(
            f"""
        <div style="font-family:'Inter',sans-serif;color:#191C1F;padding:4px 0;">

        <!-- Two-column detail -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">

            <!-- Document Sources -->
            <div>
                <p style="font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;
                           color:#5a6377;margin:0 0 10px 0;">Document Sources</p>
                <div style="background:#F2F4F6;border-radius:12px;padding:12px;">
                    <p style="font-size:14px;color:#424752;margin:0 0 10px 0;line-height:1.5;">
                        <strong>UN Treaty Body Database</strong> &mdash; five document types
                        across the complete reporting cycle
                    </p>
                    {_doc_rows}
                </div>
            </div>

            <!-- Variables Analyzed -->
            <div>
                <p style="font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;
                           color:#5a6377;margin:0 0 10px 0;">Variables Analyzed</p>
                <div style="background:#F2F4F6;border-radius:12px;padding:16px;display:flex;
                            flex-direction:column;gap:10px;">
                    <div style="padding:8px 12px;background:#FFFFFF;border-radius:8px;">
                        <span style="color:#003F87;font-weight:700;font-size:14px;">Outcome</span>
                        <span style="color:#424752;font-size:14px;"> &mdash; Document types, reporting patterns</span>
                    </div>
                    <div style="padding:8px 12px;background:#FFFFFF;border-radius:8px;">
                        <span style="color:#003F87;font-weight:700;font-size:14px;">Content</span>
                        <span style="color:#424752;font-size:14px;"> &mdash; CRPD articles, keywords, themes</span>
                    </div>
                    <div style="padding:8px 12px;background:#FFFFFF;border-radius:8px;">
                        <span style="color:#003F87;font-weight:700;font-size:14px;">Geographic</span>
                        <span style="color:#424752;font-size:14px;"> &mdash; Countries, regions, subregions</span>
                    </div>
                    <div style="padding:8px 12px;background:#FFFFFF;border-radius:8px;">
                        <span style="color:#003F87;font-weight:700;font-size:14px;">Temporal</span>
                        <span style="color:#424752;font-size:14px;"> &mdash; Years, reporting cycles</span>
                    </div>
                    <div style="padding:8px 12px;background:#FFFFFF;border-radius:8px;">
                        <span style="color:#003F87;font-weight:700;font-size:14px;">Model Language</span>
                        <span style="color:#424752;font-size:14px;"> &mdash; Medical vs. Rights-based framing</span>
                    </div>
                    <div style="padding:8px 12px;background:#FFFFFF;border-radius:8px;">
                        <span style="color:#003F87;font-weight:700;font-size:14px;">Actors</span>
                        <span style="color:#424752;font-size:14px;"> &mdash; State Parties vs. Committee emphasis</span>
                    </div>
                </div>
            </div>

        </div>
        </div>
        """
        )
