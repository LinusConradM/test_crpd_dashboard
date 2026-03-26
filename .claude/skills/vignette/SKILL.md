---
name: vignette
description: >
  Generates the CRPD Dashboard app vignette as a Quarto HTML document (~5 pages).
  TRIGGER this skill whenever the user asks to: "write the vignette", "create the vignette",
  "generate the vignette", "build the app vignette", "write up the vignette", "vignette file",
  "create a vignette", or any variation of producing the course vignette deliverable for the
  CRPD Dashboard app. The vignette is saved to the `vignette/` folder at the project root.
version: 1.0.0
---

# Vignette Skill

## What this skill does

Generates a professional Quarto `.qmd` vignette (~5 pages) documenting how to use the CRPD
Dashboard app, satisfying all 9 graded elements of the course rubric. Saves both the `.qmd`
source and renders it to a self-contained HTML file in `vignette/`.

---

## Graded elements this skill must satisfy

| Element | Points | Requirement |
|---------|--------|-------------|
| Vign.1 | 0.5 | YAML Header: Title, Author, Date, Output format |
| Vign.2 | 2.0 | Use Case: problem the app solves and for whom |
| Vign.3 | 1.0 | Required Packages: names and versions |
| Vign.4 | 2.0 | Data Source & Structure: data frames, variables, observations |
| Vign.5 | 3.0 | EDA Inputs, Controls & Outputs: scenario walkthrough with captioned + cross-referenced figures |
| Vign.6 | 3.0 | Statistical Analysis Inputs, Controls & Outputs: scenario walkthrough with captioned + cross-referenced figures |
| Vign.7 | 1.0 | References: ≥ 3 literature sources properly cited |
| Vign.8 | 0.5 | Individual Contributions: `#| include: false` — excluded from page count |
| Vign.9 | 2.0 | Readability: proper formatting, minimal spelling/grammar errors |

**Total: 15 points**

---

## Step-by-step workflow

### 1. Check for existing vignette

```bash
ls vignette/
```

If a `vignette_crpd_dashboard.qmd` already exists, ask the user whether to overwrite or create
a versioned copy (e.g., `vignette_crpd_dashboard_v2.qmd`).

### 2. Create the vignette folder

```bash
mkdir -p vignette
```

### 3. Read key project files before writing

Read these files to ensure accurate content — do NOT fabricate details:

- `data/crpd_reports.csv` — first 3 rows + column names (for Vign.4)
- `requirements.txt` — package names and pinned versions (for Vign.3)
- `src/tab_overview.py` — homepage features (for Vign.5 EDA section)
- `src/tab_explore.py` — countries/map features (for Vign.5 EDA section)
- `src/tab_analyze.py` — analysis features (for Vign.6 Statistical Analysis section)
- `src/tab_brief.py` — Policy Brief Generator (for Vign.6 Statistical Analysis section)
- `CLAUDE.md` — project overview, tech stack

### 4. Write the Quarto document

**Filename:** `vignette/vignette_crpd_dashboard.qmd`

---

#### YAML Header (Vign.1)

```yaml
---
title: "CRPD Dashboard: An Interactive Tool for Analysing Disability Rights Reporting"
author: "CRPD Analytics Project — American University, KOGOD School of Business"
date: "2026-03-20"
format:
  html:
    theme: cosmo
    toc: true
    toc-depth: 3
    toc-location: left
    number-sections: true
    embed-resources: true
    smooth-scroll: true
    fig-cap-location: bottom
execute:
  echo: false
  warning: false
  message: false
bibliography: references.bib
---
```

---

#### Section 1 — Use Case (Vign.2)

Write 3–4 paragraphs covering:

- **The problem:** UN member states submit periodic reports under the CRPD. These are
  dense, multi-page legal documents. Advocates, researchers, and policymakers have no
  efficient way to track reporting patterns, compare countries, or detect language shifts
  between the medical model and rights-based model of disability.
- **Who uses it:** UN treaty body researchers, disability rights advocates, CRPD Committee
  members, academics studying international human rights compliance.
- **What the app enables:**
  1. Explore 585 documents across 155 countries (2010–2026)
  2. Map and compare reporting frequency by country and region
  3. Detect article coverage gaps and model-framing language
  4. Generate AI-powered policy briefs grounded in actual UN documents
  5. Ask questions directly to a RAG-backed Chat Q&A interface

