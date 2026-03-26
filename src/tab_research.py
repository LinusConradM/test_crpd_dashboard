"""Research & Citation Assistant tab -- two-panel layout with source sidebar.

Provides a multi-agent research pipeline that decomposes user questions,
retrieves relevant CRPD document excerpts via FAISS, synthesises findings
with source separation, and produces structured briefings.  The right panel
shows cited source documents and keyword analysis.
"""

from datetime import UTC, datetime

import streamlit as st

from src.colors import DOC_TYPE_COLORS
from src.data_loader import get_dataset_stats
from src.llm import get_budget_status
from src.research_agent import run_research_pipeline

# research_export imports removed — no-data-download policy active
from src.research_methodology import generate_methodology_appendix


# ── Constants ─────────────────────────────────────────────────────────────────

_SESSION_LIMIT = 5
_RATE_KEY = "research_query_count"

EXAMPLE_QUERIES = [
    (
        "Which States Parties have not addressed Article 9 (Accessibility) "
        "in their most recent reports?"
    ),
    ("How does Article 24 (Education) coverage compare across East African State Party Reports?"),
    (
        "Has rights-based language in Article 19 (Living Independently) "
        "increased over the past 10 years?"
    ),
]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _extract_unique_sources(result: dict) -> list[dict]:
    """Group all_chunks by (country, doc_type, year) for right panel."""
    sources: dict[str, dict] = {}
    for c in result.get("all_chunks", []):
        key = (
            f"{c.get('country', 'Unknown')}|"
            f"{c.get('doc_type', 'Unknown')}|"
            f"{c.get('year', 'Unknown')}"
        )
        if key not in sources:
            # Sentence-boundary truncation (Flag #3): first complete sentence, max 250 chars
            raw_text = c.get("text", "")
            excerpt = raw_text[:250]
            # Find the last sentence boundary within 250 chars
            found_boundary = False
            for sep in [". ", ".\n", ".\t"]:
                idx = excerpt.rfind(sep)
                if idx > 30:  # don't truncate to a tiny fragment
                    excerpt = excerpt[: idx + 1]
                    found_boundary = True
                    break
            if not found_boundary and len(raw_text) > 250:
                # No sentence boundary found -- truncate at last word boundary
                last_space = excerpt.rfind(" ")
                if last_space > 0:
                    excerpt = excerpt[:last_space] + "..."
            sources[key] = {
                "country": c.get("country", "Unknown"),
                "doc_type": c.get("doc_type", "Unknown"),
                "year": c.get("year", "Unknown"),
                "excerpt": excerpt,
                "count": 0,
            }
        sources[key]["count"] += 1
    return sorted(sources.values(), key=lambda x: x["count"], reverse=True)


def _get_remaining_queries() -> int:
    """Return number of research queries remaining in this session."""
    used = st.session_state.get(_RATE_KEY, 0)
    return max(0, _SESSION_LIMIT - used)


def _increment_query_count():
    """Increment the session research query counter."""
    if _RATE_KEY not in st.session_state:
        st.session_state[_RATE_KEY] = 0
    st.session_state[_RATE_KEY] += 1


