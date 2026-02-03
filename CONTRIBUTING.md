# Contributing Guide (CRPD Dashboard)

Thanks for contributing to the CRPD Dashboard project. This repository is configured to require pull requests so changes are reviewed before they affect the deployed dashboard.

## Key Principles
- `main` is protected and should remain deployable.
- No direct pushes to `main` (use feature branches + PRs).
- Keep PRs small and focused.
- Document anything that affects indicators, data transformations, or policy-facing outputs.

---

## 1) Issue → Branch → PR (standard workflow)

### A. Start with an Issue
Every meaningful change should have an Issue (bug, feature, refactor, data update).
- If an Issue already exists, claim it or comment that you’re taking it.
- If not, create one describing the intent and expected behavior.

### B. Create a feature branch from `main`
Branch naming conventions:
- `feature/<short-description>`
- `fix/<short-description>`
- `chore/<short-description>`
- `docs/<short-description>`

Examples:
- `feature/country-filter`
- `fix/missing-values-imputation`
- `chore/requirements-cleanup`

### C. Open a Pull Request (PR) into `main`
PRs must include:
- What changed (summary)
- Why (context)
- How tested locally (see “Local testing” below)
- Any deployment notes (packages, secrets, env vars)

Use closing keywords when appropriate:
- `Closes #123`

---

## 2) Local development (Streamlit)

### Recommended setup
Use a virtual environment and install dependencies:

- Create/activate env (choose one):
  - `python -m venv .venv` (then activate)
  - conda env (if the team standardizes on it)

- Install dependencies:
  - `pip install -r requirements.txt`

### Run the app locally
Run Streamlit from the repo root (adjust the path if needed):
- `streamlit run app.py`

If the entry point is different (e.g., `src/app.py`), use:
- `streamlit run src/app.py`

### Secrets and configuration (important)
Do NOT commit secrets (tokens, passwords, private keys).

If the app uses Streamlit secrets, place local values here (never commit):
- `.streamlit/secrets.toml`

If the app uses environment variables, document them in:
- `docs/configuration.md` (or a “Configuration” section in README)

---

## 3) What “tested” means (minimum expectations)
Before requesting review, please do at least:

### UI sanity checks
- App starts cleanly with `streamlit run ...`
- Navigate the main pages/sections that your change affects
- Confirm key filters and charts render

### Data/logic changes (extra care)
If your change affects indicators, scoring, transformations, or mappings:
- Validate results on a small sample and/or a known baseline
- Describe assumptions in the PR
- Include screenshots or a short GIF if it changes visible outputs

---

## 4) PR review rules (repo-enforced)
- At least **1 approval** is required.
- Approvals are dismissed if new commits are pushed after approval.
- All review conversations must be resolved before merge.

---

## 5) Posit Connect deployment notes
The dashboard is deployed on Posit Connect.

General rule:
- Only merged changes from `main` should be deployed.

If your change requires deployment updates, call it out clearly in the PR:
- New Python packages / version constraints
- Changes to `requirements.txt`
- New environment variables
- Updates to secrets configuration
- Any file paths that differ between local and Connect

---

## 6) Repo hygiene
### Keep PRs focused
- Prefer multiple small PRs over one giant PR.

### Avoid committing large data
- Don’t commit raw datasets or exports unless explicitly agreed.
- Use `.gitignore` for local artifacts and caches.

### Suggested commit messages
- `Add …`
- `Fix …`
- `Refactor …`
- `Docs …`

---

## 7) Asking for help
If you’re unsure where something fits:
- Open a draft PR early, or
- Ask a question on the Issue before implementing
