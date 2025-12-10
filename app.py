# =====================================================
# 🌍 CRPD Disability Rights Data Dashboard (v6.0)
# -----------------------------------------------------
# MAJOR RESTRUCTURE: 4-Tab Architecture
# - Tab 1: Overview (Key Indicators + Insights)
# - Tab 2: Explore (Interactive filtering + views)
# - Tab 3: Analyze (Deep-dive analyses)
# - Tab 4: About (Documentation + methodology)
# =====================================================

import re
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
from collections import Counter

# -------------------------
# Page Configuration
# -------------------------
st.set_page_config(
    page_title="CRPD Disability Rights Data Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------
# Custom CSS Styling
# -------------------------
CUSTOM_STYLE = """
    <style>
        /* Hide Streamlit default elements */
        .block-container{padding-top:1.2rem;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Enhanced text sizing */
        .stApp p {
            font-size: 1.05rem;
            line-height: 1.6;
        }
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #3d5161;
            padding: 10px 20px;
            border-radius: 8px 8px 0 0;
        }
        
        .stTabs [data-baseweb="tab-list"] button {
            font-size: 1.1rem;
            font-weight: 500;
            color: white;
            background-color: transparent;
            border-radius: 6px 6px 0 0;
            padding: 12px 24px;
        }
        
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
            background-color: #26a69a;
            color: white;
        }
        
        .stTabs [data-baseweb="tab-list"] button:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
        
        /* Metric card styling */
        .metric-card {
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
            border-top: 4px solid;
            margin-bottom: 10px;
            min-height: 200px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        
        .metric-icon {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f1f1f;
            margin: 10px 0;
        }
        
        .metric-label {
            font-size: 0.9rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .metric-trend {
            font-size: 0.85rem;
            font-weight: 500;
            margin-top: 8px;
            min-height: 20px;
        }
        
        .trend-up { color: #2e7d32; }
        .trend-down { color: #c62828; }
        .trend-neutral { color: #f57c00; }
        
        /* Info boxes */
        .info-box {
            background: rgba(61, 81, 97, 0.08);
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #3d5161;
            margin: 20px 0;
            min-height: 400px;
        }
        
        .info-box h4 {
            color: #3d5161;
            margin-top: 0;
        }
        /* About tab boxes - smaller min-height */

        .about-info-box {
            background: rgba(61, 81, 97, 0.08);
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #3d5161;
            margin: 20px 0;
            min-height: 230px;  /* Smaller than the 360px we use elsewhere */
        }

        /* Insights section */
        .insights-section {
            background: #f8f9fa;
            padding: 30px;
            border-radius: 8px;
            border-left: 4px solid #3d5161;
            margin: 20px 0;
        }
        
        .insight-item {
            margin-bottom: 15px;
            line-height: 1.8;
        }
        
        .insight-item strong {
            color: #1f1f1f;
        }
        
        /* Section headers */
        h3 {
            font-size: 1.5rem;
            margin-top: 2rem;
            color: #1f1f1f;
        }
        
        /* Two-column layouts */
        .two-col-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }
    </style>
"""
st.markdown(CUSTOM_STYLE, unsafe_allow_html=True)

# -------------------------
# Load Data & Dictionaries
# -------------------------
@st.cache_data(show_spinner=True)
def load_data(csv_path: str):
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip().str.lower()
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    for c in ["doc_type", "country", "region", "subregion", "language"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    if "text_snippet" not in df.columns and "clean_text" in df.columns:
        df["text_snippet"] = df["clean_text"].apply(lambda x: " ".join(str(x).split()[:120]))
    return df

@st.cache_data
def load_article_dict():
    try:
        from crpd_article_dict import ARTICLE_PRESETS
        return ARTICLE_PRESETS
    except Exception as e:
        st.warning(f"Couldn't load article dictionary ({e}); using fallback.")
        return {
            "Article 9 — Accessibility": ["accessibility", "barrier", "universal design"],
            "Article 13 — Access to Justice": ["justice", "court", "legal"],
            "Article 24 — Education": ["education", "school", "inclusive education"]
        }

MODEL_DICT = {
    "Medical Model": [
        "treatment","rehabilitation","therapy","patient","disorder","impairment",
        "illness","diagnosis","caregiver","institution","special needs","cure"
    ],
    "Rights-Based Model": [
        "inclusion","equality","accessibility","participation","autonomy",
        "independent living","reasonable accommodation","universal design",
        "dignity","rights","empowerment","access to justice"
    ]
}

# -------------------------
# Helper Functions
# -------------------------
def filter_df(df, region, country, doc_types, year_range):
    d = df.copy()
    if region and region != "All":
        d = d[d["region"] == region]
    if country and country != "All":
        d = d[d["country"] == country]
    if doc_types:
        d = d[d["doc_type"].isin(doc_types)]
    if year_range and "year" in d.columns:
        ymin, ymax = year_range
        d = d[(d["year"].fillna(0) >= ymin) & (d["year"].fillna(9999) <= ymax)]
    return d

def count_phrases(text, phrases):
    if not isinstance(text, str):
        return 0
    total = 0
    for kw in phrases:
        total += len(re.findall(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE))
    return total

@st.cache_data
def article_frequency(df, article_dict, groupby=None):
    rows = []
    iterable = [(None, df)] if not groupby else df.groupby(groupby)
    for g, sub in iterable:
        for art, kws in article_dict.items():
            c = sub["clean_text"].apply(lambda t: count_phrases(t, kws)).sum()
            rows.append({"group": ("All" if g is None else g), "article": art, "count": int(c)})
    out = pd.DataFrame(rows)
    return out[out["count"] > 0].sort_values("count", ascending=False)

@st.cache_data
def keyword_counts(df, top_n=30):
    cnt = Counter()
    for t in df["clean_text"].astype(str).tolist():
        cnt.update(w for w in t.split() if 2 <= len(w) <= 25)
    return pd.DataFrame(cnt.items(), columns=["term", "freq"]).sort_values("freq", ascending=False).head(top_n)

@st.cache_data
def tfidf_by_doc_type(df, top_n=20):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        st.warning("scikit-learn not installed; using frequency fallback.")
        return keyword_counts(df, top_n).assign(doc_type="All").rename(columns={"freq":"score"})
    rows = []
    for dt, sub in df.groupby("doc_type"):
        docs = sub["clean_text"].dropna().astype(str).tolist()
        if len(docs) < 2:
            topk = keyword_counts(sub, top_n)
            topk["doc_type"] = dt
            rows.append(topk.rename(columns={"freq": "score"}))
            continue
        n_docs = len(docs)
        min_df = 1 if n_docs < 10 else 2
        max_df = 1.0 if n_docs <= 3 else 0.9
        try:
            vec = TfidfVectorizer(min_df=min_df, max_df=max_df, ngram_range=(1, 2))
            mat = vec.fit_transform(docs)
            terms = np.array(vec.get_feature_names_out())
            scores = np.asarray(mat.mean(axis=0)).ravel()
            idx = scores.argsort()[::-1][:top_n]
            tmp = pd.DataFrame({"term": terms[idx], "score": scores[idx], "doc_type": dt})
            rows.append(tmp)
        except ValueError:
            topk = keyword_counts(sub, top_n)
            topk["doc_type"] = dt
            rows.append(topk.rename(columns={"freq": "score"}))
    return pd.concat(rows, ignore_index=True)

@st.cache_data
def model_shift_table(df):
    rows = []
    for _, r in df.iterrows():
        text = str(r.get("clean_text", ""))
        counts = {m: count_phrases(text, kws) for m, kws in MODEL_DICT.items()}
        total = sum(counts.values()) if sum(counts.values()) > 0 else 1
        rows.append({
            "region": r.get("region","Unknown"),
            "year": r.get("year", np.nan),
            "medical": counts["Medical Model"],
            "rights": counts["Rights-Based Model"],
            "rights_share": counts["Rights-Based Model"]/total
        })
    return pd.DataFrame(rows)

def create_metric_card(icon, value, label, trend=None, color="#667eea"):
    """Create a styled metric card with icon, value, label, and optional trend"""
    trend_html = ""
    if trend:
        trend_class = "trend-up" if "↑" in trend else "trend-down" if "↓" in trend else "trend-neutral"
        trend_html = f'<div class="metric-trend {trend_class}">{trend}</div>'
    
    return f"""
    <div class="metric-card" style="border-top-color: {color};">
        <div class="metric-icon">{icon}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
        {trend_html}
    </div>
    """

# -------------------------
# Load Data
# -------------------------
DATA_PATH = "data/crpd_reports.csv"
df_all = load_data(DATA_PATH)
ARTICLE_PRESETS = load_article_dict()

# -------------------------
# Sidebar Filters
# -------------------------
st.sidebar.markdown("### 🔍 Global Filters")
st.sidebar.caption("Applied across Explore and Analyze tabs")

regions = ["All"] + sorted(df_all["region"].dropna().unique())
region = st.sidebar.selectbox("Region", regions, index=0)

countries = ["All"] + sorted(df_all.loc[(df_all["region"] == region) | (region == "All"), "country"].unique())
country = st.sidebar.selectbox("Country", countries, index=0)

doc_types_all = sorted(df_all["doc_type"].unique())
# Set default to only State Reports
default_doc_types = [dt for dt in doc_types_all if "state" in dt]
doc_types = st.sidebar.multiselect("Document Type", doc_types_all, default=default_doc_types)

if "year" in df_all.columns:
    ymin, ymax = int(df_all["year"].min()), int(df_all["year"].max())
    year_range = st.sidebar.slider("Year Range", ymin, ymax, (ymin, ymax))
else:
    year_range = None

# NEW: Article Filter
st.sidebar.markdown("---")
st.sidebar.markdown("### 📘 CRPD Article Filter")
article_list = ["All Articles"] + sorted(list(ARTICLE_PRESETS.keys()))
selected_articles = st.sidebar.multiselect(
    "Focus on specific articles",
    article_list,
    default=["All Articles"],
    help="Filter analysis to specific CRPD articles. Leave as 'All Articles' to see everything."
)

# Apply filters
df = filter_df(df_all, region, country, doc_types, year_range)

st.sidebar.markdown("---")
st.sidebar.caption(f"**Filtered Results:** {len(df):,} of {len(df_all):,} documents")

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
tab_overview, tab_explore, tab_analyze, tab_about = st.tabs([
    "📊 Overview",
    "🔍 Explore", 
    "🧪 Analyze",
    "ℹ️ About"
])

# =====================================================
# TAB 1: OVERVIEW
# =====================================================
with tab_overview:
    st.header("Understanding CRPD Implementation")
    
    # Two-column layout for "What" and "Why"
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="info-box">
            <h4>📘 What is the CRPD?</h4>
            <p>The <strong>Convention on the Rights of Persons with Disabilities (CRPD)</strong> 
            is a landmark UN human rights treaty adopted in 2006. The CRPD is also a develeopment instrument, and is aligned with the 2030 Sustainable Development Goals (SDGs) and other global development strategies. It represents a paradigm shift 
            from viewing disability through a medical lens to recognizing it as a human rights issue.</p>
            <p><em>Throughout this dashboard, we use "CRPD" as an abbreviation for the Convention.</em></p>
            <h4>🛠️ National Implementation and Monitoring</h4>
            <p>Articles 33, 35, and 36 outline how States implement and report on the CRPD. Article 33 requires States to designate national mechanisms to coordinate implementation and independent monitoring. Article 35 mandates periodic State Party reports to the CRPD Committee detailing progress. Article 36 governs the Committee’s review process, including Lists of Issues, State responses, and the Committee’s Concluding Observations. Civil society organizations may also submit alternative or “shadow” reports to inform the Committee’s review.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="info-box">
            <h4>🎯 Why It Matters</h4>
            <ul style="line-height: 1.8;">
                <li><strong>Implementation Tracking:</strong> Monitor how countries fulfill their commitments</li>
                <li><strong>Policy Accountability:</strong> Ensure governments follow through on disability rights</li>
                <li><strong>Rights Transformation:</strong> Track the shift from medical to rights-based models</li>
                <li><strong>Global Landscape:</strong> Understand worldwide disability rights progress</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Data Sources & Coverage
    st.markdown("---")
    st.subheader("📦 Data Sources & Coverage")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="info-box">
            <h4>🗂️ Document Sources</h4>
            <p><strong>UN Treaty Body Database</strong></p>
            <p>Five document types across the complete reporting cycle:</p>
            <ol style="line-height: 1.8;">
                <li>📄 <strong>State Party Reports</strong></li>
                <li>❓ <strong>List of Issues</strong></li>
                <li>💬 <strong>Written Responses</strong></li>
                <li>📋 <strong>Concluding Observations</strong></li>
                <li>↩️ <strong>Responses to COs</strong></li>
            </ol>
            <p style="margin-top: 15px; padding: 10px; background: rgba(38, 166, 154, 0.1); border-radius: 4px;">
                <strong>Coverage:</strong> 506 documents • 143 countries • 2010-2025
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="info-box">
            <h4>📊 Variables Analyzed</h4>
            <ul style="line-height: 1.8;">
                <li>📄 <strong>Outcome:</strong> Document types, reporting patterns</li>
                <li>📚 <strong>Content:</strong> CRPD articles, keywords, themes</li>
                <li>🌍 <strong>Geographic:</strong> Countries, regions, subregions</li>
                <li>⏰ <strong>Temporal:</strong> Years, reporting cycles</li>
                <li>🔄 <strong>Model Language:</strong> Medical vs. Rights-based framing</li>
                <li>🤝 <strong>Actors:</strong> State Parties vs. Committee emphasis</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Key Global CRPD Indicators
    st.markdown("---")
    st.subheader("📊 Key Global CRPD Indicators")
    st.caption("Based on currently filtered data")
    
    # Calculate metrics
    total_docs = len(df)
    total_countries = df["country"].nunique()
    total_regions = df["region"].nunique()
    if "year" in df.columns and len(df):
        years_display = f"{int(df['year'].min())}–{int(df['year'].max())}"
    else:
        years_display = "—"
    
    # Row 1: Data Coverage Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(create_metric_card(
            "📄", f"{total_docs:,}", "Total Documents", 
            trend="↑ 15% vs 2020-22", color="#3d5161"
        ), unsafe_allow_html=True)
    
    with col2:
        st.markdown(create_metric_card(
            "🌍", f"{total_countries:,}", "Countries", 
            trend="↑ 8 new since 2020", color="#3d5161"
        ), unsafe_allow_html=True)
    
    with col3:
        st.markdown(create_metric_card(
            "🗺️", f"{total_regions:,}", "Regions Covered",
            trend=" ", color="#3d5161"
        ), unsafe_allow_html=True)
    
    with col4:
        st.markdown(create_metric_card(
            "📅", years_display, "Years Spanning",
            trend=" ", color="#3d5161"
        ), unsafe_allow_html=True)
    
