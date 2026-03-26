# LLM Development Phase Tracker

Last updated: 2026-03-20 (Phase 5 ✅ COMPLETE — PM sign-off granted. All 5 phases done. MRR gap (0.62 vs 0.70) accepted as known gap for future cycle.)

## Phase 1 — AI Insights Panel
| Step | Status | Artifact | Date |
|------|--------|----------|------|
| Requirements | ✅ Complete | Plan documents | 2026-03-18 |
| Design | ✅ Complete | `LLM_Development/designs/phase1_ai_insights_panel.png` | 2026-03-18 |
| Infrastructure | ✅ Complete | `src/llm.py` | 2026-03-18 |
| Integration | ✅ Complete | `src/tab_overview.py` | 2026-03-18 |
| Evaluate | ✅ Complete | `LLM_Development/eval_results_phase1_2.json` | 2026-03-19 |

**Phase 1 Eval results (2026-03-19):** 3 questions, 0 errors. Overall avg 3.58/5.0 (PASS ≥3.5).
Note: p1_q2 (rights-based trend) scored 2.0 — expected, no model-framing columns in CSV yet. Phase 3 RAG will resolve this.

## Phase 2 — Chat Q&A Interface
| Step | Status | Artifact | Date |
|------|--------|----------|------|
| Requirements | ✅ Complete | Plan documents | 2026-03-18 |
| Design | ✅ Complete | `LLM_Development/designs/phase2_chat_qa_interface.png` | 2026-03-18 |
| Infrastructure | ✅ Complete | `src/llm.py` (ask_llm_multiturn) | 2026-03-18 |
| Integration | ✅ Complete | `src/tab_chat.py` | 2026-03-18 |
| Evaluate | ✅ Complete | `LLM_Development/eval_results_phase1_2.json` | 2026-03-19 |

**Phase 2 Eval results (2026-03-19):** 13 questions (incl. 4 multi-turn turns), 0 errors. Overall avg 4.92/5.0 (PASS).
Rate limit guard: PASS. Out-of-scope refusal: PASS. Multi-turn context retention: PASS.

## Phase 3 — RAG + Semantic Search
| Step | Status | Artifact | Date |
|------|--------|----------|------|
| Requirements | ✅ Complete | Plan documents | 2026-03-18 |
| Design | ✅ Complete | `LLM_Development/designs/phase3_rag_semantic_search.pdf` (2 screens) | 2026-03-20 |
| Infrastructure | ✅ Complete | `src/llm.py` (semantic_search, format_retrieved_chunks, rag_answer) + FAISS index (14,391 chunks, 523 docs) | 2026-03-19 |
| Integration | ✅ Complete | `src/tab_chat.py` (RAG + citations), `src/tab_explore.py` (Semantic Search tab), `src/nav.py` | 2026-03-19 |
| Evaluate | ✅ Complete | `LLM_Development/eval_results_phase3.json` | 2026-03-19 |

**Phase 3 Eval results (2026-03-19):** 10 questions + 5 search tests, 0 errors. RAG avg 4.62/5.0 (PASS ≥3.5). Semantic search 5/5 tests passed. Off-topic score: 0.15 (well below 0.4 threshold).

**Phase 3 Infrastructure complete (2026-03-19):**
- 523 PDFs downloaded via UN Digital Library API
- 14,391 chunks (500 words, 75-word overlap)
- FAISS index: 44.2 MB  |  Embeddings: 44.2 MB (14391 × 768 dims)
- Knowledge base stored in `data/faiss_index.bin`, `data/embeddings.npy`, `data/chunks_metadata.json`

## Phase 4 — Policy Brief Generation
| Step | Status | Artifact | Date |
|------|--------|----------|------|
| Requirements | ✅ Complete | Plan documents | 2026-03-18 |
| Design | ✅ Complete | `LLM_Development/designs/phase4_screen1_policy_brief_generator.png` + `phase4_screen2_generated_brief.png` | 2026-03-19 |
| Infrastructure | ✅ Complete | `src/llm.py` — `generate_policy_brief`, `_parse_brief_sections`, `format_brief_as_markdown`, `BRIEF_FORMATS`, `BRIEF_SYSTEM_PROMPT` | 2026-03-19 |
| Integration | ✅ Complete | `src/tab_brief.py`, `app.py` (page="brief"), `src/nav.py` ("Policy Brief ✦") | 2026-03-19 |
| Evaluate | ✅ Complete | `LLM_Development/eval_results_phase4.json` | 2026-03-20 |

**Phase 4 Evaluate results (2026-03-20):**

| Metric | Score | Target | Status |
|--------|-------|--------|--------|
| Judge avg | 3.75 / 5.0 | ≥ 3.5 | ✅ PASS |
| MRR | 0.62 | > 0.70 | ⚠️ Below target |
| nDCG@10 | 1.00 | > 0.80 | ✅ PASS |
| IR avg | 0.81 | — | ✅ Strong |
| Combined | 3.90 | — | ✅ |

- config_C (mpnet + Ollama llama3.2): judge avg **3.75/5.0** ✅ PASS (≥3.5), IR avg 0.81, nDCG 1.00, MRR 0.62
- config_A (mpnet + Groq): ❌ Groq free-tier rate limits (429) blocked all generation — unable to score
- config_B, config_D: not run — Groq rate limit makes parallel Groq configs unworkable on free tier
- **Winner: config_C** — Ollama llama3.2 runs locally with zero quota, proved more reliable than Groq free tier for batch evaluation
- Key finding: local Ollama stack is production-viable; Groq free tier insufficient for multi-question evaluation workloads
- Eval script updated with `--configs` flag for targeted single-config runs + retry/backoff fixes

