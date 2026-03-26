# Testing the CRPD Agent System — Step-by-Step Instructions

## Prerequisites

Before testing, make sure your project has this structure:

```
your-project/
  CLAUDE.md                           ← Updated version with agent system section
  .claude/
    skills/
      pm-orchestrator/SKILL.md        ← PM Orchestrator skill
      data-analyst/SKILL.md           ← Data Analyst skill
      data-scientist/SKILL.md         ← Data Scientist skill
      text-analytics-expert/SKILL.md  ← Text Analytics Expert skill
      ai-engineer/SKILL.md            ← AI Engineer skill
      software-engineer/SKILL.md      ← Software Engineer skill
      ux-designer/SKILL.md            ← UX Designer skill
      qa-tester/SKILL.md              ← QA Tester skill
      devops-engineer/SKILL.md        ← DevOps Engineer skill
      focused-pr/SKILL.md
      sync-requirements/SKILL.md
      model-eval-report/SKILL.md
      vignette/SKILL.md
    references/
      table-standards.md
      chart-theme.md
      data-health.md
      wcag-audit.md
      require-permission.md
  scripts/
    validate_agent_system.py          ← Structural validator
    test_agent_system.py              ← Functional test plan generator
    table_lint.py                     ← Table standards linter
  data/
    crpd_reports.csv
  src/
    data_loader.py
    analysis.py
    colors.py
    ...
  LLM_Development/
    PHASE_TRACKER.md
    ...
```

---

## Phase 1: Structural Validation (automated — 2 minutes)

This checks that all files exist and contain required sections. Run in
your terminal (not Claude Code):

```bash
cd /path/to/crpd-dashboard
python scripts/validate_agent_system.py
```

**Expected output:** A checklist of ~60 structural checks. All must show ✅.

**If checks fail:** The script tells you exactly what's missing. Fix each
failure before proceeding. Common issues:
- Missing skill file → copy from the files we built
- Skill missing frontmatter → add the `---` delimited YAML block
- CLAUDE.md missing section → use the updated CLAUDE.md
- PHASE_TRACKER.md has duplicate Phase 3 → fix the duplicate

**Do not proceed to Phase 2 until all structural checks pass.**

---

## Phase 2: Smoke Tests (manual in Claude Code — 15 minutes)

These test one critical behavior per skill. Open Claude Code in your
project directory and run:

```bash
python scripts/test_agent_system.py --quick
```

This prints 9 smoke test prompts with grading checklists. For each test:

1. **Type the prompt** exactly as shown into Claude Code
2. **Read the response** and check each item on the checklist
3. **Grade:** PASS (all items checked) / PARTIAL (most items) / FAIL (key items missing)

### The 9 smoke tests:

**PM-01:** `/pm-orchestrator What is the current status of all LLM development phases?`
→ Should read PHASE_TRACKER.md and report all 5 phases

**PM-03:** `/pm-orchestrator Skip the design step and go straight to building Phase 1 infrastructure`
→ Should BLOCK and explain the missing gate

**DA-01:** `/data-analyst Give me a breakdown of CRPD documents by UN regional group and document type`
→ Should produce a compliant table with treaty terminology

**DS-01:** `/data-scientist Is the difference in Article 24 attention between regions statistically significant?`
→ Should use correct test, report effect sizes, plain-language translation

**TA-01:** `/text-analytics-expert The keyword dictionary for Article 5 seems to miss a lot. How would you validate and improve it?`
→ Should propose validation workflow, require PM approval for changes

**AI-01:** `/ai-engineer Set up the RAG pipeline for the chat feature`
→ Should check PHASE_TRACKER first, block if phase isn't ready

**SE-01:** `/software-engineer Implement a data table on the Country Profiles page showing all documents for the selected country`
→ Should reference table-standards.md, state Tier 2, include accessibility

**QA-01:** `/qa-tester Audit the Country Profiles page for table compliance and accessibility`
→ Should run/reference table_lint.py, use the full checklist

**RT-01:** `/pm-orchestrator Who should work on this: the keyword matching misses too much`
→ Should route to Text Analytics Expert, not Data Analyst

