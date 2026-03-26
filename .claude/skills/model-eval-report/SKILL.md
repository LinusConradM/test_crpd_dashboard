---
name: model-eval-report
description: >
  Generates a professional Quarto HTML model performance evaluation report for the CRPD Dashboard
  LLM integration. TRIGGER this skill whenever the user asks to: "write a report", "generate an
  evaluation report", "document the model performance", "create a model report", "report on the
  eval results", "visualize evaluation results", or any variation of producing a report from
  LLM evaluation data. Also trigger proactively after a phase evaluation completes (evaluate_phase*.py
  runs successfully) if the user hasn't yet generated a report for that phase. Reports are saved in
  sequential order (report_001_, report_002_, …) inside the "Model Performance Evaluation/" folder
  at the project root.
version: 1.0.0
---

# Model Evaluation Report Skill

## What this skill does

Reads the latest LLM evaluation results JSON from `LLM_Development/`, generates a professional
Quarto `.qmd` report with interactive Plotly charts, a performance summary table, and a model
recommendation, then saves it sequentially in `Model Performance Evaluation/`.

## Step-by-step workflow

### 1. Find the results file

Look for evaluation result files matching `LLM_Development/eval_results_phase*.json`.
If multiple exist, ask the user which phase they want to report on, or default to the most
recently modified one.

### 2. Determine the next report number

List all files in `Model Performance Evaluation/` matching `report_NNN_*.qmd`.
The next report number is `max(existing numbers) + 1`, zero-padded to 3 digits.
If no reports exist yet, start at `001`.

### 3. Build the report filename

```
report_{NNN}_{phase_slug}_{YYYY-MM-DD}.qmd
```

Examples:
- `report_001_phase4_policy_brief_2026-03-20.qmd`
- `report_002_phase3_rag_search_2026-03-21.qmd`
- `report_003_phase1_ai_insights_2026-03-22.qmd`

Derive `phase_slug` from the results JSON `"phase"` field and the phase name in PHASE_TRACKER.md.

### 4. Read the evaluation data

Parse the JSON thoroughly before writing anything:

- `results["phase"]` — phase number
- `results["run_date"]` — evaluation date
- `results["test_questions"]` — number of test questions
- `results["configs"]` — dict of config_id → config data
  - `config["skipped"]` — whether this config was skipped
  - `config["scores"]` — aggregate metric scores
  - `config["per_question"]` — list of per-question results
  - `config["judge_avg"]`, `config["ir_avg"]`, `config["combined_score"]`
- `results["winner"]` — winning config ID
- `results["recommendation"]` — recommendation string
- `results["acceptance_criteria"]` — targets and pass/fail flags

Also read `LLM_Development/PHASE_TRACKER.md` for the phase description and known gaps.

### 5. Write the Quarto document

Use this structure (adapt section titles to the phase being reported):

```
---
title: "CRPD Dashboard — Model Performance Evaluation"
subtitle: "Phase {N}: {Phase Name} | Report {NNN}"
author: "CRPD Analytics Project"
date: "{YYYY-MM-DD}"
format:
  html:
    theme: cosmo
    toc: true
    toc-depth: 3
    toc-location: left
    number-sections: true
    embed-resources: true
    code-fold: true
    smooth-scroll: true
execute:
  echo: false
  warning: false
---
```

**Required sections:**

1. **Executive Summary** — 2–3 sentences: what was evaluated, headline result, one-line verdict
2. **Evaluation Design** — test questions table, config comparison table, metrics definition
3. **Retrieval Performance (IR Lens)** — aggregate bar chart vs targets, per-question breakdown, latency chart
4. **Answer Quality (LLM-as-Judge Lens)** — quality dimensions bar chart, per-question heatmap, per-question table
5. **Cross-Lens Analysis** — IR vs Judge scatter plot with quadrant lines
6. **Performance Summary** — the summary table (see below) + config comparison table
7. **Model Recommendation** — clear recommended config with numbered justification
8. **Known Gaps & Phase {N+1} Priorities** — gap table with Impact and Mitigation columns
9. **Methodology Notes** — ground truth, judge model, embeddings, chunk parameters, script paths

**The performance summary table is mandatory.** It must include every metric with its score, target, and ✅/⚠️/❌ status:

