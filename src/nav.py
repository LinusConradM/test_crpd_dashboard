"""
Top fixed navigation bar for the CRPD Dashboard.
Inspired by the Food Insecurity Analytics Platform navbar style.

Uses st.markdown(unsafe_allow_html=True) so the navbar lives in
Streamlit's main DOM (not an iframe), enabling position:fixed and
pathname-based navigation compatible with st.navigation().
"""

import os

import streamlit as st


# Feature flag — mirrors the check in app.py
_SHOW_RESEARCH = os.environ.get("CRPD_SHOW_RESEARCH", "") == "1"


def _icon(name: str) -> str:
    """Return a Material Symbols Outlined span for use in navbar HTML."""
    return f'<span class="material-symbols-outlined ms-nav-icon">{name}</span>'


# ---------------------------------------------------------------------------
# Navbar structure definition
# ---------------------------------------------------------------------------
NAV_ITEMS = [
    {
        "label": "Home",
        "href": "/home",
        "icon": "home",
        "page": "overview",
    },
    {
        "label": "Explore",
        "page": "countries",
        "icon": "travel_explore",
        "children": [
            {
                "label": "Map View",
                "sub": "map",
                "href": "/explore-map",
                "icon": "map",
                "desc": "Geographic distribution of documents",
            },
            {
                "label": "Reporting Timeline",
                "sub": "trends",
                "href": "/explore-timeline",
                "icon": "trending_up",
                "desc": "When and how many documents were submitted",
            },
            {
                "label": "Country Profiles",
                "sub": "profiles",
                "href": "/explore-profiles",
                "icon": "account_balance",
                "desc": "Per-country deep dive",
            },
            {
                "label": "Compare Countries",
                "sub": "compare",
                "href": "/explore-compare",
                "icon": "compare_arrows",
                "desc": "Side-by-side country metrics",
            },
            {
                "label": "Explore Documents",
                "sub": "documents",
                "href": "/explore-documents",
                "icon": "article",
                "desc": "Search and filter document text",
            },
            {
                "label": "Semantic Search \u2726",
                "sub": "search",
                "href": "/explore-search",
                "icon": "manage_search",
                "desc": "Find documents by meaning with AI",
            },
        ],
    },
    {
        "label": "Analysis",
        "page": "analysis",
        "icon": "analytics",
        "children": [
            {
                "label": "Article Coverage",
                "sub": "coverage",
                "href": "/analysis-coverage",
                "icon": "bar_chart",
                "desc": "Which CRPD articles appear most",
            },
            {
                "label": "Article Deep-Dive",
                "sub": "deepdive",
                "href": "/analysis-deepdive",
                "icon": "manage_search",
                "desc": "Keyword detail per article",
            },
            {
                "label": "Article Co-occurrence",
                "sub": "cooccur",
                "href": "/analysis-cooccur",
                "icon": "hub",
                "desc": "Articles mentioned together",
            },
            {
                "label": "Keywords & Topics",
                "sub": "keywords",
                "href": "/analysis-keywords",
                "icon": "chat_bubble",
                "desc": "Top phrases and n-grams",
            },
            {
                "label": "Model Shift Analysis",
                "sub": "modelshift",
                "href": "/analysis-modelshift",
                "icon": "sync_alt",
                "desc": "Language change over time",
            },
            {
                "label": "Comparative Analysis",
                "sub": "comparative",
                "href": "/analysis-comparative",
                "icon": "balance",
                "desc": "Cross-country analysis",
            },
        ],
    },
    {
        "label": "AI Research Assistant",
        "href": "/chat",
        "page": "chat",
        "icon": "smart_toy",
    },
    {
        "label": "Policy Brief \u2726",
        "href": "/brief",
        "page": "brief",
        "icon": "description",
    },
    {
        "label": "About",
        "href": "/about",
        "page": "about",
        "icon": "info",
    },
]

# Conditionally inject Research nav item (before About) when feature flag is set
if _SHOW_RESEARCH:
    NAV_ITEMS.insert(
        -1,
        {
            "label": "Research \u2726",
            "href": "/research",
            "page": "research",
            "icon": "science",
        },
    )

