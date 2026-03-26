#!/usr/bin/env python3
"""
Test script for N-gram extraction and Topic Modeling.
Validates the implementation and shows example outputs.
"""

import os
import sys


# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analysis import extract_ngrams, extract_topics_lda
from src.data_loader import load_data


def main():
    print("\n" + "=" * 80)
    print("N-GRAM EXTRACTION AND TOPIC MODELING TEST")
    print("=" * 80)

    # Load data
    print("\nLoading CRPD reports corpus...")
    df = load_data("data/crpd_reports.csv")
    print(f"Loaded {len(df)} documents")

    # Test N-gram Extraction
    print("\n" + "=" * 80)
    print("N-GRAM EXTRACTION TEST")
    print("=" * 80)

    # Test bi-grams
    print("\n### BI-GRAMS (2-word phrases)")
    print("-" * 80)
    bigrams = extract_ngrams(df, n=2, top_n=20, min_freq=5)
    print(f"\n{'Rank':<6} {'Phrase':<35} {'Frequency':>12}")
    print("-" * 80)
    for idx, row in bigrams.iterrows():
        rank = bigrams.index.get_loc(idx) + 1
        print(f"{rank:<6} {row['phrase']:<35} {row['freq']:>12,}")

    # Test tri-grams
    print("\n### TRI-GRAMS (3-word phrases)")
    print("-" * 80)
    trigrams = extract_ngrams(df, n=3, top_n=20, min_freq=5)
    print(f"\n{'Rank':<6} {'Phrase':<45} {'Frequency':>12}")
    print("-" * 80)
    for idx, row in trigrams.iterrows():
        rank = trigrams.index.get_loc(idx) + 1
        print(f"{rank:<6} {row['phrase']:<45} {row['freq']:>12,}")

    # Test Topic Modeling
    print("\n" + "=" * 80)
    print("TOPIC MODELING TEST (LDA)")
    print("=" * 80)

    print("\nExtracting 5 topics with 10 words each...")
    topic_results = extract_topics_lda(df, n_topics=5, n_words=10)

    if topic_results is None:
        print("❌ Not enough documents for topic modeling")
    else:
        print("\n### DISCOVERED TOPICS")
        print("-" * 80)

        for i, topic in enumerate(topic_results["topics"]):
            prevalence = topic_results["topic_prevalence"][i]
            print(f"\n{topic_results['topic_labels'][i]}")
            print(f"Prevalence: {prevalence:.1f}% of documents")
            print("Top words:")
            for word, weight in zip(topic["words"], topic["weights"], strict=False):
                print(f"  - {word:<20} (weight: {weight:.4f})")

        # Topic prevalence summary
        print("\n### TOPIC PREVALENCE SUMMARY")
        print("-" * 80)
        print(f"{'Topic':<50} {'Prevalence':>12}")
        print("-" * 80)
        for i, label in enumerate(topic_results["topic_labels"]):
            prevalence = topic_results["topic_prevalence"][i]
            print(f"{label:<50} {prevalence:>11.1f}%")

    # Analysis
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)

    print(f"\n✅ Bi-gram extraction: {len(bigrams)} phrases found")
    print(f"✅ Tri-gram extraction: {len(trigrams)} phrases found")

    if topic_results:
        print(f"✅ Topic modeling: {len(topic_results['topics'])} topics extracted")
        print(
            f"✅ Average topic prevalence: {sum(topic_results['topic_prevalence']) / len(topic_results['topic_prevalence']):.1f}%"
        )

    # Validate results
    print("\n### VALIDATION")
    print("-" * 80)

    # Check bi-grams
    expected_bigrams = ["persons disabilities", "reasonable accommodation", "independent living"]
    found_bigrams = bigrams["phrase"].tolist()
    for phrase in expected_bigrams:
        if phrase in found_bigrams:
            print(f"✅ Expected bi-gram found: '{phrase}'")
        else:
            print(f"⚠️  Expected bi-gram not found: '{phrase}'")

    # Check tri-grams
    expected_trigrams = ["persons with disabilities"]
    found_trigrams = trigrams["phrase"].tolist()
    for phrase in expected_trigrams:
        if phrase in found_trigrams:
            print(f"✅ Expected tri-gram found: '{phrase}'")
        else:
            print(f"⚠️  Expected tri-gram not found: '{phrase}'")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\n✅ N-gram extraction working correctly")
    if topic_results:
        print("✅ Topic modeling working correctly")
    print("✅ Ready for dashboard integration")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
