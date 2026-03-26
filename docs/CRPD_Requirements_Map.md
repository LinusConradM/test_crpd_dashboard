# CRPD Dashboard — Requirements Map & Compliance Tracker

## How to use this document
Mark each item: ✅ Done | 🔧 In Progress | ❌ Not Started | ⏸️ Deferred | N/A Not Applicable
Review with your team before each milestone (Professor Cogburn review, deployment, graduation).

**Last updated:** 2026-03-23
**Summary:** 250 total requirements | ~172 Done | ~50 In Progress | ~18 Not Started | ~10 Deferred

---

## 1. AGENT SYSTEM & DEVELOPMENT INFRASTRUCTURE

### 1.1 Skills Architecture
| # | Requirement | Status | Notes |
|---|---|---|---|
| 1.1.1 | 14 skills in `.claude/skills/` with YAML frontmatter | ✅ | PM, DA, DS, TA, AI, SE, UX, QA, DevOps, FocusedPR, SyncReq, ModelEval, Vignette, Stakeholder Advocate |
| 1.1.2 | 6 reference files in `.claude/references/` | ✅ | table-standards, table-standards-enforcement, chart-theme, data-health, wcag-audit, require-permission |
| 1.1.3 | PM Orchestrator as single entry point | ✅ | v3.0.0 |
| 1.1.4 | Dependency graph enforced | ✅ | Updated for Stakeholder Advocate |
| 1.1.5 | Permission gate on all role skills | ✅ | |
| 1.1.6 | Stakeholder output gate on user-facing skills | ✅ | QA routes to Advocate before PM |
| 1.1.7 | States Parties terminology in all skills | ✅ | |
| 1.1.8 | Table standards reference in relevant skills | ✅ | |
| 1.1.9 | Stakeholder Advocate with 4-lens review | ✅ | v1.0.0 — PASS/FLAG/BLOCK |
| 1.1.10 | All 14 skills have `version:` in frontmatter | ✅ | Gap #1 closed |
| 1.1.11 | devops-engineer exempt documented | ✅ | Gap #3 |
| 1.1.12 | qa-tester has stakeholder output gate | ✅ | Gap #2 closed |

### 1.2 Validation & Testing
| # | Requirement | Status | Notes |
|---|---|---|---|
| 1.2.1 | validate_agent_system.py — 130+ checks | ✅ | 130/130 |
| 1.2.2 | test_agent_system.py — 18 functional tests | ✅ | --quick for 9 smoke |
| 1.2.3 | table_lint.py — 9 automated checks | ✅ | |
| 1.2.4 | testing_instructions.md — 5-phase guide | ✅ | |
| 1.2.5 | CLAUDE.md accurate and current | ✅ | Command names fixed |

### 1.3 Quality Gates
| # | Requirement | Status | Notes |
|---|---|---|---|
| 1.3.1 | Ruff linting after every change | ✅ | |
| 1.3.2 | Read-before-write rule | ✅ | |
| 1.3.3 | PHASE_TRACKER.md maintained | ✅ | |
| 1.3.4 | Protected files enforced | ✅ | |

**Section 1 total: 21/21 ✅**

---

## 2. DATA & ANALYTICS

