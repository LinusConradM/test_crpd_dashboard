#!/usr/bin/env python3
"""CRPD Dashboard — Agent System Functional Test Runner.

Generates the exact Claude Code prompts to test each skill and prints
the grading rubric for each test. Run this to get your test plan, then
execute each prompt in Claude Code and grade the response.

Usage:
    python scripts/test_agent_system.py              # Full test plan
    python scripts/test_agent_system.py --skill pm-orchestrator  # Test one skill
    python scripts/test_agent_system.py --quick      # Quick smoke test (1 per skill)

This script does NOT run the tests automatically — Claude Code slash commands
must be invoked manually. This script tells you what to type and what to check.
"""

import argparse
from dataclasses import dataclass, field
import json
import sys


@dataclass
class TestCase:
    id: str
    skill: str
    prompt: str
    check: list[str]
    reference_files_consulted: list[str] = field(default_factory=list)
    gates_tested: list[str] = field(default_factory=list)
    priority: str = "standard"  # "smoke" for quick test, "standard" for full


TESTS = [
    # ─────────────────────────────────────────────────
    # PM ORCHESTRATOR
    # ─────────────────────────────────────────────────
    TestCase(
        id="PM-01",
        skill="pm-orchestrator",
        prompt="/pm-orchestrator What is the current status of all LLM development phases?",
        check=[
            "Reads and displays PHASE_TRACKER.md",
            "Shows all 5 phases with their current step status",
            "Identifies what is blocking progress",
            "States the next concrete action",
            "Does NOT attempt to do specialist work itself",
        ],
        gates_tested=["PM Gate"],
        priority="smoke",
    ),
    TestCase(
        id="PM-02",
        skill="pm-orchestrator",
        prompt="/pm-orchestrator Analyze whether rights-based language is increasing and show it on the dashboard",
        check=[
            "Classifies as multi-agent task (full research pipeline or analyze-and-visualize)",
            "Selects correct team (should include Text Analytics, Data Analyst or Data Scientist, UX, SW Engineer, QA)",
            "Presents team announcement with 'Why included' column",
            "Decomposes into numbered tasks (T1, T2, T3...)",
            "Each task has: Agent, Description, Inputs, Outputs, Depends on, Gate",
            "Respects dependency graph (Data Analyst before Data Scientist, UX before SW Engineer)",
            "Waits for user approval before executing",
            "Does NOT start doing the analysis itself",
        ],
        gates_tested=["Permission Gate"],
        priority="standard",
    ),
    TestCase(
        id="PM-03",
        skill="pm-orchestrator",
        prompt="/pm-orchestrator Skip the design step and go straight to building Phase 1 infrastructure",
        check=[
            "BLOCKS the request — does not proceed",
            "Names the specific gate: Design must be complete before Infrastructure",
            "States the missing artifact: no .pen file in LLM_Development/designs/",
            "States the next action: UX Designer creates design spec",
            "Does NOT rationalize skipping the gate",
        ],
        gates_tested=["PM Gate", "Phase Gate Enforcement"],
        priority="smoke",
    ),
    TestCase(
        id="PM-04",
        skill="pm-orchestrator",
        prompt="/pm-orchestrator Fix the spacing on the sidebar filters",
        check=[
            "Classifies as UI/styling change (not feature build)",
            "Selects minimal team: UX Designer → SW Engineer → QA Tester",
            "Does NOT include Data Analyst, Data Scientist, AI Engineer, or DevOps",
            "Minimum team principle applied",
        ],
        gates_tested=[],
        priority="standard",
    ),
    # ─────────────────────────────────────────────────
    # DATA ANALYST
    # ─────────────────────────────────────────────────
    TestCase(
        id="DA-01",
        skill="data-analyst",
        prompt="/data-analyst Give me a breakdown of CRPD documents by UN regional group and document type",
        check=[
            "Produces a cross-tabulation table",
            "Uses 'States Parties' not 'countries'",
            "Includes n= for every group",
            "Includes totals row and/or totals column",
            "Uses dynamic values (references get_dataset_stats or computes from df)",
            "Includes 'Data current through {year}'",
            "Uses plain-language column headers",
            "Numbers right-aligned, text left-aligned (or notes this for implementation)",
            "Missing values shown as em dash if any",
            "Doc types are title-cased ('State Report' not 'state report')",
        ],
        reference_files_consulted=["table-standards.md"],
        priority="smoke",
    ),
    TestCase(
        id="DA-02",
        skill="data-analyst",
        prompt="/data-analyst Which countries have not submitted any documents?",
        check=[
            "Frames answer in accountability terms ('X States Parties have not yet submitted')",
            "NOT just 'X countries are missing from the dataset'",
            "Breaks down by UN regional group",
            "Caveats: absence from dataset ≠ non-compliance",
            "Uses treaty terminology throughout",
            "Includes data timestamp",
        ],
        reference_files_consulted=["table-standards.md"],
        priority="standard",
    ),
    TestCase(
        id="DA-03",
        skill="data-analyst",
        prompt="/data-analyst Prepare the data for the Data Scientist to analyze regional patterns in Article 24",
        check=[
            "Filters to a single doc_type (likely State Reports)",
            "Normalizes article counts by word_count",
            "Documents the DataFrame: shape, columns, dtypes, filter criteria",
            "Reports n= per region",
            "Flags small-n regions",
            "States which table-standards tier applies ('Tier 2 for dashboard')",
            "Handoff includes all required gate fields",
        ],
        gates_tested=["Data Analyst → Data Scientist gate"],
        priority="standard",
    ),
    # ─────────────────────────────────────────────────
    # DATA SCIENTIST
    # ─────────────────────────────────────────────────
    TestCase(
        id="DS-01",
        skill="data-scientist",
        prompt="/data-scientist Is the difference in Article 24 attention between regions statistically significant?",
        check=[
            "Runs appropriate test (Kruskal-Wallis for multi-group comparison)",
            "Reports test statistic, p-value (≤3 significant digits), and effect size (≤2 decimals)",
            "Reports confidence intervals where applicable",
            "Reports n= for every region",
            "Includes plain-language translation of the finding",
            "Uses 'Article 24 (Education)' not just 'Article 24'",
            "Uses 'States Parties' not 'countries'",
            "Flags small-n regions",
            "Caveats keyword-based measurement limitations",
        ],
        reference_files_consulted=["table-standards.md"],
        priority="smoke",
    ),
    TestCase(
        id="DS-02",
        skill="data-scientist",
        prompt="/data-scientist Specify a chart showing the medical vs rights-based language trend over time",
        check=[
            "Produces a complete chart specification with ALL fields",
            "Chart type: line (dual-line with confidence bands)",
            "Story-driven title (not 'Model Proportion Over Time')",
            "References src/colors.py palette name (not hex values)",
            "Includes accessibility: colorblind-safe, contrast, alt-text",
            "Includes user context (which audience, what action it enables)",
            "References Article names, not just numbers",
            "Subtitle includes sample size and filter context",
        ],
        priority="standard",
    ),
    # ─────────────────────────────────────────────────
    # TEXT ANALYTICS EXPERT
    # ─────────────────────────────────────────────────
    TestCase(
        id="TA-01",
        skill="text-analytics-expert",
        prompt="/text-analytics-expert The keyword dictionary for Article 5 seems to miss a lot. How would you validate and improve it?",
        check=[
            "Proposes a validation workflow (sample zero-count documents, check for false negatives)",
            "Suggests expansion methods (concordance, semantic similarity, cross-lingual terms)",
            "States that dictionary changes require PM approval",
            "Notes that expanded keywords need corpus evidence",
            "Mentions impact assessment (how many documents would change)",
            "References crpd_article_dict.py as the file to modify",
            "Uses 'Article 5 (Equality and Non-discrimination)' with full name",
            "Does NOT modify the dictionary without permission",
        ],
        priority="smoke",
    ),
    TestCase(
        id="TA-02",
        skill="text-analytics-expert",
        prompt="/text-analytics-expert What themes might we be missing that the article dictionary does not capture?",
        check=[
            "Proposes topic modeling approach (BERTopic or LDA)",
            "Explains concept of 'orphan topics' — themes not mapped to any article",
            "Suggests running on chunk corpus",
            "States validation approach (topic stability, multiple seeds)",
            "Includes plain-language framing for stakeholders",
            "Mentions handoff to Data Scientist for statistical testing of topic features",
        ],
        priority="standard",
    ),
    # ─────────────────────────────────────────────────
    # AI ENGINEER
    # ─────────────────────────────────────────────────
    TestCase(
        id="AI-01",
        skill="ai-engineer",
        prompt="/ai-engineer Set up the RAG pipeline for the chat feature",
        check=[
            "FIRST checks PHASE_TRACKER.md — is the chat phase approved?",
            "If phase is not at Infrastructure step, BLOCKS and reports what is missing",
            "If phase is approved, reads design spec from LLM_Development/designs/",
            "Describes the retrieval flow (embed → FAISS search → retrieve → truncate → prompt → LLM)",
            "References correct model routing (Groq for chat)",
            "Includes error handling for all failure modes",
            "Mentions session rate limiting",
            "Plans handoff to Software Engineer for UI wiring",
            "Uses treaty terminology in prompt template design",
            "Requires source citations in LLM output",
        ],
        gates_tested=["PM Gate", "Phase Gate"],
        priority="smoke",
    ),
    TestCase(
        id="AI-02",
        skill="ai-engineer",
        prompt="/ai-engineer The chatbot told a user something wrong about Kenya's Concluding Observations. How do you investigate?",
        check=[
            "Treats as critical issue (fabricated claims harm advocacy)",
            "Proposes reproducing the query and inspecting retrieved chunks",
            "Checks: were correct chunks retrieved? Did LLM hallucinate?",
            "Checks metadata filtering — was country filter applied?",
            "Proposes strengthening no-fabrication clause in system prompt",
            "Mentions adding the failure case as a regression test",
            "Plans evaluation re-run after fix",
        ],
        priority="standard",
    ),
    # ─────────────────────────────────────────────────
    # SOFTWARE ENGINEER
    # ─────────────────────────────────────────────────
    TestCase(
        id="SE-01",
        skill="software-engineer",
        prompt="/software-engineer Implement a data table on the Country Profiles page showing all documents for the selected country",
        check=[
            "Consults table-standards.md (mentions it or follows its rules)",
            "States this is a Tier 2 (dashboard) table",
            "Chooses appropriate Streamlit component (st.dataframe for interactive)",
            "Uses plain-language column headers",
            "Includes CSV download button with contextual filename",
            "Applies column_config for number formatting",
            "Includes caption with filter context and n=",
            "Mentions accessibility (th scope, screen reader support)",
            "References src/colors.py for any styling",
            "Plans to run ruff and table_lint.py before handoff",
        ],
        reference_files_consulted=["table-standards.md", "require-permission.md"],
        priority="smoke",
    ),
    # ─────────────────────────────────────────────────
    # QA TESTER
    # ─────────────────────────────────────────────────
    TestCase(
        id="QA-01",
        skill="qa-tester",
        prompt="/qa-tester Audit the Country Profiles page for table compliance and accessibility",
        check=[
            "Runs or references table_lint.py as first automated check",
            "Uses the table audit checklist from table-standards.md",
            "Checks: hardcoded numbers, treaty terminology, decimal precision",
            "Checks: CSV download present, captions present, th scope",
            "Checks: WCAG contrast, keyboard navigation, screen reader",
            "Reports violations using industry terminology (e.g., 'decimal alignment violation')",
            "Produces pass/fail verdict",
        ],
        reference_files_consulted=["table-standards.md", "wcag-audit.md"],
        priority="smoke",
    ),
    # ─────────────────────────────────────────────────
    # CROSS-SKILL: ROUTING ACCURACY
    # ─────────────────────────────────────────────────
    TestCase(
        id="RT-01",
        skill="pm-orchestrator",
        prompt="/pm-orchestrator Who should work on this: the keyword matching misses too much",
        check=[
            "Routes to Text Analytics Expert (not Data Analyst or Data Scientist)",
            "Classifies as 'dictionary update' or 'improve measurement'",
            "Team includes: Text Analytics → Data Analyst → Data Scientist → SW Engineer → QA",
            "Does NOT assign all 8 roles",
        ],
        priority="smoke",
    ),
    TestCase(
        id="RT-02",
        skill="pm-orchestrator",
        prompt="/pm-orchestrator Build a country profile page for Kenya",
        check=[
            "Classifies as 'country profile deep dive' (Pattern 6)",
            "Team includes Data Analyst, potentially Text Analytics, Data Scientist, UX, SW Engineer, QA",
            "Decomposes into: data pull → analysis → chart spec → design → implementation → test",
        ],
        priority="standard",
    ),
    # ─────────────────────────────────────────────────
    # CROSS-SKILL: GATE ENFORCEMENT
    # ─────────────────────────────────────────────────
    TestCase(
        id="GT-01",
        skill="pm-orchestrator",
        prompt="/pm-orchestrator The Data Scientist wants to analyze the data but the Data Analyst has not prepared it yet. Can we skip that step?",
        check=[
            "BLOCKS — enforces dependency (Data Analyst before Data Scientist)",
            "Names the dependency rule",
            "States what must happen first",
            "Does NOT allow skipping",
        ],
        gates_tested=["Dependency enforcement"],
        priority="standard",
    ),
    # ─────────────────────────────────────────────────
    # REFERENCE FILE: TABLE STANDARDS
    # ─────────────────────────────────────────────────
    TestCase(
        id="TS-01",
        skill="data-analyst",
        prompt="/data-analyst Show me document counts by region. I want this as a dashboard table.",
        check=[
            "Explicitly states 'Tier 2' for dashboard",
            "References table template from §3 (likely Cross-Tabulation §3B)",
            "Includes all Tier 2 requirements: WCAG markup notes, CSV download, colors.py reference",
            "Headers are plain language, centered, bold (or notes this for UX/SW)",
            "Numbers right-aligned",
            "Totals row present",
            "Treaty terminology used",
        ],
        reference_files_consulted=["table-standards.md"],
        priority="standard",
    ),
    # ─────────────────────────────────────────────────
    # REFERENCE FILE: REQUIRE-PERMISSION
    # ─────────────────────────────────────────────────
    TestCase(
        id="RP-01",
        skill="software-engineer",
        prompt="/software-engineer Fix the table caption on the overview page to include the sample size",
        check=[
            "Presents a Change Summary BEFORE making any edit",
            "Lists exact file(s) to modify",
            "Shows what will change (current → replacement)",
            "Waits for explicit approval",
            "Does NOT modify the file without permission",
        ],
        reference_files_consulted=["require-permission.md"],
        priority="smoke",
    ),
]


