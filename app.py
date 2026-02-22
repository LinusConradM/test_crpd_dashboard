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
article_list = ["All Articles"] + sorted(
    list(ARTICLE_PRESETS.keys()),
    key=lambda x: int(x.split()[1])
)
selected_articles = st.sidebar.multiselect(
    "Focus on all or specific articles",
    article_list,
    default=["All Articles"],
    help="Filter analysis to specific CRPD articles. Leave as 'All Articles' to see everything."
)

# Apply filters
df = filter_df(df_all, region, country, doc_types, year_range)

# Apply article filter if specific articles are selected
if selected_articles and "All Articles" not in selected_articles:
    article_keywords = []
    for art in selected_articles:
        if art in ARTICLE_PRESETS:
            article_keywords.extend(ARTICLE_PRESETS[art])
    if article_keywords:
        mask = df["clean_text"].apply(lambda t: count_phrases(t, article_keywords) > 0)
        df = df[mask]

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

st.caption("Developed by the Institute on Disability and Public Policy (IDPP) at American University.")

# -------------------------
# 4-TAB STRUCTURE
# -------------------------
tab1, tab2, tab3, tab4 = st.tabs([
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

    # --- Dynamic trend calculations (early vs late period split) ---
    def pct_trend(early_val, late_val):
        if early_val and early_val > 0:
            pct = (late_val - early_val) / early_val * 100
            arrow = "↑" if pct > 0 else "↓" if pct < 0 else "→"
            return f"{arrow} {abs(pct):.0f}% vs earlier period"
        return " "

    if "year" in df.columns and len(df) >= 4:
        sorted_years = sorted(df["year"].dropna().unique())
        mid_year = sorted_years[len(sorted_years) // 2]
        df_early = df[df["year"] < mid_year]
        df_late  = df[df["year"] >= mid_year]

        docs_trend = pct_trend(len(df_early), len(df_late))

        early_countries = df_early["country"].nunique()
        late_countries  = df_late["country"].nunique()
        diff = late_countries - early_countries
        if diff > 0:
            countries_trend = f"↑ {diff} more countries vs earlier period"
        elif diff < 0:
            countries_trend = f"↓ {abs(diff)} fewer countries vs earlier period"
        else:
            countries_trend = "→ Same countries across periods"
    else:
        docs_trend      = " "
        countries_trend = " "

    # Row 1: Data Coverage Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(create_metric_card(
            "📄", f"{total_docs:,}", "Total Documents",
            trend=docs_trend, color="#3d5161"
        ), unsafe_allow_html=True)

    with col2:
        st.markdown(create_metric_card(
            "🌍", f"{total_countries:,}", "Countries",
            trend=countries_trend, color="#3d5161"
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

        # Dynamic trends for Row 2
        if "year" in df.columns and len(df) >= 4:
            if "word_count" in df.columns:
                early_words = df_early["word_count"].mean() if len(df_early) else 0
                late_words  = df_late["word_count"].mean()  if len(df_late)  else 0
                words_trend = pct_trend(early_words, late_words)
            else:
                words_trend = " "

            mt_early = model_shift_table(df_early)
            mt_late  = model_shift_table(df_late)
            if len(mt_early) and len(mt_late):
                early_r = mt_early["rights"].sum()
                early_m = mt_early["medical"].sum()
                late_r  = mt_late["rights"].sum()
                late_m  = mt_late["medical"].sum()
                early_rights_pct = (early_r / (early_r + early_m) * 100) if (early_r + early_m) > 0 else 0
                late_rights_pct  = (late_r  / (late_r  + late_m)  * 100) if (late_r  + late_m)  > 0 else 0
                rights_trend = pct_trend(early_rights_pct, late_rights_pct)
            else:
                rights_trend = " "
        else:
            words_trend  = " "
            rights_trend = " "
    else:
        top_article_short = "N/A"
        top_article_topic = ""
        avg_words = 0
        rights_pct = 0
        review_rate = "N/A"
        words_trend  = " "
        rights_trend = " "

    with col1:
        st.markdown(create_metric_card(
            "📘", top_article_short, "Most Reported Article",
            trend=top_article_full, color="#3d5161"
        ), unsafe_allow_html=True)

    with col2:
        st.markdown(create_metric_card(
            "📝", f"{avg_words:,}", "Avg Words/Document",
            trend=words_trend, color="#3d5161"
        ), unsafe_allow_html=True)

    with col3:
        st.markdown(create_metric_card(
            "⚖️", f"{rights_pct:.1f}%", "Rights-Based Language",
            trend=rights_trend, color="#3d5161"
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
        <h3 style="margin-top: 0;color: #3d5161;">💡 Key Insights from CRPD Data</h3>
    </div>
    """, unsafe_allow_html=True)

    # --- Compute dynamic insight values ---
    if len(df):
        # 1. Global reporting patterns: best region by docs-per-country
        region_rates = df.groupby("region").apply(
            lambda x: len(x) / x["country"].nunique()
        ).sort_values(ascending=False)
        best_reg  = region_rates.index[0]  if not region_rates.empty else "N/A"
        best_rate = f"{region_rates.iloc[0]:.1f}" if not region_rates.empty else "N/A"
        reporting_summary = (
            f"{total_countries} countries are represented in the current view. "
            f"{best_reg} leads with {best_rate} documents per country on average."
        )

        # 2. Model shift: use already-computed rights_pct and rights_trend
        trend_note = rights_trend.strip() if rights_trend.strip() else "Trend data unavailable for current filters."
        model_shift_text = (
            f"Rights-based language accounts for {rights_pct:.1f}% of model-related terms "
            f"in the current data. {trend_note}"
        )

        # 3. Document evolution: compare early vs late avg word count for concluding observations
        if "word_count" in df.columns and "year" in df.columns and len(df) >= 4:
            co_sub = df[df["doc_type"] == "concluding observations"]
            if len(co_sub) >= 4:
                co_years = sorted(co_sub["year"].dropna().unique())
                co_mid   = co_years[len(co_years) // 2]
                early_w  = co_sub[co_sub["year"] <  co_mid]["word_count"].mean()
                late_w   = co_sub[co_sub["year"] >= co_mid]["word_count"].mean()
                if early_w and late_w:
                    pct_w = (late_w - early_w) / early_w * 100
                    arw = "↑" if pct_w > 0 else "↓" if pct_w < 0 else "→"
                    doc_evolution = (
                        f"Concluding Observations grew {arw} {abs(pct_w):.0f}% in average length "
                        f"(from ~{int(early_w):,} to ~{int(late_w):,} words), reflecting deeper analysis over time."
                    )
                else:
                    doc_evolution = f"Average document length is {avg_words:,} words."
            else:
                doc_evolution = f"Average document length is {avg_words:,} words."
        else:
            doc_evolution = f"Average document length is {avg_words:,} words."

        # 4. Regional disparities: gap between highest and lowest docs-per-country region
        if len(region_rates) > 1:
            worst_reg  = region_rates.index[-1]
            disp_pct   = (region_rates.iloc[0] - region_rates.iloc[-1]) / region_rates.iloc[0] * 100
            regional_disp = (
                f"{worst_reg} has {disp_pct:.0f}% fewer documents per country than {best_reg}, "
                f"highlighting uneven reporting capacity across regions."
            )
        else:
            regional_disp = f"Only one region found in the current filtered data: {best_reg}."

        # 5. Article emphasis: most-mentioned vs Article 13
        if not art_freq.empty:
            art_totals = art_freq.groupby("article")["count"].sum().sort_values(ascending=False)
            top_name   = art_totals.index[0]
            top_cnt    = int(art_totals.iloc[0])
            a13_key    = next((k for k in art_totals.index if "Article 13" in k), None)
            if a13_key and art_totals[a13_key] > 0 and top_name != a13_key:
                ratio      = top_cnt / art_totals[a13_key]
                top_short  = top_name.split("—")[1].strip() if "—" in top_name else top_name
                top_num    = top_name.split("—")[0].strip()
                article_emphasis = (
                    f"{top_short} ({top_num}) is referenced {ratio:.1f}× more than "
                    f"Access to Justice (Article 13), indicating clear priority differences."
                )
            else:
                top_short = top_name.split("—")[1].strip() if "—" in top_name else top_name
                article_emphasis = f"{top_short} is the most frequently referenced article in the current data."
        else:
            article_emphasis = "Article frequency analysis unavailable for current filters."

        # 6. Implementation gaps: % of countries with COs that also filed a response
        co_set   = set(df[df["doc_type"] == "concluding observations"]["country"].dropna())
        resp_set = set(df[df["doc_type"] == "response to concluding observations"]["country"].dropna())
        if co_set:
            resp_pct = len(resp_set & co_set) / len(co_set) * 100
            impl_gap = (
                f"{resp_pct:.0f}% of countries that received Concluding Observations have "
                f"submitted a formal response, indicating follow-through challenges."
            )
        else:
            impl_gap = "Response rate data unavailable for current filters."
    else:
        reporting_summary = "No data available for current filters."
        model_shift_text  = "N/A"
        doc_evolution     = "N/A"
        regional_disp     = "N/A"
        article_emphasis  = "N/A"
        impl_gap          = "N/A"

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div class="insight-item">
            <strong>Global Reporting Patterns:</strong> {reporting_summary}
        </div>
        <div class="insight-item">
            <strong>Model Shift Progress:</strong> {model_shift_text}
        </div>
        <div class="insight-item">
            <strong>Document Evolution:</strong> {doc_evolution}
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="insight-item">
            <strong>Regional Disparities:</strong> {regional_disp}
        </div>
        <div class="insight-item">
            <strong>Article Emphasis:</strong> {article_emphasis}
        </div>
        <div class="insight-item">
            <strong>Implementation Gaps:</strong> {impl_gap}
        </div>
        """, unsafe_allow_html=True)
    
    # Global Snapshot Visualization
    st.markdown("---")
    st.subheader("🌍 Global Reporting Snapshot")
    
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        region_counts = df.groupby("region").size().reset_index(name="documents").sort_values("documents", ascending=True)
        if not region_counts.empty:
            fig = px.bar(
                region_counts,
                x="documents",
                y="region",
                orientation="h",
                title="Documents by Region",
                labels={"documents": "Number of Documents", "region": "Region"},
                color="documents",
                color_continuous_scale="Blues"
            )
            fig.update_layout(height=500, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        st.caption("🗺️ See the full interactive world map in the Explore tab → Map View")
    
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
    explore_subtabs = st.tabs(["🗺️ Map View", "📈 Trends", "🏛️ Country Profiles", "🔀 Compare Countries", "📋 Document Explorer"])
    
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
    
    # Compare Countries
    with explore_subtabs[3]:
        st.subheader("Multi-Country Comparison")
        st.caption("Select 2–5 countries to compare side-by-side across key dimensions.")

        available_countries = sorted(df["country"].unique()) if len(df) else []
        selected_countries = st.multiselect(
            "Select countries to compare:",
            options=available_countries,
            default=available_countries[:2] if len(available_countries) >= 2 else available_countries,
            help="Choose between 2 and 5 countries."
        )

        if len(selected_countries) < 2:
            st.info("Select at least 2 countries to begin comparison.")
        elif len(selected_countries) > 5:
            st.warning("Please select no more than 5 countries for a clear comparison.")
        else:
            cmp_df = df[df["country"].isin(selected_countries)]

            # --- Summary metrics table ---
            st.markdown("#### Summary Metrics")
            summary_rows = []
            for c in selected_countries:
                cdf = cmp_df[cmp_df["country"] == c]
                mt_c = model_shift_table(cdf)
                total_model = mt_c["rights"].sum() + mt_c["medical"].sum() if len(mt_c) else 0
                r_pct = mt_c["rights"].sum() / total_model * 100 if total_model > 0 else 0
                yrange = (
                    f"{int(cdf['year'].min())}–{int(cdf['year'].max())}"
                    if "year" in cdf.columns and len(cdf) else "—"
                )
                summary_rows.append({
                    "Country":         c,
                    "Documents":       len(cdf),
                    "Doc Types":       cdf["doc_type"].nunique(),
                    "Avg Words":       int(cdf["word_count"].mean()) if "word_count" in cdf.columns and len(cdf) else 0,
                    "Rights Lang. %":  f"{r_pct:.1f}%",
                    "Year Range":      yrange,
                })
            st.dataframe(pd.DataFrame(summary_rows).set_index("Country"), use_container_width=True)

            # --- Document volume by type ---
            st.markdown("#### Document Volume by Type")
            doc_type_counts = (
                cmp_df.groupby(["country", "doc_type"]).size().reset_index(name="count")
            )
            fig_vol = px.bar(
                doc_type_counts, x="country", y="count", color="doc_type", barmode="group",
                title="Documents by Type per Country",
                labels={"count": "Documents", "country": "Country", "doc_type": "Type"},
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            st.plotly_chart(fig_vol, use_container_width=True)

            # --- Top articles comparison ---
            st.markdown("#### Top CRPD Articles Referenced")
            art_frames = []
            for c in selected_countries:
                af = article_frequency(cmp_df[cmp_df["country"] == c], ARTICLE_PRESETS)
                if not af.empty:
                    af = af.copy()
                    af["country"] = c
                    art_frames.append(af)

            if art_frames:
                combined_art = pd.concat(art_frames)
                top_articles  = (
                    combined_art.groupby("article")["count"].sum()
                    .nlargest(10).index
                )
                top_art_df = (
                    combined_art[combined_art["article"].isin(top_articles)]
                    .groupby(["country", "article"])["count"].sum().reset_index()
                )
                top_art_df["article_short"] = top_art_df["article"].apply(
                    lambda x: x.split("—")[0].strip() if "—" in x else x
                )
                fig_art = px.bar(
                    top_art_df, x="article_short", y="count", color="country", barmode="group",
                    title="Top 10 Articles Referenced (by country)",
                    labels={"count": "Keyword Mentions", "article_short": "Article", "country": "Country"},
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_art.update_layout(xaxis_tickangle=-35)
                st.plotly_chart(fig_art, use_container_width=True)

            # --- Rights vs Medical language ---
            st.markdown("#### Rights-Based vs. Medical Model Language")
            model_rows = []
            for c in selected_countries:
                mt_c = model_shift_table(cmp_df[cmp_df["country"] == c])
                if len(mt_c):
                    model_rows.append({
                        "Country":       c,
                        "Rights-Based":  int(mt_c["rights"].sum()),
                        "Medical Model": int(mt_c["medical"].sum()),
                    })
            if model_rows:
                model_melt = pd.DataFrame(model_rows).melt(
                    id_vars="Country", var_name="Model", value_name="Count"
                )
                fig_model = px.bar(
                    model_melt, x="Country", y="Count", color="Model", barmode="group",
                    title="Rights-Based vs. Medical Model Language by Country",
                    color_discrete_map={"Rights-Based": "#26a69a", "Medical Model": "#ef5350"}
                )
                st.plotly_chart(fig_model, use_container_width=True)
            else:
                st.info("Not enough model-language data for selected countries.")

    # Document Explorer
    with explore_subtabs[4]:
        st.subheader("Browse Documents")

        if len(df):
            search_query = st.text_input(
                "Search document text",
                placeholder="e.g. inclusive education, legal capacity, reasonable accommodation...",
                help="Searches the full document text within the currently filtered results."
            )

            df_search = df.copy()
            if search_query.strip():
                mask = df_search["clean_text"].astype(str).str.contains(
                    search_query.strip(), case=False, na=False, regex=False
                )
                df_search = df_search[mask]
                st.caption(f"Found **{len(df_search):,}** documents containing '{search_query}' (out of {len(df):,} filtered)")
            else:
                st.caption(f"Showing {len(df_search):,} documents matching current filters")

            # Document table
            display_cols = ["country", "year", "doc_type", "region"]
            if "word_count" in df_search.columns:
                display_cols.append("word_count")
            if "text_snippet" in df_search.columns:
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
        ["CRPD Article Coverage", "Article Deep-Dive", "Keywords & Topics", "Comparative Analysis", "Model Shift Analysis", "Article Co-occurrence"],
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
    elif analysis_type == "Model Shift Analysis":
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

# Article Deep-Dive Analysis
    elif analysis_type == "Article Deep-Dive":
        st.subheader("🔍 Article-Specific Deep-Dive Analysis")
        st.markdown("""
        Explore how a specific CRPD article is represented across countries, regions, 
        document types, and over time.
        """)
        
        # Article selector
        selected_article = st.selectbox(
            "Select CRPD Article to analyze:",
            sorted(list(ARTICLE_PRESETS.keys()), key=lambda x: int(x.split()[1])),
            help="Choose an article to see detailed analysis of its coverage"
        )
        
        st.markdown(f"### 📊 Analysis for **{selected_article}**")
        
        # Get keywords for this article
        article_keywords = ARTICLE_PRESETS[selected_article]
        st.caption(f"**Tracking keywords:** {', '.join(article_keywords[:8])}{'...' if len(article_keywords) > 8 else ''}")
        
        # Calculate mentions across filtered data
        with st.spinner("Analyzing article mentions..."):
            df['article_mentions'] = df['clean_text'].apply(
                lambda t: count_phrases(t, article_keywords)
            )
        
        # Filter to only documents that mention this article
        df_with_article = df[df['article_mentions'] > 0].copy()
        
        if len(df_with_article) == 0:
            st.warning(f"❌ No mentions of **{selected_article}** found in the currently filtered data. Try adjusting your filters in the sidebar.")
        else:
            # Key Metrics
            st.markdown("#### 📈 Key Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            total_mentions = int(df_with_article['article_mentions'].sum())
            docs_with_mentions = len(df_with_article)
            avg_mentions = df_with_article['article_mentions'].mean()
            pct_docs = (len(df_with_article) / len(df) * 100) if len(df) > 0 else 0
            
            col1.metric("Documents Mentioning", f"{docs_with_mentions:,}")
            col2.metric("Total Mentions", f"{total_mentions:,}")
            col3.metric("Avg Mentions/Doc", f"{avg_mentions:.1f}")
            col4.metric("% of Filtered Docs", f"{pct_docs:.1f}%")
            
            st.markdown("---")
            
            # Geographic Analysis
            st.markdown("#### 🌍 Geographic Distribution")
            col1, col2 = st.columns(2)
            
            with col1:
                by_region = df_with_article.groupby('region')['article_mentions'].sum().reset_index()
                by_region = by_region.sort_values('article_mentions', ascending=False)
                if not by_region.empty:
                    fig = px.bar(by_region, x='article_mentions', y='region', orientation='h',
                                title=f"Mentions by Region",
                                labels={'article_mentions': 'Total Mentions', 'region': 'Region'})
                    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(f"📊 {selected_article.split('—')[0].strip()} is most discussed in {by_region.iloc[0]['region']}")
            
            with col2:
                by_country = df_with_article.groupby('country')['article_mentions'].sum().reset_index()
                by_country = by_country.nlargest(15, 'article_mentions')
                if not by_country.empty:
                    fig = px.bar(by_country, x='article_mentions', y='country', orientation='h',
                                title=f"Top 15 Countries by Mentions",
                                labels={'article_mentions': 'Total Mentions', 'country': 'Country'})
                    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(f"🌍 {by_country.iloc[0]['country']} mentions this article most frequently")
            
            # Document Type Analysis
            st.markdown("---")
            st.markdown("#### 📄 Document Type Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                by_doctype = df_with_article.groupby('doc_type')['article_mentions'].sum().reset_index()
                by_doctype = by_doctype.sort_values('article_mentions', ascending=False)
                if not by_doctype.empty:
                    fig = px.bar(by_doctype, x='doc_type', y='article_mentions',
                                title=f"Mentions by Document Type",
                                labels={'article_mentions': 'Total Mentions', 'doc_type': 'Document Type'})
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Pie chart showing distribution
                if not by_doctype.empty:
                    fig = px.pie(by_doctype, values='article_mentions', names='doc_type',
                                title=f"Distribution Across Document Types")
                    st.plotly_chart(fig, use_container_width=True)
            
            if not by_doctype.empty:
                top_doctype = by_doctype.iloc[0]
                st.caption(f"📋 Most mentioned in **{top_doctype['doc_type']}** ({top_doctype['article_mentions']} mentions)")
            
            # Temporal Analysis
            if 'year' in df_with_article.columns and len(df_with_article) > 0:
                st.markdown("---")
                st.markdown("#### 📅 Temporal Trends")
                
                by_year = df_with_article.groupby('year')['article_mentions'].sum().reset_index().sort_values('year')
                if not by_year.empty:
                    fig = px.line(by_year, x='year', y='article_mentions', markers=True,
                                 title=f"Mentions Over Time",
                                 labels={'article_mentions': 'Total Mentions', 'year': 'Year'})
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Calculate trend
                    if len(by_year) >= 2:
                        first_year_mentions = by_year.iloc[0]['article_mentions']
                        last_year_mentions = by_year.iloc[-1]['article_mentions']
                        if first_year_mentions > 0:
                            pct_change = ((last_year_mentions - first_year_mentions) / first_year_mentions * 100)
                            trend_emoji = "📈" if pct_change > 0 else "📉" if pct_change < 0 else "➡️"
                            st.caption(f"{trend_emoji} Mentions changed by {pct_change:+.1f}% from {int(by_year.iloc[0]['year'])} to {int(by_year.iloc[-1]['year'])}")
            
            # Top Documents
            st.markdown("---")
            st.markdown("#### 📑 Documents with Most Mentions")
            
            display_cols = ['country', 'year', 'doc_type', 'article_mentions']
            if 'region' in df_with_article.columns:
                display_cols.insert(1, 'region')
            if 'text_snippet' in df_with_article.columns:
                display_cols.append('text_snippet')
            
            top_docs = df_with_article.nlargest(15, 'article_mentions')[display_cols].copy()
            top_docs = top_docs.rename(columns={'article_mentions': 'Mentions'})
            st.dataframe(top_docs, use_container_width=True)
            st.caption(f"📊 Showing top 15 documents mentioning {selected_article.split('—')[0].strip()}")

            # Article 13 Spotlight — extra analysis for Access to Justice
            if "Article 13" in selected_article:
                st.markdown("---")
                st.markdown("#### ⚖️ Article 13 Spotlight: Access to Justice")
                st.caption("Additional analysis drawn from justice-related language in the filtered documents.")

                col1, col2 = st.columns(2)

                with col1:
                    freq_df = keyword_counts(df_with_article, top_n=20)
                    if not freq_df.empty:
                        fig = px.bar(
                            freq_df.sort_values("freq"),
                            x="freq", y="term", orientation="h",
                            title="Top Terms in Article 13 Documents",
                            labels={"freq": "Frequency", "term": "Term"}
                        )
                        fig.update_layout(height=450)
                        st.plotly_chart(fig, use_container_width=True)
                        st.caption("Most frequent words in documents mentioning Article 13.")

                with col2:
                    justice_keywords = ["justice", "court", "legal", "tribunal", "procedural",
                                        "police", "prison", "lawyer", "representation", "fair trial"]
                    concern_keywords = ["barrier", "lack", "inaccessible", "discrimination",
                                        "concern", "obstacle", "failure", "inadequate"]
                    if len(df_with_article):
                        justice_total = df_with_article["clean_text"].apply(
                            lambda t: count_phrases(t, justice_keywords)
                        ).sum()
                        concern_total = df_with_article["clean_text"].apply(
                            lambda t: count_phrases(t, concern_keywords)
                        ).sum()
                        tone_df = pd.DataFrame({
                            "Category": ["Justice Access Terms", "Concern/Barrier Terms"],
                            "Count": [int(justice_total), int(concern_total)]
                        })
                        fig = px.bar(
                            tone_df, x="Category", y="Count",
                            title="Justice Access vs. Concern Language",
                            color="Category",
                            color_discrete_map={
                                "Justice Access Terms": "#26a69a",
                                "Concern/Barrier Terms": "#ef5350"
                            }
                        )
                        fig.update_layout(height=450, showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
                        st.caption("Higher concern language signals areas flagged by the Committee.")

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
