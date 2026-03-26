#!/usr/bin/env python3
"""
Evaluation script — Phase 3: RAG + Semantic Search (CRPD Dashboard)
=====================================================================
Scope:
  Phase 3 — RAG-grounded chat answers + semantic document search

What this measures:
  RAG Answer Quality (LLM-as-judge, 1–5 per dimension):
    - accuracy      : Factually grounded in retrieved chunks? No hallucinations?
    - relevance     : Directly addresses the question?
    - groundedness  : Every claim supported by a retrieved source?
    - completeness  : Covers key aspects of the question?
    - citation      : Cites sources with country, year, doc_type?

  Semantic Search Quality (automated pass/fail):
    - retrieval_hit : Returns results for a relevant query
    - score_range   : All scores in [0, 1]
    - filter_doc    : Doc-type filter returns only that doc type
    - filter_year   : Year filter returns only docs >= year_min
    - off_topic     : Off-topic query returns low scores (< 0.4)

Output:
  LLM_Development/eval_results_phase3.json  — full per-question results
  (summary table printed to stdout)

Usage:
  python LLM_Development/evaluate_phase3.py

  GROQ_API_KEY can be set as an environment variable or placed in
  .streamlit/secrets.toml (auto-detected).
"""

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys

import pandas as pd


# ── Path setup ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATA_PATH = PROJECT_ROOT / "data" / "crpd_reports.csv"
TEST_SET_PATH = Path(__file__).parent / "test_questions_phase3.jsonl"
RESULTS_PATH = Path(__file__).parent / "eval_results_phase3.json"

GROQ_MODEL = "llama-3.3-70b-versatile"
PASS_THRESHOLD = 3.5  # minimum average score to pass
SEARCH_SCORE_THRESHOLD = 0.4  # off-topic queries should score below this


# ── API key ───────────────────────────────────────────────────────────────────


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
                tomllib = None
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


# ── Groq client ───────────────────────────────────────────────────────────────


def _groq_call(client, messages: list[dict], max_tokens: int = 800) -> str:
    """Make a single Groq API call and return the text content."""
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


# ── System prompts ────────────────────────────────────────────────────────────

RAG_SYSTEM_PROMPT = (
    "You are an expert CRPD research assistant for the Institute on Disability and Public "
    "Policy (IDPP) at American University.\n\n"
    "You have been given excerpts from actual CRPD state party reports, parallel reports, "
    "and concluding observations. Answer the question using ONLY these excerpts.\n\n"
    "Rules:\n"
    "- Ground every claim in a specific source excerpt provided.\n"
    "- Cite sources by country, year, and document type (e.g., Kenya 2022 state report).\n"
    "- Never invent facts not present in the provided excerpts.\n"
    "- If the excerpts are insufficient to answer fully, say so explicitly.\n"
    "- Use formal, accessible language appropriate for policy audiences.\n"
    "- Frame answers through a disability rights lens.\n"
    "- Be concise — aim for 2–4 paragraphs per response."
)

JUDGE_SYSTEM_PROMPT = (
    "You are an impartial evaluator assessing the quality of AI-generated answers "
    "about CRPD (Convention on the Rights of Persons with Disabilities) documents.\n\n"
    "The answers were generated using RAG (Retrieval-Augmented Generation): "
    "the AI retrieved excerpts from real CRPD documents and used them to answer.\n\n"
    "Score each answer on 5 dimensions, each from 1 (very poor) to 5 (excellent):\n"
    "- accuracy: Is the answer factually consistent with the retrieved document excerpts?\n"
    "- relevance: Does the answer directly address what was asked?\n"
    "- groundedness: Is every claim supported by the retrieved excerpts? "
    "Flag any hallucinated content not present in the provided sources.\n"
    "- completeness: Does it cover the key aspects of the question using the available excerpts?\n"
    "- citation: Does the answer cite sources with country, year, and document type?\n\n"
    "Also note: for hallucination probes (fictional countries/topics), "
    "did the answer correctly refuse or acknowledge the limitation?\n\n"
    'Respond ONLY with valid JSON: {"accuracy": N, "relevance": N, '
    '"groundedness": N, "completeness": N, "citation": N, "notes": "brief comment"}'
)


