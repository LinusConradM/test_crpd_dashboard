"""
CRPD Document Sync  (Data Collection Only)
===========================================
Detects and downloads CRPD documents from the UN Digital Library API,
then updates crpd_reports.csv.

No LLM or vector database components — this script handles
data collection only. LLM integration is a planned future phase.

The UN Digital Library provides a documented JSON API at:
    https://digitallibrary.un.org/search?p=CRPD%2FC&of=recjson&...

Modes:

  SYNC MODE (default) — detect and download newly published documents:
    python scripts/sync_new_documents.py
    python scripts/sync_new_documents.py --dry-run
    python scripts/sync_new_documents.py --skip-extract

  BACKFILL MODE — download all PDFs missing from data/pdfs/ (no CSV changes):
    python scripts/sync_new_documents.py --backfill
    python scripts/sync_new_documents.py --backfill --dry-run
    python scripts/sync_new_documents.py --backfill --resume  (skip existing files)

Requirements:
    pip install requests pandas pdfplumber country-converter

Notes:
    - A 2-second delay is added between requests to be respectful of the
      UN server. Do not reduce this.
    - Backfill runtime estimate: ~20 min for 558 documents (2s delay each).
    - Re-run with --dry-run at any time to preview without downloading.
    - The UN Treaty Body documents are public domain. Review OHCHR terms of
      use at https://www.ohchr.org/en/legal before use.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import time

import pandas as pd
import requests


# ── Optional dependencies (graceful degradation if missing) ────────────────
try:
    import pdfplumber

    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import country_converter as coco

    _cc = coco.CountryConverter()
    HAS_CC = True
except ImportError:
    HAS_CC = False


# ── Configuration ──────────────────────────────────────────────────────────
UN_LIBRARY_API = "https://digitallibrary.un.org/search"
DOWNLOAD_BASE = "https://tbinternet.ohchr.org/_layouts/treatybodyexternal/Download.aspx"
CSV_PATH = Path("data/crpd_reports.csv")
PDF_DIR = Path("data/pdfs")
SYNC_LOG_PATH = Path("scripts/sync_log.json")

DELAY_SECS = 3  # seconds between download requests — be polite to UN server
RATE_LIMIT_BACKOFF = 60  # seconds to wait when server returns 429 Too Many Requests
BATCH_SIZE = 100  # records per API page
TIMEOUT = 60  # seconds per request
MAX_RETRIES = 3

HEADERS = {}  # No custom User-Agent — UN Digital Library blocks non-default agents

# Document type mapping: keyword in UN Library title → internal doc_type value
DOC_TYPE_MAP = {
    "state part": "state report",
    "initial report": "state report",
    "periodic report": "state report",
    "list of issues": "loi",
    "concluding observation": "concluding observations",
    "written repl": "written response",
    "written response": "written response",
    "response to concluding": "response to concluding observations",
    "shadow report": "shadow report",
    "alternative report": "shadow report",
    "parallel report": "shadow report",
}


# ── Region / subregion lookup ───────────────────────────────────────────────
# Manual overrides for entities that country_converter doesn't recognise
_REGION_OVERRIDES = {
    "European Union": "Europe",
    "China (Hong Kong)": "Asia",
    "China (Macau)": "Asia",
    "Philipines": "Asia",  # typo in source data
    "State of Palestine": "Asia",
    "Türkiye": "Asia",
}
_SUBREGION_OVERRIDES = {
    "European Union": "Western Europe",
    "China (Hong Kong)": "Eastern Asia",
    "China (Macau)": "Eastern Asia",
    "Philipines": "South-eastern Asia",
    "State of Palestine": "Western Asia",
    "Türkiye": "Western Asia",
}


def get_region(country: str) -> str:
    """Map a country name to its continent using country_converter."""
    import unicodedata

    if not country or country == "Unknown":
        return "Unknown"
    country = unicodedata.normalize("NFC", country)
    if country in _REGION_OVERRIDES:
        return _REGION_OVERRIDES[country]
    if HAS_CC:
        try:
            result = _cc.convert(country, to="continent")
            if result and result != "not found":
                # Normalise country_converter's "America" → "Americas"
                return "Americas" if result == "America" else result
        except Exception:
            pass
    return "Unknown"


def get_subregion(country: str) -> str:
    """Map a country name to its UN subregion using country_converter."""
    import unicodedata

    if not country or country == "Unknown":
        return ""
    country = unicodedata.normalize("NFC", country)
    if country in _SUBREGION_OVERRIDES:
        return _SUBREGION_OVERRIDES[country]
    if HAS_CC:
        try:
            result = _cc.convert(country, to="UNregion")
            if result and result != "not found":
                return result
        except Exception:
            pass
    return ""


# ── UN Digital Library API ─────────────────────────────────────────────────
def fetch_library_page(query: str, start: int, page_size: int) -> list:
    """Fetch one page of results from the UN Digital Library JSON API."""
    params = {
        "p": query,
        "of": "recjson",
        "sf": "year",
        "so": "d",  # newest first
        "jrec": start,
        "rg": page_size,
    }
    resp = requests.get(UN_LIBRARY_API, params=params, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json() if resp.text.strip() else []


def fetch_all_library_records(since_year: int) -> list:
    """
    Fetch CRPD/C records from the UN Digital Library for each year
    from since_year to the current year.  Querying year-by-year keeps
    each page small (< 100 records) and avoids pulling tens of thousands
    of irrelevant or duplicate-language records.
    """
    current_year = datetime.now().year
    all_records = []

    for year in range(since_year, current_year + 1):
        query = f"CRPD/C year:{year}"
        print(f"  Fetching {year} records (query: '{query}')...")
        start = 1
        year_count = 0
        while True:
            page = fetch_library_page(query, start, BATCH_SIZE)
            if not page:
                break
            all_records.extend(page)
            year_count += len(page)
            if len(page) < BATCH_SIZE:
                break
            start += BATCH_SIZE
            time.sleep(1)
        print(f"    → {year_count} records found for {year}")

    print(f"\n  Total records fetched: {len(all_records)}\n")
    return all_records


def parse_record(record: dict):
    """
    Extract fields from a raw UN Digital Library JSON record.

    The API does not reliably include a 'title' field. Instead, the UN
    document symbol is embedded in the PDF file names inside 'files[]',
    e.g. 'CRPD_C_IRL_1-EN.pdf'.  Country name comes from 'subject' terms.
    Returns None if a valid CRPD/C symbol cannot be found.
    """
    # ── 1. Extract symbol and English download URL from files[] ───────────
    # File names look like: CRPD_C_IRL_1-EN.pdf  (symbol + language suffix)
    # We prefer the English (-EN) version; fall back to any CRPD file.
    SKIP_SUBJECTS = {
        "HUMAN RIGHTS",
        "PERSONS WITH DISABILITIES",
        "LAWS AND REGULATIONS",
        "PERIODIC REPORTS",
        "CONCLUDING OBSERVATIONS",
        "IMPLEMENTATION",
        "EQUAL RECOGNITION BEFORE THE LAW",
        "REGIONAL ORGANIZATIONS",
    }

    symbol_csv = None
    download_url = None
    files = record.get("files", []) or []

    for lang_suffix in ("-EN", ""):  # prefer English, then any
        for f in files:
            if not isinstance(f, dict):
                continue
            name = f.get("full_name", "")
            if not (name.upper().startswith("CRPD") and name.endswith(".pdf")):
                continue
            if lang_suffix and not name.upper().endswith(f"{lang_suffix}.PDF"):
                continue
            # Strip language suffix: CRPD_C_IRL_1-EN.pdf → CRPD_C_IRL_1
            base = re.sub(r"-[A-Z]{1,2}\.pdf$", "", name, flags=re.IGNORECASE)
            symbol_csv = base.upper()
            download_url = f.get("url", "")
            break
        if symbol_csv:
            break

    if not symbol_csv:
        return None

    # ── Validate: only keep country-specific CRPD/C documents ────────────
    # Valid symbols: CRPD_C_[ISO-CODE]_... where ISO-CODE is 2–3 letters.
    # This filters out Summary Records (SR.*), session-level docs (31, 30...),
    # Conference of States Parties (CSP), and procedural documents.
    parts = symbol_csv.split("_")
    if len(parts) < 3:
        return None
    if parts[1].upper() != "C":  # must be CRPD/C/... not CRPD/CSP/...
        return None
    if not re.match(r"^[A-Z]{2,3}$", parts[2]):  # 3rd segment must be ISO country code
        return None

    # Convert underscore symbol back to slash form for display / fallback URL
    symbol_raw = symbol_csv.replace("_", "/")

    # ── 2. Extract year from imprint date ─────────────────────────────────
    year = None
    imprint = record.get("imprint", {})
    if isinstance(imprint, dict):
        year_m = re.search(r"\b(20\d{2})\b", str(imprint.get("date", "")))
        if year_m:
            year = int(year_m.group(1))

    # ── 3. Determine doc type from symbol pattern ─────────────────────────
    # Examples: CRPD_C_IRL_1 → state report
    #           CRPD_C_IRL_CO_1 → concluding observations
    #           CRPD_C_IRL_Q_1  → loi
    #           CRPD_C_IRL_Q_1_Add_1 → written response
    #           CRPD_C_IRL_FCO_1 → response to concluding observations
    sym_up = symbol_csv.upper()
    if "_Q_" in sym_up and "_ADD" in sym_up:
        doc_type = "written response"
    elif "_Q_" in sym_up:
        doc_type = "loi"
    elif "_CO_" in sym_up or sym_up.endswith("_CO"):
        doc_type = "concluding observations"
    elif "_FCO_" in sym_up:
        doc_type = "response to concluding observations"
    else:
        doc_type = "state report"  # default for country-level CRPD/C docs

    # ── 4. Extract country from ISO code, corporate_name, or subject terms ──
    # Manual overrides checked first — some ISO codes (e.g. EU) are not
    # standard countries and will be misidentified by country_converter.
    MANUAL_COUNTRY = {"EU": "European Union"}

    country = "Unknown"

    # Priority 1: manual override by ISO code (e.g. EU → European Union)
    if parts[2] in MANUAL_COUNTRY:
        country = MANUAL_COUNTRY[parts[2]]

    # Priority 2: corporate_name field (present on some records)
    if country == "Unknown":
        corp = record.get("corporate_name", "")
        if isinstance(corp, list) and corp:
            corp = corp[0]
        if isinstance(corp, dict):
            corp = corp.get("name", "") or corp.get("corporate_name", "")
        if isinstance(corp, str) and corp.strip():
            country = corp.strip().title()

    # Priority 3: subject terms contain the country name in ALL CAPS
    if country == "Unknown":
        for s in record.get("subject", []) or []:
            if not isinstance(s, dict):
                continue
            term = s.get("term", "").strip()
            if term and term.upper() not in SKIP_SUBJECTS:
                country = term.title()  # "IRELAND" → "Ireland"
                break

    # Priority 4: derive from ISO-3 code via country_converter
    if country == "Unknown" and HAS_CC:
        converted = _cc.convert(parts[2], to="name_short")
        if converted and converted != "not found":
            country = converted

    # ── 5. Build file name and ensure download URL ─────────────────────────
    country_clean = re.sub(r"[^\w\s-]", "", country).strip().replace(" ", "_")
    file_name = f"{country_clean}_{year}_{symbol_csv}.pdf" if year else f"{symbol_csv}.pdf"

    if not download_url:
        encoded = symbol_raw.replace("/", "%2F")
        download_url = f"{DOWNLOAD_BASE}?symbolno={encoded}&Lang=en"

    return {
        "symbol_csv": symbol_csv,
        "symbol_raw": symbol_raw,
        "country": country,
        "year": year,
        "doc_type": doc_type,
        "language": "en",
        "file_name": file_name,
        "download_url": download_url,
        "region": get_region(country),
        "subregion": get_subregion(country),
    }


# ── Download ───────────────────────────────────────────────────────────────
def download_pdf(url: str, dest: Path, retries: int = MAX_RETRIES) -> bool:
    """Download a PDF from the given URL. Returns True on success."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
            if resp.status_code == 404:
                print("    [404] Document not found at UN server — skipping.")
                return False
            resp.raise_for_status()

            # Verify it's actually a PDF (not an HTML error page)
            content_type = resp.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and "octet" not in content_type.lower():
                print(f"    [WARN] Unexpected content type: {content_type} — skipping.")
                return False

            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            return dest.stat().st_size > 1000

        except Exception as e:
            print(f"    [Attempt {attempt}/{retries}] Error: {e}")
            if attempt < retries:
                time.sleep(DELAY_SECS * attempt)

    print(f"    [FAILED] Giving up after {retries} attempts.")
    return False


