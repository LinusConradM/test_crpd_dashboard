import pandas as pd
import streamlit as st


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
        "treatment", "rehabilitation", "therapy", "patient", "disorder", "impairment",
        "illness", "diagnosis", "caregiver", "institution", "special needs", "cure"
    ],
    "Rights-Based Model": [
        "inclusion", "equality", "accessibility", "participation", "autonomy",
        "independent living", "reasonable accommodation", "universal design",
        "dignity", "rights", "empowerment", "access to justice"
    ]
}
