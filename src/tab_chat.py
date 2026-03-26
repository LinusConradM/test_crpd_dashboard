"""AI Research Assistant tab — Phase 2 Chat Q&A Interface.

Standalone page providing multi-turn conversation with Groq (configured via
GROQ_MODEL) over the full CRPD dataset. No filters — uses the complete
unfiltered data.
"""

import html

import bleach
import streamlit as st

from src.data_loader import get_dataset_stats
from src.llm import (
    EMBEDDING_MODEL,
    get_remaining_calls,
    rag_answer,
)


# ── HTML sanitization for XSS prevention ─────────────────────────────────────

# Tags allowed in LLM-generated responses (formatting only, no scripts/iframes)
_ALLOWED_TAGS = [
    "p",
    "strong",
    "em",
    "b",
    "i",
    "u",
    "ul",
    "ol",
    "li",
    "br",
    "code",
    "pre",
    "h1",
    "h2",
    "h3",
    "h4",
    "a",
    "blockquote",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
]
_ALLOWED_ATTRS = {
    "a": ["href", "title"],
    "th": ["scope"],
}


def _sanitize_llm_html(text: str) -> str:
    """Sanitize LLM output: allow safe formatting tags, strip everything else.

    Links are restricted to https:// and mailto: protocols only to prevent
    LLM-crafted phishing links with javascript: or data: URIs.
    """
    return bleach.clean(
        text,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        protocols=["https", "mailto"],
        strip=True,
    )


# ── Card metadata for the starter question grid ─────────────────────────────
# (icon, title, accent_color, bg_color, question)
_STARTER_CARDS = [
    (
        "school",
        "Inclusive Education",
        "#003F87",
        "#F2F4F8",
        "How do States Parties describe implementing inclusive education under Article 24?",
    ),
    (
        "gavel",
        "Legal Capacity",
        "#003F87",
        "#F2F4F8",
        "What do Concluding Observations say about legal capacity and supported decision-making?",
    ),
    (
        "person_raised_hand",
        "Women with Disabilities",
        "#003F87",
        "#F2F4F8",
        "How do States Parties address violence against women with disabilities?",
    ),
    (
        "accessible",
        "Accessibility Measures",
        "#003F87",
        "#F2F4F8",
        "What accessibility measures have States Parties reported under Article 9?",
    ),
    (
        "work",
        "Employment Rights",
        "#003F87",
        "#F2F4F8",
        "What barriers to employment do States Parties report for persons with disabilities?",
    ),
    (
        "other_houses",
        "Committee Concerns",
        "#003F87",
        "#F2F4F8",
        "What has the CRPD Committee recommended about deinstitutionalization?",
    ),
]