# ── Text extraction ─────────────────────────────────────────────────────────
def extract_text(pdf_path: Path):
    """
    Extract text from a PDF using pdfplumber.
    Returns (clean_text, word_count, snippet).
    """
    if not HAS_PDFPLUMBER:
        return "", 0, ""
    try:
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        full_text = "\n".join(text_parts).strip()
        words = full_text.split()
        snippet = " ".join(words[:120])
        return full_text, len(words), snippet
    except Exception as e:
        print(f"    [WARN] Text extraction failed: {e}")
        return "", 0, ""


# ── Sync log ───────────────────────────────────────────────────────────────
def load_sync_log() -> dict:
    if SYNC_LOG_PATH.exists():
        with open(SYNC_LOG_PATH) as f:
            return json.load(f)
    return {"runs": [], "total_downloaded": 0}


def save_sync_log(log: dict):
    SYNC_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SYNC_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


# ── Main sync routine ──────────────────────────────────────────────────────
def sync(dry_run: bool = False, skip_extract: bool = False):
    print("=" * 65)
    print("CRPD New Document Sync  (Data Collection Only)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65 + "\n")

    if not HAS_PDFPLUMBER and not skip_extract:
        print("[WARN] pdfplumber not installed — text extraction will be skipped.")
        print("       Install with: pip install pdfplumber\n")

    if not HAS_CC:
        print("[WARN] country_converter not installed — regions will show as 'Unknown'.")
        print("       Install with: pip install country-converter\n")

    # 1. Load existing CSV
    df_existing = pd.read_csv(CSV_PATH)
    known_symbols = set(df_existing["symbol"].astype(str).str.strip())
    print(f"Known documents in CSV : {len(known_symbols)}")
    print(f"PDF output directory   : {PDF_DIR.resolve()}\n")

    # Determine fetch window: start one year before the latest year in the CSV
    # (catches any documents published late in the previous year that were missed)
    max_csv_year = int(df_existing["year"].dropna().max())
    since_year = max_csv_year - 1
    print(f"Fetching documents from {since_year} onward (CSV max year: {max_csv_year})...\n")

    # 2. Fetch records from UN Digital Library (year-by-year, targeted)
    records_raw = fetch_all_library_records(since_year)

    # 3. Parse and identify new records
    new_records = []
    filtered_out = 0

    for raw in records_raw:
        parsed = parse_record(raw)
        if parsed is None:
            filtered_out += 1
            continue
        if parsed["symbol_csv"] not in known_symbols:
            new_records.append(parsed)

    print(f"New documents detected : {len(new_records)}")
    print(f"Already in CSV         : {len(records_raw) - len(new_records) - filtered_out}")
    print(f"Filtered (non-country) : {filtered_out}\n")

    if not new_records:
        print("✓ No new documents found. CSV is up to date.")
        _log_run(added=0, dry_run=dry_run)
        return

    # 4. Show what was found
    print("New documents:")
    for r in new_records:
        print(f"  {r['symbol_csv']:<38}  {r['country']!s:<28}  {r['year']}  {r['doc_type']}")
    print()

    if dry_run:
        print("[DRY RUN] No files downloaded or CSV updated.")
        _log_run(added=0, dry_run=True)
        return

    # 5. Download PDFs and optionally extract text
    successfully_added = []

    for i, rec in enumerate(new_records, 1):
        print(f"[{i}/{len(new_records)}] {rec['symbol_csv']} — {rec['country']} {rec['year']}")

        pdf_path = PDF_DIR / rec["file_name"]

        # Download PDF
        print(f"    Downloading: {rec['download_url'][:75]}...")
        ok = download_pdf(rec["download_url"], pdf_path)

        if not ok:
            print("    [FAILED] Could not download PDF — skipping.")
            continue

        size_kb = pdf_path.stat().st_size / 1024
        print(f"    [OK] PDF saved ({size_kb:.0f} KB)")

        # Extract text
        clean_text, word_count, snippet = "", 0, ""
        if not skip_extract:
            clean_text, word_count, snippet = extract_text(pdf_path)
            if word_count:
                print(f"    [OK] Text extracted ({word_count:,} words)")

        rec["word_count"] = word_count
        rec["clean_text"] = clean_text
        rec["text_snippet"] = snippet
        successfully_added.append(rec)

        time.sleep(DELAY_SECS)

    # 6. Append new rows to CSV
    if successfully_added:
        csv_cols = [
            "doc_type",
            "country",
            "year",
            "region",
            "subregion",
            "word_count",
            "language",
            "symbol",
            "file_name",
            "clean_text",
            "text_snippet",
        ]
        new_rows = []
        for r in successfully_added:
            new_rows.append(
                {
                    "doc_type": r["doc_type"],
                    "country": r["country"],
                    "year": r["year"],
                    "region": r["region"],
                    "subregion": r["subregion"],
                    "word_count": r["word_count"],
                    "language": r["language"],
                    "symbol": r["symbol_csv"],
                    "file_name": r["file_name"],
                    "clean_text": r["clean_text"],
                    "text_snippet": r["text_snippet"],
                }
            )

        df_new = pd.DataFrame(new_rows, columns=csv_cols)
        df_updated = pd.concat([df_existing, df_new], ignore_index=True)
        df_updated.to_csv(CSV_PATH, index=False)

        print(f"\n✓ CSV updated: {len(df_existing)} → {len(df_updated)} rows")
        print(f"  Added {len(successfully_added)} new document(s) to {CSV_PATH}")
    else:
        print("\nNo documents were successfully downloaded.")

    _log_run(added=len(successfully_added), dry_run=dry_run)

    print("\n" + "=" * 65)
    print(f"Sync complete. {len(successfully_added)} document(s) added.")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)


