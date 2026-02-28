import re
import numpy as np
import pandas as pd
import streamlit as st
from collections import Counter

from src.data_loader import MODEL_DICT


# Pre-compile regex patterns for better performance
_COMPILED_PATTERNS_CACHE = {}


def _get_compiled_pattern(phrase):
    """Get or create a compiled regex pattern for a phrase."""
    if phrase not in _COMPILED_PATTERNS_CACHE:
        pattern = r"\b" + re.escape(phrase) + r"\b"
        _COMPILED_PATTERNS_CACHE[phrase] = re.compile(pattern, re.IGNORECASE)
    return _COMPILED_PATTERNS_CACHE[phrase]


# English stopwords (common words to exclude from frequency analysis)
STOPWORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 
    'by', 'can', 'did', 'do', 'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from', 
    'further', 'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'herself', 'him', 
    'himself', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'itself', 'just', 
    'me', 'might', 'more', 'most', 'must', 'my', 'myself', 'no', 'nor', 'not', 'now', 'of', 
    'off', 'on', 'once', 'only', 'or', 'other', 'our', 'ours', 'ourselves', 'out', 'over', 
    'own', 'same', 'she', 'should', 'so', 'some', 'such', 'than', 'that', 'the', 'their', 
    'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they', 'this', 'those', 'through', 
    'to', 'too', 'under', 'until', 'up', 'very', 'was', 'we', 'were', 'what', 'when', 'where', 
    'which', 'while', 'who', 'whom', 'why', 'will', 'with', 'would', 'you', 'your', 'yours', 
    'yourself', 'yourselves', 'could', 'may', 'also', 'however', 'therefore', 'thus', 'hence',
    'moreover', 'furthermore', 'nevertheless', 'nonetheless', 'meanwhile', 'otherwise', 'whereas',
    'yet', 'still', 'already', 'always', 'never', 'often', 'sometimes', 'usually', 'generally',
    'particularly', 'especially', 'specifically', 'namely', 'including', 'within', 'without',
    'upon', 'via', 'per', 'amongst', 'toward', 'towards', 'throughout', 'across', 'along',
    'around', 'behind', 'beside', 'besides', 'beyond', 'near', 'onto', 'since', 'till',
    'unless', 'unlike', 'whether', 'whose', 'whoever', 'whomever', 'whatever', 'whichever',
    'wherever', 'whenever', 'however', 'indeed', 'rather', 'quite', 'fairly', 'pretty',
    'much', 'many', 'several', 'various', 'certain', 'another', 'others', 'either', 'neither',
    'every', 'each', 'both', 'few', 'less', 'least', 'little', 'enough', 'such', 'own',
    'self', 'selves', 'one', 'two', 'three', 'first', 'second', 'third', 'last', 'next',
    'previous', 'following', 'above', 'below', 'former', 'latter', 'earlier', 'later'
}

# Domain-specific stopwords for CRPD documents (procedural/structural terms)
DOMAIN_STOPWORDS = {
    'committee', 'state', 'party', 'article', 'paragraph', 'report', 'section', 'chapter',
    'annex', 'appendix', 'page', 'document', 'number', 'date', 'year', 'month', 'day', 'act',
    'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september',
    'october', 'november', 'december', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
    'saturday', 'sunday', 'crpd', 'convention', 'united', 'nations', 'general', 'assembly',
    'session', 'meeting', 'agenda', 'item', 'resolution', 'decision', 'recommendation',
    'note', 'letter', 'communication', 'submission', 'reply', 'response', 'observation',
    'concluding', 'initial', 'periodic', 'supplementary', 'additional', 'follow', 'followup',
    'pursuant', 'accordance', 'regard', 'respect', 'concerning', 'regarding', 'relation',
    'reference', 'referred', 'refers', 'referring', 'mentioned', 'noted', 'stated', 'indicated',
    'provided', 'reported', 'informed', 'requested', 'recommended', 'urged', 'called', 'invited',
    'welcomed', 'acknowledged', 'recognized', 'emphasized', 'stressed', 'reiterated', 'recalled',
    'reaffirmed', 'confirmed', 'expressed', 'noted', 'took', 'took', 'made', 'adopted', 'approved',
    'shall', 'should', 'must', 'may', 'might', 'can', 'could', 'would', 'will', 'need', 'needs',
    'ensure', 'ensuring', 'ensured', 'ensure', 'take', 'taking', 'taken', 'make', 'making',
    'provide', 'providing', 'given', 'give', 'giving', 'implement', 'implementing', 'implemented',
    'establish', 'establishing', 'established', 'develop', 'developing', 'developed', 'promote',
    'promoting', 'promoted', 'strengthen', 'strengthening', 'strengthened', 'improve', 'improving',
    'improved', 'enhance', 'enhancing', 'enhanced', 'increase', 'increasing', 'increased',
    'continue', 'continuing', 'continued', 'maintain', 'maintaining', 'maintained', 'support',
    'supporting', 'supported', 'facilitate', 'facilitating', 'facilitated', 'encourage',
    'encouraging', 'encouraged', 'address', 'addressing', 'addressed', 'consider', 'considering',
    'considered', 'review', 'reviewing', 'reviewed', 'monitor', 'monitoring', 'monitored',
    'evaluate', 'evaluating', 'evaluated', 'assess', 'assessing', 'assessed'
}

