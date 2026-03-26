import copy
from datetime import datetime
import json
import re

import altair as alt
import branca.colormap as cm
import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pycountry
import streamlit as st
from streamlit_folium import st_folium

from src.analysis import (
    DOMAIN_STOPWORDS,
    article_frequency,
    extract_distinctive_terms,
    extract_ngrams,
    extract_topics_lda,
    global_topic_transform,
    keyword_counts,
    model_shift_table,
)
from src.colors import (
    CARD_BG,
    CATEGORICAL_PALETTE,
    COMPARE_PALETTE,
    DOC_TYPE_COLORS,
    MAP_NO_DATA,
    MODEL_COLORS,
    NARRATIVE_BG,
    PHASE_BALANCED_BG,
    PHASE_BALANCED_TEXT,
    PHASE_MEDICAL_BG,
    PHASE_RIGHTS_BG,
    REGION_COLORS,
    SEQUENTIAL_BLUES,
    TEXT_MUTED,
    TREND_COLORS,
)
from src.components import render_accessible_table
from src.data_loader import display_columns, get_custom_organizations, get_dataset_stats, load_data


@st.cache_data
def _load_geojson():
    """Load Natural Earth countries GeoJSON (cached)."""
    with open("data/countries.geojson") as f:
        return json.load(f)


# ── Diverging palette thresholds for Reporting Gap metric ──
_REPORTING_GAP_DOMAIN = [0, 3, 6]
_REPORTING_GAP_COLORS = [
    "#009E73",  # Green (0-2 year gap — on track)
    "#E69F00",  # Amber (3-5 year gap — overdue)
    "#D55E00",  # Red (6+ year gap — critically overdue)
]


@st.cache_data
def _compute_country_terms(df_json: str, top_n: int = 3) -> dict:
    """Compute top terms per country from document text. Cached to avoid recomputation."""
    from collections import Counter

    df_terms = pd.read_json(df_json, orient="split")
    country_terms = {}
    for c, sub in df_terms.groupby("country"):
        texts = sub["clean_text"].dropna().astype(str).tolist()
        if texts:
            words = []
            for t in texts:
                words.extend(
                    w for w in re.findall(r"\b[a-z]{4,}\b", t.lower()) if w not in DOMAIN_STOPWORDS
                )
            top = [w for w, _ in Counter(words).most_common(top_n)]
            country_terms[c] = ", ".join(top) if top else ""
        else:
            country_terms[c] = ""
    return country_terms


def render_documents(df, article_presets=None):
    """Sub-tab for document browsing, search, and comparison."""
    from src.data_loader import load_article_dict

    if article_presets is None:
        article_presets = load_article_dict()

    st.subheader("Explore Documents")

    # ── Two entry points: text search OR country+article comparison ──
    _entry = st.radio(
        "How would you like to compare?",
        ["Search by Text", "Compare by Country & Article"],
        horizontal=True,
        key="doc_entry_mode",
        help=(
            "**Search by Text:** Find documents containing specific keywords, "
            "then compare side-by-side. "
            "**Compare by Country & Article:** Pick countries and CRPD articles "
            "to see how each country addresses specific rights."
        ),
    )

    if _entry == "Compare by Country & Article":
        _render_country_article_comparison(df, article_presets)
        return

    st.caption("Search CRPD documents matching your sidebar filters.")

    if len(df):
        # ── Fix #5: wrap search in form to prevent keystroke reruns ──
        with st.form("doc_search_form", clear_on_submit=False):
            search_query = st.text_input(
                "Search document text",
                placeholder="e.g. inclusive education, legal capacity, reasonable accommodation...",
                help="Searches the full document text within the currently filtered results.",
            )
            st.form_submit_button("Search", use_container_width=False)

        df_search = df.copy()
        if search_query.strip():
            mask = (
                df_search["clean_text"]
                .astype(str)
                .str.contains(search_query.strip(), case=False, na=False, regex=False)
            )
            df_search = df_search[mask]
            st.caption(
                f"Found **{len(df_search):,}** documents containing"
                f" \u2018{search_query}\u2019 (out of {len(df):,} filtered)"
            )
        else:
            st.caption(f"Showing {len(df_search):,} documents matching current filters")

        # ── Fix #6: Browse table FIRST, then selection + toggle below ──
        # ── Browse results table (always visible) ──
        display_cols = ["country", "year", "doc_type", "region"]
        if "word_count" in df_search.columns:
            display_cols.append("word_count")
        if "text_snippet" in df_search.columns:
            display_cols.append("text_snippet")

        _search_display = df_search[display_cols].sort_values("year", ascending=False)
        if "text_snippet" in _search_display.columns:
            _search_display = _search_display.copy()

            # Fix #13: truncate at word boundary, only add "..." if truncated
            def _smart_truncate(s, limit=150):
                s = str(s)
                if len(s) <= limit:
                    return s
                trunc = s[:limit].rsplit(" ", 1)[0]
                return trunc + "\u2026" if trunc else s[:limit] + "\u2026"

            _search_display["text_snippet"] = _search_display["text_snippet"].apply(_smart_truncate)

        # Fix #17: visual separator before results
        st.markdown("---")

        render_accessible_table(
            display_columns(_search_display),
            caption=f"Document search results (n={len(df_search)})",
            max_height=500,
            page_size=20,
            page_key="doc_browse_page",
        )

        # ── Fix #17: visual separator between browse and compare controls ──
        st.markdown("---")

        # ── Document selection for comparison ──
        _doc_options = []
        _doc_index = {}  # label -> row index
        _seen_labels = set()
        for idx, row in df_search.iterrows():
            # Fix #15: skip rows with missing year or nan-string country
            if pd.isna(row["year"]):
                continue
            _country_val = str(row["country"])
            if _country_val in ("nan", ""):
                continue
            label = f"{_country_val} \u2014 {int(row['year'])} \u2014 {row['doc_type']}"
            # Fix #14: handle label collision by appending index
            if label in _seen_labels:
                label = f"{label} [{idx}]"
            _seen_labels.add(label)
            _doc_options.append(label)
            _doc_index[label] = idx

        # Fix #1: validate stored selections against current options
        _stored = st.session_state.get("doc_compare_selection", [])
        _valid_stored = [s for s in _stored if s in _doc_index]
        if _valid_stored != _stored:
            st.session_state["doc_compare_selection"] = _valid_stored

        _selected_docs = st.multiselect(
            "Select documents to compare (2\u20135)",
            options=_doc_options,
            max_selections=5,
            default=_valid_stored,
            key="doc_compare_selection",
            help="Choose 2 to 5 documents from the search results above.",
            placeholder="Type a State Party name or year to filter\u2026",
        )
        _n_sel = len(_selected_docs)

        # ── Fix #7: replace buttons with segmented control ──
        _mode_options = ["Browse", f"Compare ({_n_sel})"]
        _current_mode = st.session_state.get("doc_compare_mode", "Browse")
        if _current_mode not in ("Browse", "Compare"):
            _current_mode = "Browse"
        _mode_choice = st.radio(
            "View mode",
            _mode_options,
            index=0 if _current_mode == "Browse" else 1,
            horizontal=True,
            key="doc_mode_radio",
            label_visibility="collapsed",
        )
        _compare_mode = _mode_choice.startswith("Compare") and _n_sel >= 2

        if _compare_mode:
            if _n_sel < 2:
                st.info("Select at least 2 documents above to compare.")
            else:
                _render_document_comparison(
                    df_search, _selected_docs, _doc_index, article_presets, df
                )

    else:
        st.info("No documents match current filters.")


def _render_country_article_comparison(df, article_presets):
    """Compare how selected countries address specific CRPD articles.

    Flow: country picker → theme filter → article picker → Compare button → cards.
    """
    import re

    # ── Article theme groups ──
    _article_themes = {
        "All Articles": None,
        "General Principles (Articles 1\u20134)": list(range(1, 5)),
        "Civil & Political Rights (Articles 5\u201313)": list(range(5, 14)),
        "Autonomy & Participation (Articles 14\u201321)": list(range(14, 22)),
        "Social & Economic Rights (Articles 22\u201328)": list(range(22, 29)),
        "Implementation & Monitoring (Articles 29\u201333)": list(range(29, 34)),
        "Procedural Articles (Articles 34\u201350)": list(range(34, 51)),
    }

    _all_articles = sorted(
        article_presets.keys(),
        key=lambda a: int(re.search(r"\d+", a).group()) if re.search(r"\d+", a) else 99,
    )

    st.caption(
        "Compare how States Parties address specific CRPD articles across their reporting history."
    )

    # ── Selection UI ──
    _countries = sorted(df["country"].dropna().unique().tolist())

    _sel_countries = st.multiselect(
        "Select States Parties to compare (2\u20135)",
        options=_countries,
        max_selections=5,
        key="cac_countries",
        placeholder="Type a State Party name\u2026",
    )

    for _c in _sel_countries:
        _n = len(df[df["country"] == _c])
        if _n == 0:
            st.warning(f"{_c} has no documents in the dataset.")
        elif _n == 1:
            st.caption(f"\u26a0\ufe0f {_c} has only 1 document \u2014 comparison may be limited.")

    _theme = st.selectbox(
        "Filter articles by theme",
        options=list(_article_themes.keys()),
        key="cac_theme",
    )
    _theme_nums = _article_themes[_theme]

    if _theme_nums:
        _filtered_articles = [
            a for a in _all_articles if int(re.search(r"\d+", a).group()) in _theme_nums
        ]
    else:
        _filtered_articles = _all_articles

    _sel_articles = st.multiselect(
        "Select CRPD articles to compare (1\u20135)",
        options=_filtered_articles,
        max_selections=5,
        key="cac_articles",
        placeholder="Choose up to 5 articles\u2026",
    )

    _ready = len(_sel_countries) >= 2 and len(_sel_articles) >= 1
    _compare_clicked = st.button(
        "Compare",
        type="primary",
        disabled=not _ready,
        key="cac_compare_btn",
    )

    if not _compare_clicked and not st.session_state.get("cac_last_compared"):
        if not _ready:
            st.info("Select at least 2 States Parties and 1 article, then click **Compare**.")
        return

    if _compare_clicked:
        st.session_state["cac_last_compared"] = {
            "countries": _sel_countries,
            "articles": _sel_articles,
        }

    _last = st.session_state.get("cac_last_compared", {})
    _cmp_countries = _last.get("countries", _sel_countries)
    _cmp_articles = _last.get("articles", _sel_articles)

    if len(_cmp_countries) < 2 or len(_cmp_articles) < 1:
        return

    # ── Asymmetry warning ──
    _doc_counts = {c: len(df[df["country"] == c]) for c in _cmp_countries}
    _max_n = max(_doc_counts.values()) if _doc_counts else 0
    _min_n = min(_doc_counts.values()) if _doc_counts else 0
    if _max_n > 0 and _min_n > 0 and _max_n / _min_n > 3:
        st.info(
            "Document counts vary significantly "
            f"({', '.join(f'{c}: {n}' for c, n in _doc_counts.items())}). "
            "Raw keyword counts are not directly comparable across different "
            "document volumes."
        )

    _stats = get_dataset_stats()

    _card_css = (
        "border:1px solid #dce1e8;border-radius:8px;padding:20px 16px;"
        "background:#fff;box-shadow:0 1px 3px rgba(0,0,0,0.06);"
    )

    st.markdown("---")

    for _art_key in _cmp_articles:
        _art_num = re.search(r"\d+", _art_key)
        _art_short = f"Art. {_art_num.group()}" if _art_num else _art_key
        _keywords = article_presets.get(_art_key, [])

        st.markdown(f"### {_art_key}")
        st.caption(f"Keywords: {', '.join(_keywords[:5])}{'…' if len(_keywords) > 5 else ''}")

        _n_countries = len(_cmp_countries)
        _cols = st.columns(min(_n_countries, 3))

        for i, _country in enumerate(_cmp_countries):
            _col_idx = i % 3
            if _n_countries > 3 and i == 3:
                _cols = st.columns(min(_n_countries - 3, 3))
                _col_idx = 0

            with _cols[_col_idx]:
                _c_df = df[df["country"] == _country]
                _n_docs = len(_c_df)

                st.markdown(
                    f'<div role="region" aria-label="Article comparison for '
                    f'{_country}" style="{_card_css}">',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    f'<div style="font-size:18px;font-weight:600;'
                    f'color:{CATEGORICAL_PALETTE[0]};margin-bottom:4px;">'
                    f"{_country}</div>",
                    unsafe_allow_html=True,
                )

                if _n_docs == 0:
                    st.warning("No documents in dataset.")
                    st.markdown("</div>", unsafe_allow_html=True)
                    continue

                _years = _c_df["year"].dropna()
                _yr_range = (
                    f"{int(_years.min())}\u2013{int(_years.max())}"
                    if len(_years) > 1
                    else str(int(_years.iloc[0]))
                )
                st.caption(f"Based on {_n_docs} document{'s' if _n_docs > 1 else ''} ({_yr_range})")

                _af = article_frequency(_c_df, article_presets)
                _art_row = _af[_af["article"] == _art_key] if len(_af) else pd.DataFrame()
                _count = int(_art_row["count"].iloc[0]) if len(_art_row) else 0
                _total = int(_af["count"].sum()) if len(_af) else 0
                _share = round(_count / _total * 100, 1) if _total > 0 else 0.0

                if len(_af):
                    _af_sorted = _af.sort_values("count", ascending=False).reset_index(drop=True)
                    _rank_match = _af_sorted[_af_sorted["article"] == _art_key]
                    _rank = int(_rank_match.index[0]) + 1 if len(_rank_match) else None
                    _total_arts = len(_af_sorted)
                else:
                    _rank = None
                    _total_arts = 0

                if _count == 0:
                    st.markdown(
                        f"**No mentions found** for {_art_short}. "
                        "This may reflect different terminology or "
                        "translation, not absence of policy."
                    )
                else:
                    st.metric("Keyword Mentions", f"{_count:,}")
                    st.metric("Article Share", f"{_share}%")
                    if _rank:
                        st.metric(
                            "Coverage Rank",
                            f"{_rank} of {_total_arts} articles",
                        )

                # KWIC passages (up to 3)
                _combined_text = " ".join(str(t) for t in _c_df["clean_text"].dropna().tolist())
                if _combined_text and _keywords and _count > 0:
                    _pattern = "|".join(
                        re.escape(kw) for kw in sorted(_keywords, key=len, reverse=True)
                    )
                    _matches = list(re.finditer(_pattern, _combined_text, re.IGNORECASE))
                    if _matches:
                        st.markdown(
                            f"**Sample passages** ({min(len(_matches), 3)} of {len(_matches)}):"
                        )
                        for _m in _matches[:3]:
                            _start = max(0, _m.start() - 60)
                            _end = min(len(_combined_text), _m.end() + 60)
                            _ctx = _combined_text[_start:_end].replace("\n", " ")
                            st.markdown(f"> \u2026{_ctx}\u2026")

                # Per-document detail
                if _n_docs > 1 and _count > 0:
                    with st.expander("View by document"):
                        _doc_rows = []
                        for _, _r in _c_df.iterrows():
                            _r_df = pd.DataFrame([_r])
                            _r_af = article_frequency(_r_df, article_presets)
                            _r_match = (
                                _r_af[_r_af["article"] == _art_key]
                                if len(_r_af)
                                else pd.DataFrame()
                            )
                            _r_count = int(_r_match["count"].iloc[0]) if len(_r_match) else 0
                            _doc_rows.append(
                                {
                                    "Document Type": _r.get("doc_type", "\u2014"),
                                    "Year": (int(_r["year"]) if pd.notna(_r["year"]) else "\u2014"),
                                    "Keyword Hits": _r_count,
                                }
                            )
                        if _doc_rows:
                            render_accessible_table(
                                pd.DataFrame(_doc_rows),
                                caption=f"{_art_short} mentions by document",
                            )

                st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.caption(
        "Counts reflect keyword matches in UN Treaty Body documents, "
        "not policy implementation. Document length and type affect match rates."
    )
    with st.expander("Methodology"):
        st.markdown(
            "Metrics use **dictionary-based keyword matching** against a validated "
            "CRPD term list (50 articles with multi-word "
            "keyword phrases). Matching is case-insensitive on extracted document "
            "text. Sample passages show a 60-character context window around each "
            "keyword match. Translation effects may influence results for documents "
            "not originally authored in English. Treat all metrics as "
            "**hypothesis-generating, not definitive** \u2014 they require "
            "qualitative validation."
        )
        st.caption(f"Data current through {_stats['year_max']}.")