# ── RAG pipeline (standalone, no Streamlit) ───────────────────────────────────


def _load_kb():
    """Load FAISS index and chunk metadata. Returns (index, chunks) or (None, [])."""
    import json as _json

    faiss_path = PROJECT_ROOT / "data" / "faiss_index.bin"
    meta_path = PROJECT_ROOT / "data" / "chunks_metadata.json"

    if not faiss_path.exists() or not meta_path.exists():
        return None, []

    try:
        import faiss
        import numpy as np

        index = faiss.read_index(str(faiss_path))
        with open(meta_path) as f:
            chunks = _json.load(f)
        return index, chunks
    except Exception as e:
        print(f"  [WARN] Could not load knowledge base: {e}")
        return None, []


def _load_embed_model():
    """Load sentence-transformer model."""
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer("all-mpnet-base-v2")
    except ImportError:
        return None


def _semantic_search(
    model,
    index,
    chunks,
    query: str,
    top_k: int = 8,
    filter_doc_type: str | None = None,
    filter_year_min: int | None = None,
) -> list[dict]:
    """Run semantic search — mirrors src/llm.py semantic_search()."""
    import numpy as np

    if model is None or index is None or not chunks:
        return []

    query_vec = model.encode([query], convert_to_numpy=True).astype("float32")
    norm = np.linalg.norm(query_vec, axis=1, keepdims=True)
    query_vec = query_vec / np.maximum(norm, 1e-10)

    k_retrieve = min(top_k * 4, len(chunks))
    scores, indices = index.search(query_vec, k_retrieve)

    results = []
    for score, idx in zip(scores[0], indices[0], strict=False):
        if idx < 0 or idx >= len(chunks):
            continue
        chunk = chunks[idx]

        if filter_doc_type and chunk.get("doc_type") != filter_doc_type:
            continue
        if filter_year_min:
            yr = chunk.get("year")
            if yr and yr < filter_year_min:
                continue

        results.append({**chunk, "score": float(score)})
        if len(results) >= top_k:
            break

    return results


def _format_chunks(chunks: list[dict]) -> str:
    """Format retrieved chunks for LLM prompt."""
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


# ── Evaluation runners ────────────────────────────────────────────────────────


