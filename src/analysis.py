import re
import numpy as np
import pandas as pd
import streamlit as st
from collections import Counter

from src.data_loader import MODEL_DICT


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
        return keyword_counts(df, top_n).assign(doc_type="All").rename(columns={"freq": "score"})
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
            "region": r.get("region", "Unknown"),
            "year": r.get("year", np.nan),
            "medical": counts["Medical Model"],
            "rights": counts["Rights-Based Model"],
            "rights_share": counts["Rights-Based Model"] / total
        })
    return pd.DataFrame(rows)
