#!/usr/bin/env python3
"""
Evaluation script — Phases 1 & 2 LLM Integration (CRPD Dashboard)
===================================================================
Scope:
  Phase 1 — AI Insights panel (Groq chat.completions, data-context summary)
  Phase 2 — Chat Q&A interface (multi-turn conversation, grounded answers)

What this measures (per plan Phase 5 criteria, scoped to pre-RAG phases):
  - Accuracy      : Is the answer factually grounded in the data context?
  - Relevance     : Does it directly address the question?
  - Groundedness  : No hallucinated stats, country names, or dates not in context?
  - Completeness  : Does it cover the key aspects of the question?
  (Scored 1–5 by LLM-as-judge, per plan §8.5)

Also measures:
  - Rate limit enforcement (SESSION_LIMIT guard)
  - Out-of-scope refusal behaviour
  - Multi-turn context retention

Output:
  LLM_Development/eval_results_phase1_2.json  — full per-question results
  (summary table printed to stdout)

Usage:
  python LLM_Development/evaluate_phases_1_2.py

  GROQ_API_KEY can be set as an environment variable or placed in
  .streamlit/secrets.toml (auto-detected).
"""

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys

import pandas as pd


# ── Path setup ───────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATA_PATH = PROJECT_ROOT / "data" / "crpd_reports.csv"
TEST_SET_PATH = Path(__file__).parent / "test_questions_phase1_2.jsonl"
RESULTS_PATH = Path(__file__).parent / "eval_results_phase1_2.json"

GROQ_MODEL = "llama-3.3-70b-versatile"

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


# ── Data context builder (standalone, no Streamlit dependency) ────────────────


def build_eval_context(df: pd.DataFrame) -> str:
    """Build a concise data context string from the CSV — mirrors src/llm.py logic."""
    parts = []

    n_docs = len(df)
    n_countries = df["country"].nunique() if "country" in df.columns else 0
    n_types = df["doc_type"].nunique() if "doc_type" in df.columns else 0

    year_range = ""
    if "year" in df.columns and not df["year"].dropna().empty:
        yr_min = int(df["year"].min())
        yr_max = int(df["year"].max())
        year_range = f" spanning {yr_min}–{yr_max}"

    parts.append(
        f"DATASET OVERVIEW: {n_docs:,} CRPD documents from {n_countries} countries "
        f"and {n_types} document types{year_range}."
    )

    # Yearly submissions
    if "year" in df.columns:
        yearly = df.groupby("year").size().reset_index(name="count")
        if len(yearly) >= 2:
            peak = yearly.loc[yearly["count"].idxmax()]
            parts.append(
                f"SUBMISSIONS BY YEAR: Peak was {int(peak['year'])} with "
                f"{int(peak['count'])} documents. "
                f"Range: {int(yearly['count'].min())}–{int(yearly['count'].max())}."
            )

    # Regional breakdown
    if "region" in df.columns:
        region_counts = df["region"].value_counts().head(8)
        region_strs = [f"{r}: {c}" for r, c in region_counts.items()]
        parts.append(f"DOCUMENTS BY REGION: {', '.join(region_strs)}.")

    # Document types
    if "doc_type" in df.columns:
        type_counts = df["doc_type"].value_counts()
        type_strs = [f"{t}: {c}" for t, c in type_counts.items()]
        parts.append(f"DOCUMENT TYPES: {', '.join(type_strs)}.")

    # Model framing (if columns exist)
    if "medical_score" in df.columns and "rights_score" in df.columns:
        by_year = (
            df.groupby("year")[["medical_score", "rights_score"]]
            .mean()
            .reset_index()
            .sort_values("year")
        )
        if len(by_year) >= 2:
            first = by_year.iloc[0]
            last = by_year.iloc[-1]
            parts.append(
                f"MODEL FRAMING: Rights-based score went from "
                f"{first['rights_score']:.2f} in {int(first['year'])} to "
                f"{last['rights_score']:.2f} in {int(last['year'])}."
            )

    return "\n\n".join(parts)


# ── Groq client (direct — no st.secrets dependency) ──────────────────────────


def _groq_call(client, messages: list[dict], max_tokens: int = 600) -> str:
    """Make a single Groq API call and return the text content."""
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


# ── System prompts ────────────────────────────────────────────────────────────

