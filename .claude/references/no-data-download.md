---
name: no-data-download
description: >
  Policy: All data download capabilities are disabled until explicitly
  re-enabled by the human operator. This includes CSV exports, PDF/DOCX
  briefing downloads, Markdown exports, and any other file download
  from the dashboard UI.
version: 1.0.0
status: ACTIVE
activated: 2026-03-23
deactivated: null
---

# No Data Download Policy

## Rule

**No code that enables a user to download any data or file from the
CRPD Dashboard may be written, added, or re-enabled until the human
operator explicitly says "I want to enable data download."**

## What is prohibited

- `st.download_button()` in any form
- CSV export from any table
- PDF export from any briefing or report
- DOCX export from any briefing or report
- Markdown export from any research output
- Any file download mechanism (direct links, generated files, etc.)
- Any UI element that says "Export", "Download", or "Save as file"

## What is allowed

- Internal data processing that writes temp files for computation
  (e.g., FAISS index building, cache files)
- The export functions in `src/research_export.py` may EXIST in the
  codebase as dormant code — they just cannot be called from any UI
- The TDD document may reference export as a future feature

## Enforcement

Every agent must check this policy before:
- Adding any `st.download_button` to any file
- Creating any export function that connects to the UI
- Suggesting "add a CSV download" as an improvement
- Implementing any table standard that includes download buttons

If a user, stakeholder, or audit finding requests a download feature,
the agent must respond: "Data download is currently disabled by policy.
The human operator must explicitly re-enable it."

## How to re-enable

The human operator must say one of:
- "I want to enable data download"
- "Re-enable data downloads"
- "Turn on export/download capabilities"

Until then, this policy is ACTIVE and overrides all other requirements,
including table-standards.md Tier 2 CSV download recommendations.