_CHAT_CSS = """
<style>

/* ── Starter card visual ── */
.starter-full-card {
    background: #F2F4F8;
    border: 1px solid rgba(194, 198, 212, 0.4);
    border-radius: 0.75rem;
    padding: 1.1rem 1.25rem;
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 16px;
    transition: background 0.18s ease, box-shadow 0.18s ease;
    pointer-events: none;
}
.starter-full-card-hover {
    background: #E8ECF2 !important;
    box-shadow: 0 4px 16px rgba(100, 116, 145, 0.10) !important;
}
.starter-icon-box {
    width: 48px;
    height: 48px;
    border-radius: 10px;
    background: #003F87;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.starter-icon-box .material-symbols-outlined {
    color: white !important;
    font-size: 1.3rem !important;
}
.starter-card-text { display: flex; flex-direction: column; gap: 4px; }
.starter-card-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #191C1F;
    font-family: 'Inter', Arial, sans-serif;
    line-height: 1.3;
}
.starter-card-question { font-size: 0.85rem; color: #6b7280; line-height: 1.5; }

/* ── Grid overlay: button and card share the same cell ── */
div[data-testid="stVerticalBlock"]:has(> div.element-container .starter-full-card) {
    display: grid !important;
    grid-template-columns: 1fr !important;
    align-items: stretch !important;
    margin-bottom: 0.75rem !important;
}
div[data-testid="stVerticalBlock"]:has(> div.element-container .starter-full-card)
> div.element-container {
    grid-row: 1 !important;
    grid-column: 1 !important;
    position: relative !important;
    align-self: stretch !important;
}
/* Button layer: invisible, z-index on top → receives clicks */
div[data-testid="stVerticalBlock"]:has(> div.element-container .starter-full-card)
> div.element-container:has(div[data-testid="stButton"]) {
    z-index: 10 !important;
    opacity: 0 !important;
}
/* Card layer: visible, below button layer */
div[data-testid="stVerticalBlock"]:has(> div.element-container .starter-full-card)
> div.element-container:has(.starter-full-card) {
    z-index: 5 !important;
}
/* Button stretches to fill the grid cell (matches card height) */
div[data-testid="stVerticalBlock"]:has(> div.element-container .starter-full-card)
div[data-testid="stButton"] {
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
}
div[data-testid="stVerticalBlock"]:has(> div.element-container .starter-full-card)
div[data-testid="stButton"] > button {
    flex: 1 !important;
    width: 100% !important;
    min-height: 80px !important;
    background: transparent !important;
    border: none !important;
    cursor: pointer !important;
    padding: 0 !important;
    margin: 0 !important;
}

/* ── Chat card: complete self-contained card ── */
.chat-card {
    background: #ffffff;
    border: 1px solid rgba(194, 198, 212, 0.5);
    border-radius: 0.75rem;
    box-shadow: 0 4px 24px rgba(100, 116, 145, 0.06);
    overflow: hidden;
    margin-bottom: 12px;
    min-height: 560px;
    display: flex;
    flex-direction: column;
}
.chat-card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 16px 20px;
    background: #F2F4F8;
    border-bottom: 1px solid rgba(194, 198, 212, 0.4);
}
.chat-status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #22c55e;
    flex-shrink: 0;
}
.chat-header-title {
    font-family: 'Inter', Arial, sans-serif;
    font-size: 0.95rem;
    font-weight: 700;
    color: #191C1F;
}
.chat-header-sub {
    font-family: 'Inter', Arial, sans-serif;
    font-size: 0.88rem;
    color: #424752;
}

/* ── Empty state ── */
.chat-empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 32px 24px 28px;
    text-align: center;
    flex: 1;
}
.chat-empty-icon {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    background: #F2F4F8;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
}
.chat-empty-icon .material-symbols-outlined {
    font-size: 1.8rem !important;
    color: #424752 !important;
}
.chat-empty-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #191C1F;
    margin-bottom: 6px;
}
.chat-empty-sub {
    font-size: 0.88rem;
    color: #424752;
}

/* ── Messages ── */
.chat-messages {
    padding: 20px 20px 12px;
    display: flex;
    flex-direction: column;
    gap: 16px;
}
.chat-row-user {
    display: flex;
    align-items: flex-end;
    justify-content: flex-end;
    gap: 10px;
}
.chat-bubble-user {
    background: linear-gradient(135deg, #003F87, #0056B3);
    color: #ffffff;
    padding: 12px 18px;
    border-radius: 18px 18px 4px 18px;
    max-width: 72%;
    font-size: 0.93rem;
    line-height: 1.5;
    font-family: 'Inter', Arial, sans-serif;
}
.chat-avatar-user {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: #F2F4F8;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.chat-avatar-user .material-symbols-outlined {
    font-size: 1.05rem !important;
    color: #424752 !important;
}
.chat-row-ai {
    display: flex;
    align-items: flex-start;
    gap: 10px;
}
.chat-avatar-ai {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: #F2F4F8;
    border: 1px solid rgba(194, 198, 212, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 2px;
}
.chat-avatar-ai .material-symbols-outlined {
    font-size: 1.05rem !important;
    color: #003F87 !important;
}
.chat-bubble-ai {
    background: #F2F4F8;
    color: #191C1F;
    padding: 14px 18px;
    border-radius: 4px 18px 18px 18px;
    max-width: 80%;
    font-size: 0.93rem;
    line-height: 1.6;
    font-family: 'Inter', Arial, sans-serif;
}
.chat-meta-ai {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;
}
.chat-model-tag {
    font-size: 0.68rem;
    font-family: 'IBM Plex Mono', monospace;
    color: #424752;
    background: rgba(194, 198, 212, 0.35);
    padding: 2px 7px;
    border-radius: 4px;
}
.chat-calls-tag {
    font-size: 0.68rem;
    color: #424752;
}

/* ── Animated loading dots ── */
.chat-loading-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
}
.chat-dots {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 14px 18px;
    background: #F2F4F8;
    border-radius: 4px 18px 18px 18px;
}
.chat-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #424752;
    animation: chat-bounce 1.2s infinite ease-in-out;
}
.chat-dot:nth-child(2) { animation-delay: 0.15s; }
.chat-dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes chat-bounce {
    0%, 80%, 100% { transform: scale(0.7); opacity: 0.5; }
    40% { transform: scale(1); opacity: 1; }
}
.chat-thinking-label {
    font-size: 0.82rem;
    color: #424752;
    padding: 14px 0 0 4px;
    font-style: italic;
}


/* ── Input form ── */
div[data-testid="stForm"] {
    border: 1px solid rgba(194, 198, 212, 0.5) !important;
    border-radius: 0.75rem !important;
    background: #ffffff !important;
    padding: 8px 8px 8px 4px !important;
    box-shadow: 0 4px 24px rgba(100, 116, 145, 0.06) !important;
    overflow: hidden !important;
    margin-top: 0 !important;
    transition: border-color 0.15s ease !important;
}
div[data-testid="stForm"]:focus-within {
    border-color: #003F87 !important;
}
/* Spacing between input and button columns */
div[data-testid="stForm"] [data-testid="stHorizontalBlock"] {
    gap: 8px !important;
    align-items: center !important;
    padding: 0 4px !important;
}
div[data-testid="stForm"] [data-testid="column"] {
    padding: 0 !important;
    min-width: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
/* Input field */
div[data-testid="stForm"] div[data-testid="stTextInput"] label {
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
}
div[data-testid="stTextInput"] input {
    border: 1px solid rgba(194, 198, 212, 0.5) !important;
    border-radius: 0.5rem !important;
    padding: 10px 16px !important;
    font-size: 0.93rem !important;
    font-family: 'Inter', Arial, sans-serif !important;
    background: #F7F9FD !important;
    box-shadow: none !important;
    color: #191C1F !important;
    outline: none !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #003F87 !important;
    background: #ffffff !important;
    box-shadow: none !important;
    outline: none !important;
}
/* Send button */
div[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #003F87, #0056B3) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 0.5rem !important;
    font-family: 'Inter', Arial, sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 8px 16px !important;
    width: auto !important;
    height: auto !important;
    min-height: unset !important;
    white-space: nowrap !important;
    transition: opacity 0.15s ease !important;
}
div[data-testid="stFormSubmitButton"] > button:hover {
    opacity: 0.88 !important;
}
/* ── Hide Streamlit's native "Press Enter to submit form" hint ── */
div[data-testid="stTextInput"] small,
div[data-testid="stTextInput"] [data-testid="InputInstructions"],
div[data-testid="stTextInput"] ~ small {
    display: none !important;
    visibility: hidden !important;
}
div[data-testid="stTextInput"] input::placeholder {
    color: #424752;
    opacity: 0.6;
}

/* ── RAG citations panel ── */
.rag-citations {
    margin: 6px 0 4px 44px;
    background: #FFFBF0;
    border: 1px solid rgba(197, 124, 10, 0.25);
    border-radius: 0.65rem;
    padding: 10px 14px;
    max-width: 80%;
}
.rag-citations-hdr {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 0.72rem;
    font-weight: 700;
    color: #92580A;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-family: 'Inter', Arial, sans-serif;
    margin-bottom: 8px;
}
.rag-source-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 5px 0;
    border-bottom: 1px solid rgba(197, 124, 10, 0.1);
}
.rag-source-row:last-child { border-bottom: none; padding-bottom: 0; }
.rag-source-num {
    font-size: 0.7rem;
    font-weight: 700;
    color: #92580A;
    background: rgba(197, 124, 10, 0.15);
    border-radius: 4px;
    padding: 1px 6px;
    flex-shrink: 0;
    font-family: 'IBM Plex Mono', monospace;
}
.rag-source-meta {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 1px;
}
.rag-source-label {
    font-size: 0.82rem;
    font-weight: 600;
    color: #191C1F;
    font-family: 'Inter', Arial, sans-serif;
}
.rag-source-type {
    font-size: 0.73rem;
    color: #6b7280;
    font-family: 'Inter', Arial, sans-serif;
}
.rag-score-wrap {
    flex-shrink: 0;
    width: 68px;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
}
.rag-score-track {
    width: 68px;
    height: 3px;
    background: rgba(197, 124, 10, 0.15);
    border-radius: 2px;
    overflow: hidden;
}
.rag-score-fill {
    height: 3px;
    background: #C57C0A;
    border-radius: 2px;
}
.rag-score-val {
    font-size: 0.68rem;
    color: #92580A;
    font-family: 'IBM Plex Mono', monospace;
}
</style>
"""


