"""Build the CRPD knowledge base for Phase 3 RAG + Semantic Search.

One-time script: converts PDFs → Markdown → chunks → embeddings → FAISS index.
Runtime: ~15–20 minutes on CPU for 585 documents.

Usage:
    python LLM_Development/build_knowledge_base.py
    python LLM_Development/build_knowledge_base.py --pdf-dir data/pdfs --resume

Outputs (written to data/):
    faiss_index.bin       — FAISS IndexFlatIP (typically tens of MB; size depends on corpus)
    embeddings.npy        — All chunk vectors (size depends on number of chunks and embedding dim)
    chunks_metadata.json  — Chunk text + metadata (country, year, doc_type, …; scales with corpus)
    markdown/             — Intermediate Markdown files (one per PDF; size depends on source PDFs)
"""

import argparse
import json
import os
from pathlib import Path
import re
import sys


# Prevent tokenizer parallelism warnings/segfaults (safe default everywhere)
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Limit MKL/OpenMP threads only on macOS or when explicitly requested.
# On non-macOS platforms, multi-threading is allowed by default to avoid
# unnecessary slowdowns during embedding/index builds.
_limit_threads_flag = os.getenv("CRPD_LIMIT_THREADS", "").lower()
if sys.platform == "darwin" or _limit_threads_flag in {"1", "true", "yes"}:
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np


# ── Configuration ─────────────────────────────────────────────────────────────

PDF_DIR = Path("data/pdfs")
MARKDOWN_DIR = Path("data/markdown")
OUTPUT_DIR = Path("data")

EMBEDDING_MODEL_NAME = "all-mpnet-base-v2"
CHUNK_SIZE = 500  # target words per chunk
CHUNK_OVERLAP = 75  # overlapping words at chunk boundaries
BATCH_SIZE = 32  # embedding batch size (reduce if OOM or segfault on macOS)


# ── Helpers ───────────────────────────────────────────────────────────────────


def pdf_to_markdown(pdf_path: Path, out_dir: Path) -> Path | None:
    """Convert a single PDF to Markdown using pymupdf4llm.

    Args:
        pdf_path: Path to the source PDF.
        out_dir: Directory to write the .md file.

    Returns:
        Path to the written .md file, or None on failure.
    """
    try:
        import pymupdf4llm

        md_text = pymupdf4llm.to_markdown(str(pdf_path))
        out_path = out_dir / (pdf_path.stem + ".md")
        out_path.write_text(md_text, encoding="utf-8")
        return out_path
    except Exception as exc:
        print(f"  ✗ PDF conversion failed for {pdf_path.name}: {exc}", file=sys.stderr)
        return None


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences using regex for common sentence boundaries.

    Handles abbreviations (Mr., Dr., Art., No.) and decimal numbers to
    avoid false splits. Falls back to newline splitting if no periods found.
    """
    import re

    # Split on period/question/exclamation followed by space and uppercase,
    # but not after common abbreviations
    _abbrev = r"(?<!\bMr)(?<!\bMrs)(?<!\bDr)(?<!\bArt)(?<!\bNo)(?<!\bVol)"
    _pattern = rf"{_abbrev}(?<=[.!?])\s+(?=[A-Z])"
    sentences = re.split(_pattern, text)
    # Also split on double newlines (paragraph boundaries)
    result = []
    for s in sentences:
        parts = s.split("\n\n")
        result.extend(p.strip() for p in parts if p.strip())
    return result


def _split_into_word_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping sentence-boundary-aware chunks.

    Attempts to split at sentence boundaries rather than mid-sentence.
    Falls back to word-based splitting if sentences are very long.
    Discards chunks shorter than 50 words (degenerate: TOC, headers, etc.).

    Args:
        text: Full document text.
        chunk_size: Maximum words per chunk.
        overlap: Words shared between consecutive chunks (approximate).

    Returns:
        List of chunk strings.
    """
    sentences = _split_into_sentences(text)
    if not sentences:
        return []

    chunks = []
    current_words: list[str] = []
    overlap_buffer: list[str] = []

    for sent in sentences:
        sent_words = sent.split()
        if not sent_words:
            continue

        # If adding this sentence would exceed chunk_size, flush current chunk
        if current_words and len(current_words) + len(sent_words) > chunk_size:
            chunk_text = " ".join(current_words)
            if len(current_words) >= 50:  # Min chunk quality threshold
                chunks.append(chunk_text)
            # Keep last ~overlap words for context continuity
            overlap_buffer = current_words[-overlap:] if overlap else []
            current_words = list(overlap_buffer) + sent_words
        else:
            current_words.extend(sent_words)

    # Flush final chunk
    if current_words and len(current_words) >= 50:
        chunks.append(" ".join(current_words))

    # Fallback: if sentence splitting produced nothing, use raw word windows
    if not chunks:
        words = text.split()
        if not words:
            return []
        start = 0
        step = max(chunk_size - overlap, 1)
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_text = " ".join(words[start:end])
            if len(words[start:end]) >= 50:
                chunks.append(chunk_text)
            if end == len(words):
                break
            start += step

    return chunks