def _format_briefing_as_markdown(result: dict) -> str:
    """Format pipeline result as downloadable Markdown."""
    now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    n_chunks = len(result.get("all_chunks", []))
    n_countries = len(set(c.get("country", "") for c in result.get("all_chunks", [])))

    lines = [
        "# CRPD Research Briefing",
        "",
        f"**Query:** {result.get('query', '')}  ",
        f"**Generated:** {now}  ",
        f"**Excerpts retrieved:** {n_chunks}  ",
        f"**States Parties represented:** {n_countries}  ",
        f"**LLM calls:** {result.get('llm_calls', 0)}  ",
        f"**Processing time:** {result.get('duration_seconds', 0)}s  ",
        "",
        "---",
        "",
    ]

    # Sub-questions
    sub_qs = result.get("sub_questions", [])
    if sub_qs:
        lines.append("## Research Plan")
        lines.append("")
        for i, sq in enumerate(sub_qs, 1):
            lines.append(f"{i}. {sq}")
        lines.append("")

    # Briefing
    lines.append("## Briefing")
    lines.append("")
    lines.append(result.get("briefing", ""))
    lines.append("")

    # Sources
    all_chunks = result.get("all_chunks", [])
    if all_chunks:
        lines.append("## Sources")
        lines.append("")
        seen: set[str] = set()
        for c in all_chunks:
            country = c.get("country", "Unknown")
            doc_type = c.get("doc_type", "Unknown")
            year = c.get("year", "Unknown")
            key = f"{country}|{doc_type}|{year}"
            if key not in seen:
                seen.add(key)
                lines.append(f"- {country}, {doc_type}, {year}")
        lines.append("")

    lines.append("---")
    lines.append(
        "*Generated by the CRPD Dashboard -- Institute on Disability "
        "and Public Policy, American University*"
    )
    return "\n".join(lines)


# ── Card HTML helpers ─────────────────────────────────────────────────────────

_CARD_STYLE = (
    "background:#ffffff;border-radius:12px;padding:1.5rem;margin:1rem 0;"
    "box-shadow:0 2px 12px rgba(0,0,0,0.04);"
    "border:1px solid rgba(195,198,210,0.3);"
)

_CALLOUT_STYLE = (
    "background:#f3f3fa;padding:1rem 1.25rem;border-radius:8px;"
    "border-left:4px solid #003F87;margin:1rem 0;"
)

_CHIP_STYLE = (
    "display:inline-block;background:#cbdafe;color:#0b1b36;"
    "font-size:0.75rem;font-weight:700;padding:3px 8px;"
    "border-radius:4px;margin:2px;"
)


def _source_card_html(source: dict, today_str: str) -> str:
    """Render a single source document card for the right panel."""
    doc_type = source["doc_type"]
    border_color = DOC_TYPE_COLORS.get(doc_type, "#003F87")
    country = source["country"]
    year = source["year"]
    excerpt = source["excerpt"].replace("<", "&lt;").replace(">", "&gt;")
    count = source["count"]
    count_label = f"{count} excerpt{'s' if count != 1 else ''}"

    return f"""
    <div style="background:#ffffff;padding:12px 14px;border-radius:8px;
                border-left:3px solid {border_color};margin-bottom:10px;
                box-shadow:0 1px 4px rgba(0,0,0,0.03);">
        <div style="display:flex;justify-content:space-between;align-items:center;
                    margin-bottom:6px;">
            <span style="font-weight:700;font-size:0.88rem;color:#191C1F;">
                {country}
            </span>
            <span style="{_CHIP_STYLE}">{count_label}</span>
        </div>
        <div style="font-size:0.8rem;color:#424752;margin-bottom:6px;">
            {doc_type} &middot; {year}
        </div>
        <div style="font-size:0.82rem;line-height:1.5;color:#434751;
                    display:-webkit-box;-webkit-line-clamp:3;
                    -webkit-box-orient:vertical;overflow:hidden;
                    word-break:break-word;">
            {excerpt}
        </div>
        <div style="font-size:0.7rem;color:#7a8194;margin-top:8px;
                    border-top:1px solid #eef0f4;padding-top:6px;">
            Retrieved by CRPD Dashboard | {today_str} | AI-assisted excerpt
            &mdash; verify against original UN document
        </div>
        <div style="font-size:0.7rem;color:#7a8194;margin-top:2px;">
            Locate in UN Treaty Body Database: search {country} {doc_type} {year}
        </div>
    </div>
    """


# ── Main render ───────────────────────────────────────────────────────────────


