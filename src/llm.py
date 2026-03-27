"""LLM runtime module for the CRPD Dashboard.

Handles Ollama (local) and Groq (cloud) model routing, data context
building, session rate limiting, and AI insight generation.

Phase 1: Ollama (configured via OLLAMA_MODEL) for AI Insights panel (local, free).
Phase 2+: Groq (configured via GROQ_MODEL) for chat and reports (free tier).
Phase 3+: FAISS semantic search + RAG grounding for chat and document explorer.
"""

from datetime import UTC, datetime
import os
from pathlib import Path

import streamlit as st


# ── Model Configuration (single source of truth) ────────────────────────────
# Override via environment variables for deployment flexibility:
#   OLLAMA_MODEL=mistral  GROQ_MODEL=llama-3.3-70b-versatile  streamlit run app.py

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
CLAUDE_SONNET = "claude-sonnet-4-20250514"
CLAUDE_HAIKU = "claude-haiku-4-5-20251001"
EMBEDDING_MODEL = "all-mpnet-base-v2"


# ── Generic Ollama call ───────────────────────────────────────────────────────


@st.cache_data(show_spinner=False)
def _cached_ollama_call(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
) -> dict:
    """Cached Ollama call — identical inputs return cached result without re-calling the model."""
    try:
        import ollama

        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": temperature, "num_predict": max_tokens},
            keep_alive="10m",  # Keep model loaded for 10 minutes between calls
        )
        return {"text": response["message"]["content"], "error": None}
    except Exception as e:
        return {"text": "", "error": str(e)}


def call_ollama(
    system_prompt: str,
    user_prompt: str,
    model: str = OLLAMA_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 800,
) -> dict:
    """Generic Ollama LLM call with prompt caching.

    Two caching layers:
    1. @st.cache_data — identical (system_prompt, user_prompt) pairs
       return cached results without re-calling the model.
    2. keep_alive="10m" — Ollama keeps the model loaded in memory for
       10 minutes, avoiding cold-load latency between pipeline steps.
    """
    return _cached_ollama_call(system_prompt, user_prompt, model, temperature, max_tokens)


def call_ollama_uncached(
    system_prompt: str,
    user_prompt: str,
    model: str = OLLAMA_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 800,
) -> dict:
    """Uncached Ollama call — for cases where caching would be inappropriate
    (e.g., revision loops where the same prompt should produce a different result)."""
    try:
        import ollama

        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": temperature, "num_predict": max_tokens},
            keep_alive="10m",
        )
        return {"text": response["message"]["content"], "error": None}
    except Exception as e:
        return {"text": "", "error": str(e)}


# ── Budgeted Claude client (Phase 3 — Premium tier) ─────────────────────────

# Model routing: simple tasks → Haiku, complex tasks → Sonnet
CLAUDE_MODELS = {
    "haiku": CLAUDE_HAIKU,
    "sonnet": CLAUDE_SONNET,
}

# Monthly budget in USD — starts conservative, adjust based on usage data
_MONTHLY_BUDGET_USD = 50.0

# Cost per million tokens (input / output) as of 2025
_MODEL_COSTS = {
    "haiku": {"input": 0.25, "output": 1.25},
    "sonnet": {"input": 3.0, "output": 15.0},
}

# Agent → model routing: simple tasks use Haiku, complex use Sonnet
AGENT_MODEL_MAP = {
    "planner": "haiku",  # Structured decomposition — low reasoning
    "synthesizer": "sonnet",  # Multi-doc synthesis — needs nuance
    "reviewer": "haiku",  # 7-point checklist — binary checks
    "writer": "sonnet",  # Structured prose output — needs quality
}

_USAGE_STATE_KEY = "claude_usage_this_month"


def _get_monthly_usage() -> dict:
    """Get current month's Claude API usage from session state."""
    if _USAGE_STATE_KEY not in st.session_state:
        st.session_state[_USAGE_STATE_KEY] = {
            "month": datetime.now(tz=UTC).strftime("%Y-%m"),
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "request_count": 0,
        }
    # Reset if month changed
    current_month = datetime.now(tz=UTC).strftime("%Y-%m")
    if st.session_state[_USAGE_STATE_KEY]["month"] != current_month:
        st.session_state[_USAGE_STATE_KEY] = {
            "month": current_month,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "request_count": 0,
        }
    return st.session_state[_USAGE_STATE_KEY]


def _estimate_cost(input_tokens: int, output_tokens: int, model_tier: str) -> float:
    """Estimate cost in USD for a given token count and model tier."""
    costs = _MODEL_COSTS.get(model_tier, _MODEL_COSTS["sonnet"])
    return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1_000_000


def get_budget_status() -> dict:
    """Return current budget status for display in the UI."""
    usage = _get_monthly_usage()
    return {
        "spent": round(usage["total_cost_usd"], 4),
        "budget": _MONTHLY_BUDGET_USD,
        "remaining": round(_MONTHLY_BUDGET_USD - usage["total_cost_usd"], 4),
        "requests": usage["request_count"],
        "month": usage["month"],
        "pct_used": round(usage["total_cost_usd"] / _MONTHLY_BUDGET_USD * 100, 1)
        if _MONTHLY_BUDGET_USD > 0
        else 0,
    }


