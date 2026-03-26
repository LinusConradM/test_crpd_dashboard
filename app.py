# =====================================================
# CRPD Disability Rights Data Dashboard
# =====================================================

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from src.colors import CATEGORICAL_PALETTE
from src.data_loader import get_dataset_stats
from src.styles import CUSTOM_STYLE


# -------------------------
# Global Plotly axis styling + WCAG color theme
# -------------------------
pio.templates["crpd"] = go.layout.Template(
    layout=dict(
        colorway=CATEGORICAL_PALETTE,
        title=dict(x=0.5, xanchor="center", xref="container"),
        xaxis=dict(tickfont=dict(size=14), title=dict(font=dict(size=15))),
        yaxis=dict(tickfont=dict(size=14), title=dict(font=dict(size=15))),
    )
)
pio.templates.default = "plotly+crpd"

# -------------------------
# Global title centering — wraps st.plotly_chart so every Plotly chart
# gets title_x=0.5, title_xref="container" applied before rendering.
# Plotly.js ignores these when they come only from template defaults,
# so we enforce them explicitly on every figure.
# -------------------------
_original_plotly_chart = st.plotly_chart


def _centered_plotly_chart(figure_or_data, *args, **kwargs):
    """Wrapper that centers Plotly titles before rendering."""
    if hasattr(figure_or_data, "update_layout"):
        figure_or_data.update_layout(title_x=0.5, title_xanchor="center", title_xref="container")
    return _original_plotly_chart(figure_or_data, *args, **kwargs)


st.plotly_chart = _centered_plotly_chart

import os

from src import tab_about, tab_analyze, tab_brief, tab_chat, tab_explore, tab_overview
from src.data_loader import load_article_dict, load_data


# Feature flag — set CRPD_SHOW_RESEARCH=1 locally to enable the Research page.
# Posit Connect and colleagues without this env var will not see it.
_SHOW_RESEARCH = os.environ.get("CRPD_SHOW_RESEARCH", "") == "1"
if _SHOW_RESEARCH:
    from src import tab_research
from src.filters import render_inline_filter_panel
from src.nav import ANALYSIS_SUB_TO_TYPE, render_navbar


