# Codex Assist Guide

> **Purpose**: Route agents to Codex CLI for cross-model second opinions, code review, and feasibility analysis. Codex is called via Bash, not MCP -- any agent with Bash tool can use it.

---

## The Problem

Agents sometimes benefit from a second model's perspective -- reviewing scientific code, diagnosing subtle bugs, or evaluating requirement feasibility. Codex CLI provides this via `codex_bridge.py`, but it is **slow** (default timeout 600s) and should only be used when the benefit justifies the cost.

---

## When to Use Codex

**Use when**:
- You need a cross-model review of scientifically critical code (formulas, algorithms)
- You're stuck on a bug and want a second opinion
- You need to evaluate whether a requirement is technically feasible
- You want to validate a complex diff before committing

**Do NOT use when**:
- The task is straightforward (simple refactor, typo fix, config change)
- You can verify correctness yourself (ruff, pytest, checkcode)
- Speed matters more than thoroughness
- The question is about library API usage (use Context7 instead)

---

## Command Templates

Script path: `~/.claude/skills/with-codex/scripts/codex_bridge.py`

### Exec Mode (general tasks)

```bash
python3 ~/.claude/skills/with-codex/scripts/codex_bridge.py \
  --mode exec --cd "$(pwd)" --full-auto --ephemeral \
  --timeout 600 --idle-timeout 90 \
  --inject-context implement \
  --PROMPT "Your task description"
```

### Review Mode (diff-aware code review)

```bash
python3 ~/.claude/skills/with-codex/scripts/codex_bridge.py \
  --mode review --cd "$(pwd)" --full-auto \
  --timeout 600 --idle-timeout 90 \
  --inject-context review \
  --uncommitted
```

### Resume Mode (multi-turn follow-up)

```bash
python3 ~/.claude/skills/with-codex/scripts/codex_bridge.py \
  --mode resume --SESSION_ID "<uuid>" --PROMPT "Follow-up question"
```

### Output Format

All modes return JSON:
```json
{"success": true, "SESSION_ID": "uuid", "agent_messages": "...", "usage": {...}}
```

Parse `agent_messages` for the response content. Save `SESSION_ID` if you need follow-up.

---

## Agent-Specific Patterns

### review agent: Cross-Model Review

Use `--mode review` to get Codex's perspective on uncommitted changes:

```bash
python3 ~/.claude/skills/with-codex/scripts/codex_bridge.py \
  --mode review --cd "$(pwd)" --full-auto \
  --inject-context review \
  --uncommitted --timeout 600 --idle-timeout 90
```

Best for D1 (Scientific Correctness) verification on formula-heavy code.

### debug agent: Second-Opinion Diagnosis

Use `--mode exec` when stuck on a non-obvious bug:

```bash
python3 ~/.claude/skills/with-codex/scripts/codex_bridge.py \
  --mode exec --cd "$(pwd)" --full-auto --ephemeral \
  --timeout 600 --idle-timeout 90 \
  --inject-context debug \
  --PROMPT "Analyze this error and suggest root cause: <error details>"
```

### plan agent: Requirement Feasibility

Use `--mode exec --ephemeral` to evaluate whether a requirement is implementable:

```bash
python3 ~/.claude/skills/with-codex/scripts/codex_bridge.py \
  --mode exec --cd "$(pwd)" --full-auto --ephemeral \
  --timeout 600 --idle-timeout 90 \
  --inject-context implement \
  --PROMPT "Evaluate feasibility: <requirement description>"
```

### research agent: Deep Analysis

Use `--mode exec` for complex codebase analysis that benefits from a second model:

```bash
python3 ~/.claude/skills/with-codex/scripts/codex_bridge.py \
  --mode exec --cd "$(pwd)" --full-auto --ephemeral \
  --timeout 600 --idle-timeout 90 \
  --inject-context implement \
  --PROMPT "Analyze the architecture of <module> and identify potential issues"
```

---

## Error Handling and Degradation

| Error | Recovery |
|-------|----------|
| Idle timeout (90s no output) | Codex stalled; retry with simpler prompt or reduce scope |
| Total timeout (600s default) | Task too large; split into smaller questions |
| Partial result (`"partial": true`) | Use partial `agent_messages` if available; complete analysis yourself |
| `codex` CLI not installed | Skip Codex step; rely on own analysis |
| `success: false` in output | Read `error` field; retry once with simpler prompt |
| Empty `agent_messages` | Codex had nothing to add; proceed without it |

**Degradation rule**: Codex is always optional. If unavailable or slow, proceed with your own analysis and note that Codex was skipped.

---

## Anti-Patterns

| Wrong | Right |
|-------|-------|
| Call Codex for every review | Only call for scientifically critical or complex code |
| Use Codex for API lookups | Use Context7 (Layer 0) for library docs |
| Forget `--ephemeral` on one-off queries | Always add `--ephemeral` unless you need multi-turn |
| Ignore Codex timeout in tight loops | Use `--idle-timeout 60` for quick exec, `--timeout 600` for long tasks |
| Block on Codex failure | Codex is optional; degrade gracefully |