def call_claude(
    system_prompt: str,
    user_prompt: str,
    agent_role: str = "synthesizer",
    temperature: float = 0.3,
    max_tokens: int = 1200,
    use_cache: bool = True,
) -> dict:
    """Budgeted Claude API call with tiered model routing and prompt caching.

    Routes to Haiku or Sonnet based on agent_role (see AGENT_MODEL_MAP).
    Tracks usage against monthly budget. Blocks if budget exceeded.

    Parameters
    ----------
    system_prompt : str
        System instructions for the model.
    user_prompt : str
        User message / context.
    agent_role : str
        Pipeline agent name — maps to model tier via AGENT_MODEL_MAP.
    temperature : float
        Sampling temperature (0.0-1.0).
    max_tokens : int
        Maximum output tokens.
    use_cache : bool
        Enable Anthropic prompt caching on system prompt (90% cost savings
        for repeated system prompts within 5-minute window).

    Returns
    -------
    dict with keys: text, model, input_tokens, output_tokens, cost_usd,
    cache_hit, error
    """
    # Budget check
    usage = _get_monthly_usage()
    if usage["total_cost_usd"] >= _MONTHLY_BUDGET_USD:
        return {
            "text": "",
            "model": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "cache_hit": False,
            "error": (
                f"Monthly API budget exhausted "
                f"(${usage['total_cost_usd']:.2f} / ${_MONTHLY_BUDGET_USD:.2f}). "
                f"Budget resets next month."
            ),
        }

    # Model selection based on agent role
    model_tier = AGENT_MODEL_MAP.get(agent_role, "sonnet")
    model_id = CLAUDE_MODELS[model_tier]

    try:
        import anthropic

        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {
                "text": "",
                "model": model_id,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "cache_hit": False,
                "error": "ANTHROPIC_API_KEY not configured in st.secrets.",
            }

        client = anthropic.Anthropic(api_key=api_key)

        # Build system message with optional cache control
        system_block = [
            {
                "type": "text",
                "text": system_prompt,
                **({"cache_control": {"type": "ephemeral"}} if use_cache else {}),
            }
        ]

        response = client.messages.create(
            model=model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_block,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Extract usage
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cache_hit = getattr(response.usage, "cache_read_input_tokens", 0) > 0
        cost = _estimate_cost(input_tokens, output_tokens, model_tier)

        # Update usage tracking
        usage["total_input_tokens"] += input_tokens
        usage["total_output_tokens"] += output_tokens
        usage["total_cost_usd"] += cost
        usage["request_count"] += 1

        return {
            "text": response.content[0].text,
            "model": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
            "cache_hit": cache_hit,
            "error": None,
        }

    except Exception as e:
        return {
            "text": "",
            "model": model_id,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "cache_hit": False,
            "error": str(e),
        }


def call_research_llm(
    system_prompt: str,
    user_prompt: str,
    agent_role: str = "synthesizer",
    tier: str = "free",
) -> dict:
    """Route research LLM calls to Ollama (free) or Claude (premium).

    This is the single entry point for the research pipeline.
    Free tier uses local Ollama ($0 cost).
    Premium tier uses Claude with budgeted cost tracking.
    """
    if tier == "premium":
        return call_claude(system_prompt, user_prompt, agent_role=agent_role)
    return call_ollama(system_prompt, user_prompt)


# ── System prompt ────────────────────────────────────────────────────────────

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
    "- Frame answers through a disability rights lens — the shift from medical "
    "to rights-based models is a central theme of this research.\n"
    "- Keep responses concise: 3–4 bullet points for insights, under 200 words total."
)

# ── Rate limiting ────────────────────────────────────────────────────────────

SESSION_LIMIT = 20  # Maximum LLM calls per session
_RATE_KEY = "llm_call_count"


def _check_rate_limit():
    """Check session rate limit. Returns True if under limit."""
    if _RATE_KEY not in st.session_state:
        st.session_state[_RATE_KEY] = 0
    return st.session_state[_RATE_KEY] < SESSION_LIMIT


def _increment_call_count():
    """Increment the session call counter."""
    if _RATE_KEY not in st.session_state:
        st.session_state[_RATE_KEY] = 0
    st.session_state[_RATE_KEY] += 1


def get_remaining_calls():
    """Return number of LLM calls remaining in this session."""
    used = st.session_state.get(_RATE_KEY, 0)
    return max(0, SESSION_LIMIT - used)


# ── Brief-specific rate limiting (S2) ───────────────────────────────────────

BRIEF_SESSION_LIMIT = 10  # Separate budget for policy briefs
_BRIEF_RATE_KEY = "brief_call_count"


def _check_brief_rate_limit():
    """Check brief-specific rate limit."""
    if _BRIEF_RATE_KEY not in st.session_state:
        st.session_state[_BRIEF_RATE_KEY] = 0
    return st.session_state[_BRIEF_RATE_KEY] < BRIEF_SESSION_LIMIT


def _increment_brief_count():
    """Increment brief call counter."""
    if _BRIEF_RATE_KEY not in st.session_state:
        st.session_state[_BRIEF_RATE_KEY] = 0
    st.session_state[_BRIEF_RATE_KEY] += 1


def get_remaining_brief_calls():
    """Return number of brief generations remaining."""
    used = st.session_state.get(_BRIEF_RATE_KEY, 0)
    return max(0, BRIEF_SESSION_LIMIT - used)


# ── Client initialization ───────────────────────────────────────────────────


def get_groq_client():
    """Initialize and return a Groq API client using st.secrets."""
    from groq import Groq  # Lazy import — only needed for Phase 2+

    import os

    try:
        api_key = st.secrets.get("GROQ_API_KEY")
    except Exception:
        api_key = None

    api_key = api_key or os.environ.get("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY not found in secrets or environment variables")
    return Groq(api_key=api_key)


# ── Data context builder ────────────────────────────────────────────────────


