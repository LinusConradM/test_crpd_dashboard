"""Policy Brief Generation page — Phase 4.

Two-column layout matching the Pencil design:
  Left panel: Configure Brief (country selector, articles, date range, format, generate)
  Right panel: Brief preview → generated brief + export buttons + generation stats

State keys used:
  brief_result       — dict from generate_policy_brief(), or None
  brief_countries    — list[str] of selected countries
  brief_articles     — list[str] of selected article labels
  brief_year_range   — tuple(int, int)
  brief_format       — str ("Executive Summary" | "Full Report" | "Fact Sheet")
"""

import html as _html

import bleach
import streamlit as st

from src.llm import (
    BRIEF_FORMATS,
    BRIEF_SESSION_LIMIT,
    GROQ_MODEL,
    generate_policy_brief,
    get_remaining_brief_calls,
)


# Tags allowed in LLM-generated brief sections (formatting only)
_ALLOWED_TAGS = [
    "p",
    "strong",
    "em",
    "b",
    "i",
    "u",
    "ul",
    "ol",
    "li",
    "br",
    "code",
    "pre",
    # h1/h2 removed — LLM output should not override page heading hierarchy
    "h3",
    "h4",
    "a",
    "blockquote",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
]
_ALLOWED_ATTRS = {
    "a": ["href", "title"],
    "th": ["scope"],
}


# ── Section colour palette (intentional design tokens per Pencil mockup) ─────

_SECTION_STYLES: dict[str, dict] = {
    "context": {
        "label": "01  CONTEXT",
        "bg": "#EEF4FF",
        "color": "#005bbb",
        "border": "#BFDBFE",
        "num_bg": "#005bbb",
    },
    "key_findings": {
        "label": "02  KEY FINDINGS",
        "bg": "#F0FDF4",
        "color": "#166534",
        "border": "#BBF7D0",
        "num_bg": "#1D4ED8",
    },
    "recommendations": {
        "label": "03  RECOMMENDATIONS",
        "bg": "#FFF7ED",
        "color": "#C2410C",
        "border": "#FED7AA",
        "num_bg": "#059669",
    },
    "sources": {
        "label": "04  SOURCES",
        "bg": "#F9FAFB",
        "color": "#374151",
        "border": "#E0E4ED",
        "num_bg": "#6B7280",
    },
}


def _section_html(key: str, text: str) -> str:
    """Render a brief section as styled HTML matching the Pencil design."""
    style = _SECTION_STYLES[key]
    label_html = (
        f'<span style="display:inline-block;padding:3px 10px;'
        f"background:{style['bg']};color:{style['color']};"
        f"border:1px solid {style['border']};border-radius:4px;"
        f"font-size:10px;font-weight:700;letter-spacing:0.08em;"
        f'font-family:Inter,sans-serif;margin-bottom:10px;">'
        f"{style['label']}</span>"
    )
    # Sanitize LLM output then convert newlines to <br> for HTML display
    clean_text = bleach.clean(text, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS, strip=True)
    body_html = clean_text.replace("\n", "<br>")
    return (
        f'<div style="margin-bottom:20px;">'
        f"{label_html}"
        f'<div style="font-size:13.5px;color:#374151;line-height:1.75;'
        f'font-family:Inter,sans-serif;">{body_html}</div>'
        f"</div>"
    )


def _stat_row(label: str, value: str) -> str:
    """Render a single key-value stat row for the generation stats box."""
    return (
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;padding:4px 0;border-bottom:1px solid #F3F4F6;">'
        f'<span style="font-size:12px;color:#6B7280;font-family:Inter,sans-serif;">{label}</span>'
        f'<span style="font-size:12px;font-weight:600;color:#191C1F;'
        f'font-family:Inter,sans-serif;">{value}</span>'
        f"</div>"
    )