| # | Requirement | Status | Notes |
|---|---|---|---|
| 2.1.1 | crpd_reports.csv loads via load_data() | ✅ | |
| 2.1.2 | get_dataset_stats() returns dynamic counts | ✅ | |
| 2.1.3 | All displayed counts dynamic | ✅ | Homepage C4, C6 fixed |
| 2.1.4 | No hardcoded counts anywhere | 🔧 | Homepage fixed; verify Reporting Timeline |
| 2.1.5 | country_converter ISO3 codes | ✅ | |
| 2.1.6 | pycountry ISO fallback dict | ✅ | |
| 2.1.7 | State of Palestine in ISO fallback | ✅ | Map View C8 |
| 2.2.1 | model_shift_table() | ✅ | |
| 2.2.2 | article_frequency() | ✅ | |
| 2.2.3 | extract_topics_lda() | ✅ | Dead call removed from Map View |
| 2.2.4 | keyword_counts() | ✅ | |
| 2.2.5 | extract_distinctive_terms() | ✅ | |
| 2.2.6 | extract_ngrams() | ✅ | |
| 2.2.7 | global_topic_transform() | ✅ | |
| 2.2.8 | generate_smart_insights() | ✅ | Insight panel audited |
| 2.2.9 | DOMAIN_STOPWORDS | ✅ | |
| 2.2.10 | pycountry subdivision stopwords | ✅ | |
| 2.3.1 | Raw keyword counts not normalized | ✅ | Standing decision |
| 2.3.2 | datetime.now().year for reporting gaps | 🔧 | Map View ✅; Timeline approved |
| 2.3.3 | Never-reported uses df_all | 🔧 | Bug found; fix approved |
| 2.3.4 | No double-normalization on area charts | ✅ | Homepage C3 fixed |
| 2.3.5 | Early/late splits disclose n= | ✅ | |
| 2.3.6 | Empty DataFrame guards | 🔧 | Map View ✅; Timeline approved |
| 2.3.7 | fillna(0) before astype(int) | ✅ | Map View C7 |

**Section 2: 19/23 ✅, 4 🔧**

---

## 3. TREATY TERMINOLOGY & FRAMING

| # | Requirement | Status | Notes |
|---|---|---|---|
| 3.1.1 | "States Parties" not "countries" | 🔧 | Homepage ✅, Map View ✅, Timeline has 2 remaining |
| 3.1.2 | "Article 24 (Education)" format | ✅ | |
| 3.1.3 | Doc types in title case | ✅ | |
| 3.1.4 | "CRPD Committee" not "the Committee" | ✅ | |
| 3.1.5 | "Concluding Observations" not "COs" | ✅ | |
| 3.1.6 | "persons with disabilities" | ✅ | |
| 3.1.7 | "States Parties" plural, capitalized | 🔧 | app.py fixed; check Timeline |
| 3.2.1 | No compliance judgments | ✅ | |
| 3.2.2 | No causal claims from keywords | ✅ | |
| 3.2.3 | "keyword share" not "adoption" | 🔧 | Timeline approved |
| 3.2.4 | Phase labels include "Language" | 🔧 | Timeline condition #3 approved |
| 3.2.5 | Narrative adapts to data direction | 🔧 | Timeline condition #1 CRITICAL approved |
| 3.2.6 | Narrative adapts to doc_type filter | 🔧 | Timeline condition #2 approved |
| 3.2.7 | Gaps framed as systemic barriers | ✅ | |
| 3.2.8 | Rankings framed neutrally | ✅ | Map View fixed |
| 3.2.9 | Reporting gap color direction correct | ✅ | Map View C4 |
| 3.2.10 | Methodology caveats proximate to claims | ✅ | |

**Section 3: 11/17 ✅, 6 🔧**

---

## 4. ACCESSIBILITY (WCAG 2.2 AA)

| # | Requirement | Status | Notes |
|---|---|---|---|
| 4.1.1 | All text ≥ 14px | 🔧 | Homepage ✅; Timeline 6 violations |
| 4.1.2 | Color contrast ≥ 4.5:1 | 🔧 | Homepage ✅; Timeline badge approved |
| 4.1.3 | Adjacent choropleth bins distinguishable | 🔧 | SEQUENTIAL_BLUES[4] vs [5] flagged |
| 4.1.4 | MAP_NO_DATA distinct from lowest bin | ✅ | |
| 4.1.5 | Colorblind-safe palette | ✅ | |
| 4.2.1 | Tables: caption, th scope, no merged cells | ✅ | render_accessible_table() |
| 4.2.2 | Scroll containers: role, aria-label, tabindex | ❌ | Smart table T5 needed |
| 4.2.3 | Decorative SVG: aria-hidden | ✅ | |
| 4.2.4 | Metric cards: role="group", aria-label | 🔧 | Flagged I6 |
| 4.2.5 | :focus-visible on interactive elements | 🔧 | Map pills ✅; check others |
| 4.2.6 | Metric pills keyboard focus ring | ✅ | Map View fixed |
| 4.2.7 | Charts: sr-only alt-text | 🔧 | Homepage ✅; Timeline 0/13 |
| 4.3.1 | Choropleth companion table | ✅ | |
| 4.3.2 | Chart data accessible without hover | 🔧 | Map ✅; Timeline no tables |
| 4.3.3 | Table sorting with aria-sort | ❌ | Smart table T5 |
| 4.3.4 | Table text search for 10+ rows | ❌ | Smart table T5 |
| 4.3.5 | Custom HTML tables (not st.dataframe) | ✅ | |

