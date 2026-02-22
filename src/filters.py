import streamlit as st

from src.analysis import count_phrases


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


def render_sidebar(df_all, ARTICLE_PRESETS):
    """Render all sidebar widgets and return the filtered DataFrame."""
    st.sidebar.markdown("### \U0001f50d Global Filters")
    st.sidebar.caption("Applied across Explore and Analyze tabs")

    regions = ["All"] + sorted(df_all["region"].dropna().unique())
    region = st.sidebar.selectbox("Region", regions, index=0)

    countries = ["All"] + sorted(
        df_all.loc[(df_all["region"] == region) | (region == "All"), "country"].unique()
    )
    country = st.sidebar.selectbox("Country", countries, index=0)

    doc_types_all = sorted(df_all["doc_type"].unique())
    default_doc_types = [dt for dt in doc_types_all if "state" in dt.lower()]
    doc_types = st.sidebar.multiselect("Document Type", doc_types_all, default=default_doc_types)

    if "year" in df_all.columns:
        ymin, ymax = int(df_all["year"].min()), int(df_all["year"].max())
        year_range = st.sidebar.slider("Year Range", ymin, ymax, (ymin, ymax))
    else:
        year_range = None

    # Article Filter
    st.sidebar.markdown("---")
    st.sidebar.markdown("### \U0001f4d8 CRPD Article Filter")
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

    export_cols = ["country", "year", "doc_type", "region"]
    if "word_count" in df.columns:
        export_cols.append("word_count")
    if "text_snippet" in df.columns:
        export_cols.append("text_snippet")
    st.sidebar.download_button(
        label="\u2b07\ufe0f Download Filtered Data (CSV)",
        data=df[export_cols].to_csv(index=False).encode("utf-8"),
        file_name="crpd_filtered_data.csv",
        mime="text/csv",
        use_container_width=True
    )

    return df