def _init_state() -> None:
    """Initialise session-state keys on first load."""
    defaults: dict = {
        "brief_result": None,
        "brief_countries": [],
        "brief_articles": [],
        "brief_year_range": (2015, 2025),
        "brief_format": "Executive Summary",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def render(df_all) -> None:
    """Render the Policy Brief Generator page.

    Args:
        df_all: Full (unfiltered) CRPD DataFrame — used to populate country list.
    """
    _init_state()

    from src.data_loader import get_dataset_stats

    _stats = get_dataset_stats()
    _year_span = _stats["year_max"] - _stats["year_min"]

    # I4: Dynamic year range from data
    _yr_min = _stats["year_min"]
    _yr_max = _stats["year_max"]

    # ── Page header ────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="text-align:center;margin-top:-2rem;margin-bottom:1.8rem;">
            <h1 class="hero-title">
                Policy Brief <span class="gradient-word">Generator</span>
            </h1>
            <p style="max-width:860px;margin:1.2rem auto 0 auto;font-size:1.15rem;
               color:#424752;line-height:1.8;">
                Turn <strong>{_year_span} years</strong> of UN disability rights reporting into
                structured policy summaries — by State Party, article, and reporting period
            </p>
        </div>
        <hr style="border:none;border-top:1px solid #E0E4ED;margin-bottom:1.5rem;">
        <style>
            /* Bold blue widget labels on the Policy Brief page */
            [data-testid="stWidgetLabel"] p,
            [data-testid="stWidgetLabel"] label {{
                color: #003F87 !important;
                font-weight: 700 !important;
                font-family: Inter, sans-serif !important;
                font-size: 14px !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # S4: Distinguish from AI Research Assistant
    st.caption(
        "**Policy Brief Generator** creates structured, evidence-based documents. "
        "For exploratory questions, use the AI Research Assistant."
    )

    # ── Two-column layout ───────────────────────────────────────────────────────
    left_col, right_col = st.columns([2, 3], gap="large")

    # ── Left panel: Configure Brief ────────────────────────────────────────────
    with left_col:
        st.markdown(
            '<p style="font-size:14px;font-weight:700;color:#003F87;'
            'font-family:Inter,sans-serif;margin-bottom:1rem;">Configure Brief</p>',
            unsafe_allow_html=True,
        )

        # ── Region filters (narrow the country list) ───────────────────────────
        from src.data_loader import get_custom_organizations, load_article_dict

        orgs = get_custom_organizations()
        org_names = sorted(orgs.keys())

        raw_regions = df_all["region"].dropna().replace("America", "Americas").unique()
        geo_regions = ["All", *sorted(r for r in raw_regions if r != "Unknown")]

        # Region popover + Country multiselect — same row
        geo_val = st.session_state.get("brief_geo_region", "All")
        org_val = st.session_state.get("brief_org_region", "All")
        active = [v for v in [geo_val, org_val] if v != "All"]
        btn_label = "Region: " + " + ".join(active) if active else "Region"

        rc_left, rc_right = st.columns(2, gap="small")

        with rc_left:
            st.markdown(
                '<p style="font-size:14px;font-weight:700;color:#003F87;'
                'font-family:Inter,sans-serif;margin:0 0 4px 0;">Region</p>',
                unsafe_allow_html=True,
            )
            with st.popover(btn_label, width="stretch"):
                gc, oc = st.columns(2, gap="small")
                with gc:
                    st.radio("Geographic", geo_regions, key="brief_geo_region")
                with oc:
                    st.radio("Organization", ["All", *org_names], key="brief_org_region")

        geo_region = st.session_state.get("brief_geo_region", "All")
        org_region = st.session_state.get("brief_org_region", "All")

        # Narrow country list by whichever region filters are active
        base = df_all.copy()
        if geo_region != "All":
            base = base[base["region"] == geo_region]
        if org_region != "All":
            base = base[base["iso3"].isin(orgs.get(org_region, []))]
        filtered_countries = sorted(base["country"].dropna().unique().tolist())

        # Reset selections that are no longer in the filtered list
        valid_defaults = [c for c in st.session_state["brief_countries"] if c in filtered_countries]

        with rc_right:
            selected_countries = st.multiselect(
                "State Party",
                options=filtered_countries,
                default=valid_defaults,
                placeholder="Search States Parties…",
                max_selections=5,
                help="Select up to 5 States Parties. Brief will draw from documents of all selected States Parties.",
                key="brief_country_select",
            )
        st.session_state["brief_countries"] = selected_countries

        # Article selector (from article dict)

        article_dict = load_article_dict()
        article_options = list(article_dict.keys())
        selected_articles = st.multiselect(
            "CRPD Articles",
            options=article_options,
            default=st.session_state["brief_articles"],
            placeholder="All articles (leave blank for all)…",
            help="Focus the brief on specific articles. Leave blank to cover all.",
            key="brief_article_select",
        )
        st.session_state["brief_articles"] = selected_articles

        # Date range
        year_range = st.slider(
            "Reporting Period",
            min_value=_yr_min,
            max_value=_yr_max,
            value=(
                max(_yr_min, st.session_state["brief_year_range"][0]),
                min(_yr_max, st.session_state["brief_year_range"][1]),
            ),
            step=1,
            help="Only documents from this year range will be retrieved.",
            key="brief_year_slider",
        )
        st.session_state["brief_year_range"] = year_range

        # Brief format
        fmt_options = list(BRIEF_FORMATS.keys())
        brief_format = st.radio(
            "Brief Format",
            options=fmt_options,
            index=fmt_options.index(st.session_state["brief_format"]),
            horizontal=True,
            help="Executive Summary: ~400 words · Full Report: ~800 words · Fact Sheet: bullets",
            key="brief_format_radio",
        )
        st.session_state["brief_format"] = brief_format

        st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)

        # Resolve which countries to use for generation:
        # — specific picks if any, otherwise ALL countries in the filtered region
        region_active = geo_region != "All" or org_region != "All"
        if selected_countries:
            countries_for_brief = selected_countries
            scope_label = ", ".join(selected_countries[:3]) + (
                f" +{len(selected_countries) - 3} more" if len(selected_countries) > 3 else ""
            )
        elif region_active:
            countries_for_brief = filtered_countries
            scope_label = f"All {len(filtered_countries)} States Parties in " + " + ".join(
                v for v in [geo_region, org_region] if v != "All"
            )
        else:
            countries_for_brief = []
            scope_label = ""

        can_generate = len(countries_for_brief) > 0

        if region_active and not selected_countries:
            st.info(
                f"No specific country selected — brief will cover **all "
                f"{len(filtered_countries)} States Parties** in the selected region.",
                icon="🌍",
            )

        generate_clicked = st.button(
            "✦ Generate Brief",
            type="primary",
            width="stretch",
            disabled=not can_generate,
            help="Select a country or region to generate a brief.",
        )

        # I6: Rate-limit counter
        _remaining = get_remaining_brief_calls()
        if _remaining < BRIEF_SESSION_LIMIT:
            st.caption(f"Briefs remaining this session: {_remaining} of {BRIEF_SESSION_LIMIT}")

        if not can_generate:
            st.caption("Select a region or at least one State Party to enable generation.")
        else:
            st.caption(
                f"{scope_label} · {BRIEF_FORMATS[brief_format]['word_target']} · "
                f"Model: Groq {GROQ_MODEL}"
            )

        # Trigger generation
        if generate_clicked and can_generate:
            with st.spinner("Retrieving documents and generating brief…"):
                result = generate_policy_brief(
                    countries=countries_for_brief,
                    articles=selected_articles,
                    year_min=year_range[0],
                    year_max=year_range[1],
                    brief_format=brief_format,
                )
            st.session_state["brief_result"] = result
            if result["error"]:
                st.warning(result["error"])
            st.rerun()

        # Reset button (only show after a result)
        if st.session_state["brief_result"] is not None:
            st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)
            if st.button(
                "↺ Reset",
                width="stretch",
                help="Clear the current brief and start over.",
            ):
                st.session_state["brief_result"] = None
                st.rerun()
            # S3: Regenerate with same parameters
            if st.button(
                "🔄 Regenerate",
                width="stretch",
                help="Generate a new brief with the same parameters.",
                disabled=not can_generate,
            ):
                with st.spinner("Regenerating brief…"):
                    result = generate_policy_brief(
                        countries=countries_for_brief,
                        articles=selected_articles,
                        year_min=year_range[0],
                        year_max=year_range[1],
                        brief_format=brief_format,
                    )
                st.session_state["brief_result"] = result
                st.rerun()

    # ── Right panel: Preview → Generated Brief ─────────────────────────────────
    with right_col:
        result: dict | None = st.session_state["brief_result"]

        # ── Header row: title + status badge ───────────────────────────────────
        hcol1, hcol2 = st.columns([3, 1])
        with hcol1:
            st.markdown(
                '<p style="font-size:14px;font-weight:700;color:#003F87;'
                'font-family:Inter,sans-serif;margin-bottom:0.5rem;">Brief Preview</p>',
                unsafe_allow_html=True,
            )
        with hcol2:
            if result is None:
                st.markdown(
                    '<span role="status" aria-live="polite" style="display:inline-block;padding:4px 12px;'
                    "background:#FEF9C3;color:#B45309;border-radius:20px;"
                    "font-size:11px;font-weight:600;font-family:Inter,sans-serif;"
                    'float:right;">⏱ Not yet generated</span>',
                    unsafe_allow_html=True,
                )
            elif result.get("error"):
                st.markdown(
                    '<span role="status" aria-live="polite" style="display:inline-block;padding:4px 12px;'
                    "background:#FEE2E2;color:#B91C1C;border-radius:20px;"
                    "font-size:11px;font-weight:600;font-family:Inter,sans-serif;"
                    'float:right;">✗ Error</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<span role="status" aria-live="polite" style="display:inline-block;padding:4px 12px;'
                    "background:#F0FDF4;color:#166534;border-radius:20px;"
                    "font-size:11px;font-weight:600;font-family:Inter,sans-serif;"
                    'float:right;">✓ Ready</span>',
                    unsafe_allow_html=True,
                )

        # ── Not yet generated: show placeholder ────────────────────────────────
        if result is None:
            _render_placeholder(countries_for_brief, selected_articles, year_range, brief_format)
            return

        # ── Error state ─────────────────────────────────────────────────────────
        if result.get("error"):
            st.warning(f"{result['error']}")
            return

        # ── Generated brief: show title + sections ──────────────────────────────
        # S6: html.escape() defense-in-depth on user-controlled strings
        country_str = _html.escape(scope_label if scope_label else "All States Parties")
        article_str = _html.escape(
            ", ".join(a.split("—")[0].strip() for a in selected_articles[:4])
            if selected_articles
            else "All Articles"
        )
        if selected_articles and len(selected_articles) > 4:
            article_str += f" +{len(selected_articles) - 4} more"

        st.markdown(
            f'<div style="background:#FFFFFF;border:1px solid #E0E4ED;'
            f"border-radius:12px;padding:28px 32px;margin-bottom:1rem;"
            f'font-family:Inter,sans-serif;">'
            f'<h2 style="font-size:18px;font-weight:700;color:#191C1F;margin:0 0 4px 0;">'
            f"{brief_format} — {country_str}</h2>"
            f'<p style="font-size:13px;color:#6B7280;margin:0 0 16px 0;">'
            f"{article_str} &nbsp;·&nbsp; {year_range[0]}–{year_range[1]}</p>"
            f'<hr style="border:none;border-top:2px solid #005bbb;margin:0 0 20px 0;">'
            + "".join(
                _section_html(k, result["sections"].get(k, ""))
                for k in ["context", "key_findings", "recommendations", "sources"]
                if result["sections"].get(k, "").strip()
            )
            # C1: AI disclaimer banner
            + '<div style="margin-top:16px;padding:12px 16px;background:#FEF3C7;'
            "border:1px solid #F59E0B;border-radius:8px;font-size:12px;color:#92400E;"
            'line-height:1.6;font-family:Inter,sans-serif;">'
            "<strong>⚠ AI-Generated Content.</strong> This brief was produced by an AI model "
            "(Groq LLM) using keyword-matched document excerpts from the UN Treaty Body Database. "
            "It has not been reviewed by a human analyst and should not be cited as an official "
            "UN document. Verify all claims against source documents before use.</div>" + "</div>",
            unsafe_allow_html=True,
        )

        # ── Stats ───────────────────────────────────────────────────────────────
        _, stats_col = st.columns([3, 2], gap="medium")

        with stats_col:
            st.markdown(
                '<p style="font-size:14px;font-weight:700;color:#003F87;'
                'font-family:Inter,sans-serif;margin-bottom:0.5rem;">Generation Stats</p>',
                unsafe_allow_html=True,
            )
            elapsed_s = f"{result['generation_time_ms'] / 1000:.1f} s"
            tokens_str = f"{result['tokens_used']:,}" if result["tokens_used"] else "n/a"
            model_short = result["model"].replace("-versatile", "")
            stats_html = (
                '<div style="background:#F9FAFB;border:1px solid #E0E4ED;'
                "border-radius:8px;padding:12px 14px;"
                'font-family:Inter,sans-serif;">'
                + _stat_row("Chunks retrieved", str(result["chunks_retrieved"]))
                + _stat_row("Tokens used", tokens_str)
                + _stat_row("Generation time", elapsed_s)
                + _stat_row(
                    "Model",
                    f'<span style="color:#005bbb;font-weight:600;">{model_short}</span>',
                )
                + "</div>"
            )
            st.markdown(stats_html, unsafe_allow_html=True)

        # I5: Copy brief text to clipboard (no download per policy)
        if result.get("raw_text"):
            with st.popover("📋 Copy Brief Text"):
                st.code(result["raw_text"], language=None)
                st.caption("Select all text above and copy (Ctrl+C / Cmd+C).")


def _render_placeholder(
    countries: list[str],
    articles: list[str],
    year_range: tuple[int, int],
    brief_format: str,
) -> None:
    """Render the placeholder card shown before a brief has been generated."""
    country_str = ", ".join(countries) if countries else "—"
    article_str = (
        ", ".join(a.split("—")[0].strip() for a in articles[:3]) if articles else "All Articles"
    )
    if articles and len(articles) > 3:
        article_str += f" +{len(articles) - 3} more"

    st.markdown(
        f'<div style="background:#FFFFFF;border:1px solid #E0E4ED;border-radius:12px;'
        f"padding:28px 32px;font-family:Inter,sans-serif;"
        f'opacity:{0.6 if not countries else 1};">'
        f'<h2 style="font-size:18px;font-weight:700;color:#191C1F;margin:0 0 4px 0;">'
        f"{brief_format}"
        f"{'  — ' + country_str if countries else ''}</h2>"
        f'<p style="font-size:13px;color:#6B7280;margin:0 0 20px 0;">'
        f"{article_str} &nbsp;·&nbsp; {year_range[0]}–{year_range[1]}</p>"
        + "".join(
            f'<div style="margin-bottom:16px;">'
            f'<span style="display:inline-block;padding:3px 10px;'
            f"background:{s['bg']};color:{s['color']};border:1px solid {s['border']};"
            f"border-radius:4px;font-size:10px;font-weight:700;letter-spacing:0.08em;"
            f'font-family:Inter,sans-serif;margin-bottom:8px;">{s["label"]}</span>'
            f'<div style="height:12px;background:#F3F4F6;border-radius:4px;'
            f'margin-bottom:6px;width:90%;"></div>'
            f'<div style="height:12px;background:#F3F4F6;border-radius:4px;'
            f'margin-bottom:6px;width:75%;"></div>'
            f'<div style="height:12px;background:#F3F4F6;border-radius:4px;'
            f'width:82%;">'
            f"</div></div>"
            for s in _SECTION_STYLES.values()
        )
        + (
            '<p style="text-align:center;font-size:13px;color:#9CA3AF;margin-top:8px;">'
            "Configure your brief on the left and click ✦ Generate Brief</p>"
            if not countries
            else ""
        )
        + "</div>",
        unsafe_allow_html=True,
    )