### Passing criteria

All 9 smoke tests must PASS for the system to be functional. If any test
FAILS, the corresponding skill needs revision before the system is reliable.

---

## Phase 3: Full Test Suite (manual in Claude Code — 45 minutes)

Run all 18 tests including handoff quality, gate enforcement, and reference
file consultation:

```bash
python scripts/test_agent_system.py
```

Grade each test and record results. Pay special attention to:

- **Gate tests (PM-03, GT-01):** Must BLOCK — any PASS-through is a critical failure
- **Handoff tests (DA-03):** Must include all gate checklist fields
- **Terminology tests (all):** Must use "States Parties," "Article 24 (Education)"
- **Reference file tests (TS-01, RP-01):** Must demonstrate consultation

---

## Phase 4: Table Linter Validation (automated — 2 minutes)

Test that the table linter catches real violations:

```bash
# Run against your source code
python scripts/table_lint.py src/

# Check specific rules
python scripts/table_lint.py src/ --rule terminology
python scripts/table_lint.py src/ --rule hardcoded-number

# Get summary view
python scripts/table_lint.py src/ --summary
```

The linter should find violations in existing code (most projects have
some). Review each violation to confirm it's a real issue. If the linter
finds zero violations on first run, either the code is already perfect
(unlikely) or the linter rules need tuning.

---

## Phase 5: End-to-End Workflow Test (manual — 30 minutes)

The ultimate test: run a real multi-agent workflow through the PM.

```
/pm-orchestrator Review the Reporting Timeline sub-tab in tab_explore.py for data
accuracy, statistical claims, and text compliance. Then implement the fixes.
```

**What should happen:**
1. PM classifies as code review/audit
2. PM selects team: Data Analyst, Data Scientist, Text Analytics Expert, QA
3. PM decomposes into tasks with parallel review → merge → implement → QA
4. PM presents plan and waits for approval
5. After approval, each agent reviews the code from their perspective
6. PM merges findings, removes duplicates, presents prioritized list
7. After approval, Software Engineer implements fixes
8. QA Tester validates
9. PM runs post-implementation review
10. Workflow complete summary with pass/fail per task

**Grade this on:**
- Did the PM decompose correctly?
- Did each agent stay in their lane?
- Did handoffs include required gate fields?
- Did the PM merge findings without losing any?
- Did the final output use treaty terminology?
- Did ruff pass after code changes?

---

## Exporting Results

Export the test plan as JSON for tracking:

```bash
python scripts/test_agent_system.py --export-json tests/agent-system-evals.json
```

After grading, you can update the JSON with your results and track
improvement across skill revisions.

---

## What to Do When Tests Fail

| Failure type | Fix |
|---|---|
| Wrong skill triggered | Revise the `description:` field in the skill's frontmatter — add trigger phrases that match the test prompt |
| Skill ignores its own rules | Add the rule to the skill body with emphasis, or add a worked example showing correct behavior |
| Gate doesn't block | Strengthen the gate language — change "consider" to "BLOCK and explain" |
| Reference file not consulted | Add explicit "consult `.claude/references/X.md`" to the skill body |
| Treaty terminology missing | Add to the stakeholder output gate in the skill |
| Hardcoded numbers | Add to the self-check requirements in the skill |
| Handoff missing fields | Add the specific fields to the handoff gate checklist |

After fixing, re-run the failing test to confirm the fix works. Then re-run
the full smoke test suite to confirm nothing else broke.

---

## Quick Command Reference

```bash
# Structural validation (run first)
python scripts/validate_agent_system.py

# Smoke tests (9 tests, ~15 min)
python scripts/test_agent_system.py --quick

# Full test suite (18 tests, ~45 min)
python scripts/test_agent_system.py

# Test one skill only
python scripts/test_agent_system.py --skill pm-orchestrator
python scripts/test_agent_system.py --skill data-analyst

# Export as JSON
python scripts/test_agent_system.py --export-json tests/agent-system-evals.json

# Table linter
python scripts/table_lint.py src/
python scripts/table_lint.py src/ --summary

# WCAG audit
python scripts/wcag_audit.py
```
