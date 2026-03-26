#!/usr/bin/env python3
"""
Evaluation script — Phase 4: Policy Brief Generation (CRPD Dashboard)
======================================================================
Cross-model comparison across 4 configs:
  config_A: all-mpnet-base-v2 + Groq llama-3.3-70b  (production baseline)
  config_B: all-MiniLM-L6-v2 + Groq llama-3.3-70b  (smaller/faster embeddings)
  config_C: all-mpnet-base-v2 + Ollama llama3        (local LLM fallback)
  config_D: all-mpnet-base-v2 + query rewriting + Groq (advanced RAG)

IR Metrics (retrieval pipeline quality, threshold-based):
  MRR, nDCG@10, Recall@5, Recall@10, Precision@5, avg_retrieval_latency_ms

LLM-as-Judge (answer quality, 1–5 per dimension via Groq evaluator):
  accuracy, completeness, relevance, groundedness

Output:
  LLM_Development/eval_results_phase4.json

Usage:
  python LLM_Development/evaluate_phase4.py

  GROQ_API_KEY can be set via environment variable or .streamlit/secrets.toml.
  Ollama must be running locally (http://localhost:11434) for config_C.

  NOTE: First run builds a MiniLM FAISS index for config_B (~3–5 min).
  Subsequent runs load it from data/faiss_index_minilm.bin.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
import math
import os
from pathlib import Path
import sys
import time

import numpy as np


# ── Path setup ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

TEST_SET_PATH = Path(__file__).parent / "test_questions_phase4.jsonl"
RESULTS_PATH = Path(__file__).parent / "eval_results_phase4.json"
CHARTS_DIR = Path(__file__).parent / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

GROQ_MODEL = "llama-3.3-70b-versatile"
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"

PASS_THRESHOLD = 3.5
# Chunks above this similarity score are treated as "relevant" for IR metrics
RELEVANCE_THRESHOLD = 0.45

# Config registry
CONFIGS: dict[str, dict] = {
    "config_A": {
        "embedding_model": "all-mpnet-base-v2",
        "llm": "groq/llama-3.3-70b-versatile",
        "query_rewrite": False,
        "description": "Production baseline: mpnet + Groq",
    },
    "config_B": {
        "embedding_model": "all-MiniLM-L6-v2",
        "llm": "groq/llama-3.3-70b-versatile",
        "query_rewrite": False,
        "description": "Smaller embeddings: MiniLM + Groq",
    },
    "config_C": {
        "embedding_model": "all-mpnet-base-v2",
        "llm": "ollama/llama3.2",
        "query_rewrite": False,
        "description": "Local LLM fallback: mpnet + Ollama",
    },
    "config_D": {
        "embedding_model": "all-mpnet-base-v2",
        "llm": "groq/llama-3.3-70b-versatile",
        "query_rewrite": True,
        "description": "Advanced RAG: mpnet + query rewriting + Groq",
    },
}

# ── System prompts ────────────────────────────────────────────────────────────

BRIEF_SYSTEM_PROMPT = (
    "You are an expert CRPD policy analyst for the Institute on Disability and Public Policy "
    "(IDPP) at American University.\n\n"
    "Generate a structured policy brief using ONLY the provided document excerpts.\n\n"
    "You MUST use these EXACT section headers in this order:\n"
    "## CONTEXT\n## KEY FINDINGS\n## RECOMMENDATIONS\n## SOURCES\n\n"
    "Rules:\n"
    "- Ground every claim in the provided excerpts. Never invent facts.\n"
    "- In SOURCES list the documents you drew from (country, year, document type).\n"
    "- Use formal policy language. Frame analysis through a disability rights lens.\n"
    "- If excerpts are sparse, acknowledge it rather than fabricating content."
)

REWRITE_PROMPT = (
    "You are a search query optimizer for a UN disability rights document database.\n"
    "Rewrite the following policy brief request as a concise, information-dense search query "
    "(max 20 words) that will surface the most relevant CRPD document excerpts.\n"
    "Return ONLY the rewritten query, no explanation."
)

JUDGE_SYSTEM_PROMPT = (
    "You are an impartial evaluator assessing AI-generated CRPD policy briefs.\n\n"
    "The briefs were produced using RAG: the AI retrieved excerpts from real CRPD state party "
    "reports and concluding observations, then generated a structured brief.\n\n"
    "Score the brief on 4 dimensions, each from 1 (very poor) to 5 (excellent):\n"
    "- accuracy: Are all factual claims consistent with the retrieved document excerpts?\n"
    "- completeness: Does the brief contain all required sections "
    "(Context, Key Findings, Recommendations, Sources) with substantive content?\n"
    "- relevance: Is the content directly relevant to the specified countries, "
    "articles, and reporting period?\n"
    "- groundedness: Is every claim supported by a retrieved excerpt? "
    "Penalise any hallucinated countries, years, or statistics not present in the sources.\n\n"
    'Respond ONLY with valid JSON: {"accuracy": N, "completeness": N, '
    '"relevance": N, "groundedness": N, "notes": "brief comment"}'
)


# ── API key helpers ───────────────────────────────────────────────────────────


def _get_groq_api_key() -> str:
    """Read GROQ_API_KEY from environment or .streamlit/secrets.toml."""
    key = os.environ.get("GROQ_API_KEY", "")
    if key:
        return key

    secrets_path = PROJECT_ROOT / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ImportError:
                tomllib = None  # type: ignore[assignment]
        if tomllib is not None:
            with open(secrets_path, "rb") as f:
                secrets = tomllib.load(f)
            key = secrets.get("GROQ_API_KEY", "")
            if key:
                return key

    raise RuntimeError(
        "GROQ_API_KEY not found.\n"
        "  Option 1: export GROQ_API_KEY=gsk_...\n"
        "  Option 2: add GROQ_API_KEY = '...' to .streamlit/secrets.toml"
    )


def _groq_call(client, messages: list[dict], max_tokens: int = 1200) -> str:
    """Single Groq API call with exponential backoff on 429 rate-limit errors."""
    max_retries = 5
    base_wait = 15  # seconds — Groq free tier resets quickly

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            msg = str(exc)
            is_rate_limit = (
                "429" in msg or "rate_limit" in msg.lower() or "rate limit" in msg.lower()
            )
            if is_rate_limit and attempt < max_retries - 1:
                wait = base_wait * (2**attempt)
                print(
                    f"    [429] Rate limit — waiting {wait}s before retry {attempt + 1}/{max_retries - 1}…"
                )
                time.sleep(wait)
            else:
                raise


def _ollama_check() -> bool:
    """Return True if Ollama is reachable on localhost:11434."""
    try:
        import urllib.request

        req = urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        return req.status == 200
    except Exception:
        return False


def _ollama_generate(prompt: str, system: str) -> str:
    """Call Ollama generate API. Returns text or raises on error."""
    import urllib.request

    payload = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "prompt": f"{system}\n\n{prompt}",
            "stream": False,
        }
    ).encode()

    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data.get("response", "").strip()


# ── Knowledge base helpers ────────────────────────────────────────────────────


def _load_chunks() -> list[dict]:
    """Load chunk metadata from disk."""
    meta_path = PROJECT_ROOT / "data" / "chunks_metadata.json"
    if not meta_path.exists():
        return []
    with open(meta_path) as f:
        return json.load(f)


def _load_faiss_index(index_path: Path):
    """Load a FAISS index from disk. Returns index or None."""
    try:
        import faiss

        return faiss.read_index(str(index_path))
    except Exception as e:
        print(f"  [WARN] Could not load index {index_path.name}: {e}")
        return None


def _load_embed_model(model_name: str):
    """Load a sentence-transformer model."""
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name)
    except Exception as e:
        print(f"  [WARN] Could not load embedding model '{model_name}': {e}")
        return None


def _build_minilm_index(chunks: list[dict]) -> object | None:
    """
    Build a FAISS IndexFlatIP from all chunk texts using MiniLM.
    Saves result to data/faiss_index_minilm.bin for reuse.
    Returns the index or None on failure.
    """
    minilm_path = PROJECT_ROOT / "data" / "faiss_index_minilm.bin"

    try:
        import faiss
        from sentence_transformers import SentenceTransformer

        print("  Building MiniLM FAISS index (first run — ~3–5 min)…")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        texts = [c.get("text", "") for c in chunks]

        batch_size = 256
        all_vecs = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            vecs = model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
            all_vecs.append(vecs)
            if (start // batch_size) % 20 == 0:
                pct = min(100, int((start + batch_size) / len(texts) * 100))
                print(f"    {pct}% encoded…")

        matrix = np.vstack(all_vecs).astype("float32")
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        matrix = matrix / np.maximum(norms, 1e-10)

        dim = matrix.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(matrix)

        faiss.write_index(index, str(minilm_path))
        print(f"  MiniLM index saved → {minilm_path} ({index.ntotal:,} vectors)")
        return index

    except Exception as e:
        print(f"  [WARN] MiniLM index build failed: {e}")
        return None


def _get_index_for_config(config_id: str, config: dict, chunks: list[dict]):
    """Return (embed_model, faiss_index) for a given config."""
    model_name = config["embedding_model"]

    if model_name == "all-MiniLM-L6-v2":
        minilm_path = PROJECT_ROOT / "data" / "faiss_index_minilm.bin"
        if minilm_path.exists():
            index = _load_faiss_index(minilm_path)
        else:
            index = _build_minilm_index(chunks)
        model = _load_embed_model("all-MiniLM-L6-v2")
    else:
        # Default: use production mpnet index
        index = _load_faiss_index(PROJECT_ROOT / "data" / "faiss_index.bin")
        model = _load_embed_model("all-mpnet-base-v2")

    return model, index


# ── Semantic search ───────────────────────────────────────────────────────────


def _semantic_search(
    model,
    index,
    chunks: list[dict],
    query: str,
    top_k: int = 10,
    filter_country: str | None = None,
    filter_year_min: int | None = None,
    filter_year_max: int | None = None,
) -> tuple[list[dict], float]:
    """
    Run semantic search and return (results, latency_ms).
    results is a list of chunk dicts with "score" added.
    """
    if model is None or index is None or not chunks:
        return [], 0.0

    t0 = time.perf_counter()
    query_vec = model.encode([query], convert_to_numpy=True).astype("float32")
    norm = np.linalg.norm(query_vec, axis=1, keepdims=True)
    query_vec = query_vec / np.maximum(norm, 1e-10)

    k_retrieve = min(top_k * 5, index.ntotal)
    scores, indices = index.search(query_vec, k_retrieve)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    results: list[dict] = []
    for score, idx in zip(scores[0], indices[0], strict=False):
        if idx < 0 or idx >= len(chunks):
            continue
        chunk = chunks[idx]

        # Apply filters
        if filter_country and chunk.get("country", "").lower() != filter_country.lower():
            continue
        if filter_year_min and (chunk.get("year") or 0) < filter_year_min:
            continue
        if filter_year_max and (chunk.get("year") or 9999) > filter_year_max:
            continue

        results.append({**chunk, "score": float(score)})
        if len(results) >= top_k:
            break

    return results, elapsed_ms


def _format_chunks(chunks: list[dict]) -> str:
    """Format retrieved chunks for LLM context."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        country = chunk.get("country", "Unknown")
        year = chunk.get("year", "n/a")
        doc_type = str(chunk.get("doc_type", "document")).title()
        text = chunk.get("text", "")
        words = text.split()
        if len(words) > 600:
            text = " ".join(words[:600]) + "…"
        parts.append(f"[Source {i}: {country}, {year}, {doc_type}]\n{text}")
    return "\n\n---\n\n".join(parts)