def _render_document_comparison(df_search, selected_docs, doc_index, article_presets, df_full):
    """Render the document comparison view with metrics, heatmap, and similarity.

    Parameters
    ----------
    df_search : DataFrame  – current filtered/searched results
    selected_docs : list    – labels of selected documents
    doc_index : dict        – label -> DataFrame index
    article_presets : dict  – article keyword dictionary
    df_full : DataFrame     – full unfiltered dataset (for percentiles)
    """
    _n_docs = len(selected_docs)

    _sel_indices = [doc_index[label] for label in selected_docs]
    _sel_df = df_search.loc[_sel_indices]

    st.markdown("#### Document Comparison")

    # Mixed doc-type caveat
    _sel_types = _sel_df["doc_type"].unique()
    if len(_sel_types) > 1:
        st.info(
            "Rights-based language share varies by author. "
            "Concluding Observations are written by the CRPD Committee, which applies "
            "a rights-based framework by mandate. State Reports are authored by the "
            "State Party. Cross-type comparisons reflect different authorial voices, "
            "not necessarily differences in implementation commitment."
        )

    # Cross-country caveat
    _sel_countries = _sel_df["country"].unique()
    if len(_sel_countries) > 1:
        st.caption(
            "Cross-country comparisons reflect reporting vocabulary and structure, "
            "not disability rights outcomes. National context, translation, and "
            "reporting cycle stage affect all metrics."
        )

    # Fix #2: Document-length caveat (always visible)
    st.caption(
        "Document length affects keyword detection rates \u2014 "
        "compare word counts alongside other metrics."
    )

    # ── Fix #9: compute corpus-wide percentile reference from full dataset ──
    _full_wc = df_full["word_count"].dropna().astype(float)

    # ── Compute per-document metrics ──
    _all_doc_metrics = []
    for idx in _sel_indices:
        _row = df_search.loc[[idx]]
        _country = _row["country"].iloc[0]
        _year = int(_row["year"].iloc[0])
        _doc_type = _row["doc_type"].iloc[0]
        _wc = int(_row["word_count"].iloc[0]) if "word_count" in _row.columns else 0

        # Fix #4: detect empty clean_text
        _clean = str(_row["clean_text"].iloc[0]) if "clean_text" in _row.columns else ""
        _has_text = bool(_clean and _clean not in ("nan", "", "None"))

        # Rights-based language share
        if _has_text:
            _mt = model_shift_table(_row)
            _total_model = (_mt["rights"].sum() + _mt["medical"].sum()) if len(_mt) else 0
            _rights_pct = (_mt["rights"].sum() / _total_model * 100) if _total_model > 0 else 0.0
        else:
            _rights_pct = None  # signals "no text"

        # Article frequency
        if _has_text:
            _af = article_frequency(_row, article_presets)
            _articles_present = set(_af["article"].tolist()) if len(_af) else set()
            _article_breadth = len(_articles_present)
        else:
            _af = pd.DataFrame()
            _articles_present = set()
            _article_breadth = 0

        # Top 5 articles
        _top5 = []
        if len(_af):
            _top5_df = _af.nlargest(5, "count")
            _top5 = list(
                zip(_top5_df["article"].tolist(), _top5_df["count"].tolist(), strict=False)
            )

        # Keyword density (total article keyword hits / word_count * 1000)
        _total_hits = int(_af["count"].sum()) if len(_af) else 0
        _kw_density = (_total_hits / _wc * 1000) if _wc > 0 else 0.0

        # Fix #9: percentile for word count (against full dataset)
        _wc_pct = round((_full_wc < _wc).sum() / len(_full_wc) * 100) if len(_full_wc) > 0 else None

        _all_doc_metrics.append(
            {
                "country": _country,
                "year": _year,
                "doc_type": _doc_type,
                "word_count": _wc,
                "rights_pct": _rights_pct,
                "article_breadth": _article_breadth,
                "top5": _top5,
                "articles_present": _articles_present,
                "kw_density": _kw_density,
                "has_text": _has_text,
                "wc_percentile": _wc_pct,
            }
        )

    # ── Fix #3 & #10: styled card containers with semantic grouping ──
    _card_css = (
        "border:1px solid #dce1e8;border-radius:8px;padding:16px 14px;"
        "background:#fff;box-shadow:0 1px 3px rgba(0,0,0,0.06);"
    )

    if _n_docs <= 3:
        _cols = st.columns(_n_docs)
        for i, (_label, dm) in enumerate(zip(selected_docs, _all_doc_metrics, strict=False)):
            with _cols[i]:
                st.markdown(
                    f'<div role="group" aria-label="Metrics for {dm["country"]} '
                    f'{dm["year"]}" style="{_card_css}">',
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{dm['country']}**")
                st.caption(f"{dm['year']} \u00b7 {dm['doc_type']}")

                # Fix #4: show warning if no text
                if not dm["has_text"]:
                    st.warning(
                        "Text not available for this document. "
                        "Keyword analysis shows \u2014 (em dash)."
                    )

                _wc_label = f"{dm['word_count']:,}"
                if dm["wc_percentile"] is not None:
                    _wc_label += f"  ({dm['wc_percentile']}th percentile)"
                st.metric("Document Length (words)", _wc_label)
                st.metric(
                    "Rights-Based Language Share",
                    f"{dm['rights_pct']:.1f}%" if dm["rights_pct"] is not None else "\u2014",
                )
                st.metric("CRPD Articles Detected", dm["article_breadth"])
                # Fix #21: keyword density in card view too
                st.metric(
                    "Keyword Density (per 1,000 words)",
                    f"{dm['kw_density']:.1f}" if dm["has_text"] else "\u2014",
                )

                st.markdown("**Top 5 Articles:**")
                if dm["top5"]:
                    for art, count in dm["top5"]:
                        _short = art.split(" \u2014 ", 1)[1] if " \u2014 " in art else art
                        st.markdown(f"- {_short}: {count}")
                else:
                    st.markdown("- No articles detected")

                st.markdown("</div>", unsafe_allow_html=True)
    else:
        # Build comparison table for 4-5 documents
        _tbl_data = {
            "Metric": [
                "Document Length (words)",
                "Rights-Based Language Share",
                "CRPD Articles Detected",
                "Keyword Density (per 1,000 words)",
                "Top Article",
            ]
        }
        for dm in _all_doc_metrics:
            _col_label = f"{dm['country']} \u2014 {dm['year']}"
            _top_art = ""
            if dm["top5"]:
                _a = dm["top5"][0][0]
                _top_art = _a.split(" \u2014 ", 1)[1] if " \u2014 " in _a else _a
            _wc_str = f"{dm['word_count']:,}"
            if dm["wc_percentile"] is not None:
                _wc_str += f" ({dm['wc_percentile']}th pctl)"
            _tbl_data[_col_label] = [
                _wc_str,
                f"{dm['rights_pct']:.1f}%" if dm["rights_pct"] is not None else "\u2014",
                str(dm["article_breadth"]),
                f"{dm['kw_density']:.1f}" if dm["has_text"] else "\u2014",
                _top_art if _top_art else "\u2014",
            ]
        _tbl_df = pd.DataFrame(_tbl_data)
        render_accessible_table(
            _tbl_df,
            caption=f"Document comparison ({_n_docs} documents)",
        )

    # ── Article overlap heatmap ──
    _all_articles = set()
    for dm in _all_doc_metrics:
        _all_articles.update(dm["articles_present"])

    if _all_articles:
        st.markdown("---")
        # Sort by how many docs reference each article (descending)
        _art_list = sorted(
            _all_articles,
            key=lambda a: sum(1 for dm in _all_doc_metrics if a in dm["articles_present"]),
            reverse=True,
        )
        _art_list = _art_list[:15]  # Cap at top 15

        _matrix = []
        _text_matrix = []
        for art in _art_list:
            row = []
            text_row = []
            for dm in _all_doc_metrics:
                present = 1 if art in dm["articles_present"] else 0
                row.append(present)
                text_row.append("Yes" if present else "\u2014")
            _matrix.append(row)
            _text_matrix.append(text_row)

        # Short labels for articles
        _art_labels = []
        for a in _art_list:
            if "\u2014" in a:
                _parts = a.split("\u2014", 1)
                _short = f"Art. {_parts[0].strip().split()[-1]}"
                _name = _parts[1].strip()
                _art_labels.append(f"{_short} ({_name})")
            else:
                _art_labels.append(a)

        # Short labels for docs
        _doc_short = [f"{dm['country']}\n{dm['year']}" for dm in _all_doc_metrics]

        # Fix #11: build sr-only alt-text summary
        _alt_articles = ", ".join(
            f"{dm['country']} {dm['year']}: {dm['article_breadth']} articles"
            for dm in _all_doc_metrics
        )

        fig = go.Figure(
            go.Heatmap(
                z=_matrix,
                x=_doc_short,
                y=_art_labels,
                colorscale=[[0, CARD_BG], [1, CATEGORICAL_PALETTE[0]]],
                showscale=False,
                text=_text_matrix,
                texttemplate="%{text}",
                hovertemplate="<b>%{x}</b><br>%{y}<br>%{text}<extra></extra>",
            )
        )
        fig.update_layout(
            title=dict(
                text="Article Coverage Overlap",
                font=dict(family="Inter", size=15),
            ),
            font=dict(family="Inter"),
            margin=dict(l=220, r=20, t=50, b=60),
            height=min(420, max(200, 28 * len(_art_list) + 80)),
            xaxis=dict(side="top", tickfont=dict(size=11)),
            yaxis=dict(tickfont=dict(size=12), autorange="reversed"),
        )
        st.plotly_chart(fig, use_container_width=True, key="doc_compare_heatmap")
        # Fix #11: sr-only alt text
        st.markdown(
            f'<p class="sr-only">Article coverage heatmap: {_alt_articles}</p>',
            unsafe_allow_html=True,
        )
        # Fix #22: heatmap caption with length caveat
        st.caption(
            f"Article overlap: {_n_docs} documents \u00d7 {len(_art_labels)} articles. "
            "Blue cells = article detected; white = not detected. "
            "Longer documents are more likely to trigger keyword matches \u2014 "
            "compare word counts above."
        )

    # ── Analytical Detail (Jaccard + methodology — Fix #12: consolidated) ──
    with st.expander("Analytical Detail & Methodology"):
        if _n_docs == 2:
            _set_a = _all_doc_metrics[0]["articles_present"]
            _set_b = _all_doc_metrics[1]["articles_present"]
            _intersection = _set_a & _set_b
            _union = _set_a | _set_b
            _jaccard = len(_intersection) / len(_union) if _union else 0
            st.markdown(
                f"**Jaccard Similarity:** {_jaccard:.2f} \u2014 "
                f"these documents share {len(_intersection)} of "
                f"{len(_union)} referenced articles."
            )
        else:
            # Pairwise Jaccard for 3-5 docs
            _pairs = []
            for i in range(_n_docs):
                for j in range(i + 1, _n_docs):
                    _si = _all_doc_metrics[i]["articles_present"]
                    _sj = _all_doc_metrics[j]["articles_present"]
                    _inter = _si & _sj
                    _uni = _si | _sj
                    _jac = len(_inter) / len(_uni) if _uni else 0
                    _pairs.append(
                        {
                            "Document A": (
                                f"{_all_doc_metrics[i]['country']} ({_all_doc_metrics[i]['year']})"
                            ),
                            "Document B": (
                                f"{_all_doc_metrics[j]['country']} ({_all_doc_metrics[j]['year']})"
                            ),
                            "Shared Articles": len(_inter),
                            "Total Articles": len(_uni),
                            "Jaccard Similarity": f"{_jac:.2f}",
                        }
                    )
            if _pairs:
                _jac_df = pd.DataFrame(_pairs)
                render_accessible_table(
                    _jac_df,
                    caption="Pairwise Jaccard similarity (article overlap)",
                )

        # Fix #12 + #20: single consolidated methodology section
        st.markdown("---")
        st.markdown("**Methodology**")
        st.markdown(
            "Metrics use **dictionary-based keyword matching** against a validated "
            "CRPD term list (50+ articles with multi-word "
            "keyword phrases). Matching is case-insensitive regex on the full "
            "extracted document text. Rights-based language share measures vocabulary "
            "patterns, not compliance quality \u2014 a lower score does not indicate "
            "a rights violation. Jaccard similarity operates on binary article "
            "presence/absence (whether an article\u2019s keywords appear at least "
            "once), not on frequency counts. Treat all metrics as "
            "**hypothesis-generating, not definitive** \u2014 they require "
            "qualitative validation."
        )
        _stats = get_dataset_stats()
        st.caption(f"Data current through {_stats['year_max']}.")


def _country_metrics(country, year_from, year_to, full_df, article_presets):
    """Compute comparison metrics for a single country within a year window."""
    cdf = full_df[full_df["country"] == country]
    if year_from is None and year_to is None:
        cdf_window = cdf
    elif year_to is None:
        cdf_window = cdf[cdf["year"] >= year_from]
    else:
        cdf_window = cdf[(cdf["year"] >= year_from) & (cdf["year"] <= year_to)]
    mt = model_shift_table(cdf_window)
    total_model = (mt["rights"].sum() + mt["medical"].sum()) if len(mt) else 0
    r_pct = (mt["rights"].sum() / total_model * 100) if total_model > 0 else 0.0
    n_docs = len(cdf_window)
    avg_words = (
        cdf_window["word_count"].mean() if "word_count" in cdf_window.columns and n_docs else 0.0
    )
    art_df = article_frequency(cdf_window, article_presets)
    n_articles = art_df["article"].nunique() if not art_df.empty else 0
    # Fix #1: exact match to avoid counting "Response to Concluding Observations"
    has_co = (cdf_window["doc_type"] == "Concluding Observations").sum()
    has_report = (
        cdf_window["doc_type"]
        .isin(
            [
                "State Report",
                "List of Issues (LOI)",
                "Written Reply",
                "Response to Concluding Observations",
            ]
        )
        .sum()
    )
    co_rate = (has_co / has_report * 100) if has_report > 0 else 0.0
    yrange = (
        f"{int(cdf_window['year'].min())}–{int(cdf_window['year'].max())}"
        if n_docs and "year" in cdf_window.columns
        else "—"
    )
    return {
        "Rights-Based Language %": round(r_pct, 1),
        "Documents Submitted": n_docs,
        "Avg Document Length (words)": round(avg_words, 0) if not pd.isna(avg_words) else 0.0,
        "Article Coverage Breadth": n_articles,
        "CO Response Rate %": round(co_rate, 1),
        "_year_range": yrange,
        "_doc_types": cdf_window["doc_type"].nunique() if n_docs else 0,
    }


def _pct_change(base_val, current_val):
    """Compute % change with None/NaN guards (Fix #4)."""
    if base_val is None or current_val is None:
        return None
    if pd.isna(base_val) or pd.isna(current_val):
        return None
    if base_val == 0:
        return None
    return round((current_val - base_val) / abs(base_val) * 100, 1)


def _render_group_profile(
    df_group, group_name, group_type, df_all, article_presets, org_iso_codes=None
):
    """Render a region or organization profile with 7 sections."""
    _n_parties = df_group["country"].nunique()
    _n_docs = len(df_group)
    _yr_min = int(df_group["year"].min()) if len(df_group) else 0
    _yr_max = int(df_group["year"].max()) if len(df_group) else 0

    # Header
    if group_type == "Organization":
        _header = f"CRPD Reporting: {group_name} Member States"
    else:
        _header = f"CRPD Reporting: {group_name}"

    st.markdown(f"### {_header}")

    # Metric cards row
    _mc1, _mc2, _mc3 = st.columns(3)
    with _mc1:
        st.metric("States Parties", _n_parties)
    with _mc2:
        st.metric("Total Documents", f"{_n_docs:,}")
    with _mc3:
        st.metric("Year Range", f"{_yr_min}\u2013{_yr_max}" if _n_docs else "\u2014")

    # ── Section 2: Rights-Based Keyword Share ──
    _mt = model_shift_table(df_group)
    if len(_mt):
        _r = _mt["rights"].sum()
        _m = _mt["medical"].sum()
        _total = _r + _m
        if _total > 0:
            _weighted_pct = round(_r / _total * 100, 1)

            # Unweighted: per-country average
            _mt_country = _mt.groupby("country").agg(
                rights=("rights", "sum"), medical=("medical", "sum")
            )
            _mt_country["total"] = _mt_country["rights"] + _mt_country["medical"]
            _mt_country = _mt_country[_mt_country["total"] > 0]
            _mt_country["pct"] = _mt_country["rights"] / _mt_country["total"] * 100
            _unweighted_pct = round(_mt_country["pct"].mean(), 1)
            _n_with_data = len(_mt_country)

            st.markdown("#### Rights-Based Language")
            st.metric("Rights-Based Keyword Share", f"{_weighted_pct}%")
            st.caption(
                f"Weighted by document count across {_n_with_data} States Parties. "
                f"Unweighted State Party average: {_unweighted_pct}%. "
                "High-volume States Parties have greater influence on the weighted figure. "
                "See member table below for individual values."
            )

    # ── Section 3: Top 10 Articles ──
    _af = article_frequency(df_group, article_presets)
    if len(_af):
        _n_parties_af = df_group["country"].nunique()
        _top = _af.groupby("article")["count"].sum().nlargest(10).reset_index()
        _top["avg_per_sp"] = round(_top["count"] / _n_parties_af, 1)
        _top = _top.sort_values("avg_per_sp", ascending=True)

        st.markdown("#### Most Referenced CRPD Articles")
        fig = px.bar(
            _top,
            x="avg_per_sp",
            y="article",
            orientation="h",
            title="Top 10 Articles \u2014 Average Mentions per State Party",
            color_discrete_sequence=[CATEGORICAL_PALETTE[0]],
            labels={"avg_per_sp": "Avg. Mentions per State Party", "article": ""},
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, width="stretch", key=f"group_articles_{group_name}")
        st.caption(
            f"Average keyword mentions per State Party (n={_n_parties_af}). "
            "Total matches shown in parentheses."
        )

    # ── Section 4: Documents Per Year ──
    if len(df_group):
        _yearly = df_group.groupby("year").size().reset_index(name="count").sort_values("year")
        _yearly["year"] = _yearly["year"].astype(int).astype(str)

        st.markdown("#### Reporting Volume Over Time")
        fig = px.bar(
            _yearly,
            x="year",
            y="count",
            title="Documents Per Year",
            color_discrete_sequence=[CATEGORICAL_PALETTE[0]],
            labels={"count": "Documents", "year": "Year"},
        )
        st.plotly_chart(fig, width="stretch", key=f"group_yearly_{group_name}")

    # ── Section 5: Doc Type Breakdown ──
    if len(df_group):
        _dtype = (
            df_group.groupby("doc_type")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )

        st.markdown("#### Document Type Breakdown")
        fig = px.bar(
            _dtype,
            x="count",
            y="doc_type",
            orientation="h",
            color="doc_type",
            color_discrete_map=DOC_TYPE_COLORS,
            labels={"count": "Documents", "doc_type": "Document Type"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch", key=f"group_doctype_{group_name}")

    # ── Section 6: Member States Parties Table ──
    st.markdown("#### Member States Parties")
    _current_year = datetime.now().year
    _country_stats = (
        df_group.groupby("country")
        .agg(
            documents=("year", "size"),
            last_year=("year", "max"),
        )
        .reset_index()
    )
    _country_stats["years_since"] = _current_year - _country_stats["last_year"]

    # Add rights-based % per country from _mt if available
    if len(_mt):
        _mt_by_country = (
            _mt.groupby("country")
            .agg(rights=("rights", "sum"), medical=("medical", "sum"))
            .reset_index()
        )
        _mt_by_country["total"] = _mt_by_country["rights"] + _mt_by_country["medical"]
        _mt_by_country["rights_pct"] = round(
            _mt_by_country["rights"] / _mt_by_country["total"].replace(0, 1) * 100, 1
        )
        _country_stats = _country_stats.merge(
            _mt_by_country[["country", "rights_pct"]], on="country", how="left"
        )
    else:
        _country_stats["rights_pct"] = None

    _country_stats = _country_stats.sort_values("documents", ascending=False)

    # Rename for display
    _display = _country_stats.rename(
        columns={
            "country": "State Party",
            "documents": "Documents",
            "last_year": "Last Submission Year",
            "years_since": "Years Since Last Submission",
            "rights_pct": "Rights-Based %",
        }
    )

    st.caption(
        f"{group_name} member States Parties \u2014 reporting activity overview. "
        "Use alongside country profiles for full context."
    )

    render_accessible_table(
        _display,
        caption=(f"CRPD reporting summary for {group_name} States Parties (n={len(_display)})"),
        page_size=10,
        page_key=f"grp_members_page2_{group_name}",
    )

    # ── Section 7: Not-Yet-Represented States Parties (org mode only) ──
    if org_iso_codes is not None:
        _reported_isos = set(df_group["iso3"].dropna().unique())
        _all_org_isos = set(org_iso_codes)
        _missing_isos = _all_org_isos - _reported_isos

        if _missing_isos:
            _missing_names = []
            for iso in sorted(_missing_isos):
                try:
                    c = pycountry.countries.get(alpha_3=iso)
                    _missing_names.append(c.name if c else iso)
                except Exception:
                    _missing_names.append(iso)

            with st.expander(
                f"States Parties not yet represented in this dataset ({len(_missing_names)})"
            ):
                st.caption(
                    "Absence may reflect recent accession, reporting cycle timing, "
                    "or data availability at the time of collection. "
                    "This list should not be interpreted as a statement of non-compliance. "
                    "For official treaty body status, consult the UN Treaty Body Database."
                )
                for name in sorted(_missing_names):
                    st.markdown(f"- {name}")


def _render_group_profile(
    df_group, group_name, group_type, df_all, article_presets, org_iso_codes=None
):
    """Render an aggregated CRPD reporting profile for a group of States Parties.

    Parameters
    ----------
    df_group : DataFrame — filtered to the group's countries
    group_name : str — "Africa" or "ASEAN" etc.
    group_type : str — "Region" or "Organization"
    df_all : DataFrame — full dataset (for benchmarking)
    article_presets : dict — article keyword dictionaries
    org_iso_codes : list[str] | None — ISO3 codes for org members (for not-yet-represented)
    """
    if df_group.empty:
        st.info(f"No documents found for {group_name} with current filters.")
        return

    _safe_key = re.sub(r"[^a-zA-Z0-9]", "_", group_name)

    # ── E1: Header ──
    _suffix = "Member States" if group_type == "Organization" else ""
    st.markdown(f"### CRPD Reporting: {group_name} {_suffix}".strip())

    # ── E2: Metric pills ──
    _n_states = df_group["country"].nunique()
    _n_docs = len(df_group)
    _n_dtypes = df_group["doc_type"].nunique()
    if "year" in df_group.columns and len(df_group):
        _yr_min = int(df_group["year"].min())
        _yr_max = int(df_group["year"].max())
        _years_range = f"{_yr_min}–{_yr_max}" if _yr_min != _yr_max else str(_yr_min)
    else:
        _years_range = "—"

    _mt = model_shift_table(df_group)
    _rights_val = "—"
    _unweighted_avg = "—"
    if len(_mt) and _mt[["medical", "rights"]].sum().sum() > 0:
        _rights_pct = _mt["rights"].sum() / (_mt["medical"].sum() + _mt["rights"].sum()) * 100
        _rights_val = f"{_rights_pct:.0f}%"

        # Unweighted: average of per-country rights share
        _per_country = (
            _mt.groupby("country")[["medical", "rights"]]
            .sum()
            .assign(
                total=lambda x: x["medical"] + x["rights"],
                pct=lambda x: x["rights"] / (x["medical"] + x["rights"]) * 100,
            )
        )
        _per_country = _per_country[_per_country["total"] > 0]
        if len(_per_country):
            _unweighted_avg = f"{_per_country['pct'].mean():.0f}%"

    _metrics = [
        ("States Parties", f"{_n_states:,}"),
        ("Documents", f"{_n_docs:,}"),
        ("Document Types", str(_n_dtypes)),
        ("Year Range", _years_range),
        ("Rights-Based %", _rights_val),
    ]
    _pills = "".join(
        f"<span style='display:inline-flex;align-items:baseline;gap:5px;"
        f"padding:6px 16px;border-radius:8px;background:#ffffff;"
        f"box-shadow:0 1px 4px rgba(0,0,0,0.06);"
        f"font-family:Inter,Arial,sans-serif;font-size:14px;'>"
        f"<span style='color:#5a6377;font-weight:500;'>{lbl}</span>"
        f"<span style='color:#191C1F;font-weight:700;'>{val}</span>"
        f"</span>"
        for lbl, val in _metrics
    )
    st.markdown(
        f"<div style='display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px;'>{_pills}</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        f"Weighted by document count. Unweighted State Party average: "
        f"{_unweighted_avg}. High-volume States Parties have greater influence."
    )

    # ── E3: Doc Type Breakdown ──
    _dtype_counts = (
        df_group.groupby("doc_type").size().reset_index(name="count").sort_values("count")
    )
    if not _dtype_counts.empty:
        fig = px.bar(
            _dtype_counts,
            x="count",
            y="doc_type",
            orientation="h",
            title=f"Document Types — {group_name}",
            color="doc_type",
            color_discrete_map=DOC_TYPE_COLORS,
            labels={"count": "Documents", "doc_type": "Document Type"},
        )
        fig.update_layout(
            showlegend=False,
        )
        st.plotly_chart(fig, key=f"grp_doctype_{_safe_key}")
        st.caption(
            f"{_n_dtypes} document types across {_n_states} States Parties "
            f"({_n_docs:,} documents total)"
        )

    # ── E4: Article 1 toggle ──
    _exclude_art1 = st.toggle(
        "**Exclude Article 1 — Purpose (highest frequency article)**",
        value=False,
        key=f"exclude_art1_{_safe_key}",
    )
    st.markdown(
        "<style>[data-testid='stToggle'] label p "
        "{color: #000000 !important; font-weight: 700 !important;}</style>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    # ── E5: Top Articles by Doc Type ──
    with col1:
        _art_by_dtype = article_frequency(df_group, article_presets, groupby="doc_type")
        if _exclude_art1:
            _art_by_dtype = _art_by_dtype[_art_by_dtype["article"] != "Article 1 — Purpose"]
        if not _art_by_dtype.empty:
            _top_articles = (
                _art_by_dtype.groupby("article")["count"].sum().nlargest(10).index.tolist()
            )
            _top_art_df = _art_by_dtype[_art_by_dtype["article"].isin(_top_articles)]
            fig = px.bar(
                _top_art_df,
                x="count",
                y="article",
                color="group",
                orientation="h",
                title=f"Top CRPD Articles — {group_name}",
                color_discrete_map=DOC_TYPE_COLORS,
                labels={
                    "count": "Mentions",
                    "article": "Article",
                    "group": "Document Type",
                },
            )
            fig.update_layout(
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.2,
                    xanchor="center",
                    x=0.5,
                ),
            )
            st.plotly_chart(fig, key=f"grp_articles_{_safe_key}")
            st.caption(
                f"Top 10 of {len(_art_by_dtype['article'].unique())} articles "
                f"by keyword frequency across {_n_states} States Parties"
            )
        else:
            st.info("No CRPD article references found for this group.")

    # ── E6: Article Coverage Over Time ──
    with col2:
        _art_by_yr = article_frequency(df_group, article_presets, groupby="year")
        if _exclude_art1:
            _art_by_yr = _art_by_yr[_art_by_yr["article"] != "Article 1 — Purpose"]
        if not _art_by_yr.empty:
            _art_by_yr["group"] = _art_by_yr["group"].astype(int).astype(str)
            _n_years = _art_by_yr["group"].nunique()

            if _n_years <= 1:
                _single_yr = _art_by_yr["group"].iloc[0]
                _top_single = (
                    _art_by_yr.groupby("article")["count"].sum().nlargest(15).reset_index()
                )
                fig = px.bar(
                    _top_single,
                    x="count",
                    y="article",
                    orientation="h",
                    title=f"Article Mentions ({_single_yr}) — {group_name}",
                    color_discrete_sequence=[SEQUENTIAL_BLUES[4]],
                    labels={"count": "Mentions", "article": "Article"},
                )
                st.plotly_chart(fig, key=f"grp_heatmap_{_safe_key}")
                st.caption(f"Article keyword counts for {_single_yr} — {_n_docs} document(s)")
            else:
                pivot = _art_by_yr.pivot(index="article", columns="group", values="count").fillna(0)
                _top_art_names = pivot.sum(axis=1).nlargest(15).index.tolist()
                pivot = pivot.loc[_top_art_names]
                fig = px.imshow(
                    pivot,
                    title=f"Article Coverage Over Time — {group_name}",
                    color_continuous_scale=[
                        SEQUENTIAL_BLUES[0],
                        SEQUENTIAL_BLUES[2],
                        SEQUENTIAL_BLUES[5],
                    ],
                    labels={"x": "Year", "y": "Article", "color": "Mentions"},
                    aspect="auto",
                )
                st.plotly_chart(fig, key=f"grp_heatmap_{_safe_key}")
                st.caption(
                    f"Keyword mention intensity across {_n_years} reporting "
                    f"year(s) — {_n_docs} documents"
                )
        else:
            st.info("No article coverage data available.")

    # ── E8: Document Length + E9: Model Language Evolution ──
    col3, col4 = st.columns(2)

    with col3:
        if "word_count" in df_group.columns and df_group["word_count"].notna().any():
            _len_df = df_group.dropna(subset=["year", "word_count"]).copy()
            _len_df["year"] = _len_df["year"].astype(int).astype(str)
            fig = px.bar(
                _len_df,
                x="year",
                y="word_count",
                color="doc_type",
                title=f"Document Length — {group_name}",
                color_discrete_map=DOC_TYPE_COLORS,
                labels={
                    "word_count": "Word Count",
                    "year": "Year",
                    "doc_type": "Document Type",
                },
                barmode="group",
            )
            fig.update_layout(
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.25,
                    xanchor="center",
                    x=0.5,
                ),
            )
            _group_avg = df_group["word_count"].mean()
            if _group_avg:
                fig.add_hline(
                    y=_group_avg,
                    line_dash="dash",
                    line_color=CATEGORICAL_PALETTE[6],
                    annotation_text=(f"Group avg: {int(_group_avg):,} (across {_n_docs:,} docs)"),
                    annotation_position="top right",
                )
            st.plotly_chart(fig, key=f"grp_doclen_{_safe_key}")
            st.caption(f"Document word counts with {group_name} average reference line")

    with col4:
        if "year" in df_group.columns and len(df_group):
            _mt_group = model_shift_table(df_group)
            if len(_mt_group):
                _by_year = (
                    _mt_group.groupby("year")[["medical", "rights"]]
                    .sum()
                    .reset_index()
                    .sort_values("year")
                )
                _by_year["total"] = _by_year["medical"] + _by_year["rights"]
                _by_year["Rights-Based %"] = (_by_year["rights"] / _by_year["total"] * 100).round(1)
                _by_year["Medical %"] = (_by_year["medical"] / _by_year["total"] * 100).round(1)
                _by_year["year"] = _by_year["year"].astype(int).astype(str)

                _model_color_map = {
                    "Rights-Based %": MODEL_COLORS["Rights-Based"],
                    "Medical %": MODEL_COLORS["Medical Model"],
                }

                _model_long = _by_year.melt(
                    id_vars=["year"],
                    value_vars=["Rights-Based %", "Medical %"],
                    var_name="Model",
                    value_name="Share (%)",
                )

                if len(_by_year) < 6:
                    fig = px.bar(
                        _model_long,
                        x="year",
                        y="Share (%)",
                        color="Model",
                        title=f"Model Language — {group_name}",
                        color_discrete_map=_model_color_map,
                        labels={"year": "Year"},
                        barmode="group",
                    )
                else:
                    fig = px.area(
                        _model_long,
                        x="year",
                        y="Share (%)",
                        color="Model",
                        title=f"Model Language Evolution — {group_name}",
                        color_discrete_map=_model_color_map,
                        labels={"year": "Year"},
                    )

                fig.update_layout(
                    yaxis_range=[0, 100],
                    legend_title_text="Language Model",
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.25,
                        xanchor="center",
                        x=0.5,
                    ),
                )
                st.plotly_chart(fig, key=f"grp_model_{_safe_key}")
                st.caption("Percentage of medical vs. rights-based keywords per year")
            else:
                st.info("No model language data available for this group.")
        else:
            st.info("Year data not available for model language analysis.")

    # ── Member States Parties table ──
    st.markdown("#### Member States Parties")
    _current_year = datetime.now().year
    _country_summary_rows = []
    for _c, _cdf in df_group.groupby("country"):
        _c_mt = model_shift_table(_cdf)
        _c_rights = "—"
        if len(_c_mt) and _c_mt[["medical", "rights"]].sum().sum() > 0:
            _c_rights = f"{_c_mt['rights'].sum() / (_c_mt['medical'].sum() + _c_mt['rights'].sum()) * 100:.0f}%"
        _last_yr = int(_cdf["year"].max()) if "year" in _cdf.columns else None
        _yrs_since = f"{_current_year - _last_yr}" if _last_yr else "—"
        _country_summary_rows.append(
            {
                "State Party": _c,
                "Documents": len(_cdf),
                "Last Submission": _last_yr if _last_yr else "—",
                "Years Since Last": _yrs_since,
                "Rights-Based %": _c_rights,
            }
        )
    _country_summary = (
        pd.DataFrame(_country_summary_rows)
        .sort_values("Documents", ascending=False)
        .reset_index(drop=True)
    )
    render_accessible_table(
        _country_summary,
        caption=f"{group_name} member States Parties — reporting activity overview.",
        sortable=True,
        sort_key=f"grp_members_{_safe_key}",
        page_size=10,
        page_key=f"grp_members_page_{_safe_key}",
    )

    # ── Not-yet-represented expander (org mode only) ──
    if org_iso_codes is not None:
        _represented_isos = set(df_group["iso3"].dropna().unique())
        _missing_isos = [iso for iso in org_iso_codes if iso not in _represented_isos]
        if _missing_isos:
            _missing_names = []
            for _iso in _missing_isos:
                _pyc = pycountry.countries.get(alpha_3=_iso)
                _missing_names.append(_pyc.name if _pyc else _iso)
            with st.expander(
                f"States Parties not yet represented in dataset ({len(_missing_names)})"
            ):
                st.caption(
                    "Absence may reflect recent accession, reporting cycle timing, "
                    "or data availability. Consult the UN Treaty Body Database for "
                    "official status."
                )
                for _name in sorted(_missing_names):
                    st.markdown(f"- {_name}")


def render_countries(df, ARTICLE_PRESETS, default_tab: int = 0):
    """Countries page — Map, Trends, Country Profiles, Compare Countries."""
    # Auto-select the tab driven by the navbar sub-page link

    # Map View
    if default_tab == 0:
        # ── Build country_stats with all metrics ──
        country_stats = (
            df.groupby(["country", "region"])
            .agg(
                documents=("country", "size"),
                avg_word_count=("word_count", "mean"),
                doc_types=("doc_type", "nunique"),
            )
            .reset_index()
        )
        country_stats["avg_word_count"] = (
            country_stats["avg_word_count"].fillna(0).round(0).astype(int)
        )

        # Rights-Based % per country (from model_shift_table)
        _mt_map = model_shift_table(df)
        _mt_country = (
            _mt_map.groupby("country")
            .agg(medical=("medical", "sum"), rights=("rights", "sum"))
            .reset_index()
        )
        _mt_country["_total"] = _mt_country["medical"] + _mt_country["rights"]
        _mt_country["rights_pct"] = (
            _mt_country["rights"] / _mt_country["_total"].replace(0, 1) * 100
        ).round(1)
        country_stats = country_stats.merge(
            _mt_country[["country", "rights_pct"]], on="country", how="left"
        )
        country_stats["rights_pct"] = country_stats["rights_pct"].fillna(0)

        # Article coverage breadth per country
        _art_country = article_frequency(df, ARTICLE_PRESETS, groupby="country")
        if len(_art_country):
            _art_breadth = (
                _art_country.groupby("group")["article"]
                .nunique()
                .reset_index(name="article_breadth")
                .rename(columns={"group": "country"})
            )
            country_stats = country_stats.merge(_art_breadth, on="country", how="left")
        else:
            country_stats["article_breadth"] = 0
        country_stats["article_breadth"] = country_stats["article_breadth"].fillna(0).astype(int)

        # TF-IDF top terms per country (cached)
        _country_terms = _compute_country_terms(
            df[["country", "clean_text"]].to_json(orient="split")
        )
        country_stats["top_terms"] = country_stats["country"].map(_country_terms).fillna("")

        # Reporting gap: years since last submission (always relative to calendar year)
        _current_year = datetime.now().year
        _last_year = df.groupby("country")["year"].max().reset_index(name="last_year")
        country_stats = country_stats.merge(_last_year, on="country", how="left")
        country_stats["reporting_gap"] = (
            _current_year - country_stats["last_year"].fillna(_current_year)
        ).astype(int)

        # ── ISO3 alpha code from df (for Folium GeoJSON join) ──
        _iso3_map = df.dropna(subset=["iso3"]).drop_duplicates(subset=["country"])[
            ["country", "iso3"]
        ]
        country_stats = country_stats.merge(_iso3_map, on="country", how="left")

        # ── ISO numeric lookup with fallback dict ──
        _ISO_FALLBACK = {
            "Bolivia (Plurinational State of)": 68,
            "Iran (Islamic Republic of)": 364,
            "Venezuela (Bolivarian Republic of)": 862,
            "Micronesia (Federated States Of)": 583,
            "China (Hong Kong)": 344,
            "China (Macau)": 446,
            "State of Palestine": 275,
        }

        def get_iso_numeric(name):
            if name in _ISO_FALLBACK:
                return _ISO_FALLBACK[name]
            try:
                res = pycountry.countries.search_fuzzy(name)
                if res:
                    return int(res[0].numeric)
            except Exception:
                pass
            return None

        country_stats["id"] = country_stats["country"].apply(get_iso_numeric)
        _total_entities = len(country_stats)
        country_stats = country_stats.dropna(subset=["id"])
        _n_dropped = _total_entities - len(country_stats)
        country_stats["id"] = country_stats["id"].astype(int)

        if country_stats.empty:
            st.info("No valid geographical data found to render on the map.")
        else:
            # ── Country search widget ──
            _country_list = [
                "All States Parties",
                *sorted(country_stats["country"].unique()),
            ]
            _selected_search = st.selectbox(
                "Find a State Party:",
                options=_country_list,
                index=0,
                key="map_country_search",
                label_visibility="visible",
            )

            # ── Metric selector stripe (st.pills) ──
            _metric_options = {
                ":material/description: Document Count": "documents",
                ":material/balance: Rights-Based %": "rights_pct",
                ":material/menu_book: Article Breadth": "article_breadth",
                ":material/schedule: Reporting Cycle": "reporting_gap",
            }
            # Style the pills to match dashboard design
            st.markdown(
                """
                <style>
                /* Map metric pills — styled to match dashboard theme */
                div[data-testid="stPills"] > div {
                    gap: 6px !important;
                }
                div[data-testid="stPills"] button {
                    font-family: 'Inter', sans-serif !important;
                    font-weight: 600 !important;
                    font-size: 0.85rem !important;
                    padding: 10px 16px !important;
                    border-radius: 10px !important;
                    border: 1.5px solid #e2e6ed !important;
                    background: #ffffff !important;
                    color: #191C1F !important;
                    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
                    transition: all 0.15s ease !important;
                    min-height: 44px !important;
                }
                div[data-testid="stPills"] button:hover {
                    border-color: #003F87 !important;
                    box-shadow: 0 2px 10px rgba(0,63,135,0.13) !important;
                    background: #f7f9fd !important;
                }
                div[data-testid="stPills"] button[aria-checked="true"] {
                    background: linear-gradient(135deg, #003F87, #0056B3) !important;
                    border-color: #003F87 !important;
                    color: #ffffff !important;
                    box-shadow: 0 4px 16px rgba(0,63,135,0.25) !important;
                }
                div[data-testid="stPills"] button:focus-visible {
                    outline: 2px solid #005bbb !important;
                    outline-offset: 2px !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            _pill_keys = list(_metric_options.keys())
            _selected_pill = st.pills(
                "Map metric",
                _pill_keys,
                default=_pill_keys[0],
                key="map_metric_pills",
                label_visibility="collapsed",
            )
            _metric_col = _metric_options.get(_selected_pill, "documents")
            # Display name for legend title (strip the :material/...: prefix)
            _metric_display = (
                _selected_pill.split(": ", 1)[1] if _selected_pill else "Document Count"
            )

            # ── Choropleth map (Folium) ──
            _map_titles = {
                "documents": "CRPD Documents by State Party",
                "rights_pct": "Rights-Based Keyword Share by State Party (%)",
                "article_breadth": "CRPD Article Coverage Breadth by State Party",
                "reporting_gap": "Years Since Last CRPD Submission by State Party",
            }
            _metric_subtitles = {
                "documents": "Based on CRPD reporting documents matching current filters",
                "rights_pct": "Based on keyword frequency analysis of CRPD reporting documents",
                "article_breadth": "Based on keyword frequency analysis of CRPD reporting documents",
                "reporting_gap": "Years since last document submission to the CRPD Committee",
            }
            _subtitle = _metric_subtitles.get(_metric_col, "Based on CRPD reporting documents")
            _active_types = df["doc_type"].unique()
            if len(_active_types) < 5:
                _subtitle += f" | Filtered to: {', '.join(sorted(_active_types))}"

            st.markdown(
                f"<h4 style='text-align:center;margin-bottom:0;'>"
                f"{_map_titles.get(_metric_col, 'CRPD Map')}</h4>"
                f"<p style='text-align:center;color:#5a6377;font-size:12px;"
                f"margin-top:4px;'>{_subtitle}</p>",
                unsafe_allow_html=True,
            )

            # Build ISO3 lookup dict for style_function
            _stats_by_iso = {}
            for _, _row in country_stats.iterrows():
                _iso = _row.get("iso3")
                if _iso and pd.notna(_iso):
                    _stats_by_iso[_iso] = _row.to_dict()

            # Color scale
            _metric_captions = {
                "documents": "Documents per State Party",
                "rights_pct": "Rights-Based Keyword Share (%)",
                "article_breadth": "Distinct CRPD Articles Detected",
                "reporting_gap": "Years Since Last Submission",
            }
            _valid_vals = country_stats[_metric_col].dropna()
            if len(_valid_vals) > 0:
                _vmin = float(_valid_vals.min())
                _vmax = float(_valid_vals.max())
                if _metric_col == "reporting_gap":
                    _map_colors = [
                        _REPORTING_GAP_COLORS[0],
                        _REPORTING_GAP_COLORS[1],
                        _REPORTING_GAP_COLORS[2],
                    ]
                    _colormap = cm.LinearColormap(
                        colors=_map_colors,
                        vmin=0,
                        vmax=max(_vmax, 7),
                        caption=_metric_captions[_metric_col],
                    )
                else:
                    _map_colors = [
                        SEQUENTIAL_BLUES[0],
                        SEQUENTIAL_BLUES[2],
                        SEQUENTIAL_BLUES[4],
                        SEQUENTIAL_BLUES[5],
                    ]
                    _colormap = cm.LinearColormap(
                        colors=_map_colors,
                        vmin=_vmin,
                        vmax=_vmax,
                        caption=_metric_captions[_metric_col],
                    )
            else:
                _colormap = None

            # Determine map center/zoom based on active regions
            unique_regions = df["region"].dropna().unique()
            _REGION_VIEW = {
                "Africa": {"location": [0, 20], "zoom": 3},
                "Americas": {"location": [10, -80], "zoom": 3},
                "Asia": {"location": [30, 90], "zoom": 3},
                "Europe": {"location": [50, 15], "zoom": 4},
                "Oceania": {"location": [-10, 150], "zoom": 3},
            }
            if len(unique_regions) == 1 and unique_regions[0] in _REGION_VIEW:
                _view = _REGION_VIEW[unique_regions[0]]
                _map_location = _view["location"]
                _map_zoom = _view["zoom"]
            else:
                _map_location = [10, 10]
                _map_zoom = 2

            _m = folium.Map(
                location=_map_location,
                zoom_start=_map_zoom,
                min_zoom=2,
                max_zoom=8,
                tiles="cartodbpositron",
                max_bounds=True,
            )

            # Deep copy GeoJSON so we don't mutate the cached original
            _geo = copy.deepcopy(_load_geojson())

            # Merge CRPD stats into GeoJSON properties for tooltips
            for _feat in _geo["features"]:
                _iso = _feat.get("properties", {}).get("ISO_A3", "")
                _st = _stats_by_iso.get(_iso, {})
                _feat["properties"]["crpd_country"] = _st.get(
                    "country", _feat["properties"].get("ADMIN", "Unknown")
                )
                _feat["properties"]["crpd_documents"] = (
                    str(int(_st["documents"])) if _st.get("documents") is not None else "\u2014"
                )
                _rpct = _st.get("rights_pct")
                _feat["properties"]["crpd_rights_pct"] = (
                    f"{_rpct:.1f}%" if _rpct is not None else "\u2014"
                )
                _feat["properties"]["crpd_articles"] = (
                    str(int(_st["article_breadth"]))
                    if _st.get("article_breadth") is not None
                    else "\u2014"
                )
                _feat["properties"]["crpd_gap"] = (
                    str(int(_st["reporting_gap"]))
                    if _st.get("reporting_gap") is not None
                    else "\u2014"
                )
                _feat["properties"]["crpd_last_year"] = (
                    str(int(_st["last_year"]))
                    if _st.get("last_year") is not None and pd.notna(_st.get("last_year"))
                    else "\u2014"
                )

            def _style_fn(feature):
                _iso = feature.get("properties", {}).get("ISO_A3", "")
                _st = _stats_by_iso.get(_iso, {})
                _val = _st.get(_metric_col)
                if _val is not None and _colormap is not None:
                    _fill = _colormap(_val)
                else:
                    _fill = MAP_NO_DATA
                return {
                    "fillColor": _fill,
                    "color": "white",
                    "weight": 0.5,
                    "fillOpacity": 0.65,
                }

            folium.GeoJson(
                _geo,
                style_function=_style_fn,
                tooltip=folium.GeoJsonTooltip(
                    fields=[
                        "crpd_country",
                        "crpd_documents",
                        "crpd_rights_pct",
                        "crpd_articles",
                        "crpd_gap",
                        "crpd_last_year",
                    ],
                    aliases=[
                        "State Party:",
                        "Documents:",
                        "Rights-Based Keywords:",
                        "Distinct CRPD Articles Detected:",
                        "Years Since Last Submission:",
                        "Last Submission Year:",
                    ],
                    sticky=True,
                    style="font-family:Inter,sans-serif;font-size:13px;line-height:1.6;",
                ),
                highlight_function=lambda x: {
                    "weight": 2,
                    "color": "#003F87",
                    "fillOpacity": 0.8,
                },
            ).add_to(_m)

            if _colormap:
                _colormap.add_to(_m)

            # Attribution overlay for screenshot context
            stats_obj = get_dataset_stats()
            _m.get_root().html.add_child(
                folium.Element(
                    f"<div style='position:absolute;bottom:25px;left:10px;z-index:999;"
                    f"font-size:10px;color:#666;font-family:Inter,sans-serif;"
                    f"background:rgba(255,255,255,0.8);padding:2px 6px;border-radius:3px;'>"
                    f"CRPD Dashboard | Data through {stats_obj['year_max']}"
                    f" | Keyword frequency analysis</div>"
                )
            )

            st_folium(
                _m,
                height=500,
                use_container_width=True,
                key=f"main_map_{_metric_col}",
                returned_objects=[],
            )

            # Caption with transparency about dropped entities
            stats = get_dataset_stats()
            _drop_note = f" ({_n_dropped} entities could not be mapped)" if _n_dropped else ""
            st.caption(
                f"Showing {len(country_stats)} of {_total_entities} reporting entities "
                f"across {len(country_stats['region'].unique())} regions{_drop_note}. "
                f"Data current through {stats['year_max']}."
            )
            st.caption(
                "Small island States may not be visible at this scale. "
                "Use the data table below or the Country Profiles tab "
                "for detailed country-level information."
            )
            st.caption(
                "This map uses Web Mercator projection. Land areas near the "
                "equator appear smaller than their true relative size."
            )

            # ── Companion data table — non-hover alternative for accessibility ──
            # Pre-fill companion table search when a country is selected
            if _selected_search != "All States Parties":
                st.session_state["map_companion_search"] = _selected_search
            with st.expander("View data as table", expanded=True):
                _table_cols = [
                    "country",
                    "region",
                    "documents",
                    "rights_pct",
                    "article_breadth",
                    "reporting_gap",
                    "doc_types",
                ]
                _table_df = country_stats[
                    [c for c in _table_cols if c in country_stats.columns]
                ].copy()
                _table_df = _table_df.rename(
                    columns={
                        "country": "State Party",
                        "region": "Region",
                        "documents": "Documents",
                        "rights_pct": "Rights-Based %",
                        "article_breadth": "Articles Referenced",
                        "reporting_gap": "Years Since Last Report",
                        "doc_types": "Document Types",
                    }
                )
                render_accessible_table(
                    _table_df,
                    caption=(
                        f"All {len(_table_df)} States Parties with CRPD"
                        " documents — sortable and searchable"
                    ),
                    page_size=15,
                    page_key="map_companion_page",
                    sortable=True,
                    sort_key="map_companion_sort",
                    searchable=True,
                    search_key="map_companion_search",
                )
                # CSV download removed — no-data-download policy active

            # ── Document type stacked bar chart (linked) ──
            doc_type_df = (
                df.groupby(["country", "region", "doc_type"]).size().reset_index(name="count")
            )
            _n_countries = len(df["country"].unique())
            _top_n = min(20, _n_countries)
            _top_countries = df.groupby("country").size().nlargest(_top_n).index.tolist()
            doc_type_top = doc_type_df[doc_type_df["country"].isin(_top_countries)]

            stacked_chart = (
                alt.Chart(doc_type_top)
                .mark_bar()
                .encode(
                    x=alt.X("count:Q", title="Documents", stack="zero"),
                    y=alt.Y("country:N", sort="-x", title=""),
                    color=alt.Color(
                        "doc_type:N",
                        title="Document Type",
                        legend=alt.Legend(titleColor="#000000"),
                        scale=alt.Scale(
                            domain=list(DOC_TYPE_COLORS.keys()),
                            range=list(DOC_TYPE_COLORS.values()),
                        ),
                    ),
                    tooltip=[
                        alt.Tooltip("country:N", title="State Party"),
                        alt.Tooltip("doc_type:N", title="Type"),
                        alt.Tooltip("count:Q", title="Count"),
                    ],
                )
                .properties(
                    width="container",
                    height=max(300, _top_n * 22),
                    title=alt.Title(
                        f"CRPD Document Composition ({_top_n} States Parties with Most Documents in Dataset)",
                        subtitle=(
                            f"Showing {_top_n} of {_n_countries} States Parties"
                            + (
                                f" | Filtered to: {', '.join(sorted(df['doc_type'].unique()))}"
                                if df["doc_type"].nunique() < 5
                                else ""
                            )
                        ),
                        anchor="middle",
                    ),
                )
            )
            st.altair_chart(stacked_chart, width="stretch")

            # ── Regional Deep Dive (collapsed to reduce scroll depth) ──
            with st.expander("Regional Deep Dive", expanded=False):
                # ── Regional Grouped Bar Chart ──
                _bar_regions = sorted(country_stats["region"].dropna().unique().tolist())
                if len(_bar_regions) >= 2:
                    _show_doc_len = st.toggle(
                        "INCLUDE AVG DOC LENGTH",
                        value=True,
                        help="Avg Doc Length (thousands of words) dwarfs other dimensions. Toggle off to reveal smaller metrics.",
                    )
                    _bar_dims = [
                        "Avg Documents",
                        "Rights-Based Keyword %",
                        "Articles Referenced",
                    ]
                    if _show_doc_len:
                        _bar_dims.append("Avg Doc Length")
                    _bar_rows = []
                    for reg in _bar_regions:
                        _rsub = country_stats[country_stats["region"] == reg]
                        _bar_rows.append(
                            {
                                "Region": reg,
                                "Avg Documents": round(float(_rsub["documents"].mean()), 1),
                                "Rights-Based Keyword %": round(
                                    float(_rsub["rights_pct"].mean()), 1
                                ),
                                "Articles Referenced": round(
                                    float(_rsub["article_breadth"].mean()), 1
                                ),
                                "Avg Doc Length": round(float(_rsub["avg_word_count"].mean()), 0),
                            }
                        )
                    _bar_df = pd.DataFrame(_bar_rows)
                    _bar_long = _bar_df.melt(
                        id_vars="Region",
                        value_vars=_bar_dims,
                        var_name="Dimension",
                        value_name="Value",
                    )
                    _bar_fig = px.bar(
                        _bar_long,
                        x="Dimension",
                        y="Value",
                        color="Region",
                        barmode="group",
                        color_discrete_map=REGION_COLORS,
                        title="Regional Reporting Profiles",
                    )
                    _bar_fig.update_layout(
                        height=500,
                        margin=dict(l=60, r=60, t=60, b=60),
                        legend=dict(title=dict(text="Region")),
                    )
                    st.plotly_chart(_bar_fig, width="stretch")
                    st.caption(
                        "Actual values per dimension. "
                        "Regions with fewer States Parties may show higher averages."
                    )

                # ── Scatter Plot: Rights % vs Article Breadth ──
                _scatter_fig = px.scatter(
                    country_stats,
                    x="rights_pct",
                    y="article_breadth",
                    color="region",
                    hover_name="country",
                    hover_data={
                        "documents": True,
                        "rights_pct": ":.1f",
                        "article_breadth": True,
                        "region": False,
                    },
                    color_discrete_map=REGION_COLORS,
                    labels={
                        "rights_pct": "Rights-Based Keyword Share (%)",
                        "article_breadth": "CRPD Articles Referenced",
                        "documents": "Documents",
                    },
                    size="documents",
                    size_max=18,
                    opacity=0.5,
                )
                _scatter_fig.update_layout(
                    title=dict(
                        text="Rights-Based Keyword Share vs. Article Coverage by State Party",
                        x=0.5,
                        xref="container",
                    ),
                    legend=dict(title=dict(text="Region")),
                    height=500,
                )
                st.plotly_chart(_scatter_fig, width="stretch")
                st.caption(
                    "Each bubble represents a State Party. Size reflects document count. "
                    "States Parties in the upper-right quadrant show both high rights-based "
                    "keyword share and broad article coverage."
                )

                # ── Regional Small Multiples (5 mini-maps, Folium) ──
                _sm_regions = sorted(country_stats["region"].dropna().unique().tolist())
                _SM_VIEW = {
                    "Africa": {"location": [2, 20], "zoom": 3},
                    "Americas": {"location": [0, -75], "zoom": 2},
                    "Asia": {"location": [28, 80], "zoom": 3},
                    "Europe": {"location": [54, 15], "zoom": 3},
                    "Oceania": {"location": [-18, 155], "zoom": 3},
                }
                if len(_sm_regions) >= 2:
                    _sm_metric = _metric_col
                    _sm_metric_label = _metric_display
                    st.markdown(
                        f"<h4 style='text-align:center; margin-top:1.5rem;'>"
                        f"Regional Detail: {_sm_metric_label} by State Party</h4>",
                        unsafe_allow_html=True,
                    )

                    # Compute GLOBAL scale from full country_stats
                    _sm_vals = country_stats[_sm_metric]
                    _global_vmin = float(_sm_vals.min())
                    _global_vmax = float(_sm_vals.max())

                    # Build shared colormap once
                    if _sm_metric == "reporting_gap":
                        _sm_colormap = cm.LinearColormap(
                            colors=[
                                _REPORTING_GAP_COLORS[0],
                                _REPORTING_GAP_COLORS[1],
                                _REPORTING_GAP_COLORS[2],
                            ],
                            vmin=0,
                            vmax=max(_global_vmax, 7),
                        )
                    else:
                        _global_q33 = float(_sm_vals.quantile(0.33))
                        _global_q66 = float(_sm_vals.quantile(0.66))
                        _sm_colormap = cm.LinearColormap(
                            colors=[
                                SEQUENTIAL_BLUES[0],
                                SEQUENTIAL_BLUES[2],
                                SEQUENTIAL_BLUES[4],
                                SEQUENTIAL_BLUES[5],
                            ],
                            vmin=_global_vmin,
                            vmax=_global_vmax,
                        )

                    # Build regional ISO lookup
                    _sm_stats_by_iso = {}
                    for _, _row in country_stats.iterrows():
                        _iso = _row.get("iso3")
                        if _iso and pd.notna(_iso):
                            _sm_stats_by_iso[_iso] = _row.to_dict()

                    # Row 1: first 3 regions; Row 2: remaining, centered
                    _row1_regs = _sm_regions[:3]
                    _row2_regs = _sm_regions[3:]
                    _row1_cols = st.columns(len(_row1_regs))
                    _row2_cols = st.columns([1, *([2] * len(_row2_regs)), 1]) if _row2_regs else []
                    _layout = [(_row1_regs, _row1_cols, False)]
                    if _row2_regs:
                        _layout.append((_row2_regs, _row2_cols, True))

                    # Load GeoJSON once for all regional maps
                    _sm_geo_base = _load_geojson()

                    for _regs, _cols, _padded in _layout:
                        for i, reg in enumerate(_regs):
                            _reg_data = country_stats[country_stats["region"] == reg]
                            _reg_isos = set(_reg_data["iso3"].dropna().tolist())

                            _view = _SM_VIEW.get(reg, {"location": [0, 0], "zoom": 2})
                            _rm = folium.Map(
                                location=_view["location"],
                                zoom_start=_view["zoom"],
                                tiles="cartodbpositron",
                                dragging=False,
                                scrollWheelZoom=False,
                                zoom_control=False,
                                attributionControl=False,
                            )

                            # Deep copy GeoJSON for this region
                            _sm_geo = copy.deepcopy(_sm_geo_base)
                            for _feat in _sm_geo["features"]:
                                _iso = _feat["properties"].get("ISO_A3", "")
                                _st = _sm_stats_by_iso.get(_iso, {})
                                _feat["properties"]["crpd_country"] = _st.get(
                                    "country",
                                    _feat["properties"].get("ADMIN", "Unknown"),
                                )
                                _val = _st.get(_sm_metric)
                                _feat["properties"]["crpd_metric"] = (
                                    str(round(_val, 1)) if _val is not None else "\u2014"
                                )

                            def _sm_style_fn(feature, _cmap=_sm_colormap, _isos=_reg_isos):
                                _iso = feature["properties"].get("ISO_A3", "")
                                _st = _sm_stats_by_iso.get(_iso, {})
                                _val = _st.get(_sm_metric)
                                if _iso in _isos and _val is not None:
                                    _fill = _cmap(_val)
                                else:
                                    _fill = MAP_NO_DATA
                                return {
                                    "fillColor": _fill,
                                    "color": "white",
                                    "weight": 0.3,
                                    "fillOpacity": 0.65,
                                }

                            folium.GeoJson(
                                _sm_geo,
                                style_function=_sm_style_fn,
                                tooltip=folium.GeoJsonTooltip(
                                    fields=["crpd_country", "crpd_metric"],
                                    aliases=["State Party:", f"{_sm_metric_label}:"],
                                    sticky=True,
                                    style=("font-family:Inter,sans-serif;font-size:12px;"),
                                ),
                                highlight_function=lambda x: {
                                    "weight": 2,
                                    "color": "#003F87",
                                    "fillOpacity": 0.8,
                                },
                            ).add_to(_rm)

                            _col_idx = i + 1 if _padded else i
                            with _cols[_col_idx]:
                                st.markdown(
                                    f"<p style='text-align:center;font-size:13px;"
                                    f"font-weight:600;margin-bottom:4px;'>"
                                    f"{reg} ({len(_reg_data)} States Parties)</p>",
                                    unsafe_allow_html=True,
                                )
                                st_folium(
                                    _rm,
                                    height=220,
                                    use_container_width=True,
                                    key=f"sm_map_{reg}_{_sm_metric}",
                                    returned_objects=[],
                                )

                    # Oceania detail map (zoomable)
                    if "Oceania" in _sm_regions:
                        with st.expander("Pacific Islands Detail (zoomable)", expanded=False):
                            _oc_data = country_stats[country_stats["region"] == "Oceania"]
                            _oc_m = folium.Map(
                                location=[-5, 170],
                                zoom_start=4,
                                tiles="cartodbpositron",
                                max_bounds=True,
                            )
                            _oc_geo = copy.deepcopy(_sm_geo_base)
                            _oc_isos = set(_oc_data["iso3"].dropna().tolist())
                            for _feat in _oc_geo["features"]:
                                _iso = _feat["properties"].get("ISO_A3", "")
                                _st = _sm_stats_by_iso.get(_iso, {})
                                _feat["properties"]["crpd_country"] = _st.get(
                                    "country",
                                    _feat["properties"].get("ADMIN", "Unknown"),
                                )
                                _val = _st.get(_sm_metric)
                                _feat["properties"]["crpd_metric"] = (
                                    str(round(_val, 1)) if _val is not None else "\u2014"
                                )

                            def _oc_style_fn(feature):
                                _iso = feature["properties"].get("ISO_A3", "")
                                _st = _sm_stats_by_iso.get(_iso, {})
                                _val = _st.get(_sm_metric)
                                if _iso in _oc_isos and _val is not None:
                                    _fill = _sm_colormap(_val)
                                else:
                                    _fill = MAP_NO_DATA
                                return {
                                    "fillColor": _fill,
                                    "color": "white",
                                    "weight": 0.5,
                                    "fillOpacity": 0.65,
                                }

                            folium.GeoJson(
                                _oc_geo,
                                style_function=_oc_style_fn,
                                tooltip=folium.GeoJsonTooltip(
                                    fields=["crpd_country", "crpd_metric"],
                                    aliases=["State Party:", f"{_sm_metric_label}:"],
                                    sticky=True,
                                    style=("font-family:Inter,sans-serif;font-size:12px;"),
                                ),
                                highlight_function=lambda x: {
                                    "weight": 2,
                                    "color": "#003F87",
                                    "fillOpacity": 0.8,
                                },
                            ).add_to(_oc_m)

                            st_folium(
                                _oc_m,
                                height=400,
                                use_container_width=True,
                                key=f"oceania_detail_{_sm_metric}",
                                returned_objects=[],
                            )

                    if _sm_metric == "reporting_gap":
                        _scale_desc = (
                            "Color scale: 0\u20132 years (green) \u2192 3\u20135 years"
                            " (amber) \u2192 6+ years (red). Gray = no data in dataset."
                        )
                    else:
                        _scale_desc = (
                            f"Color scale: {_global_vmin} (lightest) \u2192"
                            f" {_global_q33:.0f} (33rd pctl) \u2192"
                            f" {_global_q66:.0f} (66th pctl) \u2192"
                            f" {_global_vmax} (darkest). Gray = no data in dataset."
                        )
                    st.caption(_scale_desc)
                    st.caption(
                        "All regional maps use the same color scale for cross-region comparison."
                    )

            # ── Never-Reported Entities ──
            _full_df = load_data("data/crpd_reports.csv")
            _all_dataset_countries = set(_full_df["country"].unique())
            # Verified against UN Treaty Collection as of 2025-12. Update when new ratifications occur.
            _crpd_ratifiers = {
                "Afghanistan",
                "Albania",
                "Algeria",
                "Andorra",
                "Angola",
                "Antigua and Barbuda",
                "Argentina",
                "Armenia",
                "Australia",
                "Austria",
                "Azerbaijan",
                "Bahamas",
                "Bahrain",
                "Bangladesh",
                "Barbados",
                "Belarus",
                "Belgium",
                "Belize",
                "Benin",
                "Bolivia (Plurinational State of)",
                "Bosnia and Herzegovina",
                "Botswana",
                "Brazil",
                "Brunei Darussalam",
                "Bulgaria",
                "Burkina Faso",
                "Burundi",
                "Cabo Verde",
                "Cambodia",
                "Cameroon",
                "Canada",
                "Central African Republic",
                "Chad",
                "Chile",
                "China",
                "Colombia",
                "Comoros",
                "Congo",
                "Cook Islands",
                "Costa Rica",
                "Croatia",
                "Cuba",
                "Cyprus",
                "Czechia",
                "Denmark",
                "Djibouti",
                "Dominica",
                "Dominican Republic",
                "Ecuador",
                "Egypt",
                "El Salvador",
                "Estonia",
                "Ethiopia",
                "Fiji",
                "Finland",
                "France",
                "Gabon",
                "Gambia",
                "Georgia",
                "Germany",
                "Ghana",
                "Greece",
                "Grenada",
                "Guatemala",
                "Guinea",
                "Guinea-Bissau",
                "Guyana",
                "Haiti",
                "Honduras",
                "Hungary",
                "Iceland",
                "India",
                "Indonesia",
                "Iran (Islamic Republic of)",
                "Iraq",
                "Ireland",
                "Israel",
                "Italy",
                "Jamaica",
                "Japan",
                "Jordan",
                "Kazakhstan",
                "Kenya",
                "Kiribati",
                "Kuwait",
                "Lao People's Democratic Republic",
                "Latvia",
                "Lebanon",
                "Lesotho",
                "Liberia",
                "Libya",
                "Lithuania",
                "Luxembourg",
                "Madagascar",
                "Malawi",
                "Malaysia",
                "Maldives",
                "Mali",
                "Malta",
                "Marshall Islands",
                "Mauritania",
                "Mauritius",
                "Mexico",
                "Micronesia (Federated States Of)",
                "Monaco",
                "Mongolia",
                "Montenegro",
                "Morocco",
                "Mozambique",
                "Myanmar",
                "Namibia",
                "Nauru",
                "Nepal",
                "Netherlands",
                "New Zealand",
                "Nicaragua",
                "Niger",
                "Nigeria",
                "North Macedonia",
                "Norway",
                "Oman",
                "Pakistan",
                "Palau",
                "Panama",
                "Papua New Guinea",
                "Paraguay",
                "Peru",
                "Philippines",
                "Poland",
                "Portugal",
                "Qatar",
                "Republic of Korea",
                "Republic of Moldova",
                "Romania",
                "Russian Federation",
                "Rwanda",
                "Saint Kitts and Nevis",
                "Saint Lucia",
                "Saint Vincent and the Grenadines",
                "Samoa",
                "San Marino",
                "Saudi Arabia",
                "Senegal",
                "Serbia",
                "Seychelles",
                "Sierra Leone",
                "Singapore",
                "Slovakia",
                "Slovenia",
                "Somalia",
                "South Africa",
                "South Sudan",
                "Spain",
                "Sri Lanka",
                "State of Palestine",
                "Sudan",
                "Suriname",
                "Sweden",
                "Switzerland",
                "Syrian Arab Republic",
                "Thailand",
                "Timor-Leste",
                "Togo",
                "Trinidad and Tobago",
                "Tunisia",
                "Turkiye",
                "Turkmenistan",
                "Tuvalu",
                "Uganda",
                "Ukraine",
                "United Arab Emirates",
                "United Kingdom",
                "United Republic of Tanzania",
                "Uruguay",
                "Uzbekistan",
                "Vanuatu",
                "Venezuela (Bolivarian Republic of)",
                "Viet Nam",
                "Yemen",
                "Zambia",
                "Zimbabwe",
            }
            _never_reported = sorted(_crpd_ratifiers - _all_dataset_countries)
            if _never_reported:
                st.markdown(
                    f"<h4 style='text-align:center; margin-top:1.5rem;'>"
                    f"States Parties with No Documents in Dataset "
                    f"({len(_never_reported)})</h4>",
                    unsafe_allow_html=True,
                )
                # Build country→region mapping from full dataset
                _country_region_map = dict(
                    zip(_full_df["country"], _full_df["region"], strict=False)
                )
                _nr_df = pd.DataFrame(
                    {
                        "State Party": _never_reported,
                        "Region": [_country_region_map.get(c, "Unknown") for c in _never_reported],
                    }
                )
                render_accessible_table(
                    _nr_df,
                    caption=f"States Parties with no documents in dataset (n={len(_never_reported)})",
                    max_height=400,
                )
                # CSV download removed — no-data-download policy active
                st.caption(
                    f"{len(_never_reported)} CRPD ratifiers have no documents "
                    f"in the dataset. This may reflect reporting delays, "
                    f"pending submissions, or data collection gaps. "
                    f"Some States Parties ratified the CRPD recently and may not yet "
                    f"have reached their first reporting deadline (initial report is "
                    f"due within 2 years of ratification)."
                )

    # Trends
    elif default_tab == 1:
        st.markdown(
            """
            <p style="font-size:0.94rem;color:#424752;line-height:1.7;margin-bottom:1.5rem;">
                This page tracks the CRPD reporting cycle over time — when
                States Parties submitted documents, which treaty articles
                receive the most attention, and how language patterns have
                evolved. All analysis is based on keyword frequency matching
                against curated dictionaries, not human judgment. Document
                availability reflects the UN Treaty Body Database and may
                lag actual submission dates.
            </p>
            """,
            unsafe_allow_html=True,
        )
        if "year" in df.columns and len(df):
            # Shared computations used by multiple sections
            _yr_min = int(df["year"].min())
            _yr_max = int(df["year"].max())
            _year_span = _yr_max - _yr_min  # #19: guard for overlapping windows

            # ═══════════════════════════════════════════════════════════
            # SECTION 1: Submission Volume
            # ═══════════════════════════════════════════════════════════
            st.markdown("### Submission Volume")
            col1, col2 = st.columns(2)

            with col1:
                yearly = df.groupby("year").size().reset_index(name="count").sort_values("year")
                yearly["year"] = yearly["year"].astype(int).astype(str)
                fig = px.bar(
                    yearly,
                    x="year",
                    y="count",
                    title="Documents Published Per Year",  # #37
                    color_discrete_sequence=[CATEGORICAL_PALETTE[0]],
                    labels={"count": "Documents", "year": "Year"},
                )
                fig.update_layout(
                    xaxis=dict(categoryorder="array", categoryarray=yearly["year"].tolist()),
                )

                _yr_list = yearly["year"].tolist()

                # #34: Partial year heuristic — compare against median
                _max_yr_str = str(_yr_max)
                _max_yr_count = int(yearly.loc[yearly["year"] == _max_yr_str, "count"].iloc[0])
                _median_count = yearly["count"].median()
                if _max_yr_count < _median_count * 0.5:
                    _max_idx = _yr_list.index(_max_yr_str)
                    fig.add_annotation(
                        x=_max_idx,
                        y=_max_yr_count,
                        text="partial year",
                        showarrow=True,
                        arrowhead=2,
                        ax=0,
                        ay=-30,
                        font=dict(size=11, color=CATEGORICAL_PALETTE[6]),  # #17
                    )

                # #31, #36: COVID-era shading + annotation
                if "2020" in yearly["year"].values and "2021" in yearly["year"].values:
                    _idx_2020 = _yr_list.index("2020")
                    _idx_2021 = _yr_list.index("2021")
                    fig.add_shape(
                        type="rect",
                        x0=_idx_2020 - 0.5,
                        x1=_idx_2021 + 0.5,
                        y0=0,
                        y1=1,
                        yref="paper",
                        fillcolor=CATEGORICAL_PALETTE[6],
                        opacity=0.08,
                        line_width=0,
                    )
                    fig.add_annotation(
                        x=(_idx_2020 + _idx_2021) / 2,
                        y=1,
                        yref="paper",
                        text="COVID-19 pandemic",  # #31
                        showarrow=False,
                        font=dict(size=11, color=CATEGORICAL_PALETTE[6]),  # #17
                        yshift=5,
                    )

                st.plotly_chart(fig, width="stretch", key="tl_v5_bump")
                st.markdown(
                    '<span class="sr-only">Bar chart showing the number of CRPD '
                    "documents published per year.</span>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"Showing {len(yearly)} years of reporting data "
                    f"({yearly['count'].sum():,} documents). "
                    "COVID-19 shading shown for temporal reference. "  # #36
                    "Year reflects database availability, which may lag submission."  # Fix 6
                )

            with col2:
                by_type_year = df.groupby(["year", "doc_type"]).size().reset_index(name="count")
                # Fix #1: Cast year to int→str
                by_type_year["year"] = by_type_year["year"].astype(int).astype(str)
                fig = px.bar(
                    by_type_year,
                    x="year",
                    y="count",
                    color="doc_type",
                    title="Document Type Composition Over Time",
                    color_discrete_map=DOC_TYPE_COLORS,
                    labels={
                        "count": "Documents",
                        "year": "Year",
                        "doc_type": "Document Type",
                    },
                )
                _yr_order = sorted(by_type_year["year"].unique().tolist())
                fig.update_layout(
                    barnorm="percent",
                    yaxis_title="Share of Documents (%)",
                    bargap=0.1,
                    xaxis=dict(categoryorder="array", categoryarray=_yr_order),
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.25,
                        xanchor="center",
                        x=0.5,
                    ),
                )
                st.plotly_chart(fig, width="stretch", key="tl_v10_gaps")
                st.markdown(
                    '<span class="sr-only">Stacked bar chart showing document type '
                    "composition as percentages over time.</span>",
                    unsafe_allow_html=True,
                )
                # Batch C: Annotate years where not all doc types are present
                _n_all_types = df["doc_type"].nunique()
                _types_per_yr = by_type_year.groupby("year")["doc_type"].nunique()
                _incomplete_yrs = _types_per_yr[_types_per_yr < _n_all_types]
                _type_note = ""
                if len(_incomplete_yrs):
                    _type_note = (
                        f" Not all {_n_all_types} document types appear in every year; "
                        "early years may be dominated by State Reports."
                    )
                st.caption(
                    f"Proportional breakdown across {_n_all_types} document types.{_type_note}"
                )

            # ═══════════════════════════════════════════════════════════
            # SECTION 2: Language & Framing
            # ═══════════════════════════════════════════════════════════
            st.markdown("---")
            st.markdown("### Language & Framing")

            # #14: Compute model_shift_table ONCE, derive early/late from it
            _mt_all = model_shift_table(df)
            _early_df = df[df["year"] <= _yr_min + 2]
            _late_df = df[df["year"] >= _yr_max - 2]
            _mt_early = _mt_all[_mt_all["year"] <= _yr_min + 2] if len(_mt_all) else pd.DataFrame()
            _mt_late = _mt_all[_mt_all["year"] >= _yr_max - 2] if len(_mt_all) else pd.DataFrame()

            _early_rpct = _late_rpct = 0
            if len(_mt_early) and _mt_early[["medical", "rights"]].sum().sum() > 0:
                _early_rpct = (
                    _mt_early["rights"].sum()
                    / (_mt_early["medical"].sum() + _mt_early["rights"].sum())
                    * 100
                )
            if len(_mt_late) and _mt_late[["medical", "rights"]].sum().sum() > 0:
                _late_rpct = (
                    _mt_late["rights"].sum()
                    / (_mt_late["medical"].sum() + _mt_late["rights"].sum())
                    * 100
                )

            _n_early = len(_early_df)
            _n_late = len(_late_df)

            # #8: Minimum n guard for phase label
            if _n_late < 5:
                _phase_label = "Insufficient Data"
                _phase_bg = CARD_BG
                _phase_color = TEXT_MUTED
            elif _late_rpct >= 55:
                # #4: Include "Language" in phase labels
                _phase_label = "Predominantly Rights-Based Language"
                _phase_bg = PHASE_RIGHTS_BG
                _phase_color = SEQUENTIAL_BLUES[3]
            elif _late_rpct <= 45:
                _phase_label = "Predominantly Medical Language"
                _phase_bg = PHASE_MEDICAL_BG
                _phase_color = CATEGORICAL_PALETTE[6]
            else:
                _phase_label = "Balanced"
                _phase_bg = PHASE_BALANCED_BG
                _phase_color = PHASE_BALANCED_TEXT  # #5: darker olive for contrast

            # #1: Detect doc type authorship for accurate framing
            _committee_types = {"Concluding Observations", "List of Issues (LOI)"}
            _state_types = {"State Report", "Written Reply"}
            _active_types = set(df["doc_type"].unique())
            if _active_types <= _committee_types:
                _doc_framing = "CRPD committee documents"
            elif _active_types <= _state_types:
                _doc_framing = "States Parties' CRPD reporting"
            else:
                _doc_framing = "CRPD documents"

            # #2: Data-driven shift description
            if _late_rpct > _early_rpct + 5:
                _shift_desc = "a shift toward rights-based language"
            elif _early_rpct > _late_rpct + 5:
                _shift_desc = "a shift toward medical-model language"
            else:
                _shift_desc = "relatively stable language proportions"

            # #21: Filter context note
            _filter_note = ""
            if df["doc_type"].nunique() < 5:
                _active_list = ", ".join(sorted(df["doc_type"].unique()))
                _filter_note = (
                    f"<div style='font-size:12px;color:{TEXT_MUTED};"
                    f"margin-top:4px;'>Filtered to: {_active_list}</div>"
                )

            # #20: Single document guard
            if len(df) < 2 or _yr_min == _yr_max:
                st.markdown(
                    f"<div role='region' aria-label='Language patterns summary' "
                    f"style='background:{NARRATIVE_BG};border-left:4px solid "
                    f"{SEQUENTIAL_BLUES[3]};padding:20px 24px;"
                    "border-radius:0 8px 8px 0;margin-bottom:20px;"
                    "font-family:Inter,Arial,sans-serif;'>"
                    "<h4 style='font-size:15px;font-weight:700;"
                    f"color:{SEQUENTIAL_BLUES[5]};margin:0 0 8px 0;'>"
                    "Language Patterns in CRPD Reporting</h4>"
                    f"<p style='font-size:14px;color:#000000;line-height:1.7;"
                    f"margin:0;'>Only {len(df)} document(s) from {_yr_min}. "
                    f"Language balance: {_late_rpct:.0f}% rights-based keywords.</p>"
                    "</div>",
                    unsafe_allow_html=True,
                )
            elif _year_span < 5:
                # #19: Short span — no shift framing (guard widened to <5 to prevent window overlap)
                st.markdown(
                    f"<div role='region' aria-label='Language patterns summary' "
                    f"style='background:{NARRATIVE_BG};border-left:4px solid "
                    f"{SEQUENTIAL_BLUES[3]};padding:20px 24px;"
                    "border-radius:0 8px 8px 0;margin-bottom:20px;"
                    "font-family:Inter,Arial,sans-serif;'>"
                    "<h4 style='font-size:15px;font-weight:700;"
                    f"color:{SEQUENTIAL_BLUES[5]};margin:0 0 8px 0;'>"
                    "Language Patterns in CRPD Reporting</h4>"
                    f"<p style='font-size:14px;color:#000000;line-height:1.7;"
                    f"margin:0 0 12px 0;'>Across {len(df)} {_doc_framing} "
                    f"({_yr_min}\u2013{_yr_max}), rights-based keywords account "
                    f"for {_late_rpct:.0f}% of model keywords (n={_n_late}), "
                    "as measured by keyword frequency analysis.</p>"
                    "<div style='display:flex;align-items:center;gap:8px;'>"
                    f"<span style='font-size:12px;font-weight:700;"
                    f"color:{CATEGORICAL_PALETTE[6]};"
                    "text-transform:uppercase;letter-spacing:1.5px;'>"
                    "Current Balance</span>"
                    f"<span style='font-size:13px;font-weight:600;"
                    f"color:{_phase_color};background:{_phase_bg};"
                    "padding:2px 10px;border-radius:12px;'>"
                    f"{_phase_label} ({_late_rpct:.0f}%)</span>"
                    f"</div>{_filter_note}</div>",
                    unsafe_allow_html=True,
                )
            else:
                # #3, #16: Full narrative card with semantic HTML
                st.markdown(
                    f"<div role='region' aria-label='Language patterns summary' "
                    f"style='background:{NARRATIVE_BG};border-left:4px solid "
                    f"{SEQUENTIAL_BLUES[3]};padding:20px 24px;"
                    "border-radius:0 8px 8px 0;margin-bottom:20px;"
                    "font-family:Inter,Arial,sans-serif;'>"
                    "<h4 style='font-size:15px;font-weight:700;"
                    f"color:{SEQUENTIAL_BLUES[5]};margin:0 0 8px 0;'>"
                    "Language Patterns in CRPD Reporting</h4>"
                    f"<p style='font-size:14px;color:#000000;line-height:1.7;"
                    f"margin:0 0 12px 0;'>Across the selected {_doc_framing} between "
                    f"{_yr_min} and {_yr_max}, keyword analysis shows {_shift_desc} \u2014 "
                    f"from <strong style='color:{SEQUENTIAL_BLUES[5]};'>"
                    f"{100 - _early_rpct:.0f}% medical</strong> keywords in early "
                    f"reports (n={_n_early}) to "
                    f"<strong style='color:{SEQUENTIAL_BLUES[3]};'>"
                    f"{_late_rpct:.0f}% rights-based</strong> in recent reports "
                    f"(n={_n_late}), as measured by keyword frequency analysis.</p>"
                    "<div style='display:flex;align-items:center;gap:8px;'>"
                    f"<span style='font-size:12px;font-weight:700;"
                    f"color:{CATEGORICAL_PALETTE[6]};"
                    "text-transform:uppercase;letter-spacing:1.5px;'>"
                    "Current Balance</span>"
                    f"<span style='font-size:13px;font-weight:600;"
                    f"color:{_phase_color};background:{_phase_bg};"
                    "padding:2px 10px;border-radius:12px;'>"
                    f"{_phase_label} ({_late_rpct:.0f}%)</span>"
                    f"</div>{_filter_note}</div>",
                    unsafe_allow_html=True,
                )

            # Fix 2: Aggregate caveat when no single-country filter is active
            if df["country"].nunique() > 1:
                st.caption(
                    "This reflects the aggregate across all filtered documents. "
                    "Individual States Parties may differ significantly."
                )
            # Stakeholder flag #4: Ratification-expansion disclosure
            if _year_span >= 5:
                st.caption(
                    "Note: Early-period data reflects fewer ratifications "
                    "(~50 States Parties by 2012) compared to the current period "
                    "(~190). Differences may partly reflect expanding participation "
                    "rather than language shifts within individual States Parties."
                )

            # ── Keyword Category Trends chart ──
            st.markdown("---")
            st.markdown("#### Keyword Category Trends")  # #26 → Fix 5: renamed
            if len(_mt_all):
                # #9, #22: Use charted (non-NaN year) rows for caption counts
                _mt_charted = _mt_all.dropna(subset=["year"])
                _mt_yearly = _mt_charted.groupby("year")[["medical", "rights"]].sum().reset_index()
                _mt_yearly["year"] = _mt_yearly["year"].astype(int).astype(str)
                _mt_yearly_long = _mt_yearly.melt(
                    id_vars="year",
                    value_vars=["medical", "rights"],
                    var_name="Model",
                    value_name="Keywords",
                )
                _mt_yearly_long["Model"] = _mt_yearly_long["Model"].map(
                    {"medical": "Medical Model", "rights": "Rights-Based Model"}
                )
                # Fix 4: Compute per-year doc counts for hover context
                _docs_per_year = (
                    df.dropna(subset=["year"]).groupby("year").size().reset_index(name="n_docs")
                )
                _docs_per_year["year"] = _docs_per_year["year"].astype(int).astype(str)
                _mt_yearly_long = _mt_yearly_long.merge(_docs_per_year, on="year", how="left")
                _mt_yearly_long["n_docs"] = _mt_yearly_long["n_docs"].fillna(0).astype(int)
                fig = px.area(
                    _mt_yearly_long,
                    x="year",
                    y="Keywords",
                    color="Model",
                    title="Medical vs. Rights-Based Language Over Time",
                    color_discrete_map={
                        "Rights-Based Model": MODEL_COLORS["Rights-Based"],
                        "Medical Model": MODEL_COLORS["Medical Model"],
                    },
                    labels={"year": "Year", "Keywords": "Keyword Count"},
                    groupnorm="fraction",
                    custom_data=["n_docs"],
                )
                fig.update_traces(
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "%{fullData.name}: %{y:.0%}<br>"
                        "Documents: %{customdata[0]}"
                        "<extra></extra>"
                    )
                )
                _mt_yr_order = sorted(_mt_yearly["year"].unique().tolist())
                fig.update_layout(
                    yaxis_title="Share of Keywords",
                    yaxis_tickformat=".0%",
                    xaxis=dict(categoryorder="array", categoryarray=_mt_yr_order),
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.2,
                        xanchor="center",
                        x=0.5,
                    ),
                )
                st.plotly_chart(fig, width="stretch", key="tl_model_shift")
                # #6: Alt-text for screen readers
                st.markdown(
                    '<span class="sr-only">Area chart showing the proportional share of '
                    "medical vs rights-based keywords over time.</span>",
                    unsafe_allow_html=True,
                )
                # #9, #22: Caption uses charted totals
                _charted_total = int(_mt_charted["medical"].sum() + _mt_charted["rights"].sum())
                st.caption(
                    f"Proportional keyword share across {len(_mt_yearly)} years "
                    f"({_charted_total:,} total keyword matches). "
                    "Years with low document volume may show volatile proportions."
                )
                # #25: CSV download removed — no-data-download policy active

            # ═══════════════════════════════════════════════════════════
            # SECTION 3: Reporting Gaps
            # ═══════════════════════════════════════════════════════════
            st.markdown("---")
            st.markdown("### Reporting Gaps")
            _current_year = datetime.now().year  # #13
            _last_report = df.groupby("country")["year"].max().reset_index()
            _last_report["gap"] = _current_year - _last_report["year"]
            _overdue = (
                _last_report[_last_report["gap"] >= 3].sort_values("gap", ascending=False).head(20)
            )
            if len(_overdue):
                fig = px.bar(
                    _overdue,
                    x="gap",
                    y="country",
                    orientation="h",
                    title="Reporting Cycle Status by State Party",  # Fix 10: reframed
                    color="gap",
                    color_continuous_scale=[
                        SEQUENTIAL_BLUES[1],
                        SEQUENTIAL_BLUES[3],
                        SEQUENTIAL_BLUES[5],
                    ],
                    labels={
                        "gap": "Years Since Last Submission",  # Fix 10
                        "country": "State Party",  # #12
                    },
                )
                fig.update_layout(
                    yaxis=dict(autorange="reversed"),
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig, width="stretch", key="tl_dd_v6_lang")
                st.markdown(
                    '<span class="sr-only">Horizontal bar chart showing '
                    "reporting cycle status by State Party.</span>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"{len(_overdue)} States Parties with 3+ years since last submission. "
                    "Gaps reflect database availability; reports may be in processing. "
                    "Recently ratified States Parties may not yet be due for "
                    "initial reports."  # Fix 10: caveat
                )
            else:
                st.info("No States Parties with reporting gaps of 3+ years.")

            # ═══════════════════════════════════════════════════════════
            # DEEP DIVE EXPANDER (collapsed by default)
            # V6, V7, V8, V12, V13 — V11 removed (redundant with V8)
            # ═══════════════════════════════════════════════════════════
            st.markdown("---")
            with st.expander(
                "**Explore: Regional Patterns, Document Characteristics & NLP**",
                expanded=False,
            ):
                # ── V7 (Regional cadence) + V6 (Language of submission) ──
                _dd_col1, _dd_col2 = st.columns(2)

                with _dd_col1:
                    region_year = df.groupby(["year", "region"]).size().reset_index(name="count")
                    # Batch C: Region guard — heatmap needs 2+ regions
                    if len(region_year) and region_year["region"].nunique() < 2:
                        st.info(
                            "Regional cadence heatmap requires 2+ regions. "
                            "Broaden filters to compare."
                        )
                    elif len(region_year):
                        # #7: Normalize by number of States Parties per region
                        _region_sp_count = df.groupby("region")["country"].nunique()
                        region_year["per_sp"] = region_year.apply(
                            lambda r: r["count"] / _region_sp_count.get(r["region"], 1),
                            axis=1,
                        )
                        region_year["year"] = region_year["year"].astype(int).astype(str)
                        pivot = region_year.pivot(
                            index="region", columns="year", values="per_sp"
                        ).fillna(0)
                        fig = px.imshow(
                            pivot,
                            title="Documents Per State Party by Region",  # #7
                            color_continuous_scale=[
                                SEQUENTIAL_BLUES[0],
                                SEQUENTIAL_BLUES[2],
                                SEQUENTIAL_BLUES[5],
                            ],
                            labels={
                                "x": "Year",
                                "y": "Region",
                                "color": "Docs / State Party",  # #7
                            },
                            aspect="auto",
                        )
                        st.plotly_chart(fig, width="stretch", key="tl_dd_v6_cum")
                        st.markdown(
                            '<span class="sr-only">Heatmap showing documents per '
                            "State Party by region and year.</span>",
                            unsafe_allow_html=True,
                        )
                        st.caption(
                            f"Documents per State Party across {len(pivot)} regions and "
                            f"{len(pivot.columns)} years (normalized by States Parties per region)"
                        )

                with _dd_col2:
                    if "language" in df.columns and df["language"].nunique() >= 2:
                        _lang_yr = (
                            df.dropna(subset=["year"])
                            .groupby(["year", "language"])
                            .size()
                            .reset_index(name="count")
                        )
                        if len(_lang_yr):
                            _lang_yr["year"] = _lang_yr["year"].astype(int).astype(str)
                            fig = px.bar(
                                _lang_yr,
                                x="year",
                                y="count",
                                color="language",
                                title="Language of Submission Over Time",
                                color_discrete_sequence=CATEGORICAL_PALETTE,
                                labels={
                                    "count": "Documents",
                                    "year": "Year",
                                    "language": "Language",
                                },
                            )
                            _lang_yr_order = sorted(_lang_yr["year"].unique().tolist())
                            fig.update_layout(
                                barnorm="percent",
                                yaxis_title="Share of Documents (%)",
                                bargap=0.1,
                                xaxis=dict(categoryorder="array", categoryarray=_lang_yr_order),
                                legend=dict(
                                    orientation="h",
                                    yanchor="top",
                                    y=-0.25,
                                    xanchor="center",
                                    x=0.5,
                                ),
                            )
                            st.plotly_chart(fig, width="stretch", key="tl_dd_v8_boxplot")
                            st.markdown(
                                '<span class="sr-only">Stacked bar chart showing '
                                "submission language distribution over time.</span>",
                                unsafe_allow_html=True,
                            )
                            st.caption(
                                f"Submission languages across {df['language'].nunique()} languages"
                            )
                    else:
                        # Fallback: Cumulative countries reporting over time
                        _df_yr = df.dropna(subset=["year"]).sort_values("year")
                        if len(_df_yr):
                            _yearly_countries = _df_yr.groupby("year")["country"].apply(set)
                            _seen: set = set()
                            _cum_list = []
                            for yr in _yearly_countries.index:
                                _seen |= _yearly_countries[yr]
                                _cum_list.append({"year": yr, "cumulative_countries": len(_seen)})
                            _cum_countries = pd.DataFrame(_cum_list)
                            _cum_countries["year"] = _cum_countries["year"].astype(int).astype(str)
                            fig = px.area(
                                _cum_countries,
                                x="year",
                                y="cumulative_countries",
                                title="Cumulative States Parties Reporting Over Time",
                                color_discrete_sequence=[CATEGORICAL_PALETTE[2]],
                                labels={
                                    "cumulative_countries": "Distinct States Parties",  # #11
                                    "year": "Year",
                                },
                            )
                            fig.update_layout(
                                xaxis=dict(
                                    categoryorder="array",
                                    categoryarray=_cum_countries["year"].tolist(),
                                ),
                            )
                            st.plotly_chart(fig, width="stretch", key="tl_dd_v12_keywords")
                            st.markdown(
                                '<span class="sr-only">Area chart showing cumulative '
                                "States Parties reporting over time.</span>",
                                unsafe_allow_html=True,
                            )
                            st.caption(
                                f"{df['country'].nunique()} distinct States Parties "
                                f"across {len(_cum_countries)} years"
                            )

                # ── V8 (Doc length box plots) + V12 (Top keywords) ──
                _dd_col3, _dd_col4 = st.columns(2)

                with _dd_col3:
                    if "word_count" in df.columns and df["word_count"].notna().any():
                        # #33: Skip years with <5 docs for meaningful box plots
                        _yr_counts = df.groupby("year").size()
                        _valid_years = _yr_counts[_yr_counts >= 5].index
                        _box_df = df[df["year"].isin(_valid_years)].copy()
                        _box_df["year"] = _box_df["year"].astype(int).astype(str)
                        _skipped = len(_yr_counts) - len(_valid_years)

                        fig = px.box(
                            _box_df,
                            x="year",
                            y="word_count",
                            title="Document Length Distribution by Year",
                            color_discrete_sequence=[CATEGORICAL_PALETTE[0]],
                            labels={"word_count": "Word Count", "year": "Year"},
                        )
                        _box_yr_order = sorted(_box_df["year"].unique().tolist())
                        fig.update_layout(
                            xaxis=dict(categoryorder="array", categoryarray=_box_yr_order),
                        )
                        st.plotly_chart(fig, width="stretch", key="tl_dd_v13_topics")
                        st.markdown(
                            '<span class="sr-only">Box plot showing document length '
                            "distribution by year.</span>",
                            unsafe_allow_html=True,
                        )
                        # #24, #33: Count non-NaN word_count rows
                        _wc_count = _box_df["word_count"].notna().sum()
                        _skip_note = (
                            f" ({_skipped} year(s) with <5 docs excluded)" if _skipped else ""
                        )
                        st.caption(
                            f"Word count distribution across {_wc_count:,} documents{_skip_note}"
                        )

                with _dd_col4:
                    _top_kw = keyword_counts(df, top_n=15)
                    if len(_top_kw):
                        _top_kw = _top_kw.sort_values("freq", ascending=True)
                        fig = px.bar(
                            _top_kw,
                            x="freq",
                            y="term",
                            orientation="h",
                            title="Most Frequent Terms Across Documents",
                            color_discrete_sequence=[CATEGORICAL_PALETTE[0]],
                            labels={"freq": "Occurrences", "term": "Term"},  # Fix 11
                        )
                        st.plotly_chart(fig, width="stretch")
                        st.markdown(
                            '<span class="sr-only">Horizontal bar chart showing '
                            "the 15 most frequent terms across documents.</span>",
                            unsafe_allow_html=True,
                        )
                        st.caption(f"Top 15 terms from {len(df):,} documents (stopwords removed)")

                # ── V13: Topic Discovery (full width in expander) ──
                st.markdown("---")
                st.markdown("##### Topic Discovery")
                # #15: LDA minimum document threshold (Batch C: raised 20→50)
                if len(df) >= 50:
                    _topics = extract_topics_lda(df, n_topics=5, n_words=8)
                else:
                    _topics = None
                if _topics and _topics.get("topic_labels"):
                    _topic_data = pd.DataFrame(
                        {
                            "Topic": _topics["topic_labels"],
                            "Prevalence": _topics["topic_prevalence"],
                        }
                    )
                    _topic_data = _topic_data.sort_values("Prevalence", ascending=True)
                    fig = px.bar(
                        _topic_data,
                        x="Prevalence",
                        y="Topic",
                        orientation="h",
                        title="Dominant Topics Across CRPD Documents",
                        color="Topic",
                        color_discrete_sequence=CATEGORICAL_PALETTE,
                        labels={"Prevalence": "Documents Where Dominant (%)"},
                    )
                    fig.update_layout(
                        showlegend=False,
                    )
                    st.plotly_chart(fig, width="stretch")
                    st.markdown(
                        '<span class="sr-only">Horizontal bar chart showing dominant '
                        "topics discovered via LDA topic modeling.</span>",
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        f"LDA topic model with 5 topics across {len(df):,} documents. "
                        "Topic labels are auto-generated from dominant keywords "
                        "in each cluster. Exploratory — topics are filter-dependent "
                        "and may change with different selections."  # Batch C: caveat
                    )
                elif len(df) < 50:
                    st.info(
                        "Topic discovery requires at least 50 documents for stable results. "
                        f"Current selection has {len(df)}."
                    )

        else:
            st.info("Year data not available or no documents match current filters.")

    # Country Profiles
    elif default_tab == 2:
        st.markdown(
            "<h2 style='font-family:Inter,Arial,sans-serif;font-weight:800;"
            "color:#191C1F;margin-bottom:2px;'>Country Profiles</h2>"
            "<p style='font-family:Inter,Arial,sans-serif;font-size:1.05rem;"
            "color:#5a6377;margin-top:0;margin-bottom:1.2rem;'>"
            "Deep-dive into a single country's CRPD reporting history "
            "and article coverage.</p>",
            unsafe_allow_html=True,
        )

        _profile_mode = st.radio(
            "Browse profiles by:",
            ["State Party", "Geographic Region", "International Organization"],
            horizontal=True,
            index=[
                "State Party",
                "Geographic Region",
                "International Organization",
            ].index(st.session_state.get("profile_mode", "State Party")),
            key="profile_mode",
        )

        if _profile_mode == "Geographic Region":
            if len(df):
                _regions = sorted(df["region"].dropna().unique())
                _selected_region = st.selectbox("Select a region:", _regions, key="profile_region")
                df_group = df[df["region"] == _selected_region]
                _render_group_profile(df_group, _selected_region, "Region", df, ARTICLE_PRESETS)
            else:
                st.info("No data available with current filters.")

        elif _profile_mode == "International Organization":
            if len(df):
                _orgs = get_custom_organizations()
                _selected_org = st.selectbox(
                    "Select an organization:",
                    sorted(_orgs.keys()),
                    key="profile_org",
                )
                _org_isos = _orgs[_selected_org]
                df_group = df[df["iso3"].isin(_org_isos)]
                _render_group_profile(
                    df_group,
                    _selected_org,
                    "Organization",
                    df,
                    ARTICLE_PRESETS,
                    org_iso_codes=_org_isos,
                )
            else:
                st.info("No data available with current filters.")

        elif len(df):
            # Compute global benchmarks once (not per country selection)
            _mt_global = model_shift_table(df)
            _global_rights_pct = None
            if len(_mt_global) and _mt_global[["medical", "rights"]].sum().sum() > 0:
                _global_rights_pct = (
                    _mt_global["rights"].sum()
                    / (_mt_global["medical"].sum() + _mt_global["rights"].sum())
                    * 100
                )

            selected_country = st.selectbox(
                "Select a country to explore:", sorted(df["country"].unique())
            )

            if selected_country:
                country_df = df[df["country"] == selected_country]

                # Region / subregion context
                _region = country_df["region"].iloc[0] if "region" in country_df.columns else ""
                _subregion = (
                    country_df["subregion"].iloc[0] if "subregion" in country_df.columns else ""
                )
                _loc_parts = [p for p in [_subregion, _region] if p and p != "nan"]
                if _loc_parts:
                    st.caption(" · ".join(_loc_parts))

                # Country metrics
                _n_docs = f"{len(country_df):,}"
                _n_dtypes = str(country_df["doc_type"].nunique())
                if "year" in country_df.columns and len(country_df):
                    years_range = f"{int(country_df['year'].min())}–{int(country_df['year'].max())}"
                else:
                    years_range = "—"
                _avg_words = (
                    f"{int(country_df['word_count'].mean()):,}"
                    if "word_count" in country_df.columns
                    else "—"
                )
                _mt = model_shift_table(country_df)
                if len(_mt) and _mt[["medical", "rights"]].sum().sum() > 0:
                    _rights_pct = (
                        _mt["rights"].sum() / (_mt["medical"].sum() + _mt["rights"].sum()) * 100
                    )
                    _rights_val = f"{_rights_pct:.0f}%"
                    if _global_rights_pct is not None:
                        _diff = _rights_pct - _global_rights_pct
                        _arrow = "↑" if _diff > 0 else "↓" if _diff < 0 else "→"
                        _rights_val += f" ({_arrow} vs {_global_rights_pct:.0f}% global)"
                else:
                    _rights_val = "—"

                _metrics = [
                    ("Documents", _n_docs),
                    ("Document Types", _n_dtypes),
                    ("Years", years_range),
                    ("Avg Words", _avg_words),
                    ("Rights-Based %", _rights_val),
                ]
                _pills = "".join(
                    f"<span style='display:inline-flex;align-items:baseline;gap:5px;"
                    f"padding:6px 16px;border-radius:8px;background:#ffffff;"
                    f"box-shadow:0 1px 4px rgba(0,0,0,0.06);"
                    f"font-family:Inter,Arial,sans-serif;font-size:14px;'>"
                    f"<span style='color:#5a6377;font-weight:500;'>{lbl}</span>"
                    f"<span style='color:#191C1F;font-weight:700;'>{val}</span>"
                    f"</span>"
                    for lbl, val in _metrics
                )
                st.markdown(
                    f"<div style='display:flex;flex-wrap:wrap;gap:10px;"
                    f"margin-bottom:12px;'>{_pills}</div>",
                    unsafe_allow_html=True,
                )

                # ── Row 2: Reporting Cycle Status (full width) ──
                _expected_types = [
                    "State Report",
                    "List of Issues (LOI)",
                    "Written Reply",
                    "Concluding Observations",
                    "Response to Concluding Observations",
                ]
                _submitted = set(country_df["doc_type"].unique())
                _badge_parts = []
                for dt in _expected_types:
                    if dt in _submitted:
                        _dt_rows = country_df[country_df["doc_type"] == dt]
                        _dt_count = len(_dt_rows)
                        _dt_years = sorted(_dt_rows["year"].dropna().astype(int).unique())
                        if _dt_count == 1:
                            _yr_label = str(_dt_years[0])
                        else:
                            _yr_label = f"{_dt_count}× : {_dt_years[0]}–{_dt_years[-1]}"
                        _bg = DOC_TYPE_COLORS.get(dt, CATEGORICAL_PALETTE[6])
                        _badge_parts.append(
                            f"<span style='display:inline-flex;align-items:center;gap:6px;"
                            f"padding:6px 14px;border-radius:6px;background:{_bg};"
                            f"color:#ffffff;font-size:13px;font-weight:600;"
                            f"font-family:Inter,Arial,sans-serif;'>"
                            f"&#10003; {dt} ({_yr_label})</span>"
                        )
                    else:
                        _badge_parts.append(
                            "<span style='display:inline-flex;align-items:center;gap:6px;"
                            "padding:6px 14px;border-radius:6px;background:#e8e8e8;"
                            "color:#999999;font-size:13px;font-weight:600;"
                            f"font-family:Inter,Arial,sans-serif;'>&#10007; {dt}</span>"
                        )
                st.markdown("#### Reporting Cycle Status")
                st.markdown(
                    "<div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;'>"
                    + "".join(_badge_parts)
                    + "</div>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"{len(_submitted)} of {len(_expected_types)} document types submitted "
                    f"({len(country_df)} documents total)"
                )

                if len(country_df) <= 2:
                    st.info(
                        f"⚠ Limited data: {selected_country} has only "
                        f"{len(country_df)} document(s). Charts below may be sparse."
                    )

                # ── Row 3: Article bar by doc type + Article coverage heatmap ──
                _exclude_art1 = st.toggle(
                    "**Exclude Article 1 — Purpose (highest frequency article)**",
                    value=False,
                    key=f"exclude_art1_{selected_country}",
                )
                st.markdown(
                    "<style>[data-testid='stToggle'] label p "
                    "{color: #000000 !important; font-weight: 700 !important;}</style>",
                    unsafe_allow_html=True,
                )
                col1, col2 = st.columns(2)

                with col1:
                    country_art = article_frequency(country_df, ARTICLE_PRESETS, groupby="doc_type")
                    if _exclude_art1:
                        country_art = country_art[country_art["article"] != "Article 1 — Purpose"]
                    if not country_art.empty:
                        top_articles = (
                            country_art.groupby("article")["count"]
                            .sum()
                            .nlargest(10)
                            .index.tolist()
                        )
                        top_art_df = country_art[country_art["article"].isin(top_articles)]
                        fig = px.bar(
                            top_art_df,
                            x="count",
                            y="article",
                            color="group",
                            orientation="h",
                            title=f"Top CRPD Articles — {selected_country}",
                            color_discrete_map=DOC_TYPE_COLORS,
                            labels={
                                "count": "Mentions",
                                "article": "Article",
                                "group": "Document Type",
                            },
                        )
                        fig.update_layout(
                            legend=dict(
                                orientation="h",
                                yanchor="top",
                                y=-0.2,
                                xanchor="center",
                                x=0.5,
                            ),
                        )
                        st.plotly_chart(fig, width="stretch")
                        st.caption(
                            f"Top 10 of {len(country_art['article'].unique())} "
                            "articles by keyword frequency (regex-matched from document text)"
                        )
                    else:
                        st.info("No CRPD article references found for this country.")

                with col2:
                    country_art_yr = article_frequency(country_df, ARTICLE_PRESETS, groupby="year")
                    if _exclude_art1:
                        country_art_yr = country_art_yr[
                            country_art_yr["article"] != "Article 1 — Purpose"
                        ]
                    if not country_art_yr.empty:
                        # Cast year groups to int→str for clean axis labels
                        country_art_yr["group"] = country_art_yr["group"].astype(int).astype(str)
                        _n_years = country_art_yr["group"].nunique()

                        if _n_years <= 1:
                            # Single-year: simple horizontal bar instead of heatmap
                            _single_yr = country_art_yr["group"].iloc[0]
                            _top_single = (
                                country_art_yr.groupby("article")["count"]
                                .sum()
                                .nlargest(15)
                                .reset_index()
                            )
                            fig = px.bar(
                                _top_single,
                                x="count",
                                y="article",
                                orientation="h",
                                title=f"Article Mentions ({_single_yr}) — {selected_country}",
                                color_discrete_sequence=[SEQUENTIAL_BLUES[4]],
                                labels={"count": "Mentions", "article": "Article"},
                            )
                            st.plotly_chart(fig, width="stretch")
                            st.caption(
                                f"Article keyword counts for {_single_yr} "
                                f"— {len(country_df)} document(s)"
                            )
                        else:
                            # Multi-year: heatmap
                            pivot = country_art_yr.pivot(
                                index="article", columns="group", values="count"
                            ).fillna(0)
                            top_art_names = pivot.sum(axis=1).nlargest(15).index.tolist()
                            pivot = pivot.loc[top_art_names]
                            fig = px.imshow(
                                pivot,
                                title=f"Article Coverage Over Time — {selected_country}",
                                color_continuous_scale=[
                                    SEQUENTIAL_BLUES[0],
                                    SEQUENTIAL_BLUES[2],
                                    SEQUENTIAL_BLUES[5],
                                ],
                                labels={"x": "Year", "y": "Article", "color": "Mentions"},
                                aspect="auto",
                            )
                            st.plotly_chart(fig, width="stretch")
                            st.caption(
                                f"Keyword mention intensity across {_n_years} reporting "
                                f"year(s) — {len(country_df)} documents"
                            )
                    else:
                        st.info("No article coverage data available.")

                # ── Row 3b: KWIC — keyword-in-context samples ──
                with st.expander("Keyword-in-Context Samples"):
                    import re as _re

                    _kwic_articles = (
                        country_art.groupby("article")["count"].sum().nlargest(5).index.tolist()
                        if not country_art.empty
                        else []
                    )
                    if _kwic_articles:
                        _sel_art = st.selectbox(
                            "Select article to inspect matches:",
                            _kwic_articles,
                            key=f"kwic_art_{selected_country}",
                        )
                        _art_keywords = ARTICLE_PRESETS.get(_sel_art, [])
                        if _art_keywords:
                            _kw_pattern = _re.compile(
                                r"\b("
                                + "|".join(
                                    _re.escape(kw)
                                    for kw in sorted(_art_keywords, key=len, reverse=True)
                                )
                                + r")\b",
                                _re.IGNORECASE,
                            )
                            _kwic_rows = []
                            for _, row in country_df.iterrows():
                                text = str(row.get("clean_text", ""))
                                for m in _kw_pattern.finditer(text):
                                    start = max(0, m.start() - 60)
                                    end = min(len(text), m.end() + 60)
                                    context = (
                                        ("..." if start > 0 else "")
                                        + text[start : m.start()]
                                        + f"[{m.group().upper()}]"
                                        + text[m.end() : end]
                                        + ("..." if end < len(text) else "")
                                    )
                                    _kwic_rows.append(
                                        {
                                            "Year": int(row.get("year", 0)),
                                            "Document Type": str(row.get("doc_type", "")),
                                            "Keyword": m.group(),
                                            "Context": context,
                                        }
                                    )
                                    if len(_kwic_rows) >= 20:
                                        break
                                if len(_kwic_rows) >= 20:
                                    break
                            if _kwic_rows:
                                render_accessible_table(
                                    pd.DataFrame(_kwic_rows),
                                    caption=f"Keyword-in-context matches for {_sel_art} (up to 20)",
                                )
                            else:
                                st.info(f"No keyword matches found for {_sel_art}.")
                        else:
                            st.info(f"No keywords defined for {_sel_art}.")
                    else:
                        st.info("No article data available for keyword inspection.")

                # ── Row 4: Document length + Model language evolution ──
                col3, col4 = st.columns(2)

                with col3:
                    if (
                        "word_count" in country_df.columns
                        and country_df["word_count"].notna().any()
                    ):
                        len_df = country_df.copy()
                        len_df["year"] = len_df["year"].astype(int).astype(str)
                        fig = px.bar(
                            len_df,
                            x="year",
                            y="word_count",
                            color="doc_type",
                            title=f"Document Length — {selected_country}",
                            color_discrete_map=DOC_TYPE_COLORS,
                            labels={
                                "word_count": "Word Count",
                                "year": "Year",
                                "doc_type": "Document Type",
                            },
                            barmode="group",
                        )
                        fig.update_layout(
                            legend=dict(
                                orientation="h",
                                yanchor="top",
                                y=-0.25,
                                xanchor="center",
                                x=0.5,
                            ),
                        )
                        _global_avg = (
                            df["word_count"].mean() if "word_count" in df.columns else None
                        )
                        if _global_avg:
                            fig.add_hline(
                                y=_global_avg,
                                line_dash="dash",
                                line_color=CATEGORICAL_PALETTE[6],
                                annotation_text=(
                                    f"Global avg: {int(_global_avg):,} (across {len(df):,} docs)"
                                ),
                                annotation_position="top right",
                            )
                        st.plotly_chart(fig, width="stretch")
                        st.caption("Document word counts with global average reference line")

                with col4:
                    if "year" in country_df.columns and len(country_df):
                        mt_country = model_shift_table(country_df)
                        if len(mt_country):
                            by_year = (
                                mt_country.groupby("year")[["medical", "rights"]]
                                .sum()
                                .reset_index()
                                .sort_values("year")
                            )
                            by_year["total"] = by_year["medical"] + by_year["rights"]
                            by_year["Rights-Based %"] = (
                                by_year["rights"] / by_year["total"] * 100
                            ).round(1)
                            by_year["Medical %"] = (
                                by_year["medical"] / by_year["total"] * 100
                            ).round(1)
                            by_year["year"] = by_year["year"].astype(int).astype(str)

                            _model_color_map = {
                                "Rights-Based %": MODEL_COLORS["Rights-Based"],
                                "Medical %": MODEL_COLORS["Medical Model"],
                            }

                            if len(by_year) < 6:
                                model_long = by_year.melt(
                                    id_vars=["year"],
                                    value_vars=["Rights-Based %", "Medical %"],
                                    var_name="Model",
                                    value_name="Share (%)",
                                )
                                fig = px.bar(
                                    model_long,
                                    x="year",
                                    y="Share (%)",
                                    color="Model",
                                    title=f"Model Language — {selected_country}",
                                    color_discrete_map=_model_color_map,
                                    labels={"year": "Year"},
                                    barmode="group",
                                )
                            else:
                                model_long = by_year.melt(
                                    id_vars=["year"],
                                    value_vars=["Rights-Based %", "Medical %"],
                                    var_name="Model",
                                    value_name="Share (%)",
                                )
                                fig = px.area(
                                    model_long,
                                    x="year",
                                    y="Share (%)",
                                    color="Model",
                                    title=f"Model Language Evolution — {selected_country}",
                                    color_discrete_map=_model_color_map,
                                    labels={"year": "Year"},
                                )

                            fig.update_layout(
                                yaxis_range=[0, 100],
                                legend_title_text="Language Model",
                                legend=dict(
                                    orientation="h",
                                    yanchor="top",
                                    y=-0.25,
                                    xanchor="center",
                                    x=0.5,
                                ),
                            )
                            st.plotly_chart(fig, width="stretch")
                            st.caption("Percentage of medical vs. rights-based keywords per year")
                        else:
                            st.info("No model language data available for this country.")
                    else:
                        st.info("Year data not available for model language analysis.")

        else:
            st.info("No countries available with current filters.")

    # Compare Countries
    elif default_tab == 3:
        # ── Uniform spacing for Compare Countries slots ──
        st.markdown(
            """
            <style>
            /* Slot headers: divider line + breathing room */
            div[data-testid="stVerticalBlock"] h4 {
                margin-top: 2rem !important;
                margin-bottom: 0.3rem !important;
                padding-top: 1.2rem !important;
                border-top: 1px solid #e2e6ed !important;
            }
            /* Captions directly after headers: minimal top gap */
            div[data-testid="stCaptionContainer"] {
                margin-top: -0.3rem !important;
                margin-bottom: 0.3rem !important;
            }
            /* Plotly charts: reduce top/bottom breathing room */
            div[data-testid="stPlotlyChart"] {
                margin-top: 0 !important;
                margin-bottom: 0 !important;
            }
            /* Radio buttons and toggles: compact */
            div[data-testid="stRadio"],
            div[data-testid="stCheckbox"] {
                margin-top: -0.3rem !important;
                margin-bottom: -0.3rem !important;
            }
            /* Custom HTML blocks (caveats, badges): tight */
            div[data-testid="stMarkdown"] > div > div > div.caveat-note {
                margin-top: -0.5rem !important;
            }
            /* Horizontal rules between major sections */
            hr {
                margin-top: 1rem !important;
                margin-bottom: 1rem !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        available_countries = sorted(df["country"].unique()) if len(df) else []

        if not available_countries or len(available_countries) < 2:
            st.info("Not enough country data available with current filters.")
        else:
            # ── Comparison mode ─────────────────────────────────────────────
            _mode_cards = {
                "Individual Countries": {
                    "icon": "public",
                    "desc": "Pick specific States Parties to compare side-by-side",
                    "color": CATEGORICAL_PALETTE[0],  # UN Blue
                },
                "Geographic Region": {
                    "icon": "map",
                    "desc": "Compare all States Parties within a UN region",
                    "color": CATEGORICAL_PALETTE[2],  # Bluish Green
                },
                "Organization": {
                    "icon": "groups",
                    "desc": "Compare members of ASEAN, EU, ECOWAS, and more",
                    "color": CATEGORICAL_PALETTE[3],  # Reddish Purple
                },
            }
            _mode_names = list(_mode_cards.keys())

            # Initialise session state for mode
            if "cmp_mode_idx" not in st.session_state:
                st.session_state["cmp_mode_idx"] = 0

            _card_cols = st.columns(3, gap="medium")
            for _ci, (_mode_name, _mc) in enumerate(
                zip(_mode_names, _mode_cards.values(), strict=False)
            ):
                with _card_cols[_ci]:
                    _is_active = st.session_state["cmp_mode_idx"] == _ci
                    _border_color = _mc["color"] if _is_active else "#e0e0e0"
                    _bg = f"{_mc['color']}0D" if _is_active else "#ffffff"
                    _icon_bg = _mc["color"] if _is_active else "#e8e8e8"
                    _icon_color = "#ffffff" if _is_active else "#666666"
                    _title_weight = "700" if _is_active else "600"
                    _shadow = f"0 2px 8px {_mc['color']}30" if _is_active else "0 1px 3px #00000010"

                    st.markdown(
                        f"<div style='border:2px solid {_border_color};"
                        f"border-radius:12px;padding:20px 16px;background:{_bg};"
                        f"box-shadow:{_shadow};text-align:center;"
                        f"min-height:140px;display:flex;flex-direction:column;"
                        f"align-items:center;justify-content:center;gap:8px;'>"
                        f"<span class='material-symbols-outlined' style='"
                        f"font-size:28px;color:{_icon_color};background:{_icon_bg};"
                        f"border-radius:50%;padding:10px;line-height:1;'>"
                        f"{_mc['icon']}</span>"
                        f"<div style='font-family:Inter,sans-serif;font-size:15px;"
                        f"font-weight:{_title_weight};color:#191C1F;'>"
                        f"{_mode_name}</div>"
                        f"<div style='font-family:Inter,sans-serif;font-size:12px;"
                        f"color:#5a6377;line-height:1.4;'>{_mc['desc']}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Select" if not _is_active else "Selected",
                        key=f"cmp_mode_btn_{_ci}",
                        width="stretch",
                        type="primary" if _is_active else "secondary",
                    ):
                        st.session_state["cmp_mode_idx"] = _ci
                        st.rerun()

            compare_mode = _mode_names[st.session_state["cmp_mode_idx"]]

            st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

            comparison_countries: list[str] = []
            primary_country = ""

            if compare_mode == "Individual Countries":
                _sel_cols = st.columns([2, 3])
                with _sel_cols[0]:
                    primary_country = st.selectbox(
                        "Primary country:",
                        options=available_countries,
                        index=0,
                        key="cmp_primary_country",
                    )
                with _sel_cols[1]:
                    comparison_options = [c for c in available_countries if c != primary_country]
                    comparison_countries = st.multiselect(
                        "Comparison countries:",
                        options=comparison_options,
                        default=comparison_options[:1] if comparison_options else [],
                        key="cmp_comparison_countries",
                    )

            elif compare_mode == "Geographic Region":
                _regions = sorted(df["region"].dropna().unique())
                _reg_cols = st.columns([2, 3])
                with _reg_cols[0]:
                    primary_region = st.selectbox(
                        "Primary region:",
                        options=_regions,
                        index=0,
                        key="cmp_geo_primary",
                    )
                with _reg_cols[1]:
                    _cmp_region_opts = [r for r in _regions if r != primary_region]
                    comparison_regions = st.multiselect(
                        "Comparison regions:",
                        options=_cmp_region_opts,
                        default=[],
                        key="cmp_geo_comparison",
                    )
                _all_regions = [primary_region, *comparison_regions]
                _region_countries = sorted(df[df["region"].isin(_all_regions)]["country"].unique())
                if _region_countries:
                    # Primary region countries first, then comparison
                    _primary_rc = sorted(df[df["region"] == primary_region]["country"].unique())
                    _comparison_rc = (
                        sorted(df[df["region"].isin(comparison_regions)]["country"].unique())
                        if comparison_regions
                        else []
                    )
                    primary_country = _primary_rc[0] if _primary_rc else ""
                    comparison_countries = _primary_rc[1:] + _comparison_rc
                _region_label = " vs ".join(_all_regions)
                _n_primary = df[df["region"] == primary_region]["country"].nunique()
                _n_comparison = (
                    df[df["region"].isin(comparison_regions)]["country"].nunique()
                    if comparison_regions
                    else 0
                )
                st.caption(
                    f"{primary_region} ({_n_primary} States Parties)"
                    + (
                        f" vs {', '.join(comparison_regions)} ({_n_comparison} States Parties)"
                        if comparison_regions
                        else ""
                    )
                )

            else:  # Organization
                _orgs = get_custom_organizations()
                _org_names = sorted(_orgs.keys())
                _org_cols = st.columns([2, 3])
                with _org_cols[0]:
                    primary_org = st.selectbox(
                        "Primary organization:",
                        options=_org_names,
                        index=0,
                        key="cmp_org_primary",
                    )
                with _org_cols[1]:
                    _cmp_org_opts = [o for o in _org_names if o != primary_org]
                    comparison_orgs = st.multiselect(
                        "Comparison organizations:",
                        options=_cmp_org_opts,
                        default=[],
                        key="cmp_org_comparison",
                    )
                _all_orgs = [primary_org, *comparison_orgs]
                _org_iso3s: set[str] = set()
                for _o in _all_orgs:
                    _org_iso3s.update(_orgs[_o])
                # Primary org countries first, then comparison
                _primary_oc = sorted(
                    df[df["iso3"].isin(set(_orgs[primary_org]))]["country"].unique()
                )
                _cmp_org_iso3s: set[str] = set()
                for _o in comparison_orgs:
                    _cmp_org_iso3s.update(_orgs[_o])
                _comparison_oc = (
                    sorted(df[df["iso3"].isin(_cmp_org_iso3s)]["country"].unique())
                    if comparison_orgs
                    else []
                )
                if _primary_oc:
                    primary_country = _primary_oc[0]
                    comparison_countries = _primary_oc[1:] + _comparison_oc
                _n_primary_org = len(_primary_oc)
                _n_cmp_org = len(_comparison_oc)
                st.caption(
                    f"{primary_org} ({_n_primary_org} States Parties)"
                    + (
                        f" vs {', '.join(comparison_orgs)} ({_n_cmp_org} States Parties)"
                        if comparison_orgs
                        else ""
                    )
                )

            if not comparison_countries:
                st.info("Select at least one comparison country to begin.")
            else:
                all_countries = [primary_country, *comparison_countries]
                cmp_df = df[df["country"].isin(all_countries)]

                # ── Shared computation ───────────────────────────────────────
                metric_keys = [
                    "Rights-Based Language %",
                    "Documents Submitted",
                    "Avg Document Length (words)",
                    "Article Coverage Breadth",
                    "CO Response Rate %",
                ]
                palette_colors = COMPARE_PALETTE
                palette_patterns = ["", "/", "x", ".", "\\"]
                country_style = {
                    c: {
                        "color": palette_colors[i % len(palette_colors)],
                        "pattern": palette_patterns[i % len(palette_patterns)],
                    }
                    for i, c in enumerate(all_countries)
                }

                # Compute current metrics for selected + all countries
                metrics_current = {
                    c: _country_metrics(c, None, None, df, ARTICLE_PRESETS) for c in all_countries
                }
                _all_metrics = {
                    c: _country_metrics(c, None, None, df, ARTICLE_PRESETS)
                    for c in available_countries
                }

                # Percentile ranks (Hazen method)
                _all_values = {
                    m: [_all_metrics[c][m] for c in available_countries] for m in metric_keys
                }
                _n_all = len(available_countries)
                _percentiles = {}
                for c in all_countries:
                    _percentiles[c] = {}
                    for m in metric_keys:
                        vals = _all_values[m]
                        _val = _all_metrics[c][m]
                        _below = sum(1 for v in vals if v < _val)
                        _equal = sum(1 for v in vals if v == _val)
                        _percentiles[c][m] = round((_below + 0.5 * _equal) / _n_all * 100, 1)

                # ── Narrative header (individual mode only) ────────────────
                st.markdown("---")
                if compare_mode == "Individual Countries":
                    if len(comparison_countries) == 1:
                        comparison_label = f"**{comparison_countries[0]}**"
                    else:
                        comparison_label = (
                            ", ".join(f"**{c}**" for c in comparison_countries[:-1])
                            + f", and **{comparison_countries[-1]}**"
                        )
                    st.markdown(f"### Comparing **{primary_country}** with {comparison_label}")
                    _primary_m = metrics_current[primary_country]
                    _narrative_parts = []
                    for c in comparison_countries:
                        _cm = metrics_current[c]
                        _diffs = []
                        if (
                            _cm["Rights-Based Language %"]
                            > _primary_m["Rights-Based Language %"] + 5
                        ):
                            _diffs.append("stronger rights-based framing")
                        elif (
                            _cm["Rights-Based Language %"]
                            < _primary_m["Rights-Based Language %"] - 5
                        ):
                            _diffs.append("weaker rights-based framing")
                        if _cm["Documents Submitted"] > _primary_m["Documents Submitted"]:
                            _diffs.append("more documents submitted")
                        elif _cm["Documents Submitted"] < _primary_m["Documents Submitted"]:
                            _diffs.append("fewer documents submitted")
                        if (
                            _cm["Article Coverage Breadth"]
                            > _primary_m["Article Coverage Breadth"] + 3
                        ):
                            _diffs.append("broader article coverage")
                        if _diffs:
                            _narrative_parts.append(f"**{c}** shows {', '.join(_diffs)}")
                    if _narrative_parts:
                        st.markdown(
                            f"Compared to {primary_country}: " + "; ".join(_narrative_parts) + "."
                        )

                # ── Determine group mode (used by all slots below) ────────
                _use_regional_radar = compare_mode in (
                    "Geographic Region",
                    "Organization",
                )
                _radar_groups: dict[str, list[str]] = {}
                if _use_regional_radar:
                    if compare_mode == "Geographic Region":
                        _radar_groups = {
                            r: sorted(
                                df[(df["region"] == r) & (df["country"].isin(all_countries))][
                                    "country"
                                ].unique()
                            )
                            for r in [primary_region, *comparison_regions]
                        }
                    else:  # Organization
                        for _o in [primary_org, *comparison_orgs]:
                            _o_iso3s = set(_orgs[_o])
                            _radar_groups[_o] = sorted(
                                df[
                                    (df["iso3"].isin(_o_iso3s))
                                    & (df["country"].isin(all_countries))
                                ]["country"].unique()
                            )

                # ════════════════════════════════════════════════════════════
                # SLOT 1: Summary Scorecard
                # ════════════════════════════════════════════════════════════
                st.markdown("#### Summary Scorecard")
                _stats = get_dataset_stats()

                if _use_regional_radar:
                    # ── Aggregated group-level scorecard ──
                    _group_names = list(_radar_groups.keys())
                    _n_members_total = sum(len(gc) for gc in _radar_groups.values())
                    if compare_mode == "Geographic Region":
                        _all_sel = [primary_region, *comparison_regions]
                    else:
                        _all_sel = [primary_org, *comparison_orgs]
                    _sc_description = (
                        f"Aggregated metrics for "
                        f"{' vs '.join(_all_sel)} "
                        f"({_n_members_total} States Parties total)."
                    )
                    st.caption(_sc_description)

                    _sc_cols = [
                        ("Group", "left"),
                        ("States Parties", "right"),
                        ("Documents", "right"),
                        ("Document Types", "right"),
                        ("Avg. Word Count", "right"),
                        ("Rights-Based %", "right"),
                        ("Articles Referenced", "right"),
                        ("Concluding Observations Rate", "right"),
                        ("Year Range", "center"),
                    ]
                    _sc_rows = []
                    for grp_name in _group_names:
                        grp_countries = _radar_groups[grp_name]
                        grp_df = cmp_df[cmp_df["country"].isin(grp_countries)]
                        if grp_df.empty:
                            continue
                        _n_members = grp_df["country"].nunique()
                        _n_docs = len(grp_df)
                        _n_dtypes = grp_df["doc_type"].nunique()
                        _avg_wc = (
                            int(grp_df["word_count"].mean())
                            if "word_count" in grp_df.columns
                            else 0
                        )
                        # Rights-based %
                        _mt = model_shift_table(grp_df)
                        if len(_mt):
                            _r = _mt["rights"].sum()
                            _m = _mt["medical"].sum()
                            _rights_pct = round(_r / (_r + _m) * 100, 1) if (_r + _m) > 0 else 0.0
                        else:
                            _rights_pct = 0.0
                        # Article breadth (mean across members)
                        _breadths = []
                        for _gc in grp_countries:
                            _gc_df = grp_df[grp_df["country"] == _gc]
                            if not _gc_df.empty:
                                _af = article_frequency(_gc_df, ARTICLE_PRESETS)
                                _breadths.append(len(_af[_af["count"] > 0]) if not _af.empty else 0)
                        _avg_breadth = int(sum(_breadths) / len(_breadths)) if _breadths else 0
                        # CO rate
                        _sr_c = set(
                            grp_df[grp_df["doc_type"] == "State Report"]["country"].unique()
                        )
                        _co_c = set(
                            grp_df[grp_df["doc_type"] == "Concluding Observations"][
                                "country"
                            ].unique()
                        )
                        _co_rate = round(len(_sr_c & _co_c) / len(_sr_c) * 100, 1) if _sr_c else 0.0
                        # Year range
                        _yr_min_g = int(grp_df["year"].min())
                        _yr_max_g = int(grp_df["year"].max())
                        _yr_range = f"{_yr_min_g}\u2013{_yr_max_g}"
                        _sc_rows.append(
                            [
                                grp_name,
                                _n_members,
                                _n_docs,
                                _n_dtypes,
                                _avg_wc,
                                _rights_pct,
                                _avg_breadth,
                                _co_rate,
                                _yr_range,
                            ]
                        )
                    _sc_col_names = [h for h, _ in _sc_cols]
                    _sc_df = pd.DataFrame(_sc_rows, columns=_sc_col_names)
                    _table_caption = (
                        f"Scorecard for {' vs '.join(_all_sel)} ({_n_members_total} States Parties)"
                    )
                    render_accessible_table(
                        _sc_df,
                        caption=_table_caption,
                        sortable=True,
                        sort_key="cmp_scorecard_sort",
                        searchable=True,
                        search_key="cmp_scorecard_search",
                    )
                else:
                    # ── Individual country scorecard (unchanged) ──
                    _sc_description = (
                        f"Comparing {len(all_countries)} States Parties. "
                        f"Percentile ranks are computed across all "
                        f"{_n_all} States Parties using the Hazen method."
                    )
                    st.caption(_sc_description)

                    def _ordinal(n):
                        """Return ordinal string."""
                        n = int(n)
                        if 11 <= (n % 100) <= 13:
                            return f"{n}th"
                        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
                        return f"{n}{suffix}"

                    _sc_cols = [
                        ("State Party", "left"),
                        ("Documents", "right"),
                        ("Document Types", "right"),
                        ("Avg. Word Count", "right"),
                        ("Rights-Based %", "right"),
                        ("Articles Referenced", "right"),
                        ("Concluding Observations Rate", "right"),
                        ("Year Range", "center"),
                        ("Rights Percentile", "right"),
                        ("Documents Percentile", "right"),
                        ("Breadth Percentile", "right"),
                    ]
                    _sc_rows = []
                    for c in all_countries:
                        m = metrics_current[c]
                        _sc_rows.append(
                            [
                                c,
                                int(m["Documents Submitted"]),
                                int(m["_doc_types"]),
                                int(m["Avg Document Length (words)"]),
                                round(m["Rights-Based Language %"], 1),
                                int(m["Article Coverage Breadth"]),
                                round(m["CO Response Rate %"], 1),
                                m["_year_range"],
                                round(_percentiles[c]["Rights-Based Language %"]),
                                round(_percentiles[c]["Documents Submitted"]),
                                round(_percentiles[c]["Article Coverage Breadth"]),
                            ]
                        )
                    _sc_col_names = [h for h, _ in _sc_cols]
                    _sc_df = pd.DataFrame(_sc_rows, columns=_sc_col_names)
                    _table_caption = (
                        f"Comparison scorecard for {primary_country} and "
                        f"{len(comparison_countries)} peer States Parties "
                        f"(n={len(all_countries)})"
                    )
                    render_accessible_table(
                        _sc_df,
                        caption=_table_caption,
                        page_size=10,
                        page_key="cmp_scorecard_page",
                        sortable=True,
                        sort_key="cmp_scorecard_sort",
                        searchable=True,
                        search_key="cmp_scorecard_search",
                    )
                st.caption(f"Data current through {_stats['year_max']}.")

                # ════════════════════════════════════════════════════════════
                # SLOT 2: Article Coverage Radar
                # ════════════════════════════════════════════════════════════
                st.markdown("#### Article Coverage Radar")
                st.caption(
                    "Top CRPD articles by reference count. Each spoke "
                    "shows raw keyword mentions. Wider shapes = broader "
                    "thematic coverage."
                )
                _exclude_art1_radar = st.toggle(
                    "Exclude Article 1 (Purpose)",
                    value=True,
                    key="cmp_radar_excl_art1",
                    help="Article 1 dominates; toggle off to reveal other articles.",
                )
                if _use_regional_radar:
                    _radar_frames = []
                    for grp_name, grp_countries in _radar_groups.items():
                        grp_df = cmp_df[cmp_df["country"].isin(grp_countries)]
                        af = article_frequency(grp_df, ARTICLE_PRESETS)
                        if not af.empty:
                            af = af.copy()
                            if _exclude_art1_radar:
                                af = af[~af["article"].str.startswith("Article 1 ")]
                            af["group"] = grp_name
                            _radar_frames.append(af)

                    if _radar_frames:
                        _radar_all = pd.concat(_radar_frames)
                        _top12 = (
                            _radar_all.groupby("article")["count"].sum().nlargest(12).index.tolist()
                        )
                        _radar_filt = _radar_all[_radar_all["article"].isin(_top12)]
                        _short_map = {
                            a: (f"Art. {a.split('—')[0].strip().split()[-1]}" if "—" in a else a)
                            for a in _top12
                        }
                        fig_radar = go.Figure()
                        _grp_palette = COMPARE_PALETTE
                        for gi, (grp_name, grp_countries) in enumerate(_radar_groups.items()):
                            _sub = _radar_filt[_radar_filt["group"] == grp_name]
                            _vals = []
                            _labels = []
                            for art in _top12:
                                row = _sub[_sub["article"] == art]
                                _vals.append(int(row["count"].sum()) if len(row) else 0)
                                _labels.append(_short_map[art])
                            _vals.append(_vals[0])
                            _labels.append(_labels[0])
                            _color = _grp_palette[gi % len(_grp_palette)]
                            fig_radar.add_trace(
                                go.Scatterpolar(
                                    r=_vals,
                                    theta=_labels,
                                    fill="toself",
                                    name=(f"{grp_name} (n={len(grp_countries)} States Parties)"),
                                    fillcolor=_color,
                                    opacity=0.2,
                                    line=dict(color=_color, width=2),
                                )
                            )
                        fig_radar.update_layout(
                            polar=dict(radialaxis=dict(visible=True)),
                            title="CRPD Article Reference Profiles by Region",
                            height=500,
                            font=dict(
                                family="'Inter', Arial, Helvetica, sans-serif",
                                size=13,
                            ),
                        )
                        st.plotly_chart(fig_radar, width="stretch")

                else:
                    # Individual countries mode — original behavior
                    _radar_frames = []
                    for c in all_countries:
                        af = article_frequency(cmp_df[cmp_df["country"] == c], ARTICLE_PRESETS)
                        if not af.empty:
                            af = af.copy()
                            if _exclude_art1_radar:
                                af = af[~af["article"].str.startswith("Article 1 ")]
                            af["country"] = c
                            _radar_frames.append(af)
                    if _radar_frames:
                        _radar_all = pd.concat(_radar_frames)
                        _top12 = (
                            _radar_all.groupby("article")["count"].sum().nlargest(12).index.tolist()
                        )
                        _radar_filt = _radar_all[_radar_all["article"].isin(_top12)]
                        _short_map = {
                            a: (f"Art. {a.split('—')[0].strip().split()[-1]}" if "—" in a else a)
                            for a in _top12
                        }
                        fig_radar = go.Figure()
                        for c in all_countries:
                            _sub = _radar_filt[_radar_filt["country"] == c]
                            _vals = []
                            _labels = []
                            for art in _top12:
                                row = _sub[_sub["article"] == art]
                                _vals.append(int(row["count"].sum()) if len(row) else 0)
                                _labels.append(_short_map[art])
                            _vals.append(_vals[0])
                            _labels.append(_labels[0])
                            style = country_style[c]
                            fig_radar.add_trace(
                                go.Scatterpolar(
                                    r=_vals,
                                    theta=_labels,
                                    fill="toself",
                                    name=(f"{c} (n={len(cmp_df[cmp_df['country'] == c])})"),
                                    fillcolor=style["color"],
                                    opacity=0.2,
                                    line=dict(color=style["color"], width=2),
                                )
                            )
                        fig_radar.update_layout(
                            polar=dict(radialaxis=dict(visible=True)),
                            title="CRPD Article Reference Profiles",
                            height=500,
                            font=dict(
                                family="'Inter', Arial, Helvetica, sans-serif",
                                size=13,
                            ),
                        )
                        st.plotly_chart(fig_radar, width="stretch")

                # ════════════════════════════════════════════════════════════
                # SLOT 3: Rights vs Medical Framing (stacked 100%)
                # ════════════════════════════════════════════════════════════
                st.markdown("#### Rights-Based vs. Medical Model Framing")
                st.caption(
                    "Proportion of rights-based vs. medical model keywords, "
                    "normalized to 100% to compare framing emphasis."
                )
                model_rows = []
                if _use_regional_radar:
                    # Aggregate by region/org group
                    for grp_name, grp_countries in _radar_groups.items():
                        grp_df = cmp_df[cmp_df["country"].isin(grp_countries)]
                        mt_g = model_shift_table(grp_df)
                        if len(mt_g):
                            _r = mt_g["rights"].sum()
                            _m = mt_g["medical"].sum()
                            _total = _r + _m
                            if _total > 0:
                                model_rows.append(
                                    {
                                        "Group": grp_name,
                                        "Rights-Based": round(_r / _total * 100, 1),
                                        "Medical Model": round(_m / _total * 100, 1),
                                        "_total": int(_total),
                                    }
                                )
                    _model_x_col = "Group"
                else:
                    for c in all_countries:
                        mt_c = model_shift_table(cmp_df[cmp_df["country"] == c])
                        if len(mt_c):
                            _r = mt_c["rights"].sum()
                            _m = mt_c["medical"].sum()
                            _total = _r + _m
                            if _total > 0:
                                model_rows.append(
                                    {
                                        "Group": c,
                                        "Rights-Based": round(_r / _total * 100, 1),
                                        "Medical Model": round(_m / _total * 100, 1),
                                        "_total": int(_total),
                                    }
                                )
                    _model_x_col = "Group"

                if model_rows:
                    model_df_full = pd.DataFrame(model_rows)
                    model_melt = model_df_full.melt(
                        id_vars=[_model_x_col, "_total"],
                        var_name="Model",
                        value_name="Share (%)",
                    )
                    fig_model = px.bar(
                        model_melt,
                        x=_model_x_col,
                        y="Share (%)",
                        color="Model",
                        barmode="stack",
                        title="Language Framing: Rights-Based vs. Medical (%)",
                        color_discrete_map={
                            "Rights-Based": MODEL_COLORS["Rights-Based"],
                            "Medical Model": MODEL_COLORS["Medical Model"],
                        },
                    )
                    fig_model.update_layout(
                        yaxis=dict(range=[0, 105], dtick=25),
                        font=dict(
                            family="'Inter', Arial, Helvetica, sans-serif",
                            size=13,
                        ),
                    )
                    for row in model_rows:
                        fig_model.add_annotation(
                            x=row[_model_x_col],
                            y=102,
                            text=f"n={row['_total']}",
                            showarrow=False,
                            font=dict(size=10, color="grey"),
                        )
                    st.plotly_chart(fig_model, width="stretch")
                else:
                    st.info("Not enough model-language data for selected countries.")

                # ════════════════════════════════════════════════════════════
                # SLOT 4: When States Parties Reported (stacked bar)
                # ════════════════════════════════════════════════════════════
                st.markdown("#### When States Parties Reported")

                # Doc type stack order (review cycle sequence)
                _dt_stack_order = [
                    "State Report",
                    "List of Issues (LOI)",
                    "Written Reply",
                    "Concluding Observations",
                    "Response to Concluding Observations",
                ]

                # Determine facet entities
                if _use_regional_radar:
                    _facet_entities = list(_radar_groups.keys())
                    _entity_label = (
                        "region"
                        if compare_mode == "Geographic Region"
                        else "intergovernmental bloc"
                    )
                    st.caption(
                        f"Documents submitted per year by {_entity_label} "
                        f"and document type. Empty bars indicate years with "
                        f"no submissions. Absence may reflect dataset "
                        f"coverage, not confirmed non-submission."
                    )
                else:
                    _facet_entities = all_countries
                    st.caption(
                        "Documents submitted per year by State Party "
                        "and document type. Empty bars indicate years with "
                        "no submissions. Absence may reflect dataset "
                        "coverage, not confirmed non-submission."
                    )

                _yr_min = int(cmp_df["year"].min())
                _yr_max = int(cmp_df["year"].max())
                _all_chart_years = list(range(_yr_min, _yr_max + 1))

                # ── Paginate: max 10 panels per page ──
                _page_size = 10
                _total_entities = len(_facet_entities)
                if _total_entities > _page_size:
                    _pk = "cmp_timeline_page"
                    _total_pages = (_total_entities + _page_size - 1) // _page_size
                    if _pk not in st.session_state:
                        st.session_state[_pk] = 0
                    _cur_page = max(0, min(st.session_state[_pk], _total_pages - 1))
                    _start = _cur_page * _page_size
                    _end = min(_start + _page_size, _total_entities)
                    _page_entities = _facet_entities[_start:_end]

                    # Pagination controls
                    _pc = st.columns([3, 1, 1])
                    with _pc[0]:
                        st.markdown(
                            f"<div style='font-size:13px;color:#555;"
                            f"padding:6px 0;font-family:Inter,sans-serif;'>"
                            f"Showing {_start + 1}–{_end} of "
                            f"{_total_entities}</div>",
                            unsafe_allow_html=True,
                        )
                    with _pc[1]:
                        if st.button(
                            "Previous",
                            key=f"{_pk}_prev",
                            disabled=_cur_page == 0,
                            width="stretch",
                        ):
                            st.session_state[_pk] = _cur_page - 1
                            st.rerun()
                    with _pc[2]:
                        if st.button(
                            "Next",
                            key=f"{_pk}_next",
                            disabled=_cur_page >= _total_pages - 1,
                            width="stretch",
                        ):
                            st.session_state[_pk] = _cur_page + 1
                            st.rerun()
                else:
                    _page_entities = _facet_entities

                _n_facets = len(_page_entities)

                fig_sub = make_subplots(
                    rows=_n_facets,
                    cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.06,
                )

                _legend_shown: set[str] = set()

                for fi, entity in enumerate(_page_entities):
                    _row = fi + 1
                    if _use_regional_radar:
                        _e_countries = _radar_groups[entity]
                        _e_df = cmp_df[cmp_df["country"].isin(_e_countries)]
                    else:
                        _e_df = cmp_df[cmp_df["country"] == entity]

                    for dt in _dt_stack_order:
                        _dt_df = _e_df[_e_df["doc_type"] == dt]
                        if _dt_df.empty:
                            _counts = [0] * len(_all_chart_years)
                        else:
                            _yr_counts = (
                                _dt_df.groupby("year")
                                .size()
                                .reindex(_all_chart_years, fill_value=0)
                            )
                            _counts = _yr_counts.tolist()

                        _show = dt not in _legend_shown
                        _legend_shown.add(dt)

                        fig_sub.add_trace(
                            go.Bar(
                                x=_all_chart_years,
                                y=_counts,
                                name=dt,
                                marker_color=DOC_TYPE_COLORS.get(dt, "#999999"),
                                legendgroup=dt,
                                showlegend=_show,
                                hovertemplate=(
                                    f"<b>{entity}</b><br>"
                                    f"{dt}<br>"
                                    "Year: %{x}<br>"
                                    "Documents: %{y}"
                                    "<extra></extra>"
                                ),
                            ),
                            row=_row,
                            col=1,
                        )

                    # Entity label: horizontal, left of panel, vertically centered
                    _yref = f"y{_row} domain" if _row > 1 else "y domain"
                    fig_sub.add_annotation(
                        text=f"<b>{entity}</b>",
                        xref="paper",
                        yref=_yref,
                        x=-0.01,
                        y=0.5,
                        xanchor="right",
                        yanchor="middle",
                        showarrow=False,
                        font=dict(size=12, color="#333"),
                        textangle=0,
                    )

                fig_sub.update_layout(
                    barmode="stack",
                    height=max(250, 120 * _n_facets),
                    plot_bgcolor="white",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=12),
                    ),
                    font=dict(
                        family="'Inter', Arial, Helvetica, sans-serif",
                        size=13,
                    ),
                    margin=dict(t=50, l=120),
                )

                # Remove subplot_titles clutter — we use annotations instead
                for ann in fig_sub.layout.annotations:
                    if ann.text in _page_entities:
                        ann.text = ""

                # X-axis: show on bottom panel only
                fig_sub.update_xaxes(
                    dtick=2,
                    range=[_yr_min - 0.5, _yr_max + 0.5],
                    row=_n_facets,
                    col=1,
                    title_text="Year",
                )
                # Y-axes: clean — no labels, no ticks, just bar height
                for fi in range(1, _n_facets + 1):
                    fig_sub.update_yaxes(
                        showticklabels=False,
                        showgrid=False,
                        rangemode="tozero",
                        row=fi,
                        col=1,
                    )

                st.plotly_chart(fig_sub, width="stretch")

                # ════════════════════════════════════════════════════════════
                # SLOT 5: Rights-Based vs. Medical Keyword Balance (dual-view)
                # ════════════════════════════════════════════════════════════
                st.markdown(
                    "<h4 style='margin:0 0 0.3rem 0;"
                    "font-family:Inter,sans-serif;'>"
                    "Rights-Based vs. Medical Keyword Balance</h4>",
                    unsafe_allow_html=True,
                )

                # ── Compute rights % per entity per year ──
                _rt_entity_col = "Group" if _use_regional_radar else "Entity"
                _rights_trend_rows: list[dict] = []

                if _use_regional_radar:
                    for grp_name, grp_countries in _radar_groups.items():
                        grp_df = cmp_df[cmp_df["country"].isin(grp_countries)]
                        for yr in sorted(grp_df["year"].dropna().unique().astype(int)):
                            _yr_df = grp_df[grp_df["year"] == yr]
                            mt_yr = model_shift_table(_yr_df)
                            if len(mt_yr):
                                _r = mt_yr["rights"].sum()
                                _m = mt_yr["medical"].sum()
                                _t = _r + _m
                                if _t > 0:
                                    _rights_trend_rows.append(
                                        {
                                            _rt_entity_col: grp_name,
                                            "Year": int(yr),
                                            "Rights %": round(_r / _t * 100, 1),
                                            "n_docs": len(_yr_df),
                                        }
                                    )
                else:
                    for c in all_countries:
                        _c_df = cmp_df[cmp_df["country"] == c]
                        for yr in sorted(_c_df["year"].dropna().unique().astype(int)):
                            _yr_df = _c_df[_c_df["year"] == yr]
                            mt_yr = model_shift_table(_yr_df)
                            if len(mt_yr):
                                _r = mt_yr["rights"].sum()
                                _m = mt_yr["medical"].sum()
                                _t = _r + _m
                                if _t > 0:
                                    _rights_trend_rows.append(
                                        {
                                            _rt_entity_col: c,
                                            "Year": int(yr),
                                            "Rights %": round(_r / _t * 100, 1),
                                            "n_docs": len(_yr_df),
                                        }
                                    )

                if not _rights_trend_rows:
                    st.info("Not enough data for rights trajectory.")
                else:
                    _rt_df = pd.DataFrame(_rights_trend_rows)

                    # ── Build dumbbell data: earliest vs latest per entity ──
                    _dumbbell_rows: list[dict] = []
                    for entity in _rt_df[_rt_entity_col].unique():
                        _e_df = _rt_df[_rt_df[_rt_entity_col] == entity].sort_values("Year")
                        if len(_e_df) < 1:
                            continue
                        _first = _e_df.iloc[0]
                        _last = _e_df.iloc[-1]
                        _delta = round(_last["Rights %"] - _first["Rights %"], 1)
                        _dumbbell_rows.append(
                            {
                                _rt_entity_col: entity,
                                "Start %": _first["Rights %"],
                                "End %": _last["Rights %"],
                                "Start Year": int(_first["Year"]),
                                "End Year": int(_last["Year"]),
                                "Delta": _delta,
                                "n_points": len(_e_df),
                            }
                        )
                    _db_df = pd.DataFrame(_dumbbell_rows).sort_values("Delta", ascending=True)

                    # ── View toggle (inline) ──
                    st.markdown(
                        "<style>#cmp_rights_view label:first-of-type {display:none;}</style>",
                        unsafe_allow_html=True,
                    )
                    _vt_cols = st.columns([0.4, 4], gap="small")
                    with _vt_cols[0]:
                        st.markdown(
                            "<div style='font-size:14px;font-weight:600;"
                            "font-family:Inter,sans-serif;padding-top:8px;'>"
                            "View:</div>",
                            unsafe_allow_html=True,
                        )
                    with _vt_cols[1]:
                        _rt_view = st.radio(
                            "View:",
                            ["Full Timeline", "Direction of Change"],
                            horizontal=True,
                            key="cmp_rights_view",
                            label_visibility="collapsed",
                        )

                    if _rt_view == "Direction of Change":
                        # ── DUMBBELL CHART ──
                        st.caption(
                            "Change in rights-based keyword share from "
                            "earliest to latest document. Green = increase, "
                            "red = decrease. Changes < 5 pp are within "
                            "measurement variability."
                        )
                        fig_db = go.Figure()

                        for _, row in _db_df.iterrows():
                            _name = row[_rt_entity_col]
                            _delta = row["Delta"]
                            if _delta > 1:
                                _color = TREND_COLORS["up"]
                            elif _delta < -1:
                                _color = TREND_COLORS["down"]
                            else:
                                _color = TREND_COLORS["neutral"]

                            # Connecting line
                            fig_db.add_trace(
                                go.Scatter(
                                    x=[row["Start %"], row["End %"]],
                                    y=[_name, _name],
                                    mode="lines",
                                    line=dict(color=_color, width=3),
                                    showlegend=False,
                                    hoverinfo="skip",
                                )
                            )
                            # Start dot (hollow)
                            fig_db.add_trace(
                                go.Scatter(
                                    x=[row["Start %"]],
                                    y=[_name],
                                    mode="markers",
                                    marker=dict(
                                        size=10,
                                        color="white",
                                        line=dict(color=_color, width=2),
                                    ),
                                    showlegend=False,
                                    hovertemplate=(
                                        f"<b>{_name}</b> — "
                                        f"{int(row['Start Year'])}<br>"
                                        f"Rights-Based: "
                                        f"{row['Start %']:.1f}%"
                                        "<extra></extra>"
                                    ),
                                )
                            )
                            # End dot (filled)
                            fig_db.add_trace(
                                go.Scatter(
                                    x=[row["End %"]],
                                    y=[_name],
                                    mode="markers",
                                    marker=dict(
                                        size=10,
                                        color=_color,
                                    ),
                                    showlegend=False,
                                    hovertemplate=(
                                        f"<b>{_name}</b> — "
                                        f"{int(row['End Year'])}<br>"
                                        f"Rights-Based: "
                                        f"{row['End %']:.1f}%"
                                        "<extra></extra>"
                                    ),
                                )
                            )
                            # Delta annotation
                            _annot_x = max(row["Start %"], row["End %"]) + 1.5
                            _sign = "+" if _delta > 0 else ""
                            fig_db.add_annotation(
                                x=_annot_x,
                                y=_name,
                                text=(
                                    f"{_sign}{_delta:.1f} pp"
                                    f" ({int(row['Start Year'])}–"
                                    f"{int(row['End Year'])})"
                                ),
                                showarrow=False,
                                font=dict(size=11, color=_color),
                                xanchor="left",
                            )

                        fig_db.update_layout(
                            title=("Direction of Change in Rights-Based Language"),
                            xaxis_title="Rights-Based Share (%)",
                            xaxis=dict(range=[0, 105]),
                            height=max(300, 50 * len(_db_df)),
                            plot_bgcolor="white",
                            font=dict(
                                family=("'Inter', Arial, Helvetica, sans-serif"),
                                size=13,
                            ),
                            margin=dict(r=160, t=30, b=10),
                        )
                        st.plotly_chart(fig_db, width="stretch")

                    else:
                        # ── DOT PLOT with true temporal axis ──
                        st.caption(
                            "Each dot represents one or more documents in "
                            "a given year. Lines connect observations "
                            "within 2 years of each other. Keyword-based "
                            "measurement — changes < 5 pp may be noise."
                        )
                        _all_years = sorted(_rt_df["Year"].unique().astype(int))
                        fig_dot = go.Figure()

                        _entities = (
                            list(_radar_groups.keys()) if _use_regional_radar else all_countries
                        )
                        _dot_palette = COMPARE_PALETTE

                        for ei, entity in enumerate(_entities):
                            _sub = (
                                _rt_df[_rt_df[_rt_entity_col] == entity].sort_values("Year").copy()
                            )
                            if _sub.empty:
                                continue
                            _color = _dot_palette[ei % len(_dot_palette)]
                            _n_pts = len(_sub)

                            # Markers for all points
                            fig_dot.add_trace(
                                go.Scatter(
                                    x=_sub["Year"],
                                    y=_sub["Rights %"],
                                    mode="markers",
                                    name=f"{entity} ({_n_pts} pts)",
                                    marker=dict(
                                        size=_sub["n_docs"] * 2 + 6,
                                        color=_color,
                                    ),
                                    hovertemplate=(
                                        f"<b>{entity}</b><br>"
                                        "Year: %{x}<br>"
                                        "Rights: %{y:.1f}%<br>"
                                        "Documents: %{text}"
                                        "<extra></extra>"
                                    ),
                                    text=_sub["n_docs"].tolist(),
                                    legendgroup=entity,
                                )
                            )

                            # Lines only where year gap <= 2
                            _years = _sub["Year"].tolist()
                            _vals = _sub["Rights %"].tolist()
                            for i in range(len(_years) - 1):
                                if _years[i + 1] - _years[i] <= 2:
                                    fig_dot.add_trace(
                                        go.Scatter(
                                            x=[_years[i], _years[i + 1]],
                                            y=[_vals[i], _vals[i + 1]],
                                            mode="lines",
                                            line=dict(
                                                color=_color,
                                                width=1.5,
                                                dash="dot",
                                            ),
                                            showlegend=False,
                                            hoverinfo="skip",
                                            legendgroup=entity,
                                        )
                                    )

                        fig_dot.update_layout(
                            title="",
                            xaxis_title="Year",
                            yaxis_title="Rights-Based Share (%)",
                            height=340,
                            plot_bgcolor="white",
                            margin=dict(t=30, b=10),
                            xaxis=dict(
                                dtick=1,
                                tickangle=0,
                                range=[
                                    min(_all_years) - 0.5,
                                    max(_all_years) + 0.5,
                                ],
                            ),
                            yaxis=dict(dtick=5),
                            font=dict(
                                family=("'Inter', Arial, Helvetica, sans-serif"),
                                size=13,
                            ),
                        )
                        st.plotly_chart(fig_dot, width="stretch")

                    # ── Methodology caveat ──
                    st.markdown(
                        "<div class='caveat-note' style='font-size:12px;margin-top:-1rem;"
                        "color:#666;padding:0;"
                        "font-family:Inter,sans-serif;'>"
                        "Classification uses keyword frequency matching "
                        "(30 medical-model terms, 27 rights-based terms). "
                        "Percentages mix document types — Committee-authored "
                        "documents use rights-based language by institutional "
                        "mandate."
                        "</div>",
                        unsafe_allow_html=True,
                    )

                # ════════════════════════════════════════════════════════════
                # SLOT 6: Distinctive Language (TF-IDF diverging bar)
                # ════════════════════════════════════════════════════════════
                if _use_regional_radar:
                    _dl_label = "Group" if compare_mode == "Geographic Region" else "Organization"
                    st.markdown(f"#### Distinctive Language by {_dl_label}")
                    st.caption(
                        "Terms ranked by keyness (log-ratio vs full corpus). "
                        "Higher scores mean the term is disproportionately "
                        f"frequent in this {_dl_label.lower()}'s documents."
                    )
                    _has_any_terms = False
                    _group_names = list(_radar_groups.keys())
                    _kw_cols = st.columns(len(_group_names))
                    for ci, grp_name in enumerate(_group_names):
                        grp_countries = _radar_groups[grp_name]
                        _g_df = cmp_df[cmp_df["country"].isin(grp_countries)]
                        if len(_g_df) == 0:
                            continue
                        _dt = extract_distinctive_terms(_g_df, df, top_n=10)
                        with _kw_cols[ci]:
                            st.markdown(
                                f"**{grp_name}** "
                                f"<span style='color:grey;font-size:0.8em;'>"
                                f"({len(_g_df)} docs, "
                                f"{_g_df['country'].nunique()} States Parties)"
                                f"</span>",
                                unsafe_allow_html=True,
                            )
                            if not _dt.empty:
                                _has_any_terms = True
                                _kw_table = _dt.rename(
                                    columns={
                                        "term": "Term",
                                        "freq": "Freq",
                                        "keyness": "Keyness",
                                    }
                                )
                                render_accessible_table(
                                    _kw_table,
                                    caption=f"Distinctive terms for {grp_name}",
                                )
                            else:
                                st.caption("No distinctive terms found.")
                    if not _has_any_terms:
                        st.info("Not enough text data for keyword comparison.")
                else:
                    st.markdown("#### Distinctive Language by Country")
                    st.caption(
                        "Terms ranked by keyness (log-ratio vs full corpus). "
                        "Higher scores mean the term is disproportionately "
                        "frequent in this country's documents."
                    )
                    _has_any_terms = False
                    _kw_cols = st.columns(len(all_countries))
                    for ci, c in enumerate(all_countries):
                        _c_df = cmp_df[cmp_df["country"] == c]
                        if len(_c_df) == 0:
                            continue
                        _dt = extract_distinctive_terms(_c_df, df, top_n=10)
                        with _kw_cols[ci]:
                            st.markdown(
                                f"**{c}** "
                                f"<span style='color:grey;font-size:0.8em;'>"
                                f"({len(_c_df)} docs)"
                                f"</span>",
                                unsafe_allow_html=True,
                            )
                            if not _dt.empty:
                                _has_any_terms = True
                                _kw_table = _dt.rename(
                                    columns={
                                        "term": "Term",
                                        "freq": "Freq",
                                        "keyness": "Keyness",
                                    }
                                )
                                render_accessible_table(
                                    _kw_table,
                                    caption=f"Distinctive terms for {c}",
                                )
                            else:
                                st.caption("No distinctive terms found.")
                    if not _has_any_terms:
                        st.info("Not enough text data for keyword comparison.")

                # ════════════════════════════════════════════════════════════
                # SLOT 7: Article Coverage Gap Matrix (binary heatmap)
                # ════════════════════════════════════════════════════════════
                st.markdown("#### Article Coverage Gap Matrix")

                def _art_sort_key(a):
                    _m = re.search(r"Article\s+(\d+)", a)
                    return int(_m.group(1)) if _m else 999

                if _use_regional_radar:
                    st.caption(
                        "Which CRPD articles at least one member of each "
                        "group references (green) vs. none mention (red). "
                        "Gaps = advocacy opportunities."
                    )
                    _gap_frames = []
                    for grp_name, grp_countries in _radar_groups.items():
                        grp_df = cmp_df[cmp_df["country"].isin(grp_countries)]
                        af = article_frequency(grp_df, ARTICLE_PRESETS)
                        if not af.empty:
                            af = af.copy()
                            af["group"] = grp_name
                            _gap_frames.append(af)
                    if _gap_frames:
                        _gap_all = pd.concat(_gap_frames)
                        _gap_pivot = _gap_all.pivot_table(
                            index="group",
                            columns="article",
                            values="count",
                            fill_value=0,
                        )
                        _gap_binary = (_gap_pivot > 0).astype(int)
                        _sorted_cols = sorted(_gap_binary.columns, key=_art_sort_key)
                        _gap_binary = _gap_binary[_sorted_cols]
                        _short_art = [
                            (f"Art. {a.split('—')[0].strip().split()[-1]}" if "—" in a else a)
                            for a in _gap_binary.columns
                        ]
                        _coverage_pct = _gap_binary.sum(axis=1) / _gap_binary.shape[1] * 100
                        _group_labels = [
                            f"{g} ({_coverage_pct[g]:.0f}%)" for g in _gap_binary.index
                        ]
                        fig_gap = go.Figure(
                            data=go.Heatmap(
                                z=_gap_binary.values,
                                x=_short_art,
                                y=_group_labels,
                                colorscale=[[0, "#FFCDD2"], [1, "#C8E6C9"]],
                                showscale=False,
                                text=_gap_binary.values,
                                texttemplate="%{text}",
                                hovertemplate="<b>%{y}</b><br>%{x}: %{text:d}<extra></extra>",
                            )
                        )
                        fig_gap.update_layout(
                            title="Article Coverage (1 = referenced, 0 = gap)",
                            height=max(250, 70 * len(_radar_groups)),
                            xaxis=dict(tickangle=-45),
                            font=dict(
                                family="'Inter', Arial, Helvetica, sans-serif",
                                size=11,
                            ),
                        )
                        st.plotly_chart(fig_gap, width="stretch")
                        st.caption(
                            "Percentage after group name = share of all "
                            "CRPD articles covered by at least one member. "
                            "Red cells are collective advocacy gaps."
                        )
                else:
                    st.caption(
                        "Which CRPD articles each country references (green) "
                        "vs. never mentions (red). Gaps = advocacy opportunities."
                    )
                    _gap_frames = []
                    for c in all_countries:
                        af = article_frequency(cmp_df[cmp_df["country"] == c], ARTICLE_PRESETS)
                        if not af.empty:
                            af = af.copy()
                            af["country"] = c
                            _gap_frames.append(af)
                    if _gap_frames:
                        _gap_all = pd.concat(_gap_frames)
                        _gap_pivot = _gap_all.pivot_table(
                            index="country",
                            columns="article",
                            values="count",
                            fill_value=0,
                        )
                        _gap_binary = (_gap_pivot > 0).astype(int)
                        _sorted_cols = sorted(_gap_binary.columns, key=_art_sort_key)
                        _gap_binary = _gap_binary[_sorted_cols]
                        _short_art = [
                            (f"Art. {a.split('—')[0].strip().split()[-1]}" if "—" in a else a)
                            for a in _gap_binary.columns
                        ]
                        _coverage_pct = _gap_binary.sum(axis=1) / _gap_binary.shape[1] * 100
                        fig_gap = go.Figure(
                            data=go.Heatmap(
                                z=_gap_binary.values,
                                x=_short_art,
                                y=[f"{c} ({_coverage_pct[c]:.0f}%)" for c in _gap_binary.index],
                                colorscale=[[0, "#FFCDD2"], [1, "#C8E6C9"]],
                                showscale=False,
                                text=_gap_binary.values,
                                texttemplate="%{text}",
                                hovertemplate="<b>%{y}</b><br>%{x}: %{text:d}<extra></extra>",
                            )
                        )
                        fig_gap.update_layout(
                            title="Article Coverage (1 = referenced, 0 = gap)",
                            height=max(250, 70 * len(all_countries)),
                            xaxis=dict(tickangle=-45),
                            font=dict(
                                family="'Inter', Arial, Helvetica, sans-serif",
                                size=11,
                            ),
                        )
                        st.plotly_chart(fig_gap, width="stretch")
                        st.caption(
                            "Percentage after country name = share of all "
                            "CRPD articles covered. Red cells are advocacy gaps."
                        )

                # ════════════════════════════════════════════════════════════
                # SLOT 8: Regional Peer Benchmarking (beeswarm)
                # ════════════════════════════════════════════════════════════
                if not _use_regional_radar:
                    st.markdown("#### Regional Peer Benchmarking")
                    # Collect unique regions from selected countries
                    _sel_regions = sorted(
                        df[df["country"].isin(all_countries)]["region"].dropna().unique()
                    )
                    _all_regions = sorted(df["region"].dropna().unique())
                    _default_region = _sel_regions[0] if _sel_regions else _all_regions[0]
                    _default_idx = (
                        _all_regions.index(_default_region)
                        if _default_region in _all_regions
                        else 0
                    )
                    _bench_region = st.selectbox(
                        "Benchmark against region:",
                        options=_all_regions,
                        index=_default_idx,
                        key="cmp_bench_region",
                        help="Compare selected countries against all peers in this region.",
                    )
                    st.caption(
                        f"Where selected countries fall among all "
                        f"{_bench_region} peers. Grey dots = other "
                        f"countries in the region; diamonds = your selection."
                    )
                    _region_df = df[df["region"] == _bench_region]
                    _region_countries = sorted(_region_df["country"].unique())
                    if len(_region_countries) >= 3:
                        _region_metrics = {
                            c: _country_metrics(c, None, None, df, ARTICLE_PRESETS)
                            for c in _region_countries
                        }
                        # Also compute for selected countries not in this region
                        _outside = [c for c in all_countries if c not in _region_metrics]
                        for c in _outside:
                            _region_metrics[c] = _all_metrics[c]
                        _bench_metrics = [
                            "Rights-Based Language %",
                            "Documents Submitted",
                            "Article Coverage Breadth",
                        ]
                        _bench_cols = st.columns(len(_bench_metrics))
                        for bidx, bm in enumerate(_bench_metrics):
                            with _bench_cols[bidx]:
                                _vals = [(_region_metrics[c][bm], c) for c in _region_countries]
                                fig_bench = go.Figure()
                                _bg_vals = [v[0] for v in _vals]
                                _bg_names = [v[1] for v in _vals]
                                fig_bench.add_trace(
                                    go.Box(
                                        y=_bg_vals,
                                        name=_bench_region,
                                        marker=dict(color="#E0E0E0"),
                                        boxpoints="all",
                                        jitter=0.3,
                                        pointpos=0,
                                        text=_bg_names,
                                        hovertemplate="%{text}: %{y}<extra></extra>",
                                        line=dict(color="#BDBDBD"),
                                        fillcolor="rgba(224,224,224,0.3)",
                                    )
                                )
                                for c in all_countries:
                                    _v = _region_metrics.get(c, _all_metrics.get(c, {})).get(bm, 0)
                                    style = country_style[c]
                                    _is_outside = c not in set(_region_countries)
                                    fig_bench.add_trace(
                                        go.Scatter(
                                            x=[_bench_region],
                                            y=[_v],
                                            mode="markers",
                                            name=(f"{c} ★" if _is_outside else c),
                                            marker=dict(
                                                size=12,
                                                color=style["color"],
                                                symbol=(
                                                    "star-diamond" if _is_outside else "diamond"
                                                ),
                                                line=dict(width=1, color="white"),
                                            ),
                                            hovertemplate=(
                                                f"<b>{c}</b>"
                                                f"{' (outside region)' if _is_outside else ''}"
                                                f": %{{y}}<extra></extra>"
                                            ),
                                        )
                                    )
                                fig_bench.update_layout(
                                    title=bm.replace(" (%)", ""),
                                    height=350,
                                    showlegend=bidx == 0,
                                    plot_bgcolor="white",
                                    font=dict(
                                        family="'Inter', Arial, Helvetica, sans-serif",
                                        size=11,
                                    ),
                                    margin=dict(l=40, r=10, t=40, b=30),
                                )
                                st.plotly_chart(fig_bench, width="stretch")
                        st.caption(
                            f"Distribution = all {len(_region_countries)} "
                            f"{_bench_region} countries. "
                            f"◆ = in-region selection, ★ = outside region."
                        )
                    else:
                        st.info(f"Not enough countries in {_bench_region} for benchmarking.")

                # ════════════════════════════════════════════════════════════
                # SLOT 9: Substantive-vs-Boilerplate Ratio (TA-4)
                # ════════════════════════════════════════════════════════════
                st.markdown("#### Substantive vs. Boilerplate Language")
                _entity_label_s9 = "group" if _use_regional_radar else "country"
                st.caption(
                    f"What share of each {_entity_label_s9}'s text is substantive "
                    "policy content (CRPD article keywords) vs. procedural "
                    "boilerplate language. Higher substantive ratio = more "
                    "policy-dense reporting."
                )
                _boilerplate_extra = {
                    "pursuant",
                    "accordance",
                    "reiterated",
                    "reaffirmed",
                    "concluding",
                    "periodic",
                    "recommends",
                    "encouraged",
                    "notes",
                    "recalls",
                    "welcomes",
                    "takes note",
                    "urges",
                }
                _boilerplate_terms = DOMAIN_STOPWORDS | _boilerplate_extra
                _subst_rows = []

                if _use_regional_radar:
                    _subst_entities = list(_radar_groups.keys())
                    for grp_name in _subst_entities:
                        grp_countries = _radar_groups[grp_name]
                        _g_df = cmp_df[cmp_df["country"].isin(grp_countries)]
                        if _g_df.empty:
                            continue
                        _total_words = 0
                        _boiler_hits = 0
                        for text in _g_df["clean_text"].astype(str):
                            words = text.lower().split()
                            _total_words += len(words)
                            for w in words:
                                if w in _boilerplate_terms:
                                    _boiler_hits += 1
                        af = article_frequency(_g_df, ARTICLE_PRESETS)
                        _subst_hits = int(af["count"].sum()) if not af.empty else 0
                        if _total_words > 0:
                            _s_pct = round(_subst_hits / _total_words * 100, 2)
                            _b_pct = round(_boiler_hits / _total_words * 100, 2)
                            _ratio = round(_s_pct / _b_pct, 2) if _b_pct > 0 else 0
                            _subst_rows.append(
                                {
                                    "Entity": grp_name,
                                    "Substantive": _s_pct,
                                    "Boilerplate": _b_pct,
                                    "Ratio": _ratio,
                                    "_total_words": _total_words,
                                }
                            )
                else:
                    for c in all_countries:
                        _c_df = cmp_df[cmp_df["country"] == c]
                        if _c_df.empty:
                            continue
                        _total_words = 0
                        _boiler_hits = 0
                        for text in _c_df["clean_text"].astype(str):
                            words = text.lower().split()
                            _total_words += len(words)
                            for w in words:
                                if w in _boilerplate_terms:
                                    _boiler_hits += 1
                        af = article_frequency(_c_df, ARTICLE_PRESETS)
                        _subst_hits = int(af["count"].sum()) if not af.empty else 0
                        if _total_words > 0:
                            _s_pct = round(_subst_hits / _total_words * 100, 2)
                            _b_pct = round(_boiler_hits / _total_words * 100, 2)
                            _ratio = round(_s_pct / _b_pct, 2) if _b_pct > 0 else 0
                            _subst_rows.append(
                                {
                                    "Entity": c,
                                    "Substantive": _s_pct,
                                    "Boilerplate": _b_pct,
                                    "Ratio": _ratio,
                                    "_total_words": _total_words,
                                }
                            )

                if _subst_rows:
                    _subst_df = pd.DataFrame(_subst_rows)
                    _subst_melt = _subst_df.melt(
                        id_vars=["Entity", "_total_words", "Ratio"],
                        value_vars=["Substantive", "Boilerplate"],
                        var_name="Category",
                        value_name="Share (%)",
                    )
                    fig_subst = px.bar(
                        _subst_melt,
                        x="Entity",
                        y="Share (%)",
                        color="Category",
                        barmode="group",
                        title="Substantive vs. Boilerplate Language Density (%)",
                        color_discrete_map={
                            "Substantive": "#4CAF50",
                            "Boilerplate": "#FF9800",
                        },
                    )
                    fig_subst.update_layout(
                        yaxis_title="Share of Total Words (%)",
                        font=dict(
                            family="'Inter', Arial, Helvetica, sans-serif",
                            size=13,
                        ),
                    )
                    _max_val = _subst_melt["Share (%)"].max()
                    for row in _subst_rows:
                        fig_subst.add_annotation(
                            x=row["Entity"],
                            y=_max_val + 0.5,
                            text=(f"Ratio: {row['Ratio']:.1f}x | {row['_total_words']:,} words"),
                            showarrow=False,
                            font=dict(size=10, color="grey"),
                        )
                    st.plotly_chart(fig_subst, width="stretch")
                    st.caption(
                        "Substantive = CRPD article keyword density. "
                        "Boilerplate = procedural/formulaic terms. "
                        "Ratio > 1.0 = more policy content than boilerplate."
                    )

                # ════════════════════════════════════════════════════════════
                # Deep Dive expander (bigrams, topics, heatmap)
                # ════════════════════════════════════════════════════════════
                with st.expander("Deep Dive Analytics"):
                    # ── Bigram comparison ──
                    _dd_entity_label = "Group" if _use_regional_radar else "Country"
                    st.markdown("##### Distinctive Phrases (Bigrams)")
                    st.caption(
                        f"Top two-word phrases per {_dd_entity_label.lower()} "
                        "— ranked by **keyness** (over-representation vs the "
                        "full corpus) so only genuinely distinctive terms appear."
                    )

                    if _use_regional_radar:
                        _dd_entities = list(_radar_groups.keys())
                        _ngram_cols = st.columns(len(_dd_entities))
                        for ci, grp_name in enumerate(_dd_entities):
                            grp_countries = _radar_groups[grp_name]
                            _g_df = cmp_df[cmp_df["country"].isin(grp_countries)]
                            if len(_g_df) == 0:
                                continue
                            try:
                                _ng = extract_ngrams(
                                    _g_df,
                                    n=2,
                                    top_n=10,
                                    min_freq=1,
                                    reference_df=df,
                                )
                            except ValueError:
                                _ng = pd.DataFrame(columns=["phrase", "freq"])
                            with _ngram_cols[ci]:
                                st.markdown(f"**{grp_name}**")
                                if not _ng.empty:
                                    render_accessible_table(
                                        _ng.rename(
                                            columns={
                                                "phrase": "Phrase",
                                                "freq": "Freq",
                                            }
                                        ),
                                        caption=f"Top bigrams for {grp_name}",
                                    )
                                else:
                                    st.caption("No bigrams found.")
                    else:
                        _ngram_cols = st.columns(len(all_countries))
                        for ci, c in enumerate(all_countries):
                            _c_df = cmp_df[cmp_df["country"] == c]
                            if len(_c_df) == 0:
                                continue
                            try:
                                _ng = extract_ngrams(
                                    _c_df,
                                    n=2,
                                    top_n=10,
                                    min_freq=1,
                                    reference_df=df,
                                )
                            except ValueError:
                                _ng = pd.DataFrame(columns=["phrase", "freq"])
                            with _ngram_cols[ci]:
                                st.markdown(f"**{c}**")
                                if not _ng.empty:
                                    render_accessible_table(
                                        _ng.rename(
                                            columns={
                                                "phrase": "Phrase",
                                                "freq": "Freq",
                                            }
                                        ),
                                        caption=f"Top bigrams for {c}",
                                    )
                                else:
                                    st.caption("No bigrams found.")

                    # ── Topic comparison (NMF) ──
                    if len(cmp_df) >= 10:
                        st.markdown("##### Topic Comparison (NMF)")
                        st.caption(
                            "Dominant topics discovered via NMF on TF-IDF across "
                            "the full corpus, then projected onto the selected "
                            f"{_dd_entity_label.lower()}s — topics stay stable "
                            "regardless of selection."
                        )
                        try:
                            _topics = global_topic_transform(df, cmp_df, n_topics=7)
                            if (
                                _topics
                                and "topic_labels" in _topics
                                and "doc_topic_dist" in _topics
                            ):
                                _topic_labels = _topics["topic_labels"]
                                _doc_dist = _topics["doc_topic_dist"]
                                _topic_rows = []

                                if _use_regional_radar:
                                    for grp_name, grp_countries in _radar_groups.items():
                                        _g_idx = cmp_df[cmp_df["country"].isin(grp_countries)].index
                                        _pos_idx = [
                                            i for i, idx in enumerate(cmp_df.index) if idx in _g_idx
                                        ]
                                        if not _pos_idx or len(_doc_dist) == 0:
                                            continue
                                        _valid = [i for i in _pos_idx if i < len(_doc_dist)]
                                        if not _valid:
                                            continue
                                        _g_dist = [_doc_dist[i] for i in _valid]
                                        _avg = [
                                            sum(d[t] for d in _g_dist) / len(_g_dist)
                                            for t in range(len(_topic_labels))
                                        ]
                                        for t, label in enumerate(_topic_labels):
                                            _topic_rows.append(
                                                {
                                                    "Entity": grp_name,
                                                    "Topic": label,
                                                    "Weight": round(_avg[t], 3),
                                                }
                                            )
                                else:
                                    for c in all_countries:
                                        _c_idx = cmp_df[cmp_df["country"] == c].index
                                        _pos_idx = [
                                            i for i, idx in enumerate(cmp_df.index) if idx in _c_idx
                                        ]
                                        if not _pos_idx or len(_doc_dist) == 0:
                                            continue
                                        _valid = [i for i in _pos_idx if i < len(_doc_dist)]
                                        if not _valid:
                                            continue
                                        _c_dist = [_doc_dist[i] for i in _valid]
                                        _avg = [
                                            sum(d[t] for d in _c_dist) / len(_c_dist)
                                            for t in range(len(_topic_labels))
                                        ]
                                        for t, label in enumerate(_topic_labels):
                                            _topic_rows.append(
                                                {
                                                    "Entity": c,
                                                    "Topic": label,
                                                    "Weight": round(_avg[t], 3),
                                                }
                                            )

                                if _topic_rows:
                                    _topic_df = pd.DataFrame(_topic_rows)
                                    fig_topic = px.bar(
                                        _topic_df,
                                        x="Entity",
                                        y="Weight",
                                        color="Topic",
                                        barmode="stack",
                                        title=f"Topic Distribution by {_dd_entity_label}",
                                        color_discrete_sequence=CATEGORICAL_PALETTE,
                                    )
                                    fig_topic.update_layout(
                                        yaxis=dict(range=[0, 1], dtick=0.25),
                                        font=dict(
                                            family="'Inter', Arial, Helvetica, sans-serif",
                                            size=13,
                                        ),
                                    )
                                    st.plotly_chart(fig_topic, width="stretch")
                        except Exception:
                            st.info(
                                "Topic modeling requires sufficient text. "
                                "Try selections with more documents."
                            )
                    else:
                        st.info(f"Topic comparison needs 10+ documents (currently {len(cmp_df)}).")

                    # ── Reporting cycle completeness heatmap ──
                    st.markdown("##### Reporting Cycle Completeness")
                    _cycle_types = [
                        "State Report",
                        "List of Issues (LOI)",
                        "Written Reply",
                        "Concluding Observations",
                        "Response to Concluding Observations",
                    ]

                    if _use_regional_radar:
                        st.caption(
                            "Total documents of each type submitted by "
                            "members of each group. Higher counts indicate "
                            "more complete collective reporting cycles."
                        )
                        _cycle_rows = []
                        for grp_name, grp_countries in _radar_groups.items():
                            _g_df = cmp_df[cmp_df["country"].isin(grp_countries)]
                            for dt in _cycle_types:
                                _count = (_g_df["doc_type"] == dt).sum()
                                _cycle_rows.append(
                                    {
                                        "Group": grp_name,
                                        "Document Type": dt,
                                        "Count": _count,
                                    }
                                )
                        _cycle_df = pd.DataFrame(_cycle_rows)
                        _cycle_pivot = _cycle_df.pivot(
                            index="Group",
                            columns="Document Type",
                            values="Count",
                        ).fillna(0)
                        _ordered_cols = [ct for ct in _cycle_types if ct in _cycle_pivot.columns]
                        _cycle_pivot = _cycle_pivot[_ordered_cols]
                        fig_cycle = go.Figure(
                            data=go.Heatmap(
                                z=_cycle_pivot.values,
                                x=_cycle_pivot.columns.tolist(),
                                y=_cycle_pivot.index.tolist(),
                                colorscale=[
                                    [0, "#f0f0f0"],
                                    [0.5, "#6BAED6"],
                                    [1, "#003F87"],
                                ],
                                text=_cycle_pivot.values.astype(int),
                                texttemplate="%{text}",
                                hovertemplate=("<b>%{y}</b><br>%{x}: %{z} docs<extra></extra>"),
                            )
                        )
                        fig_cycle.update_layout(
                            title="Reporting Cycle Document Coverage",
                            height=max(200, 70 * len(_radar_groups)),
                            xaxis=dict(tickangle=-25),
                            font=dict(
                                family="'Inter', Arial, Helvetica, sans-serif",
                                size=13,
                            ),
                        )
                        st.plotly_chart(fig_cycle, width="stretch")
                    else:
                        st.caption(
                            "Which document types each country has submitted. "
                            "Complete cycles: State Report → LOI → "
                            "Written Reply → Concluding Observations."
                        )
                        _cycle_rows = []
                        for c in all_countries:
                            _c_df = cmp_df[cmp_df["country"] == c]
                            for dt in _cycle_types:
                                _count = (_c_df["doc_type"] == dt).sum()
                                _cycle_rows.append(
                                    {
                                        "Country": c,
                                        "Document Type": dt,
                                        "Count": _count,
                                    }
                                )
                        _cycle_df = pd.DataFrame(_cycle_rows)
                        _cycle_pivot = _cycle_df.pivot(
                            index="Country",
                            columns="Document Type",
                            values="Count",
                        ).fillna(0)
                        _ordered_cols = [ct for ct in _cycle_types if ct in _cycle_pivot.columns]
                        _cycle_pivot = _cycle_pivot[_ordered_cols]
                        fig_cycle = go.Figure(
                            data=go.Heatmap(
                                z=_cycle_pivot.values,
                                x=_cycle_pivot.columns.tolist(),
                                y=_cycle_pivot.index.tolist(),
                                colorscale=[
                                    [0, "#f0f0f0"],
                                    [0.5, "#6BAED6"],
                                    [1, "#003F87"],
                                ],
                                text=_cycle_pivot.values.astype(int),
                                texttemplate="%{text}",
                                hovertemplate=("<b>%{y}</b><br>%{x}: %{z} docs<extra></extra>"),
                            )
                        )
                        fig_cycle.update_layout(
                            title="Reporting Cycle Document Coverage",
                            height=max(200, 60 * len(all_countries)),
                            xaxis=dict(tickangle=-25),
                            font=dict(
                                family="'Inter', Arial, Helvetica, sans-serif",
                                size=13,
                            ),
                        )
                        st.plotly_chart(fig_cycle, width="stretch")

    # Explore Documents
    elif default_tab == 4:
        render_documents(df, ARTICLE_PRESETS)

    # Semantic Search
    elif default_tab == 5:
        render_semantic_search(df)


def render_semantic_search(df):
    """Semantic document search powered by FAISS + sentence-transformers."""
    import html as _html
    import re as _re

    from src.llm import check_index_freshness, load_search_index, semantic_search

    _s = get_dataset_stats()
    _, _chunks = load_search_index()

    # Check whether the knowledge base has been built BEFORE rendering hero
    if not _chunks:
        st.markdown(
            """
<div style="text-align:center;margin-top:-1rem;margin-bottom:1.8rem;">
    <h1 class="hero-title">
        Smart Document <span class="gradient-word">Search</span>
    </h1>
</div>
""",
            unsafe_allow_html=True,
        )
        st.warning(
            "**Knowledge base not yet available.** "
            f"Semantic search requires all {_s['n_docs']} CRPD documents "
            "to be indexed. Use **Explore Documents** above for keyword "
            "search in the meantime."
        )
        return

    _n_chunks = len(_chunks)
    st.markdown(
        f"""
<div style="text-align:center;margin-top:-1rem;margin-bottom:1.8rem;">
    <h1 class="hero-title">
        Smart Document <span class="gradient-word">Search</span>
    </h1>
    <p style="max-width:700px;margin:0 auto;font-size:1rem;color:#424752;line-height:1.8;">
        Find CRPD documents by <strong>meaning</strong> — not just keywords.
        Search finds passages that discuss similar concepts to your query,
        even when they use different words. Searching across
        <strong>{_n_chunks:,} passages</strong> from
        <strong>{_s["n_docs"]} documents</strong> spanning
        <strong>{_s["n_countries"]} States Parties</strong>
        ({_s["year_min"]}–{_s["year_max"]}).
    </p>
</div>
""",
        unsafe_allow_html=True,
    )

    # ── P1-4: Index freshness check ──
    _freshness = check_index_freshness(_chunks, _s["n_docs"])
    if not _freshness["is_fresh"]:
        st.info(
            f"ℹ️ The search index covers **{_freshness['indexed_docs']}** of "
            f"**{_freshness['dataset_docs']}** documents. "
            f"**{_freshness['missing_count']}** recently added documents are "
            "not yet searchable. The index will be updated in the next rebuild."
        )

    # ── Search bar ──
    st.markdown(
        """
<style>
div[data-testid="stTextInput"] > div > div > input {
    font-size: 1.05rem !important;
    padding: 0.85rem 1.1rem !important;
    border: 2px solid #005bbb !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 16px rgba(0,91,187,0.13) !important;
    background: #fff !important;
    color: #191C1F !important;
}
div[data-testid="stTextInput"] > div > div > input:focus {
    border-color: #0056B3 !important;
    box-shadow: 0 0 0 3px rgba(0,91,187,0.18) !important;
}
div[data-testid="stTextInput"] > div > div > input::placeholder {
    color: #7a8494 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )
    query = st.text_input(
        "Search query",
        placeholder="e.g. legal capacity and supported decision-making for persons with disabilities",
        label_visibility="collapsed",
        key="sem_search_query",
    )

    # ── Optional filters ──
    with st.expander("Filters (optional)", expanded=False):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            all_countries = [
                "All States Parties",
                *sorted(df["country"].dropna().unique().tolist()),
            ]
            sel_country = st.selectbox("State Party", all_countries, key="ss_country")
            filter_country = None if sel_country == "All States Parties" else sel_country
        with fc2:
            all_types = ["All types", *sorted(df["doc_type"].dropna().unique().tolist())]
            sel_type = st.selectbox("Document type", all_types, key="ss_type")
            filter_doc_type = None if sel_type == "All types" else sel_type
        with fc3:
            y_min = int(df["year"].min()) if "year" in df.columns and len(df) else 2010
            y_max = int(df["year"].max()) if "year" in df.columns and len(df) else 2025
            filter_year_min = st.number_input(
                "Year from", value=y_min, min_value=y_min, max_value=y_max, key="ss_yr_min"
            )
        with fc4:
            filter_year_max = st.number_input(
                "Year to", value=y_max, min_value=y_min, max_value=y_max, key="ss_yr_max"
            )

    if not query.strip():
        return

    # ── Run search ──
    with st.spinner("Searching knowledge base…"):
        results = semantic_search(
            query.strip(),
            top_k=8,
            filter_country=filter_country,
            filter_doc_type=filter_doc_type,
            filter_year_min=int(filter_year_min),
            filter_year_max=int(filter_year_max),
        )

    # ── P0-5: Filter results below minimum relevance threshold ──
    _MIN_SCORE = 0.25
    results = [r for r in results if float(r.get("score", 0.0)) >= _MIN_SCORE]

    if not results:
        st.info("No matching excerpts found. Try a broader query or remove filters.")
        return

    st.markdown(
        f"<p style='font-size:0.9rem;color:#1a1a2e;font-weight:500;margin-bottom:0;'>"
        f"<strong>{len(results)}</strong> most relevant excerpts</p>",
        unsafe_allow_html=True,
    )
    st.caption(
        "**Relevance** scores measure textual similarity to your query, "
        "not factual agreement or legal authority."
    )
    st.divider()

    # ── P1-2: Build highlight pattern from query terms ──
    _q_words = [
        w
        for w in query.strip().split()
        if len(w) > 2
        and w.lower()
        not in {"the", "and", "for", "with", "from", "that", "this", "are", "was", "were", "not"}
    ]
    _hl_pattern = (
        _re.compile(
            r"(" + "|".join(_re.escape(w) for w in _q_words) + r")",
            _re.IGNORECASE,
        )
        if _q_words
        else None
    )

    def _highlight(text_str: str) -> str:
        """Wrap query terms in a highlight <mark> tag."""
        if not _hl_pattern:
            return text_str
        return _hl_pattern.sub(
            r'<mark style="background:#FEF3CD;padding:0 2px;border-radius:2px;">\1</mark>',
            text_str,
        )

    for i, chunk in enumerate(results, 1):
        country = _html.escape(str(chunk.get("country", "Unknown")))
        year = _html.escape(str(chunk.get("year", "n/a")))
        doc_type = _html.escape(str(chunk.get("doc_type", "document")).title())
        symbol = _html.escape(str(chunk.get("symbol", "")))
        score = float(chunk.get("score", 0.0))
        text = chunk.get("text", "")
        display_text = _html.escape(text[:400] + "…" if len(text) > 400 else text)
        # Apply highlighting AFTER escaping (safe — highlight tags are ours)
        display_text = _highlight(display_text)

        col_info, col_score = st.columns([5, 1])
        with col_info:
            _sym_tag = (
                f" &nbsp;·&nbsp; <code style='font-size:0.75rem;color:#555;'>{symbol}</code>"
                if symbol
                else ""
            )
            st.markdown(
                f"**{i}. {country}** &nbsp;·&nbsp; {year} &nbsp;·&nbsp; {doc_type}{_sym_tag}",
                unsafe_allow_html=True,
            )
        with col_score:
            st.markdown(
                f"<div style='text-align:right;font-size:0.82rem;"
                f"color:#92580A;font-weight:600;"
                f'font-family:"IBM Plex Mono",monospace;\'>'
                f"Relevance {score:.2f}</div>",
                unsafe_allow_html=True,
            )
        st.progress(min(score, 1.0))
        st.markdown(
            f"<blockquote style='"
            "margin:0.5rem 0 0 0;"
            "padding:0.75rem 1rem;"
            "border-left:3px solid #005bbb;"
            "background:#f0f4fa;"
            "border-radius:0 6px 6px 0;"
            "font-size:0.9rem;"
            "line-height:1.6;"
            "color:#1F2937;"
            f"'>{display_text}</blockquote>",
            unsafe_allow_html=True,
        )
        if i < len(results):
            st.divider()

    # ── P1-3: Research Assistant cross-link ──
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center;padding:1rem 0;'>"
        "<p style='font-size:0.95rem;color:#4B5563;margin-bottom:0.5rem;'>"
        "Want to ask follow-up questions about these documents?</p>"
        "<a href='/chat' style='display:inline-block;padding:0.5rem 1.5rem;"
        "background:#003F87;color:#fff;border-radius:8px;text-decoration:none;"
        "font-weight:600;font-size:0.9rem;'>Try the AI Research Assistant →</a>"
        "</div>",
        unsafe_allow_html=True,
    )


# render() kept for backward compatibility
def render(df, ARTICLE_PRESETS):
    render_countries(df, ARTICLE_PRESETS)
