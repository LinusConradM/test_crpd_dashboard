# Contributing Guide (CRPD Dashboard)

Thanks for contributing to the CRPD Dashboard. This repo is protected so changes are reviewed before they affect the deployed dashboard on Posit Connect.

## Planned repository structure
The repo is moving toward this structure (it does not fully match yet):

crpd-dashboard/
├── app.py                  # Main Streamlit application
├── data/                   # Data files
├── src/                    # Source code modules
├── assets/                 # Static assets
└── docs/                   # Documentation

If you notice the current repo differs, follow existing conventions and flag structural changes in your PR.

---

## 1) Workflow: Issue → Branch → Pull Request

### A. Start with an Issue
Every meaningful change should have an Issue (bug, feature, refactor, data update).  
If an Issue exists, comment that you’re taking it.

### B. Create a branch from `main`
Branch naming:
- feature: `feature/<short-description>`
- bugfix: `fix/<short-description>`
- maintenance: `chore/<short-description>`
- docs: `docs/<short-description>`

Examples:
- `feature/country-filter`
- `fix/missing-values-display`
- `chore/requirements-refresh`

### C. Open a PR into `main`
PR description must include:
- **What changed**
- **Why**
- **How tested locally**
- **Any Posit Connect notes** (new packages, env vars, secrets, file paths)

Use closing keywords when appropriate:
- `Closes #123`

---

## 2) Local development (Streamlit)

### Create and activate a virtual environment
Choose one:

**venv**
- `python -m venv .venv`
- macOS/Linux: `source .venv/bin/activate`
- Windows: `.venv\Scripts\activate`

**conda**
- `conda create -n crpd-dashboard python=3.11`
- `conda activate crpd-dashboard`

### Install dependencies
- `pip install -r requirements.txt`

### Run the app
From the repo root:
- `streamlit run app.py`

---

## 3) Code organization conventions

### app.py
- Keep `app.py` as the Streamlit entry point and UI wiring.
- Prefer pushing business logic into `src/` modules.

### src/
- Put reusable logic in `src/` (data loading, transforms, indicator computation, plotting helpers).
- Avoid duplicating logic in multiple pages/sections.

### assets/
- Static resources only (images, icons, style assets).

### docs/
- Documentation and project notes:
  - `docs/configuration.md` (env vars, secrets, runtime)
  - `docs/data.md` (data sources, schemas, refresh procedures)
  - `docs/deployment.md` (Posit Connect details)

### data/
Important: do not commit large or sensitive datasets by accident.
- Small reference tables (e.g., mappings, ISO codes) are usually OK.
- Larger datasets should be staged via approved methods and/or external storage.
- If you add data files, document them in `docs/data.md`.

---

## 4) Secrets and configuration (critical)

Do NOT commit secrets (tokens, passwords, keys).

If using Streamlit secrets, keep local secrets in:
- `.streamlit/secrets.toml`  (must be gitignored)

If using environment variables:
- document required variables in `docs/configuration.md`

---

## 5) Testing / validation expectations

Minimum before requesting review:
- App launches locally: `streamlit run app.py`
- Navigate the areas affected by your change
- Confirm key UI elements render (filters, charts, tables)

For changes that affect indicators/scoring/transforms:
- Provide a quick sanity check (before/after screenshots or a short explanation)
- Note assumptions and any known limitations

---

## 6) Posit Connect deployment notes

The app is deployed on Posit Connect. In PRs, call out anything that affects deployment:
- New/updated Python dependencies (`requirements.txt`)
- New secrets keys / env vars
- File path assumptions (relative paths, working directory)
- Any system dependency needs (rare, but flag if present)

General rule:
- Only merged changes from `main` should be deployed.

---

## 7) PR hygiene

- Keep PRs focused (one feature/bugfix per PR).
- Prefer small PRs over large multi-week branches.
- Add screenshots/GIFs for UI-visible changes when helpful.

Suggested commit messages:
- `Add …`
- `Fix …`
- `Refactor …`
- `Docs …`

---

---

## 8) Reports (Quarto → PDF)

We use Quarto (`.qmd`) to write and render project reports to PDF. Contributors may use any IDE (Positron, VS Code, PyCharm, etc.); the shared contract is that reports must render successfully using the Quarto CLI.

### Where reports live
Reports should be placed in:
- `reports/` (recommended), or
- `docs/` for shorter documentation-style pages

If you introduce `reports/`, suggested structure:

reports/
├── _quarto.yml
├── index.qmd
└── <report-name>.qmd

### Required software
- **Quarto** (team-standard version; see below)
- A **LaTeX** distribution for PDF rendering:
  - Recommended: **TinyTeX** (lightweight), or
  - TeX Live / MacTeX (heavier)

### Standard render commands
From the repository root:

- Render all reports in the project:
  - `quarto render`

- Render a single report:
  - `quarto render reports/<report-name>.qmd`

### Quarto version policy
To avoid “works on my machine” differences, contributors should use the same major/minor Quarto version.

- Recommended policy: use the team’s current pinned version shown in `docs/configuration.md`
- To check your version:
  - `quarto --version`

### Python execution in Quarto (choose one approach)

Quarto can execute Python code in `.qmd` in two main ways. This project uses **one** of the following approaches (document which is current in `docs/configuration.md`):

#### Option A (recommended for cross-platform teams): Jupyter kernel execution
This approach tends to be the most consistent across IDEs and operating systems.

- Ensure Jupyter is installed in your environment:
  - `pip install jupyter`

- Ensure your environment is available as a kernel (example):
  - `python -m ipykernel install --user --name crpd-dashboard --display-name "crpd-dashboard"`

- Render normally:
  - `quarto render reports/<report-name>.qmd`

Notes:
- This option is ideal when multiple contributors have different Python installations but can standardize on a kernel name.

#### Option B (direct interpreter): use a specific Python path
This approach is useful when the project standardizes on a known Python environment per repo.

- In the relevant Quarto config (e.g., `reports/_quarto.yml`), specify the interpreter path under `execute`.

Example (illustrative; do not hardcode a personal machine path unless the team standardizes it):
- `execute:`
  - `python: /path/to/python`

Then render:
- `quarto render reports/<report-name>.qmd`

Notes:
- This option works well when the team explicitly manages Python envs and paths, but can be more machine-specific.

### R execution (if applicable)
If a report uses R code:
- Ensure R is installed and required packages are available.
- Render with the same `quarto render` commands above.

### What to commit (PDF outputs)
By default, we do **not** require committing rendered PDFs unless explicitly requested.
Preferred options:
- Commit only `.qmd` sources, and render PDFs for releases/milestones, or
- Store PDFs in a designated folder (e.g., `reports/output/`) if the team decides to version outputs

If PDFs are committed, keep them organized and avoid frequent churn.

### Troubleshooting PDF rendering
- If PDF rendering fails, it is often a LaTeX issue.
- Confirm LaTeX is installed and working (TinyTeX or TeX Live/MacTeX).
- Try:
  - `quarto render reports/<report-name>.qmd --verbose`

---

## 9) Asking for help
If you’re unsure where something fits:
- Open a draft PR early, or
- Ask a question on the Issue before implementing
