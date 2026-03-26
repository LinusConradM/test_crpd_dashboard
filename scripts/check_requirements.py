#!/usr/bin/env python3
"""
check_requirements.py — Pre-commit requirements guard for CRPD Dashboard.

Runs the dependency scanner and BLOCKS the commit if:
  - Any package imported in source is missing from requirements.txt
  - Any pinned version in requirements.txt doesn't match what's installed

Exits 0 (allow commit) only when requirements.txt is 100% aligned.
Exits 1 (block commit) if mismatches or missing entries are found.

Known dev-only packages that are allowed to be not-installed locally:
  playwright, axe-playwright-python

Known import-name / pip-name mismatches that are not violations:
  faiss  →  faiss-cpu  (import 'faiss', installed as 'faiss-cpu')

Usage:
    python scripts/check_requirements.py          # run check
    python scripts/check_requirements.py --fix    # print fix instructions
"""

import json
from pathlib import Path
import subprocess
import sys


# ── Packages that are allowed to be not-installed locally (dev/CI tools) ──
DEV_ONLY_PACKAGES = {"playwright", "axe-playwright-python"}

# ── Import names whose pip package differs — not a violation ──
KNOWN_ALIASES = {
    "faiss",  # imported as 'faiss', installed as 'faiss-cpu' — already in requirements.txt
    "docx",  # imported as 'docx', installed as 'python-docx' — already in requirements.txt
    "fpdf",  # imported as 'fpdf', installed as 'fpdf2' — already in requirements.txt
    "branca",  # transitive dependency of folium — installed automatically
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCANNER = PROJECT_ROOT / ".claude" / "skills" / "sync-requirements" / "scripts" / "scan_imports.py"


def run_scanner() -> dict:
    result = subprocess.run(
        [sys.executable, str(SCANNER)],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode != 0:
        print(f"❌ Scanner failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def main() -> int:
    fix_mode = "--fix" in sys.argv

    print("🔍 Checking requirements.txt alignment...", flush=True)
    report = run_scanner()
    summary = report["summary"]

    # ── Filter known aliases out of not_installed ──
    not_installed = [
        p for p in summary["not_installed"] if p not in DEV_ONLY_PACKAGES and p not in KNOWN_ALIASES
    ]

    missing = [p for p in summary["missing_from_requirements"] if p not in KNOWN_ALIASES]
    mismatches = summary["version_mismatch"]
    violations = missing + mismatches + not_installed

    # ── Print results ──
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║         REQUIREMENTS ALIGNMENT CHECK                    ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    if missing:
        print("🔴 MISSING from requirements.txt (imported in code but not listed):")
        for pkg in missing:
            installed = report["packages"].get(pkg, {}).get("installed_version", "?")
            print(f"   {pkg}  (installed: {installed})")
        print()

    if mismatches:
        print("🔴 VERSION MISMATCH (pinned ≠ installed):")
        for m in mismatches:
            print(f"   {m}")
        print()

    if not_installed:
        print("🔴 NOT INSTALLED (in requirements.txt but missing from env):")
        for pkg in not_installed:
            print(f"   {pkg}")
        print()

    dev_skipped = [p for p in summary["not_installed"] if p in DEV_ONLY_PACKAGES]
    if dev_skipped:
        print(f"⚪ Skipped (dev-only, not required locally): {', '.join(dev_skipped)}")
        print()

    if not violations:
        print(f"✅ requirements.txt is 100% aligned  ({len(summary['up_to_date'])} packages)")
        print()
        return 0

    # ── Violations found — block commit ──
    print(f"❌ COMMIT BLOCKED — {len(violations)} requirement violation(s) found.")
    print()
    print("Fix options:")
    print("  1. Run:  python scripts/check_requirements.py --fix")
    print("     to see exact commands needed.")
    print()
    print("  2. Or run the sync-requirements skill in Claude:")
    print('     say "sync requirements" to auto-fix and update requirements.txt')
    print()

    if fix_mode:
        print("── FIX INSTRUCTIONS ────────────────────────────────────────")
        if missing:
            print("\nAdd missing packages to requirements.txt:")
            for pkg in missing:
                installed = report["packages"].get(pkg, {}).get("installed_version", "UNKNOWN")
                print(f"  echo '{pkg}=={installed}' >> requirements.txt")
        if mismatches:
            print("\nUpdate pinned versions in requirements.txt:")
            for m in mismatches:
                parts = m.split(": pinned ")
                if len(parts) == 2:
                    pkg = parts[0]
                    rest = parts[1].split(", installed ")
                    if len(rest) == 2:
                        pinned, installed = rest
                        print(f"  # Change: {pkg}=={pinned}  →  {pkg}=={installed}")
        if not_installed:
            print("\nInstall missing packages:")
            for pkg in not_installed:
                spec = report["packages"].get(pkg, {}).get("requirements_spec", "")
                print(f"  pip install '{pkg}{spec}'")
        print("────────────────────────────────────────────────────────────")

    return 1


if __name__ == "__main__":
    sys.exit(main())