def _log_run(added: int, dry_run: bool):
    log = load_sync_log()
    log["runs"].append(
        {
            "timestamp": datetime.now().isoformat(),
            "documents_added": added,
            "dry_run": dry_run,
        }
    )
    log["total_downloaded"] = log.get("total_downloaded", 0) + added
    save_sync_log(log)


# ── Backfill — download all missing PDFs from the existing CSV ─────────────
def backfill(dry_run: bool = False, resume: bool = False):
    """
    Download PDFs for all 585 rows in crpd_reports.csv that are missing
    from data/pdfs/.  Uses the UN Digital Library API to get authoritative
    download URLs — the same source that successfully downloaded the first
    27 PDFs.  Does NOT modify crpd_reports.csv.
    """
    print("=" * 65)
    print("CRPD PDF Backfill  (UN Digital Library API)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65 + "\n")

    # 1. Load CSV — get the full symbol→file_name mapping
    df = pd.read_csv(CSV_PATH)
    df = df.dropna(subset=["symbol"])
    df = df.drop_duplicates(subset=["file_name"])
    total_csv = len(df)

    existing_files = {p.name for p in PDF_DIR.glob("*.pdf")}
    missing = df[~df["file_name"].isin(existing_files)]

    print(f"Documents in CSV   : {total_csv}")
    print(f"Already on disk    : {total_csv - len(missing)}")
    print(f"Missing PDFs       : {len(missing)}")
    print(f"Output directory   : {PDF_DIR.resolve()}\n")

    if missing.empty:
        print("✓ All PDFs already downloaded.")
        return

    if dry_run:
        print("[DRY RUN] Documents that would be downloaded:")
        for row in missing.itertuples():
            print(f"  {row.symbol:<40}  {row.country}  {row.year}")
        print(f"\n[DRY RUN] Would attempt {len(missing)} downloads. No files written.")
        return

    # 2. Fetch download URLs from the UN Digital Library API (2010 → now)
    print("Fetching download URLs from UN Digital Library API (2010 → now)...")
    print("This may take 1–2 minutes...\n")
    records_raw = fetch_all_library_records(since_year=2010)

    # Build symbol → download_url map from API results
    url_map: dict[str, str] = {}
    for raw in records_raw:
        parsed = parse_record(raw)
        if parsed and parsed.get("download_url"):
            url_map[parsed["symbol_csv"]] = parsed["download_url"]

    print(f"\nAPI returned URLs for {len(url_map)} symbols.\n")
    print("=" * 65)

    # 3. Download each missing PDF
    downloaded = 0
    skipped = 0
    failed = 0

    missing_list = list(missing.itertuples())
    for i, row in enumerate(missing_list, 1):
        dest = PDF_DIR / row.file_name
        label = f"[{i:>4}/{len(missing_list)}] {row.country} {row.year} — {row.file_name}"

        if resume and dest.exists():
            print(f"  ⏭  {label}")
            skipped += 1
            continue

        url = url_map.get(str(row.symbol).upper())
        if not url:
            print(f"  ⚠  {label}")
            print(f"       No URL found in API for symbol: {row.symbol}")
            failed += 1
            continue

        print(f"  ⬇  {label}")
        ok = download_pdf(url, dest)
        if ok:
            size_kb = dest.stat().st_size / 1024
            print(f"       ✓ Saved ({size_kb:.0f} KB)")
            downloaded += 1
        else:
            failed += 1

        time.sleep(DELAY_SECS)

    print("\n" + "=" * 65)
    print("Backfill complete.")
    print(f"  Downloaded : {downloaded}")
    print(f"  Skipped    : {skipped}")
    print(f"  Failed     : {failed}")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)


