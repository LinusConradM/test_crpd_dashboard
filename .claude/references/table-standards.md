# Table Standards Reference — CRPD Dashboard

**Consulted by:** data-analyst (table structure and content), software-engineer
(implementation), ux-designer (visual design and accessibility)

**Why this exists:** Tables are the most-used component on a dashboard serving
researchers, government officials, DPOs, and policy advocates. Every table on the
CRPD Dashboard may be cited in policy briefs, government reports, academic papers,
or advocacy campaigns. These standards ensure tables are accurate, accessible,
professionally formatted, and consistent across all pages.

---

## Governing Standards

The formatting rules in this document follow established professional frameworks
for tabular design. When a rule is questioned or an edge case arises, these are
the authoritative sources:

| Standard | Scope | Reference |
|---|---|---|
| **IBCS (International Business Communication Standards)** | Notation rules for business and analytical reporting — numeric alignment, unit placement, precision, summary rows | ibcs.com |
| **APA 7th Edition (Table and Figure Guidelines)** | Academic table formatting — header demarcation, three-rule structure, uniform precision, caption conventions | APA Publication Manual, Chapter 7 |
| **Stephen Few — *Show Me the Numbers*** | Practical tabular design — alignment rules, analytical ordering, minimal decoration, meaningful precision | Few (2012), Analytics Press |
| **Edward Tufte — *The Visual Display of Quantitative Information*** | Data-ink ratio principle — remove non-data ink, minimize gridlines, maximize information density | Tufte (2001), Graphics Press |
| **WCAG 2.2 AA** | Accessibility — semantic markup, screen reader support, contrast ratios, keyboard navigation | w3.org/WAI/WCAG22 |
| **UN Editorial Guidelines** | Treaty terminology, country nomenclature, regional group names | UN Editorial Manual |

### Tabular Typography Rules

The discipline of formatting data within tables for readability, accuracy, and
professional credibility is called **tabular typography**. Every rule in this
document maps to a named principle:

| Rule | Industry term | Source | Section |
|---|---|---|---|
| Numbers right-aligned | **Decimal alignment** (tabular figure alignment) | IBCS, APA, Few | §2 |
| Text left-aligned | **Natural reading alignment** | Universal | §2 |
| Column headers centered and bold | **Header demarcation** | APA 7th Ed | §2 |
| Decimals ≤ 2 places | **Precision constraint** (meaningful precision only) | APA, IBCS | §2 |
| Consistent decimals within a column | **Uniform precision** | APA 7th Ed | §2 |
| Comma separators for ≥1,000 | **Digit grouping** | IBCS, ISO 80000 | §2 |
| No interior vertical rules | **Minimal rule structure** / **Three-rule table** | Tufte, APA | §2 |
| Alternating row shading | **Zebra striping** (row banding) | Few | §2 |
| Totals row at bottom | **Summary aggregation row** | IBCS | §1 |
| Units in header, not in cells | **Unit factoring** | IBCS | §2 |
| Sort by meaningful variable | **Analytical ordering** | Few, IBCS | §2 |
| No merged cells | **Atomic cell structure** | WCAG, Few | §2, §4 |
| Caption above table | **Table identification** | APA 7th Ed | §6 |
| Source/notes below table | **Table notes hierarchy** (general, specific, probability) | APA 7th Ed | §6 |
| Missing data as em dash | **Null representation** | APA 7th Ed | §1 |
| Percentage columns sum to 100% | **Exhaustive partition check** | IBCS | §2 |

When agents discuss table formatting, use these terms. "The numbers need
decimal alignment" is precise and auditable; "make the numbers line up" is not.

---

## 1 — Content Standards

### Data Integrity (Data Analyst owns)

- **Dynamic values only.** Every count, percentage, and aggregate must be
  computed from `get_dataset_stats()` or the filtered DataFrame. Never
  hardcode numbers.
- **Always show n=.** Every table that aggregates data must state the sample
  size, either in the table caption or as a column.