def build_data_context(
    df,
    yearly_model_df=None,
    region_counts_df=None,
    yearly_counts_df=None,
    bump_df=None,
):
    """Build a concise text summary of the current dashboard state.

    This context is sent to the LLM instead of raw data — never pass
    the full DataFrame. Keeps prompt under ~600 words.

    Args:
        df: Current filtered DataFrame
        yearly_model_df: Rights vs Medical % by year (from area chart)
        region_counts_df: Document counts by region (from lollipop chart)
        yearly_counts_df: Document counts by year (from bar chart)
        bump_df: Article rank trajectories (from bump chart)

    Returns:
        str: Formatted data context for the LLM prompt
    """
    parts = []

    # Overview stats
    n_docs = len(df)
    n_countries = df["country"].nunique() if "country" in df.columns else 0
    n_types = df["doc_type"].nunique() if "doc_type" in df.columns else 0

    year_range = ""
    if "year" in df.columns and not df["year"].dropna().empty:
        yr_min = int(df["year"].min())
        yr_max = int(df["year"].max())
        year_range = f" spanning {yr_min}–{yr_max}"

    parts.append(
        f"DATASET OVERVIEW: {n_docs:,} CRPD documents from {n_countries} States Parties "
        f"and {n_types} document types{year_range}."
    )

    # Yearly submissions
    if yearly_counts_df is not None and len(yearly_counts_df) >= 2:
        peak_row = yearly_counts_df.loc[yearly_counts_df["count"].idxmax()]
        parts.append(
            f"SUBMISSIONS BY YEAR: Peak was {int(peak_row['year'])} "
            f"with {int(peak_row['count'])} documents. "
            f"Range: {int(yearly_counts_df['count'].min())}–{int(yearly_counts_df['count'].max())}."
        )

    # Model shift data
    if yearly_model_df is not None and len(yearly_model_df) >= 2:
        first = yearly_model_df.iloc[0]
        last = yearly_model_df.iloc[-1]
        parts.append(
            f"MODEL FRAMING: Rights-based language went from {first['Rights-Based']:.1f}% "
            f"in {int(first['year'])} to {last['Rights-Based']:.1f}% in {int(last['year'])}. "
            f"Medical-based: {first['Medical-Based']:.1f}% → {last['Medical-Based']:.1f}%."
        )

    # Regional breakdown
    if region_counts_df is not None and len(region_counts_df) >= 1:
        region_strs = [
            f"{row['region']}: {int(row['documents'])}" for _, row in region_counts_df.iterrows()
        ]
        parts.append(f"DOCUMENTS BY REGION: {', '.join(region_strs)}.")

    # Top article trends (bump chart)
    if bump_df is not None and len(bump_df) >= 2 and "rank" in bump_df.columns:
        max_year = bump_df["year"].max()
        top_now = bump_df[bump_df["year"] == max_year].sort_values("rank").head(5)
        article_strs = [f"#{int(row['rank'])} {row['article']}" for _, row in top_now.iterrows()]
        parts.append(f"TOP ARTICLES (latest year, by rank): {'; '.join(article_strs)}.")

    return "\n\n".join(parts)


# ── LLM call: Ollama (local) ────────────────────────────────────────────────


def generate_insights_local(data_context):
    """Generate AI insights using Ollama (configured via OLLAMA_MODEL).

    Args:
        data_context: Text summary from build_data_context()

    Returns:
        dict with keys:
            "text": str — the generated insight text
            "model": str — model name used
            "timestamp": str — ISO timestamp
            "error": str | None — error message if failed
    """
    import ollama  # Lazy import — avoids crash if not installed at startup

    if not _check_rate_limit():
        return {
            "text": None,
            "model": OLLAMA_MODEL,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "error": f"Session limit reached ({SESSION_LIMIT} calls). Refresh the page to reset.",
        }

    prompt = (
        f"{data_context}\n\n"
        "Based on the data above, provide 3–4 key insights about CRPD reporting "
        "patterns. Each insight should be a single clear sentence referencing "
        "specific numbers from the data. Format as bullet points."
    )

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": CRPD_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        _increment_call_count()
        return {
            "text": response["message"]["content"],
            "model": OLLAMA_MODEL,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "error": None,
        }
    except Exception as e:
        return {
            "text": None,
            "model": OLLAMA_MODEL,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "error": f"Ollama error: {e}",
        }


# ── LLM call: Groq (cloud) — for Phase 2+ ───────────────────────────────────


def ask_llm(context, question):
    """Send a question with context to Groq (configured via GROQ_MODEL).

    Args:
        context: Text context (data summary or RAG chunks)
        question: User's question

    Returns:
        dict with keys: "text", "model", "timestamp", "error"
    """
    if not _check_rate_limit():
        return {
            "text": None,
            "model": GROQ_MODEL,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "error": f"Session limit reached ({SESSION_LIMIT} calls). Refresh the page to reset.",
        }

    prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": CRPD_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        _increment_call_count()
        return {
            "text": response.choices[0].message.content,
            "model": GROQ_MODEL,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "error": None,
        }
    except Exception as e:
        return {
            "text": None,
            "model": GROQ_MODEL,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "error": f"Groq error: {e}",
        }


# ── Multi-turn chat: Groq (Phase 2) ─────────────────────────────────────────