# ── IR metrics ────────────────────────────────────────────────────────────────


def _compute_ir_metrics(
    results: list[dict],
    threshold: float = RELEVANCE_THRESHOLD,
) -> dict[str, float]:
    """
    Compute threshold-based IR metrics for a single query's retrieved results.
    Treats chunks with score >= threshold as "relevant".

    Metrics:
      mrr        : 1 / rank_of_first_relevant (0 if none)
      ndcg_10    : nDCG@10 using score as gain
      recall_5   : relevant in top-5 / total relevant
      recall_10  : relevant in top-10 / total relevant
      precision_5: relevant in top-5 / 5
    """
    if not results:
        return {"mrr": 0.0, "ndcg_10": 0.0, "recall_5": 0.0, "recall_10": 0.0, "precision_5": 0.0}

    relevant_flags = [1 if r["score"] >= threshold else 0 for r in results]
    total_relevant = sum(relevant_flags)

    # MRR
    mrr = 0.0
    for rank, flag in enumerate(relevant_flags, 1):
        if flag:
            mrr = 1.0 / rank
            break

    # nDCG@10
    gains = [r["score"] for r in results[:10]]
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
    ideal_gains = sorted(gains, reverse=True)
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal_gains))
    ndcg_10 = dcg / idcg if idcg > 0 else 0.0

    # Recall@K and Precision@K
    rel_in_5 = sum(relevant_flags[:5])
    rel_in_10 = sum(relevant_flags[:10])
    recall_5 = rel_in_5 / total_relevant if total_relevant > 0 else 0.0
    recall_10 = rel_in_10 / total_relevant if total_relevant > 0 else 0.0
    precision_5 = rel_in_5 / 5.0

    return {
        "mrr": round(mrr, 4),
        "ndcg_10": round(ndcg_10, 4),
        "recall_5": round(recall_5, 4),
        "recall_10": round(recall_10, 4),
        "precision_5": round(precision_5, 4),
    }


