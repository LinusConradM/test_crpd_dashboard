import streamlit as st
import plotly.express as px

from src.analysis import article_frequency, model_shift_table
from src.components import create_metric_card, pct_trend


def render(df, df_all, ARTICLE_PRESETS):
    st.header("Understanding CRPD Implementation")

    # Two-column layout for "What" and "Why"
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="info-box">
            <h4>📘 What is the CRPD?</h4>
            <p>The <strong>Convention on the Rights of Persons with Disabilities (CRPD)</strong>
            is a landmark UN human rights treaty adopted in 2006. The CRPD is also a development instrument, and is aligned with the 2030 Sustainable Development Goals (SDGs) and other global development strategies. It represents a paradigm shift
            from viewing disability through a medical lens to recognizing it as a human rights issue.</p>
            <p><em>Throughout this dashboard, we use "CRPD" as an abbreviation for the Convention.</em></p>
            <h4>🛠️ National Implementation and Monitoring</h4>
            <p>Articles 33, 35, and 36 outline how States implement and report on the CRPD. Article 33 requires States to designate national mechanisms to coordinate implementation and independent monitoring. Article 35 mandates periodic State Party reports to the CRPD Committee detailing progress. Article 36 governs the Committee's review process, including Lists of Issues, State responses, and the Committee's Concluding Observations. Civil society organizations may also submit alternative or "shadow" reports to inform the Committee's review.</p>
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
    if "year" in df.columns and len(df) >= 4:
        sorted_years = sorted(df["year"].dropna().unique())
        mid_year = sorted_years[len(sorted_years) // 2]
        df_early = df[df["year"] < mid_year]
        df_late = df[df["year"] >= mid_year]

        docs_trend = pct_trend(len(df_early), len(df_late))

        early_countries = df_early["country"].nunique()
        late_countries = df_late["country"].nunique()
        diff = late_countries - early_countries
        if diff > 0:
            countries_trend = f"↑ {diff} more countries vs earlier period"
        elif diff < 0:
            countries_trend = f"↓ {abs(diff)} fewer countries vs earlier period"
        else:
            countries_trend = "→ Same countries across periods"
    else:
        docs_trend = " "
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
            top_article_short = top_article_full.split("—")[0].strip()
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
                late_words = df_late["word_count"].mean() if len(df_late) else 0
                words_trend = pct_trend(early_words, late_words)
            else:
                words_trend = " "

            mt_early = model_shift_table(df_early)
            mt_late = model_shift_table(df_late)
            if len(mt_early) and len(mt_late):
                early_r = mt_early["rights"].sum()
                early_m = mt_early["medical"].sum()
                late_r = mt_late["rights"].sum()
                late_m = mt_late["medical"].sum()
                early_rights_pct = (early_r / (early_r + early_m) * 100) if (early_r + early_m) > 0 else 0
                late_rights_pct = (late_r / (late_r + late_m) * 100) if (late_r + late_m) > 0 else 0
                rights_trend = pct_trend(early_rights_pct, late_rights_pct)
            else:
                rights_trend = " "
        else:
            words_trend = " "
            rights_trend = " "
    else:
        top_article_short = "N/A"
        top_article_full = "N/A"
        top_article_topic = ""
        avg_words = 0
        rights_pct = 0
        review_rate = "N/A"
        words_trend = " "
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
        best_reg = region_rates.index[0] if not region_rates.empty else "N/A"
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
                co_mid = co_years[len(co_years) // 2]
                early_w = co_sub[co_sub["year"] < co_mid]["word_count"].mean()
                late_w = co_sub[co_sub["year"] >= co_mid]["word_count"].mean()
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
            worst_reg = region_rates.index[-1]
            disp_pct = (region_rates.iloc[0] - region_rates.iloc[-1]) / region_rates.iloc[0] * 100
            regional_disp = (
                f"{worst_reg} has {disp_pct:.0f}% fewer documents per country than {best_reg}, "
                f"highlighting uneven reporting capacity across regions."
            )
        else:
            regional_disp = f"Only one region found in the current filtered data: {best_reg}."

        # 5. Article emphasis: most-mentioned vs Article 13
        if not art_freq.empty:
            art_totals = art_freq.groupby("article")["count"].sum().sort_values(ascending=False)
            top_name = art_totals.index[0]
            top_cnt = int(art_totals.iloc[0])
            a13_key = next((k for k in art_totals.index if "Article 13" in k), None)
            if a13_key and art_totals[a13_key] > 0 and top_name != a13_key:
                ratio = top_cnt / art_totals[a13_key]
                top_short = top_name.split("—")[1].strip() if "—" in top_name else top_name
                top_num = top_name.split("—")[0].strip()
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
        co_set = set(df[df["doc_type"] == "concluding observations"]["country"].dropna())
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
        model_shift_text = "N/A"
        doc_evolution = "N/A"
        regional_disp = "N/A"
        article_emphasis = "N/A"
        impl_gap = "N/A"

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
        st.caption("🗺️ Explore the full interactive world map in the Map View section of this dashboard.")

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
