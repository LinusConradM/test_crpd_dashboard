#!/usr/bin/env python3
"""Table standards linter for the CRPD Dashboard.

Scans Streamlit source files for common table standards violations.
Run after implementing or modifying any table component.

Usage:
    python scripts/table_lint.py src/
    python scripts/table_lint.py src/tab_explore.py
    python scripts/table_lint.py src/ --rule hardcoded-number
    python scripts/table_lint.py src/ --summary

Exit codes:
    0 = no violations
    1 = violations found

Reference: .claude/references/table-standards.md
"""

import argparse
from pathlib import Path
import re
import sys


class Violation:
    """A single table standards violation."""

    def __init__(self, file: str, line: int, rule: str, message: str):
        self.file = file
        self.line = line
        self.rule = rule
        self.message = message

    def __str__(self) -> str:
        return f"{self.file}:{self.line}  [{self.rule}]  {self.message}"


def check_hardcoded_numbers(filepath: str, lines: list[str]) -> list[Violation]:
    """§1 Content: Detect hardcoded data counts that should use get_dataset_stats().

    Looks for patterns like 'n=585', '155 countries', '193 States Parties'
    with literal numbers that should be computed dynamically.
    """
    violations = []
    patterns = [
        (r"\b(n\s*=\s*)\d{2,}(?!\d*px)", "Hardcoded sample size — use get_dataset_stats()"),
        (
            r"\b\d{2,4}\s+(countries|nations|states)",
            "Hardcoded country count — compute dynamically",
        ),
        (r"\b\d{2,4}\s+States\s+Parties", "Hardcoded States Parties count — compute dynamically"),
        (r"\b\d{2,4}\s+documents", "Hardcoded document count — compute dynamically"),
        (
            r"len\(df\)",
            "len(df) may include NaN rows — use filtered count or yearly['count'].sum()",
        ),
    ]

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue
        for pattern, message in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                violations.append(Violation(filepath, i, "hardcoded-number", message))

    return violations


def check_terminology(filepath: str, lines: list[str]) -> list[Violation]:
    """§1 Treaty terminology: Flag 'countries' without 'States Parties' nearby."""
    violations = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        string_matches = re.findall(r'["\']([^"\']*\bcountries\b[^"\']*)["\']', line, re.IGNORECASE)
        for match in string_matches:
            if "States Parties" not in match and "states parties" not in match.lower():
                violations.append(
                    Violation(
                        filepath,
                        i,
                        "terminology",
                        f'Use "States Parties" instead of "countries" in user-facing text: ...{match[:60]}...',
                    )
                )

    return violations


def check_missing_values(filepath: str, lines: list[str]) -> list[Violation]:
    """§1 Null representation: Flag N/A, null, None used for missing data display."""
    violations = []
    bad_patterns = [
        (r'["\']N/A["\']', 'Use em dash "\u2014" instead of "N/A" for missing data'),
        (r'["\']null["\']', 'Use em dash "\u2014" instead of "null" for missing data'),
        (
            r'["\']None["\']',
            'Use em dash "\u2014" instead of "None" for missing data (unless Python None check)',
        ),
        (
            r'\.fillna\(\s*["\']["\']',
            'fillna with empty string \u2014 use em dash "\u2014" instead',
        ),
        (
            r"\.fillna\(\s*0\s*\)",
            "fillna(0) may conflate missing with zero \u2014 verify this is intentional",
        ),
    ]

    for i, line in enumerate(lines, 1):
        for pattern, message in bad_patterns:
            if re.search(pattern, line):
                violations.append(Violation(filepath, i, "null-representation", message))

    return violations


def check_decimal_precision(filepath: str, lines: list[str]) -> list[Violation]:
    """§2 Precision constraint: Flag format strings with >2 decimal places."""
    violations = []
    patterns = [
        (r":\.\d*[3-9]f", "Decimal precision > 2 places \u2014 max 2 for this dashboard"),
        (r"%\.\d*[3-9]f", "Decimal precision > 2 places \u2014 max 2 for this dashboard"),
        (
            r"round\([^,]+,\s*[3-9]\)",
            "round() with >2 decimal places \u2014 max 2 for this dashboard",
        ),
    ]

    for i, line in enumerate(lines, 1):
        for pattern, message in patterns:
            if re.search(pattern, line):
                if "p_val" in line or "p_value" in line or "pvalue" in line:
                    continue
                violations.append(Violation(filepath, i, "precision", message))

    return violations


def check_csv_download(filepath: str, lines: list[str]) -> list[Violation]:
    """§4 Alternative access: Check that files with tables have CSV download buttons."""
    violations = []
    has_dataframe = False
    has_table = False
    has_download = False
    has_accessible_table = False

    for line in lines:
        if "st.dataframe" in line:
            has_dataframe = True
        if "st.table" in line:
            has_table = True
        if "st.download_button" in line:
            has_download = True
        if "render_accessible_table" in line:
            has_accessible_table = True

    if (has_dataframe or has_table or has_accessible_table) and not has_download:
        violations.append(
            Violation(
                filepath,
                0,
                "csv-download",
                "File contains table(s) but no st.download_button() \u2014 every table needs a CSV download",
            )
        )

    return violations