# ── Brief generation ──────────────────────────────────────────────────────────


def _build_query(question: dict) -> str:
    """Build a search query string from a test question."""
    parts = question.get("countries", []) + question.get("articles", [])
    base = " ".join(parts)
    return base if base.strip() else "CRPD disability rights"


def _rewrite_query(client, original_query: str) -> str:
    """Use Groq to rewrite the query for better retrieval (config_D)."""
    try:
        messages = [
            {"role": "system", "content": REWRITE_PROMPT},
            {"role": "user", "content": original_query},
        ]
        return _groq_call(client, messages, max_tokens=60)
    except Exception as e:
        print(f"    [WARN] Query rewrite failed: {e} — using original")
        return original_query


def _generate_brief_groq(client, question: dict, chunks: list[dict]) -> tuple[str, int]:
    """Generate brief via Groq. Returns (raw_text, tokens_used)."""
    countries = question.get("countries", [])
    articles = question.get("articles", [])
    year_min = question.get("year_min", 2010)
    year_max = question.get("year_max", 2024)
    brief_format = question.get("brief_format", "Executive Summary")

    evidence = _format_chunks(chunks[:8])
    user_prompt = (
        f"Write a {brief_format} on CRPD implementation in: {', '.join(countries) or 'all countries'}.\n"
        f"Focus on: {', '.join(articles) or 'all articles'}.\n"
        f"Reporting period: {year_min}–{year_max}.\n\n"
        f"DOCUMENT EXCERPTS:\n{evidence}\n\n"
        "Now write the brief using the EXACT section headers specified."
    )
    messages = [
        {"role": "system", "content": BRIEF_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    try:
        # Route through _groq_call so 429 retry-with-backoff is applied
        raw = _groq_call(client, messages, max_tokens=1400)
        return raw, 0  # token count not available via _groq_call wrapper
    except Exception as e:
        return f"ERROR: {e}", 0


def _generate_brief_ollama(question: dict, chunks: list[dict]) -> str:
    """Generate brief via Ollama. Returns raw text or error string."""
    countries = question.get("countries", [])
    articles = question.get("articles", [])
    year_min = question.get("year_min", 2010)
    year_max = question.get("year_max", 2024)
    brief_format = question.get("brief_format", "Executive Summary")

    evidence = _format_chunks(chunks[:6])  # smaller context for local model
    prompt = (
        f"Write a {brief_format} on CRPD implementation in: {', '.join(countries) or 'all countries'}.\n"
        f"Focus on: {', '.join(articles) or 'all articles'}.\n"
        f"Reporting period: {year_min}–{year_max}.\n\n"
        f"DOCUMENT EXCERPTS:\n{evidence}\n\n"
        "Write the brief using the EXACT section headers: "
        "## CONTEXT, ## KEY FINDINGS, ## RECOMMENDATIONS, ## SOURCES"
    )
    try:
        return _ollama_generate(prompt, BRIEF_SYSTEM_PROMPT)
    except Exception as e:
        return f"ERROR: Ollama generation failed — {e}"


# ── LLM-as-Judge ─────────────────────────────────────────────────────────────


def _judge_brief_ollama(question: dict, brief_text: str, chunks: list[dict]) -> dict:
    """Score a generated brief on 4 dimensions using Ollama as judge (no Groq quota used)."""
    evidence_summary = _format_chunks(chunks[:5])
    judge_prompt = (
        f"RETRIEVED DOCUMENT EXCERPTS PROVIDED TO THE AI:\n{evidence_summary}\n\n"
        f"BRIEF REQUEST:\n"
        f"  Countries: {question.get('countries', [])}\n"
        f"  Articles: {question.get('articles', [])}\n"
        f"  Period: {question.get('year_min')}–{question.get('year_max')}\n"
        f"  Format: {question.get('brief_format')}\n\n"
        f"GENERATED BRIEF:\n{brief_text[:3000]}\n\n"
        f"EVALUATION CRITERIA: {question.get('criteria', '')}\n\n"
        "Score this brief on all 4 dimensions. Respond with ONLY valid JSON."
    )
    judge_raw = ""
    try:
        judge_raw = _ollama_generate(
            f"{JUDGE_SYSTEM_PROMPT}\n\n{judge_prompt}", JUDGE_SYSTEM_PROMPT
        )
        judge_raw = judge_raw.strip()
        if judge_raw.startswith("```"):
            parts = judge_raw.split("```")
            judge_raw = parts[1] if len(parts) > 2 else parts[-1]
            if judge_raw.startswith("json"):
                judge_raw = judge_raw[4:]
        return json.loads(judge_raw.strip())
    except Exception as e:
        return {"error": f"Judge parse failed: {e}", "raw": judge_raw[:200]}


def _judge_brief(client, question: dict, brief_text: str, chunks: list[dict]) -> dict:
    """Score a generated brief on 4 dimensions using Groq as judge."""
    evidence_summary = _format_chunks(chunks[:5])
    judge_prompt = (
        f"RETRIEVED DOCUMENT EXCERPTS PROVIDED TO THE AI:\n{evidence_summary}\n\n"
        f"BRIEF REQUEST:\n"
        f"  Countries: {question.get('countries', [])}\n"
        f"  Articles: {question.get('articles', [])}\n"
        f"  Period: {question.get('year_min')}–{question.get('year_max')}\n"
        f"  Format: {question.get('brief_format')}\n\n"
        f"GENERATED BRIEF:\n{brief_text[:3000]}\n\n"
        f"EVALUATION CRITERIA: {question.get('criteria', '')}\n\n"
        "Score this brief on all 4 dimensions."
    )
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": judge_prompt},
    ]
    judge_raw = ""
    try:
        judge_raw = _groq_call(client, messages, max_tokens=300)
        judge_raw = judge_raw.strip()
        if judge_raw.startswith("```"):
            parts = judge_raw.split("```")
            judge_raw = parts[1] if len(parts) > 2 else parts[-1]
            if judge_raw.startswith("json"):
                judge_raw = judge_raw[4:]
        return json.loads(judge_raw.strip())
    except Exception as e:
        return {"error": f"Judge parse failed: {e}", "raw": judge_raw[:200]}


# ── Per-config evaluation ─────────────────────────────────────────────────────


def run_config(
    config_id: str,
    config: dict,
    questions: list[dict],
    chunks: list[dict],
    groq_client,
) -> dict:
    """
    Run full evaluation for a single config.
    Returns a results dict matching the eval_results_phase4.json spec.
    """
    print(f"\n{'─' * 60}")
    print(f"Config: {config_id} — {config['description']}")
    print("─" * 60)

    # Check Ollama availability
    if config["llm"] == "ollama/llama3.2" and not _ollama_check():
        print("  [SKIP] Ollama not running. Skipping config_C.")
        return {
            "embedding_model": config["embedding_model"],
            "llm": config["llm"],
            "description": config["description"],
            "skipped": True,
            "skip_reason": "Ollama not running on localhost:11434",
            "scores": {},
            "per_question": [],
        }

    # Load embedding model and index
    print(f"  Loading embedding model: {config['embedding_model']}…")
    embed_model, faiss_index = _get_index_for_config(config_id, config, chunks)

    if embed_model is None or faiss_index is None:
        print("  [ERROR] Could not load model or index. Skipping config.")
        return {
            "embedding_model": config["embedding_model"],
            "llm": config["llm"],
            "description": config["description"],
            "skipped": True,
            "skip_reason": "Failed to load embedding model or FAISS index",
            "scores": {},
            "per_question": [],
        }

    per_question = []
    dim_scores: dict[str, list[float]] = {
        "accuracy": [],
        "completeness": [],
        "relevance": [],
        "groundedness": [],
    }
    ir_scores: dict[str, list[float]] = {
        "mrr": [],
        "ndcg_10": [],
        "recall_5": [],
        "recall_10": [],
        "precision_5": [],
    }
    retrieval_latencies: list[float] = []
    generation_latencies: list[float] = []

    for q in questions:
        qid = q["id"]
        print(
            f"\n  [{qid}] {q['category']} — {q.get('countries', [])} | {q.get('brief_format', '')}"
        )

        # Build search query
        base_query = _build_query(q)

        # Config D: rewrite query
        if config["query_rewrite"]:
            print("    → Rewriting query via Groq…")
            search_query = _rewrite_query(groq_client, base_query)
            print(f"    → Rewritten: {search_query[:80]}")
        else:
            search_query = base_query

        # Retrieve chunks (per country if specified)
        countries = q.get("countries", [])
        all_results: list[dict] = []
        total_latency_ms = 0.0

        if countries:
            per_country_k = max(3, 8 // len(countries))
            for country in countries[:5]:
                results, lat_ms = _semantic_search(
                    embed_model,
                    faiss_index,
                    chunks,
                    search_query,
                    top_k=per_country_k,
                    filter_country=country,
                    filter_year_min=q.get("year_min"),
                    filter_year_max=q.get("year_max"),
                )
                all_results.extend(results)
                total_latency_ms += lat_ms
        else:
            all_results, total_latency_ms = _semantic_search(
                embed_model,
                faiss_index,
                chunks,
                search_query,
                top_k=8,
                filter_year_min=q.get("year_min"),
                filter_year_max=q.get("year_max"),
            )

        # Deduplicate by chunk_id
        seen_ids: set[str] = set()
        unique_chunks: list[dict] = []
        for c in all_results:
            cid = c.get("chunk_id", c.get("source_file", "") + str(c.get("chunk_index", 0)))
            if cid not in seen_ids:
                seen_ids.add(cid)
                unique_chunks.append(c)

        # Fallback: unfiltered search if nothing retrieved
        if not unique_chunks:
            fallback_q = " ".join(countries) + " CRPD disability rights"
            unique_chunks, lat_ms = _semantic_search(
                embed_model, faiss_index, chunks, fallback_q, top_k=8
            )
            total_latency_ms += lat_ms
            print(
                f"    [WARN] Country filter returned 0 results — used fallback ({len(unique_chunks)} chunks)"
            )

        retrieval_latencies.append(total_latency_ms)

        # Compute IR metrics
        ir = _compute_ir_metrics(unique_chunks[:10])
        for k in ir_scores:
            ir_scores[k].append(ir[k])

        print(
            f"    Chunks: {len(unique_chunks)}  "
            f"MRR:{ir['mrr']:.2f}  nDCG:{ir['ndcg_10']:.2f}  "
            f"R@5:{ir['recall_5']:.2f}  lat:{total_latency_ms:.0f}ms"
        )

        # Generate brief
        print("    → Generating brief…")
        t_gen = time.perf_counter()

        use_ollama = config["llm"] == "ollama/llama3.2"
        if use_ollama:
            raw_brief = _generate_brief_ollama(q, unique_chunks)
            tokens_used = 0
        else:
            raw_brief, tokens_used = _generate_brief_groq(groq_client, q, unique_chunks)

        gen_latency_ms = (time.perf_counter() - t_gen) * 1000
        generation_latencies.append(gen_latency_ms)
        brief_ok = not raw_brief.startswith("ERROR:")

        # Judge the brief — use Ollama judge for config_C to avoid Groq quota
        judge_scores: dict = {}
        if brief_ok:
            print("    → Judging brief…")
            if use_ollama:
                judge_scores = _judge_brief_ollama(q, raw_brief, unique_chunks)
            else:
                time.sleep(3.0)  # pause between generation and judge calls
                judge_scores = _judge_brief(groq_client, q, raw_brief, unique_chunks)
            if "error" not in judge_scores:
                for dim in dim_scores:
                    val = judge_scores.get(dim)
                    if isinstance(val, int | float):
                        dim_scores[dim].append(float(val))
                avg = (
                    sum(
                        judge_scores.get(d, 0)
                        for d in ["accuracy", "completeness", "relevance", "groundedness"]
                    )
                    / 4
                )
                status = "✅ PASS" if avg >= PASS_THRESHOLD else "⚠ LOW"
                print(
                    f"    ACC:{judge_scores.get('accuracy')}  "
                    f"CPL:{judge_scores.get('completeness')}  "
                    f"REL:{judge_scores.get('relevance')}  "
                    f"GRD:{judge_scores.get('groundedness')}  "
                    f"avg:{avg:.2f}  {status}"
                )
                print(f"    Notes: {str(judge_scores.get('notes', ''))[:80]}")
            else:
                print(f"    [WARN] Judge error: {judge_scores.get('error')}")
        else:
            print(f"    [ERROR] Generation failed: {raw_brief[:80]}")

        per_question.append(
            {
                "id": qid,
                "category": q["category"],
                "countries": countries,
                "articles": q.get("articles", []),
                "brief_format": q.get("brief_format"),
                "search_query_used": search_query,
                "chunks_retrieved": len(unique_chunks),
                "retrieval_latency_ms": round(total_latency_ms, 1),
                "generation_latency_ms": round(gen_latency_ms, 1),
                "tokens_used": tokens_used,
                "ir_metrics": ir,
                "judge_scores": judge_scores,
                "brief_ok": brief_ok,
                "brief_preview": raw_brief[:500] if brief_ok else None,
                "error": None if brief_ok else raw_brief,
            }
        )

        time.sleep(12.0)  # Rate-limit pause between questions (Groq free tier ~6k tokens/min)

    # Aggregate scores
    def _avg(lst: list[float]) -> float:
        return round(sum(lst) / len(lst), 4) if lst else 0.0

    agg_scores = {
        "accuracy": _avg(dim_scores["accuracy"]),
        "completeness": _avg(dim_scores["completeness"]),
        "relevance": _avg(dim_scores["relevance"]),
        "groundedness": _avg(dim_scores["groundedness"]),
        "mrr": _avg(ir_scores["mrr"]),
        "ndcg_10": _avg(ir_scores["ndcg_10"]),
        "recall_5": _avg(ir_scores["recall_5"]),
        "recall_10": _avg(ir_scores["recall_10"]),
        "precision_5": _avg(ir_scores["precision_5"]),
        "avg_retrieval_latency_ms": round(_avg(retrieval_latencies), 1),
        "avg_generation_latency_ms": round(_avg(generation_latencies), 1),
    }

    judge_avg = _avg(
        dim_scores["accuracy"]
        + dim_scores["completeness"]
        + dim_scores["relevance"]
        + dim_scores["groundedness"]
    )
    ir_avg = _avg(ir_scores["mrr"] + ir_scores["ndcg_10"])
    combined = round((judge_avg + ir_avg * 5) / 2, 4)  # normalize IR to same 0–5 scale

    return {
        "embedding_model": config["embedding_model"],
        "llm": config["llm"],
        "description": config["description"],
        "skipped": False,
        "scores": agg_scores,
        "judge_avg": round(judge_avg, 4),
        "ir_avg": round(ir_avg, 4),
        "combined_score": combined,
        "per_question": per_question,
    }


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Phase 4 Evaluation — Policy Brief Generation")
    parser.add_argument(
        "--configs",
        default="A,B,C,D",
        help="Comma-separated list of config IDs to run (e.g. A or A,D). Default: A,B,C,D",
    )
    args = parser.parse_args()
    selected_ids = {f"config_{c.strip().upper()}" for c in args.configs.split(",")}
    active_configs = {k: v for k, v in CONFIGS.items() if k in selected_ids}
    if not active_configs:
        print(f"ERROR: No valid configs found in --configs={args.configs!r}. Use A, B, C, or D.")
        sys.exit(1)

    print("=" * 60)
    print("Phase 4 Evaluation — Policy Brief Generation")
    print(f"Started: {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M:%S')}")
    if active_configs.keys() != CONFIGS.keys():
        print(f"Running configs: {', '.join(sorted(active_configs))}")
    print("=" * 60)

    # Load test questions
    if not TEST_SET_PATH.exists():
        print(f"ERROR: {TEST_SET_PATH} not found.")
        sys.exit(1)
    questions: list[dict] = []
    with open(TEST_SET_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    print(f"Loaded {len(questions)} test questions.\n")

    # Load chunks metadata (shared across configs)
    print("Loading chunk metadata…")
    chunks = _load_chunks()
    if not chunks:
        print("ERROR: data/chunks_metadata.json not found. Run build_knowledge_base.py first.")
        sys.exit(1)
    print(f"  {len(chunks):,} chunks loaded.\n")

    # Load Groq
    api_key = _get_groq_api_key()
    from groq import Groq

    groq_client = Groq(api_key=api_key)

    # Run each config — pause between configs to let Groq token bucket refill
    config_results: dict[str, dict] = {}
    config_ids = list(active_configs.items())
    for i, (config_id, config) in enumerate(config_ids):
        result = run_config(config_id, config, questions, chunks, groq_client)
        config_results[config_id] = result
        if i < len(config_ids) - 1:
            print("\n  ⏳ Waiting 90s between configs to reset Groq token bucket…")
            time.sleep(90)

    # Determine winner (highest combined_score among non-skipped configs)
    active = {k: v for k, v in config_results.items() if not v.get("skipped")}
    winner = max(active, key=lambda k: active[k].get("combined_score", 0)) if active else "config_A"
    winner_data = active.get(winner, {})

    # Build recommendation string
    w_judge = winner_data.get("judge_avg", 0)
    w_ir = winner_data.get("ir_avg", 0)
    skipped = [k for k, v in config_results.items() if v.get("skipped")]
    skip_note = (
        f" (config_C skipped: {config_results['config_C'].get('skip_reason', '')})"
        if skipped
        else ""
    )

    recommendation = (
        f"{winner} is the top performer (judge avg {w_judge:.2f}/5.0, "
        f"IR avg {w_ir:.2f}/1.0){skip_note}. "
    )
    if w_judge >= PASS_THRESHOLD and w_ir >= 0.70:
        recommendation += (
            "Both answer quality and retrieval meet targets. Deploy as production config."
        )
    elif w_judge >= PASS_THRESHOLD:
        recommendation += (
            "Answer quality meets threshold but retrieval MRR < 0.70. Consider query rewriting."
        )
    elif w_ir >= 0.70:
        recommendation += (
            "Retrieval quality is strong but judge scores are low. Review prompt or model config."
        )
    else:
        recommendation += "Neither threshold met. Expand knowledge base or improve chunk quality."

    # ── Summary ──
    print(f"\n{'=' * 60}")
    print("PHASE 4 EVALUATION SUMMARY")
    print("=" * 60)
    for cid, res in config_results.items():
        if res.get("skipped"):
            print(f"  {cid}: SKIPPED — {res.get('skip_reason')}")
        else:
            s = res["scores"]
            print(
                f"  {cid}: judge={res['judge_avg']:.2f}  "
                f"IR={res['ir_avg']:.2f}  "
                f"combined={res['combined_score']:.2f}  "
                f"MRR={s.get('mrr', 0):.2f}  nDCG={s.get('ndcg_10', 0):.2f}"
            )

    print(f"\n  Winner: {winner}")
    print(f"  Recommendation: {recommendation}")

    # ── Save results ──
    output = {
        "phase": 4,
        "run_date": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "test_questions": len(questions),
        "configs": config_results,
        "winner": winner,
        "recommendation": recommendation,
        "acceptance_criteria": {
            "mrr_target": 0.70,
            "ndcg_target": 0.80,
            "judge_avg_target": PASS_THRESHOLD,
            "winner_mrr": winner_data.get("scores", {}).get("mrr", 0),
            "winner_ndcg": winner_data.get("scores", {}).get("ndcg_10", 0),
            "winner_judge_avg": w_judge,
            "mrr_met": winner_data.get("scores", {}).get("mrr", 0) >= 0.70,
            "ndcg_met": winner_data.get("scores", {}).get("ndcg_10", 0) >= 0.80,
            "judge_met": w_judge >= PASS_THRESHOLD,
        },
    }

    with open(RESULTS_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nResults saved → {RESULTS_PATH}")
    print(f"Finished: {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
