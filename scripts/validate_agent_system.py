#!/usr/bin/env python3
"""CRPD Dashboard — Agent System Validation Script.

Validates that all skill files, reference files, and CLAUDE.md are properly
set up and structurally correct. Run this BEFORE functional testing.

Usage:
    python scripts/validate_agent_system.py

Exit codes:
    0 = all checks pass
    1 = failures found
"""

from pathlib import Path
import re
import sys


class Check:
    def __init__(self, name: str, passed: bool, detail: str = ""):
        self.name = name
        self.passed = passed
        self.detail = detail

    def __str__(self) -> str:
        status = "✅" if self.passed else "❌"
        detail = f" — {self.detail}" if self.detail else ""
        return f"  {status} {self.name}{detail}"


def validate_file_exists(path: str, label: str) -> Check:
    """Check that a file exists."""
    exists = Path(path).exists()
    return Check(
        f"{label} exists at {path}",
        exists,
        "" if exists else "FILE MISSING",
    )


def validate_file_contains(path: str, label: str, required_strings: list[str]) -> list[Check]:
    """Check that a file contains required content."""
    checks = []
    p = Path(path)
    if not p.exists():
        checks.append(Check(f"{label} content check", False, "file not found"))
        return checks

    content = p.read_text(encoding="utf-8")
    for s in required_strings:
        found = s.lower() in content.lower()
        checks.append(
            Check(
                f"{label} contains '{s}'",
                found,
                "" if found else f"MISSING: '{s}' not found in {path}",
            )
        )
    return checks


def validate_skill_frontmatter(path: str, label: str) -> list[Check]:
    """Check that a skill file has proper YAML frontmatter with name and description."""
    checks = []
    p = Path(path)
    if not p.exists():
        checks.append(Check(f"{label} frontmatter", False, "file not found"))
        return checks

    content = p.read_text(encoding="utf-8")

    # Check for YAML frontmatter delimiters
    has_frontmatter = content.startswith("---") and content.count("---") >= 2
    checks.append(
        Check(
            f"{label} has YAML frontmatter",
            has_frontmatter,
            "" if has_frontmatter else "Missing --- delimiters",
        )
    )

    # Check for name field
    has_name = bool(re.search(r"^name:\s*\S+", content, re.MULTILINE))
    checks.append(
        Check(
            f"{label} has 'name:' field",
            has_name,
            "" if has_name else "Missing name field in frontmatter",
        )
    )

    # Check for description field
    has_desc = bool(re.search(r"^description:\s*", content, re.MULTILINE))
    checks.append(
        Check(
            f"{label} has 'description:' field",
            has_desc,
            "" if has_desc else "Missing description field in frontmatter",
        )
    )

    return checks


def validate_claude_md() -> list[Check]:
    """Validate CLAUDE.md has all required sections."""
    checks = []
    path = "CLAUDE.md"

    checks.append(validate_file_exists(path, "CLAUDE.md"))
    if not Path(path).exists():
        return checks

    required_sections = [
        "agent system",
        "who this platform serves",
        "llm development phases",
        "table standards",
        "protected files",
        "dependency graph",
        "quality gates",
        "get_dataset_stats",
        "require-permission",
        "States Parties",
        "WCAG 2.2",
    ]

    checks.extend(validate_file_contains(path, "CLAUDE.md", required_sections))
    return checks


def validate_skills() -> list[Check]:
    """Validate all 15 skill files exist and have proper structure."""
    checks = []
    skills = {
        "pm-orchestrator": "PM Orchestrator",
        "data-analyst": "Data Analyst",
        "data-scientist": "Data Scientist",
        "text-analytics-expert": "Text Analytics Expert",
        "ai-engineer": "AI Engineer",
        "software-engineer": "Software Engineer",
        "ux-designer": "UX Designer",
        "qa-tester": "QA Tester",
        "devops-engineer": "DevOps Engineer",
        "stakeholder-advocate": "Stakeholder Advocate",
        "focused-pr": "Focused PR",
        "sync-requirements": "Sync Requirements",
        "model-eval-report": "Model Eval Report",
        "vignette": "Vignette",
        "compliance-audit": "Compliance Audit",
    }

    skills_dir = Path(".claude/skills")
    checks.append(
        Check(
            ".claude/skills/ directory exists",
            skills_dir.exists(),
            "" if skills_dir.exists() else "Directory missing — create .claude/skills/",
        )
    )

    for dirname, label in skills.items():
        filepath = f".claude/skills/{dirname}/SKILL.md"
        checks.append(validate_file_exists(filepath, label))
        if Path(filepath).exists():
            checks.extend(validate_skill_frontmatter(filepath, label))

    return checks


