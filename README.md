# CRPD Disability Rights Data Dashboard

The first NLP and AI-powered platform to make the full UN Convention on the
Rights of Persons with Disabilities (CRPD) reporting cycle searchable, visual,
and actionable — built for disability rights organizations, governments,
researchers, and policy advocates.

**Live dashboard:** <https://idpp.connect.posit.cloud/crpd-dashboard>

## Project Overview

This interactive Streamlit dashboard analyzes CRPD reporting patterns across
150+ States Parties and 5 document types (2010–2026). It combines corpus
linguistics, NLP, and AI-powered retrieval to surface treaty compliance trends,
rights-based language shifts, and cross-country comparisons from the full CRPD
reporting cycle.

> Exact dataset counts (countries, documents, year range) are dynamic and
> computed at runtime via `get_dataset_stats()` in `src/data_loader.py`.

### Who This Platform Serves

| User Group | What They Need |
|---|---|
| **DPOs (disability rights organizations)** | Accountability evidence — which rights are neglected, which governments are falling short |
| **Governments & national focal points** | Compliance benchmarking — how their reporting compares to regional peers |
| **Researchers** | Rigorous, reproducible data with proper methodology documentation |
| **Policy advocates** | Clear, quotable numbers and shareable visualizations for policy briefs |

**Accessibility is subject matter, not just compliance.** The CRPD mandates
accessible information (Articles 9 and 21). Building an inaccessible disability
rights platform is a contradiction. WCAG 2.2 AA is the minimum standard.

## Features

### 17 Dashboard Pages

**Home**
- Hero section with key corpus metrics
- "At a Glance" summary cards and reporting overview

**Explore (6 pages)**
- **Map View** — Interactive Folium choropleth with zoom, pan, and click popups — 4 switchable metrics (document count, article coverage, rights-based %, reporting completeness)
- **Reporting Timeline** — Temporal trends in CRPD reporting across document types
- **Country Profiles** — Deep-dive into individual State Party reporting history with 3-mode selector: Individual State Party, Geographic Region, International Organization
- **Compare Countries** — Side-by-side comparison supporting individual, regional, and organization-level aggregation. Region and Organization modes show aggregated group-level data (e.g., 3 rows for 3 regions, not 90 rows for member countries)
- **Explore Documents** — Browse and filter the full document corpus. Includes Document Comparison — side-by-side analysis of 2–5 documents with article overlap heatmap, rights-based language comparison, and Jaccard similarity
- **Semantic Search** — AI-powered vector similarity search across all CRPD documents using FAISS

**Analyze (6 pages)**
- **Article Coverage** — Which CRPD articles receive the most/least attention
- **Article Deep-Dive** — Detailed analysis of individual article references across the corpus
- **Article Co-occurrence** — Which articles are discussed together
- **Keywords & Topics** — NLP-derived keyword and topic analysis
- **Model Shift Analysis** — Medical model vs. rights-based language trends over time
- **Regional Reporting Profiles** — Radar charts comparing regional reporting patterns

**AI-Powered (2 pages)**
- **AI Research Assistant** — RAG-powered chat interface for querying the CRPD corpus with inline source citations (Groq llama-3.3-70b)
- **Policy Brief Generator** — AI-generated policy briefs with computed data context, treaty-aware prompting, separate rate limiting, and AI-generated content disclaimer

**About**
- Methodology documentation, data sources, team, and accessibility statement

> Export capabilities are currently disabled platform-wide by policy.
> See `.claude/references/no-data-download.md`.

## Data

- **Source:** UN Treaty Body Database
- **Document types:** State Reports, Lists of Issues (LOI), Written Replies, Concluding Observations, Responses to Concluding Observations
- **Coverage:** 150+ States Parties, 2010–2026
- **Format:** Full-text corpus with metadata (country, region, subregion, year, document type)
- **Geography:** `countries.geojson` — Natural Earth country boundaries (bundled locally, no CDN dependency)

## Tech Stack

