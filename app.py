# =====================================================
# CRPD Disability Rights Data Dashboard
# -----------------------------------------------------
# Modular 4-Tab Architecture
# - Tab 1: Overview (Key Indicators + Insights)
# - Tab 2: Explore (Interactive filtering + views)
# - Tab 3: Analyze (Deep-dive analyses)
# - Tab 4: About (Documentation + methodology)
# =====================================================

import streamlit as st

from src.styles import CUSTOM_STYLE
from src.data_loader import load_data, load_article_dict
from src.filters import render_sidebar
from src import tab_overview, tab_explore, tab_analyze, tab_about

# -------------------------
# Page Configuration
# -------------------------
st.set_page_config(
    page_title="CRPD Disability Rights Data Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(CUSTOM_STYLE, unsafe_allow_html=True)

# -------------------------
# Load Data
# -------------------------
DATA_PATH = "data/crpd_reports.csv"
df_all = load_data(DATA_PATH)
ARTICLE_PRESETS = load_article_dict()

# -------------------------
# Sidebar Filters
# -------------------------
df = render_sidebar(df_all, ARTICLE_PRESETS)

# -------------------------
# Header
# -------------------------
st.title("🌍 CRPD Disability Rights Data Dashboard")

st.markdown("""
<div style='margin: 1rem 0 1.5rem 0; padding: 1.5rem;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%);
            border-left: 4px solid #667eea; border-radius: 6px;'>
    <p style='font-size: 1.3rem; font-weight: 500; margin: 0; line-height: 1.5;'>
        <strong>The first comprehensive interactive platform</strong> tracking CRPD implementation
        across 143 countries through <strong>five document types spanning the complete UN reporting cycle</strong>
        from 2010–2025 — mapping how nations translate disability rights into policy, practice, and progress.
    </p>
</div>
""", unsafe_allow_html=True)

st.caption("Brought to you by the Institute on Disability and Public Policy (IDPP) at American University.")

# -------------------------
# 4-TAB STRUCTURE
# -------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Overview",
    "🔍 Explore",
    "🧪 Analyze",
    "ℹ️ About"
])

with tab1:
    tab_overview.render(df, df_all, ARTICLE_PRESETS)

with tab2:
    tab_explore.render(df, ARTICLE_PRESETS)

with tab3:
    tab_analyze.render(df, ARTICLE_PRESETS)

with tab4:
    tab_about.render()

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.9em;'>
    Dashboard developed by Dr. Derrick Cogburn and the <b>Institute on Disability and Public Policy (IDPP)</b> research team.<br>
    © 2025 American University
</div>
""", unsafe_allow_html=True)