def check_table_captions(filepath: str, lines: list[str]) -> list[Violation]:
    """§6 Table identification: Check for tables without captions."""
    violations = []

    for i, line in enumerate(lines, 1):
        if "render_accessible_table" in line and ('caption=""' in line or "caption=''" in line):
            violations.append(
                Violation(
                    filepath,
                    i,
                    "missing-caption",
                    "render_accessible_table() called with empty caption",
                )
            )

    for i, line in enumerate(lines, 1):
        if "st.dataframe(" in line or "st.table(" in line:
            has_caption = False
            start = max(0, i - 6)
            for j in range(start, i - 1):
                if any(
                    kw in lines[j]
                    for kw in ["st.caption", "st.subheader", "st.markdown", "<caption>"]
                ):
                    has_caption = True
                    break
            if not has_caption:
                violations.append(
                    Violation(
                        filepath,
                        i,
                        "missing-caption",
                        "st.dataframe()/st.table() without a preceding caption or subheader",
                    )
                )

    return violations


def check_th_scope(filepath: str, lines: list[str]) -> list[Violation]:
    """§4 WCAG structure: Check custom HTML tables for <th scope> attributes."""
    violations = []

    for i, line in enumerate(lines, 1):
        if "<th>" in line and "scope=" not in line:
            violations.append(
                Violation(
                    filepath,
                    i,
                    "wcag-th-scope",
                    '<th> without scope attribute \u2014 use <th scope="col"> or <th scope="row">',
                )
            )

    return violations


def check_hardcoded_colors(filepath: str, lines: list[str]) -> list[Violation]:
    """§2 Colors: Flag hardcoded hex colors in table-related code."""
    violations = []

    table_keywords = ["table", "dataframe", "column", "header", "row", "cell", "stripe", "zebra"]

    for i, line in enumerate(lines, 1):
        if re.search(r"#[0-9A-Fa-f]{3,8}", line):
            context_start = max(0, i - 3)
            context_end = min(len(lines), i + 3)
            context = " ".join(lines[context_start:context_end]).lower()
            if any(kw in context for kw in table_keywords):
                violations.append(
                    Violation(
                        filepath,
                        i,
                        "hardcoded-color",
                        "Hardcoded hex color near table code \u2014 use src/colors.py palette",
                    )
                )

    return violations


def check_column_headers(filepath: str, lines: list[str]) -> list[Violation]:
    """§1 Plain-language headers: Flag DataFrame column names used as display headers."""
    violations = []
    bad_headers = [
        "n_docs",
        "doc_type",
        "un_region",
        "word_count",
        "art_",
        "rights_pct",
        "medical_pct",
        "yr",
        "n_countries",
    ]

    for i, line in enumerate(lines, 1):
        for header in bad_headers:
            if f'"{header}"' in line or f"'{header}'" in line:
                if ".rename" in line and f'"{header}"' in line.split(":")[0]:
                    continue
                if (f'["{header}"]' in line or f"['{header}']" in line) and any(
                    kw in line for kw in ["column_config", "columns=", "header"]
                ):
                    violations.append(
                        Violation(
                            filepath,
                            i,
                            "raw-column-name",
                            f'Column name "{header}" may be shown to users \u2014 use plain-language header',
                        )
                    )

    return violations


ALL_CHECKS = [
    check_hardcoded_numbers,
    check_terminology,
    check_missing_values,
    check_decimal_precision,
    # Disabled: no-data-download policy active (see .claude/references/no-data-download.md)
    # check_csv_download,
    check_table_captions,
    check_th_scope,
    check_hardcoded_colors,
    check_column_headers,
]


def lint_file(filepath: str) -> list[Violation]:
    """Run all checks on a single file."""
    path = Path(filepath)
    if not path.exists():
        print(f"Warning: {filepath} not found, skipping", file=sys.stderr)
        return []
    if path.suffix != ".py":
        return []

    lines = path.read_text(encoding="utf-8").splitlines()
    violations = []
    for check in ALL_CHECKS:
        violations.extend(check(filepath, lines))

    return violations


def lint_directory(dirpath: str) -> list[Violation]:
    """Run all checks on all .py files in a directory (recursive)."""
    violations = []
    for path in sorted(Path(dirpath).rglob("*.py")):
        violations.extend(lint_file(str(path)))
    return violations


def main():
    parser = argparse.ArgumentParser(
        description="Table standards linter for CRPD Dashboard",
        epilog="Reference: .claude/references/table-standards.md",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Files or directories to lint",
    )
    parser.add_argument(
        "--rule",
        help="Only check this rule (e.g., 'hardcoded-number', 'terminology')",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show violation counts by rule instead of individual violations",
    )

    args = parser.parse_args()

    violations = []
    for path in args.paths:
        p = Path(path)
        if p.is_dir():
            violations.extend(lint_directory(str(p)))
        elif p.is_file():
            violations.extend(lint_file(str(p)))
        else:
            print(f"Warning: {path} not found", file=sys.stderr)

    if args.rule:
        violations = [v for v in violations if v.rule == args.rule]

    if args.summary:
        from collections import Counter

        counts = Counter(v.rule for v in violations)
        print(f"\n{'Rule':<25} {'Count':>6}")
        print("-" * 32)
        for rule, count in counts.most_common():
            print(f"{rule:<25} {count:>6}")
        print("-" * 32)
        print(f"{'Total':<25} {len(violations):>6}")
    else:
        for v in violations:
            print(v)

    if violations:
        print(f"\n{len(violations)} violation(s) found.", file=sys.stderr)
        sys.exit(1)
    else:
        print("No violations found.", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