⚠️ **Known gap going into Phase 5 — MRR 0.62 misses > 0.70 target:**
MRR measures how quickly the first relevant chunk appears in ranked results. At 0.62, the correct chunk is landing at rank 2+ on some questions rather than rank 1. High nDCG (1.00) and judge scores (3.75) confirm the LLM recovered well from imperfect ranking — the right evidence was retrieved, just not always top-ranked. Phase 5 should investigate query expansion or re-ranking to push MRR above 0.70.

**Infrastructure complete (2026-03-19):**
- `generate_policy_brief(countries, articles, year_min, year_max, brief_format)` — multi-country RAG retrieval → Groq llama-3.3-70b → structured dict with sections + stats (chunks_retrieved, tokens_used, generation_time_ms, model)
- `_parse_brief_sections(raw_text)` — splits LLM output into context / key_findings / recommendations / sources by `## HEADER` markers
- `format_brief_as_markdown(brief, ...)` — formats structured brief as clean Markdown for download
- `BRIEF_FORMATS` — 3 format configs: Executive Summary (900 tokens), Full Report (1600 tokens), Fact Sheet (600 tokens)
- `BRIEF_SYSTEM_PROMPT` — grounding-first system prompt enforcing exact section headers
- Ruff: ✅ 0 errors | Import tests: ✅ all assertions passed

**Design screens (2026-03-19):**
- Screen 1: Policy Brief Generator — left panel (country chips, article selector, date range, format toggle, Generate button) + right panel (brief preview with 4 colour-coded sections: Context, Key Findings, Recommendations, Sources)
- Screen 2: Generated Brief View — full brief with numbered sections (Context, Key Findings, Recommendations) + right sidebar (Export PDF, Export Word, Copy Link, Regenerate, Generation Stats showing chunks/tokens/latency/model)

## Phase 5 — Evaluation & Quality Assurance
| Step | Status | Artifact | Date |
|------|--------|----------|------|
| Requirements | ✅ Complete | Plan documents + evaluation script spec added 2026-03-19 | 2026-03-18 |
| Design | N/A | No UI — pure evaluation pipeline | — |
| Infrastructure | ✅ Complete | `evaluate_phase4.py`, `visualize_phase4.py`, `eval_results_phase4.json`, `charts/phase4_*.html` | 2026-03-20 |
| Integration | ✅ Complete | `Model Performance Evaluation/report_001_phase4_policy_brief_2026-03-20.qmd` + rendered HTML | 2026-03-20 |
| Evaluate | ✅ Complete — PM sign-off granted | All criteria met; MRR gap accepted as known gap for future cycle | 2026-03-20 |

**Phase 5 deliverables — all complete (2026-03-20):**
- `LLM_Development/evaluate_phase4.py` ✅ — full evaluation harness (MRR, nDCG, Recall@K, LLM-as-Judge, 4 model configs, `--configs` flag)
- `LLM_Development/visualize_phase4.py` ✅ — 6 Plotly charts:
  - **IR/RAG lens**: `phase4_ir_metrics.html`, `phase4_ir_latency.html`
  - **LLM-as-Judge lens**: `phase4_judge_quality.html`, `phase4_judge_heatmap.html`
  - **Cross-lens**: `phase4_radar_ir_vs_judge.html`, `phase4_scatter_ir_vs_judge.html`
- `LLM_Development/eval_results_phase4.json` ✅ — config_C results (winner)
- `LLM_Development/charts/phase4_*.html` ✅ — 6 interactive HTML charts saved
- `Model Performance Evaluation/report_001_phase4_policy_brief_2026-03-20.qmd` ✅ — professional Quarto report, renders to self-contained HTML
- `.claude/skills/model-eval-report/` ✅ — skill for generating sequential evaluation reports

**Phase 5 acceptance criteria status:**

| Criterion | Status |
|-----------|--------|
| At least one config reaches MRR > 0.70 | ⚠️ config_C MRR = 0.62 — below target (known gap) |
| At least one config reaches nDCG > 0.80 | ✅ config_C nDCG = 1.00 |
| At least one config reaches judge avg ≥ 3.5/5.0 | ✅ config_C judge avg = 3.75 |
| `ruff check . && ruff format --check .` passes | ✅ Zero errors |
| Evaluation script is reproducible (`--configs` flag) | ✅ |
| 6 Plotly charts saved to `charts/` | ✅ |
| Professional evaluation report produced | ✅ report_001 rendered |

✅ **PM sign-off granted 2026-03-20.** MRR = 0.62 accepted as known gap (target 0.70). Decision: production deploy Config C (mpnet + Ollama llama3.2) now; address MRR in a future improvement cycle via query expansion, hybrid BM25+dense retrieval, or lightweight re-ranking. All other acceptance criteria met.

---

## 🎉 All 5 Phases Complete

| Phase | Name | Final Score | Date |
|-------|------|-------------|------|
| 1 | AI Insights Panel | 3.58/5.0 avg ✅ | 2026-03-19 |
| 2 | Chat Q&A Interface | 4.92/5.0 avg ✅ | 2026-03-19 |
| 3 | RAG + Semantic Search | 4.62/5.0 avg ✅ | 2026-03-19 |
| 4 | Policy Brief Generation | 3.75/5.0 avg ✅ | 2026-03-20 |
| 5 | Evaluation & QA | All deliverables ✅ | 2026-03-20 |

**Production stack:** all-mpnet-base-v2 embeddings + FAISS (14,391 chunks) + Ollama llama3.2 (local) + Groq llama-3.3-70b (cloud fallback)

**Known gaps for next cycle:**
- MRR 0.62 → 0.70 target: query expansion or BM25 hybrid retrieval
- 3 Groq configs (A, B, D) untested due to free-tier rate limits — re-evaluate with paid tier
- p4_b2 (Kenya/Article 24) judge parse error — fix judge prompt JSON schema