def _build_chat_card(status: str, body_html: str) -> str:
    return (
        "<div class='chat-card'>"
        "<div class='chat-card-header'>"
        "<div class='chat-status-dot'></div>"
        "<span class='chat-header-title'>AI Research Assistant</span>"
        f"<span class='chat-header-sub'>&nbsp;{status}</span>"
        "</div>"
        f"{body_html}"
        "</div>"
    )


def _build_citations_html(chunks: list) -> str:
    """Build amber citations panel HTML for RAG-retrieved source chunks."""
    if not chunks:
        return ""
    items_html = ""
    for i, chunk in enumerate(chunks, 1):
        country = html.escape(str(chunk.get("country", "Unknown")))
        year = html.escape(str(chunk.get("year", "n/a")))
        doc_type = html.escape(str(chunk.get("doc_type", "document")).title())
        score = float(chunk.get("score", 0.0))
        score_pct = max(0, min(int(score * 100), 100))
        items_html += (
            f"<div class='rag-source-row'>"
            f"<span class='rag-source-num'>{i}</span>"
            f"<div class='rag-source-meta'>"
            f"<span class='rag-source-label'>{country} · {year}</span>"
            f"<span class='rag-source-type'>{doc_type}</span>"
            f"</div>"
            f"<div class='rag-score-wrap'>"
            f"<div class='rag-score-track'>"
            f"<div class='rag-score-fill' style='width:{score_pct}%'></div>"
            f"</div>"
            f"<span class='rag-score-val'>{score:.2f}</span>"
            f"</div>"
            f"</div>"
        )
    return (
        "<div class='rag-citations'>"
        "<div class='rag-citations-hdr'>"
        "<span class='material-symbols-outlined' "
        "style='font-size:0.85rem!important;color:#C57C0A!important;'>auto_awesome</span>"
        "Sources Retrieved"
        "</div>"
        f"{items_html}"
        "</div>"
    )


