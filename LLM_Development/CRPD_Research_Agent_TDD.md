# CRPD Research & Citation Studio — Technical Design Document

## 1. Overview

A RAG + LLM-powered research assistant that generates structured briefings from the actual UN CRPD PDF documents. Two tiers: Free (Ollama local) and Premium (Claude API via Anthropic).

---

## 2. Architecture

### 2.1 Dual-LLM Strategy

| Component | Free Tier (Ollama) | Premium Tier (Claude API) |
|---|---|---|
| Model | llama3.2 / mistral (local) | claude-sonnet-4-20250514 |
| Context window | ~128K tokens | 200K tokens |
| Cost | Zero (runs on server) | Pay-per-use (metered per subscriber) |
| Latency | Slower (local inference) | Faster (API) |
| Quality | Good for retrieval + summarization | Superior for planning, synthesis, nuanced reasoning |
| Data privacy | All data stays local | Data sent to Anthropic API |

### 2.2 Six-Agent Pipeline

```
User Query
    → [1] Planner (decompose into sub-questions)
    → [2] Retriever (FAISS semantic search per sub-question)
    → [3] Synthesizer (summarize retrieved chunks with citations)
    → [4] Analyst (optional: run quantitative analysis tools)
    → [5] Reviewer (check for overclaiming, treaty terminology, caveats)
    → [6] Writer (assemble structured briefing with citations)
    → Output (render in UI + optional PDF/DOCX export)
```

Each agent is an LLM call with a specialized system prompt — not a separate model, just a different role prompt routed to either Ollama or Claude depending on the tier.

### 2.3 Agent Definitions

#### Agent 1: Planner
- **Input:** User query (string)
- **Output:** List of 3-5 sub-questions + research plan
- **System prompt constraints:**
  - Decompose into specific, answerable sub-questions
  - Use treaty terminology ("States Parties", "Article 24 (Education)")
  - No leading questions or assumptions of compliance/non-compliance
  - Identify whether sub-questions need RAG-only or RAG + analytical tools
- **LLM routing:** Premium tier always uses Claude (better decomposition). Free tier uses Ollama.

#### Agent 2: Retriever
- **Input:** List of sub-questions from Planner
- **Output:** Per sub-question: top-k relevant chunks with metadata
- **Implementation:** `src/llm.py::semantic_search()` per sub-question
- **Parameters:**
  - top_k = 8 per sub-question
  - Deduplicate: if same chunk appears for multiple sub-questions, keep once with all question references
  - Total context budget: max 30 chunks across all sub-questions
- **No LLM call** — this is pure FAISS retrieval

#### Agent 3: Synthesizer
- **Input:** Sub-question + retrieved chunks
- **Output:** 1-2 paragraph synthesis with inline citations
- **System prompt constraints:**
  - Every factual claim must cite source: "(Country, Doc Type, Year)"
  - Never fabricate quotes — paraphrase with attribution
  - Distinguish State Party claims vs Committee findings
  - State sample size: "Based on N documents from..."
  - Flag when evidence is thin: "Limited evidence (N=2) suggests..."
- **LLM routing:** Both tiers use their respective model

#### Agent 4: Analyst (optional, triggered by Planner)
- **Input:** Sub-question flagged as needing quantitative analysis
- **Output:** Statistical finding with method disclosure
- **Tool access:** Can call these `src/analysis.py` functions:
  - `article_frequency(df, ARTICLE_PRESETS, groupby=...)` — article coverage
  - `model_shift_table(df)` — rights vs medical keyword counts
  - `keyword_counts(df, top_n=...)` — term frequencies
  - `extract_distinctive_terms(df, reference_df, top_n=...)` — keyness
- **System prompt constraints:**
  - Always disclose method: "Using keyword frequency matching (30 medical-model terms, 27 rights-based terms)..."
  - Report n= for every aggregation
  - No causal claims from correlational data
- **LLM routing:** Premium only (free tier skips analytical queries or returns basic counts)

