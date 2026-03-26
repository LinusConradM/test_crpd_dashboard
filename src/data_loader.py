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

    # Map raw doc_type values to display names at load time
    if "doc_type" in df.columns:
        _doc_type_map = {
            "state report": "State Report",
            "loi": "List of Issues (LOI)",
            "written response": "Written Reply",
            "concluding observations": "Concluding Observations",
            "response to concluding observations": "Response to Concluding Observations",
        }
        df["doc_type"] = df["doc_type"].map(_doc_type_map).fillna(df["doc_type"])

    # Fix known country name misspellings
    if "country" in df.columns:
        _country_fixes = {
            "Philipines": "Philippines",
        }
        df["country"] = df["country"].replace(_country_fixes)

    if "text_snippet" not in df.columns and "clean_text" in df.columns:
        import re as _re

        # Patterns that mark the start of substantive content after UN header boilerplate
        _content_markers = _re.compile(
            r"(?:the\s+present\s+document\s+is\s+being\s+issued|"
            r"introduction\s*the\s+committee\s+considered|"
            r"\bintroduction\b|"
            r"a\s+purpose\s+and\s+general\s+obligations|"
            r"purpose\s+and\s+general\s+obligations|"
            r"general\s+obligations|"
            r"the\s+committee\s+considered|"
            r"implementation\s+of\s+the\s+convention|"
            r"consideration\s+of\s+reports)",
            _re.IGNORECASE,
        )
        _boilerplate_start = _re.compile(
            r"^(?:ge\s+e\w*\s+|united\s+nations\s+crpd\b)",
            _re.IGNORECASE,
        )

        def _clean_snippet(text):
            s = str(text)
            if _boilerplate_start.match(s):
                m = _content_markers.search(s)
                if m:
                    s = s[m.start() :].strip()
            words = s.split()
            return " ".join(words[:120]) if words else " ".join(str(text).split()[:120])

        df["text_snippet"] = df["clean_text"].apply(_clean_snippet)

    # Standardize country names into ISO3 codes for accurate organization joining
    try:
        import logging

        import country_converter as coco

        # Suppress non-critical warnings from country_converter
        logging.getLogger("country_converter").setLevel(logging.ERROR)

        cc = coco.CountryConverter()

        # cc.pandas_convert can sometimes return lists for ambiguous/multiple matches.
        # Streamlit's @st.cache_data requires all dataframe elements to be hashable (no lists).
        # We apply a lambda to extract the first string element if a list is returned.
        raw_iso = cc.pandas_convert(series=df["country"], to="ISO3", not_found=None)

        def safe_extract(val):
            if isinstance(val, list):
                return val[0] if len(val) > 0 else None
            return val

        df["iso3"] = raw_iso.apply(safe_extract)

    except Exception as e:
        df["iso3"] = None
        st.warning(f"Failed to load country_converter: {e}")

    return df


@st.cache_data
def get_custom_organizations():
    """Return dictionary of custom political/economic organizations mapping to lists of member ISO3 codes."""
    return {
        "ASEAN": ["BRN", "KHM", "IDN", "LAO", "MYS", "MMR", "PHL", "SGP", "THA", "VNM"],
        "CARICOM": [
            "ATG",
            "BHS",
            "BRB",
            "BLZ",
            "DMA",
            "GRD",
            "GUY",
            "HTI",
            "JAM",
            "MSR",
            "KNA",
            "LCA",
            "VCT",
            "SUR",
            "TTO",
        ],
        "ECOWAS": [
            "BEN",
            "BFA",
            "CPV",
            "CIV",
            "GMB",
            "GHA",
            "GIN",
            "GNB",
            "LBR",
            "MLI",
            "NER",
            "NGA",
            "SEN",
            "SLE",
            "TGO",
        ],
        "SADC": [
            "AGO",
            "BWA",
            "COM",
            "COD",
            "SWZ",
            "LSO",
            "MDG",
            "MWI",
            "MUS",
            "MOZ",
            "NAM",
            "SYC",
            "ZAF",
            "TZA",
            "ZMB",
            "ZWE",
        ],
        "EU": [
            "AUT",
            "BEL",
            "BGR",
            "HRV",
            "CYP",
            "CZE",
            "DNK",
            "EST",
            "FIN",
            "FRA",
            "DEU",
            "GRC",
            "HUN",
            "IRL",
            "ITA",
            "LVA",
            "LTU",
            "LUX",
            "MLT",
            "NLD",
            "POL",
            "PRT",
            "ROU",
            "SVK",
            "SVN",
            "ESP",
            "SWE",
        ],
    }