# Chat-specific system prompt — slightly different from insights prompt
CHAT_SYSTEM_PROMPT = (
    "You are an expert CRPD research assistant for the Institute on Disability and Public "
    "Policy (IDPP) at American University.\n\n"
    "You help researchers, policymakers, and advocates explore CRPD reporting data "
    "through conversation. You have access to aggregated statistics from the dashboard's "
    "current filtered view.\n\n"
    "Rules:\n"
    "- Answer ONLY using the data context provided at the start of this conversation.\n"
    "- Never invent statistics, country names, or document references.\n"
    "- If the data context is insufficient, say so explicitly.\n"
    "- Use formal, accessible language appropriate for policy audiences.\n"
    "- Frame answers through a disability rights lens.\n"
    "- Be concise — aim for 2–4 paragraphs per response.\n"
    "- When users ask follow-up questions, refer back to the data context."
)

# STARTER_QUESTIONS removed — tab_chat.py owns the starter cards (_STARTER_CARDS).


def ask_llm_multiturn(data_context, chat_history):
    """Send a multi-turn conversation to Groq (configured via GROQ_MODEL).

    The data context is injected as the first user message so the model
    has it available throughout the conversation.

    Args:
        data_context: Text summary from build_data_context()
        chat_history: List of dicts [{"role": "user"|"assistant", "content": str}, ...]

    Returns:
        dict with keys: "text", "model", "timestamp", "error"
    """
    if not _check_rate_limit():
        return {
            "text": None,
            "model": GROQ_MODEL,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "error": f"Session limit reached ({SESSION_LIMIT} calls). Refresh the page to reset.",
        }

    # Build message list: system prompt → data context → conversation history
    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Here is the current CRPD dashboard data:\n\n{data_context}\n\n"
            "Use this data to answer my questions. Acknowledge briefly and wait for my question.",
        },
        {
            "role": "assistant",
            "content": "I have the current CRPD dataset context. Please go ahead with your question.",
        },
    ]
    messages.extend(chat_history)

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=600,
        )
        _increment_call_count()
        return {
            "text": response.choices[0].message.content,
            "model": GROQ_MODEL,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "error": None,
        }
    except Exception as e:
        return {
            "text": None,
            "model": GROQ_MODEL,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "error": f"Groq error: {e}",
        }


# ── Phase 3: RAG + Semantic Search ───────────────────────────────────────────

_FAISS_INDEX_PATH = Path("data") / "faiss_index.bin"
_CHUNKS_META_PATH = Path("data") / "chunks_metadata.json"
_MAX_CHUNK_WORDS = 300  # cap chunk text before including in LLM prompt

# RAG system prompt — grounding-first, citation-required
RAG_SYSTEM_PROMPT = (
    "You are an expert CRPD research assistant for the Institute on Disability and Public "
    "Policy (IDPP) at American University.\n\n"
    "You have been given excerpts from actual CRPD States Parties reports, parallel reports, "
    "and concluding observations. Answer the question using ONLY these excerpts.\n\n"
    "Rules:\n"
    "- Ground every claim in a specific source excerpt provided.\n"
    "- Cite sources by country, year, and document type (e.g., Kenya 2022 State Report).\n"
    "- Never invent facts not present in the provided excerpts.\n"
    "- If the excerpts are insufficient to answer fully, say so explicitly.\n"
    "- Use formal, accessible language appropriate for policy audiences.\n"
    "- Frame answers through a disability rights lens.\n"
    "- Be concise — aim for 2–4 paragraphs per response.\n"
    '- Always use "States Parties" (not "countries") when referring to CRPD member nations.\n'
    "- Distinguish between State Party claims and CRPD Committee assessments. "
    "Note which source type each finding comes from.\n"
    "- Never rank, rate, grade, or judge States Parties' compliance. "
    "Report what documents contain without evaluative judgments.\n"
    "- If the question is not about CRPD, disability rights, or UN treaty reporting, "
    'respond: "I can only answer questions about CRPD implementation and disability rights '
    "reporting. Try asking about a specific State Party's reporting, CRPD article coverage, "
    'or language patterns in treaty documents."'
)


@st.cache_resource
def load_embedding_model():
    """Load sentence-transformer embedding model (cached, loaded once at startup).

    Returns:
        SentenceTransformer instance, or None if sentence-transformers is not installed.
    """
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(EMBEDDING_MODEL)
    except ImportError:
        return None


@st.cache_resource
def load_search_index():
    """Load FAISS index and chunk metadata from disk (cached, loaded once at startup).

    Returns:
        tuple: (faiss.Index, list[dict]) or (None, []) if knowledge base not yet built.
    """
    import json

    if not _FAISS_INDEX_PATH.exists() or not _CHUNKS_META_PATH.exists():
        return None, []

    try:
        import faiss

        index = faiss.read_index(str(_FAISS_INDEX_PATH))
        with open(_CHUNKS_META_PATH) as f:
            chunks = json.load(f)
        return index, chunks
    except Exception as exc:
        st.warning(f"⚠️ Failed to load knowledge base: {exc}")
        return None, []


def check_index_freshness(chunks: list[dict], dataset_doc_count: int) -> dict:
    """Compare indexed document count against dataset to detect staleness.

    Args:
        chunks: Chunk metadata list from load_search_index().
        dataset_doc_count: Current document count from get_dataset_stats()['n_docs'].

    Returns:
        dict with keys: is_fresh (bool), indexed_docs (int), dataset_docs (int),
        missing_count (int).
    """
    if not chunks:
        return {
            "is_fresh": False,
            "indexed_docs": 0,
            "dataset_docs": dataset_doc_count,
            "missing_count": dataset_doc_count,
        }
    _indexed_docs = len({c.get("doc_id", "") for c in chunks})
    _missing = max(0, dataset_doc_count - _indexed_docs)
    return {
        "is_fresh": _missing == 0,
        "indexed_docs": _indexed_docs,
        "dataset_docs": dataset_doc_count,
        "missing_count": _missing,
    }