# Combine all stopwords
ALL_STOPWORDS = STOPWORDS | DOMAIN_STOPWORDS


def count_phrases(text, phrases):
    """Count occurrences of phrases in text using pre-compiled regex patterns."""
    if not isinstance(text, str):
        return 0
    total = 0
    for kw in phrases:
        pattern = _get_compiled_pattern(kw)
        total += len(pattern.findall(text))
    return total


@st.cache_data
def article_frequency(df, article_dict, groupby=None):
    """Highly optimized article frequency calculation using word boundaries and case-insensitive matching."""
    # Pre-process: lowercase all text once for case-insensitive matching
    # This avoids repeated regex operations
    
    rows = []
    iterable = [(None, df)] if not groupby else df.groupby(groupby)
    
    for g, sub in iterable:
        # Initialize counters for all articles
        article_counts = {art: 0 for art in article_dict.keys()}
        
        # Process each document once
        for text in sub["clean_text"]:
            if not isinstance(text, str):
                continue
            
            # Lowercase once for case-insensitive matching
            text_lower = text.lower()
            
            # Count matches for each article
            for art, keywords in article_dict.items():
                for kw in keywords:
                    kw_lower = kw.lower()
                    # Use word-boundary-aware regex for all phrases to avoid partial matches
                    if ' ' in kw_lower:
                        # Multi-word phrase - use cached regex pattern with word boundaries
                        pattern = _get_compiled_pattern(kw)
                        article_counts[art] += len(pattern.findall(text))
                    else:
                        # Single word - use word boundary check with regex (cached)
                        pattern = _get_compiled_pattern(kw)
                        article_counts[art] += len(pattern.findall(text))
        
        # Add non-zero counts to results
        for art, count in article_counts.items():
            if count > 0:
                rows.append({
                    "group": ("All" if g is None else g),
                    "article": art,
                    "count": count
                })
    
    out = pd.DataFrame(rows)
    return out.sort_values("count", ascending=False) if len(out) > 0 else out


@st.cache_data
def keyword_counts(df, top_n=30, remove_stopwords=True, min_word_length=3):
    """
    Extract most frequent meaningful terms from documents.
    
    Args:
        df: DataFrame with 'clean_text' column
        top_n: Number of top terms to return
        remove_stopwords: Whether to filter out common stopwords
        min_word_length: Minimum word length to consider
    
    Returns:
        DataFrame with columns ['term', 'freq'] sorted by frequency
    """
    cnt = Counter()
    
    for text in df["clean_text"].astype(str).tolist():
        # Extract words using regex (handles punctuation better)
        words = re.findall(r'\b[a-z]+\b', text.lower())
        
        # Filter words
        filtered_words = [
            w for w in words
            if len(w) >= min_word_length  # Minimum length
            and (not remove_stopwords or w not in ALL_STOPWORDS)  # Remove stopwords if enabled
            and not w.isdigit()  # Remove pure numbers
        ]
        
        cnt.update(filtered_words)
    
    return pd.DataFrame(
        cnt.items(), 
        columns=["term", "freq"]
    ).sort_values("freq", ascending=False).head(top_n)


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
def extract_ngrams(df, n=2, top_n=20, min_freq=5, remove_stopwords=True):
    """
    Extract most frequent n-grams from documents.
    
    Args:
        df: DataFrame with 'clean_text' column
        n: N-gram size (2 for bi-grams, 3 for tri-grams)
        top_n: Number of top n-grams to return
        min_freq: Minimum document frequency
        remove_stopwords: Whether to filter stopwords
    
    Returns:
        DataFrame with columns ['phrase', 'freq']
    """
    from sklearn.feature_extraction.text import CountVectorizer
    
    # Configure vectorizer
    stop_words = list(ALL_STOPWORDS) if remove_stopwords else None
    vectorizer = CountVectorizer(
        ngram_range=(n, n),
        stop_words=stop_words,
        min_df=min_freq,
        max_df=0.8,  # Ignore phrases in >80% of documents
        lowercase=True
    )
    
    # Extract n-grams
    texts = df['clean_text'].dropna().astype(str).tolist()
    # If there are fewer documents than the minimum frequency threshold,
    # no n-grams can satisfy min_df, so return an empty result.
    if len(texts) < min_freq:
        return pd.DataFrame(columns=['phrase', 'freq'])
    
    X = vectorizer.fit_transform(texts)
    
    # Get frequencies
    phrases = vectorizer.get_feature_names_out()
    freqs = X.sum(axis=0).A1
    
    # Create DataFrame and sort
    ngram_df = pd.DataFrame({
        'phrase': phrases,
        'freq': freqs.astype(int)
    }).sort_values('freq', ascending=False).head(top_n)
    
    return ngram_df


