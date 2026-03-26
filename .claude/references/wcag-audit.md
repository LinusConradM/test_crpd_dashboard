# WCAG 2.2 AA Audit Reference

**Consulted by:** qa-tester (runs the audit), software-engineer (implements fixes)

## Running the audit

```bash
# 1. Verify Streamlit is running
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/healthz

# 2. Run the audit script (patch port if needed)
cd "<project-root>"
sed 's/localhost:8502/localhost:8501/g' scripts/wcag_audit.py \
  | /opt/anaconda3/bin/python 2>&1
```

## Report format

```
### WCAG 2.2 AA Audit Results

**Total violations: N**

| # | Rule | Severity | WCAG Criterion | Elements affected |
|---|------|----------|---------------|-------------------|
| 1 | `rule-id` | 🔴 Critical / 🟠 Serious / 🟡 Moderate / 🔵 Minor | x.x.x | N element(s) |
```

For each violation:
```
[SEVERITY] rule-id
Rule: <human-readable rule description>
WCAG: <criterion number and name>
Affected elements:
  1. Selector: <CSS selector>
     Snippet: <truncated HTML>
     Issue: <specific message from axe>
```

## Known violations in this project

| Rule | Typical cause | Fix approach |
|------|-------------------------------|--------------|
| `color-contrast` | Nav link text too light on blue background | Lighten text color in `src/nav.py` `.nav-link` |
| `aria-allowed-attr` | Streamlit BaseWeb dropdown `div` with invalid `aria-expanded` | Cannot fix — Streamlit internal |
| `target-size` | Multiselect hidden `<input>` too small (2px) | CSS override in `src/styles.py`: `min-width: 24px; min-height: 24px` |
| `label` | Form input missing associated label | Add `aria-label` or `<label for=...>` |
| `button-name` | Button with no accessible name | Add `aria-label` to button element |
| `link-name` | Anchor with no text | Add `aria-label` or visible text |
| `image-alt` | `<img>` missing `alt` attribute | Add descriptive `alt` text |

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

## Usability Beyond Compliance

WCAG technical compliance is necessary but not sufficient. The Stakeholder
Advocate reviews whether WCAG-compliant elements are practically usable by the
four target user groups. This section bridges the gap between passing an
automated audit and serving real users.

**What this covers:** After the QA Tester confirms WCAG 2.2 AA technical
compliance (automated audit + manual checklist), the Stakeholder Advocate
applies a usability lens from each user group's perspective:

| User group | WCAG-compliant but unusable example | What Stakeholder Advocate catches |
|---|---|---|
| **DPOs** | A chart has alt-text, but the alt-text says "bar chart" instead of describing the finding | Alt-text must convey the insight, not just the chart type |
| **Governments** | A comparison table is keyboard-navigable, but the data ordering makes peer comparison impossible | Analytical ordering matters for the task, not just keyboard access |
| **Researchers** | A data table has proper `<th scope>` headers, but no CSV download to enable independent analysis | Technical accessibility without functional access is insufficient |
| **Policy advocates** | A metric card meets contrast requirements, but the number lacks context for quotation | Accessible display without quotable framing fails the advocacy use case |

**When this review happens:** After QA Tester passes WCAG technical audit,
before PM presents to human. The Stakeholder Advocate does not re-run the
technical audit — they trust QA's results and focus on whether compliance
translates to real usability for each user community.

**Key principle:** An element can pass every WCAG criterion and still fail its
users. The Stakeholder Advocate's job is to catch that gap.

## After fixing

1. Re-run the audit
2. Confirm the fixed violation no longer appears
3. Report the before/after violation count
