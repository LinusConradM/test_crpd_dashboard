"""Auto-generated methodology appendix for CRPD research briefings."""

from __future__ import annotations

from src.data_loader import MODEL_DICT
from src.llm import EMBEDDING_MODEL


def generate_methodology_appendix(result: dict, stats: dict, article_presets: dict) -> str:
    """Generate auto-generated methodology appendix from pipeline metadata.

    Parameters
    ----------
    result : dict
        Pipeline result dict from ``run_research_pipeline``.
    stats : dict
        Dataset statistics from ``get_dataset_stats()``.
    article_presets : dict
        Article dictionary used for keyword-based analysis.

    Returns
    -------
    str
        Markdown-formatted methodology appendix.
    """
    n_docs = stats.get("n_docs", 0)
    n_countries = stats.get("n_countries", 0)
    year_min = stats.get("year_min", 0)
    year_max = stats.get("year_max", 0)
    n_doc_types = stats.get("n_doc_types", 0)

    n_chunks = len(result.get("all_chunks", []))
    n_sub_questions = len(result.get("sub_questions", []))
    llm_calls = result.get("llm_calls", 0)
    duration = result.get("duration_seconds", 0)

    n_medical = len(MODEL_DICT.get("Medical Model", []))
    n_rights = len(MODEL_DICT.get("Rights-Based Model", []))
    n_articles = len(article_presets)
    n_total_phrases = sum(len(v) for v in article_presets.values())

    analyst = result.get("analyst")
    analyst_invoked = analyst is not None and analyst.get("invoked", False)

    sections: list[str] = []

    # --- Section 1: Corpus Description ---
    sections.append("### 1. Corpus Description")
    sections.append("")
    sections.append(
        f"This briefing draws on a corpus of {n_docs} UN treaty body documents "
        f"from {n_countries} States Parties, spanning {year_min}--{year_max}, "
        f"covering {n_doc_types} document types (State Reports, Lists of Issues, "
        f"Written Replies, Concluding Observations, and Responses to Concluding "
        f"Observations). The corpus is derived from publicly available records in "
        f"the UN Treaty Body Database."
    )
    sections.append("")

    # --- Section 2: Retrieval Method ---
    sections.append("### 2. Retrieval Method")
    sections.append("")
    sections.append(
        f"Relevant excerpts were identified using semantic similarity search "
        f"(FAISS IndexFlatIP with {EMBEDDING_MODEL} embeddings, 768 dimensions). "
        f"The user's research question was decomposed into {n_sub_questions} "
        f"sub-questions by a planner agent. Each sub-question was used as a "
        f"query against the vector index, retrieving up to 8 excerpts per "
        f"sub-question. After deduplication, {n_chunks} unique excerpts were "
        f"retained for synthesis."
    )
    sections.append("")

    # --- Section 3: Analytical Methods (conditional) ---
    if analyst_invoked:
        sections.append("### 3. Analytical Methods")
        sections.append("")
        sections.append(
            f"Article mentions were detected using a curated dictionary of "
            f"{n_articles} CRPD articles mapped to {n_total_phrases} keyword "
            f"phrases. Matching uses pre-compiled regular expressions with "
            f"longest-phrase-first ordering to avoid partial matches. Counts "
            f"represent raw keyword frequency (not normalized per 1,000 words), "
            f"following corpus linguistics conventions."
        )
        sections.append("")
        sections.append(
            f"Rights-based versus medical-model language was measured using "
            f"two curated keyword lists: {n_rights} rights-based phrases and "
            f"{n_medical} medical-model phrases. The rights-based share is "
            f"calculated as rights / (rights + medical). These are keyword "
            f"frequencies, not sentiment or intent classifications."
        )
        sections.append("")
        if analyst.get("n_docs_analyzed"):
            sections.append(
                f"Keyword analysis was performed on {analyst['n_docs_analyzed']} "
                f"documents from {analyst['n_countries_analyzed']} States Parties "
                f"identified through the retrieval step."
            )
            sections.append("")

    # --- Section 4: AI Processing ---
    _section_num = 4 if analyst_invoked else 3
    sections.append(f"### {_section_num}. AI Processing")
    sections.append("")
    sections.append(
        f"An AI language model was used to decompose the research question "
        f"(planner), synthesize retrieved excerpts with source separation "
        f"(synthesizer), review outputs for evidence standards (reviewer), "
        f"and compile the final briefing (writer). A total of {llm_calls} "
        f"LLM calls were made over {duration} seconds. The AI synthesizes "
        f"and paraphrases -- it does not quote directly from source documents."
    )
    sections.append("")

    # --- Section 5: Limitations ---
    _section_num += 1
    sections.append(f"### {_section_num}. Limitations")
    sections.append("")
    sections.append(
        "1. **Retrieval bias:** Semantic search may miss relevant excerpts that "
        "use different terminology than the query. Absence of mention does not "
        "indicate absence of action."
    )
    sections.append(
        "2. **Corpus coverage:** The corpus includes only documents publicly "
        "available in the UN Treaty Body Database. Delayed submissions, "
        "documents not yet digitized, or documents in languages other than "
        "English may be absent."
    )
    sections.append(
        "3. **Keyword limitations:** Keyword matching detects lexical presence, "
        "not meaning, context, or legislative intent. A keyword match does not "
        "indicate compliance or implementation."
    )
    sections.append(
        "4. **AI synthesis:** Language model outputs may contain inaccuracies, "
        "omissions, or subtle misrepresentations. All claims should be verified "
        "against original UN documents."
    )
    sections.append(
        "5. **No compliance assessment:** This platform does not assess "
        "compliance with the CRPD. Keyword frequencies and document excerpts "
        "describe reporting patterns, not implementation outcomes."
    )
    sections.append(
        "6. **Temporal lag:** The corpus reflects documents available at the "
        "time of last update and may not include the most recent submissions."
    )
    sections.append(
        "7. **Single-language analysis:** Text analysis is performed on English "
        "text only. Documents originally submitted in other languages rely on "
        "official UN translations, which may introduce translation artifacts."
    )
    sections.append("")

    # --- Section 6: Suggested Citation ---
    _section_num += 1
    sections.append(f"### {_section_num}. Suggested Citation")
    sections.append("")
    sections.append(
        "Institute on Disability and Public Policy, American University. "
        f"*CRPD Research Briefing: {result.get('query', '')}*. "
        f"Generated {result.get('timestamp', '')}. "
        "CRPD Dashboard, https://idpp.connect.posit.cloud/crpd-dashboard. "
        "AI-assisted analysis -- verify against original UN documents."
    )
    sections.append("")

    return "\n".join(sections)