def semantic_search(
    query: str,
    top_k: int = 8,
    filter_country: str | None = None,
    filter_doc_type: str | None = None,
    filter_year_min: int | None = None,
    filter_year_max: int | None = None,
    max_per_country: int = 2,
) -> list[dict]:
    """Embed a query and retrieve top_k most relevant document chunks via FAISS.

    Uses IndexFlatIP (cosine similarity after L2 normalisation) over
    EMBEDDING_MODEL embeddings. Optional metadata filters are applied
    post-retrieval, so over-retrieval is used to fill the top_k quota.

    A per-country cap (max_per_country) ensures result diversity across
    States Parties. Set to 0 to disable the cap.

    Args:
        query: Natural language search query.
        top_k: Number of results to return. Capped at 10.
        filter_country: Restrict results to this country (exact match).
        filter_doc_type: Restrict results to this doc type (exact match).
        filter_year_min: Restrict results to documents from this year onward.
        filter_year_max: Restrict results to documents up to this year.
        max_per_country: Max chunks per country (0 = unlimited). Default 2.

    Returns:
        List of chunk dicts with keys: chunk_id, text, doc_id, country, year,
        doc_type, region, symbol, source_file, chunk_index, score.
        Returns [] if the knowledge base has not been built yet.
    """
    from collections import Counter

    import numpy as np

    top_k = min(top_k, 10)
    model = load_embedding_model()
    index, chunks = load_search_index()

    if model is None or index is None or not chunks:
        return []

    # Embed and L2-normalise for cosine similarity via inner product
    query_vec = model.encode([query], convert_to_numpy=True).astype("float32")
    norm = np.linalg.norm(query_vec, axis=1, keepdims=True)
    query_vec = query_vec / np.maximum(norm, 1e-10)

    # Over-retrieve to absorb post-filter and diversity losses
    _diversity_factor = 8 if max_per_country else 4
    k_retrieve = min(top_k * _diversity_factor, len(chunks))
    scores, indices = index.search(query_vec, k_retrieve)

    results = []
    _country_counts: Counter = Counter()
    for score, idx in zip(scores[0], indices[0], strict=False):
        if idx < 0 or idx >= len(chunks):
            continue
        chunk = chunks[idx]

        # Metadata filters
        if filter_country and chunk.get("country") != filter_country:
            continue
        if filter_doc_type and chunk.get("doc_type") != filter_doc_type:
            continue
        if filter_year_min and chunk.get("year") and chunk["year"] < filter_year_min:
            continue
        if filter_year_max and chunk.get("year") and chunk["year"] > filter_year_max:
            continue

        # Per-country diversity cap
        _c = chunk.get("country", "Unknown")
        if max_per_country and _country_counts[_c] >= max_per_country:
            continue
        _country_counts[_c] += 1

        # I8: Minimum similarity threshold — skip low-relevance chunks
        if float(score) < 0.15:
            continue
        results.append({**chunk, "score": float(score)})
        if len(results) >= top_k:
            break

    return results


def format_retrieved_chunks(chunks: list[dict]) -> str:
    """Format retrieved chunks into a context block for LLM prompts.

    Each chunk is headed by a source label and its text is capped at
    _MAX_CHUNK_WORDS words to keep prompts within token limits.

    Args:
        chunks: List of chunk dicts from semantic_search().

    Returns:
        Formatted string with source headers and truncated excerpt text.
    """
    parts = []
    for i, chunk in enumerate(chunks, 1):
        country = chunk.get("country", "Unknown")
        year = chunk.get("year", "n/a")
        doc_type = str(chunk.get("doc_type", "document")).title()
        text = chunk.get("text", "")

        # Truncate to word limit
        words = text.split()
        if len(words) > _MAX_CHUNK_WORDS:
            text = " ".join(words[:_MAX_CHUNK_WORDS]) + "…"

        header = f"[Source {i}: {country}, {year}, {doc_type}]"
        parts.append(f"{header}\n{text}")

    return "\n\n---\n\n".join(parts)