| Component | Technology |
|---|---|
| **Framework** | Streamlit 1.54.0 |
| **Visualizations** | Plotly 6.5.2, Altair 5.5.0 |
| **Data processing** | Pandas, NumPy, Scikit-learn, SciPy |
| **Mapping** | Folium + streamlit-folium (interactive choropleths, replaced earlier Altair static maps), pycountry, country-converter |
| **LLM (local)** | Ollama — qwen3:8b (configurable via `OLLAMA_MODEL` env var) — summaries, insights |
| **LLM (cloud)** | Groq — llama-3.3-70b-versatile (configurable via `GROQ_MODEL` env var) — chat, policy briefs |
| **LLM (premium)** | Anthropic Claude (claude-sonnet-4, claude-haiku-4.5) — Research & Citation pipeline |
| **Embeddings** | sentence-transformers (all-mpnet-base-v2, 768-dim) |
| **Vector store** | FAISS IndexFlatIP |
| **PDF extraction** | pdfplumber, PyMuPDF (pymupdf4llm) |
| **Research export** | fpdf2 (PDF), python-docx (DOCX) |
| **Security** | bleach (HTML sanitization for LLM output), html.escape() (defense-in-depth) |
| **Data validation** | country-converter (ISO3 normalization, region/subregion mapping) |
| **Linting** | Ruff |
| **Testing** | Playwright + axe-playwright-python (WCAG audits) |
| **Reports** | Quarto (.qmd → HTML/PDF) |

### LLM Architecture

The dashboard uses a dual-LLM stack — both at $0/month:

- **Ollama (local, qwen3:8b):** Handles lightweight, frequent tasks like AI
  Insights Panel summaries. Runs on-device with no API key, no rate limits,
  and no internet dependency. RAG-optimized for 2026 workloads.
- **Groq (cloud API, llama-3.3-70b-versatile):** Powers the AI Research
  Assistant and Policy Brief Generator — tasks requiring deeper reasoning,
  source citation, and structured multi-section output. Free tier with 12K
  tokens-per-minute rate limit.
- **RAG pipeline:** Documents are chunked, embedded with sentence-transformers
  (all-mpnet-base-v2), and indexed in FAISS. Semantic search retrieves
  relevant passages (minimum 0.15 similarity threshold), which are injected
  into LLM prompts alongside computed data context from article frequency and
  model shift analysis.

**Centralized model config:** All model names are defined once in `src/llm.py`
as constants (`OLLAMA_MODEL`, `GROQ_MODEL`, `EMBEDDING_MODEL`) with
`os.environ.get()` override. To switch models:

```bash
OLLAMA_MODEL=mistral GROQ_MODEL=llama-3.3-70b-versatile streamlit run app.py
```

## Project Structure

```
app.py                              # Streamlit entry point, page routing, global Plotly theme
src/
  data_loader.py                    # CSV loading, get_dataset_stats(), MODEL_DICT
  analysis.py                       # Article frequency, model shift, NLP, stopwords
  filters.py                        # Filter UI components & logic
  components.py                     # Reusable UI: metric cards, trends
  styles.py                         # Global CSS (UN Blue theme, WCAG focus)
  nav.py                            # Navigation bar, routing, dropdowns
  colors.py                         # Color palettes (all chart/table colors)
  crpd_article_dict.py              # 50+ CRPD articles with keyword phrases
  llm.py                            # LLM integration (Ollama/Groq/Claude), RAG, semantic search
  tab_overview.py                   # Home: hero, metrics, "At a Glance"
  tab_explore.py                    # Explore: map, timeline, profiles, compare, documents, search
  tab_analyze.py                    # Analyze: coverage, deep-dive, co-occurrence, keywords, model shift
  tab_chat.py                       # AI Research Assistant (RAG chat)
  tab_brief.py                      # Policy Brief Generator
  tab_about.py                      # About & methodology
  tab_research.py                   # Research & Citation (local dev only, env-var gated)
  research_agent.py                 # Research agent logic
  research_export.py                # PDF/DOCX export for research briefings
  research_methodology.py           # Research methodology utilities
  research_prompts.py               # Research-specific LLM prompts
data/
  crpd_reports.csv                  # Main dataset (read-only source of truth)
  faiss_index.bin                   # FAISS vector index (768-dim, all-mpnet-base-v2)
  chunks_metadata.json              # Chunk metadata for RAG retrieval
  embeddings.npy                    # Embedding vectors
  countries.geojson                 # Natural Earth country boundaries (local, no CDN)
  pdfs/                             # Downloaded UN document PDFs
  markdown/                         # PDF → Markdown conversions
scripts/
  table_lint.py                     # Table standards linter (9 automated checks)
  wcag_audit.py                     # WCAG accessibility audit (Playwright + axe)
  sync_new_documents.py             # Document sync from UN Treaty Body Database
  check_requirements.py             # Requirements alignment check
  validate_agent_system.py          # Agent system validator (142 structural checks)
LLM_Development/
  PHASE_TRACKER.md                  # LLM phase status tracker
  CRPD_LLM_Integration_Plan.qmd    # LLM integration requirements
  LLM_Integration_Plan.qmd         # LLM integration plan
  CRPD_Research_Agent_TDD.md        # Research Agent technical design document
  build_knowledge_base.py           # Chunk, embed, build FAISS index
  evaluate_phases_1_2.py            # Phase 1–2 evaluation (Insights + Chat)
  evaluate_phase3.py                # Phase 3 evaluation (RAG + Semantic Search)
  evaluate_phase4.py                # Phase 4 evaluation (Policy Brief Generator)
  designs/                          # .pen design files per phase
.claude/
  skills/                           # 15 agent skill files (see Agent-Assisted Development)
  references/                       # 8 reference files consulted by agents
    table-standards.md              # Accessible table rendering standards (IBCS, APA, Few)
    table-standards-enforcement.md  # Table standards enforcement rules
    chart-theme.md                  # WCAG-compliant chart theming standards
    data-health.md                  # Data health monitoring & hardcoded number scanning
    wcag-audit.md                   # WCAG compliance audit procedures
    require-permission.md           # Permission-gated operations protocol
    requirements-registry.md        # 250 tracked requirements across 15 categories
    no-data-download.md             # Platform-wide download prohibition policy
```