#### Agent 5: Reviewer
- **Input:** Combined synthesis from all sub-questions
- **Output:** Review with PASS/FLAG/BLOCK per section
- **Checklist:**
  - [ ] Treaty terminology correct ("States Parties" not "countries")
  - [ ] No compliance judgments ("the data shows reporting patterns" not "the country fails to comply")
  - [ ] All claims cite source documents
  - [ ] Sample sizes disclosed
  - [ ] Methodology limitations stated
  - [ ] State Party documents distinguished from Committee documents
  - [ ] No causal claims from keyword data
  - [ ] Language is empowering, not patronizing
- **LLM routing:** Both tiers

#### Agent 6: Writer
- **Input:** Reviewed synthesis + research plan
- **Output:** Structured briefing
- **Output format:**
  ```
  ## Executive Summary
  [2-3 sentence overview]

  ## Findings
  ### [Sub-question 1]
  [Synthesis with citations]

  ### [Sub-question 2]
  [Synthesis with citations]

  ...

  ## Methodology Note
  This briefing is based on keyword-based text analysis of [N] UN treaty
  body documents. Classification uses [30] medical-model terms and [27]
  rights-based terms. [Additional methodology details.]

  ## Sources
  [List of all cited documents with country, type, year]
  ```
- **LLM routing:** Premium uses Claude (better prose). Free uses Ollama.

---

## 3. Citation Format

### 3.1 Inline Citations
```
"Uganda's initial State Report emphasizes community-based rehabilitation
as a primary service delivery model (Uganda, State Report, 2013)."
```

### 3.2 Source List Entry
```
- Uganda, State Report, 2013 [Chunks 1247, 1248, 1252]
- CRPD Committee, Concluding Observations on Uganda, 2016 [Chunks 3891, 3892]
```

### 3.3 Citation Flow
1. Retriever returns chunks with metadata: `{country, year, doc_type, text, chunk_id}`
2. Synthesizer embeds `(country, doc_type, year)` inline
3. Writer collects all citations into a Sources section
4. Publisher formats for export (APA-style for PDF, linked for UI)

---

## 4. Context Window Budget

| Step | Tokens (estimated) | Notes |
|---|---|---|
| System prompt (per agent) | ~500 | Role definition + constraints |
| User query | ~50-200 | Original question |
| Research plan | ~300-500 | Planner output |
| Retrieved chunks (30 × ~500 tokens) | ~15,000 | Main context cost |
| Per-sub-question synthesis | ~500-800 each | Synthesizer output |
| Combined synthesis (5 sub-Qs) | ~3,000-4,000 | Input to Reviewer |
| Reviewer output | ~500-1,000 | Review checklist |
| **Total per research query** | **~20,000-25,000** | Well within both models |

Ollama (128K) and Claude (200K) both have ample headroom. No chunking of the pipeline itself is needed.

---

## 5. State Management

### 5.1 LangGraph State Schema
```python
from typing import TypedDict, List, Optional

class ResearchState(TypedDict):
    # Input
    user_query: str
    tier: str  # "free" or "premium"

    # Planner output
    sub_questions: List[dict]  # [{question, needs_analysis, status}]
    research_plan: str

    # Retriever output
    retrieved_chunks: dict  # {sub_question_id: [chunks]}
    deduplicated_chunks: List[dict]

    # Synthesizer output
    syntheses: dict  # {sub_question_id: {text, citations}}

    # Analyst output (optional)
    analytical_results: dict  # {sub_question_id: {finding, method, n}}

    # Reviewer output
    review: dict  # {verdicts: [...], overall: PASS/FLAG/BLOCK}

    # Writer output
    briefing: dict  # {executive_summary, findings, methodology, sources}

    # Metadata
    total_chunks_retrieved: int
    total_llm_calls: int
    total_tokens_used: int
    citations: List[dict]  # [{country, doc_type, year, chunk_ids}]
```

### 5.2 LangGraph DAG
```
START → Planner → Retriever → [Synthesizer, Analyst (parallel)] → Reviewer
    → (if BLOCK: Reviser → Reviewer loop, max 2 iterations)
    → Writer → END
```

---

## 6. Dual-LLM Routing Logic

