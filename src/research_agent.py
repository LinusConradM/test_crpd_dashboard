"""CRPD Research Pipeline -- sequential agent chain."""

from __future__ import annotations

from datetime import UTC, datetime
import re
import time

from src.llm import call_ollama_uncached, call_research_llm, semantic_search
from src.research_prompts import (
    PLANNER_PROMPT,
    REVIEWER_PROMPT,
    SYNTHESIZER_PROMPT,
    WRITER_PROMPT,
)


def _parse_sub_questions(planner_output: str) -> list[str]:
    """Extract numbered sub-questions from planner LLM output."""
    lines = planner_output.strip().split("\n")
    questions = []
    for line in lines:
        cleaned = re.sub(r"^\d+[\.\)]\s*", "", line.strip())
        if cleaned and len(cleaned) > 10:
            questions.append(cleaned)
    return questions[:5]  # Cap at 5


def _format_chunks_for_synthesis(chunks: list[dict], sub_question: str) -> str:
    """Format retrieved chunks as context for the Synthesizer."""
    if not chunks:
        return f"Sub-question: {sub_question}\n\nNo relevant excerpts found."
    context_parts = [f"Sub-question: {sub_question}\n\nDocument excerpts:\n"]
    for i, chunk in enumerate(chunks, 1):
        country = chunk.get("country", "Unknown")
        doc_type = chunk.get("doc_type", "Unknown")
        year = chunk.get("year", "Unknown")
        text = chunk.get("text", "")[:600]  # Cap excerpt length
        context_parts.append(f"[{i}] ({country}, {doc_type}, {year}):\n{text}\n")
    return "\n".join(context_parts)


