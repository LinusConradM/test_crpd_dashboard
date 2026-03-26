# CLAUDE.md — CRPD Dashboard

## Project overview

Interactive Streamlit dashboard analyzing CRPD (Convention on the Rights of
Persons with Disabilities) reporting patterns across 150+ countries and 5
document types (2010–2026). The first NLP and AI-powered platform to make
the full CRPD reporting cycle searchable, visual, and actionable. Deployed
on Posit Connect at https://idpp.connect.posit.cloud/crpd-dashboard.

Exact dataset counts (countries, documents, year range) are dynamic — use
`get_dataset_stats()` from `src/data_loader.py`. Never hardcode data counts
in code, documentation, or conversation.

## Who this platform serves

Every feature, visualization, and AI output is built for four user communities:

| User group | What they need |
|---|---|
| **DPOs (disability rights organizations)** | Accountability evidence — which rights are neglected, which governments are falling short |
| **Governments & national focal points** | Compliance benchmarking — how their reporting compares to regional peers |
| **Researchers** | Rigorous, reproducible data with proper methodology documentation |
| **Policy advocates** | Clear, quotable numbers and shareable visualizations for policy briefs |

**Accessibility is subject matter, not just compliance.** The CRPD mandates
accessible information (Articles 9 and 21). Building an inaccessible disability
rights platform is a contradiction. WCAG 2.2 AA is the minimum standard.

## Agent system

This project uses a multi-agent workflow. Each agent is a skill file in
`.claude/skills/` with defined responsibilities, boundaries, and handoff
protocols. The PM orchestrator is the entry point for all coordination.

### Skills (15 active)

| # | Skill | Command | Role |
|---|---|---|---|
| 1 | PM Orchestrator | `/pm-orchestrator` | Entry point — classifies tasks, selects agents, decomposes goals, sequences work, enforces gates, tracks LLM phases |
| 2 | Data Analyst | `/data-analyst` | Data cleaning, validation, completeness tracking, descriptive summaries, country profiles |
| 3 | Data Scientist | `/data-scientist` | Statistical inference, hypothesis testing, metrics, trend analysis, chart specifications |
| 4 | Text Analytics Expert | `/text-analytics-expert` | NLP — dictionary validation, topic modeling, framing analysis, corpus linguistics |
| 5 | AI Engineer | `/ai-engineer` | LLM integration (Ollama/Groq), RAG pipeline, FAISS, embeddings, prompt engineering |
| 6 | Software Engineer | `/software-engineer` | Streamlit UI, component wiring, chart implementation, deployment, accessibility |
| 7 | UX Designer | `/ux-designer` | UI/UX design specs — layout, typography, spacing, color, accessibility |
| 8 | QA Tester | `/qa-tester` | Testing, WCAG audits, regression checks, lint verification |
| 9 | DevOps Engineer | `/devops-engineer` | Posit Connect deployment, CI/CD, requirements, environment config |
| 10 | Focused PR | `/focused-pr` | Clean PR enforcement |
| 11 | Sync Requirements | `/sync-requirements` | requirements.txt management |
| 12 | Model Eval Report | `/model-eval-report` | Quarto evaluation report generation |
| 13 | Vignette | `/vignette` | Quarto app vignette generation |
| 14 | Stakeholder Advocate | `/stakeholder-advocate` | Last-gate user advocacy review — stress-tests outputs from DPO, government, researcher, and advocate perspectives before human approval |
| 15 | Compliance Audit | `/compliance-audit` | Pre-release quality gate — 250 requirements across 15 categories, structured verdicts, gap analysis |

### Reference files (`.claude/references/`)

Consulted by agents during their work — not triggered independently.