def rag_answer(
    query: str,
    df,
    top_k: int = 8,
) -> tuple[dict, list[dict]]:
    """Full RAG pipeline: embed query → retrieve chunks → ground answer with Groq.

    Falls back to data-context-only answering if the knowledge base has not
    been built yet (e.g., before PDFs are downloaded and indexed).

    Args:
        query: The user's question.
        df: Current CRPD DataFrame — used to build statistical data context.
        top_k: Number of chunks to retrieve (default 8, capped at 10).

    Returns:
        tuple: (result_dict, retrieved_chunks)
            result_dict has keys: "text", "model", "timestamp", "error"
            retrieved_chunks is the list of dicts from semantic_search()
    """
    _empty: dict = {
        "text": None,
        "model": GROQ_MODEL,
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "error": None,
    }

    if not _check_rate_limit():
        _empty["error"] = (
            f"You have used all {SESSION_LIMIT} questions for this session. "
            "Refresh the page to start a new session."
        )
        return _empty, []

    # Step 1: Retrieve relevant chunks and filter by minimum relevance
    _MIN_RAG_SCORE = 0.25
    retrieved = [
        c
        for c in semantic_search(query, top_k=top_k)
        if float(c.get("score", 0.0)) >= _MIN_RAG_SCORE
    ]

    # Step 2: Graceful fallback if knowledge base not built yet or no relevant chunks
    if not retrieved:
        data_ctx = build_data_context(df)
        fallback_prompt = (
            f"DATASET SUMMARY:\n{data_ctx}\n\n"
            f"QUESTION: {query}\n\n"
            "Note: The full document knowledge base is not yet available. "
            "Answer using the dataset summary above and note this limitation."
        )
        try:
            client = get_groq_client()
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": RAG_SYSTEM_PROMPT},
                    {"role": "user", "content": fallback_prompt},
                ],
                temperature=0.3,
                max_tokens=800,
            )
            _increment_call_count()
            _empty["text"] = response.choices[0].message.content
            return _empty, []
        except Exception as e:
            _empty["error"] = f"Groq error: {e}"
            return _empty, []

    # Step 3: Format chunks as evidence context
    evidence = format_retrieved_chunks(retrieved)
    data_ctx = build_data_context(df)

    prompt = (
        f"DATASET SUMMARY:\n{data_ctx}\n\n"
        f"RELEVANT DOCUMENT EXCERPTS:\n{evidence}\n\n"
        f"QUESTION: {query}\n\n"
        "Answer based on the document excerpts above. "
        "Cite specific sources by country, year, and document type."
    )

    import time as _time

    _max_retries = 2
    _last_error = None
    for _attempt in range(_max_retries + 1):
        try:
            client = get_groq_client()
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": RAG_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=800,
                stream=True,
            )
            # Collect streamed chunks into full response
            _parts = []
            for _chunk in response:
                _delta = _chunk.choices[0].delta.content
                if _delta:
                    _parts.append(_delta)
            _increment_call_count()
            _empty["text"] = "".join(_parts)
            return _empty, retrieved
        except Exception as e:
            _last_error = e
            if _attempt < _max_retries:
                _time.sleep(1)
                continue
            _empty["error"] = f"Groq error after {_max_retries + 1} attempts: {e}"
            return _empty, retrieved


# ── Phase 4: Policy Brief Generation ─────────────────────────────────────────

# Format configuration: (label, max_tokens, word_target, instructions)
BRIEF_FORMATS: dict[str, dict] = {
    "Executive Summary": {
        "max_tokens": 900,
        "word_target": "350–450 words total",
        "instructions": (
            "Write a concise executive summary. Each section should be 2–3 sentences. "
            "Recommendations should be 3 bullet points."
        ),
    },
    "Full Report": {
        "max_tokens": 1600,
        "word_target": "700–900 words total",
        "instructions": (
            "Write a comprehensive policy report. Each section should be 3–5 sentences. "
            "Recommendations should be 4–6 bullet points with supporting rationale."
        ),
    },
    "Fact Sheet": {
        "max_tokens": 600,
        "word_target": "200–280 words total",
        "instructions": (
            "Write a punchy fact sheet using bullet points throughout. "
            "Each section should be 3–5 bullets. No paragraph prose."
        ),
    },
}

BRIEF_SYSTEM_PROMPT = (
    "You are a senior policy analyst at the Institute on Disability and Public Policy "
    "(IDPP) at American University. You write evidence-based policy briefs grounded "
    "exclusively in CRPD reporting documents from the UN Treaty Body Database.\n\n"
    "Rules:\n"
    "- Use ONLY the provided document excerpts as evidence.\n"
    "- Never invent statistics, country names, or document references.\n"
    "- Every factual claim must cite its source inline using [Source N] notation.\n"
    "- Use 'States Parties' (not 'countries') when referring to CRPD signatories.\n"
    "- Clearly distinguish between State Party positions (from State Reports and "
    "Written Replies) and CRPD Committee assessments (from Lists of Issues and "
    "Concluding Observations). Never attribute Committee recommendations to a "
    "State Party or vice versa.\n"
    "- Do NOT render compliance judgments (e.g., 'failed to comply', 'violated'). "
    "Describe reporting patterns and documented positions neutrally.\n"
    "- Frame all analysis through a disability rights lens (rights-based model, "
    "not medical model).\n"
    "- Use formal, accessible language appropriate for UN and government audiences.\n"
    "- Structure output EXACTLY as instructed — do not add extra sections.\n"
    "- End the brief with a note: 'This brief was generated by AI (Groq LLM) based "
    "on keyword-matched document excerpts. It should be verified against source "
    "documents before citation.'\n\n"
    "Output format (use these EXACT section headers):\n"
    "## CONTEXT\n"
    "<text>\n\n"
    "## KEY FINDINGS\n"
    "<text>\n\n"
    "## RECOMMENDATIONS\n"
    "<text>\n\n"
    "## SOURCES\n"
    "<numbered list of sources cited>"
)


