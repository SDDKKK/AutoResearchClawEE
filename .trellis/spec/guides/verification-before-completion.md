# Verification Before Completion

> Adapted from [Superpowers](https://github.com/obra/superpowers) for Trellis workflow.

## Iron Law

**NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE.**

Every claim that something "works" or "passes" must be backed by a command you ran
in the current message, with output you read and confirmed.

## Gate Function

BEFORE claiming any status (lint passes, tests pass, feature works):

1. **IDENTIFY** -- What command proves this claim?
2. **RUN** -- Execute the FULL command right now (not from memory)
3. **READ** -- Read the complete output, check exit code
4. **VERIFY** -- Does the output actually confirm the claim?
5. **ONLY THEN** -- Make the claim, citing the output

## Trellis-Specific Verification Commands

| Claim | Required Command |
|-------|-----------------|
| Lint passes | `uv run ruff check .` |
| Format passes | `uv run ruff format --check .` |
| Tests pass | `uv run pytest tests/ -q` |
| No type errors | `mcp__ide__getDiagnostics` |
| Feature works | Run the actual feature and show output |

## Red Flags (Prohibited Patterns)

These phrases indicate a verification gap. Do NOT use them:

- "should pass now" / "should be fixed"
- "looks correct" / "appears to work"
- "based on the previous run..."
- "the tests passed earlier"
- "I believe this is correct"
- Expressing satisfaction or confidence before running verification
- Trusting a previous run's output instead of re-running
- Trusting another agent's success report without independent verification

## Correct Patterns

- "Running `uv run ruff check .` now... Output: `All checks passed.` Exit code 0."
- "Verified: `uv run pytest tests/test_x.py -q` shows 5 passed, 0 failed."
- "getDiagnostics returned 0 errors for `src/module.py`."

## When This Applies

- Before claiming implementation is complete (implement agent)
- Before claiming all checks pass (check agent)
- Before outputting completion markers (review agent)
- Before marking a task as done (finish phase)
- After every fix -- re-run the failing command to confirm

## Integration with Ralph Loop

The Ralph Loop enforces verification programmatically for check/review agents.
This spec extends that principle to ALL agents, including implement and finish,
where Ralph Loop does not run.

## Core Principle

> Trust nothing. Verify everything. Show your evidence.
