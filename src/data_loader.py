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
        # Clinical/Diagnostic (high frequency, medical framing)
        "treatment", "rehabilitation", "therapy", "diagnosis", "disorder", "impairment",
        "illness", "medical", "health", "clinical", "symptom", "condition",
        # Dependency/Care (caregiving and assistance framing)
        "patient", "caregiver", "care", "assistance", "dependent", "needs",
        # Deficit-Based Language (emphasizes limitations)
        "disabled", "deficiency", "abnormal", "dysfunction", "limitation", "suffering",
        # Institutional/Segregated (institutional care model)
        "institution", "special needs", "specialized", "segregated", "hospitalization",
        # Treatment-Focused (intervention and cure orientation)
        "cure", "intervention", "medication"
    ],
    "Rights-Based Model": [
        # Participation & Inclusion (social participation)
        "inclusion", "participation", "engagement", "involvement", "mainstream", "integrated",
        # Autonomy & Self-Determination (agency and choice)
        "autonomy", "independent living", "self-determination", "choice", "control", "agency",
        # Equality & Non-Discrimination (rights and equality)
        "equality", "rights", "equal", "non-discrimination", "discrimination", "protection",
        # Accessibility & Accommodation (barrier removal)
        "accessibility", "accessible", "reasonable accommodation", "universal design", "barrier",
        # Empowerment & Advocacy (capacity and voice)
        "empowerment", "advocacy", "voice", "capacity building", "leadership",
        # Community & Belonging (community-based services)
        "community", "belonging", "dignity", "access to justice", "legal rights"
    ]
}