def generate_policy_brief(
    countries: list[str],
    articles: list[str],
    year_min: int,
    year_max: int,
    brief_format: str = "Executive Summary",
) -> dict:
    """Generate a structured CRPD policy brief using RAG + Groq (configured via GROQ_MODEL).

    Retrieves relevant document chunks for the selected countries and articles,
    then prompts the LLM to produce a structured brief with four sections:
    Context, Key Findings, Recommendations, and Sources.

    Args:
        countries: List of country names to focus on (up to 5).
        articles: List of CRPD article names/labels to focus on (e.g. ["Article 9", "Article 24"]).
        year_min: Start of the reporting period.
        year_max: End of the reporting period.
        brief_format: One of "Executive Summary", "Full Report", or "Fact Sheet".

    Returns:
        dict with keys:
            "sections": dict with keys "context", "key_findings", "recommendations", "sources"
            "raw_text": str — full LLM output (for download)
            "chunks_retrieved": int
            "tokens_used": int | None
            "generation_time_ms": int
            "model": str
            "error": str | None
    """
    import time

    _empty: dict = {
        "sections": {},
        "raw_text": "",
        "chunks_retrieved": 0,
        "tokens_used": None,
        "generation_time_ms": 0,
        "model": GROQ_MODEL,
        "error": None,
    }

    if not _check_brief_rate_limit():
        _empty["error"] = (
            f"You have used all {BRIEF_SESSION_LIMIT} brief generations for this session. "
            "Refresh the page to start a new session."
        )
        return _empty

    fmt = BRIEF_FORMATS.get(brief_format, BRIEF_FORMATS["Executive Summary"])

    # ── Step 1: Retrieve chunks across all selected countries ─────────────────
    all_chunks: list[dict] = []
    chunks_per_country = max(2, 8 // max(len(countries), 1))

    for country in countries[:5]:  # cap at 5 countries to keep prompt size sane
        retrieved = semantic_search(
            query=(
                f"CRPD implementation {country} "
                + (
                    " ".join(a.split("—")[0].strip() for a in articles)
                    if articles
                    else "disability rights"
                )
            ),
            top_k=chunks_per_country,
            filter_country=country,
            filter_year_min=year_min,
            filter_year_max=year_max,
        )
        all_chunks.extend(retrieved)

    # Deduplicate by chunk_id, preserve insertion order
    seen: set[str] = set()
    unique_chunks: list[dict] = []
    for c in all_chunks:
        cid = c.get("chunk_id", c.get("source_file", "") + str(c.get("chunk_index", 0)))
        if cid not in seen:
            seen.add(cid)
            unique_chunks.append(c)

    # Fallback: if country filters yielded nothing, try unfiltered
    if not unique_chunks:
        fallback_query = " ".join(articles + countries) if articles else " ".join(countries)
        unique_chunks = semantic_search(
            query=fallback_query,
            top_k=8,
            filter_year_min=year_min,
            filter_year_max=year_max,
        )

    _empty["chunks_retrieved"] = len(unique_chunks)

    # I3: Abort when zero chunks retrieved — don't let LLM hallucinate
    if not unique_chunks:
        _empty["error"] = (
            "No relevant documents were found for the selected States Parties "
            "and reporting period. Try broadening your selection or adjusting "
            "the year range."
        )
        return _empty

    # I9: Only discuss countries that have retrieved evidence
    _countries_with_evidence = sorted(
        {c.get("country", "") for c in unique_chunks if c.get("country")}
    )

    # ── Step 2: Build evidence context ───────────────────────────────────────
    evidence = format_retrieved_chunks(unique_chunks[:6])  # hard cap at 6 chunks in prompt

    country_str = (
        ", ".join(_countries_with_evidence) if _countries_with_evidence else ", ".join(countries)
    )
    article_str = ", ".join(articles) if articles else "all articles"

    # C2: Pass computed data context so LLM has grounded statistics
    from src.analysis import article_frequency, model_shift_table
    from src.data_loader import load_article_dict, load_data

    _data_context = ""
    try:
        _df = load_data()
        _article_dict = load_article_dict()
        _brief_df = _df[
            (_df["country"].isin(countries)) & (_df["year"] >= year_min) & (_df["year"] <= year_max)
        ]
        if len(_brief_df) > 0:
            _n_docs = len(_brief_df)
            _n_sp = _brief_df["country"].nunique()
            _doc_types = ", ".join(sorted(_brief_df["doc_type"].unique()))
            _af = article_frequency(_brief_df, _article_dict)
            _top_arts = (
                ", ".join(_af.nlargest(5, "count")["article"].tolist()) if not _af.empty else "n/a"
            )
            _mt = model_shift_table(_brief_df)
            if len(_mt):
                _r = _mt["rights"].sum()
                _m = _mt["medical"].sum()
                _rights_pct = round(_r / (_r + _m) * 100, 1) if (_r + _m) > 0 else 0
                _lang_context = f"Rights-based keyword share: {_rights_pct}%"
            else:
                _lang_context = "Language framing data not available"
            _data_context = (
                f"\nDATASET STATISTICS (computed from the full dataset, not excerpts):\n"
                f"- Documents in scope: {_n_docs} across {_n_sp} States Parties\n"
                f"- Document types: {_doc_types}\n"
                f"- Most referenced articles: {_top_arts}\n"
                f"- {_lang_context}\n"
                f"Use these statistics for accuracy. Do not invent different numbers.\n\n"
            )
    except Exception:
        _data_context = ""

    user_prompt = (
        f"Write a {brief_format} on CRPD implementation in: {country_str}.\n"
        f"Focus on: {article_str}.\n"
        f"Reporting period: {year_min}–{year_max}.\n\n"
        f"{fmt['instructions']}\n"
        f"Target length: {fmt['word_target']}.\n\n"
        f"{_data_context}"
        f"DOCUMENT EXCERPTS:\n{evidence}\n\n"
        "Now write the brief using the EXACT section headers specified."
    )

    # ── Step 3: Call Groq ────────────────────────────────────────────────────
    t0 = time.perf_counter()
    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": BRIEF_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,  # Lower than chat — briefs need consistency
            max_tokens=fmt["max_tokens"],
        )
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        _increment_brief_count()

        raw = response.choices[0].message.content or ""
        tokens = getattr(response.usage, "total_tokens", None)

        sections = _parse_brief_sections(raw)

        # Auto-populate sources from chunk metadata if the LLM left the section
        # empty or wrote only the "(No document excerpts provided)" fallback.
        src = sections.get("sources", "")
        if not src.strip() or "no document excerpts" in src.lower():
            sections["sources"] = _build_sources_from_chunks(unique_chunks[:6])

        _empty["raw_text"] = raw
        _empty["tokens_used"] = tokens
        _empty["generation_time_ms"] = elapsed_ms
        _empty["sections"] = sections
        return _empty

    except Exception as e:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        err_str = str(e).lower()
        if "rate_limit" in err_str or "413" in err_str or "too large" in err_str:
            _empty["error"] = (
                "The request exceeded the AI model's token limit. "
                "Try selecting fewer countries or narrowing the reporting period."
            )
        else:
            _empty["error"] = (
                "The AI summary service is temporarily unavailable. Please try again in a moment."
            )
        _empty["generation_time_ms"] = elapsed_ms
        return _empty


