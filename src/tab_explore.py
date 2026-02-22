import pandas as pd
import streamlit as st
import plotly.express as px

from src.analysis import article_frequency, model_shift_table


def render(df, ARTICLE_PRESETS):
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
                by_year = mt.groupby("year")[["medical", "rights"]].sum().reset_index().sort_values("year")
                fig = px.area(by_year, x="year", y=["medical", "rights"],
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
                        top_arts = country_art.groupby("article")["count"].sum().reset_index().nlargest(10, "count")
                        fig = px.bar(top_arts, x="count", y="article", orientation="h",
                                   title=f"Top CRPD Articles - {selected_country}")
                        st.plotly_chart(fig, use_container_width=True)

                with col2:
                    if "year" in country_df.columns and len(country_df):
                        mt_country = model_shift_table(country_df)
                        if len(mt_country):
                            by_year = mt_country.groupby("year")[["medical", "rights"]].sum().reset_index().sort_values("year")
                            fig = px.area(by_year, x="year", y=["medical", "rights"],
                                        title=f"Model Language Evolution - {selected_country}")
                            st.plotly_chart(fig, use_container_width=True)

                # Recent documents
                st.subheader("Recent Documents")
                display_cols = ["year", "doc_type", "text_snippet"] if "text_snippet" in country_df.columns else ["year", "doc_type"]
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
                top_articles = (
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

            st.dataframe(df_search[display_cols].sort_values("year", ascending=False), use_container_width=True)

            st.download_button(
                label="⬇️ Download as CSV",
                data=df_search[display_cols].sort_values("year", ascending=False).to_csv(index=False).encode("utf-8"),
                file_name="crpd_filtered_data.csv",
                mime="text/csv"
            )
        else:
            st.info("No documents match current filters.")