def _parse_doc_id(filename: str) -> dict:
    """Extract metadata from a standardised PDF filename.

    Expected format: Country_Year_CRPD_C_XXX_N[_extra].pdf
    Falls back to empty strings when parsing fails.

    Args:
        filename: PDF stem (no extension).

    Returns:
        dict with keys: country, year, doc_type, symbol.
    """
    # Derive country from all tokens before the year token
    parts = filename.split("_")
    country = "Unknown"
    year = None
    if parts:
        year_token_index = None
        for idx, part in enumerate(parts):
            if re.fullmatch(r"(?:19|20)\d{2}", part):
                year_token_index = idx
                year = int(part)
                break
        if year_token_index is not None and year_token_index > 0:
            country = " ".join(p.replace("-", " ") for p in parts[:year_token_index])
        else:
            country = parts[0].replace("-", " ")
            year_match = re.search(r"(?:19|20)\d{2}", filename)
            year = int(year_match.group(0)) if year_match else None

    # Infer doc_type — check specific CO markers before generic CRPD/C
    fname_lower = filename.lower()
    if re.search(r"[_/]co[_/]", filename, re.IGNORECASE) or "concluding" in fname_lower:
        doc_type = "concluding observations"
    elif "parallel" in fname_lower or "shadow" in fname_lower or "civil" in fname_lower:
        doc_type = "parallel report"
    elif "state" in fname_lower or re.search(r"crpd[_/]c[_/]", filename, re.IGNORECASE):
        doc_type = "state report"
    else:
        doc_type = "document"

    # Build UN symbol (e.g. CRPD/C/KEN/1)
    symbol_match = re.search(r"CRPD[_/]C[_/](\w+)[_/](\d+)", filename, re.IGNORECASE)
    symbol = f"CRPD/C/{symbol_match.group(1)}/{symbol_match.group(2)}" if symbol_match else ""

    return {
        "country": country,
        "year": year,
        "doc_type": doc_type,
        "symbol": symbol,
    }


def _infer_region(country: str) -> str:
    """Map country to UN regional group (best-effort, non-exhaustive).

    Args:
        country: Country name string.

    Returns:
        Region label string.
    """
    try:
        import country_converter as coco

        cc = coco.CountryConverter()
        region = cc.convert(names=country, to="UNregion")
        if region and region != "not found":
            return str(region)
    except Exception:
        pass
    return "Other"


def chunk_markdown_file(md_path: Path, chunk_size: int, overlap: int) -> list[dict]:
    """Read a Markdown file and return a list of chunk records.

    Args:
        md_path: Path to the Markdown file.
        chunk_size: Target words per chunk.
        overlap: Overlapping words between chunks.

    Returns:
        List of chunk dicts ready for embedding.
    """
    text = md_path.read_text(encoding="utf-8", errors="replace")

    # Strip Markdown syntax for cleaner embeddings (keep prose)
    text = re.sub(r"#{1,6}\s+", "", text)  # headings
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)  # bold/italic
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)  # code
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links
    text = re.sub(r"\n{3,}", "\n\n", text)  # excess blank lines
    text = text.strip()

    doc_id = md_path.stem
    meta = _parse_doc_id(doc_id)
    region = _infer_region(meta["country"])

    raw_chunks = _split_into_word_chunks(text, chunk_size, overlap)
    records = []
    for i, chunk_text in enumerate(raw_chunks):
        records.append(
            {
                "chunk_id": None,  # assigned globally after all files processed
                "text": chunk_text,
                "doc_id": doc_id,
                "country": meta["country"],
                "year": meta["year"],
                "doc_type": meta["doc_type"],
                "region": region,
                "symbol": meta["symbol"],
                "source_file": md_path.name,
                "chunk_index": i,
            }
        )
    return records


# ── Main pipeline ─────────────────────────────────────────────────────────────