---

#### Section 2 — Required Packages (Vign.3)

Use a markdown table. Pull **exact version numbers** from `requirements.txt`.
Group by category:

| Category | Package | Version | Purpose |
|----------|---------|---------|---------|
| Framework | streamlit | pinned | App framework |
| Visualisation | plotly | pinned | Interactive charts |
| Visualisation | folium | pinned | Choropleth maps |
| Visualisation | streamlit-folium | pinned | Folium ↔ Streamlit bridge |
| Data | pandas | pinned | Data wrangling |
| Data | numpy | pinned | Numerical operations |
| ML / NLP | scikit-learn | pinned | TF-IDF, clustering |
| ML / NLP | sentence-transformers | pinned | Semantic embeddings (mpnet) |
| ML / NLP | faiss-cpu | pinned | Vector similarity search |
| LLM | groq | pinned | Groq API client (llama-3.3-70b) |
| Geography | pycountry | pinned | ISO country codes |
| Geography | country-converter | pinned | Country name normalisation |
| PDF | pdfplumber | pinned | PDF text extraction |

Note: fill in actual version numbers from `requirements.txt` — never invent them.

---

#### Section 3 — Data Source & Structure (Vign.4)

Write 2–3 paragraphs covering:

- **Source:** UN Treaty Body Database (https://tbinternet.ohchr.org). Documents downloaded
  via UN Digital Library API.
- **Main dataset:** `data/crpd_reports.csv`
  - **Observations:** 585 documents
  - **Countries:** 155 unique
  - **Year range:** 2010–2026
  - **Key variables:**
    - `doc_type` — type of report (State Report, List of Issues, Concluding Observations, etc.)
    - `country` — submitting state
    - `year` — submission year
    - `region` / `subregion` — UN geographic groupings
    - `word_count` — document length
    - `language` — document language
    - `symbol` — UN document symbol (unique ID)
    - `clean_text` — pre-processed full text for NLP
- **Supplementary data:** 14,391 text chunks indexed in `data/faiss_index.bin` (FAISS vector
  store) and `data/chunks_metadata.json` — used by the RAG pipeline and semantic search.

Include a small inline code block showing how to load the data (as a Quarto code chunk with
`echo: true` so the reader can see the code):

```python
import pandas as pd
df = pd.read_csv("data/crpd_reports.csv")
print(df.shape)         # (585, 11)
print(df.dtypes)
print(df["doc_type"].value_counts().head())
```

---

#### Section 4 — EDA Inputs, Controls & Outputs (Vign.5)

**Scenario:** *"A disability rights researcher wants to understand which regions submit the
most CRPD reports, and whether reporting has grown over time."*

Walk through this workflow step by step, with a captioned + cross-referenced figure at each
key output:

**Step 1 — Overview page**
- Navigate to the **Overview** page (default landing page)
- Point out the four metric cards: Total Documents, Countries Covered, Year Range, Avg Word Count
- Show the "At a Glance" distribution charts

**Step 2 — Explore → Global Map**
- Navigate to **Countries → Global Map**
- Use the **Year Range** slider and **Region** multi-select in the left sidebar to filter
- The choropleth map colours countries by document count; darker = more reports
- Hovering a country shows its name, count, and latest report year
- *Figure: screenshot or simulated map showing Africa vs Europe reporting density*

**Step 3 — Explore → Reporting Trends**
- Navigate to **Countries → Reporting Trends**
- Select **"All Regions"** — observe the year-over-year submission line chart
- Toggle individual regions to compare reporting trajectory
- *Figure: line chart of reporting trends 2010–2025*

**Step 4 — Explore → Country Profiles**
- Select a single country (e.g., Uganda) from the dropdown
- The profile shows: total reports, article coverage bar chart, key phrases
- *Figure: Uganda country profile panel with article coverage*

**Quarto figures:** Combine Steps 2 and 3 figures into a layout panel using:

```
::: {layout-ncol=2}
![Caption A](figures/map_choropleth.png){#fig-map}
![Caption B](figures/trends_line.png){#fig-trends}
:::
```

Cross-reference in text: `As shown in @fig-map ...` and `@fig-trends reveals ...`

---

#### Section 5 — Statistical Analysis Inputs, Controls & Outputs (Vign.6)

**Scenario:** *"A UN treaty body analyst wants to identify which CRPD articles are most
frequently cited in Sub-Saharan African reports, and then generate a targeted policy brief."*

Walk through this workflow:

**Step 1 — Analyze → Article Coverage**
- Navigate to **Analyze → Article Coverage**
- Filter by **Region = Sub-Saharan Africa** and **Year = 2015–2025**
- The bar chart shows normalised article frequency across all 50+ CRPD articles
- Articles 19 (Independent Living), 24 (Education), and 27 (Work & Employment) typically rank highest
- *Figure: article coverage bar chart for Sub-Saharan Africa*

**Step 2 — Analyze → Model Shift**
- Navigate to **Analyze → Model Shift**
- The time-series chart shows the ratio of Medical Model vs Rights-Based Model language per year
- A rising rights-based score indicates improving CRPD alignment
- *Figure: model shift time-series chart*

**Step 3 — Analyze → Co-occurrence**
- Navigate to **Analyze → Co-occurrence**
- The heatmap shows which articles are frequently cited together
- *Figure: article co-occurrence heatmap*

**Step 4 — Policy Brief Generator**
- Navigate to **Policy Brief ✦**
- Select countries: Uganda, Kenya, Tanzania
- Select articles: 19, 24, 27
- Set year range: 2015–2025
- Choose format: Full Report
- Click **Generate Brief**
- The brief appears in four colour-coded sections: Context, Key Findings, Recommendations, Sources
- *Figure: generated brief preview panel*

**Quarto figures:** Combine Article Coverage + Model Shift as a 2-column layout:

```
::: {layout-ncol=2}
![Article coverage — Sub-Saharan Africa](figures/article_coverage.png){#fig-articles}
![Medical vs Rights-Based model shift](figures/model_shift.png){#fig-modelshift}
:::
```

Cross-reference: `@fig-articles shows ...` and `The upward trend in @fig-modelshift ...`

---

#### Section 6 — References (Vign.7)

Include at least **3 properly cited sources** using Quarto's `[@key]` citation syntax.
Create a `vignette/references.bib` BibTeX file alongside the `.qmd`.

Suggested references (use these — they are directly relevant):

```bibtex
@article{kayess2008,
  author  = {Kayess, Rosemary and French, Phillip},
  title   = {Out of Darkness into Light? Introducing the Convention on the Rights of Persons with Disabilities},
  journal = {Human Rights Law Review},
  year    = {2008},
  volume  = {8},
  number  = {1},
  pages   = {1--34},
  doi     = {10.1093/hrlr/ngm044}
}

@book{quinn2002,
  author    = {Quinn, Gerard and Degener, Theresia},
  title     = {Human Rights and Disability: The Current Use and Future Potential of United Nations Human Rights Instruments in the Context of Disability},
  publisher = {United Nations},
  year      = {2002},
  address   = {New York and Geneva}
}

@article{mccallum2013,
  author  = {McCallum, Ron},
  title   = {The United Nations Convention on the Rights of Persons with Disabilities: Some Reflections},
  journal = {Sydney Law Review},
  year    = {2013},
  volume  = {35},
  pages   = {831--843}
}

@article{lord2008,
  author  = {Lord, Janet E. and Stein, Michael Ashley},
  title   = {The Domestic Incorporation of Human Rights Law and the United Nations Convention on the Rights of Persons with Disabilities},
  journal = {Washington Law Review},
  year    = {2008},
  volume  = {83},
  number  = {4},
  pages   = {449--479}
}
```

In-text use: `[@kayess2008]`, `[@quinn2002]`, `[@lord2008]`

---

#### Section 7 — Individual Contributions (Vign.8)

This section **must use `#| include: false`** so it does NOT appear in the rendered output
and does NOT count against the 5-page limit:

````markdown
```{python}
#| include: false
# Individual Contributions (not rendered in output)
# Team Member 1 — [Name]: Overview page, data loading, country mapping
# Team Member 2 — [Name]: Article analysis, co-occurrence, model shift
# Team Member 3 — [Name]: RAG pipeline, Chat Q&A, semantic search
# Team Member 4 — [Name]: Policy Brief Generator, LLM integration
# Team Member 5 — [Name]: Evaluation harness, Quarto reports, deployment
```
````

---

### 5. Create the references file

Write `vignette/references.bib` with the 4 BibTeX entries from Vign.7.

### 6. Create the figures folder

```bash
mkdir -p vignette/figures
```

**Important:** The skill writes the `.qmd` with figure references. If actual screenshots are
not yet available, use placeholder comments:

```markdown
<!-- TODO: Replace with actual screenshot from running app -->
![Choropleth map of CRPD report counts by country (2010–2025)](figures/map_choropleth.png){#fig-map}
```

Alternatively, generate synthetic figures using Plotly/Pandas with actual data from
`data/crpd_reports.csv` inside `{python}` code chunks — this is preferred over placeholders.

**Preferred approach for figures:** Use `{python}` code chunks that read
`data/crpd_reports.csv` and generate the figures programmatically. This ensures the
figures always reflect real data and render at quarto render time. Example:

```python
#| label: fig-map
#| fig-cap: "Number of CRPD reports submitted per country, 2010–2025. Darker shading indicates more submissions."
import pandas as pd
import plotly.express as px

df = pd.read_csv("../data/crpd_reports.csv")
counts = df.groupby("country").size().reset_index(name="reports")
fig = px.choropleth(counts, locations="country", locationmode="country names",
                    color="reports", color_continuous_scale="Blues",
                    title="CRPD Reports per Country")
fig.update_layout(height=400, margin=dict(l=0, r=0, t=40, b=0))
fig.show()
```

Use this approach for all figures where possible. For UI screenshots (Policy Brief panel,
Chat interface), use static image placeholders with a TODO note.

---

### 7. Page length guidance

The vignette must be **approximately 5 pages** when rendered. Calibrate as follows:

- Section 1 Use Case: ~0.5 page
- Section 2 Packages: ~0.5 page (table)
- Section 3 Data Structure: ~0.5 page
- Section 4 EDA walkthrough + 2 figures: ~1.5 pages
- Section 5 Statistical Analysis walkthrough + 2 figures: ~1.5 pages
- Section 6 References: ~0.25 page
- Individual Contributions: 0 pages (hidden)

**Total: ~5 pages** ✅

If the draft runs long, trim narrative prose — keep figures and tables.
If it runs short, expand the scenario walkthroughs with more interpretive commentary.

---

### 8. Tell the user what was created

After saving both files, report:

```
✅ Vignette created:
   vignette/vignette_crpd_dashboard.qmd   ← source
   vignette/references.bib                ← bibliography

To render:
   quarto render vignette/vignette_crpd_dashboard.qmd

Output: vignette/vignette_crpd_dashboard.html  (self-contained, ~5 pages)

Figures: generated from real data via Python code chunks — no static screenshots needed.
Replace figures/map_choropleth.png and figures/policy_brief_panel.png with actual
app screenshots when available.
```

---

## Formatting rules

- Use `#` H1 only for the document title (handled by YAML)
- Use `##` for top-level sections (numbered by Quarto)
- Use `###` for subsections (scenario steps)
- Use Quarto callout boxes for tips:
  - `::: {.callout-tip}` — for workflow shortcuts or key insights
  - `::: {.callout-note}` — for data notes or caveats
- All figures: captioned + cross-referenced via `@fig-label`
- Layout panels: use `{layout-ncol=2}` to combine related figures and save vertical space
- Code chunks visible to reader: use `#| echo: true` only for the data loading example (Vign.3)
- All other code chunks: `#| echo: false` (charts render silently)

---

## UN Blue colour palette (use in all Plotly charts)

```python
UN_BLUE    = "#005bbb"
UN_GOLD    = "#f5a623"
PASS_GREEN = "#27ae60"
LIGHT_GREY = "#f8f9fa"
MID_GREY   = "#6c757d"
```

---

## File structure after skill runs

```
vignette/
├── vignette_crpd_dashboard.qmd     ← source (submit this)
├── vignette_crpd_dashboard.html    ← rendered output (submit this)
└── references.bib                  ← bibliography file
```