| File | Consulted by | Purpose |
|---|---|---|
| `table-standards.md` | data-analyst, data-scientist, software-engineer, ux-designer, qa-tester | Tabular typography (IBCS, APA, Few), formatting, WCAG tables, Streamlit implementation, tier system |
| `table-standards-enforcement.md` | all role skills | Gap analysis and enforcement additions for table standards |
| `chart-theme.md` | data-scientist, software-engineer, ux-designer | WCAG-compliant chart colors and palettes |
| `data-health.md` | data-analyst | Hardcoded number scanning |
| `wcag-audit.md` | qa-tester, software-engineer | Accessibility audit procedures including table-specific WCAG checks |
| `require-permission.md` | all role skills | Change approval gate protocol |
| `requirements-registry.md` | compliance-audit, pm-orchestrator | 250 tracked requirements, gap summary, priority classification |
| `no-data-download.md` | all role skills | Data download prohibition policy |

### How to use the agent system

**Multi-agent tasks (most work):**
```
/pm-orchestrator Analyze whether rights-based language is increasing and show it
on the dashboard
```
The PM classifies the task, selects the team, decomposes into sub-tasks,
and guides you through invoking each specialist in order.

**Single-agent tasks:**
```
/data-analyst How many documents does Kenya have?
/data-scientist Is the regional difference in Article 24 significant?
/software-engineer Fix the spacing on the country profile page
```

### Dependency graph

Tasks flow through agents in this order. The PM enforces the sequence.

```
PM Orchestrator (classify, select, route)
    │
    ├── Data Analyst (clean, validate, describe)
    ├── Text Analytics Expert (NLP features)
    └── AI Engineer (RAG, LLM, embeddings)
            │
            ▼
        Data Scientist (inference, metrics, chart specs)
            │
            ▼
        UX Designer (visual specs)
            │
            ▼
        Software Engineer (implement, wire)
            │
            ▼
        QA Tester (verify, audit)
            │
            ▼
        Stakeholder Advocate (user-group review)
```

### Quality gates

Every handoff between agents must pass a gate. Key gates:

- **Permission Gate:** User approves Change Summary before any file write
- **PM Gate:** LLM phase has Design = ✅ before infrastructure work begins
- **Lint Gate:** `ruff check .` + `ruff format --check .` = zero errors after any code change
- **QA Gate:** Functional tests pass, WCAG verified after implementation
- **Table Gate:** Tables comply with `.claude/references/table-standards.md`
- **Stakeholder Gate:** Plain language, treaty terminology, article names, caveats, timestamp
- **Stakeholder Advocate Gate:** DPO, government, researcher, and advocate lens review on all user-facing outputs. Stakeholder Advocate verdicts (APPROVE/CHANGES REQUESTED/BLOCK) are recommendations to the human, not autonomous approvals.

## LLM development phases

The AI Engineer's work follows a 5-phase, 5-step pipeline tracked in
`LLM_Development/PHASE_TRACKER.md`. The PM orchestrator owns this file
and enforces the gates.

**Phases:** (1) AI Insights Panel → (2) Chat Q&A Interface → (3) RAG +
Semantic Search → (4) Policy Brief Generation → (5) Evaluation & QA

**Steps per phase:** Requirements → Design → Infrastructure → Integration → Evaluate

**Gate rule:** No phase step may begin until its predecessor is complete.
Design requires a `.pen` file in `LLM_Development/designs/` (except Phase 5,
which has no UI).

**Key files:**
- `LLM_Development/PHASE_TRACKER.md` — phase status tracker
- `LLM_Development/CRPD_LLM_Integration_Plan.qmd` — requirements
- `LLM_Development/LLM_Integration_Plan.qmd` — requirements
- `LLM_Development/designs/*.pen` — design artifacts

## Tech stack

- **Framework:** Streamlit 1.54.0
- **Visualizations:** Plotly 6.5.2
- **Data:** Pandas, NumPy, Scikit-learn, SciPy
- **Mapping:** Folium + streamlit-folium, pycountry, country-converter
- **LLM (local):** Ollama (llama3) — summaries, insights
- **LLM (cloud):** Groq (llama-3.3-70b) — chat, reports
- **Embeddings:** sentence-transformers (local)
- **Vector store:** FAISS IndexFlatIP
- **PDF extraction:** pdfplumber
- **NLP:** spaCy, NLTK, BERTopic, gensim, textstat
- **Testing:** Playwright + axe-playwright-python (WCAG audits)
- **Linting:** Ruff
- **Reports:** Quarto (.qmd → PDF)

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

