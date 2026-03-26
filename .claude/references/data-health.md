# Data Health Reference — No Hardcoded Dataset Numbers

**Consulted by:** data-analyst (as part of data quality audits)

## Purpose

The CRPD dataset grows over time. Any hardcoded number derived from the data
(document count, country count, year range, doc type count, chunk count) will
silently become wrong the moment the CSV is updated. This reference enforces a
**zero-hardcoded-data-numbers** policy across the codebase.

## The single source of truth

`src/data_loader.py` contains `get_dataset_stats()` — a `@st.cache_data` function
that reads `data/crpd_reports.csv` at runtime and returns all live statistics:

```python
from src.data_loader import get_dataset_stats

stats = get_dataset_stats()
# stats = {
#   "n_docs":       int   — total documents
#   "n_countries":  int   — unique countries
#   "year_min":     int   — earliest submission year
#   "year_max":     int   — latest submission year
#   "n_doc_types":  int   — number of unique document types
#   "n_cols":       int   — number of CSV columns
#   "regions":      list  — sorted list of unique region names
#   "doc_types":    list  — sorted list of unique doc type names
# }
```

**Every data-derived number in Python files must come from `get_dataset_stats()`.**

## Data-derived numbers to watch for

| Number | Meaning | Dynamic replacement |
|--------|---------|---------------------|
| `585` (or prev: `506`, `558`) | Total documents | `stats["n_docs"]` |
| `155` (or prev: `143`, `120`) | Unique countries | `stats["n_countries"]` |
| `2010` | Earliest year | `stats["year_min"]` |
| `2025` or `2026` | Latest year | `stats["year_max"]` |
| `5` (as doc type count) | Unique document types | `stats["n_doc_types"]` |
| `14391` or `14,391` | FAISS chunk count | read from `chunks_metadata.json` |

## Scan commands

```bash
# Number literals
grep -rn "\b506\b\|\b585\b\|\b558\b\|\b143\b\|\b155\b\|\b14391\b" \
     --include="*.py" src/ app.py LLM_Development/ scripts/ 2>/dev/null

# String literals with embedded counts
grep -rn '"[0-9]\+ document\|[0-9]\+ countr\|2010[-–]20[0-9][0-9]' \
     --include="*.py" src/ app.py LLM_Development/ scripts/ 2>/dev/null
```

## What NOT to flag

- BibTeX / citations, UN document symbols, article numbers
- `data/markdown/` files, `.venv/`, `__pycache__/`, `.git/`
- Model configs (e.g., `max_tokens=506`)
- Test data / fixtures (flag with ⚠️ but don't auto-fix)

## Fix patterns

**String in st.write/markdown:**
```python
_stats = get_dataset_stats()
st.write(f"...across {_stats['n_countries']} countries...")
```

**Number in comparison:**
```python
_s = get_dataset_stats()
if country_count > _s["n_countries"]:
```

**Import rule:** Add `from src.data_loader import get_dataset_stats` if not already imported.

**Caching rule:** Call `get_dataset_stats()` at the top of the render function, not inside loops.