def run(pdf_dir: Path, resume: bool = False) -> None:
    """Execute the full knowledge base build pipeline.

    Steps:
        1. PDF → Markdown (skips existing .md files if resume=True)
        2. Markdown → chunks with metadata
        3. Chunks → embeddings (all-mpnet-base-v2)
        4. Embeddings → FAISS IndexFlatIP
        5. Save faiss_index.bin, embeddings.npy, chunks_metadata.json

    Args:
        pdf_dir: Directory containing source PDFs.
        resume: If True, skip PDFs whose .md file already exists.
    """
    try:
        import faiss
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        print(
            f"Missing dependency: {exc}\n"
            "Install with: pip install faiss-cpu sentence-transformers pymupdf4llm",
            file=sys.stderr,
        )
        sys.exit(1)

    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print(
            f"No PDFs found in {pdf_dir}. Run: python scripts/sync_new_documents.py --backfill",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print("CRPD Knowledge Base Builder")
    print(f"{'=' * 60}")
    print(f"PDFs found   : {len(pdf_files)}")
    print(f"Chunk size   : {CHUNK_SIZE} words  (overlap: {CHUNK_OVERLAP})")
    print(f"Embed model  : {EMBEDDING_MODEL_NAME}")
    print(f"Resume mode  : {resume}")
    print()

    # ── Step 1: PDF → Markdown ────────────────────────────────────────────────
    print("Step 1/4  Converting PDFs to Markdown …")
    converted = 0
    skipped = 0
    failed = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        md_path = MARKDOWN_DIR / (pdf_path.stem + ".md")
        if resume and md_path.exists():
            skipped += 1
            continue
        print(f"  [{i:>4}/{len(pdf_files)}] {pdf_path.name}", end="\r")
        result = pdf_to_markdown(pdf_path, MARKDOWN_DIR)
        if result:
            converted += 1
        else:
            failed += 1

    print(f"  Converted: {converted}  Skipped: {skipped}  Failed: {failed}          ")

    # ── Step 2: Markdown → chunks ─────────────────────────────────────────────
    print("\nStep 2/4  Chunking Markdown files …")
    md_files = sorted(MARKDOWN_DIR.glob("*.md"))
    all_chunks: list[dict] = []

    for md_path in md_files:
        chunks = chunk_markdown_file(md_path, CHUNK_SIZE, CHUNK_OVERLAP)
        all_chunks.extend(chunks)

    # Assign global chunk IDs
    for global_id, chunk in enumerate(all_chunks):
        chunk["chunk_id"] = global_id

    print(f"  Total chunks: {len(all_chunks):,}  from {len(md_files)} documents")

    # ── Step 3: Embed all chunks ──────────────────────────────────────────────
    print(f"\nStep 3/4  Embedding {len(all_chunks):,} chunks (this takes ~15–20 min) …")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    texts = [c["text"] for c in all_chunks]

    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,  # pre-normalise for cosine via IndexFlatIP
    )
    embeddings = embeddings.astype("float32")
    print(f"  Embeddings shape: {embeddings.shape}")

    # ── Step 4: Build FAISS index ─────────────────────────────────────────────
    print("\nStep 4/4  Building FAISS index …")
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    print(f"  Index total vectors: {index.ntotal:,}")

    # ── Step 5: Save artifacts ────────────────────────────────────────────────
    faiss_path = OUTPUT_DIR / "faiss_index.bin"
    emb_path = OUTPUT_DIR / "embeddings.npy"
    meta_path = OUTPUT_DIR / "chunks_metadata.json"

    faiss.write_index(index, str(faiss_path))
    np.save(str(emb_path), embeddings)

    # Save metadata without embedding vectors (kept in .npy)
    meta_records = [{k: v for k, v in c.items() if k != "embedding"} for c in all_chunks]
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_records, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print("Knowledge base built successfully!")
    print(f"  {faiss_path}  ({faiss_path.stat().st_size / 1e6:.1f} MB)")
    print(f"  {emb_path}    ({emb_path.stat().st_size / 1e6:.1f} MB)")
    print(f"  {meta_path}  ({meta_path.stat().st_size / 1e6:.1f} MB)")
    print(f"{'=' * 60}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build CRPD knowledge base for RAG.")
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=PDF_DIR,
        help=f"Directory containing source PDFs (default: {PDF_DIR})",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip PDFs whose Markdown file already exists (faster re-runs)",
    )
    args = parser.parse_args()
    run(pdf_dir=args.pdf_dir, resume=args.resume)