def run_rag_question(
    client,
    model,
    index,
    chunks,
    df,
    question: dict,
) -> dict:
    """Run a single RAG question and judge the response."""
    q_text = question["question"]
    results = _semantic_search(model, index, chunks, q_text, top_k=8)

    # Build prompt
    if results:
        evidence = _format_chunks(results)
        prompt = (
            f"RELEVANT DOCUMENT EXCERPTS:\n{evidence}\n\n"
            f"QUESTION: {q_text}\n\n"
            "Answer based on the document excerpts above. "
            "Cite specific sources by country, year, and document type."
        )
    else:
        prompt = (
            f"QUESTION: {q_text}\n\n"
            "Note: No relevant document excerpts were retrieved. "
            "Explain that you cannot answer without document evidence."
        )

    messages = [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    print("  → Calling Groq for RAG answer…")
    try:
        answer = _groq_call(client, messages, max_tokens=800)
    except Exception as e:
        return {
            "id": question["id"],
            "category": question["category"],
            "question": q_text,
            "answer": None,
            "chunks_retrieved": 0,
            "scores": None,
            "error": str(e),
        }

    # Judge the answer
    judge_prompt = (
        f"RETRIEVED EXCERPTS PROVIDED TO THE AI:\n{_format_chunks(results) if results else '(none)'}\n\n"
        f"QUESTION: {q_text}\n\n"
        f"AI ANSWER:\n{answer}\n\n"
        f"EVALUATION CRITERIA: {question['criteria']}\n\n"
        "Score this answer."
    )
    judge_messages = [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": judge_prompt},
    ]

    print("  → Calling Groq for judgment…")
    try:
        judge_raw = _groq_call(client, judge_messages, max_tokens=300)
        # Strip markdown code fences if present
        judge_raw = judge_raw.strip()
        if judge_raw.startswith("```"):
            judge_raw = judge_raw.split("```")[-2] if "```" in judge_raw[3:] else judge_raw[3:]
        judge_raw = judge_raw.strip()
        scores = json.loads(judge_raw)
    except Exception as e:
        scores = {
            "error": f"Judge parse failed: {e}",
            "raw": judge_raw if "judge_raw" in dir() else "",
        }

    return {
        "id": question["id"],
        "category": question["category"],
        "question": q_text,
        "answer": answer,
        "chunks_retrieved": len(results),
        "chunk_sources": [
            {
                "country": c.get("country"),
                "year": c.get("year"),
                "doc_type": c.get("doc_type"),
                "score": c.get("score"),
            }
            for c in results[:3]
        ],
        "scores": scores,
        "error": None,
    }


def run_search_test(model, index, chunks, question: dict) -> dict:
    """Run a semantic search test and check automated pass/fail criteria."""
    test_type = question.get("test_type", "search")
    query = question["query"]

    filter_doc_type = question.get("filter_doc_type")
    filter_year_min = question.get("filter_year_min")

    results = _semantic_search(
        model,
        index,
        chunks,
        query,
        top_k=8,
        filter_doc_type=filter_doc_type,
        filter_year_min=filter_year_min,
    )

    checks = {}

    if test_type == "search":
        checks["retrieval_hit"] = len(results) > 0
        checks["scores_in_range"] = all(0 <= r["score"] <= 1.0 for r in results)
        checks["top_score_reasonable"] = (results[0]["score"] > 0.2) if results else False

    elif test_type == "search_filter":
        checks["retrieval_hit"] = len(results) > 0
        if filter_doc_type:
            checks["filter_doc_type_respected"] = all(
                r.get("doc_type") == filter_doc_type for r in results
            )
        if filter_year_min:
            checks["filter_year_respected"] = all(
                (r.get("year") or 0) >= filter_year_min for r in results
            )

    elif test_type == "search_empty":
        # Off-topic — scores should be low
        max_score = max((r["score"] for r in results), default=0.0)
        checks["off_topic_low_score"] = max_score < SEARCH_SCORE_THRESHOLD
        checks["max_score"] = round(max_score, 4)

    passed = all(v for k, v in checks.items() if isinstance(v, bool))

    return {
        "id": question["id"],
        "category": question["category"],
        "test_type": test_type,
        "query": query,
        "results_count": len(results),
        "top_results": [
            {
                "country": r.get("country"),
                "year": r.get("year"),
                "doc_type": r.get("doc_type"),
                "score": round(r["score"], 4),
            }
            for r in results[:3]
        ],
        "checks": checks,
        "passed": passed,
        "error": None,
    }


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    print("=" * 60)
    print("Phase 3 Evaluation — RAG + Semantic Search")
    print(f"Started: {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Load data
    if not DATA_PATH.exists():
        print(f"ERROR: {DATA_PATH} not found.")
        sys.exit(1)
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df):,} documents from CSV.")

    # Load knowledge base
    print("Loading knowledge base…")
    index, chunks = _load_kb()
    if not chunks:
        print("ERROR: Knowledge base not found. Run build_knowledge_base.py first.")
        sys.exit(1)
    print(f"  FAISS index: {index.ntotal:,} vectors")
    print(f"  Chunks metadata: {len(chunks):,} chunks")

    # Load embedding model
    print("Loading embedding model…")
    model = _load_embed_model()
    if model is None:
        print("ERROR: sentence-transformers not installed.")
        sys.exit(1)
    print("  Model loaded: all-mpnet-base-v2")

    # Load Groq
    api_key = _get_groq_api_key()
    from groq import Groq

    client = Groq(api_key=api_key)

    # Load test questions
    if not TEST_SET_PATH.exists():
        print(f"ERROR: {TEST_SET_PATH} not found.")
        sys.exit(1)
    questions = []
    with open(TEST_SET_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    print(f"Loaded {len(questions)} test questions.\n")

    # Separate RAG questions from search tests
    rag_questions = [q for q in questions if q.get("test_type") is None]
    search_tests = [q for q in questions if q.get("test_type") is not None]

    results_all = []

    # ── Run RAG answer evaluations ──
    print("─" * 60)
    print(f"RAG Answer Evaluation ({len(rag_questions)} questions)")
    print("─" * 60)

    for q in rag_questions:
        print(f"\n[{q['id']}] {q['category'].upper()}")
        print(f"  Q: {q['question'][:80]}…" if len(q["question"]) > 80 else f"  Q: {q['question']}")
        result = run_rag_question(client, model, index, chunks, df, q)
        results_all.append(result)

        scores = result.get("scores", {})
        if scores and "error" not in scores:
            dims = ["accuracy", "relevance", "groundedness", "completeness", "citation"]
            avg = sum(scores.get(d, 0) for d in dims) / len(dims)
            score_str = "  ".join(f"{d[:3].upper()}:{scores.get(d, '?')}" for d in dims)
            status = "✅ PASS" if avg >= PASS_THRESHOLD else "⚠ LOW"
            print(f"  {score_str}  avg:{avg:.2f}  {status}")
            print(f"  Chunks: {result['chunks_retrieved']}  Notes: {scores.get('notes', '')[:60]}")
        else:
            print(f"  ⚠ Judge error or no scores: {scores}")

    # ── Run semantic search tests ──
    print(f"\n{'─' * 60}")
    print(f"Semantic Search Tests ({len(search_tests)} tests)")
    print("─" * 60)

    for q in search_tests:
        print(f"\n[{q['id']}] {q['category'].upper()} ({q.get('test_type', '')})")
        print(f"  Query: {q['query'][:80]}")
        result = run_search_test(model, index, chunks, q)
        results_all.append(result)

        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"  Results: {result['results_count']}  {status}")
        for k, v in result["checks"].items():
            icon = "✅" if (v is True) else ("❌" if v is False else "ℹ")
            print(f"    {icon} {k}: {v}")

    # ── Summary ──
    print(f"\n{'=' * 60}")
    print("PHASE 3 EVALUATION SUMMARY")
    print("=" * 60)

    rag_results = [r for r in results_all if "scores" in r and r.get("scores")]
    search_results = [r for r in results_all if "passed" in r]

    # RAG summary
    print(f"\nRAG Answer Quality ({len(rag_results)} questions):")
    dims = ["accuracy", "relevance", "groundedness", "completeness", "citation"]
    dim_avgs = {}
    valid = [r for r in rag_results if r["scores"] and "error" not in r["scores"]]
    for d in dims:
        scores_d = [
            r["scores"].get(d, 0) for r in valid if isinstance(r["scores"].get(d), int | float)
        ]
        dim_avgs[d] = sum(scores_d) / len(scores_d) if scores_d else 0
        print(f"  {d.capitalize():<14}: {dim_avgs[d]:.2f}/5.0")

    overall_avg = sum(dim_avgs.values()) / len(dim_avgs) if dim_avgs else 0
    rag_pass = overall_avg >= PASS_THRESHOLD
    print(
        f"  {'Overall avg':<14}: {overall_avg:.2f}/5.0  {'✅ PASS' if rag_pass else '❌ FAIL'} (threshold: {PASS_THRESHOLD})"
    )

    # Search summary
    print(f"\nSemantic Search Quality ({len(search_results)} tests):")
    passed_count = sum(1 for r in search_results if r["passed"])
    print(f"  Passed: {passed_count}/{len(search_results)}")
    search_pass = passed_count == len(search_results)
    print(f"  Status: {'✅ PASS' if search_pass else '❌ FAIL (see details above)'}")

    overall_phase_pass = rag_pass and search_pass
    print(f"\nPhase 3 Overall: {'✅ PASS' if overall_phase_pass else '❌ FAIL'}")

    # ── Save results ──
    output = {
        "phase": 3,
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "summary": {
            "rag_questions": len(rag_questions),
            "search_tests": len(search_tests),
            "rag_overall_avg": round(overall_avg, 3),
            "rag_pass": rag_pass,
            "search_pass": search_pass,
            "phase_pass": overall_phase_pass,
            "dim_avgs": {k: round(v, 3) for k, v in dim_avgs.items()},
        },
        "results": results_all,
    }

    with open(RESULTS_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nResults saved to: {RESULTS_PATH}")
    print(f"Finished: {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