| Metric | Score | Target | Status |
|--------|-------|--------|--------|
| Judge Average | X.XX / 5.0 | ≥ 3.5 | ✅/⚠️/❌ |
| Accuracy | ... | ≥ 3.5 | ... |
| Completeness | ... | ≥ 3.5 | ... |
| Relevance | ... | ≥ 3.5 | ... |
| Groundedness | ... | ≥ 3.5 | ... |
| MRR | X.XXX | > 0.70 | ... |
| nDCG@10 | X.XXX | > 0.80 | ... |
| Recall@5 | X.XXX | > 0.60 | ... |
| Recall@10 | X.XXX | > 0.60 | ... |
| Avg Retrieval Latency | X,XXX ms | < 2,000 ms | ... |
| Avg Generation Latency | X,XXX ms | < 120,000 ms | ... |
| Briefs Generated | N / M | M / M | ... |

Status icons:
- ✅ PASS — meets target
- ⚠️ Below target — misses by < 20%
- ❌ FAIL — misses by ≥ 20% or completely failed

**Charts** — use Plotly in Python code chunks (`{python}` blocks):

| Chart | Type | Key elements |
|-------|------|-------------|
| IR metrics bar | `go.Bar` + `go.Scatter` | Bars = config scores, dashed line = targets |
| Per-question IR | `make_subplots` MRR + nDCG | Colour bars by pass/fail vs target |
| Retrieval latency | `px.bar` | Colour by MRR value |
| Judge quality bar | `go.Bar` + `add_hline` | Horizontal line at 3.5 threshold |
| Per-question heatmap | `go.Heatmap` | 1–5 colour scale, grey for missing |
| Cross-lens scatter | `px.scatter` + `add_vline`/`add_hline` | Quadrant lines at MRR=0.70, Judge=3.5 |

Always use the UN Blue theme palette:
```python
UN_BLUE    = "#005bbb"
UN_GOLD    = "#f5a623"
PASS_GREEN = "#27ae60"
FAIL_RED   = "#e74c3c"
WARN_AMBER = "#f39c12"
LIGHT_GREY = "#f8f9fa"
```

**Callout boxes** — use Quarto callouts for emphasis:
- `::: {.callout-note}` — for scope/context
- `::: {.callout-warning}` — for limitations (e.g., rate-limit failures)
- `::: {.callout-tip}` — for the model recommendation (make it stand out)

### 6. Save the file

Write to:
```
{project_root}/Model Performance Evaluation/report_{NNN}_{phase_slug}_{date}.qmd
```

Then tell the user:
- The full file path
- How to render it: `quarto render "Model Performance Evaluation/report_NNN_...qmd"`
- The report number and how many reports now exist in the folder
- A brief summary of headline results (judge avg, MRR, recommendation)

### 7. Open in editor (optional)

If the user is likely to want to review it, offer to open it:
```bash
open "Model Performance Evaluation/report_NNN_....qmd"
```

## Handling skipped or failed configs

When configs were skipped due to rate limits or other errors:
- Include them in the config comparison table with ❌ and the reason
- Add a `.callout-warning` box explaining the limitation
- Make clear this is an evaluation infrastructure constraint, not a model quality issue
- Recommend re-running with the paid tier or local inference for a complete comparison

## Handling missing judge scores

Some questions may have unparseable judge responses (JSON parse errors from the judge LLM).
- Show these as "—" in tables
- Note in the methodology section that N of M questions had judge parse failures
- Flag the affected question IDs in the per-question table

## Multiple active configs

If more than one config completed successfully:
- Add a grouped bar chart comparing all active configs side by side
- Add a multi-config radar chart overlaying all configs
- Name the winner clearly in the recommendation section

## What makes a good recommendation

The recommendation should:
1. Name the winning config clearly (bold, callout box)
2. Give 3–5 numbered reasons why it wins
3. Acknowledge any metrics that miss targets
4. State the condition for production use (e.g., "after MRR gap is resolved in Phase 5")
5. Compare inference cost and rate-limit risk across configs

## File naming conventions

```
Model Performance Evaluation/
├── report_001_phase4_policy_brief_2026-03-20.qmd
├── report_002_phase3_rag_search_2026-03-21.qmd
├── report_003_phase2_chat_qa_2026-03-22.qmd
└── report_004_phase4_policy_brief_v2_2026-03-25.qmd  ← re-runs append _v2
```

For re-runs of the same phase (e.g., after adding more configs), append `_v2`, `_v3` to the slug before the date.

## Rendering instructions to give the user

After saving, always include these instructions:

```bash
# Render to HTML (requires Quarto installed)
cd "{project_root}"
quarto render "Model Performance Evaluation/report_{NNN}_{slug}_{date}.qmd"

# Output: Model Performance Evaluation/report_{NNN}_{slug}_{date}.html
# Open: open "Model Performance Evaluation/report_{NNN}_{slug}_{date}.html"
```

If Quarto is not installed: `brew install quarto` (macOS) or https://quarto.org/docs/get-started/