@st.cache_data
def load_article_dict():
    try:
        from src.crpd_article_dict import ARTICLE_PRESETS

        return ARTICLE_PRESETS
    except Exception as e:
        st.warning(f"Couldn't load article dictionary ({e}); using fallback.")
        return {
            "Article 9 — Accessibility": ["accessibility", "barrier", "universal design"],
            "Article 13 — Access to Justice": ["justice", "court", "legal"],
            "Article 24 — Education": ["education", "school", "inclusive education"],
        }


@st.cache_data
def get_dataset_stats(csv_path: str = "data/crpd_reports.csv") -> dict:
    """
    Return live dataset statistics derived directly from crpd_reports.csv.
    Cached by Streamlit — recomputes only when the file changes.

    Use this function instead of hardcoding any dataset-derived numbers.
    Example:
        stats = get_dataset_stats()
        st.write(f"{stats['n_docs']} documents across {stats['n_countries']} countries")
    """
    df = pd.read_csv(csv_path)
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")

    return {
        "n_docs": len(df),
        "n_countries": int(df["country"].nunique()) if "country" in df.columns else 0,
        "year_min": int(df["year"].min()) if "year" in df.columns else 0,
        "year_max": int(df["year"].max()) if "year" in df.columns else 0,
        "n_doc_types": int(df["doc_type"].nunique()) if "doc_type" in df.columns else 0,
        "n_cols": len(df.columns),
        "regions": sorted(df["region"].dropna().unique().tolist())
        if "region" in df.columns
        else [],
        "doc_types": sorted(df["doc_type"].dropna().unique().tolist())
        if "doc_type" in df.columns
        else [],
    }


COLUMN_DISPLAY_NAMES = {
    "year": "Year",
    "doc_type": "Document Type",
    "country": "State Party",
    "region": "Region",
    "subregion": "Subregion",
    "word_count": "Word Count",
    "text_snippet": "Text Snippet",
    "language": "Language",
    "article_mentions": "Article Mentions",
}


def display_columns(df):
    """Rename raw column names to human-readable display names for tables."""
    return df.rename(columns=COLUMN_DISPLAY_NAMES)


MODEL_DICT = {
    "Medical Model": [
        # Clinical/Diagnostic (high frequency, medical framing)
        "treatment",
        "rehabilitation",
        "therapy",
        "diagnosis",
        "disorder",
        "impairment",
        "illness",
        "medical",
        "health",
        "clinical",
        "symptom",
        "condition",
        # Dependency/Care (caregiving and assistance framing)
        "patient",
        "caregiver",
        "care",
        "assistance",
        "dependent",
        "needs",
        # Deficit-Based Language (emphasizes limitations)
        "disabled",
        "deficiency",
        "abnormal",
        "dysfunction",
        "limitation",
        "suffering",
        # Institutional/Segregated (institutional care model)
        "institution",
        "special needs",
        "specialized",
        "segregated",
        "hospitalization",
        # Treatment-Focused (intervention and cure orientation)
        "cure",
        "intervention",
        "medication",
    ],
    "Rights-Based Model": [
        # Participation & Inclusion (social participation)
        "inclusion",
        "participation",
        "engagement",
        "involvement",
        "mainstream",
        "integrated",
        # Autonomy & Self-Determination (agency and choice)
        "autonomy",
        "independent living",
        "self-determination",
        "choice",
        "control",
        "agency",
        # Equality & Non-Discrimination (rights and equality)
        "equality",
        "rights",
        "equal",
        "non-discrimination",
        "discrimination",
        "protection",
        # Accessibility & Accommodation (barrier removal)
        "accessibility",
        "accessible",
        "reasonable accommodation",
        "universal design",
        "barrier",
        # Empowerment & Advocacy (capacity and voice)
        "empowerment",
        "advocacy",
        "voice",
        "capacity building",
        "leadership",
        # Community & Belonging (community-based services)
        "community",
        "belonging",
        "dignity",
        "access to justice",
        "legal rights",
    ],
}