def _parse_brief_sections(raw_text: str) -> dict[str, str]:
    """Parse LLM output into structured sections by header markers.

    Args:
        raw_text: Full LLM output string.

    Returns:
        dict with keys: "context", "key_findings", "recommendations", "sources".
        Missing sections default to empty string.
    """
    sections: dict[str, str] = {
        "context": "",
        "key_findings": "",
        "recommendations": "",
        "sources": "",
    }

    header_map = {
        "## CONTEXT": "context",
        "## KEY FINDINGS": "key_findings",
        "## RECOMMENDATIONS": "recommendations",
        "## SOURCES": "sources",
    }

    current_key: str | None = None
    buffer: list[str] = []

    for line in raw_text.splitlines():
        stripped = line.strip()
        matched = False
        for header, key in header_map.items():
            if stripped.upper().startswith(header.lstrip("# ").upper()) or stripped == header:
                if current_key and buffer:
                    sections[current_key] = "\n".join(buffer).strip()
                current_key = key
                buffer = []
                matched = True
                break
        if not matched and current_key is not None:
            buffer.append(line)

    # Flush last section
    if current_key and buffer:
        sections[current_key] = "\n".join(buffer).strip()

    return sections


def _build_sources_from_chunks(chunks: list[dict]) -> str:
    """Build a numbered sources list directly from retrieved chunk metadata.

    Used as a fallback when the LLM does not populate the ## SOURCES section.
    Deduplicates by doc_id (or symbol + country + year) so each document appears
    only once regardless of how many chunks came from it.

    Args:
        chunks: List of chunk dicts from semantic_search() / generate_policy_brief().

    Returns:
        Numbered string, e.g. "1. Kenya (2019) — State Report [CRPD/C/KEN/1]\n2. ..."
        Empty string if chunks is empty.
    """
    seen: set[str] = set()
    lines: list[str] = []

    doc_type_display_map = {
        "State Report": "State Report",
        "List of Issues (LOI)": "List of Issues",
        "Written Reply": "Written Reply",
        "Concluding Observations": "Concluding Observations",
        "Response to Concluding Observations": "Response to Concluding Observations",
    }

    for chunk in chunks:
        country = chunk.get("country") or "Unknown"
        year = chunk.get("year")
        doc_type_raw = (chunk.get("doc_type") or "document").lower()
        symbol = chunk.get("symbol") or ""
        doc_id = chunk.get("doc_id") or ""

        # Dedup key: prefer doc_id, fall back to symbol, then country+year+type
        dedup_key = doc_id or symbol or f"{country}|{year}|{doc_type_raw}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        year_str = str(int(year)) if year else "n.d."
        doc_type_str = doc_type_display_map.get(doc_type_raw, doc_type_raw.title())
        ref = f"{country} ({year_str}) — {doc_type_str}"
        if symbol:
            ref += f" [{symbol}]"
        lines.append(ref)

    if not lines:
        return ""
    return "\n".join(f"{i + 1}. {line}" for i, line in enumerate(lines))


def format_brief_as_markdown(
    brief: dict,
    countries: list[str],
    articles: list[str],
    year_min: int,
    year_max: int,
    brief_format: str,
) -> str:
    """Convert a generated brief dict into a clean Markdown string for download.

    Args:
        brief: Return value from generate_policy_brief().
        countries: Country names used in the brief.
        articles: Article filters used.
        year_min: Start year.
        year_max: End year.
        brief_format: Format label (e.g. "Executive Summary").

    Returns:
        Formatted Markdown string ready for st.download_button.
    """
    from datetime import UTC, datetime

    now = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    country_str = ", ".join(countries) if countries else "All Countries"
    article_str = ", ".join(articles) if articles else "All Articles"

    lines = [
        f"# CRPD Policy Brief — {brief_format}",
        f"**Countries:** {country_str}  ",
        f"**Articles:** {article_str}  ",
        f"**Period:** {year_min}–{year_max}  ",
        f"**Generated:** {now}  ",
        f"**Model:** {brief['model']}  ",
        f"**Chunks retrieved:** {brief['chunks_retrieved']}",
        "",
        "---",
        "",
    ]

    section_titles = {
        "context": "## 1. Context",
        "key_findings": "## 2. Key Findings",
        "recommendations": "## 3. Recommendations",
        "sources": "## 4. Sources",
    }

    for key, title in section_titles.items():
        text = brief["sections"].get(key, "").strip()
        if text:
            lines.append(title)
            lines.append("")
            lines.append(text)
            lines.append("")

    lines.append("---")
    lines.append(
        "*Generated by the CRPD Dashboard — Institute on Disability and Public Policy, "
        "American University*"
    )
    return "\n".join(lines)