def render(df, article_presets):
    """Render the Research & Citation Assistant page."""
    stats = get_dataset_stats()
    today_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    # ── Hero header (full-width, above columns) ──────────────────────────────
    st.markdown(
        f"""
        <div style="text-align:center;margin-top:-1.5rem;margin-bottom:1.25rem;">
            <div class="hero-badge">
                <span class="dot"></span>
                Live &mdash; Local AI Processing
            </div>
            <h1 class="hero-title">
                Research &amp; Citation
                <span class="gradient-word">Assistant</span>
            </h1>
            <p class="hero-sub">
                Ask a question about CRPD implementation. Get a structured
                briefing with references to specific document excerpts from the
                UN reporting cycle.
            </p>
            <p style="font-size:0.92rem;color:#424752;margin-top:-0.8rem;">
                Powered by {stats["n_docs"]} documents across
                {stats["n_countries"]} States Parties
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Two-panel split ──────────────────────────────────────────────────────
    left_panel, right_panel = st.columns([2, 1], gap="large")

    # ── LEFT PANEL ───────────────────────────────────────────────────────────
    with left_panel:
        # Tier selector
        try:
            _has_api_key = bool(st.secrets.get("ANTHROPIC_API_KEY", ""))
        except Exception:
            _has_api_key = False
        if _has_api_key:
            _budget = get_budget_status()
            _budget_exceeded = _budget["remaining"] <= 0

            if _budget_exceeded:
                st.info("Extended tier monthly budget reached. Using local AI processing.")
                _selected_tier = "free"
            else:
                _tier_choice = st.radio(
                    "Processing tier:",
                    ["Standard (local AI)", "Extended (cloud AI)"],
                    horizontal=True,
                    key="research_tier_radio",
                )
                _selected_tier = "premium" if "Extended" in _tier_choice else "free"
                if _selected_tier == "premium":
                    st.caption(
                        f"Monthly usage: ${_budget['spent']:.2f} of "
                        f"${_budget['budget']:.2f} "
                        f"({_budget['pct_used']:.0f}% used)"
                    )
        else:
            _selected_tier = "free"

        # Query input
        query = st.text_input(
            "Ask a research question about CRPD implementation...",
            value=st.session_state.get("research_query_text", ""),
            key="research_input",
        )

        # Example query chips
        st.markdown(
            "<p style='font-size:0.88rem;color:#424752;margin-bottom:4px;'>"
            "Try an example question:</p>",
            unsafe_allow_html=True,
        )
        chip_cols = st.columns(3)
        for i, (col, example) in enumerate(zip(chip_cols, EXAMPLE_QUERIES, strict=False)):
            with col:
                if st.button(
                    example[:60] + "..." if len(example) > 60 else example,
                    key=f"example_chip_{i}",
                    width="stretch",
                ):
                    st.session_state["research_query_text"] = example
                    st.rerun()

        # Rate limit display
        remaining = _get_remaining_queries()
        if remaining <= 3:
            st.caption(f"Queries remaining this session: {remaining} of {_SESSION_LIMIT}")

        # Research button
        col_btn, _ = st.columns([1, 4])
        with col_btn:
            research_clicked = st.button(
                "Research",
                type="primary",
                disabled=(not query or remaining <= 0),
                key="research_submit",
                width="stretch",
            )

        if remaining <= 0 and query:
            st.warning(
                "Session query limit reached. Refresh the page to reset.",
                icon="--",
            )

        # Execute pipeline
        if research_clicked and query and remaining > 0:
            _increment_query_count()
            with st.spinner("Researching your question -- this may take 30-60 seconds..."):
                result = run_research_pipeline(
                    query, tier=_selected_tier, df=df, article_presets=article_presets
                )
            st.session_state["research_result"] = result

        # ── Results ──────────────────────────────────────────────────────────
        result = st.session_state.get("research_result")
        if result is not None:
            # Error state
            if result.get("error") and not result.get("briefing"):
                st.error(result["error"])
            else:
                # Show partial error as warning (e.g., Writer fallback)
                if result.get("error"):
                    st.warning(result["error"])

                # Research Plan card
                sub_qs = result.get("sub_questions", [])
                if sub_qs:
                    plan_items = "".join(f"<li>{sq}</li>" for sq in sub_qs)
                    st.markdown(
                        f"""
                        <div style="{_CARD_STYLE}">
                            <h4 style="color:#003F87;margin-top:0;margin-bottom:12px;
                                        font-size:1rem;font-weight:700;">
                                Research Plan
                            </h4>
                            <ol style="margin:0;padding-left:20px;color:#424752;
                                       font-size:0.92rem;line-height:1.7;">
                                {plan_items}
                            </ol>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Findings card
                briefing = result.get("briefing", "")
                if briefing:
                    st.markdown(
                        f'<div style="{_CARD_STYLE}">',
                        unsafe_allow_html=True,
                    )
                    st.markdown(briefing)
                    st.markdown("</div>", unsafe_allow_html=True)

                # "By the Numbers" callout (Flag #4)
                analyst = result.get("analyst")
                if analyst and analyst.get("invoked"):
                    _model_summary = analyst.get("model_shift_summary", "")
                    _article_summary = analyst.get("article_freq_summary", "")
                    _keyword_summary = analyst.get("keyword_summary", "")

                    _numbers_body = ""
                    if _model_summary:
                        _numbers_body += f"<p style='margin:4px 0;font-size:0.88rem;color:#424752;'>{_model_summary}</p>"
                    if _article_summary:
                        _numbers_body += f"<p style='margin:4px 0;font-size:0.88rem;color:#424752;'>{_article_summary}</p>"
                    if _keyword_summary:
                        _numbers_body += f"<p style='margin:4px 0;font-size:0.88rem;color:#424752;'>{_keyword_summary}</p>"

                    if _numbers_body:
                        st.markdown(
                            f"""
                            <div style="{_CALLOUT_STYLE}">
                                <h4 style="color:#003F87;margin-top:0;margin-bottom:8px;
                                            font-size:0.95rem;font-weight:700;">
                                    By the Numbers
                                </h4>
                                <p style="font-size:0.82rem;color:#5a6377;
                                          margin-bottom:10px;line-height:1.55;
                                          font-style:italic;">
                                    These figures describe language patterns in the cited
                                    documents &mdash; they are not compliance scores or
                                    quality ratings. Keyword frequency reflects document
                                    type, reporting period, and authorship (State Party
                                    vs. Committee).
                                </p>
                                {_numbers_body}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                # Citation chips + retrieval coverage (Flag #9)
                all_chunks = result.get("all_chunks", [])
                if all_chunks:
                    n_chunks = len(all_chunks)
                    n_total_docs = stats["n_docs"]
                    n_countries = len(set(c.get("country", "") for c in all_chunks))

                    # Retrieval coverage indicator
                    st.markdown(
                        f"""
                        <p style="font-size:0.82rem;color:#5a6377;line-height:1.55;
                                  margin:1rem 0 0.5rem 0;font-style:italic;">
                            This briefing cites {n_chunks} of {n_total_docs}
                            documents in the database. Results reflect the documents
                            most semantically similar to your query &mdash; not all
                            relevant documents.
                        </p>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Citation chips
                    seen_chips: set[str] = set()
                    chips_html = ""
                    for c in all_chunks:
                        label = (
                            f"{c.get('country', 'Unknown')}, "
                            f"{c.get('doc_type', 'Unknown')}, "
                            f"{c.get('year', 'Unknown')}"
                        )
                        if label not in seen_chips:
                            seen_chips.add(label)
                            chips_html += f'<span style="{_CHIP_STYLE}">{label}</span>'
                    st.markdown(
                        f'<div style="margin:0.5rem 0 1rem 0;">{chips_html}</div>',
                        unsafe_allow_html=True,
                    )

                    # Metadata line
                    llm_calls = result.get("llm_calls", 0)
                    duration = result.get("duration_seconds", 0)
                    st.caption(
                        f"Retrieved {n_chunks} excerpts from "
                        f"{n_countries} States Parties "
                        f"| {llm_calls} LLM calls "
                        f"| {duration}s "
                        f"| Processed locally"
                    )

                # Follow-up action cards (Flag #7)
                st.markdown(
                    f"""
                    <div style="display:flex;gap:12px;margin:1rem 0;">
                        <div style="{_CARD_STYLE}flex:1;margin:0;">
                            <h4 style="color:#003F87;margin:0 0 6px 0;font-size:0.92rem;
                                        font-weight:700;">
                                Compare States Parties
                            </h4>
                            <p style="font-size:0.82rem;color:#424752;margin:0;
                                      line-height:1.5;">
                                Explore reporting patterns across the States Parties
                                mentioned in this briefing. Comparisons reflect document
                                availability and language patterns, not compliance rankings.
                            </p>
                        </div>
                        <div style="{_CARD_STYLE}flex:1;margin:0;">
                            <h4 style="color:#003F87;margin:0 0 6px 0;font-size:0.92rem;
                                        font-weight:700;">
                                Explore Article Coverage
                            </h4>
                            <p style="font-size:0.82rem;color:#424752;margin:0;
                                      line-height:1.5;">
                                See which CRPD articles appear most across these documents
                            </p>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Export bar removed — no-data-download policy active
                st.markdown("---")

                # Key Capabilities in expander (moved from bottom)
                with st.expander("Key Capabilities"):
                    capabilities = [
                        (
                            "Document-Grounded Research",
                            (
                                f"Structured briefings grounded in {stats['n_docs']}"
                                " document excerpts from the UN reporting cycle."
                            ),
                            "All tiers",
                        ),
                        (
                            "Full Citation Trails",
                            "Every claim traced to the source document, document type, and year.",
                            "All tiers",
                        ),
                        (
                            "Article & Keyword Analysis",
                            (
                                "Explore how CRPD articles are referenced and how"
                                " rights-based versus medical-model language is used."
                            ),
                            "All tiers",
                        ),
                        (
                            "Cross-Document Comparison",
                            (
                                "Surface common themes and differences across document"
                                " excerpts from multiple States Parties."
                            ),
                            "Extended",
                        ),
                        (
                            "Country Reporting Profiles",
                            (
                                "Structured briefing for any State Party\u2019s reporting"
                                " history, language patterns, and article coverage."
                            ),
                            "Extended",
                        ),
                        (
                            "Evidence Standards",
                            (
                                "Every output includes methodology disclosure, source"
                                " separation between State Party and Committee documents,"
                                " and measurement limitations."
                            ),
                            "All tiers",
                        ),
                    ]
                    row1 = st.columns(3)
                    for col, (title, desc, badge) in zip(row1, capabilities[:3], strict=False):
                        with col:
                            st.markdown(
                                f"""
                                <div class="about-info-box" style="min-height:180px;">
                                    <span style="display:inline-block;padding:3px 10px;
                                        background:rgba(0,63,135,0.08);border-radius:50px;
                                        font-size:0.75rem;font-weight:600;color:#003F87;
                                        margin-bottom:8px;">{badge}</span>
                                    <h4 style="color:#003F87;margin:0 0 6px 0;
                                        font-size:0.95rem;">{title}</h4>
                                    <p style="font-size:0.85rem;color:#424752;
                                        line-height:1.55;margin:0;">{desc}</p>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                    row2 = st.columns(3)
                    for col, (title, desc, badge) in zip(row2, capabilities[3:], strict=False):
                        with col:
                            st.markdown(
                                f"""
                                <div class="about-info-box" style="min-height:180px;">
                                    <span style="display:inline-block;padding:3px 10px;
                                        background:rgba(0,63,135,0.08);border-radius:50px;
                                        font-size:0.75rem;font-weight:600;color:#003F87;
                                        margin-bottom:8px;">{badge}</span>
                                    <h4 style="color:#003F87;margin:0 0 6px 0;
                                        font-size:0.95rem;">{title}</h4>
                                    <p style="font-size:0.85rem;color:#424752;
                                        line-height:1.55;margin:0;">{desc}</p>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                # Methodology appendix
                _meth_stats = get_dataset_stats()
                _methodology = generate_methodology_appendix(result, _meth_stats, article_presets)
                with st.expander("Methodology Appendix"):
                    st.markdown(_methodology)

    # ── RIGHT PANEL ──────────────────────────────────────────────────────────
    with right_panel:
        st.markdown(
            "<h3 style='color:#003F87;margin-top:0;font-size:1.1rem;"
            "font-weight:700;'>Source Documents</h3>",
            unsafe_allow_html=True,
        )

        result = st.session_state.get("research_result")

        if result is not None and result.get("all_chunks"):
            # Sort toggle (Flag #1)
            _sort_order = st.radio(
                "Sort order",
                ["Most cited", "Alphabetical"],
                horizontal=True,
                label_visibility="collapsed",
                key="research_source_sort",
            )
            st.caption("Sorted by citation frequency. Toggle to sort alphabetically.")

            sources = _extract_unique_sources(result)
            if _sort_order == "Alphabetical":
                sources = sorted(sources, key=lambda x: x["country"])

            # Source document cards
            for src in sources:
                st.markdown(
                    _source_card_html(src, today_str),
                    unsafe_allow_html=True,
                )

            # Keyword Analysis Summary card (Flag #2, #6)
            analyst = result.get("analyst")
            if analyst and analyst.get("invoked"):
                _model_summary = analyst.get("model_shift_summary", "")
                _article_summary = analyst.get("article_freq_summary", "")
                _n_docs = analyst.get("n_docs_analyzed", 0)
                _n_countries = analyst.get("n_countries_analyzed", 0)

                _analyst_body = ""
                if _model_summary:
                    _analyst_body += (
                        f"<p style='margin:4px 0;font-size:0.82rem;"
                        f"color:#424752;'>{_model_summary}</p>"
                    )
                if _article_summary:
                    _analyst_body += (
                        f"<p style='margin:4px 0;font-size:0.82rem;"
                        f"color:#424752;'>{_article_summary}</p>"
                    )

                if _analyst_body:
                    st.markdown(
                        f"""
                        <div style="{_CARD_STYLE}margin-top:16px;">
                            <h4 style="color:#003F87;margin-top:0;margin-bottom:4px;
                                        font-size:0.95rem;font-weight:700;">
                                Keyword Analysis Summary
                            </h4>
                            <p style="font-size:0.78rem;color:#5a6377;margin:0 0 10px 0;">
                                Automated analysis of rights-based and medical-model
                                language patterns in the cited documents.
                            </p>
                            {_analyst_body}
                            <p style="font-size:0.75rem;color:#7a8194;margin:10px 0 0 0;
                                      font-style:italic;">
                                Based on {_n_docs} documents from
                                {_n_countries} States Parties.
                            </p>
                            <p style="font-size:0.75rem;color:#7a8194;margin:4px 0 0 0;">
                                How was this computed? See the Methodology Appendix
                                below for dictionary definitions and limitations.
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            # Empty state
            st.markdown(
                "<p style='font-size:0.88rem;color:#5a6377;line-height:1.6;"
                "margin-bottom:16px;'>"
                "Submit a research question to see the documents and excerpts "
                "cited in the response.</p>",
                unsafe_allow_html=True,
            )

        # "How It Works" (always visible in right panel)
        with st.expander("About this tool"):
            st.markdown(
                """
                <div style="background:#F2F4F8;border-radius:0.75rem;padding:16px;">
                    <p style="font-size:0.82rem;font-weight:600;color:#003F87;
                              margin-bottom:8px;">How It Works</p>
                    <ol style="font-size:0.82rem;color:#424752;padding-left:20px;
                               margin:0;line-height:1.8;">
                        <li><strong>Planner</strong> decomposes your question</li>
                        <li><strong>Retriever</strong> searches document excerpts</li>
                        <li><strong>Synthesizer</strong> assembles findings</li>
                        <li><strong>Analyst</strong> runs keyword analysis</li>
                        <li><strong>Reviewer</strong> checks evidence standards</li>
                        <li><strong>Writer</strong> produces the briefing</li>
                    </ol>
                </div>
                """,
                unsafe_allow_html=True,
            )