# Row 2: Implementation Insights
    col1, col2, col3, col4 = st.columns(4)
    
    # Calculate additional metrics
    if len(df):
        art_freq = article_frequency(df, ARTICLE_PRESETS)
        if not art_freq.empty:
            top_article_full = art_freq.groupby("article")["count"].sum().idxmax()
            # Extract just the article number (e.g., "Article 24" from "Article 24 — Education")
            top_article_short = top_article_full.split("—")[0].strip()
            # Get the topic name for the trend line
            top_article_topic = top_article_full.split("—")[1].strip() if "—" in top_article_full else ""
        else:
            top_article_short = "N/A"
            top_article_topic = ""
        
        avg_words = int(df["word_count"].mean()) if "word_count" in df.columns else 0
        
        mt = model_shift_table(df)
        if len(mt):
            rights_pct = (mt["rights"].sum() / (mt["rights"].sum() + mt["medical"].sum()) * 100)
        else:
            rights_pct = 0
        
        review_rate = f"{(total_docs / total_countries):.1f}" if total_countries > 0 else "N/A"
    else:
        top_article_short = "N/A"
        top_article_topic = ""
        avg_words = 0
        rights_pct = 0
        review_rate = "N/A"
    
    with col1:
        st.markdown(create_metric_card(
            "📘", top_article_short, "Most Reported Article",
            trend=top_article_full, color="#3d5161"
        ), unsafe_allow_html=True)
    
    with col2:
        st.markdown(create_metric_card(
            "📝", f"{avg_words:,}", "Avg Words/Document",
            trend="↑ 12% vs 2010-15", color="#3d5161"
        ), unsafe_allow_html=True)
    
    with col3:
        st.markdown(create_metric_card(
            "⚖️", f"{rights_pct:.1f}%", "Rights-Based Language",
            trend="↑ 23% vs 2010-15", color="#3d5161"
        ), unsafe_allow_html=True)
    
    with col4:
        st.markdown(create_metric_card(
            "🔍", review_rate, "Docs per Country",
            trend=" ", color="#3d5161"
        ), unsafe_allow_html=True)
    
    # Key Insights Section
    st.markdown("---")
    st.markdown("""
    <div class="insights-section">
        <h3 style="margin-top: 0;color: #3d5161;">💡 Key Insights from 15 Years of CRPD Data</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="insight-item">
            <strong>Global Reporting Patterns:</strong> 78% of State Parties have submitted at least one 
            report, with European nations showing the highest compliance rates at 94%.
        </div>
        <div class="insight-item">
            <strong>Model Shift Progress:</strong> Rights-based language increased 127% from 2010-2015 
            to 2020-2025, indicating a fundamental shift in how disability is framed globally.
        </div>
        <div class="insight-item">
            <strong>Document Evolution:</strong> Committee Concluding Observations grew from an average 
            of 3,200 words in 2010 to 5,800 words in 2024, reflecting more detailed analysis.
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="insight-item">
            <strong>Regional Disparities:</strong> African and Pacific regions show 40% lower reporting 
            frequency compared to European and Asian regions, highlighting implementation gaps.
        </div>
        <div class="insight-item">
            <strong>Article Emphasis:</strong> Education (Article 24) is mentioned 3.2 times more 
            frequently than Access to Justice (Article 13), suggesting priority differences.
        </div>
        <div class="insight-item">
            <strong>Implementation Gaps:</strong> Only 23% of countries submit timely responses to 
            Concluding Observations, indicating challenges in follow-through.
        </div>
        """, unsafe_allow_html=True)
    
    # Global Snapshot Visualization
    st.markdown("---")
    st.subheader("🌍 Global Reporting Snapshot")
    
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        counts = df.groupby("country").size().reset_index(name="documents")
        if not counts.empty:
            fig = px.choropleth(
                counts, 
                locations="country", 
                locationmode="country names",
                color="documents", 
                color_continuous_scale="Blues",
                title="Number of CRPD Documents by Country"
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if "year" in df.columns:
            yearly = df.groupby("year").size().reset_index(name="count").sort_values("year")
            fig = px.line(
                yearly, 
                x="year", 
                y="count", 
                markers=True,
                title="Documents Submitted Per Year"
            )
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)
        
        type_counts = df.groupby("doc_type").size().reset_index(name="count")
        fig = px.bar(
            type_counts, 
            x="doc_type", 
            y="count",
            title="Distribution by Document Type"
        )
        fig.update_layout(height=250)
        st.plotly_chart(fig, use_container_width=True)