# -------------------------
# Page Configuration
# -------------------------
st.set_page_config(
    page_title="CRPD Disability Rights Data Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# -------------------------
# Load Data
# -------------------------
DATA_PATH = "data/crpd_reports.csv"
df_all = load_data(DATA_PATH)
ARTICLE_PRESETS = load_article_dict()


# -------------------------
# Page callables — thin wrappers around existing render functions
# -------------------------
def page_home():
    """Homepage: hero section, metrics, At a Glance."""
    _s = get_dataset_stats()
    st.markdown(
        f"""
    <div style="text-align:center;margin:0 auto 1rem auto;padding:1rem 0;">
        <p style="font-size:1.54rem;font-weight:800;color:#003F87;
           letter-spacing:0.03em;text-transform:uppercase;margin:0;">
            The first NLP and AI-powered interactive platform
        </p>
        <h1 style="font-size:3.5rem;font-weight:800;line-height:1.0;
                   color:#003F87;margin:0;white-space:nowrap;">
            CRPD Disability Rights <span style="color:#009E73;">Data Dashboard</span>
        </h1>
        <p style="font-size:1.8rem;font-weight:600;color:#003F87;
                  line-height:1.0;margin:0;">
            Mapping 20 Years of Disability Rights
            <span style="color:#009E73;">in Action</span>
        </p>
        <p style="font-size:1.24rem;color:#000000;font-weight:700;line-height:1.7;
                  margin:12px auto 0 auto;max-width:640px;">
            Adopted in 2006, the CRPD established disability as a matter of
            human rights — not charity or medical intervention. This platform
            makes treaty reporting evidence searchable, visual, and actionable
        </p>
        <div style="display:flex;justify-content:center;gap:24px;
                    margin-top:20px;flex-wrap:wrap;">
            <div style="display:flex;align-items:baseline;gap:6px;">
                <span style="font-size:1.6rem;font-weight:800;color:#003F87;">
                    193</span>
                <span style="font-size:1.02rem;color:#000000;font-weight:400;">
                    States Parties</span>
            </div>
            <div style="width:1px;background:#d3d1c7;align-self:stretch;"></div>
            <div style="display:flex;align-items:baseline;gap:6px;">
                <span style="font-size:1.6rem;font-weight:800;color:#009E73;">
                    {_s["n_doc_types"]}</span>
                <span style="font-size:1.02rem;color:#000000;font-weight:400;">
                    document types</span>
            </div>
            <div style="width:1px;background:#d3d1c7;align-self:stretch;"></div>
            <div style="display:flex;align-items:baseline;gap:6px;">
                <span style="font-size:1.6rem;font-weight:800;color:#003F87;">
                    {_s["n_countries"]}+</span>
                <span style="font-size:1.02rem;color:#000000;font-weight:400;">
                    reporting States Parties</span>
            </div>
            <div style="width:1px;background:#d3d1c7;align-self:stretch;"></div>
            <div style="display:flex;align-items:baseline;gap:6px;">
                <span style="font-size:1.6rem;font-weight:800;color:#009E73;">
                    {_s["year_min"]}–{_s["year_max"]}</span>
                <span style="font-size:1.02rem;color:#000000;font-weight:400;">
                    coverage</span>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    with st.expander(
        "**From Treaty to Action: The CRPD Framework** — expand to understand the reporting process",
        expanded=False,
    ):
        st.html(
            """
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<style>.material-symbols-outlined{font-variation-settings:'FILL' 0,'wght' 400,'GRAD' 0,'opsz' 24;font-size:20px;vertical-align:middle;}</style>
<div style="font-family:'Inter',sans-serif;color:#191C1F;background:#F7F9FD;padding-bottom:16px;">

<!-- Section 1: CRPD Reporting Cycle -->
<div style="margin-bottom:40px;">
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;">
<h2 style="font-family:'Inter',sans-serif;font-size:20px;font-weight:700;margin:0;white-space:nowrap;">CRPD Reporting Cycle</h2>
<div style="flex-grow:1;height:1px;background:rgba(194,198,212,0.3);margin:0 24px;"></div>
</div>
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;">

<div style="padding:32px 32px 28px 32px;background:#FFFFFF;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08);border:1px solid transparent;text-align:center;">
<div style="width:40px;height:40px;border-radius:8px;background:#003F87;display:flex;align-items:center;justify-content:center;margin:0 auto 16px auto;font-size:20px;line-height:1;">
<span class="material-symbols-outlined" style="color:#FFFFFF;">description</span>
</div>
<span style="font-family:'Inter',sans-serif;font-size:13px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#5a6377;margin-bottom:4px;display:block;">Step 01</span>
<h3 style="font-size:16px;font-weight:700;margin:0 0 8px 0;color:#003F87;">Initial Report</h3>
<p style="font-size:14px;color:#424752;line-height:1.6;margin:0;">State parties submit their first comprehensive report within two years of ratification.</p>
</div>

<div style="padding:32px 32px 28px 32px;background:#FFFFFF;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08);border:1px solid transparent;text-align:center;">
<div style="width:40px;height:40px;border-radius:8px;background:#003F87;display:flex;align-items:center;justify-content:center;margin:0 auto 16px auto;font-size:20px;line-height:1;">
<span class="material-symbols-outlined" style="color:#FFFFFF;">quiz</span>
</div>
<span style="font-family:'Inter',sans-serif;font-size:13px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#5a6377;margin-bottom:4px;display:block;">Step 02</span>
<h3 style="font-size:16px;font-weight:700;margin:0 0 8px 0;color:#003F87;">List of Issues</h3>
<p style="font-size:14px;color:#424752;line-height:1.6;margin:0;">The Committee reviews the report and raises specific questions regarding local implementation.</p>
</div>

<div style="padding:32px 32px 28px 32px;background:#FFFFFF;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08);border:1px solid transparent;text-align:center;">
<div style="width:40px;height:40px;border-radius:8px;background:#003F87;display:flex;align-items:center;justify-content:center;margin:0 auto 16px auto;font-size:20px;line-height:1;">
<span class="material-symbols-outlined" style="color:#FFFFFF;">edit_note</span>
</div>
<span style="font-family:'Inter',sans-serif;font-size:13px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#5a6377;margin-bottom:4px;display:block;">Step 03</span>
<h3 style="font-size:16px;font-weight:700;margin:0 0 8px 0;color:#003F87;">Constructive Dialogue</h3>
<p style="font-size:14px;color:#424752;line-height:1.6;margin:0;">Interactive session between the Committee and State delegates to refine legal frameworks.</p>
</div>

<div style="padding:32px 32px 28px 32px;background:#FFFFFF;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08);border:1px solid transparent;text-align:center;">
<div style="width:40px;height:40px;border-radius:8px;background:#003F87;display:flex;align-items:center;justify-content:center;margin:0 auto 16px auto;font-size:20px;line-height:1;">
<span class="material-symbols-outlined" style="color:#FFFFFF;">verified</span>
</div>
<span style="font-family:'Inter',sans-serif;font-size:13px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#5a6377;margin-bottom:4px;display:block;">Step 04</span>
<h3 style="font-size:16px;font-weight:700;margin:0 0 8px 0;color:#003F87;">Concluding Obs.</h3>
<p style="font-size:14px;color:#424752;line-height:1.6;margin:0;">Final recommendations provided by the UN Committee to guide national reform and monitoring.</p>
</div>

</div>
</div>

<!-- Section 2: Key Implementation Articles -->
<div style="margin-bottom:40px;">
<div style="margin-bottom:24px;">
<h2 style="font-family:'Inter',sans-serif;font-size:20px;font-weight:700;margin:0 0 4px 0;">Key Implementation Articles</h2>
<p style="color:#424752;font-size:14px;margin:0;">Core statutory requirements for domestic monitoring and reporting.</p>
</div>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:24px;">

<div style="padding:28px;background:#E6E8EC;border-radius:12px;">
<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
<span style="padding:6px 8px;background:#003F87;color:#FFFFFF;border-radius:8px;font-size:12px;font-weight:700;font-family:'Inter',sans-serif;">Art. 33</span>
<h3 style="font-size:16px;font-weight:700;margin:0;">National Implementation</h3>
</div>
<p style="font-size:14px;color:#424752;line-height:1.6;margin:0 0 12px 0;">Establishment of focal points within government for matters relating to the implementation of the Convention.</p>
<div style="padding-top:12px;display:flex;flex-wrap:wrap;gap:8px;">
<span style="padding:4px 12px;background:#FFFFFF;border-radius:9999px;font-size:13px;font-weight:700;color:#5a6377;font-family:'Inter',sans-serif;text-transform:uppercase;">MONITORING</span>
<span style="padding:4px 12px;background:#FFFFFF;border-radius:9999px;font-size:13px;font-weight:700;color:#5a6377;font-family:'Inter',sans-serif;text-transform:uppercase;">FOCAL POINT</span>
</div>
</div>

<div style="padding:28px;background:#E6E8EC;border-radius:12px;">
<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
<span style="padding:6px 8px;background:#003F87;color:#FFFFFF;border-radius:8px;font-size:12px;font-weight:700;font-family:'Inter',sans-serif;">Art. 35</span>
<h3 style="font-size:16px;font-weight:700;margin:0;">Reports by State Parties</h3>
</div>
<p style="font-size:14px;color:#424752;line-height:1.6;margin:0 0 12px 0;">Each State Party shall submit to the Committee a comprehensive report on measures taken to give effect to its obligations.</p>
<div style="padding-top:12px;display:flex;flex-wrap:wrap;gap:8px;">
<span style="padding:4px 12px;background:#FFFFFF;border-radius:9999px;font-size:13px;font-weight:700;color:#5a6377;font-family:'Inter',sans-serif;text-transform:uppercase;">COMPLIANCE</span>
<span style="padding:4px 12px;background:#FFFFFF;border-radius:9999px;font-size:13px;font-weight:700;color:#5a6377;font-family:'Inter',sans-serif;text-transform:uppercase;">STATISTICS</span>
</div>
</div>

<div style="padding:28px;background:#E6E8EC;border-radius:12px;">
<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
<span style="padding:6px 8px;background:#003F87;color:#FFFFFF;border-radius:8px;font-size:12px;font-weight:700;font-family:'Inter',sans-serif;">Art. 36</span>
<h3 style="font-size:16px;font-weight:700;margin:0;">Consideration of Reports</h3>
</div>
<p style="font-size:14px;color:#424752;line-height:1.6;margin:0 0 12px 0;">The Committee shall consider each report and shall make such suggestions and general recommendations as it may consider appropriate.</p>
<div style="padding-top:12px;display:flex;flex-wrap:wrap;gap:8px;">
<span style="padding:4px 12px;background:#FFFFFF;border-radius:9999px;font-size:13px;font-weight:700;color:#5a6377;font-family:'Inter',sans-serif;text-transform:uppercase;">REVIEW</span>
<span style="padding:4px 12px;background:#FFFFFF;border-radius:9999px;font-size:13px;font-weight:700;color:#5a6377;font-family:'Inter',sans-serif;text-transform:uppercase;">ADVISORY</span>
</div>
</div>

</div>
</div>

<!-- Section 3: Two-column layout -->
<div style="display:grid;grid-template-columns:1fr 1fr;gap:40px;align-items:start;">

<div>
<h2 style="font-family:'Inter',sans-serif;font-size:20px;font-weight:700;margin:0 0 16px 0;">Why This Dashboard Matters</h2>
<div style="display:flex;flex-direction:column;gap:12px;">

<div style="display:flex;gap:12px;padding:12px;background:#FFFFFF;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
<span class="material-symbols-outlined" style="color:#004278;margin-top:2px;">insights</span>
<div>
<h4 style="font-size:14px;font-weight:700;margin:0 0 2px 0;">Data Centralization</h4>
<p style="font-size:12px;color:#424752;margin:0;line-height:1.5;">Unifies diverse reporting data into a single analytical framework for policy makers.</p>
</div>
</div>

<div style="display:flex;gap:12px;padding:12px;background:#FFFFFF;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
<span class="material-symbols-outlined" style="color:#004278;margin-top:2px;">history_edu</span>
<div>
<h4 style="font-size:14px;font-weight:700;margin:0 0 2px 0;">Accountability Tracking</h4>
<p style="font-size:12px;color:#424752;margin:0;line-height:1.5;">Monitors progress against UN Committee recommendations over multi-year cycles.</p>
</div>
</div>

<div style="display:flex;gap:12px;padding:12px;background:#FFFFFF;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
<span class="material-symbols-outlined" style="color:#004278;margin-top:2px;">public</span>
<div>
<h4 style="font-size:14px;font-weight:700;margin:0 0 2px 0;">Global Benchmarking</h4>
<p style="font-size:12px;color:#424752;margin:0;line-height:1.5;">Compare national implementation strategies with global best practices and standards.</p>
</div>
</div>

</div>
</div>

<div>
<h2 style="font-family:'Inter',sans-serif;font-size:20px;font-weight:700;margin:0 0 16px 0;">Core CRPD Principles</h2>
<div style="display:flex;flex-wrap:wrap;gap:8px;">
<span style="padding:6px 12px;background:#0056B3;color:#FFFFFF;border-radius:9999px;font-size:12px;font-weight:500;font-family:'Inter',sans-serif;">Dignity &amp; Autonomy</span>
<span style="padding:6px 12px;background:#D5E0F7;color:#424752;border-radius:9999px;font-size:12px;font-weight:500;font-family:'Inter',sans-serif;">Non-Discrimination</span>
<span style="padding:6px 12px;background:#D5E0F7;color:#424752;border-radius:9999px;font-size:12px;font-weight:500;font-family:'Inter',sans-serif;">Full Participation</span>
<span style="padding:6px 12px;background:#D5E0F7;color:#424752;border-radius:9999px;font-size:12px;font-weight:500;font-family:'Inter',sans-serif;">Equality of Opportunity</span>
<span style="padding:6px 12px;background:#D5E0F7;color:#424752;border-radius:9999px;font-size:12px;font-weight:500;font-family:'Inter',sans-serif;">Accessibility</span>
<span style="padding:6px 12px;background:#D5E0F7;color:#424752;border-radius:9999px;font-size:12px;font-weight:500;font-family:'Inter',sans-serif;">Equality between Men &amp; Women</span>
<span style="padding:6px 12px;background:#0C5A9D;color:#FFFFFF;border-radius:9999px;font-size:12px;font-weight:500;font-family:'Inter',sans-serif;">Respect for Children's Capacities</span>
</div>
<div style="margin-top:24px;position:relative;height:180px;border-radius:16px;overflow:hidden;">
<img src="https://lh3.googleusercontent.com/aida-public/AB6AXuBLe8qn98n6mPLpJcy-j9cVJB_KbmUy6gH8lWznmKmTpFT2at9p18HzmhYYvZ0kCGBVifO1aND4m_jyOXQ-0O0UqOp05Agiy_fnBs6eeewH97dwhuAFQLtPnSZeo1uqRrMx9dmQIldcW8cFifmiqsR-OMWUO0k-TsVB5rNdq4dWUU-A2HcM_XuWU7KnNp39jm07_wsRnQ_m13r3DGIEbbsxnBpUxWeq-6FwxmeEWdiG2A5YXlTg1oJ8F2RSgHuCF_5LfjaRWAs_4lKk" alt="Global connectivity and human rights" style="width:100%;height:100%;object-fit:cover;filter:grayscale(100%);"/>
<div style="position:absolute;inset:0;background:rgba(0,63,135,0.4);mix-blend-mode:multiply;"></div>
<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;">
<p style="color:#FFFFFF;font-family:'Inter',sans-serif;font-weight:700;font-size:18px;text-align:center;padding:0 48px;line-height:1.4;margin:0;">Empowering rights through data-driven advocacy.</p>
</div>
</div>
</div>

</div>
</div>
"""
        )

    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

    df = render_inline_filter_panel(df_all, ARTICLE_PRESETS)
    tab_overview.render(df, df_all, ARTICLE_PRESETS)


def _explore_page(tab_idx: int):
    """Shared logic for all Explore sub-pages."""
    if tab_idx == 5:
        # Semantic Search has its own internal filters — skip the global panel
        df = df_all
    else:
        # Page heading above the filter panel
        _page_titles = {
            0: (
                "Global CRPD Reporting Map",
                "Explore the geographic distribution of CRPD reporting activity"
                f" across {get_dataset_stats()['n_countries']} States Parties \u2014 hover over a country to highlight"
                " it across both views.",
            ),
            1: (
                "Reporting Timeline",
                "Explore CRPD reporting volume, language patterns, and article coverage over time.",
            ),
            2: (
                "Country Profiles",
                "Deep-dive into a single country\u2019s CRPD reporting history"
                " and article coverage.",
            ),
            3: (
                "Compare Countries",
                "Side-by-side comparison of CRPD reporting metrics across selected countries.",
            ),
        }
        _title, _desc = _page_titles.get(tab_idx, ("Explore", ""))
        if tab_idx != 2:
            st.markdown(
                f"<h3 style='text-align:center;margin-bottom:0;'>{_title}</h3>"
                f"<p style='text-align:center;color:#003F87;font-size:1.1rem;"
                f"font-weight:600;margin-top:4px;margin-bottom:1rem;'>{_desc}</p>",
                unsafe_allow_html=True,
            )
        if tab_idx in (2, 3):
            df = df_all  # Country Profiles & Compare use their own selectors
        else:
            df = render_inline_filter_panel(df_all, ARTICLE_PRESETS)
    tab_explore.render_countries(df, ARTICLE_PRESETS, default_tab=tab_idx)


def page_explore_map():
    _explore_page(0)


def page_explore_timeline():
    _explore_page(1)


def page_explore_profiles():
    _explore_page(2)


def page_explore_compare():
    _explore_page(3)


def page_explore_documents():
    _explore_page(4)


def page_explore_search():
    _explore_page(5)


def _analysis_page(sub_key: str):
    """Shared logic for all Analysis sub-pages."""
    df = render_inline_filter_panel(df_all, ARTICLE_PRESETS)
    analysis_type = ANALYSIS_SUB_TO_TYPE.get(sub_key, "")
    tab_analyze.render(df, ARTICLE_PRESETS, analysis_type=analysis_type)


def page_analysis_coverage():
    _analysis_page("coverage")


def page_analysis_deepdive():
    _analysis_page("deepdive")


def page_analysis_cooccur():
    _analysis_page("cooccur")


def page_analysis_keywords():
    _analysis_page("keywords")


def page_analysis_modelshift():
    _analysis_page("modelshift")


def page_analysis_comparative():
    _analysis_page("comparative")


def page_chat():
    tab_chat.render(df_all)


def page_brief():
    tab_brief.render(df_all)


if _SHOW_RESEARCH:

    def page_research():
        tab_research.render(df_all, ARTICLE_PRESETS)


def page_about():
    tab_about.render()


# -------------------------
# Register all pages with st.navigation
# -------------------------
pages = [
    st.Page(page_home, title="Home", url_path="home", default=True),
    # Explore sub-pages
    st.Page(page_explore_map, title="Map View", url_path="explore-map"),
    st.Page(page_explore_timeline, title="Reporting Timeline", url_path="explore-timeline"),
    st.Page(page_explore_profiles, title="Country Profiles", url_path="explore-profiles"),
    st.Page(page_explore_compare, title="Compare Countries", url_path="explore-compare"),
    st.Page(page_explore_documents, title="Explore Documents", url_path="explore-documents"),
    st.Page(page_explore_search, title="Semantic Search", url_path="explore-search"),
    # Analysis sub-pages
    st.Page(page_analysis_coverage, title="Article Coverage", url_path="analysis-coverage"),
    st.Page(page_analysis_deepdive, title="Article Deep-Dive", url_path="analysis-deepdive"),
    st.Page(page_analysis_cooccur, title="Article Co-occurrence", url_path="analysis-cooccur"),
    st.Page(page_analysis_keywords, title="Keywords & Topics", url_path="analysis-keywords"),
    st.Page(page_analysis_modelshift, title="Model Shift Analysis", url_path="analysis-modelshift"),
    st.Page(
        page_analysis_comparative, title="Comparative Analysis", url_path="analysis-comparative"
    ),
    # Standalone pages
    st.Page(page_chat, title="AI Research Assistant", url_path="chat"),
    st.Page(page_brief, title="Policy Brief", url_path="brief"),
    st.Page(page_about, title="About", url_path="about"),
]

if _SHOW_RESEARCH:
    # Insert Research page before About (last item)
    pages.insert(-1, st.Page(page_research, title="Research & Citation", url_path="research"))

nav = st.navigation(pages, position="hidden")

# -------------------------
# Global styles
# -------------------------
st.markdown(CUSTOM_STYLE, unsafe_allow_html=True)

# -------------------------
# Determine current page/sub for navbar highlighting
# -------------------------
# Map url_path → (page_key, sub_key) for navbar active state
_URL_TO_NAV = {
    "": ("overview", ""),  # default page returns empty url_path
    "home": ("overview", ""),
    "explore-map": ("countries", "map"),
    "explore-timeline": ("countries", "trends"),
    "explore-profiles": ("countries", "profiles"),
    "explore-compare": ("countries", "compare"),
    "explore-documents": ("countries", "documents"),
    "explore-search": ("countries", "search"),
    "analysis-coverage": ("analysis", "coverage"),
    "analysis-deepdive": ("analysis", "deepdive"),
    "analysis-cooccur": ("analysis", "cooccur"),
    "analysis-keywords": ("analysis", "keywords"),
    "analysis-modelshift": ("analysis", "modelshift"),
    "analysis-comparative": ("analysis", "comparative"),
    "chat": ("chat", ""),
    "brief": ("brief", ""),
    "research": ("research", ""),
    "about": ("about", ""),
}

_current_url = nav.url_path or "home"
_nav_page, _nav_sub = _URL_TO_NAV.get(_current_url, ("overview", ""))

# -------------------------
# Top Navbar
# -------------------------
render_navbar(current_page=_nav_page, current_sub=_nav_sub)

# -------------------------
# Dispatch to the active page callable
# -------------------------
nav.run()

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.markdown(
    """
<div style='text-align: center; color: #6B7080; font-size: 0.9em;'>
    Dashboard developed by Dr. Derrick Cogburn and the <b>Institute on Disability and Public Policy (IDPP)</b> research team.<br>
    &copy; 2025-2026 Derrick Cogburn
</div>
""",
    unsafe_allow_html=True,
)
