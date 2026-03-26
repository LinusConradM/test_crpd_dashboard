# Table Standards Enforcement — Changelog

**Status: APPLIED** (2026-03-20). All additions below have been applied to their
target files. This file is retained as an audit trail documenting what was added
and why. Do not re-apply — the changes are already in place.

Original purpose: drop-in additions to 6 skills + 1 reference file to enforce
`.claude/references/table-standards.md` across the agent system.

---

## 1. data-analyst skill

**Where:** After the Permission Gate section, before the Dataset Reference
section. Add as a new subsection.

**Add:**

```markdown
## Table Standards (mandatory)

When producing any table, cross-tabulation, completeness matrix, country
profile, document inventory, or descriptive summary — whether for direct
stakeholder consumption or as a handoff to another agent — follow the rules
in `.claude/references/table-standards.md`. Key requirements:

- **Content:** Dynamic values only, n= visible, filter context in caption,
  missing data as em dash (—), totals row on aggregation tables
- **Terminology:** "States Parties," article names ("Article 24 (Education)"),
  UN country nomenclature, doc types title-cased
- **Formatting:** Decimal alignment (numbers right, text left), header
  demarcation (centered, bold), uniform precision (≤2 decimals), unit
  factoring (units in headers not cells), analytical ordering
- **Templates:** Use the appropriate table template from §3 (Country
  Comparison, Cross-Tabulation, Document Inventory, Completeness/Gap)
- **Accessibility:** em dash for missing data, no merged cells, plain-language
  headers, CSV download alongside every table

Consult the full reference before producing any table. When handing off a
table to the Software Engineer for implementation, note which template from
§3 applies.
```

---

## 2. data-scientist skill

**Where:** Inside the "Analysis Standards" section (Section 5 in the v2
skill), add as a new numbered item at the end of the standards list.

**Add:**

```markdown
11. **Table standards** — When producing statistical summary tables (means,
    CIs, test results, effect sizes) or specifying data tables in chart
    specifications, follow `.claude/references/table-standards.md`.
    Key rules: p-values to 3 significant digits, effect sizes to 2 decimals,
    confidence intervals in brackets, sample size column required, header
    demarcation (centered, bold), unit factoring (units in header not cells).
    Use the Statistical Summary Table template from §3C for all inferential
    results.
```

---

## 3. software-engineer skill

**Where:** Inside the "Component Library" section, after the existing
component descriptions (filters, charts, cards, tables). Add as a new
subsection.

**Add:**

```markdown
### Table Implementation Standards

All table components must follow `.claude/references/table-standards.md`.
Before implementing any table, read the full reference. Key requirements:

- **Component selection:** Use the decision matrix in §5 — `st.dataframe()`
  for interactive/sortable, `st.table()` for small static, custom HTML via
  `render_accessible_table()` for stakeholder-facing accessibility-critical
  tables
- **Formatting:** Apply `column_config` for number formatting (see §5
  `st.dataframe()` configuration example). Decimal alignment, digit grouping,
  uniform precision.
- **Accessibility (§4):** `<th scope="col">`, `<caption>`, no merged cells,
  contrast ≥ 4.5:1 on zebra stripes, `aria-sort` on sortable columns
- **CSS:** Use the `.crpd-table` CSS template from §5 — add to the `app.py`
  style block if not already present
- **CSV download:** Every table must have a `st.download_button()` with a
  contextual filename: `crpd_{table_name}_{max_year}.csv`
- **Headers:** Plain-language, centered, bold. Use the header mapping from §1
  (e.g., `n_docs` → "Number of Documents")

If a table specification from the Data Scientist or Data Analyst references
a template from §3, implement that template exactly.
```

---

## 4. ux-designer skill

**Where:** In the section that covers visual specifications, typography, or
design system rules. Add as a new subsection.

**Add:**

```markdown
### Table Design Standards

When specifying the visual design for any table — typography, alignment,
spacing, header styling, row treatment, conditional formatting — follow
the tabular typography rules in `.claude/references/table-standards.md` §2.
These are based on IBCS, APA 7th Edition, and Few's practical rules.

Key rules for design specs:
- **Header demarcation (APA):** Column headers centered and bold, row headers
  left-aligned and bold, sentence case
- **Decimal alignment:** Numbers right-aligned, text left-aligned
- **Minimal rule structure (Tufte/APA):** Three-rule table — horizontal rules
  at top, below header, and bottom only. Zebra striping for row separation.
  No vertical rules. No interior horizontal rules between data rows.
- **Unit factoring (IBCS):** Units in column headers, not repeated in cells
- **Colors:** All conditional formatting, highlights, and zebra stripe colors
  must use `src/colors.py` palettes. Stripe color must meet WCAG contrast
  against both text and background.
- **Data-ink ratio (Tufte):** If removing a border, shade, or decoration
  doesn't reduce comprehension, remove it

When producing a table design spec, reference the applicable table template
from `.claude/references/table-standards.md` §3.
```

---

## 5. qa-tester skill

**Where:** In the section that covers testing checklists, WCAG audit
procedures, or verification standards. Add as a new subsection.