# Map old sidebar radio labels → query param page values (for backward compat)
LABEL_TO_PAGE = {
    "\U0001f3e0 Overview": "overview",
    "\U0001f5fa\ufe0f Explore": "countries",
    "\U0001f4cb Explore Documents": "countries",
    "\U0001f9ea Analysis": "analysis",
    "\u2139\ufe0f About": "about",
}

# Map Analysis sub-page labels → tab_analyze analysis_type strings
ANALYSIS_SUB_TO_TYPE = {
    "coverage": "CRPD Article Coverage",
    "deepdive": "Article Deep-Dive",
    "cooccur": "Article Co-occurrence",
    "keywords": "Keywords & Topics",
    "modelshift": "Model Shift Analysis",
    "comparative": "Comparative Analysis",
}

COUNTRIES_SUB_TO_TAB = {
    "map": 0,
    "trends": 1,
    "profiles": 2,
    "compare": 3,
    "documents": 4,
    "search": 5,
}


def _build_dropdown_html(children, current_page, current_sub, page_key):
    """Build the <div class='dropdown'> HTML for a nav item's children."""
    items_html = ""
    for child in children:
        sub = child["sub"]
        href = child["href"]
        active_cls = " active" if (current_page == page_key and current_sub == sub) else ""
        items_html += f"""
        <a href="{href}" target="_parent" class="dropdown-item{active_cls}">
            <span class="dd-icon">{_icon(child["icon"])}</span>
            <span class="dd-text">
                <span class="dd-label">{child["label"]}</span>
                <span class="dd-desc">{child["desc"]}</span>
            </span>
        </a>"""
    return f"<div class='dropdown'>{items_html}</div>"