def render(df):
    """Render the AI Research Assistant chat interface."""
    st.markdown(_CHAT_CSS, unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "ai_thinking" not in st.session_state:
        st.session_state.ai_thinking = False

    remaining = get_remaining_calls()
    _s = get_dataset_stats()

    # ── Layout: two-column when empty, full-width when conversation active (#10) ──
    _has_history = len(st.session_state.chat_history) > 0

    if _has_history:
        # Full-width chat after first message — no wasted left column
        right_col = st.container()
        left_col = None
    else:
        left_col, right_col = st.columns([1, 2], gap="small")

    if left_col is not None:
        with left_col:
            for i, (icon, title, _color, _bg, question) in enumerate(_STARTER_CARDS):
                with st.container():
                    # Button rendered first — invisible click target
                    clicked = st.button(
                        " ",
                        key=f"starter_{i}",
                        width="stretch",
                    )
                    # Card rendered second — visual layer (pointer-events: none in CSS)
                    st.markdown(
                        f"<div class='starter-full-card'>"
                        f"<div class='starter-icon-box'>"
                        f"<span class='material-symbols-outlined'>{icon}</span>"
                        f"</div>"
                        f"<div class='starter-card-text'>"
                        f"<div class='starter-card-title'>{title}</div>"
                        f"<div class='starter-card-question'>{question}</div>"
                        f"</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                if clicked:
                    st.session_state.chat_history.append({"role": "user", "content": question})
                    st.session_state.ai_thinking = True
                    st.rerun()

    with right_col:
        # ── Chat card in scrollable container — input stays below ──
        chat_box = st.container(height=700)
        with chat_box:
            if not st.session_state.chat_history:
                body = (
                    "<div class='chat-empty-state'>"
                    "<div class='chat-empty-icon'>"
                    "<span class='material-symbols-outlined'>forum</span>"
                    "</div>"
                    "<div class='chat-empty-title'>Ask about CRPD reporting</div>"
                    "<div class='chat-empty-sub'>"
                    f"Search across {_s['n_docs']} documents from "
                    f"{_s['n_countries']} States Parties "
                    f"({_s['year_min']}–{_s['year_max']}). "
                    "Select a topic or type your own question."
                    "</div>"
                    "<div style='margin-top:1rem;padding:0.6rem 1rem;"
                    "background:#FEF3CD;border-radius:6px;font-size:0.78rem;"
                    "color:#664D03;line-height:1.5;max-width:420px;margin-left:auto;"
                    "margin-right:auto;'>"
                    "Responses are AI-generated from keyword-based document analysis. "
                    "They are not official UN interpretations. "
                    "Verify against original documents."
                    "</div>"
                    "</div>"
                )
                st.markdown(_build_chat_card("Ready to help", body), unsafe_allow_html=True)
            else:
                # Active conversation — build bubble HTML with ARIA (#4)
                messages_html = (
                    "<div class='chat-messages' role='log' "
                    "aria-label='Conversation with AI Research Assistant' aria-live='polite'>"
                )
                for msg in st.session_state.chat_history:
                    if msg["role"] == "user":
                        _safe_user = html.escape(msg["content"])
                        messages_html += (
                            "<div class='chat-row-user' role='group' aria-label='Your question'>"
                            f"<div class='chat-bubble-user'>{_safe_user}</div>"
                            "<div class='chat-avatar-user'>"
                            "<span class='material-symbols-outlined'>person</span>"
                            "</div>"
                            "</div>"
                        )
                    else:
                        _safe_ai = _sanitize_llm_html(msg["content"])
                        messages_html += (
                            "<div class='chat-row-ai' role='group' aria-label='AI response'>"
                            "<div class='chat-avatar-ai'>"
                            "<span class='material-symbols-outlined'>lightbulb</span>"
                            "</div>"
                            "<div class='chat-bubble-ai'>"
                            "<div class='chat-meta-ai'>"
                            "<span class='chat-model-tag'>AI Research Assistant</span>"
                            f"<span class='chat-calls-tag'>{remaining} questions remaining</span>"
                            "</div>"
                            f"{_safe_ai}"
                            "</div>"
                            "</div>"
                        )
                        if msg.get("chunks"):
                            messages_html += _build_citations_html(msg["chunks"])

                if st.session_state.ai_thinking:
                    messages_html += (
                        "<div class='chat-loading-row' role='status' aria-live='polite'>"
                        "<div class='chat-avatar-ai'>"
                        "<span class='material-symbols-outlined'>lightbulb</span>"
                        "</div>"
                        "<div>"
                        "<div class='chat-dots'>"
                        "<div class='chat-dot'></div>"
                        "<div class='chat-dot'></div>"
                        "<div class='chat-dot'></div>"
                        "</div>"
                        "<div class='chat-thinking-label'>Searching CRPD documents…</div>"
                        "</div>"
                        "</div>"
                    )

                messages_html += "</div>"
                st.markdown(
                    _build_chat_card("Ready to help", messages_html),
                    unsafe_allow_html=True,
                )

            # Resolve pending AI response using RAG pipeline (#5: multi-turn)
            if st.session_state.ai_thinking:
                last_user_msg = next(
                    (
                        m["content"]
                        for m in reversed(st.session_state.chat_history)
                        if m["role"] == "user"
                    ),
                    "",
                )
                # Inject last 2 turns of context into the query for better
                # FAISS retrieval on follow-up questions like "tell me more"
                _history = st.session_state.chat_history[:-1]  # exclude current question
                _recent = [
                    m
                    for m in _history[-4:]  # last 2 Q+A pairs
                    if m["role"] in ("user", "assistant") and m.get("content")
                ]
                if _recent:
                    _context_summary = " ".join(m["content"][:200] for m in _recent)
                    _contextualized_query = (
                        f"Previous context: {_context_summary}\n\nCurrent question: {last_user_msg}"
                    )
                else:
                    _contextualized_query = last_user_msg
                result, chunks = rag_answer(_contextualized_query, df)
                st.session_state["_faiss_loaded"] = True
                response_text = f"Error: {result['error']}" if result["error"] else result["text"]
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": response_text, "chunks": chunks}
                )
                st.session_state.ai_thinking = False
                st.rerun()

        # ── Input form (always visible below chat box) ──
        with st.form("chat_input_form", clear_on_submit=True):
            col_input, col_btn = st.columns([7, 1])
            with col_input:
                user_input = st.text_input(
                    "Chat message",
                    placeholder="Ask a question about the data...",
                    label_visibility="collapsed",
                )
            with col_btn:
                submitted = st.form_submit_button("Send ➤", width="stretch")

        st.markdown(
            "<div style='display:flex;justify-content:space-between;align-items:center;"
            "padding:4px 4px 0;font-family:Inter,Arial,sans-serif;font-size:0.78rem;'>"
            "<span style='color:#664D03;'>AI-generated · Not official UN interpretation "
            "· Verify against original documents</span>"
            f"<span style='color:#9ca3af;'>{remaining} questions remaining · "
            "Press Enter to Submit</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        # #8: Cross-page rate limit visibility
        if remaining <= 5 and remaining > 0:
            st.caption(
                f"⚠️ {remaining} questions remaining in this session. "
                "This quota is shared with AI Insights and Policy Brief generation."
            )
        elif remaining == 0:
            st.warning(
                "You have used all questions for this session. "
                "Refresh the page to start a new session."
            )

        # #9: Methodology disclosure
        with st.expander("ℹ️ How this works", expanded=False):
            st.markdown(
                "This assistant uses **retrieval-augmented generation (RAG)** to answer "
                "your questions. When you ask a question:\n\n"
                "1. Your query is converted to a semantic vector using the "
                f"**{EMBEDDING_MODEL}** embedding model\n"
                "2. The most relevant passages are retrieved from a FAISS vector index "
                f"of indexed passages from **{_s['n_docs']} UN documents**\n"
                "3. Retrieved passages are sent to the **Llama 3.3 70B** language model "
                "(via Groq) which synthesizes an answer grounded in the evidence\n\n"
                "**Limitations:** Answers depend on the quality of retrieved passages. "
                "The model may miss relevant context, and keyword-based chunking can split "
                "important passages. Always verify findings against the original documents."
            )
        if submitted and user_input.strip():
            st.session_state.chat_history.append({"role": "user", "content": user_input.strip()})
            st.session_state.ai_thinking = True
            st.rerun()