CRPD_SYSTEM_PROMPT = (
    "You are an expert research analyst for the Institute on Disability and Public "
    "Policy (IDPP) at American University. You assist researchers, policymakers, "
    "and advocates analyzing CRPD reporting data.\n\n"
    "Rules:\n"
    "- Answer ONLY using the data context provided.\n"
    "- Never invent statistics, country names, or document references.\n"
    "- Cite specific countries, years, and document types when referencing findings.\n"
    "- If context is insufficient to answer, say so explicitly.\n"
    "- Use formal, accessible language appropriate for policy audiences.\n"
    "- Frame answers through a disability rights lens.\n"
    "- Keep responses concise: 3–4 bullet points for insights, under 200 words total."
)

JUDGE_SYSTEM_PROMPT = (
    "You are an impartial evaluator assessing the quality of AI-generated answers "
    "about CRPD (Convention on the Rights of Persons with Disabilities) data.\n\n"
    "Score each answer on 4 dimensions, each from 1 (very poor) to 5 (excellent):\n"
    "- accuracy: Is the answer factually grounded in the provided data context? "
    "Does it avoid inventing statistics, country names, or dates not in the context?\n"
    "- relevance: Does the answer directly address what was asked?\n"
    "- groundedness: Is every claim supported by the data context? "
    "Flag any hallucinated reference not found in the context.\n"
    "- completeness: Does it cover the key aspects of the question?\n\n"
    "Also note: was the answer appropriate for out-of-scope or RAG-requiring questions "
    "(did it correctly decline or acknowledge limitations)?\n\n"
    'Respond ONLY with valid JSON: {"accuracy": N, "relevance": N, '
    '"groundedness": N, "completeness": N, "notes": "brief comment"}'
)


# ── Phase 1 evaluation ────────────────────────────────────────────────────────


def run_phase1_question(client, data_context: str, question: dict) -> dict:
    """Run a single Phase 1 AI Insights question through Groq."""
    prompt = (
        f"{data_context}\n\n"
        "Based on the data above, provide 3–4 key insights about CRPD reporting "
        "patterns. Each insight should be a single clear sentence referencing "
        "specific numbers from the data. Format as bullet points."
    )
    messages = [
        {"role": "system", "content": CRPD_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    try:
        answer = _groq_call(client, messages, max_tokens=400)
        return {"answer": answer, "error": None}
    except Exception as e:
        return {"answer": None, "error": str(e)}


# ── Phase 2 evaluation ────────────────────────────────────────────────────────

CHAT_SYSTEM_PROMPT = (
    "You are an expert CRPD research assistant for IDPP at American University.\n\n"
    "You help researchers explore CRPD reporting data through conversation. "
    "You have access to aggregated statistics from the dashboard's current view.\n\n"
    "Rules:\n"
    "- Answer ONLY using the data context provided.\n"
    "- Never invent statistics, country names, or document references.\n"
    "- If the data context is insufficient, say so explicitly.\n"
    "- Use formal, accessible language appropriate for policy audiences.\n"
    "- Frame answers through a disability rights lens.\n"
    "- Be concise — aim for 2–4 paragraphs per response."
)


def run_phase2_question(
    client,
    data_context: str,
    question: dict,
    prior_turn: dict | None = None,
) -> dict:
    """Run a single Phase 2 chat question (optionally with prior turn for multi-turn)."""
    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Here is the current CRPD dashboard data:\n\n{data_context}\n\n"
            "Use this data to answer my questions. Acknowledge briefly.",
        },
        {
            "role": "assistant",
            "content": "I have the current CRPD dataset context. Please go ahead with your question.",
        },
    ]

    # For multi-turn turn 2: inject the prior turn
    if prior_turn and prior_turn.get("answer"):
        messages.append({"role": "user", "content": prior_turn["question"]})
        messages.append({"role": "assistant", "content": prior_turn["answer"]})

    messages.append({"role": "user", "content": question["question"]})

    try:
        answer = _groq_call(client, messages, max_tokens=600)
        return {"answer": answer, "error": None}
    except Exception as e:
        return {"answer": None, "error": str(e)}


# ── LLM-as-judge ─────────────────────────────────────────────────────────────


def judge_answer(client, data_context: str, question: dict, answer: str) -> dict:
    """Use Groq as judge to score an answer on 4 dimensions."""
    judge_prompt = (
        f"DATA CONTEXT:\n{data_context}\n\n"
        f"QUESTION: {question['question']}\n\n"
        f"EXPECTED CRITERIA: {question['criteria']}\n\n"
        f"ANSWER TO EVALUATE:\n{answer}\n\n"
        "Score this answer on the 4 dimensions described in your instructions."
    )
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": judge_prompt},
    ]
    try:
        raw = _groq_call(client, messages, max_tokens=200)
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        scores = json.loads(raw.strip())
        return scores
    except Exception as e:
        return {
            "accuracy": 0,
            "relevance": 0,
            "groundedness": 0,
            "completeness": 0,
            "notes": f"Judge parse error: {e}",
        }