@st.cache_data
def extract_topics_lda(df, n_topics=5, n_words=10, remove_stopwords=True):
    """
    Extract topics using Latent Dirichlet Allocation (LDA).
    
    Args:
        df: DataFrame with 'clean_text' column
        n_topics: Number of topics to extract
        n_words: Number of top words per topic
        remove_stopwords: Whether to filter stopwords
    
    Returns:
        Dictionary with topics, labels, and document-topic distribution
    """
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.decomposition import LatentDirichletAllocation
    
    # Configure vectorizer
    stop_words = list(ALL_STOPWORDS) if remove_stopwords else None
    vectorizer = CountVectorizer(
        stop_words=stop_words,
        min_df=5,  # Ignore terms in <5 documents
    # Create list of document texts
    texts = df['clean_text'].dropna().astype(str).tolist()
    if len(texts) < n_topics:
        # Not enough documents to extract the requested number of topics
        return None
    
    # Configure vectorizer
    stop_words = list(ALL_STOPWORDS) if remove_stopwords else None
    # Use a dynamic min_df to avoid empty vocabularies on small datasets
    min_df_dynamic = 1 if len(texts) < 5 else 5
    vectorizer = CountVectorizer(
        stop_words=stop_words,
        min_df=min_df_dynamic,  # Ignore terms in <min_df_dynamic documents
        max_df=0.7,  # Ignore terms in >70% of documents
        lowercase=True,
        max_features=1000  # Limit vocabulary size
    )
    
    # Create document-term matrix
    try:
        X = vectorizer.fit_transform(texts)
    except ValueError:
        # This typically indicates an empty vocabulary (e.g., after stopword removal)
        return None
    
    # Apply LDA
    lda = LatentDirichletAllocation(
        n_components=n_topics,
        random_state=42,
        max_iter=20,
        learning_method='online'
    )
    doc_topic_dist = lda.fit_transform(X)
    
    # Extract top words per topic
    feature_names = vectorizer.get_feature_names_out()
    topics = []
    for topic_idx, topic in enumerate(lda.components_):
        top_indices = topic.argsort()[-n_words:][::-1]
        top_words = [feature_names[i] for i in top_indices]
        top_weights = [float(topic[i]) for i in top_indices]
        topics.append({
            'topic_id': topic_idx,
            'words': top_words,
            'weights': top_weights
        })
    
    # Generate topic labels (simple heuristic: top 3 words)
    topic_labels = [
        f"Topic {i+1}: {', '.join(t['words'][:3])}"
        for i, t in enumerate(topics)
    ]
    
    # Calculate topic prevalence (% of documents where topic is dominant)
    dominant_topics = doc_topic_dist.argmax(axis=1)
    topic_prevalence = [
        (dominant_topics == i).sum() / len(dominant_topics) * 100
        for i in range(n_topics)
    ]
    
    return {
        'topics': topics,
        'topic_labels': topic_labels,
        'topic_prevalence': topic_prevalence,
        'doc_topic_dist': doc_topic_dist,
        'feature_names': feature_names
    }


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