```python
def get_model(tier: str, agent_role: str) -> str:
    """Route to appropriate model based on tier and role."""
    if tier == "premium":
        return "claude-sonnet-4-20250514"

    # Free tier: Ollama for everything
    return "ollama/llama3.2"
```

### 6.1 API Configuration

**Free tier (Ollama):**
```python
# Already configured in src/llm.py
OLLAMA_URL = "http://localhost:11434/api/generate"
```

**Premium tier (Claude API):**
```python
# Anthropic API key stored in Streamlit secrets
# .streamlit/secrets.toml or Posit Connect environment
ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
```

---

## 7. Rate Limiting & Metering

| Tier | Limit | Tracking |
|---|---|---|
| Free | 10 research queries per session | `st.session_state["research_query_count"]` |
| Premium | Unlimited (metered by API cost) | API key validation + usage logging |

### 7.1 Cost Estimation (Premium)
- Average research query: ~25K input tokens + ~4K output tokens per agent × 5 agents
- Estimated cost per query: ~$0.05-0.15 with Claude Sonnet
- Monthly subscriber doing 100 queries: ~$5-15 in API costs

---

## 8. Existing Infrastructure to Reuse

| Component | Location | How Research Agent Uses It |
|---|---|---|
| FAISS index | `LLM_Development/build_knowledge_base.py` | Retriever searches this |
| Semantic search | `src/llm.py::semantic_search()` | Retriever calls this per sub-question |
| Ollama integration | `src/llm.py::generate_insights_local()` | Free tier LLM calls |
| Model shift table | `src/analysis.py::model_shift_table()` | Analyst tool |
| Article frequency | `src/analysis.py::article_frequency()` | Analyst tool |
| Keyword counts | `src/analysis.py::keyword_counts()` | Analyst tool |
| Distinctive terms | `src/analysis.py::extract_distinctive_terms()` | Analyst tool |
| Dataset stats | `src/data_loader.py::get_dataset_stats()` | Dynamic counts in outputs |
| CRPD article dict | `src/crpd_article_dict.py` | Article name resolution |
| Accessible tables | `src/components.py::render_accessible_table()` | Source list rendering |

---

## 9. File Structure

```
src/
├── research_agent.py          # NEW: Pipeline orchestration (LangGraph)
├── research_prompts.py        # NEW: System prompts for each agent role
├── research_renderer.py       # NEW: Streamlit UI for research tab
├── tab_research.py            # NEW: Tab skeleton + product page
├── llm.py                     # MODIFY: Add Claude API client alongside Ollama
├── analysis.py                # NO CHANGE: Analyst agent calls existing functions
├── data_loader.py             # NO CHANGE: get_dataset_stats() already available
└── ...

app.py                         # MODIFY: Add routing for Research & Citation tab
.streamlit/secrets.toml        # MODIFY: Add ANTHROPIC_API_KEY
```

---

## 10. Error Handling & Graceful Degradation

| Failure | Free Tier Response | Premium Tier Response |
|---|---|---|
| Ollama down | "Local AI unavailable. Please try again later." | Falls back to Claude |
| Claude API rate limit | N/A | "Processing queue full. Retrying in 30s..." |
| Claude API key invalid | N/A | "Premium features require a valid subscription." |
| FAISS returns 0 chunks | "No relevant documents found. Try broadening your query." | Same |
| Reviewer BLOCKs output | Retry with Reviser (max 2 loops), then return partial with caveat | Same |
| Sub-question gets 0 results | Skip sub-question, note in output: "Insufficient evidence for..." | Same |

---

## 11. Query Types & Routing

| Query Type | Example | Pipeline | Tier |
|---|---|---|---|
| Simple Q&A | "What did Uganda's State Report say about education?" | Retriever → Synthesizer → Writer | Both |
| Thematic exploration | "How is Article 24 referenced across East Africa?" | Planner → Retriever → Synthesizer → Writer | Both |
| Country briefing | "Generate a reporting profile for Kenya" | Planner → Retriever → Analyst → Synthesizer → Writer | Premium |
| Comparative analysis | "Compare Uganda and Kenya on Article 12" | Planner → Retriever (parallel) → Analyst → Synthesizer → Writer | Premium |
| Statistical query | "What % of African State Reports mention inclusive education?" | Planner → Retriever → Analyst → Writer | Premium |
| Temporal trend | "How has Article 12 framing changed over time?" | Planner → Analyst → Synthesizer → Writer | Premium |