# ── Rate-limit enforcement test ───────────────────────────────────────────────


def test_rate_limit_guard() -> dict:
    """Verify the rate limit constant and guard logic in src/llm.py."""
    result = {"passed": False, "details": ""}
    try:
        # _check_rate_limit uses st.session_state — simulate via monkeypatching
        import streamlit as st

        from src.llm import SESSION_LIMIT, _check_rate_limit

        st.session_state["llm_call_count"] = SESSION_LIMIT  # at limit
        at_limit = not _check_rate_limit()

        st.session_state["llm_call_count"] = SESSION_LIMIT - 1  # one below
        under_limit = _check_rate_limit()

        result["passed"] = at_limit and under_limit
        result["details"] = (
            f"SESSION_LIMIT={SESSION_LIMIT}. "
            f"Guard correctly blocks at limit: {at_limit}. "
            f"Guard correctly allows under limit: {under_limit}."
        )
    except Exception as e:
        result["details"] = f"Error: {e}"
    return result


# ── Main runner ───────────────────────────────────────────────────────────────


def main():
    print("=" * 70)
    print("CRPD Dashboard — LLM Evaluation: Phases 1 & 2")
    print(f"Run date: {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # 1. Load data
    if not DATA_PATH.exists():
        print(f"ERROR: Dataset not found at {DATA_PATH}")
        sys.exit(1)
    df = pd.read_csv(DATA_PATH)
    data_context = build_eval_context(df)
    print(f"\n✓ Loaded {len(df):,} documents from CSV")
    print(f"  Data context ({len(data_context)} chars):")
    for line in data_context.split("\n\n"):
        print(f"    {line[:90]}...")

    # 2. Load test questions
    if not TEST_SET_PATH.exists():
        print(f"ERROR: Test set not found at {TEST_SET_PATH}")
        sys.exit(1)
    questions = []
    with open(TEST_SET_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    print(f"\n✓ Loaded {len(questions)} test questions")

    # 3. Init Groq client
    try:
        api_key = _get_groq_api_key()
        from groq import Groq

        client = Groq(api_key=api_key)
        print("✓ Groq client initialized")
    except Exception as e:
        print(f"ERROR: Could not init Groq client: {e}")
        sys.exit(1)

    # 4. Run rate-limit guard test
    print("\n── Functional Tests ──────────────────────────────────────────────")
    rl_result = test_rate_limit_guard()
    status = "PASS" if rl_result["passed"] else "FAIL"
    print(f"  Rate limit guard: [{status}] {rl_result['details']}")

    # 5. Run test questions
    print("\n── Running Test Questions ────────────────────────────────────────")
    results = []
    # Track multi-turn prior turns by question ID
    prior_turns: dict[str, dict] = {}

    phase1_qs = [q for q in questions if q["phase"] == 1]
    phase2_qs = [q for q in questions if q["phase"] == 2]

    # Phase 1 questions
    for q in phase1_qs:
        print(f"  [{q['id']}] Phase 1 | {q['category']} | {q['question'][:60]}...")
        run_result = run_phase1_question(client, data_context, q)
        answer = run_result.get("answer") or ""
        error = run_result.get("error")

        scores = {}
        if answer:
            scores = judge_answer(client, data_context, q, answer)
            avg = (
                scores.get("accuracy", 0)
                + scores.get("relevance", 0)
                + scores.get("groundedness", 0)
                + scores.get("completeness", 0)
            ) / 4
            print(
                f"         → Avg score: {avg:.2f}/5.0 "
                f"(acc={scores.get('accuracy')}, rel={scores.get('relevance')}, "
                f"gnd={scores.get('groundedness')}, cmp={scores.get('completeness')})"
            )
        else:
            print(f"         → ERROR: {error}")

        results.append(
            {
                "id": q["id"],
                "phase": q["phase"],
                "category": q["category"],
                "difficulty": q.get("difficulty", ""),
                "question": q["question"],
                "criteria": q["criteria"],
                "answer": answer,
                "error": error,
                "scores": scores,
            }
        )

    # Phase 2 questions
    for q in phase2_qs:
        category = q.get("category", "")
        is_multiturn_t2 = category == "multiturn_t2"
        prior_id = q.get("follows")
        prior = prior_turns.get(prior_id) if prior_id else None

        label = f"turn {q.get('turn', 1)}" if q.get("multiturn") else "single"
        print(f"  [{q['id']}] Phase 2 | {category} ({label}) | {q['question'][:55]}...")

        run_result = run_phase2_question(
            client,
            data_context,
            q,
            prior_turn=prior if is_multiturn_t2 else None,
        )
        answer = run_result.get("answer") or ""
        error = run_result.get("error")

        # Store as prior for any follow-up turns
        prior_turns[q["id"]] = {"question": q["question"], "answer": answer}

        scores = {}
        if answer:
            scores = judge_answer(client, data_context, q, answer)
            avg = (
                scores.get("accuracy", 0)
                + scores.get("relevance", 0)
                + scores.get("groundedness", 0)
                + scores.get("completeness", 0)
            ) / 4
            print(
                f"         → Avg score: {avg:.2f}/5.0 "
                f"(acc={scores.get('accuracy')}, rel={scores.get('relevance')}, "
                f"gnd={scores.get('groundedness')}, cmp={scores.get('completeness')})"
            )
        else:
            print(f"         → ERROR: {error}")

        results.append(
            {
                "id": q["id"],
                "phase": q["phase"],
                "category": category,
                "difficulty": q.get("difficulty", ""),
                "question": q["question"],
                "criteria": q["criteria"],
                "answer": answer,
                "error": error,
                "scores": scores,
            }
        )

    # 6. Compute aggregate metrics
    print("\n── Summary ───────────────────────────────────────────────────────")
    scored = [r for r in results if r["scores"] and r["scores"].get("accuracy", 0) > 0]
    errors = [r for r in results if r["error"]]

    def _avg_dim(dim: str) -> float:
        vals = [r["scores"].get(dim, 0) for r in scored if dim in r["scores"]]
        return sum(vals) / len(vals) if vals else 0.0

    metrics = {
        "total_questions": len(results),
        "answered": len(scored),
        "errors": len(errors),
        "avg_accuracy": round(_avg_dim("accuracy"), 2),
        "avg_relevance": round(_avg_dim("relevance"), 2),
        "avg_groundedness": round(_avg_dim("groundedness"), 2),
        "avg_completeness": round(_avg_dim("completeness"), 2),
        "overall_avg": round(
            (
                _avg_dim("accuracy")
                + _avg_dim("relevance")
                + _avg_dim("groundedness")
                + _avg_dim("completeness")
            )
            / 4,
            2,
        ),
    }

    print(f"  Questions run:    {metrics['total_questions']}")
    print(f"  Answered:         {metrics['answered']}")
    print(f"  Errors:           {metrics['errors']}")
    print(f"  Avg Accuracy:     {metrics['avg_accuracy']:.2f}/5.0")
    print(f"  Avg Relevance:    {metrics['avg_relevance']:.2f}/5.0")
    print(f"  Avg Groundedness: {metrics['avg_groundedness']:.2f}/5.0")
    print(f"  Avg Completeness: {metrics['avg_completeness']:.2f}/5.0")
    print(f"  OVERALL AVG:      {metrics['overall_avg']:.2f}/5.0")

    # Evaluate against minimum targets
    targets = {
        "avg_accuracy": 3.5,
        "avg_relevance": 3.5,
        "avg_groundedness": 3.5,
        "overall_avg": 3.5,
    }
    all_pass = True
    print("\n  Target thresholds (min 3.5/5.0):")
    for dim, target in targets.items():
        val = metrics[dim]
        status = "PASS" if val >= target else "FAIL"
        if val < target:
            all_pass = False
        print(f"    {dim:25s} {val:.2f}  [{status}]")

    print(f"\n  EVALUATION: {'✅ PASS' if all_pass else '❌ FAIL — review low-scoring questions'}")

    # 7. Save results
    output = {
        "run_timestamp": datetime.now(tz=UTC).isoformat(),
        "model": GROQ_MODEL,
        "data_context_preview": data_context[:500],
        "functional_tests": {"rate_limit_guard": rl_result},
        "metrics": metrics,
        "targets": targets,
        "passed": all_pass,
        "questions": results,
    }
    with open(RESULTS_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n✓ Full results saved to: {RESULTS_PATH}")
    print("=" * 70)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