---

## Long Task Background Mode

For tasks that may run longer than the Bash tool's timeout, use `--background` with `--status-file` and Claude Code's `run_in_background`:

### Launch in Background

```bash
# Use run_in_background=true, timeout=600000 in Bash tool
python3 ~/.claude/skills/with-codex/scripts/codex_bridge.py \
  --background --status-file /tmp/codex_$(date +%s).json \
  --mode exec --cd "$(pwd)" --full-auto --timeout 600 --idle-timeout 90 \
  --PROMPT "Your long-running task"
```

### Poll Status

Read the status file to check progress:

```bash
cat /tmp/codex_<timestamp>.json
```

Status file format:
```json
{
  "phase": "running",
  "updated_at": "2026-02-22T12:41:30Z",
  "last_event": "item.completed",
  "events_count": 5,
  "thread_id": "uuid-or-null",
  "done": false,
  "result": null
}
```

Phase values: `starting` -> `running` -> `completed` | `failed` | `timeout`

When `done: true`, the `result` field contains the final output JSON (same format as synchronous mode).

---

## Oracle Pattern (query-type)

Inspired by AMP's Oracle mode: use Codex as a **read-only consultant** instead of an executor.

### When to Use Oracle vs Exec

| Situation | Use |
|-----------|-----|
| Need analysis/diagnosis, not code changes | `--query-type diagnose` |
| Review logic correctness of a formula | `--query-type review-logic` |
| Evaluate if an approach is feasible | `--query-type evaluate` |
| Want alternative design suggestions | `--query-type suggest` |
| Need Codex to actually write/modify files | `--mode exec` (no query-type) |

### What `--query-type` Does Automatically

- Forces `--dangerously-bypass-approvals-and-sandbox` (same as exec mode)
- Relies on prompt instruction ("Do NOT modify any files") + `--ephemeral` for safety
- Note: `-s read-only` sandbox is NOT used — it blocks Codex tool execution causing infinite loops
- Forces `--ephemeral` (no session persistence)
- Lowers timeouts: `review-logic` uses 300s/60s (needs file reading); others use 180s/45s
- Prepends a role-specific instruction to PROMPT

### Internal Flag Mapping (v2025-02-25)

`--full-auto` is the bridge's CLI flag; internally it maps to Codex CLI's `--dangerously-bypass-approvals-and-sandbox` for all modes (exec/resume/review/Oracle). Oracle mode relies on prompt constraints + `--ephemeral` instead of sandbox restrictions — `-s read-only` causes Codex to loop indefinitely when tool execution is blocked.

### Command Templates

```bash
# Diagnose a bug
python3 ~/.claude/skills/with-codex/scripts/codex_bridge.py \
  --mode exec --cd "$(pwd)" --full-auto \
  --query-type diagnose --inject-context debug \
  --PROMPT "Function X returns None when input has empty list. Error trace: ..."

# Review scientific correctness
python3 ~/.claude/skills/with-codex/scripts/codex_bridge.py \
  --mode exec --cd "$(pwd)" --full-auto \
  --query-type review-logic --inject-context implement \
  --PROMPT "Review the FMEA calculation in src/reliability/fmea.py for correctness"

# Evaluate feasibility
python3 ~/.claude/skills/with-codex/scripts/codex_bridge.py \
  --mode exec --cd "$(pwd)" --full-auto \
  --query-type evaluate --inject-context implement \
  --PROMPT "Is it feasible to parallelize the topology converter with multiprocessing?"

# Get architecture suggestions
python3 ~/.claude/skills/with-codex/scripts/codex_bridge.py \
  --mode exec --cd "$(pwd)" --full-auto \
  --query-type suggest --inject-context implement \
  --PROMPT "Suggest approaches to reduce duplication between bus_branch and node_breaker modules"
```

### Agent Self-Consultation Heuristic

Agents with Bash access MAY consult Codex oracle when:
- Stuck after 2+ failed attempts on a complex problem
- Reviewing scientifically critical code (formulas, algorithms)
- Uncertain about architectural trade-offs

Do NOT consult when:
- The problem is straightforward
- You can verify correctness with ruff/pytest/checkcode
- Speed is more important than thoroughness

---

## Core Principle

> **Codex is a second opinion, not a dependency.** Use it when cross-model validation adds real value. Skip it when you can verify correctness yourself.

---

## Context Passthrough (Scheme C)

When Codex is invoked as a Trellis subagent (`codex-implement`, etc.), the full context is passed via **temp file** rather than re-reading jsonl.

### Architecture