def print_test(test: TestCase, index: int):
    """Print a single test case in a readable format."""
    print(f"\n{'━' * 70}")
    print(f"  TEST {test.id} — {test.skill}")
    print(f"{'━' * 70}")
    print("\n  📋 Type this in Claude Code:\n")
    print(f"     {test.prompt}")
    print("\n  ✅ Check the response for:\n")
    for i, check in enumerate(test.check, 1):
        print(f"     {i}. {check}")
    if test.reference_files_consulted:
        print(f"\n  📁 Should consult: {', '.join(test.reference_files_consulted)}")
    if test.gates_tested:
        print(f"  🚧 Gates tested: {', '.join(test.gates_tested)}")
    print("\n  Grade: [ PASS / PARTIAL / FAIL ]")


def export_json(tests: list[TestCase], path: str):
    """Export test cases as JSON for programmatic use."""
    data = {
        "skill_name": "crpd-agent-system",
        "evals": [
            {
                "id": t.id,
                "skill": t.skill,
                "prompt": t.prompt,
                "expected_checks": t.check,
                "reference_files": t.reference_files_consulted,
                "gates_tested": t.gates_tested,
                "priority": t.priority,
            }
            for t in tests
        ],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nExported {len(tests)} test cases to {path}")


def main():
    parser = argparse.ArgumentParser(
        description="CRPD Agent System — Functional Test Plan",
    )
    parser.add_argument(
        "--skill",
        help="Only show tests for this skill (e.g., 'pm', 'data-analyst')",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Smoke test only — 1 test per skill",
    )
    parser.add_argument(
        "--export-json",
        help="Export test cases as JSON to this path",
    )
    args = parser.parse_args()

    tests = TESTS

    if args.skill:
        tests = [t for t in tests if t.skill == args.skill]

    if args.quick:
        tests = [t for t in tests if t.priority == "smoke"]

    if args.export_json:
        export_json(tests, args.export_json)
        return

    # Print header
    print("=" * 70)
    print("  CRPD Dashboard — Agent System Functional Test Plan")
    print("=" * 70)
    print(f"\n  Total tests: {len(tests)}")
    print(f"  Skills covered: {len(set(t.skill for t in tests))}")
    print("\n  Instructions:")
    print("  1. Open Claude Code in the CRPD project directory")
    print("  2. Run: python scripts/validate_agent_system.py  (structural check first)")
    print("  3. For each test below, type the prompt in Claude Code")
    print("  4. Grade the response against the checklist")
    print("  5. Record PASS / PARTIAL / FAIL for each test")

    for i, test in enumerate(tests):
        print_test(test, i)

    # Summary
    print(f"\n{'=' * 70}")
    print("  Grading Summary")
    print(f"{'=' * 70}")
    print("\n  Fill in after running each test:\n")
    print(f"  {'ID':<8} {'Skill':<20} {'Grade':<12} Notes")
    print(f"  {'─' * 8} {'─' * 20} {'─' * 12} {'─' * 20}")
    for t in tests:
        print(f"  {t.id:<8} {t.skill:<20} [        ]")

    print("\n  Passing criteria:")
    print("  • All smoke tests (--quick) must PASS for the system to be functional")
    print("  • Standard tests: PARTIAL is acceptable if the core behavior is correct")
    print("  • Any FAIL on a gate test (GT-*, PM-03) means the gate is broken")
    print("  • Any FAIL on terminology (States Parties, article names) means the")
    print("    skill needs its stakeholder output gate strengthened")


if __name__ == "__main__":
    main()
