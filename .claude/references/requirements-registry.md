---
name: requirements-registry
description: >
  Machine-readable registry of all 250 CRPD Dashboard requirements.
  Used by the compliance-audit skill and PM Orchestrator for quality gates.
  Updated after each audit cycle. Last audit: 2026-03-23.
version: 1.0.0
---

# CRPD Dashboard — Requirements Registry

This reference file is the single source of truth for all tracked requirements.
The compliance-audit skill reads this file and verifies each item against the codebase.
The PM Orchestrator references this before any SHIP decision.

## Status Legend

- ✅ Verified in code (with date of last verification)
- 🔧 Approved but not yet verified in code
- ❌ Not implemented
- ⏸️ Intentionally deferred (with reason)
- 🔴 REGRESSION — was passing, now failing

## Verification Commands Quick Reference

```bash
# Agent system
python scripts/validate_agent_system.py

# Ruff
ruff check src/

# Terminology scan
grep -rn '"[Cc]ountr' src/tab_overview.py src/tab_explore.py app.py | grep -v "country_\|country'\|\.country\|#"

# Hardcoded numbers
grep -rn '"585\|"155\|"193' src/ app.py

# Hardcoded colors (outside colors.py)
grep -rn '#[0-9a-fA-F]\{6\}' src/tab_overview.py src/tab_explore.py | grep -v "import\|from\|#.*comment"

# Font size violations
grep -rn 'font-size.*[0-9]px' src/ | grep -v "1[4-9]px\|[2-9][0-9]px\|[0-9][0-9][0-9]px"

# XSS surface
grep -rn 'unsafe_allow_html=True' src/ | wc -l

# Security: user input to HTML
grep -n 'html.escape\|bleach.clean' src/tab_chat.py src/tab_brief.py

# Alt-text coverage
grep -rn 'sr-only' src/tab_overview.py src/tab_explore.py | wc -l

# datetime.now for reporting gaps
grep -rn 'datetime.now' src/tab_explore.py

# Budget storage
grep -n 'session_state.*budget\|budget.*session_state' src/llm.py

# Free-tier commitment
grep -rn 'free.*always\|always.*free\|never.*paywall' src/ app.py
```

## Priority Classification

**P0 — Safety/Correctness:** Data integrity bugs, XSS, crashes, factually wrong output
**P1 — WCAG/Treaty:** Accessibility failures, terminology violations on a disability rights platform
**P2 — Credibility:** Framing, overclaiming, methodology disclosure — affects stakeholder trust
**P3 — Polish:** Performance, code structure, color consistency — improves quality but not blocking

## Current Gap Summary (as of 2026-03-23)

### P0 Gaps (fix immediately)
- 8.1.1: Narrative hardcodes "shift toward rights-based" regardless of data
- 11.1.6: Budget enforcement resets on browser refresh (session_state only)
- 7.4.2: Never-reported Region column shows "Unknown" for all entries
- ~~8.1.2~~: RESOLVED 2026-03-23 — `tab_explore.py:1112-1121` correctly distinguishes Committee/State Party doc types

### P1 Gaps (fix before stakeholder demo)
- 4.2.2: Scroll containers lack role="region", tabindex="0" (smart table T5)
- 4.3.3: No table sorting with aria-sort (smart table T5)
- 4.3.4: No table text search (smart table T5)
- 8.2.5: 0/13 Reporting Timeline charts have sr-only alt-text
- ~~11.4.1~~: RESOLVED 2026-03-23 — Open Data Commitment added to About page (`tab_about.py`)
- ~~11.4.2~~: RESOLVED 2026-03-23 — Commitment text written and published

### P2 Gaps (fix before production)
- 8.2.2: Regional cadence heatmap uses raw counts not per-SP
- 8.3.1: "Distinct Countries" → "States Parties" on Timeline
- 8.3.2: "country" → "State Party" in Timeline hover labels
- 12.3.4: Trend colors mismatch between styles.py and colors.py
- 7.5.3: ISO lookup not cached (150+ fuzzy searches per render)

### P3 Gaps (known debt, track for later)
- 6.3.3: _spark_docs/_spark_countries computed but unused
- 6.4.1: 15+ hardcoded hex colors in tab_overview.py
- 12.3.3: 120-line inline style block in tab_overview.py
- 12.3.2: Compare Countries CSS leaks to other tabs

## Deferred Items (post-graduation)
- 11.3.1–11.3.9: Full subscription security (auth, Stripe, PII encryption, GDPR)
- Rationale: Platform operates without PII collection for now; Extended tier activated by server-side API key, not user subscriptions

### No-Data-Download Policy (activated 2026-03-23)
- All CSV download buttons: ⏸️ Deferred — blocked by no-data-download policy
- All PDF/DOCX/Markdown export buttons: ⏸️ Deferred — blocked by no-data-download policy
- Table-standards §4 CSV download requirement: ⏸️ Deferred — blocked by no-data-download policy
- table_lint.py csv-download check: ⏸️ Deferred — blocked by no-data-download policy
- See `.claude/references/no-data-download.md` for full policy and re-enablement conditions

## Unaudited Pages
- Country Profiles (default_tab == 2): No QA audit performed
- Semantic Search (tab_chat.py beyond XSS fix): No QA audit performed
- Compare Countries (default_tab == 3): Audited for spacing/CSS but no full QA + Stakeholder Advocate pass
- Research & Citation: Functional but no formal QA audit with Stakeholder Advocate verdicts