```
Hook assembles full context (specs + prd + memory + TDD)
  → writes to temp file: /tmp/trellis-codex-ctx-{pid}-{timestamp}.md
  → passes temp file path to Wrapper Agent prompt
    → Wrapper calls: codex_bridge.py --context-file /tmp/trellis-codex-ctx-xxx.md
      → Bridge reads temp file as full context (NO re-reading jsonl)
        → Codex receives complete context via stdin pipe
```

### Why Temp File?

- Wrapper agent is AI — constructing heredoc in bash is unreliable
- Hook already assembles complete context — no need to duplicate logic
- Temp file with PID+timestamp avoids concurrency conflicts
- System cleans up `/tmp` if wrapper fails to remove file

### Backward Compatibility

- `--context-file` takes priority over `--inject-context`
- Ad-hoc calls without `--context-file` still use `--inject-context` (jsonl only)
- All existing commands continue to work

### Cleanup

Wrapper agent **must** remove the temp file after Codex completes:

```bash
rm -f /tmp/trellis-codex-ctx-xxx.md
```

---

## Codex Subagent Mode (Automated)

Besides ad-hoc usage within agents, Codex can be invoked as a **first-class Trellis subagent** via the `codex-{base}` convention. This is useful when you want Codex to perform the primary implementation/check/debug/review work instead of Claude.

### How It Works

```
Task(subagent_type="codex-implement")
    → Hook assembles full context (specs + prd + memory + TDD)
    → Hook writes context to temp file: /tmp/trellis-codex-ctx-xxx.md
    → Wrapper Agent (Claude sonnet) orchestrates:
        1. Calls codex_bridge.py --context-file /tmp/trellis-codex-ctx-xxx.md
        2. Codex receives complete context from temp file
        3. Wrapper reports results
        4. Wrapper removes temp file
```

### Available Codex Subagents

| Subagent Type | Base Agent | Context Source | Codex Mode |
|---------------|-----------|----------------|------------|
| `codex-implement` | implement | implement.jsonl | `--mode exec` |
| `codex-check` | check | check.jsonl | `--mode exec` |
| `codex-debug` | debug | debug.jsonl | `--mode exec` |
| `codex-review` | review | review.jsonl | `--mode review` |

Each requires a corresponding `.claude/agents/codex-{base}.md` file. MVP ships with `codex-implement`.

### Usage in task.json

```json
{
  "next_action": [
    {"phase": 1, "action": "codex-implement"},
    {"phase": 2, "action": "check"},
    {"phase": 3, "action": "finish"},
    {"phase": 4, "action": "create-pr"}
  ]
}
```

### Usage in Mode 1 (Direct Development)

```
Task(
  subagent_type: "codex-implement",
  prompt: "Implement the feature described in prd.md using Codex CLI"
)
```

### Adding New Codex Subagents

To add `codex-check` (example):

1. Create `.claude/agents/codex-check.md` (copy codex-implement.md, change name/description)
2. Add `action: "codex-check"` section to `dispatch.md`
3. Add entry to `manifest.json` as `shared`

No hook changes needed — `codex-` prefix matching handles routing automatically.

### Codex Subagent vs Ad-hoc Codex

| Aspect | Subagent (`codex-implement`) | Ad-hoc (`with-codex` skill) |
|--------|------------------------------|---------------------------|
| Trigger | `Task(subagent_type=...)` | Manual Bash call |
| Context | Auto-injected via `--context-file` (full context) | `--inject-context` flag (jsonl only) |
| Orchestration | Dispatch can manage | Agent manages manually |
| Result | Structured report | Raw JSON |
| Use case | Primary executor in workflow | Second opinion / consultation |

### CCR Model Routing (Optional)

The `agent-models.json` entry for `codex-implement` configures the **Wrapper Agent** (Claude), NOT Codex itself. Codex uses its own model from `~/.codex/config.toml`.

Since the wrapper only orchestrates (read prompt → call Bash → parse JSON → report), it works fine with any model. Configuring CCR routing is optional:

```json
{
  "codex-implement": "阿里-Code,glm-5"
}
```

If omitted, the wrapper uses CCR's default route. Codex's model is always independent.

---

## Main Agent Usage

When the main agent (user's direct Claude Code session) calls Codex ad-hoc, use `--inject-context` to automatically inject project specs.

### Type Selection Guide

| Intent | `--inject-context` value |
|--------|--------------------------|
| Evaluate plan/approach feasibility | `implement` |
| Review code quality | `review` |
| Analyze/diagnose a bug | `debug` |
| General analysis (no clear type) | omit -- rely on AGENTS.md baseline context |

### PROMPT Construction

- `--inject-context` handles spec injection automatically; PROMPT only needs to describe "what Codex should do"
- The main agent has full conversation context that Codex cannot see -- condense key information into PROMPT
- Keep PROMPT focused: error messages, file paths, specific questions

### Result Integration

- Parse `agent_messages` from the returned JSON
- Integrate findings into your current reasoning
- Save `SESSION_ID` if follow-up is needed (`--mode resume`)