**Section 4: 7/17 ✅, 7 🔧, 3 ❌**

---

## 5. TABLE STANDARDS

| # | Requirement | Status | Notes |
|---|---|---|---|
| 5.1.1–5.1.12 | All 12 tabular typography rules | ✅ | render_accessible_table() enforces |
| 5.2.1 | Tier 1 (conversational) | ✅ | |
| 5.2.2 | Tier 2 (dashboard) | ✅ | |
| 5.2.3 | Every skill knows which tier | ✅ | |
| 5.2.4 | table_lint.py 9 checks | ✅ | |

**Section 5: 16/16 ✅**

---

## 6. HOMEPAGE

| # | Requirement | Status | Notes |
|---|---|---|---|
| 6.1.1–6.1.10 | All 10 content/framing items | ✅ | All 8 critical fixes verified |
| 6.2.1–6.2.7 | All 7 chart items | ✅ | |
| 6.3.1 | model_shift_table() once | ✅ | C7 |
| 6.3.2 | article_frequency() once | ✅ | |
| 6.3.3 | No dead code | 🔧 | _spark_docs unused (I1 debt) |
| 6.3.4 | st.rerun() removed | ✅ | |
| 6.4.1 | All colors from colors.py | 🔧 | 15+ hardcoded (known debt) |
| 6.4.2 | WCAG contrast-compliant | ✅ | C8 |
| 6.4.3 | Font sizes ≥ 14px | ✅ | |

**Section 6: 17/19 ✅, 2 🔧 | Verdict: SHIP**

---

## 7. MAP VIEW

| # | Requirement | Status | Notes |
|---|---|---|---|
| 7.1.1 | Quantile color scale | ✅ | |
| 7.1.2 | In-chart subtitle | ✅ | C6 |
| 7.1.3 | 4 metric pills (2 cut) | 🔧 | Approved, verify |
| 7.1.4 | Pill labels plain language | 🔧 | Approved, verify |
| 7.1.5 | Reporting Gap diverging scale | ✅ | C4 |
| 7.1.6 | _n_dropped reported | ✅ | |
| 7.1.7 | Data timestamp in caption | ✅ | |
| 7.2.1 | Companion table visible | 🔧 | Approved, verify |
| 7.2.2 | Sortable columns | ❌ | T5 |
| 7.2.3 | Searchable | ❌ | T5 |
| 7.2.4 | Same data as choropleth | ✅ | DA verified |
| 7.2.5 | Scroll container accessible | ❌ | T5 |
| 7.3.1 | Stacked bar neutral title | ✅ | |
| 7.3.2 | N adapts to filter | ✅ | |
| 7.3.3 | Small multiples aligned scale | ✅ | Fixed |
| 7.3.4 | Regional Deep Dive in expander | ✅ | |
| 7.4.1 | Never-reported uses df_all | 🔧 | Fix approved |
| 7.4.2 | Region column | 🔧 | Shows "Unknown" — bug |
| 7.4.3 | Ratification year column | ❌ | Not yet |
| 7.4.4 | Caption caveats | ✅ | |
| 7.4.5 | Ratifiers set timestamped | ✅ | C8 |
| 7.5.1 | Dead LDA removed | ✅ | |
| 7.5.2 | TF-IDF cached | ✅ | C5 |
| 7.5.3 | ISO lookup cached | 🔧 | Not yet |
| 7.5.4 | Empty df guard | ✅ | |
| 7.5.5 | fillna before astype | ✅ | C7 |
| 7.5.6 | 0-country graceful degradation | 🔧 | No message yet |