## Installation

```bash
# Clone the repository
git clone https://github.com/derrickcogburn/crpd-dashboard.git
cd crpd-dashboard

# Create and activate virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the dashboard
streamlit run app.py
```

### Optional: Enable AI Features

**For AI Insights (local):**
```bash
# Install and start Ollama, then pull the model
ollama pull qwen3:8b
```

**For AI Research Assistant & Policy Briefs (cloud):**
```bash
# Set your free Groq API key
export GROQ_API_KEY="your-key-here"
```

> Model names are configurable via environment variables: `OLLAMA_MODEL`,
> `GROQ_MODEL`. Defaults are defined in `src/llm.py`.

## Accessibility

The CRPD mandates accessible information (Articles 9 and 21). Building an
inaccessible disability rights platform would be a contradiction. This
dashboard targets **WCAG 2.2 AA** compliance:

- Color contrast ≥ 4.5:1 on all text
- Colorblind-safe chart palettes from `src/colors.py`
- Keyboard-navigable interface with visible focus indicators
- ARIA labels and `role` attributes on custom components
- Alt-text descriptions on all charts
- Screen-reader-compatible headings hierarchy
- Interactive Folium maps with keyboard-navigable tooltips and click popups
- Custom accessible tables (`render_accessible_table()`) with proper `<th scope>`, `<caption>`, and scroll container attributes
- XSS sanitization via bleach on all LLM-generated content and `html.escape()` on FAISS chunk metadata
- Automated WCAG audits via Playwright + axe

## Development

### Linting

This project uses **Ruff** for linting and formatting:

```bash
ruff check . --fix    # Auto-fix lint issues
ruff format .         # Format code style
ruff check .          # Verify zero errors
```

### Testing

```bash
# Table standards linter
python scripts/table_lint.py src/

# WCAG accessibility audit
python scripts/wcag_audit.py

# Agent system validator (142 structural checks)
python scripts/validate_agent_system.py

# LLM evaluation (per phase)
python LLM_Development/evaluate_phases_1_2.py
python LLM_Development/evaluate_phase3.py
python LLM_Development/evaluate_phase4.py
```

### Git Workflow

- Branch from `main`: `feature/*`, `fix/*`, `chore/*`, `docs/*`
- Commit messages: `Add …`, `Fix …`, `Refactor …`, `Docs …`
- PRs must describe what/why/how-tested + Posit Connect deployment notes
- Only `main` is deployed to Posit Connect
- Keep PRs focused — one feature/fix per PR


## Deployment

Deployed on **Posit Connect** at
<https://idpp.connect.posit.cloud/crpd-dashboard>.

Dependencies are pinned in `requirements.txt`. Any new packages must be added
and noted in the PR for Posit Connect compatibility. Use the `/sync-requirements`
skill.

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines,
including branching, PR, testing, and deployment.

## Current Team

- Dr. Derrick Cogburn, American University
- Dr. Keiko Shikako, McGill University
- Mr. John Dylan Bustillo, American University
- Mr. Conrad Linus Muhirwe, American University
- Ms. Sharon Wanyana, American University
- Ms. Sofia Torres
- Mr. Juan David Lopez
- Ms. Olivia Prezioso, Northeastern University
- Institute on Disability and Public Policy (IDPP)

### Former Team Members

- Ms. Juliana Woods, American University
- Ms. Rachi Adhikari, American University
- Mr. Theodore Andrew Ochieng, American University

## License

This work is licensed under a [Creative Commons Attribution-NonCommercial 4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/).

## Citation

Cogburn, D. et al (2026). CRPD Disability Rights Data Dashboard. Institute on Disability and Public Policy, American University. https://idpp.connect.posit.cloud/crpd-dashboard