---

## 12. Capabilities Matrix

### Research & Analysis
| Feature | Free | Premium | Implementation |
|---|---|---|---|
| Research Agent (multi-source briefing) | ✓ (10/session) | ✓ (unlimited) | Full pipeline |
| Thematic Deep Dive | ✓ | ✓ | Planner + Retriever + Synthesizer |
| Country Briefing Generator | — | ✓ | Full pipeline + Analyst |
| Comparative Analysis | — | ✓ | Parallel retrieval + Analyst |
| Data Analysis (statistical queries) | — | ✓ | Analyst agent with analysis.py tools |

### Document Intelligence
| Feature | Free | Premium | Implementation |
|---|---|---|---|
| Chat with Documents | ✓ | ✓ | Existing semantic search + LLM |
| Document Summarization | ✓ | ✓ | Retriever + Synthesizer |
| Cross-Document Synthesis | — | ✓ | Multi-document Retriever + Synthesizer |

### Citation & Export
| Feature | Free | Premium | Implementation |
|---|---|---|---|
| Full Citation Trails | ✓ | ✓ | Citation tracking through pipeline |
| Export to PDF/DOCX | — | ✓ | Writer + Publisher (Quarto) |
| Methodology Appendix | ✓ | ✓ | Auto-generated from pipeline metadata |

### Quality Assurance (all tiers)
| Feature | Implementation |
|---|---|
| Treaty Terminology Compliance | Reviewer agent checklist |
| Overclaiming Guards | Reviewer agent checklist |
| Source Separation (State Party vs Committee) | Synthesizer prompt constraint |

---

## 13. Safety Rails

### 13.1 Queries the Agent Must Refuse
- "Is [country] complying with the CRPD?" → Redirect: "I can show you [country]'s reporting patterns and Committee observations, but compliance is a legal determination I cannot make."
- "Which countries are failing?" → Redirect: "I can identify reporting gaps and patterns, but I don't rank or judge States Parties."
- "Should [country] change its policy on...?" → Redirect: "I can show what the CRPD Committee has recommended, but policy advice is beyond my scope."
- Individual disability claims or legal advice → Refuse entirely.

### 13.2 Output Safety
- Every briefing includes a methodology note (survives screenshot extraction)
- Every claim cites a specific document
- Comparisons framed as "reporting patterns" not "performance"
- State Party documents and Committee documents clearly labeled as such
- Numbers always include n= and time period

---

## 14. Implementation Phases

### Phase 1 (Current): Placeholder UI
- Build the Research & Citation tab skeleton
- Product page with capabilities, pricing, mockup
- "Coming Soon" status throughout
- No backend wiring

### Phase 2: Core RAG Pipeline
- Implement Planner → Retriever → Synthesizer → Writer
- Ollama integration (free tier)
- Basic citation tracking
- Render in Streamlit

### Phase 3: Premium Tier
- Claude API integration
- Analyst agent with analysis.py tools
- Country briefing and comparative analysis
- Subscription/API key management

### Phase 4: Export & Polish
- PDF/DOCX export via Quarto
- Methodology appendix auto-generation
- Rate limiting and usage metering
- Production hardening

---

## 15. Pricing Structure

### Free Tier — Included
- Local AI processing (Ollama)
- 10 research queries per session
- Chat with documents
- Document summarization
- Basic citation trails
- Thematic exploration
- Markdown export
- All quality assurance features

### Premium Tier — Subscription ($9.99/month placeholder)
- Claude AI processing (Anthropic)
- Unlimited research queries
- Everything in Free, plus:
  - Country Briefing Generator
  - Comparative Analysis
  - Cross-Document Synthesis
  - Data Analysis tools
  - PDF/DOCX formatted export
  - Priority processing

---

*Document version: 1.0.0*
*Created: 2026-03-22*
*Status: Architecture planning — not yet approved for implementation*
*Next step: Team review via /pm-orchestrator, then human approval*