def validate_references() -> list[Check]:
    """Validate all 7 reference files exist."""
    checks = []
    references = {
        "table-standards.md": "Table Standards",
        "table-standards-enforcement.md": "Table Standards Enforcement",
        "chart-theme.md": "Chart Theme",
        "data-health.md": "Data Health",
        "wcag-audit.md": "WCAG Audit",
        "require-permission.md": "Require Permission",
        "requirements-registry.md": "Requirements Registry",
        "no-data-download.md": "No Data Download Policy",
    }

    refs_dir = Path(".claude/references")
    checks.append(
        Check(
            ".claude/references/ directory exists",
            refs_dir.exists(),
            "" if refs_dir.exists() else "Directory missing — create .claude/references/",
        )
    )

    for filename, label in references.items():
        filepath = f".claude/references/{filename}"
        checks.append(validate_file_exists(filepath, label))

    return checks


def validate_table_standards_content() -> list[Check]:
    """Validate table-standards.md has the key sections."""
    checks = []
    path = ".claude/references/table-standards.md"
    if not Path(path).exists():
        return checks

    required = [
        "governing standards",
        "tabular typography",
        "content standards",
        "decimal alignment",
        "header demarcation",
        "unit factoring",
        "precision constraint",
        "enforcement tiers",
        "tier 1",
        "tier 2",
        "quick reference checklist",
        "IBCS",
        "APA",
    ]
    checks.extend(validate_file_contains(path, "table-standards.md", required))
    return checks


def validate_pm_skill_content() -> list[Check]:
    """Validate PM orchestrator has all required sections."""
    checks = []
    path = ".claude/skills/pm-orchestrator/SKILL.md"
    if not Path(path).exists():
        return checks

    required = [
        "agent registry",
        "dependency graph",
        "team assembly",
        "task decomposition",
        "workflow execution",
        "quality gates",
        "post-implementation review",
        "llm phase track",
        "PHASE_TRACKER",
        "conflict resolution",
        "workflow patterns",
        "what you never do",
    ]
    checks.extend(validate_file_contains(path, "PM Orchestrator", required))
    return checks


def validate_role_skills_content() -> list[Check]:
    """Validate role skills have key cross-cutting sections.

    Only domain specialists that produce stakeholder-facing output are checked.
    Intentionally excluded:
    - devops-engineer: infrastructure role, never produces tables or stakeholder content
    - qa-tester: checked for permission gate only (stakeholder output gate added separately)
    - Utility skills (focused-pr, sync-requirements, model-eval-report, vignette): task-specific
    """
    checks = []
    role_skills = {
        ".claude/skills/data-analyst/SKILL.md": "Data Analyst",
        ".claude/skills/data-scientist/SKILL.md": "Data Scientist",
        ".claude/skills/text-analytics-expert/SKILL.md": "Text Analytics Expert",
        ".claude/skills/ai-engineer/SKILL.md": "AI Engineer",
        ".claude/skills/software-engineer/SKILL.md": "Software Engineer",
    }

    cross_cutting = [
        "permission gate",
        "States Parties",
        "table-standards",
        "stakeholder output gate",
    ]

    for filepath, label in role_skills.items():
        if not Path(filepath).exists():
            continue
        checks.extend(validate_file_contains(filepath, label, cross_cutting))

    return checks


