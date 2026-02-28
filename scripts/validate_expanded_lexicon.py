#!/usr/bin/env python3
"""
Expanded Lexicon Validation Script

This script compares the old and new lexicons to show:
1. Before/after term counts
2. Impact on document coverage
3. Changes in rights-based percentage
4. Sample document analysis
"""

import pandas as pd
import re
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import MODEL_DICT


# Old lexicon for comparison
OLD_MODEL_DICT = {
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


def load_corpus(csv_path="data/crpd_reports.csv"):
    """Load the CRPD reports corpus."""
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip().str.lower()
    return df


def count_model_terms(text, model_dict):
    """Count occurrences of model terms in text."""
    if not isinstance(text, str):
        return {"Medical Model": 0, "Rights-Based Model": 0}
    
    counts = {}
    for model_name, terms in model_dict.items():
        count = 0
        for term in terms:
            pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            count += len(pattern.findall(text))
        counts[model_name] = count
    
    return counts


def calculate_rights_percentage(medical_count, rights_count):
    """Calculate rights-based percentage."""
    total = medical_count + rights_count
    if total == 0:
        return 0.0
    return (rights_count / total) * 100


def compare_lexicons(df):
    """Compare old vs new lexicon performance."""
    print("=" * 80)
    print("LEXICON COMPARISON: OLD vs NEW")
    print("=" * 80)
    
    # Lexicon sizes
    print("\nLEXICON SIZE:")
    print(f"  Old Medical Model: {len(OLD_MODEL_DICT['Medical Model'])} terms")
    print(f"  New Medical Model: {len(MODEL_DICT['Medical Model'])} terms")
    print(f"  Change: +{len(MODEL_DICT['Medical Model']) - len(OLD_MODEL_DICT['Medical Model'])} terms")
    print()
    print(f"  Old Rights-Based Model: {len(OLD_MODEL_DICT['Rights-Based Model'])} terms")
    print(f"  New Rights-Based Model: {len(MODEL_DICT['Rights-Based Model'])} terms")
    print(f"  Change: +{len(MODEL_DICT['Rights-Based Model']) - len(OLD_MODEL_DICT['Rights-Based Model'])} terms")
    
    # Calculate metrics for each document
    old_medical_total = 0
    old_rights_total = 0
    new_medical_total = 0
    new_rights_total = 0
    
    old_rights_percentages = []
    new_rights_percentages = []
    
    print("\n" + "=" * 80)
    print("PROCESSING DOCUMENTS...")
    print("=" * 80)
    
    for idx, row in df.iterrows():
        text = str(row.get('clean_text', ''))
        
        # Old lexicon counts
        old_counts = count_model_terms(text, OLD_MODEL_DICT)
        old_medical_total += old_counts['Medical Model']
        old_rights_total += old_counts['Rights-Based Model']
        old_rights_percentages.append(
            calculate_rights_percentage(old_counts['Medical Model'], old_counts['Rights-Based Model'])
        )
        
        # New lexicon counts
        new_counts = count_model_terms(text, MODEL_DICT)
        new_medical_total += new_counts['Medical Model']
        new_rights_total += new_counts['Rights-Based Model']
        new_rights_percentages.append(
            calculate_rights_percentage(new_counts['Medical Model'], new_counts['Rights-Based Model'])
        )
    
    # Overall statistics
    print("\nOVERALL TERM COUNTS:")
    print(f"  Old Medical Model: {old_medical_total:,}")
    print(f"  New Medical Model: {new_medical_total:,}")
    print(f"  Change: +{new_medical_total - old_medical_total:,} ({((new_medical_total/old_medical_total - 1) * 100):.1f}%)")
    print()
    print(f"  Old Rights-Based Model: {old_rights_total:,}")
    print(f"  New Rights-Based Model: {new_rights_total:,}")
    print(f"  Change: +{new_rights_total - old_rights_total:,} ({((new_rights_total/old_rights_total - 1) * 100):.1f}%)")
    
    # Rights-based percentage
    old_overall_rights_pct = calculate_rights_percentage(old_medical_total, old_rights_total)
    new_overall_rights_pct = calculate_rights_percentage(new_medical_total, new_rights_total)
    
    print("\n" + "=" * 80)
    print("RIGHTS-BASED PERCENTAGE:")
    print("=" * 80)
    print(f"  Old Lexicon: {old_overall_rights_pct:.2f}%")
    print(f"  New Lexicon: {new_overall_rights_pct:.2f}%")
    print(f"  Change: {new_overall_rights_pct - old_overall_rights_pct:+.2f} percentage points")
    
    # Average per-document rights percentage
    old_avg_rights = sum(old_rights_percentages) / len(old_rights_percentages)
    new_avg_rights = sum(new_rights_percentages) / len(new_rights_percentages)
    
    print(f"\n  Old Average (per document): {old_avg_rights:.2f}%")
    print(f"  New Average (per document): {new_avg_rights:.2f}%")
    print(f"  Change: {new_avg_rights - old_avg_rights:+.2f} percentage points")
    
    return {
        'old_medical': old_medical_total,
        'new_medical': new_medical_total,
        'old_rights': old_rights_total,
        'new_rights': new_rights_total,
        'old_rights_pct': old_overall_rights_pct,
        'new_rights_pct': new_overall_rights_pct
    }


def show_new_terms():
    """Display newly added terms."""
    print("\n" + "=" * 80)
    print("NEWLY ADDED TERMS")
    print("=" * 80)
    
    old_medical = set(OLD_MODEL_DICT['Medical Model'])
    new_medical = set(MODEL_DICT['Medical Model'])
    added_medical = new_medical - old_medical
    
    old_rights = set(OLD_MODEL_DICT['Rights-Based Model'])
    new_rights = set(MODEL_DICT['Rights-Based Model'])
    added_rights = new_rights - old_rights
    
    print(f"\nMedical Model (+{len(added_medical)} terms):")
    for term in sorted(added_medical):
        print(f"  + {term}")
    
    print(f"\nRights-Based Model (+{len(added_rights)} terms):")
    for term in sorted(added_rights):
        print(f"  + {term}")


def analyze_sample_documents(df, n_samples=5):
    """Analyze sample documents to show before/after differences."""
    print("\n" + "=" * 80)
    print(f"SAMPLE DOCUMENT ANALYSIS (n={n_samples})")
    print("=" * 80)
    
    # Select random sample
    sample_df = df.sample(n=n_samples, random_state=42)
    
    for idx, row in sample_df.iterrows():
        text = str(row.get('clean_text', ''))
        country = row.get('country', 'Unknown')
        year = row.get('year', 'Unknown')
        doc_type = row.get('doc_type', 'Unknown')
        
        old_counts = count_model_terms(text, OLD_MODEL_DICT)
        new_counts = count_model_terms(text, MODEL_DICT)
        
        old_rights_pct = calculate_rights_percentage(
            old_counts['Medical Model'], old_counts['Rights-Based Model']
        )
        new_rights_pct = calculate_rights_percentage(
            new_counts['Medical Model'], new_counts['Rights-Based Model']
        )
        
        print(f"\nDocument: {country} ({year}) - {doc_type}")
        print(f"  Old: Medical={old_counts['Medical Model']}, Rights={old_counts['Rights-Based Model']}, Rights%={old_rights_pct:.1f}%")
        print(f"  New: Medical={new_counts['Medical Model']}, Rights={new_counts['Rights-Based Model']}, Rights%={new_rights_pct:.1f}%")
        print(f"  Change: Medical +{new_counts['Medical Model'] - old_counts['Medical Model']}, Rights +{new_counts['Rights-Based Model'] - old_counts['Rights-Based Model']}, Rights% {new_rights_pct - old_rights_pct:+.1f}pp")


def main():
    """Run validation analysis."""
    print("\n" + "=" * 80)
    print("EXPANDED LEXICON VALIDATION")
    print("=" * 80)
    print("\nLoading corpus...")
    
    df = load_corpus()
    
    # Show new terms
    show_new_terms()
    
    # Compare lexicons
    results = compare_lexicons(df)
    
    # Analyze sample documents
    analyze_sample_documents(df, n_samples=5)
    
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print("\n✅ Lexicon expanded successfully")
    print(f"✅ Medical Model: 12 → {len(MODEL_DICT['Medical Model'])} terms")
    print(f"✅ Rights-Based Model: 12 → {len(MODEL_DICT['Rights-Based Model'])} terms")
    print(f"✅ Total term occurrences increased: {results['old_medical'] + results['old_rights']:,} → {results['new_medical'] + results['new_rights']:,}")
    print(f"✅ Rights-based percentage: {results['old_rights_pct']:.2f}% → {results['new_rights_pct']:.2f}%")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