- **State the filter context.** If the table shows filtered data, the caption
  must say what's included: "State Reports from the African Group, 2015–2025
  (n=47)" — not just "47 documents."
- **Data timestamp.** Every table must include "Data current through {year}"
  using `get_dataset_stats()['max_year']`.
- **Missing data = em dash (—).** Never use blank cells, "N/A", "null",
  "None", or "0" for missing data. Zero and missing are different things:
  - `0` = measured and the value is zero (e.g., zero mentions of an article)
  - `—` = not measured, not applicable, or data unavailable
- **Totals row.** Include at the bottom of any aggregation table (counts,
  percentages). Label it "Total" or "All States Parties" as appropriate.
- **Reproducibility.** Every number in a table must be traceable to
  `data/crpd_reports.csv` via documented code.

### Treaty Terminology (all agents)

- **"States Parties"** — not "countries" or "nations" when referring to CRPD
  signatories. Use "countries" only in generic geographic context.
- **Country names follow UN nomenclature.** Use the names in the dataset
  (sourced from UN Treaty Collection). Common cases:
  - "Türkiye" not "Turkey"
  - "Côte d'Ivoire" not "Ivory Coast"
  - "Lao People's Democratic Republic" not "Laos"
  - "Republic of Korea" not "South Korea"
  - If the dataset uses a shortened form, match the dataset — don't introduce
    discrepancies between table and source data.
- **UN regional group names.** Use the official names from `un_region` column.
  Don't abbreviate or rename.
- **Document types title-cased.** "State Report," "Concluding Observations,"
  "List of Issues" — not lowercase.
- **CRPD articles by number AND name.** "Article 24 (Education)" not
  "Article 24" or "art_24" or "Education."

### Plain-Language Headers (Data Analyst + UX Designer)

Column headers must be understandable by a policy advocate without data
science training.

| Bad header | Good header |
|---|---|
| `n_docs` | Number of Documents |
| `word_count` | Document Length (words) |
| `art_24_per_1k` | Article 24 Mentions (per 1,000 words) |
| `un_region` | UN Regional Group |
| `doc_type` | Document Type |
| `rights_pct` | Rights-Based Language (%) |
| `review_stage` | Review Cycle Stage |
| `yr` | Year |
| `country` | States Party |

When a column header is too long for the layout, use a shorter label with a
tooltip or footnote explaining the full meaning.

---

## 2 — Tabular Typography (Formatting Standards)

*Based on IBCS notation standards, APA 7th Edition table formatting,
Few's practical rules for tabular design, and Tufte's data-ink ratio.*

### Decimal Alignment

Numeric alignment ensures digit-level comparison across rows. This is one
of the most consistently violated rules in dashboard tables.