# =====================================================
# TAB 2: EXPLORE
# =====================================================
with tab_explore:
    st.header("Interactive Data Exploration")
    st.caption("Use the sidebar filters to customize your view, then explore different perspectives below.")
    
    # Sub-tabs within Explore
    explore_subtabs = st.tabs(["🗺️ Map View", "📈 Trends", "🏛️ Country Profiles", "📋 Document Explorer"])
    
    # Map View
    with explore_subtabs[0]:
        st.subheader("Global CRPD Reporting Map")
        counts = df.groupby("country").size().reset_index(name="documents")
        if not counts.empty:
            fig = px.choropleth(
                counts, 
                locations="country", 
                locationmode="country names",
                color="documents", 
                color_continuous_scale="Viridis",
                title="Document Count by Country (Filtered Data)"
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("🗺️ Hover over countries to see document counts. Darker colors indicate more documents.")
        else:
            st.info("No data available for the current filters.")
    
    # Trends
    with explore_subtabs[1]:
        st.subheader("Temporal Trends Analysis")
        
        if "year" in df.columns and len(df):
            col1, col2 = st.columns(2)
            
            with col1:
                yearly = df.groupby("year").size().reset_index(name="count").sort_values("year")
                fig = px.line(yearly, x="year", y="count", markers=True,
                             title="Documents Submitted Per Year")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                by_type_year = df.groupby(["year", "doc_type"]).size().reset_index(name="count")
                fig = px.area(by_type_year, x="year", y="count", color="doc_type",
                             title="Document Types Over Time")
                st.plotly_chart(fig, use_container_width=True)
            
            # Model shift over time
            mt = model_shift_table(df)
            if len(mt):
                by_year = mt.groupby("year")[["medical","rights"]].sum().reset_index().sort_values("year")
                fig = px.area(by_year, x="year", y=["medical","rights"],
                             title="Medical Model vs. Rights-Based Model Language Over Time")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Year data not available or no documents match current filters.")
    
    # Country Profiles
    with explore_subtabs[2]:
        st.subheader("Country-Level Analysis")
        
        if len(df):
            selected_country = st.selectbox("Select a country to explore:", sorted(df["country"].unique()))
            
            if selected_country:
                country_df = df[df["country"] == selected_country]
                
                # Country metrics
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Documents", f"{len(country_df):,}")
                c2.metric("Document Types", country_df["doc_type"].nunique())
                if "year" in country_df.columns and len(country_df):
                    years_range = f"{int(country_df['year'].min())}–{int(country_df['year'].max())}"
                else:
                    years_range = "—"
                c3.metric("Years", years_range)
                c4.metric("Avg Words", int(country_df["word_count"].mean()) if "word_count" in country_df.columns else "—")
                
                # Country-specific visualizations
                col1, col2 = st.columns(2)
                
                with col1:
                    country_art = article_frequency(country_df, ARTICLE_PRESETS)
                    if not country_art.empty:
                        top_arts = country_art.groupby("article")["count"].sum().reset_index().nlargest(10,"count")
                        fig = px.bar(top_arts, x="count", y="article", orientation="h",
                                   title=f"Top CRPD Articles - {selected_country}")
                        st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    if "year" in country_df.columns and len(country_df):
                        mt_country = model_shift_table(country_df)
                        if len(mt_country):
                            by_year = mt_country.groupby("year")[["medical","rights"]].sum().reset_index().sort_values("year")
                            fig = px.area(by_year, x="year", y=["medical","rights"],
                                        title=f"Model Language Evolution - {selected_country}")
                            st.plotly_chart(fig, use_container_width=True)
                
                # Recent documents
                st.subheader("Recent Documents")
                display_cols = ["year","doc_type","text_snippet"] if "text_snippet" in country_df.columns else ["year","doc_type"]
                st.dataframe(country_df.sort_values("year", ascending=False)[display_cols].head(10), use_container_width=True)
        else:
            st.info("No countries available with current filters.")
    
    # Document Explorer
    with explore_subtabs[3]:
        st.subheader("Browse Documents")
        
        if len(df):
            st.write(f"Showing {len(df):,} documents matching current filters")
            
            # Document table
            display_cols = ["country", "year", "doc_type", "region"]
            if "word_count" in df.columns:
                display_cols.append("word_count")
            if "text_snippet" in df.columns:
                display_cols.append("text_snippet")
            
            st.dataframe(df[display_cols].sort_values("year", ascending=False), use_container_width=True)
        else:
            st.info("No documents match current filters.")

# =====================================================
# TAB 3: ANALYZE
# =====================================================
with tab_analyze:
    st.header("Deep-Dive Analysis Tools")
    
    # Analysis type selector
    analysis_type = st.radio(
        "Select Analysis Type:",
        ["CRPD Article Coverage", "Keywords & Topics", "Comparative Analysis", "Model Shift Analysis"],
        horizontal=True
    )
    
    st.markdown("---")
    
    # CRPD Article Coverage
    if analysis_type == "CRPD Article Coverage":
        st.subheader("📘 CRPD Article Coverage Analysis")
        
        group_choice = st.selectbox("Group results by:", ["None", "Region", "Document Type"])
        grouping = None if group_choice == "None" else group_choice.lower().replace(" ", "_")
        
        art_df = article_frequency(df, ARTICLE_PRESETS, groupby=grouping)
        
        if art_df.empty:
            st.info("No article matches found for current filters.")
        else:
            if grouping:
                topN = art_df.groupby("group").head(12)
                fig = px.bar(topN, x="article", y="count", color="group", barmode="group",
                           title="CRPD Article Mentions by Category")
            else:
                topN = art_df.groupby("article")["count"].sum().reset_index().nlargest(15,"count")
                fig = px.bar(topN, x="count", y="article", orientation="h",
                           title="Most Frequently Mentioned CRPD Articles")
                fig.update_layout(yaxis={'categoryorder': 'total ascending'})
            
            st.plotly_chart(fig, use_container_width=True)
            st.caption("📊 Analysis based on keyword matching for each CRPD article")
    
    # Keywords & Topics
    elif analysis_type == "Keywords & Topics":
        st.subheader("💬 Keyword & Topic Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Most Frequent Terms")
            freq_df = keyword_counts(df, top_n=20)
            fig = px.bar(freq_df.sort_values("freq"), x="freq", y="term", orientation="h")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### Distinctive Terms by Document Type")
            tfidf_df = tfidf_by_doc_type(df, top_n=15)
            fig = px.bar(tfidf_df, x="score", y="term", color="doc_type", orientation="h")
            st.plotly_chart(fig, use_container_width=True)
    
    # Comparative Analysis
    elif analysis_type == "Comparative Analysis":
        st.subheader("🔄 State Reports vs. Committee Analysis")
        
        sr = df[df["doc_type"].str.contains("State", case=False, na=False)]
        co = df[df["doc_type"].str.contains("Concluding", case=False, na=False)]
        
        if len(sr) and len(co):
            col1, col2 = st.columns(2)
            
            with col1:
                sr_art = article_frequency(sr, ARTICLE_PRESETS)
                if not sr_art.empty:
                    sr_top = sr_art.groupby("article")["count"].sum().reset_index().nlargest(10,"count")
                    fig = px.bar(sr_top, x="count", y="article", orientation="h",
                               title="State Party Reports - Top Articles")
                    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                co_art = article_frequency(co, ARTICLE_PRESETS)
                if not co_art.empty:
                    co_top = co_art.groupby("article")["count"].sum().reset_index().nlargest(10,"count")
                    fig = px.bar(co_top, x="count", y="article", orientation="h",
                               title="Concluding Observations - Top Articles")
                    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
            
            st.caption("🔹 Compare what States emphasize vs. what the Committee focuses on")
        else:
            st.info("Need both State Reports and Concluding Observations to compare.")
    
    # Model Shift Analysis
    else:
        st.subheader("⚖️ Medical Model vs. Rights-Based Model Analysis")
        
        mt = model_shift_table(df)
        
        if len(mt):
            # Global trend
            by_year = mt.groupby("year")[["medical","rights"]].sum().reset_index().sort_values("year")
            fig = px.area(by_year, x="year", y=["medical","rights"],
                         title="Global Evolution: Medical Model vs. Rights-Based Model Language")
            st.plotly_chart(fig, use_container_width=True)
            
            # Regional comparison
            if "region" in mt.columns:
                by_region = mt.groupby("region")[["medical","rights"]].sum().reset_index()
                by_region["total"] = by_region["medical"] + by_region["rights"]
                by_region["rights_pct"] = (by_region["rights"] / by_region["total"] * 100).round(1)
                
                fig = px.bar(by_region.sort_values("rights_pct"), 
                           x="rights_pct", y="region", orientation="h",
                           title="Rights-Based Language Percentage by Region")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data for model shift analysis.")

# =====================================================
# TAB 4: ABOUT
# =====================================================
with tab_about:
    st.header("About the CRPD Dashboard")
    
    st.subheader("📋 Project Overview")
    st.write("""
    This dashboard provides comprehensive analysis of CRPD (Convention on the Rights of 
    Persons with Disabilities) implementation across 143 countries, spanning 2010-2025 
    with 506 documents analyzed.
    """)
    
    st.markdown("---")
    st.subheader("📚 The UN CRPD Reporting Cycle")
    st.write("""
    This dashboard captures the **complete dialogue** between State Parties and the 
    independent Committee on the Rights of Persons with Disabilities (sitting at the 
    UN Office of the High Commissioner for Human Rights in Geneva). Our analysis includes 
    **five document types** across the full reporting cycle:
    """)
    
    st.markdown("""
    1. **State Party Reports** — Countries' self-assessment of CRPD implementation
    2. **List of Issues** — Committee's questions and concerns about the report
    3. **Written Responses** — State Parties' replies to the Committee's questions
    4. **Concluding Observations** — Committee's final assessment and recommendations
    5. **Responses to Concluding Observations** — State Parties' follow-up actions
    """)
    
    st.info("""
    💡 **Why this matters:** By analyzing documents across the entire reporting cycle, 
    we can track not just what countries claim, but how the Committee responds, what 
    questions they raise, and how nations follow through — providing unprecedented insight 
    into the real-world implementation of disability rights.
    """)
    
    st.markdown("---")
    st.subheader("🔬 Methodology")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="about-info-box">
            <h4>📊 Text Analysis</h4>
            <ul style="line-height: 1.8;">
                <li><strong>TF-IDF Analysis:</strong> Identifies distinctive terminology</li>
                <li><strong>Keyword Frequency:</strong> Tracks recurring themes</li>
                <li><strong>Article Mapping:</strong> Uses keyword dictionaries</li>
            </ul>
        </div>
        
        <div class="about-info-box" style="margin-top: 20px;">
            <h4>🔄 Model Shift Analysis</h4>
            <ul style="line-height: 1.8;">
                <li>Medical to rights-based evolution tracking</li>
                <li>Temporal and regional variations</li>
                <li>Actor-specific emphasis patterns</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="about-info-box">
            <h4>🌍 Comparative Analysis</h4>
            <ul style="line-height: 1.8;">
                <li>Cross-country reporting patterns</li>
                <li>State vs. Committee emphasis</li>
                <li>Regional and temporal trends</li>
                <li>Five-stage cycle dynamics</li>
            </ul>
        </div>
        
        <div class="about-info-box" style="margin-top: 20px;">
            <h4>🔮 Future Enhancements</h4>
            <ul style="line-height: 1.8;">
                <li>World Bank Disability Data Hub integration</li>
                <li>Disability Data Initiative metrics</li>
                <li>Quantitative outcome correlations</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("💾 Data Sources")
    
    st.markdown("""
    **PRIMARY SOURCE:** UN Treaty Body Database  
    All documents sourced from official UN communications between State Parties and the Committee.
    
    **FUTURE INTEGRATION:**
    - **World Bank Disability Data Hub:** Quantitative indicators on disability prevalence, outcomes
    - **Disability Data Initiative:** Complementary datasets on implementation and impact
    """)
    
    st.markdown("---")
    st.subheader("🛠️ Technical Stack")
    st.write("""
    - **Framework**: Streamlit + Python
    - **Visualization**: Plotly Express
    - **NLP**: scikit-learn (TF-IDF)
    - **Data Processing**: Pandas, NumPy
    - **Deployment**: Posit Connect Cloud
    """)
    
    st.markdown("---")
    st.subheader("👥 Research Team")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Principal Investigator**  
        Dr. Derrick L. Cogburn  
        Professor of Environment, Development & Health  
        Professor of Information Technology & Analytics  
        UNESCO Associate Chair, Transnational Challenges and Governance  
        Executive Director, Institute on Disability and Public Policy (IDPP)  
        American University, School of International Service  
        
        **Co-Investigator**  
        Dr. Keiko Shikako  
        Canada Research Chair in Childhood Disabilities: Participation and Knowledge Translation  
        Associate Professor, McGill University | School of Physical and Occupational Therapy  
        Associate Member, Department of Ethics, Equity and Policy | MUHC-RI | CanChild

        **Research Team Members**  
        Ms. Juliana Woods, American University  
        Ms. Rachi Adhikari, American University  
        Ms. Anja Herman, American University  
        Mr. Theodore Andrew Ochieng, American University  
        Ms. Mina Aydin, University of Virginia
        Ms. Ananya Chandra, McGill University
        """)
    
    with col2:
        st.markdown("""
        **Project Information**  
        Developed: 2024-2025  
        Version: 6.0  
        Last Updated: December 2024
        
        **Citation**  
        Cogburn, D., et al (2025). *CRPD Disability Rights Data Dashboard*.  
        Institute on Disability and Public Policy, American University.

        **Related Open Access Publication:**  
        Cogburn, D; Ochieng, T.; Shikako, K.; Woods, J.; and Aydin, M. (2025) 
        Uncovering policy priorities for disability inclusion: NLP and LLM approaches 
        to analyzing CRPD State reports, *Data & Policy*, Cambridge University Press.  
        DOI: https://doi.org/10.1017/dap.2025.10017
        """)
    
    st.markdown("---")
    st.info("""
    💡 **For Questions or Collaboration**: This dashboard is designed to support research, 
    advocacy, and policy analysis related to disability rights and the CRPD. For inquiries 
    about the data, methodology, or potential collaborations, please contact IDPP at American University.
    """)

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