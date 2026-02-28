#!/usr/bin/env python3
"""
Medical Model Lexicon Analysis Script

This script analyzes the current MODEL_DICT lexicon to:
1. Count frequency of each term in the corpus
2. Calculate document coverage
3. Identify candidate terms for expansion
4. Validate existing terms
"""

import pandas as pd
import re
from collections import Counter
import sys
import os

# Add parent directory to path to import project modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import MODEL_DICT


def load_corpus(csv_path="data/crpd_reports.csv"):
    """Load the CRPD reports corpus."""
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip().str.lower()
    return df


def count_term_frequency(df, term):
    """Count occurrences of a term across all documents using word boundaries."""
    pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
    total_count = 0
    doc_count = 0
    
    for text in df['clean_text'].dropna():
        matches = len(pattern.findall(str(text)))
        if matches > 0:
            total_count += matches
            doc_count += 1
    
    return total_count, doc_count


def analyze_current_lexicon(df):
    """Analyze frequency and coverage of current lexicon terms."""
    print("=" * 80)
    print("CURRENT LEXICON ANALYSIS")
    print("=" * 80)
    print(f"\nTotal documents in corpus: {len(df)}")
    print(f"Total documents with text: {df['clean_text'].notna().sum()}\n")
    
    results = {}
    
    for model_name, terms in MODEL_DICT.items():
        print(f"\n{model_name.upper()} ({len(terms)} terms)")
        print("-" * 80)
        print(f"{'Term':<30} {'Total Count':>12} {'Doc Count':>12} {'Coverage %':>12}")
        print("-" * 80)
        
        model_results = []
        for term in sorted(terms):
            total_count, doc_count = count_term_frequency(df, term)
            coverage_pct = (doc_count / len(df)) * 100
            model_results.append({
                'term': term,
                'total_count': total_count,
                'doc_count': doc_count,
                'coverage_pct': coverage_pct
            })
            print(f"{term:<30} {total_count:>12} {doc_count:>12} {coverage_pct:>11.2f}%")
        
        results[model_name] = model_results
        
        # Summary statistics
        total_counts = sum(r['total_count'] for r in model_results)
        avg_coverage = sum(r['coverage_pct'] for r in model_results) / len(model_results)
        print("-" * 80)
        print(f"{'TOTAL':<30} {total_counts:>12}")
        print(f"{'AVERAGE COVERAGE':<30} {avg_coverage:>11.2f}%")
    
    return results


def calculate_document_coverage(df):
    """Calculate how many documents contain at least one term from each model."""
    print("\n" + "=" * 80)
    print("DOCUMENT COVERAGE ANALYSIS")
    print("=" * 80)
    
    medical_docs = set()
    rights_docs = set()
    both_docs = set()
    neither_docs = set()
    
    for idx, row in df.iterrows():
        text = str(row.get('clean_text', ''))
        if not text or text == 'nan':
            continue
        
        has_medical = any(
            re.search(r'\b' + re.escape(term) + r'\b', text, re.IGNORECASE)
            for term in MODEL_DICT['Medical Model']
        )
        has_rights = any(
            re.search(r'\b' + re.escape(term) + r'\b', text, re.IGNORECASE)
            for term in MODEL_DICT['Rights-Based Model']
        )
        
        if has_medical and has_rights:
            both_docs.add(idx)
        elif has_medical:
            medical_docs.add(idx)
        elif has_rights:
            rights_docs.add(idx)
        else:
            neither_docs.add(idx)
    
    # Only count documents that were actually processed (non-empty clean_text)
    processed_doc_ids = medical_docs | rights_docs | both_docs | neither_docs
    total_docs = len(processed_doc_ids)
    
    if total_docs == 0:
        print("\nNo documents with non-empty 'clean_text' found; coverage statistics not computed.")
    else:
        print(f"\nDocuments with Medical Model terms only: {len(medical_docs)} ({len(medical_docs)/total_docs*100:.1f}%)")
        print(f"Documents with Rights-Based Model terms only: {len(rights_docs)} ({len(rights_docs)/total_docs*100:.1f}%)")
        print(f"Documents with BOTH model terms: {len(both_docs)} ({len(both_docs)/total_docs*100:.1f}%)")
        print(f"Documents with NEITHER model terms: {len(neither_docs)} ({len(neither_docs)/total_docs*100:.1f}%)")
    
    return {
        'medical_only': medical_docs,
        'rights_only': rights_docs,
        'both': both_docs,
        'neither': neither_docs
    }