def run_research_pipeline(query: str, tier: str = "free", df=None, article_presets=None) -> dict:
    """Execute the full research pipeline. Returns structured result dict.

    Parameters
    ----------
    query : str
        User's research question.
    tier : str
        "free" routes to Ollama (local), "premium" routes to Claude (budgeted).
    df : pandas.DataFrame | None
        Full CRPD dataset for analyst computations.
    article_presets : dict | None
        Article dictionary for keyword-based analysis.
    """
    start_time = time.time()
    state: dict = {
        "query": query,
        "tier": tier,
        "sub_questions": [],
        "chunks": {},  # {sq_index: [chunk_dicts]}
        "all_chunks": [],  # deduplicated flat list
        "syntheses": [],
        "analyst": None,
        "review_status": "",
        "briefing": "",
        "llm_calls": 0,
        "error": None,
        "steps_completed": [],
    }

    # --- Step 1: Planner ---
    planner_result = call_research_llm(PLANNER_PROMPT, query, agent_role="planner", tier=tier)
    state["llm_calls"] += 1
    if planner_result["error"]:
        state["error"] = f"Planner failed: {planner_result['error']}"
        return state

    sub_questions = _parse_sub_questions(planner_result["text"])
    if not sub_questions:
        state["error"] = "Planner produced no sub-questions. Try rephrasing your query."
        return state
    state["sub_questions"] = sub_questions
    state["steps_completed"].append("planner")

    # --- Step 2: Retriever (no LLM -- pure FAISS) ---
    seen_chunk_ids: set[str] = set()
    for i, sq in enumerate(sub_questions):
        chunks = semantic_search(sq, top_k=8)
        # Deduplicate across sub-questions
        unique_chunks = []
        for c in chunks:
            cid = c.get(
                "chunk_id",
                f"{c.get('country')}_{c.get('year')}_{c.get('chunk_index')}",
            )
            if cid not in seen_chunk_ids:
                seen_chunk_ids.add(cid)
                unique_chunks.append(c)
                state["all_chunks"].append(c)
        state["chunks"][i] = unique_chunks

    if not state["all_chunks"]:
        state["error"] = (
            "No relevant document excerpts found for any sub-question. "
            "The knowledge base may not cover this topic. "
            "Try Semantic Search or Country Profiles for alternative exploration."
        )
        state["steps_completed"].append("retriever")
        return state
    state["steps_completed"].append("retriever")

    # --- Step 2.5: Analyst (no LLM -- pure computation) ---
    if df is not None and article_presets is not None and state["all_chunks"]:
        # Filter df to countries found in retrieved chunks
        _analyst_countries = list(set(c.get("country", "") for c in state["all_chunks"]))
        _analyst_df = df[df["country"].isin(_analyst_countries)]

        if len(_analyst_df) > 0:
            from src.analysis import article_frequency, keyword_counts, model_shift_table

            # Article coverage for relevant countries
            _af = article_frequency(_analyst_df, article_presets, groupby="country")
            _af_summary = ""
            if not _af.empty:
                _top_articles = _af.groupby("article")["count"].sum().nlargest(5)
                _af_summary = "Top 5 articles by keyword frequency:\n" + "\n".join(
                    f"  - {art}: {count} mentions" for art, count in _top_articles.items()
                )

            # Model shift (rights vs medical)
            _mt = model_shift_table(_analyst_df)
            _mt_summary = ""
            if len(_mt) > 0:
                _r = _mt["rights"].sum()
                _m = _mt["medical"].sum()
                _total = _r + _m
                if _total > 0:
                    _rights_pct = round(_r / _total * 100, 1)
                    _mt_summary = (
                        f"Rights-based keyword share: {_rights_pct}% "
                        f"(out of {_total} total model keyword matches across "
                        f"{len(_analyst_df)} documents from "
                        f"{len(_analyst_countries)} States Parties)"
                    )

            # Top keywords
            _kw = keyword_counts(_analyst_df, top_n=10)
            _kw_summary = ""
            if not _kw.empty:
                _kw_summary = "Most frequent terms: " + ", ".join(
                    f"{row['term']} ({row['freq']})" for _, row in _kw.head(5).iterrows()
                )

            state["analyst"] = {
                "article_freq_summary": _af_summary,
                "model_shift_summary": _mt_summary,
                "keyword_summary": _kw_summary,
                "n_docs_analyzed": len(_analyst_df),
                "n_countries_analyzed": len(_analyst_countries),
                "invoked": True,
            }
            state["steps_completed"].append("analyst")

    # --- Step 3: Synthesizer ---
    # Build analyst context string once (shared across sub-questions)
    _analyst_context = ""
    if state.get("analyst") and state["analyst"].get("invoked"):
        _a = state["analyst"]
        _analyst_context = "\n\nQuantitative context (from keyword analysis):\n"
        if _a["article_freq_summary"]:
            _analyst_context += _a["article_freq_summary"] + "\n"
        if _a["model_shift_summary"]:
            _analyst_context += _a["model_shift_summary"] + "\n"
        if _a["keyword_summary"]:
            _analyst_context += _a["keyword_summary"] + "\n"

    syntheses = []
    for i, sq in enumerate(sub_questions):
        chunks = state["chunks"].get(i, [])
        context = _format_chunks_for_synthesis(chunks, sq)
        context += _analyst_context
        synth_result = call_research_llm(
            SYNTHESIZER_PROMPT, context, agent_role="synthesizer", tier=tier
        )
        state["llm_calls"] += 1
        if synth_result["error"]:
            syntheses.append(f"Synthesis unavailable for: {sq}")
        else:
            syntheses.append(synth_result["text"])
    state["syntheses"] = syntheses
    state["steps_completed"].append("synthesizer")

    # --- Step 4: Reviewer ---
    combined = "\n\n".join(
        f"## Sub-question {i + 1}: {sq}\n{synth}"
        for i, (sq, synth) in enumerate(zip(sub_questions, syntheses, strict=False))
    )
    review_result = call_research_llm(REVIEWER_PROMPT, combined, agent_role="reviewer", tier=tier)
    state["llm_calls"] += 1

    if review_result["error"]:
        state["review_status"] = "REVIEW_UNAVAILABLE"
    elif "REVISION_NEEDED" in review_result["text"].upper():
        # One revision attempt
        revision_prompt = (
            f"The reviewer flagged these issues:\n{review_result['text']}\n\n"
            f"Please revise the following synthesis to address all issues:\n\n"
            f"{combined}"
        )
        revision_result = call_ollama_uncached(SYNTHESIZER_PROMPT, revision_prompt)
        state["llm_calls"] += 1
        if not revision_result["error"]:
            # Re-review (uncached — revision content differs from original)
            re_review = call_ollama_uncached(REVIEWER_PROMPT, revision_result["text"])
            state["llm_calls"] += 1
            if not re_review["error"] and "APPROVED" in re_review["text"].upper():
                state["review_status"] = "APPROVED"
                combined = revision_result["text"]
            else:
                state["review_status"] = "APPROVED_WITH_CAVEATS"
        else:
            state["review_status"] = "APPROVED_WITH_CAVEATS"
    else:
        state["review_status"] = "APPROVED"
    state["steps_completed"].append("reviewer")

    # --- Step 5: Writer ---
    writer_context = (
        f"User query: {query}\n\n"
        f"Approved synthesis:\n{combined}\n\n"
        f"Total document excerpts retrieved: {len(state['all_chunks'])}\n"
        f"States Parties represented: "
        f"{len(set(c.get('country', '') for c in state['all_chunks']))}"
    )
    writer_context += _analyst_context
    writer_result = call_research_llm(WRITER_PROMPT, writer_context, agent_role="writer", tier=tier)
    state["llm_calls"] += 1
    if writer_result["error"]:
        state["briefing"] = combined  # Fallback to raw synthesis
        state["error"] = "Writer unavailable -- showing raw synthesis."
    else:
        state["briefing"] = writer_result["text"]
    state["steps_completed"].append("writer")

    # --- Metadata ---
    state["duration_seconds"] = round(time.time() - start_time, 1)
    state["timestamp"] = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")

    return state