def render_navbar(current_page: str = "overview", current_sub: str = ""):
    """
    Inject a fixed top navigation bar into the Streamlit app.

    Uses st.markdown(unsafe_allow_html=True) so the navbar renders in
    Streamlit's main DOM, enabling position:fixed CSS and pathname-based
    navigation compatible with st.navigation().

    Parameters
    ----------
    current_page : str
        Active top-level page key (e.g. "overview", "countries", "analysis").
    current_sub : str
        Active sub-page key (e.g. "map", "trends", "coverage").
    """

    # ------------------------------------------------------------------
    # Build nav items HTML
    # ------------------------------------------------------------------
    nav_items_html = ""
    for item in NAV_ITEMS:
        page_key = item["page"]
        is_active = current_page == page_key
        active_cls = " active" if is_active else ""
        has_dropdown = "children" in item

        if has_dropdown:
            dropdown_html = _build_dropdown_html(
                item["children"], current_page, current_sub, page_key
            )
            nav_items_html += f"""
            <div class="nav-item has-dropdown{active_cls}">
                <button class="nav-link{active_cls}" role="button" aria-haspopup="menu" aria-expanded="false">
                    {_icon(item["icon"])} {item["label"]} <span class="material-symbols-outlined caret">expand_more</span>
                </button>
                {dropdown_html}
            </div>"""
        else:
            href = item["href"]
            nav_items_html += f"""
            <div class="nav-item{active_cls}">
                <a href="{href}" target="_parent" class="nav-link{active_cls}">
                    {_icon(item["icon"])} {item["label"]}
                </a>
            </div>"""

    navbar_html = f"""
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=swap" rel="stylesheet"/>
<style>
    /* -- Material Icons — navbar context -- */
    .ms-nav-icon {{
        font-family: 'Material Symbols Outlined' !important;
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 20;
        font-size: 16px;
        vertical-align: middle;
        line-height: 1;
        display: inline-block;
        user-select: none;
    }}

    /* -- Reset Streamlit chrome -- */
    header[data-testid="stHeader"] {{ display: none !important; }}
    #MainMenu {{ display: none !important; }}
    /* -- Constrained Width Container -- */
    .block-container {{
        padding-top: 2.8rem !important;
        max-width: 1400px !important;
        padding-left: 3rem !important;
        padding-right: 3rem !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }}
    section[data-testid="stSidebar"] > div:first-child {{ padding-top: 68px !important; }}

    /* -- Navbar container — Stich: frosted glass -- */
    .crpd-navbar {{
        position: fixed;
        top: 0; left: 0; right: 0;
        height: 56px;
        background: rgba(0, 63, 135, 0.95);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0 24px;
        z-index: 9999;
        box-shadow: 0 4px 24px rgba(100, 116, 145, 0.08);
        gap: 4px;
    }}

    /* -- Brand -- */
    .crpd-brand {{
        font-size: 1.05rem;
        font-weight: 700;
        color: #ffffff;
        white-space: nowrap;
        margin-right: 20px;
        letter-spacing: 0.02em;
    }}

    /* -- Nav items -- */
    .nav-item {{
        position: relative;
        display: flex;
        align-items: center;
    }}

    .nav-link {{
        display: flex;
        align-items: center;
        gap: 5px;
        padding: 6px 14px;
        color: #c5ddf0;
        font-size: 0.92rem;
        font-weight: 500;
        text-decoration: none;
        border-radius: 5px;
        cursor: pointer;
        transition: background 0.15s, color 0.15s;
        white-space: nowrap;
        background: none;
        border: none;
        font-family: inherit;
        line-height: inherit;
    }}

    .nav-link:hover,
    .nav-item.has-dropdown:hover .nav-link {{
        background: rgba(255,255,255,0.1);
        color: #ffffff;
    }}

    .nav-link.active {{
        background: linear-gradient(135deg, #003F87, #0056B3);
        color: #ffffff;
    }}

    .caret {{
        font-family: 'Material Symbols Outlined' !important;
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 20 !important;
        font-size: 18px;
        opacity: 0.7;
        vertical-align: middle;
        transition: transform 0.15s;
    }}
    .has-dropdown:hover .caret {{
        transform: rotate(180deg);
    }}

    /* -- Dropdown — Light panel, WCAG-compliant -- */
    .dropdown {{
        display: none;
        position: absolute;
        top: 100%;
        left: 0;
        min-width: 280px;
        max-width: 340px;
        background: #ffffff;
        border: 1px solid #e2e6ed;
        border-radius: 0.75rem;
        box-shadow: 0 8px 32px rgba(0, 63, 135, 0.12);
        z-index: 10000;
        overflow: hidden;
        margin-top: 2px;
        padding: 8px 0;
    }}

    .has-dropdown:hover .dropdown {{
        display: block;
    }}

    .dropdown-item {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 16px;
        min-height: 44px;
        text-decoration: none;
        color: #424752;
        border-bottom: 1px solid #eef0f4;
        transition: background 0.12s, color 0.12s;
    }}

    .dropdown-item:last-child {{
        border-bottom: none;
    }}

    .dropdown-item:hover {{
        background: #F2F4F8;
        color: #191C1F;
    }}

    .dropdown-item:hover .dd-desc {{
        color: #424752;
    }}

    .dropdown-item.active {{
        background: rgba(0, 63, 135, 0.06);
        border-left: 3px solid #003F87;
        padding-left: 13px;
    }}

    .dropdown-item.active .dd-label {{
        color: #003F87;
    }}

    .dropdown-item:focus-visible {{
        outline: 3px solid #003F87;
        outline-offset: -3px;
        border-radius: 4px;
    }}

    .dd-icon {{
        font-size: 1.1rem;
        width: 24px;
        text-align: center;
        flex-shrink: 0;
        color: #003F87;
    }}

    .dd-text {{
        display: flex;
        flex-direction: column;
    }}

    .dd-label {{
        font-size: 0.9rem;
        font-weight: 600;
        line-height: 1.3;
        color: #191C1F;
    }}

    .dd-desc {{
        font-size: 0.8rem;
        color: #5a6377;
        line-height: 1.3;
        margin-top: 1px;
    }}
</style>

<nav class="crpd-navbar">
    <span class="crpd-brand"><span class="ms-nav-icon" style="font-size:18px;margin-right:4px;">public</span> CRPD Dashboard</span>
    {nav_items_html}
</nav>
"""

    # Use st.html for complex HTML — st.markdown corrupts large HTML blocks.
    # Pathname-based links (/explore-map) work with st.navigation routing.
    st.html(navbar_html)