def extract_candidate_terms(df, top_n=100, min_length=3, max_length=25):
    """Extract most frequent terms not in current lexicon as candidates for expansion."""
    print("\n" + "=" * 80)
    print(f"TOP {top_n} CANDIDATE TERMS (not in current lexicon)")
    print("=" * 80)
    
    # Get all current terms (lowercase for comparison)
    current_terms = set()
    for terms in MODEL_DICT.values():
        current_terms.update(term.lower() for term in terms)
    
    # Count all words in corpus
    word_counter = Counter()
    for text in df['clean_text'].dropna():
        words = re.findall(r'\b[a-z]+\b', str(text).lower())
        word_counter.update(w for w in words if min_length <= len(w) <= max_length)
    
    # Filter out current terms and get top candidates
    candidates = [
        (word, count) for word, count in word_counter.most_common(top_n * 3)
        if word not in current_terms
    ][:top_n]
    
    print(f"\n{'Rank':<6} {'Term':<25} {'Frequency':>12}")
    print("-" * 80)
    for rank, (term, count) in enumerate(candidates, 1):
        print(f"{rank:<6} {term:<25} {count:>12}")
    
    return candidates


def identify_low_frequency_terms(lexicon_results, threshold=10):
    """Identify terms with very low frequency that might be candidates for removal."""
    print("\n" + "=" * 80)
    print(f"LOW FREQUENCY TERMS (appearing in <{threshold} documents)")
    print("=" * 80)
    
    low_freq_terms = []
    
    for model_name, results in lexicon_results.items():
        print(f"\n{model_name}:")
        model_low_freq = [r for r in results if r['doc_count'] < threshold]
        
        if model_low_freq:
            for r in model_low_freq:
                print(f"  - {r['term']}: {r['doc_count']} documents, {r['total_count']} total occurrences")
                low_freq_terms.append((model_name, r['term'], r['doc_count'], r['total_count']))
        else:
            print(f"  (No terms below threshold)")
    
    return low_freq_terms


def analyze_term_cooccurrence(df, model_name, top_n=20):
    """Analyze which terms frequently co-occur with model terms."""
    print("\n" + "=" * 80)
    print(f"TERM CO-OCCURRENCE ANALYSIS: {model_name}")
    print("=" * 80)
    
    model_terms = MODEL_DICT[model_name]
    cooccurrence_counter = Counter()
    
    for text in df['clean_text'].dropna():
        text_str = str(text).lower()
        
        # Check if any model term appears in this document
        has_model_term = any(
            re.search(r'\b' + re.escape(term) + r'\b', text_str, re.IGNORECASE)
            for term in model_terms
        )
        
        if has_model_term:
            # Extract all words from this document
            words = re.findall(r'\b[a-z]{4,}\b', text_str)
            cooccurrence_counter.update(words)
    
    # Remove model terms themselves
    for term in model_terms:
        cooccurrence_counter.pop(term.lower(), None)
    
    # Get top co-occurring terms
    top_cooccurring = cooccurrence_counter.most_common(top_n)
    
    print(f"\nTop {top_n} terms co-occurring with {model_name} terms:")
    print(f"{'Rank':<6} {'Term':<25} {'Frequency':>12}")
    print("-" * 80)
    for rank, (term, count) in enumerate(top_cooccurring, 1):
        print(f"{rank:<6} {term:<25} {count:>12}")
    
    return top_cooccurring


def main():
    """Run complete lexicon analysis."""
    print("\n" + "=" * 80)
    print("MEDICAL MODEL LEXICON ANALYSIS")
    print("=" * 80)
    print("\nLoading corpus...")
    
    df = load_corpus()
    
    # 1. Analyze current lexicon
    lexicon_results = analyze_current_lexicon(df)
    
    # 2. Calculate document coverage
    coverage = calculate_document_coverage(df)
    
    # 3. Extract candidate terms
    candidates = extract_candidate_terms(df, top_n=100)
    
    # 4. Identify low-frequency terms
    low_freq = identify_low_frequency_terms(lexicon_results, threshold=10)
    
    # 5. Analyze co-occurrence for each model
    for model_name in MODEL_DICT.keys():
        analyze_term_cooccurrence(df, model_name, top_n=30)
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Review low-frequency terms for potential removal")
    print("2. Review candidate terms and co-occurrence analysis for expansion")
    print("3. Consult literature and domain experts")
    print("4. Expand lexicon systematically by category")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