| Data type | Alignment | Principle |
|---|---|---|
| Text (country names, labels) | Left | **Natural reading alignment** — text reads left-to-right |
| Integers (counts, years) | Right | **Decimal alignment** — ones/tens/hundreds stack vertically |
| Decimals (percentages, rates) | Right | **Decimal alignment** — decimal points stack vertically |
| Rank or ordinal (#) | Center | **Visual anchor** — short values centered in narrow column |

### Header Demarcation (APA 7th Ed)

- **Column headers: centered and bold.** This visually separates the header
  row from body data and signals that the row is structural, not data.
- **Row headers (first column): left-aligned and bold.** When the first
  column contains entity names (countries, regions), bold them to
  distinguish the identifier from the data columns.
- **Multi-level headers:** If a table has grouped columns (e.g., "State
  Reports" and "Concluding Observations" under a parent "Document Types"
  header), use a spanner header row with a bottom border. Avoid merged cells
  — use visual grouping via borders instead.
- **Header text:** Use sentence case ("Number of documents") not title case
  ("Number Of Documents"), unless the header is a proper noun or treaty term.

### Unit Factoring (IBCS)

- **Units belong in the column header, not repeated in every cell.**
  Write "Length (words)" in the header, then just "12,450" in each cell —
  not "12,450 words" in every row.
- **Percentage signs in the header.** If the column is "Rights-Based
  Language (%)", cells contain "67.3" not "67.3%". This reduces visual noise
  and enables proper decimal alignment.
- **Exception:** When a table mixes units in a single column (rare, and
  usually a sign the table should be restructured), include the unit in
  each cell.

### Precision Constraint (APA, IBCS)

| Data type | Format | Example | Max decimals |
|---|---|---|---|
| Counts | Integer, **digit grouping** (comma for ≥1,000) | 1,247 | 0 |
| Percentages | Fixed decimal, "%" in header or cell | 63.6 | 1 |
| Rates (per 1,000 words) | Fixed decimal | 4.7 | 1 |
| Years | Four digits, no comma | 2024 | 0 |
| Ranges | En dash, no spaces | 2010–2026 | 0 |
| Means | Fixed decimal | 12,345.7 | 1 |
| p-values | Up to 3 significant digits | < 0.001 | 3 |
| Effect sizes (Cohen's d, η²) | Two decimals | 0.42 | 2 |

- **Uniform precision (APA).** If one cell shows 63.6%, all cells in that
  column show one decimal (even 100.0% and 0.0%).
- **No false precision.** Don't report 63.636363% — one decimal is sufficient
  for policy use. Two decimals maximum for any value on this dashboard.
- **Exhaustive partition check (IBCS).** If a column should sum to 100%,
  verify rounding doesn't produce 99.9% or 100.1%. Adjust the largest
  category if needed.

### Analytical Ordering (Few, IBCS)

- **Default sort: most meaningful variable, descending.** For count tables,
  sort by count (highest first). For country tables, sort alphabetically by
  country name (users scan for their country).
- **User-sortable when possible.** Use `st.dataframe()` for interactive
  tables where users benefit from re-sorting.
- **If sorted by rank, include the rank column** as the leftmost column.
- **Tied values:** sort ties alphabetically by country/region name.
- **Categorical ordering:** Document types should follow the review cycle
  sequence (State Report → LOI → Written Reply → Concluding Observations →
  Response), not alphabetical.

### Minimal Rule Structure (Tufte, APA)

- **Three-rule table (APA).** Horizontal rules only at: top of table, below
  header row, and bottom of table. No interior horizontal rules between
  data rows. No vertical rules at all.
- **Zebra striping (Few).** Use subtle alternating row shading as the primary
  visual separator — not gridlines. Stripe color must meet WCAG contrast
  requirements against both the text and the background.
- **Atomic cell structure (WCAG, Few).** No merged cells — they break screen
  readers and make tables harder to parse programmatically. Use repeated
  values or hierarchical indentation instead.
- **Maximum ~20 visible rows without scrolling.** For longer tables, use
  pagination or scrollable containers with sticky headers.
- **Highlight rows judiciously.** Use color to draw attention to at most 1–2
  key rows (e.g., the user's selected country). Use `src/colors.py` palette
  — never hardcode hex values.
- **Data-ink ratio (Tufte).** Every visual element must communicate data. If
  removing a border, shade, or decoration doesn't reduce comprehension,
  remove it.

---

## 3 — Table Types and Templates

### A. Country Comparison Table

Used on: Compare Countries page, Country Profiles page

| States Party | Review Stage | Documents | Most Recent | Top Article |
|---|---|---|---|---|
| Uganda | Reviewed | 12 | 2023 | Article 24 (Education) |
| Kenya | Under Review | 8 | 2021 | Article 27 (Work and Employment) |
| Rwanda | Initial Submission | 3 | 2019 | Article 9 (Accessibility) |

- Sort: alphabetical by country (default), or by any column (interactive)
- Always include: review stage, document count, most recent year
- "Top Article" = highest normalized mentions per 1,000 words

### B. Cross-Tabulation (matrix)

Used on: Regional Comparison, Article Analysis

| UN Regional Group | State Reports | LOIs | Written Replies | Concluding Obs. | Responses | Total |
|---|---|---|---|---|---|---|
| African Group | 42 | 28 | 25 | 31 | 8 | 134 |
| Asia-Pacific | 38 | 22 | 20 | 26 | 5 | 111 |
| ... | | | | | | |
| **Total** | **X** | **X** | **X** | **X** | **X** | **X** |

- Always include totals row and totals column
- Sort: by total (descending) or by region name (alphabetical)
- Abbreviate "Concluding Observations" → "Concluding Obs." with tooltip

### C. Statistical Summary Table

Used on: Article Analysis, Language Trends

| Metric | Value | 95% CI | n |
|---|---|---|---|
| Mean rights-based proportion | 67.3% | [64.1%, 70.5%] | 247 |
| Sen's slope (per year) | +1.2% | [+0.8%, +1.6%] | — |
| Kruskal-Wallis H (regional) | 23.7 | p < 0.001 | 247 |

- Always include confidence intervals for estimated parameters
- Always include sample size
- Report effect sizes alongside test statistics

### D. Document Inventory Table

Used on: Country Profiles

| Document Type | Year | Length (words) | Articles Discussed |
|---|---|---|---|
| State Report | 2016 | 12,450 | 38 of 50 |
| List of Issues | 2017 | 3,210 | 22 of 50 |
| Concluding Observations | 2018 | 8,740 | 45 of 50 |

- Sort: chronological (ascending) by year
- "Articles Discussed" = count of articles with ≥1 keyword match
- Include download link to source document if available

### E. Completeness / Gap Table

Used on: Overview, Regional Comparison

| UN Regional Group | States Parties | Reporting | Under Review | Reviewed | Follow-up | Not Reporting |
|---|---|---|---|---|---|---|
| African Group | 44 | 38 (86.4%) | 6 (13.6%) | 31 (70.5%) | 8 (18.2%) | 6 (13.6%) |

- Show both count and percentage in each cell
- Highlight cells where coverage is below 50% (use warning color from
  `src/colors.py`)
- "Not Reporting" = States Parties with zero documents in dataset

---

## 4 — Accessibility Standards (WCAG 2.2 AA)

These are non-negotiable. The CRPD mandates accessible information
(Articles 9 and 21).

### Structure

- **Proper header markup.** Every column must have a `<th>` element with
  `scope="col"`. Row headers (if used) need `scope="row"`.
- **Caption.** Every table must have a `<caption>` element describing what
  the table shows and the filter context. Screen readers announce this
  before reading the table.
- **Logical reading order.** Columns left-to-right, rows top-to-bottom. No
  visual reordering that breaks the DOM order.
- **No merged cells.** They break assistive technology navigation.
- **No nested tables.** Use CSS for layout instead.

### Visual

- **Minimum font size: 14px** for table body, 12px for captions/footnotes.
- **Color contrast ≥ 4.5:1** for all text against its background (including
  zebra-striped rows).
- **Color is never the sole indicator.** If a cell is highlighted in red to
  show a warning, also include a text label, icon, or pattern.
- **Colorblind-safe palette** from `src/colors.py` for any conditional
  formatting.

### Keyboard and Screen Reader

- **Focusable.** Interactive tables (sortable, scrollable) must be keyboard-
  navigable with Tab and arrow keys.
- **Sort indicators.** If a column is sortable, indicate current sort
  direction with both an arrow icon AND an `aria-sort` attribute.
- **Scrollable containers** must have `role="region"`, `aria-label`, and
  `tabindex="0"` so keyboard users can scroll.

### Alternative Access

**Note:** CSV download is currently disabled by policy. See `no-data-download.md`. Do not implement download buttons on tables until the policy is reversed.

- ~~**CSV download on every table.** Use `st.download_button()` placed
  directly below or beside the table.~~ *Disabled by no-data-download policy.*
- **File name includes context:** `crpd_regional_comparison_2026.csv` not
  `download.csv`. *(applies when download is re-enabled)*
- **CSV must include the same plain-language headers** as the displayed table.
  *(applies when download is re-enabled)*

---

## 5 — Streamlit Implementation (Software Engineer)

### Choosing the Right Component

| Use case | Component | Why |
|---|---|---|
| User needs to sort, filter, search | `st.dataframe()` | Interactive, sortable columns, scrollable |
| Static reference table (small) | `st.table()` | Cleaner rendering, better screen reader support |
| Stakeholder-facing, accessibility-critical | Custom HTML via `st.markdown()` | Full control over `<caption>`, `<th scope>`, ARIA attributes |
| Large dataset (>100 rows) | `st.dataframe()` with pagination | Performance + usability |

### st.dataframe() Configuration

```python
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "States Party": st.column_config.TextColumn(width="medium"),
        "Number of Documents": st.column_config.NumberColumn(format="%d"),
        "Rights-Based Language (%)": st.column_config.NumberColumn(format="%.1f%%"),
        "Year": st.column_config.NumberColumn(format="%d"),
    }
)
```

### Custom HTML Table Template

For stakeholder-facing tables that need full accessibility:

```python
def render_accessible_table(df, caption, table_id):
    """Render a WCAG-compliant HTML table.

    Args:
        df: pandas DataFrame with plain-language column headers
        caption: Description of the table (visible, announced by screen readers)
        table_id: Unique ID for the table element
    """
    html = f'''
    <table id="{table_id}" role="table" class="crpd-table">
        <caption>{caption}</caption>
        <thead>
            <tr>
                {"".join(f'<th scope="col">{col}</th>' for col in df.columns)}
            </tr>
        </thead>
        <tbody>
    '''
    for _, row in df.iterrows():
        html += "<tr>"
        for i, val in enumerate(row):
            if i == 0:
                html += f'<th scope="row">{val}</th>'
            else:
                cell_val = "—" if pd.isna(val) else val
                align = "right" if isinstance(val, (int, float)) else "left"
                html += f'<td style="text-align:{align}">{cell_val}</td>'
        html += "</tr>"

    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)
```

### Table CSS (add to `app.py` style block)

```css
.crpd-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Inter', sans-serif;
    font-size: 14px;
}
.crpd-table caption {
    font-size: 12px;
    color: var(--text-secondary);
    text-align: left;
    padding-bottom: 8px;
    caption-side: top;
}
.crpd-table th {
    text-align: left;
    font-weight: 600;
    padding: 10px 12px;
    border-bottom: 2px solid var(--border-color);
}
.crpd-table td {
    padding: 8px 12px;
    border-bottom: 1px solid var(--border-light);
}
.crpd-table tbody tr:nth-child(even) {
    background-color: var(--row-stripe);
}
.crpd-table tbody tr:hover {
    background-color: var(--row-hover);
}
```

CSS variables (`--border-color`, `--row-stripe`, etc.) should be defined in
the global style block using values from `src/colors.py`.

---

## 6 — Table Captions and Footnotes

### Caption Format

Every table must have a caption. Format:

```
[What the table shows] — [filter context] (n=[sample size]).
Data current through [year].
```

Examples:
- "CRPD document counts by UN regional group and document type — all States
  Parties (n=585). Data current through 2026."
- "Article attention in State Reports — African Group, 2015–2025 (n=47).
  Normalized per 1,000 words. Data current through 2025."
- "Review cycle completion by region — all States Parties (n=155).
  Data current through 2026."

### Footnotes

Place below the table, before the download button. Use for:
- Methodology notes: "Article mentions are based on keyword matching and may
  not capture all references. See Methodology page for details."
- Caveats: "Regions with fewer than 5 States Parties are marked with †."
- Definitions: "'Reviewed' = has received Concluding Observations from the
  CRPD Committee."

---

## 7 — Stakeholder-Specific Considerations

### For DPOs

- Country search/filter must be prominent — DPOs look for their country first
- Tables comparing their country to regional peers are high-value
- Plain language is essential — many DPO users are not data professionals
- Accessibility is both a requirement and a credibility signal

### For Governments

- Tables must be factual and neutral — no characterization of performance
- Peer comparison tables should show rank within region, not global rank
  (less confrontational)
- Download/export is important — officials embed tables in government reports

### For Researchers

- Full data tables with all columns, sortable and downloadable
- Sample sizes and confidence intervals visible
- Methodology footnotes essential for reproducibility
- CSV export must include all underlying data, not just displayed columns

### For Policy Advocates

- Key numbers must be immediately visible without scrolling or filtering
- Tables should have clear, quotable takeaway rows (e.g., totals,
  averages, gaps)
- Share-friendly format — tables that render well when screenshotted or
  copied into presentations

---

## 8 — Enforcement Tiers

Not all tables pass through the full agent pipeline. A quick data pull
answered in conversation doesn't go through UX, Software Engineer, or QA.
To prevent these tables from shipping without any standards, we define
two enforcement tiers:

### Tier 1 — Conversational Tables

Applies when a table is presented directly in chat by any agent (Data
Analyst answering a question, Data Scientist showing results, PM showing
a status tracker).

**Required:**
- Dynamic values only — no hardcoded numbers (§1)
- Sample size (n=) visible (§1)
- Filter context stated (§1)
- Treaty terminology — "States Parties," article names with numbers (§1)
- Missing data as em dash (—) (§1)
- Plain-language headers (§1)
- Decimal alignment — numbers right, text left (§2)
- Uniform precision within columns — ≤2 decimals (§2)
- Analytical ordering — sorted by meaningful variable (§2)
- Header demarcation — bold headers (§2)
- "Data current through {year}" (§1)

**Not required (chat limitations):**
- WCAG HTML markup (`<th scope>`, `<caption>`) — markdown tables don't
  support this
- CSV download button — not available in conversation
- `src/colors.py` palettes — no conditional formatting in markdown
- `render_accessible_table()` — Streamlit-only

**Self-check:** The producing agent must verify Tier 1 compliance before
presenting the table. Use the Tier 1 subset of the Quick Reference
Checklist below.

### Tier 2 — Dashboard Tables

Applies when a table is implemented as a Streamlit component on any
dashboard page.

**Required:** ALL standards from §1 through §7 — content, tabular
typography, table templates, WCAG accessibility, Streamlit implementation,
captions/footnotes, and stakeholder considerations. No exceptions.

**Additional requirements beyond Tier 1:**
- WCAG HTML markup: `<th scope="col">`, `<caption>`, `aria-sort` on
  sortable columns (§4)
- ~~CSV download button with contextual filename (§4)~~ *Disabled by no-data-download policy*
- Component selection per §5 decision matrix
- CSS from §5 `.crpd-table` template
- Colors from `src/colors.py` only
- Screen reader testing
- `python scripts/table_lint.py` must pass with zero violations

**Handoff note:** When a Tier 1 table is promoted to the dashboard, the
Software Engineer must upgrade it to Tier 2 by adding all missing
requirements. Never implement a conversational table as-is in Streamlit.

### How to state the tier

In handoffs between agents, always specify:
- "This is a **Tier 1** table for conversational presentation."
- "This is a **Tier 2** table for the [page name], using template §3[A–E]."

---

## Quick Reference Checklist

Before shipping any table:

- [ ] All numbers computed dynamically (no hardcoded values)
- [ ] Sample size (n=) visible in caption or column
- [ ] Filter context stated in caption
- [ ] "Data current through {year}" present
- [ ] Missing values shown as "—" (em dash)
- [ ] Totals row included (if aggregation table)
- [ ] Column headers are plain language
- [ ] Treaty terminology used ("States Parties," article names)
- [ ] Right-aligned numbers, left-aligned text
- [ ] Consistent decimal precision within each column
- [ ] Sorted by meaningful variable
- [ ] No merged cells
- [ ] Font ≥ 14px, contrast ≥ 4.5:1
- [ ] ~~CSV download button present~~ *Disabled by no-data-download policy*
- [ ] Caption accessible to screen readers
- [ ] Colors from `src/colors.py` only
