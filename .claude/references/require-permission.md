# Require-Permission Reference — Change Approval Gate

**Embedded in:** All role skills (pm-orchestrator, software-engineer, data-analyst,
data-scientist, text-analytics-expert, ai-engineer, ux-designer, qa-tester, devops-engineer,
stakeholder-advocate)

## The Protocol

### Step 1: Freeze — do not touch any file yet

Before writing a single line of code, stop. Understand exactly what files will change and why.

### Step 2: Present the Change Summary

```
📋 Proposed Change — Awaiting Your Approval

What: [One sentence describing what will be done]

Why: [One sentence explaining the reason]

Files that will be modified:
- `path/to/file.py` — line N — exact current code → exact replacement code
- `path/to/other.py` — lines N–M — [describe the block and replacement]

Files that will NOT be touched: [list any related files left alone]

Reversibility: [Easy to undo? e.g., "Easily reversed with git revert"]

Do you approve this change? (yes / no)
```

### Step 3: Wait for explicit "yes"

Accept only: "yes", "go ahead", "approved", "do it", "proceed" — or any unambiguous affirmative.

If the user says "no", "stop", "hold on", "wait" — abort completely.

### Step 4: Execute only what was approved

If you discover mid-implementation that additional files need to change, stop again and present a new summary.

## What requires permission

- Editing any `.py`, `.md`, `.toml`, `.txt`, `.json`, `.yaml`, `.sh` file
- Creating or deleting a file
- Updating `LLM_Development/PHASE_TRACKER.md`
- Running any script that writes output to the project directory

## Stakeholder Advocate Authority

The Stakeholder Advocate can **FLAG** or **BLOCK** user-facing changes with
justification, but **cannot approve**. Approval is human-only. The Stakeholder
Advocate's verdicts (APPROVE/CHANGES REQUESTED/BLOCK) are recommendations to the
human, not autonomous approvals. The Stakeholder Advocate does not modify files —
it reviews and reports. No permission gate is needed for its read-only review work.

## What does NOT require permission (read-only)

- Reading files to understand the codebase
- Running `ruff check .` (read-only lint check)
- Checking git status or git log
- Reporting findings, status, or analysis to the user