**Section 7: 16/27 ✅, 7 🔧, 4 ❌ | Verdict: SHIP WITH CONDITIONS (5/5 met)**

---

## 8. REPORTING TIMELINE

| # | Requirement | Status | Notes |
|---|---|---|---|
| 8.1.1 | Narrative adapts to data direction | 🔧 | CRITICAL — condition #1 approved |
| 8.1.2 | Attribution adapts to doc_type | 🔧 | Condition #2 approved |
| 8.1.3 | Phase labels include "Language" | 🔧 | Condition #3 approved |
| 8.1.4 | Balanced badge contrast | 🔧 | Condition #4 approved |
| 8.1.5 | Min sample-size guard | ❌ | Recommended, not condition |
| 8.1.6 | No "overall shift" overclaiming | 🔧 | Part of condition #1 |
| 8.1.7 | Early/late n= disclosed | ❌ | Recommended, not condition |
| 8.2.1 | Area chart no double-norm | ❌ | Not verified |
| 8.2.2 | Regional heatmap per-SP | ❌ | Critical #7, not in conditions |
| 8.2.3 | "Adoption" → "Share" | 🔧 | Condition #6 approved |
| 8.2.4 | datetime.now().year | 🔧 | Condition #5 approved |
| 8.2.5 | Alt-text on 13 charts | ❌ | Critical #6, known debt |
| 8.2.6 | COVID annotation conditional | ❌ | Deferred |
| 8.3.1 | "Countries" → "States Parties" | ❌ | Recommended |
| 8.3.2 | "country" → "State Party" hover | ❌ | Recommended |
| 8.3.3 | "Submitted" → neutral | ❌ | Suggestion |

**Section 8: 0/16 ✅, 7 🔧, 9 ❌ | Verdict: SHIP WITH CONDITIONS (6 conditions pending)**

---

## 9. COMPARE COUNTRIES

| # | Requirement | Status | Notes |
|---|---|---|---|
| 9.1.1–9.1.4 | Layout & spacing (4 items) | ✅ | CSS applied |
| 9.2.1 | Scorecard sortable/searchable | 🔧 | Params added; awaits T5 |
| 9.2.2–9.2.10 | Slots 2–9 + Deep Dive | ✅ | |
| 9.3.1–9.3.3 | 3 comparison modes | ✅ | |

**Section 9: 13/14 ✅, 1 🔧 | Not yet audited post-fixes**

---

## 10. RESEARCH & CITATION

| # | Requirement | Status | Notes |
|---|---|---|---|
| 10.1.1–10.1.8 | Phase 1 UI (8 items) | ✅ | All live |
| 10.2.1–10.2.10 | Phase 2 RAG pipeline (10 items) | ✅ | All functional |
| 10.3.1–10.3.2 | LLM routing | ✅ | |
| 10.3.3 | Budget management | 🔧 | session_state resets on refresh |
| 10.3.4–10.3.9 | Premium tier (6 items) | ✅ | |
| 10.4.1–10.4.10 | Phase 4 Analyst + Export (10 items) | 🔧 | All approved, implementation in progress |

**Section 10: 27/37 ✅, 10 🔧**

---

## 11. SECURITY

| # | Requirement | Status | Notes |
|---|---|---|---|
| 11.1.1–11.1.5 | XSS fixes + bleach (5 items) | ✅ | Executed |
| 11.1.6 | Budget persistent storage | ❌ | Needs JSON/DB |
| 11.2.1–11.2.2 | HTML audit (2 items) | ✅ | |
| 11.2.3 | TLS on Posit Connect | 🔧 | Verify |
| 11.2.4 | Dependency audit | ❌ | Not run |
| 11.3.1–11.3.9 | Subscription security (9 items) | ⏸️ | Post-graduation |
| 11.4.1–11.4.2 | Free-tier floor commitment (2 items) | ❌ | Advocate BLOCK — needs About page text |