# ── CLI ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sync new CRPD documents from the UN Digital Library.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/sync_new_documents.py              # sync new docs\n"
            "  python scripts/sync_new_documents.py --dry-run    # preview sync\n"
            "  python scripts/sync_new_documents.py --backfill   # download all missing PDFs\n"
            "  python scripts/sync_new_documents.py --backfill --resume  # resume interrupted backfill\n"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without downloading or updating anything.",
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Download PDFs but skip text extraction (sync mode only).",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Download all PDFs missing from data/pdfs/ (no CSV changes).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip already-downloaded files (backfill mode only).",
    )
    args = parser.parse_args()

    if args.backfill:
        backfill(dry_run=args.dry_run, resume=args.resume)
    else:
        sync(dry_run=args.dry_run, skip_extract=args.skip_extract)


# ── Scheduling options ─────────────────────────────────────────────────────
"""
OPTION A: GitHub Actions (recommended for a shared research project)
--------------------------------------------------------------------
Create .github/workflows/sync_crpd.yml:

    name: Sync CRPD Documents
    on:
      schedule:
        - cron: '0 6 1 * *'   # 6 AM UTC on the 1st of every month
      workflow_dispatch:       # allow manual trigger from GitHub UI
    jobs:
      sync:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - uses: actions/setup-python@v5
            with: { python-version: '3.11' }
          - run: pip install requests pandas pdfplumber country-converter
          - run: python scripts/sync_new_documents.py
          - uses: actions/upload-artifact@v4
            with:
              name: updated-data
              path: |
                data/crpd_reports.csv
                scripts/sync_log.json

OPTION B: Linux/macOS cron
--------------------------
    0 7 1 * * cd /path/to/crpd-dashboard && python scripts/sync_new_documents.py >> logs/sync.log 2>&1

OPTION C: Manual on-demand
--------------------------
    python scripts/sync_new_documents.py --dry-run   # safe preview
    python scripts/sync_new_documents.py             # full run
"""
