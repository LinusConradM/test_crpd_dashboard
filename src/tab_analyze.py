import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

from src.analysis import (
    article_frequency,
    count_phrases,
    keyword_counts,
    model_shift_table,
    tfidf_by_doc_type,
    extract_ngrams,
)


def render(df, ARTICLE_PRESETS):
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
                topN = art_df.groupby("article")["count"].sum().reset_index().nlargest(15, "count")
                fig = px.bar(topN, x="count", y="article", orientation="h",
                           title="Most Frequently Mentioned CRPD Articles")
                fig.update_layout(yaxis={'categoryorder': 'total ascending'})

            st.plotly_chart(fig, use_container_width=True)
            st.caption("📊 Analysis based on keyword matching for each CRPD article")

    # Keywords & Topics
    elif analysis_type == "Keywords & Topics":
        st.subheader("💬 Keyword & Topic Analysis")

        # Row 1: Single words
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Most Frequent Terms")
            freq_df = keyword_counts(df, top_n=20)
            fig = px.bar(freq_df.sort_values("freq"), x="freq", y="term", orientation="h",
                        labels={"freq": "Frequency", "term": "Term"})
            fig.update_layout(
                height=500,
                yaxis={'categoryorder': 'total ascending'},
                margin=dict(l=20, r=20, t=40, b=20),
                yaxis_title=None
            )
            fig.update_yaxes(automargin=True)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Distinctive Terms by Document Type")
            tfidf_df = tfidf_by_doc_type(df, top_n=15)
            fig = px.bar(tfidf_df, x="score", y="term", color="doc_type", orientation="h",
                        labels={"score": "TF-IDF Score", "term": "Term", "doc_type": "Document Type"})
            fig.update_layout(
                height=500,
                margin=dict(l=20, r=20, t=40, b=20),
                yaxis_title=None
            )
            fig.update_yaxes(automargin=True)
            st.plotly_chart(fig, use_container_width=True)

        # Row 2: Phrases
        st.markdown("#### Phrase Extraction Settings")
        settings_col1, settings_col2 = st.columns([2, 1])
        with settings_col1:
            enable_phrases = st.checkbox("Enable phrase extraction", value=True)
        with settings_col2:
            min_freq = st.number_input(
                "Min phrase frequency",
                min_value=1,
                max_value=100,
                value=5,
                step=1,
            )

        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Common 2-Word Phrases")
            if enable_phrases:
                with st.spinner("Extracting phrases..."):
                    bigram_df = extract_ngrams(df, n=2, top_n=20, min_freq=min_freq)

                if not bigram_df.empty:
                    fig = px.bar(
                        bigram_df.sort_values("freq"),
                        x="freq",
                        y="phrase",
                        orientation="h",
                        labels={"freq": "Frequency", "phrase": "Phrase"},
                    )
                    fig.update_layout(
                        height=500,
                        yaxis={"categoryorder": "total ascending"},
                        margin=dict(l=20, r=20, t=40, b=20),
                        yaxis_title=None,
                    )
                    fig.update_yaxes(automargin=True)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No phrases found with current filters.")
            else:
                st.info("Enable phrase extraction to view common 2-word phrases.")

        with col2:
            st.markdown("#### Common 3-Word Phrases")
            if enable_phrases:
                with st.spinner("Extracting phrases..."):
                    trigram_df = extract_ngrams(df, n=3, top_n=20, min_freq=min_freq)

                if not trigram_df.empty:
                    fig = px.bar(
                        trigram_df.sort_values("freq"),
                        x="freq",
                        y="phrase",
                        orientation="h",
                        labels={"freq": "Frequency", "phrase": "Phrase"},
                    )
                    fig.update_layout(
                        height=500,
                        yaxis={"categoryorder": "total ascending"},
                        margin=dict(l=20, r=20, t=40, b=20),
                        yaxis_title=None,
                    )
                    fig.update_yaxes(automargin=True)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No phrases found with current filters.")
            else:
                st.info("Enable phrase extraction to view common 3-word phrases.")

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
                    sr_top = sr_art.groupby("article")["count"].sum().reset_index().nlargest(10, "count")
                    fig = px.bar(sr_top, x="count", y="article", orientation="h",
                               title="State Party Reports - Top Articles")
                    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                co_art = article_frequency(co, ARTICLE_PRESETS)
                if not co_art.empty:
                    co_top = co_art.groupby("article")["count"].sum().reset_index().nlargest(10, "count")
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
            by_year = mt.groupby("year")[["medical", "rights"]].sum().reset_index().sort_values("year")
            fig = px.area(by_year, x="year", y=["medical", "rights"],
                         title="Global Evolution: Medical Model vs. Rights-Based Model Language")
            st.plotly_chart(fig, use_container_width=True)

            # Regional comparison
            if "region" in mt.columns:
                by_region = mt.groupby("region")[["medical", "rights"]].sum().reset_index()
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
            article_mentions = df['clean_text'].apply(
                lambda t: count_phrases(t, article_keywords)
            )

        # Filter to only documents that mention this article
        df_with_article = df[article_mentions > 0].copy()
        df_with_article['article_mentions'] = article_mentions[article_mentions > 0]

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
                                title="Mentions by Region",
                                labels={'article_mentions': 'Total Mentions', 'region': 'Region'})
                    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(f"📊 {selected_article.split('—')[0].strip()} is most discussed in {by_region.iloc[0]['region']}")

            with col2:
                by_country = df_with_article.groupby('country')['article_mentions'].sum().reset_index()
                by_country = by_country.nlargest(15, 'article_mentions')
                if not by_country.empty:
                    fig = px.bar(by_country, x='article_mentions', y='country', orientation='h',
                                title="Top 15 Countries by Mentions",
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
                                title="Mentions by Document Type",
                                labels={'article_mentions': 'Total Mentions', 'doc_type': 'Document Type'})
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Pie chart showing distribution
                if not by_doctype.empty:
                    fig = px.pie(by_doctype, values='article_mentions', names='doc_type',
                                title="Distribution Across Document Types")
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
                                 title="Mentions Over Time",
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

    # Article Co-occurrence Analysis
    elif analysis_type == "Article Co-occurrence":
        st.subheader("🔗 Article Co-occurrence Analysis")
        st.markdown("""
        Discover which CRPD articles tend to appear **together** in the same documents.
        Strong connections indicate articles that are commonly addressed as a cluster —
        revealing thematic overlaps and policy linkages in CRPD reporting.
        """)

        if not len(df):
            st.info("No data available with current filters.")
        else:
            # Show data info
            st.caption(f"Analyzing {len(df)} documents...")
            
            top_n = st.slider(
                "Number of articles to include (ranked by frequency):",
                min_value=10, max_value=25, value=15, step=5
            )

            with st.spinner("Computing co-occurrence matrix… This may take a moment on first load."):
                try:
                    art_freq_co = article_frequency(df, ARTICLE_PRESETS)

                    if art_freq_co.empty:
                        st.warning("No article matches found for current filters. Try adjusting your filters in the sidebar.")
                    else:
                        top_arts = (
                            art_freq_co.groupby("article")["count"].sum()
                            .sort_values(ascending=False)
                            .head(top_n)
                            .index.tolist()
                        )

                        if len(top_arts) < 2:
                            st.warning(f"Only {len(top_arts)} article(s) found. Need at least 2 articles for co-occurrence analysis. Try adjusting your filters.")
                        else:
                            # Build a binary presence matrix: documents × top articles
                            presence = {
                                art: df["clean_text"].apply(
                                    lambda t: int(count_phrases(t, ARTICLE_PRESETS[art]) > 0)
                                )
                                for art in top_arts
                            }
                            presence_df = pd.DataFrame(presence)

                            # Co-occurrence matrix via dot product
                            cooc = presence_df.T @ presence_df

                            # Short axis labels: "Art. 13" instead of full name
                            short_labels = {
                                art: art.split("—")[0].strip().replace("Article ", "Art. ")
                                for art in top_arts
                            }
                            cooc.index = [short_labels[a] for a in cooc.index]
                            cooc.columns = [short_labels[a] for a in cooc.columns]

                            # Zero diagonal so self-occurrence doesn't dominate the colour scale
                            cooc_display = cooc.copy().astype(float)
                            np.fill_diagonal(cooc_display.values, 0)

                            # Heatmap
                            fig_hm = px.imshow(
                                cooc_display,
                                title=f"Article Co-occurrence Heatmap (Top {top_n} Articles)",
                                color_continuous_scale="Blues",
                                labels={"color": "Docs with Both"},
                                aspect="auto"
                            )
                            fig_hm.update_layout(height=560)
                            st.plotly_chart(fig_hm, use_container_width=True)
                            st.caption(
                                "Each cell shows how many documents mention **both** articles. "
                                "Darker = more documents address the pair together."
                            )

                            # Top co-occurring pairs ranked bar chart
                            st.markdown("#### Top Co-occurring Article Pairs")
                            arts = list(cooc_display.index)
                            pairs = []
                            for i in range(len(arts)):
                                for j in range(i + 1, len(arts)):
                                    val = int(cooc_display.iloc[i, j])
                                    if val > 0:
                                        pairs.append({"Pair": f"{arts[i]}  +  {arts[j]}", "Documents": val})

                            if pairs:
                                pairs_df = (
                                    pd.DataFrame(pairs)
                                    .sort_values("Documents", ascending=False)
                                    .head(15)
                                )
                                fig_pairs = px.bar(
                                    pairs_df, x="Documents", y="Pair", orientation="h",
                                    title="Top 15 Most Frequently Co-occurring Article Pairs",
                                    labels={"Documents": "Documents Mentioning Both", "Pair": "Article Pair"},
                                    color="Documents",
                                    color_continuous_scale="Blues"
                                )
                                fig_pairs.update_layout(
                                    yaxis={"categoryorder": "total ascending"},
                                    height=520,
                                    coloraxis_showscale=False
                                )
                                st.plotly_chart(fig_pairs, use_container_width=True)
                                st.caption(
                                    "Articles that frequently co-occur may indicate **policy clusters** — "
                                    "issues the Committee or States tend to address together."
                                )
                            else:
                                st.info("No co-occurring pairs found for current filters.")
                
                except Exception as e:
                    st.error(f"An error occurred while computing co-occurrence: {str(e)}")
                    st.info("This may be due to insufficient data, your current filter settings, or a timeout. Try adjusting your filters or selecting a smaller data subset.")