```
app.py                          # Streamlit entry point + page routing
src/
  data_loader.py                # CSV loading, get_dataset_stats(), MODEL_DICT
  filters.py                    # Filter UI components & logic
  analysis.py                   # Article frequency, model shift, NLP, stopwords
  components.py                 # Reusable UI: metric cards, trends
  styles.py                     # Global CSS (UN Blue theme, WCAG focus)
  nav.py                        # Navigation bar, routing, dropdowns
  colors.py                     # Color palettes (all chart/table colors)
  crpd_article_dict.py          # 50+ CRPD articles with keyword phrases
  llm.py                        # LLM integration (Ollama/Groq)
  tab_overview.py               # Homepage: hero, metrics, "At a Glance"
  tab_explore.py                # Countries: map, trends, profiles, search
  tab_analyze.py                # Article coverage, co-occurrence, model shift
  tab_chat.py                   # Chat Q&A interface
  tab_brief.py                  # Policy brief generation
  tab_about.py                  # About & methodology
data/
  crpd_reports.csv              # Main dataset (read-only source of truth)
  faiss_index.bin               # FAISS vector index (AI Engineer manages)
  chunks_metadata.json          # Chunk metadata for RAG (AI Engineer manages)
  embeddings.npy                # Embedding vectors (AI Engineer manages)
  pdfs/                         # Downloaded UN document PDFs
scripts/
  table_lint.py                 # Table standards linter (9 automated checks)
  wcag_audit.py                 # WCAG accessibility audit
  sync_new_documents.py         # Document sync
  check_requirements.py         # Requirements alignment check
LLM_Development/
  PHASE_TRACKER.md              # LLM phase status (PM owns)
  CRPD_LLM_Integration_Plan.qmd  # LLM requirements
  LLM_Integration_Plan.qmd     # LLM requirements
  designs/                      # .pen design files per phase
  build_knowledge_base.py       # Chunk, embed, build FAISS index
  download_pdfs.py              # PDF downloader
  evaluate_phase*.py            # Evaluation scripts per phase
.claude/
  skills/                       # Agent skill files (15 active)
    pm-orchestrator/SKILL.md    # PM Orchestrator (entry point)
    data-analyst/SKILL.md
    data-scientist/SKILL.md
    text-analytics-expert/SKILL.md
    ai-engineer/SKILL.md
    software-engineer/SKILL.md
    ux-designer/SKILL.md
    qa-tester/SKILL.md
    devops-engineer/SKILL.md
    stakeholder-advocate/SKILL.md
    focused-pr/SKILL.md
    sync-requirements/SKILL.md
    model-eval-report/SKILL.md
    vignette/SKILL.md
    compliance-audit/SKILL.md
  references/                   # Reference files consulted by agents
    table-standards.md
    table-standards-enforcement.md
    chart-theme.md
    data-health.md
    wcag-audit.md
    require-permission.md
    requirements-registry.md
    no-data-download.md
```

## Linting (mandatory for all code changes)

This project uses **Ruff** for linting and formatting. Configuration is in
`pyproject.toml`.

After editing ANY Python file, always run:
```bash
ruff check . --fix    # Auto-fix lint issues
ruff format .         # Auto-format code style
ruff check .          # Verify zero remaining errors
```

All three commands must pass with zero errors before committing. Key rules:
- Double quotes for all strings
- Imports ordered: stdlib → third-party → local (`src.*`)
- No unused imports, no unused variables, no trailing whitespace
- 100-character line length (E501 is ignored — Plotly configs may run wider)

## Table standards

All tables — both in conversation and on the dashboard — must follow
`.claude/references/table-standards.md`. Key rules:

- **Tier 1 (conversational):** Dynamic values, n=, treaty terminology,
  decimal alignment, plain-language headers, uniform precision
- **Tier 2 (dashboard):** Full standards — Tier 1 + WCAG markup,
  `src/colors.py` palettes, accessibility attributes (CSV download
  currently disabled by no-data-download policy)

Run the automated linter after any table work:
```bash
python scripts/table_lint.py src/
```
Eight active checks: hardcoded numbers, terminology, null representation,
precision, captions, WCAG `<th scope>`, hardcoded colors, raw column names.
(CSV download check disabled by no-data-download policy.)

## Key conventions

- **Routing:** Query-param based (`?page=overview`, `?page=countries&sub=map`)
- **Caching:** `@st.cache_data` for data loading, article frequency, filter
  option lists. `@st.cache_resource` for FAISS index, embedding model. Never
  cache LLM generation or chart rendering.
- **Colors:** All colors from `src/colors.py`. Never hardcode hex values.
  UN Blue (#005bbb) for primary brand, light bg (#f8f9fa).
- **Fonts:** Inter (all UI text), IBM Plex Mono (code/metadata only)
- **Accessibility:** WCAG 2.2 AA — visible focus outlines, keyboard nav,
  contrast ≥ 4.5:1, alt-text on all charts, colorblind-safe palettes
- **Business logic** in `src/` modules; `app.py` stays thin (routing + wiring)
- **Keyword matching:** Pre-compiled regex; longest phrases first
- **Model analysis:** Medical Model vs Rights-Based Model via `MODEL_DICT`
  in `src/data_loader.py`
- **Treaty terminology:** "States Parties" (not "countries"), article names
  with numbers ("Article 24 (Education)"), doc types title-cased
- **Dynamic values:** All data counts from `get_dataset_stats()`. Never
  hardcode numbers — not in code, not in comments, not in UI text.
- **Permission gate:** No file modifications without user approval via the
  Change Summary protocol (`.claude/references/require-permission.md`)
- **Data download disabled:** No `st.download_button` or export UI permitted. See `.claude/references/no-data-download.md`. Human operator must explicitly re-enable.

## Protected files

These files have special modification rules:

| File | Who may modify | Approval required |
|---|---|---|
| `crpd_article_dict.py` | Text Analytics Expert | PM approval + corpus evidence |
| `MODEL_DICT` (in `src/data_loader.py`) | Text Analytics Expert | PM approval + corpus evidence |
| `LLM_Development/PHASE_TRACKER.md` | PM Orchestrator only | — |
| `data/crpd_reports.csv` | Never directly | Process through scripts only |
| `data/faiss_index.bin` | AI Engineer | Rebuild via `build_knowledge_base.py` |

## Git workflow

- Branch from `main`: `feature/*`, `fix/*`, `chore/*`, `docs/*`
- Commit messages: `Add …`, `Fix …`, `Refactor …`, `Docs …`
- PRs must describe what/why/how-tested + Posit Connect deployment notes
- Only `main` is deployed to Posit Connect
- Keep PRs focused — one feature/fix per PR
- Use `/focused-pr` skill for PR discipline

## Data notes

- Source: UN Treaty Body Database
- Do not commit large or sensitive datasets
- Document new data files in `docs/data.md`
- Country conversion uses `country_converter` library
- Missing data = em dash (—), not blank, N/A, or null

## Testing before PR

1. Lint passes: `ruff check . && ruff format --check .`
2. Table lint passes: `python scripts/table_lint.py src/`
3. App launches: `streamlit run app.py`
4. Navigate affected sections
5. Confirm filters, charts, tables render correctly
6. Tables follow tier-appropriate standards from `table-standards.md`
7. For data changes: provide before/after screenshots
8. WCAG audit: `python scripts/wcag_audit.py`
9. All stakeholder-facing output uses treaty terminology and plain language

## Dependencies

Pinned in `requirements.txt`. When adding packages, update requirements and
note in PR for Posit Connect deployment. Use `/sync-requirements` skill.