**Section 11: 7/20 ✅, 1 🔧, 3 ❌, 9 ⏸️**

---

## 12. DESIGN SYSTEM

| # | Requirement | Status | Notes |
|---|---|---|---|
| 12.1.1–12.1.2 | All colors from colors.py | 🔧 | 15+ hardcoded remain |
| 12.1.3–12.1.11 | Color constants defined (9 items) | ✅ | |
| 12.2.1–12.2.2 | Typography (2 items) | ✅ | |
| 12.2.3 | No font sizes below 14px | 🔧 | Timeline violations |
| 12.3.1 | Global CSS in styles.py | ✅ | |
| 12.3.2 | Tab-specific CSS scoped | 🔧 | Map View leaks flagged |
| 12.3.3 | No conflicting inline styles | 🔧 | tab_overview.py 120-line block |
| 12.3.4 | Trend colors consistent | ❌ | styles.py vs colors.py mismatch |

**Section 12: 9/15 ✅, 5 🔧, 1 ❌**

---

## 13–14. LLM & DEPLOYMENT

| # | Requirement | Status | Notes |
|---|---|---|---|
| 13.1.1–13.1.4 | Knowledge base (4 items) | ✅ | 14,391 chunks |
| 14.1.1 | Deploys to Posit Connect | ✅ | |
| 14.1.2 | requirements.txt complete | ✅ | |
| 14.1.3 | Environment variables | 🔧 | API key needs Posit setup |
| 14.1.4 | .claude/skills/ in git | ✅ | |
| 14.2.1 | Git workflow | 🔧 | GitHub account locked |
| 14.2.2–14.2.4 | Git hygiene (3 items) | ✅ | |

**Sections 13–14: 8/10 ✅, 2 🔧**

---

## OVERALL SCORECARD

| Category | ✅ Done | 🔧 In Progress | ❌ Not Started | ⏸️ Deferred |
|---|---|---|---|---|
| 1. Agent System | 21 | 0 | 0 | 0 |
| 2. Data & Analytics | 19 | 4 | 0 | 0 |
| 3. Terminology | 11 | 6 | 0 | 0 |
| 4. Accessibility | 7 | 7 | 3 | 0 |
| 5. Table Standards | 16 | 0 | 0 | 0 |
| 6. Homepage | 17 | 2 | 0 | 0 |
| 7. Map View | 16 | 7 | 4 | 0 |
| 8. Reporting Timeline | 0 | 7 | 9 | 0 |
| 9. Compare Countries | 13 | 1 | 0 | 0 |
| 10. Research & Citation | 27 | 10 | 0 | 0 |
| 11. Security | 7 | 1 | 3 | 9 |
| 12. Design System | 9 | 5 | 1 | 0 |
| 13–14. LLM & Deploy | 8 | 2 | 0 | 0 |
| **TOTAL** | **171** | **52** | **20** | **9** |

**Completion: 68% Done | 21% In Progress | 8% Not Started | 4% Deferred**

### TOP PRIORITY GAPS (highest impact items not yet done)

1. **Reporting Timeline narrative bug** — always says "shift toward rights-based" (8.1.1) — CRITICAL
2. **Smart table T5** — sorting, search, scroll fix affects every table (4.2.2, 4.3.3, 4.3.4)
3. **Free-tier floor commitment** — Advocate BLOCK condition (11.4.1, 11.4.2)
4. **Budget persistent storage** — resets on refresh (11.1.6)
5. **Reporting Timeline alt-text** — 0/13 charts accessible (8.2.5)
6. **Phase 4 Research exports** — PDF/DOCX + Analyst approved, not yet built (10.4.1–10.4.10)
7. **3 unaudited pages** — Country Profiles, Semantic Search, Compare Countries post-fixes

---

*Document version: 1.0.0 | Created: 2026-03-23*
*CRPD Disability Rights Data Dashboard | IDDP, American University*
*Principal Investigator: Professor Derrick Cogburn*