def validate_no_download_policy() -> list[Check]:
    """Validate that no src/*.py files contain st.download_button (no-data-download policy)."""
    checks = []
    src_dir = Path("src")
    if not src_dir.exists():
        checks.append(Check("src/ directory exists for download scan", False, "src/ not found"))
        return checks

    violations = []
    for py_file in sorted(src_dir.glob("*.py")):
        content = py_file.read_text(encoding="utf-8")
        in_docstring = False
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            # Track docstring boundaries (triple quotes)
            if '"""' in stripped or "'''" in stripped:
                # Count triple quotes on this line
                dq_count = stripped.count('"""')
                sq_count = stripped.count("'''")
                total = dq_count + sq_count
                if total == 1:
                    in_docstring = not in_docstring
                # If 2+ on same line, it's an open+close on one line — no state change
            if "st.download_button" in line and not stripped.startswith("#") and not in_docstring:
                violations.append(f"{py_file}:{i}")

    if violations:
        checks.append(
            Check(
                "No st.download_button in src/ (no-data-download policy)",
                False,
                f"Data download policy violation: st.download_button found in {', '.join(violations)}",
            )
        )
    else:
        checks.append(
            Check(
                "No st.download_button in src/ (no-data-download policy)",
                True,
            )
        )

    # Also check app.py
    app_path = Path("app.py")
    if app_path.exists():
        content = app_path.read_text(encoding="utf-8")
        app_violations = []
        for i, line in enumerate(content.splitlines(), 1):
            if "st.download_button" in line and not line.strip().startswith("#"):
                app_violations.append(f"app.py:{i}")
        if app_violations:
            checks.append(
                Check(
                    "No st.download_button in app.py (no-data-download policy)",
                    False,
                    f"Data download policy violation: st.download_button found in {', '.join(app_violations)}",
                )
            )
        else:
            checks.append(
                Check(
                    "No st.download_button in app.py (no-data-download policy)",
                    True,
                )
            )

    return checks


def validate_supporting_files() -> list[Check]:
    """Validate key project files exist."""
    checks = []
    files = {
        "data/crpd_reports.csv": "Primary dataset",
        "src/data_loader.py": "Data loader",
        "src/analysis.py": "Analysis module",
        "src/colors.py": "Colors module",
        "scripts/table_lint.py": "Table linter",
        "scripts/wcag_audit.py": "WCAG audit script",
    }

    for filepath, label in files.items():
        checks.append(validate_file_exists(filepath, label))

    return checks


def validate_phase_tracker() -> list[Check]:
    """Validate PHASE_TRACKER.md exists and has proper structure."""
    checks = []
    path = "LLM_Development/PHASE_TRACKER.md"

    checks.append(validate_file_exists(path, "PHASE_TRACKER"))
    if not Path(path).exists():
        return checks

    content = Path(path).read_text(encoding="utf-8")

    # Check for all 5 phases
    for i, name in enumerate(
        ["AI Insights Panel", "Chat Q&A", "RAG", "Policy Brief", "Evaluation"], 1
    ):
        found = f"Phase {i}" in content
        checks.append(
            Check(
                f"PHASE_TRACKER has Phase {i} ({name})",
                found,
                "" if found else f"Phase {i} missing",
            )
        )

    # Check no duplicate phase section headers (## Phase N)
    phase_3_headers = content.count("## Phase 3")
    no_dup = phase_3_headers <= 1
    checks.append(
        Check(
            "No duplicate Phase 3 section header",
            no_dup,
            ""
            if no_dup
            else f"'## Phase 3' header appears {phase_3_headers} times — duplicate section",
        )
    )

    return checks


def main():
    print("=" * 60)
    print("CRPD Dashboard — Agent System Validation")
    print("=" * 60)

    all_checks = []
    sections = [
        ("CLAUDE.md", validate_claude_md),
        ("Skill Files (15)", validate_skills),
        ("Reference Files (8)", validate_references),
        ("Table Standards Content", validate_table_standards_content),
        ("PM Orchestrator Content", validate_pm_skill_content),
        ("Role Skills Cross-Cutting", validate_role_skills_content),
        ("Supporting Project Files", validate_supporting_files),
        ("LLM Phase Tracker", validate_phase_tracker),
        ("No-Data-Download Policy", validate_no_download_policy),
    ]

    for section_name, validator in sections:
        print(f"\n{'─' * 40}")
        print(f"  {section_name}")
        print(f"{'─' * 40}")
        checks = validator()
        all_checks.extend(checks)
        for check in checks:
            print(check)

    # Summary
    passed = sum(1 for c in all_checks if c.passed)
    failed = sum(1 for c in all_checks if not c.passed)
    total = len(all_checks)

    print(f"\n{'=' * 60}")
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 60}")

    if failed > 0:
        print("\nFailed checks:")
        for c in all_checks:
            if not c.passed:
                print(f"  ❌ {c.name} — {c.detail}")
        print(f"\nFix the {failed} failure(s) above before functional testing.")
        sys.exit(1)
    else:
        print("\nAll structural checks passed. Ready for functional testing.")
        sys.exit(0)


if __name__ == "__main__":
    main()