**Add:**

```markdown
### Table Audit Checklist

When auditing any page that contains a data table, verify every item in the
Quick Reference Checklist at the bottom of `.claude/references/table-standards.md`.
Every checkbox must pass.

Summary of table-specific checks:
- [ ] All numbers computed dynamically (no hardcoded values)
- [ ] Sample size (n=) visible in caption or column
- [ ] Filter context stated in caption
- [ ] "Data current through {year}" present
- [ ] Missing values shown as "—" (em dash), not blank/N/A/null
- [ ] Totals row included (if aggregation table)
- [ ] Column headers are plain language, centered, bold
- [ ] Treaty terminology used ("States Parties," article names with numbers)
- [ ] Right-aligned numbers, left-aligned text (decimal alignment)
- [ ] Consistent decimal precision within each column (≤2 places)
- [ ] Sorted by meaningful variable (analytical ordering)
- [ ] No merged cells (atomic cell structure)
- [ ] Font ≥ 14px, contrast ≥ 4.5:1 (including zebra stripe rows)
- [ ] CSV download button present with contextual filename
- [ ] Caption accessible to screen readers (`<caption>` or equivalent)
- [ ] Colors from `src/colors.py` only
- [ ] No vertical gridlines, no heavy interior borders (minimal rule structure)
- [ ] Unit factoring applied (units in headers, not cells)

Report violations using the industry terminology (e.g., "decimal alignment
violation on column 3," "uniform precision failure — mixed 1 and 2 decimal
places in Rights-Based Language column").
```

---

## 6. pm-orchestrator skill

**Where:** Inside Part 4 (Quality Gates), in the **"Any Agent →
Stakeholder-Facing Output"** gate checklist. Add as a new checkbox item.

**Add this line to the existing checklist:**

```markdown
- [ ] Tables follow `.claude/references/table-standards.md` (tabular typography, precision, treaty terminology, accessibility, CSV download)
```

**Also add to the Post-Implementation Review (Part 5)** under the
"Accessibility (WCAG 2.2)" checklist:

```markdown
- [ ] Tables: `<caption>` present, `<th scope>` on all headers, no merged cells, decimal alignment, CSV download
```

**And add to the "Code Quality" checklist in Part 5:**

```markdown
- [ ] Tables use plain-language headers (not column names from DataFrame)
- [ ] Table numbers are dynamically computed (not hardcoded)
- [ ] Missing values displayed as em dash (—), not blank or N/A
```

---

## 7. wcag-audit.md reference file

**Where:** Add as a new section in the reference file, or append to the
existing audit checklist.

**Add:**

```markdown
## Table Accessibility (WCAG 2.2 AA)

Reference: `.claude/references/table-standards.md` §4

### Structure
- [ ] Every column has `<th>` with `scope="col"`
- [ ] Row headers (if used) have `scope="row"`
- [ ] `<caption>` element present describing the table and filter context
- [ ] Logical reading order — columns left-to-right, rows top-to-bottom
- [ ] No merged cells (`colspan`, `rowspan`) — they break assistive navigation
- [ ] No nested tables

### Visual
- [ ] Font size ≥ 14px in table body, ≥ 12px in captions/footnotes
- [ ] Color contrast ≥ 4.5:1 for all text against background
- [ ] Zebra stripe color meets contrast against both text and unstriped background
- [ ] Color is never the sole indicator — text labels or icons accompany any
  color-coded cells
- [ ] Conditional formatting uses `src/colors.py` colorblind-safe palette

### Keyboard and Screen Reader
- [ ] Interactive tables (sortable, scrollable) are keyboard-navigable
  (Tab + arrow keys)
- [ ] Sortable columns have `aria-sort` attribute indicating direction
- [ ] Scrollable containers have `role="region"`, `aria-label`, and
  `tabindex="0"`

### Alternative Access
- [ ] CSV download button present next to or below the table
- [ ] CSV filename is contextual: `crpd_{table_name}_{year}.csv`
- [ ] CSV headers match the plain-language headers shown in the table
```

---

## Verification

After applying all additions, confirm the enforcement chain is complete:

```
table-standards.md (reference)
    ↓ read by
data-analyst          → produces tables following content + formatting rules
data-scientist        → produces statistical tables following precision rules
    ↓ handed off to
ux-designer           → specifies table design following tabular typography
    ↓ handed off to
software-engineer     → implements tables following Streamlit + accessibility rules
    ↓ handed off to
qa-tester             → audits tables against the full checklist
    ↓ reviewed by
stakeholder-advocate  → stress-tests tables from DPO, government, researcher, advocate perspectives
    ↓ verified by
pm-orchestrator       → enforces table compliance at every quality gate
    ↓ approved by
human                 → final approval (Stakeholder Advocate verdicts are recommendations only)

wcag-audit.md         → provides table-specific WCAG checks for qa-tester
```

Every table produced on the CRPD Dashboard passes through at least 3 agents
who reference table-standards.md, plus a QA audit, Stakeholder Advocate review,
and PM gate verification.
