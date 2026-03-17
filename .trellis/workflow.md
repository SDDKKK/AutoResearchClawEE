# Development Workflow

> Based on [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

## Table of Contents

1. [Quick Start](#quick-start)
2. [Workflow Overview](#workflow-overview)
3. [Development Modes](#development-modes)
4. [Mode 1: Direct Development](#mode-1-direct-development)
5. [Mode 2: Multi-Agent Pipeline](#mode-2-multi-agent-pipeline)
6. [Agent System](#agent-system)
7. [Ralph Loop (Quality Enforcement)](#ralph-loop-quality-enforcement)
8. [Failure Modes & Recovery](#failure-modes--recovery)
9. [Session End](#session-end)
10. [File Descriptions](#file-descriptions)
11. [Best Practices](#best-practices)
12. [Quick Reference](#quick-reference)
13. [Appendix: Worked Example (Mode 1)](#appendix-worked-example-mode-1)

## Quick Start

### Step 0: Initialize Developer Identity (First Time Only)

> **Multi-developer support**: Each developer/Agent needs to initialize their identity first

```bash
# Check if already initialized
python3 ./.trellis/scripts/get_developer.py

# If not initialized, run:
python3 ./.trellis/scripts/init_developer.py <your-name>
# Example: python3 ./.trellis/scripts/init_developer.py claude-agent
```

This creates:
- `.trellis/.developer` - Your identity file (gitignored, not committed)
- `.trellis/workspace/<your-name>/` - Your personal workspace directory

### Step 1: Understand Current Context

```bash
# Get full context in one command
python3 ./.trellis/scripts/get_context.py

# Or check manually:
python3 ./.trellis/scripts/get_developer.py      # Your identity
python3 ./.trellis/scripts/task.py list          # Active tasks
git status && git log --oneline -10      # Git state
```

### Step 2: Read Project Guidelines [MANDATORY]

**CRITICAL**: Read guidelines before writing any code:

```bash
cat .trellis/spec/python/index.md    # Python guidelines
cat .trellis/spec/matlab/index.md    # MATLAB guidelines
```

**Pro Tip**: Before searching for code, read [Codebase Search Guide](spec/guides/codebase-search-guide.md) to learn when to use semantic search vs grep.

### Step 3: Read Specific Guidelines (Based on Task)

**Python Task**:
```bash
cat .trellis/spec/python/code-style.md          # Code style
cat .trellis/spec/python/data-processing.md     # Data logic (polars)
cat .trellis/spec/python/docstring.md           # Documentation
```

**MATLAB Task**:
```bash
cat .trellis/spec/matlab/code-style.md          # Code style
cat .trellis/spec/matlab/quality-guidelines.md  # checkcode
cat .trellis/spec/matlab/docstring.md           # Documentation
```

---

## Workflow Overview

### Core Principles

1. **Read Before Write** - Understand context before starting
2. **Follow Standards** - Read and follow `.trellis/spec/` guidelines (→ Non-negotiables)
3. **Specs Injected, Not Remembered** - Hooks enforce specs; agents always receive context
4. **Memory Persists Across Sessions** - Decisions, issues, and learnings survive context resets
5. **Incremental Development** - Complete one task at a time
6. **Record Promptly** - Update tracking files immediately after completion
7. **Document Limits** - Keep journals readable and within limits (→ Non-negotiables)

### Non-negotiables

These rules apply to **every task, every session, no exceptions**:

1. **Read specs before coding** — `cat .trellis/spec/{python,matlab}/index.md` then task-specific docs → [Quick Start Step 2](#step-2-read-project-guidelines-mandatory)
2. **Journal files ≤ 2000 lines** — `add_session.py` rotates automatically → [Workspace System](#1-workspace---developer-workspaces)
3. **Mode 1: human commits only** — AI proposes, human validates and runs `git commit` → [Mode 1 Flow](#mode-1-direct-development)

### System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       USER INTERACTION                            │
│  /trellis:start  /trellis:parallel  /trellis:finish-work         │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                        SKILLS LAYER                               │
│  .claude/commands/trellis/*.md    (slash commands)                │
│  .claude/agents/*.md              (sub-agent definitions)        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                         HOOKS LAYER                               │
│  SessionStart     → session-start.py (injects workflow+context)  │
│  PreToolUse:Task  → inject-subagent-context.py (spec injection)  │
│  SubagentStop     → ralph-loop.py (quality enforcement)          │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                      PERSISTENCE LAYER                            │
│  .trellis/workspace/  (journals, session history)                │
│  .trellis/tasks/      (task tracking, context files)             │
│  .trellis/spec/       (coding guidelines)                        │
└──────────────────────────────────────────────────────────────────┘
```

### File System

```
.trellis/
|-- .developer              # Developer identity (gitignored)
|-- .current-task           # Pointer to active task directory
|-- .ralph-state.json       # Ralph Loop state (auto-managed)
|-- workflow.md             # This document
|-- worktree.yaml           # Worktree + verify config
|-- scripts/
|   |-- common/             # Shared utilities
|   |-- init_developer.py   # Initialize developer identity
|   |-- get_developer.py    # Get current developer name
|   |-- get_context.py      # Get session context
|   |-- task.py             # Manage tasks
|   |-- add_session.py      # One-click session recording
|   \-- multi_agent/        # Multi-Agent Pipeline scripts
|       |-- plan.py         # Launch Plan Agent
|       |-- start.py        # Create worktree + start Dispatch
|       |-- status.py       # Monitor running sessions
|       |-- create_pr.py    # Commit + push + create Draft PR
|       \-- cleanup.py      # Remove worktree + archive task
|-- workspace/              # Developer workspaces
|   |-- index.md            # Workspace index
|   \-- {developer}/        # Per-developer directories
|       |-- index.md        # Personal index (@@@auto markers)
|       \-- journal-N.md    # Journal files (sequential; rotated by add_session.py)
|-- tasks/                  # Task tracking
|   |-- {MM}-{DD}-{slug}/   # Active task directories
|   |   |-- task.json       # Metadata, phases, branch config
|   |   |-- prd.md          # Requirements document
|   |   |-- implement.jsonl # Context files for implement agent
|   |   |-- check.jsonl     # Context files for check agent
|   |   \-- debug.jsonl     # Context files for debug agent
|   \-- archive/            # Completed tasks
|       \-- {YYYY-MM}/
|-- memory/                 # Structured memory (persists across sessions)
|   |-- decisions.md        # Architecture decisions log (append-only)
|   |-- known-issues.md     # Active issues and workarounds
|   |-- learnings.md        # Learning log (pattern/gotcha/convention/mistake)
|   \-- scratchpad.md       # Ephemeral WIP notes (gitignored, per-task)
\-- spec/                   # Coding guidelines (→ Non-negotiables #1)
    |-- python/             # Python guidelines
    |-- matlab/             # MATLAB guidelines
    \-- guides/             # Thinking guides
```

---

## Development Modes

Trellis supports two development modes. Choose based on task complexity and requirement clarity:

> **📝 PRD Template**: Use `.trellis/templates/prd-template.md` for writing high-quality PRDs in Mode 1.
>
> **📚 Multi-Agent Pipeline Guide**: See `.trellis/docs/multi-agent-pipeline.md` for detailed Mode 2 usage.

```
Task arrives
│
├─ Question / explanation only → Answer directly
│
├─ Trivial fix (typo, single-line) → Direct edit, no task needed
│
└─ Development task → Choose mode:
    │
    ├─ Simple (single file, clear scope)
    │  → Mode 1: Direct Development
    │
    ├─ Medium (multi-file, clear scope)
    │  → Mode 1 or Mode 2 (your choice)
    │
    └─ Complex (unclear scope, needs isolation, parallel work)
       → Mode 2: Multi-Agent Pipeline
```

| Criteria | Mode 1: Direct | Mode 2: Multi-Agent Pipeline |
|----------|----------------|------------------------------|
| **Where** | Current directory | Isolated worktree |
| **Branch** | Current branch | Dedicated feature branch |
| **Agents** | Manual (or via `/trellis:start`) | Automated (Dispatch orchestrates) |
| **Commit** | Human commits | `create_pr.py` auto-commits |
| **PR** | Manual | Auto-created as Draft PR |
| **Quality** | Manual checks | Ralph Loop enforces |
| **Use for** | Small–medium tasks | Complex tasks, parallel work |

### When to Use Mode 1 vs Mode 2

**Use Mode 1 (Direct Development) when**:
- ✅ Requirements need discussion or exploration
- ✅ You want flexibility to adjust as you go
- ✅ Task is straightforward and doesn't need isolation
- ✅ You prefer interactive development

**Use Mode 2 (Multi-Agent Pipeline) when**:
- ✅ Requirements are very clear and detailed
- ✅ Task follows a standard pattern (e.g., add API endpoint, migrate function)
- ✅ You want automated quality enforcement
- ✅ You need isolation (parallel work, experimental changes)
- ✅ You want Plan Agent to evaluate and reject unclear requirements

**Quick Decision**:
```
Is requirement crystal clear? → Yes → Try Mode 2
                              → No  → Use Mode 1
```

**Note**: Mode 2 requires running `plan.py` first. See `.trellis/docs/multi-agent-pipeline.md` for details.

---

## Mode 1: Direct Development

The standard workflow for most tasks. AI works in the current directory with human oversight.

### Flow

```
1. Create or select task
   → python3 ./.trellis/scripts/task.py create "<title>" --slug <name>

2. (Optional) Research codebase
   → Task(subagent_type="research", ...)

3. Configure context + activate task
   → python3 ./.trellis/scripts/task.py init-context <task-dir> <python|matlab|both>
   → python3 ./.trellis/scripts/task.py start <task-dir>

4. Implement
   → Task(subagent_type="implement", ...)
   → Specs auto-injected by hook via implement.jsonl

5. Check quality
   → Task(subagent_type="check", ...)
   → Specs auto-injected by hook via check.jsonl

6. Self-test
   → Python: uv run ruff check . && uv run pytest
   → MATLAB: matlab -batch "checkcode('file.m')"

7. Human commits
   → git add <files>
   → git commit -m "type(scope): description"

8. Complete task
   → python3 ./.trellis/scripts/task.py complete [task-dir]

9. Record session
   → python3 ./.trellis/scripts/add_session.py --title "Title" --commit "hash"
```

### Code Quality Checklist

**Must pass before commit**:
- [OK] Python: `uv run ruff check .` passes
- [OK] MATLAB: `checkcode` shows no L1/L2 errors
- [OK] Manual feature testing passes

---

## Mode 2: Multi-Agent Pipeline

For complex tasks requiring isolation. Runs in a dedicated Git worktree with automated orchestration.

### Full Pipeline

```
Plan → Start Worktree → Dispatch → [Implement → Check → Debug]* → Create PR → Cleanup
```

### Phase 1: Plan

```bash
python3 ./.trellis/scripts/multi_agent/plan.py \
  --name <task-slug> \
  --type <python|matlab|both> \
  --requirement "<description>"
```

**What happens**:
1. Plan Agent (opus) evaluates requirements
2. Calls Research Agent to analyze codebase
3. Creates `prd.md` (requirements document)
4. Configures `task.json` (branch, scope, dev_type, phases)
5. Initializes JSONL context files (`implement.jsonl`, `check.jsonl`, `debug.jsonl`)
6. **Can REJECT** unclear/vague/too-large requirements → generates `REJECTED.md`

**Monitor**: `tail -f .trellis/tasks/MM-DD-task-name/.plan-log`

### Phase 2: Start Worktree

```bash
python3 ./.trellis/scripts/multi_agent/start.py .trellis/tasks/MM-DD-task-name
```

**What happens**:
1. Creates isolated Git worktree (in `../worktrees/`)
2. Creates new branch from `base_branch`
3. Copies environment files (per `worktree.yaml`)
4. Runs `post_create` commands (e.g., dependency install)
5. Sets `.trellis/.current-task` in worktree
6. Starts **Dispatch Agent** in background
7. Registers to `registry.json`

### Phase 3: Dispatch → Implement → Check → Debug

**Dispatch Agent** reads `task.json` and orchestrates phases automatically:

```
Dispatch reads task.json → next_action array
    │
    ├── Phase 1: implement
    │   └── Task(subagent_type="implement") — write code
    │
    ├── Phase 2: check
    │   └── Task(subagent_type="check") — review + self-fix
    │   └── Ralph Loop enforces quality (see below)
    │
    ├── Phase 3: finish (optional)
    │   └── Final verification pass
    │
    └── Phase 4: create-pr
        └── Bash("create_pr.py") — commit + push + Draft PR
```

**Monitor**:
```bash
python3 ./.trellis/scripts/multi_agent/status.py              # All sessions
python3 ./.trellis/scripts/multi_agent/status.py --watch <name> # Live watch
python3 ./.trellis/scripts/multi_agent/status.py --log <name>   # View logs
```

### Phase 4: Create PR

```bash
python3 ./.trellis/scripts/multi_agent/create_pr.py [--dry-run]
```

**What happens**:
1. Stages all changes (excludes `workspace/`)
2. Commits: `feat(<scope>): <task-name>` (commit prefix from `dev_type`)
3. Pushes to origin
4. Creates Draft PR via `gh pr create --draft`
5. Updates `task.json`: `status: "completed"`, `pr_url: "..."`

**Commit prefix mapping**:

| dev_type | Prefix |
|----------|--------|
| python, matlab, both | `feat` |
| bugfix, fix | `fix` |
| refactor | `refactor` |
| docs | `docs` |
| test | `test` |

### Phase 5: Cleanup

```bash
python3 ./.trellis/scripts/multi_agent/cleanup.py .trellis/tasks/MM-DD-task-name
```

**What happens**:
1. Archives task to `.trellis/tasks/archive/YYYY-MM/`
2. Removes from registry
3. Removes worktree: `git worktree remove <path>`
4. Optionally deletes branch

### Resuming Stopped Sessions

```bash
# Find session info
python3 ./.trellis/scripts/multi_agent/status.py --detail <task-name>

# Resume in worktree
cd ../worktrees/<branch-name>
claude --resume <session-id>
```

---

## Agent System

Specialized agents for different development phases. Each agent has specific tools and restrictions.

### Agent Types

| Agent | Purpose | Tools | Restriction |
|-------|---------|-------|-------------|
| `dispatch` | Orchestrate pipeline | Read, Bash | Pure dispatcher, no code edits |
| `plan` | Evaluate requirements | Read, Bash, Glob, Grep, Task | Can reject unclear reqs |
| `research` | Find code patterns | Read, Glob, Grep, codebase-retrieval | Read-only, no modifications |
| `implement` | Write code | Read, Write, Edit, Bash, Glob, Grep | No git commit |
| `check` | Review + self-fix | Read, Write, Edit, Bash, Glob, Grep | Controlled by Ralph Loop |
| `debug` | Fix specific issues | Read, Write, Edit, Bash, Glob, Grep | Precise fixes only, no refactor |

### Context Injection (How Specs Reach Agents)

```
Task(subagent_type="implement") called
        │
        ▼
PreToolUse hook fires → inject-subagent-context.py
        │
        ├── Read .trellis/.current-task
        │
        ├── Find task directory
        │
        ├── Load implement.jsonl
        │   {"file": ".trellis/spec/python/code-style.md", "reason": "..."}
        │   {"file": "researchclaw/pipeline/stages.py", "reason": "..."}
        │
        ├── Read each file's content
        │
        └── Build new prompt with injected context
```

### JSONL Context Files

Each task directory contains JSONL files that configure what context each agent receives:

```jsonl
{"file": ".trellis/spec/python/code-style.md", "reason": "Python code style"}
{"file": ".trellis/spec/python/data-processing.md", "reason": "Polars patterns"}
{"file": "researchclaw/pipeline/stages.py", "reason": "Existing pipeline stages"}
```

| File | Agent | Purpose |
|------|-------|---------|
| `implement.jsonl` | implement | Dev specs, code patterns to follow |
| `check.jsonl` | check | Quality criteria, review specs |
| `debug.jsonl` | debug | Debug context, error reports |

### task.json Structure

```json
{
  "name": "Add literature search stage",
  "slug": "lit-search-stage",
  "created": "2026-02-13T10:30:00",
  "assignee": "claude-agent",
  "status": "active",
  "dev_type": "python",
  "scope": "pipeline",
  "branch": "feature/lit-search-stage",
  "base_branch": "main",
  "current_phase": 1,
  "next_action": [
    {"phase": 1, "action": "implement"},
    {"phase": 2, "action": "check"},
    {"phase": 3, "action": "finish"},
    {"phase": 4, "action": "create-pr"}
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `dev_type` | string | `python`, `matlab`, `both` |
| `scope` | string | Module name (e.g., `pipeline`, `literature`, `agents`) |
| `branch` | string | Git branch (required for Multi-Agent Pipeline) |
| `base_branch` | string | PR target branch |
| `current_phase` | number | Current workflow phase |
| `next_action` | array | Workflow phase definitions |
| `status_history` | array | Status transition log (auto-managed) |

### Task Status State Machine

```
planning → active → review → completed
              ↕        ↓
           blocked   active (回退重做)
planning → rejected (终态)
```

| From | Allowed To | Trigger |
|------|-----------|---------|
| `planning` | `active`, `rejected` | implement agent / manual reject |
| `active` | `review`, `blocked` | check agent / blocker found |
| `review` | `active`, `completed` | rework needed / approved |
| `blocked` | `active` | blocker resolved |

Status transitions are validated by `inject-subagent-context.py` (warns on invalid) and `task.py set-status` (blocks invalid).

---

## Ralph Loop (Quality Enforcement)

Prevents Check Agent from stopping until all verification commands pass.

```
Check Agent completes
        │
        ▼
SubagentStop hook → ralph-loop.py
        │
        ▼
Run verify commands (from worktree.yaml):
  uv run ruff check .       → exit 0 ✓
  uv run ruff format --check . → exit 1 ✗
        │
        ▼
    All pass? ─── YES ──→ Allow stop
        │
       NO
        │
        ▼
    Block stop, inject errors → Agent continues fixing
```

### Configuration

`.trellis/worktree.yaml`:
```yaml
worktree_dir: ../worktrees

copy:
  - .trellis/.developer

post_create:
  - uv sync

verify:
  - uv run ruff check .
  - uv run ruff format --check .
```

### Limits

| Constant | Value | Description |
|----------|-------|-------------|
| `MAX_ITERATIONS` | 5 | Maximum loop attempts |
| `STATE_TIMEOUT_MINUTES` | 30 | State file timeout |
| `COMMAND_TIMEOUT` | 120s | Per verify command |

### Debugging Ralph Loop

```bash
cat .trellis/.ralph-state.json          # Check state
rm .trellis/.ralph-state.json           # Reset state
uv run ruff check . && uv run ruff format --check .  # Manual verify
```

---

## Failure Modes & Recovery

> Action-first troubleshooting. Prefer **minimal, reversible** actions.
> When in doubt, **stop and ask a human** before destructive commands.

### 1) Ralph Loop Stuck

**Symptoms**: MAX_ITERATIONS reached, same error repeats, verify hangs

**Recovery**:

```bash
# 1. Run verify manually to confirm the real failure
uv run ruff check .
uv run ruff format --check .

# 2. Check and reset Ralph state
cat .trellis/.ralph-state.json
rm -f .trellis/.ralph-state.json

# 3. If verify command hangs, kill and rerun
ps aux | grep -E "(ruff|pytest)" | grep -v grep
pkill -f "ruff" || true
```

**Escalate if**: hit max iterations twice in a row, verify is flaky (intermittent), or verify depends on network/external services.

### 2) Worktree Issues (Mode 2)

**Symptoms**: worktree missing/locked, "branch already checked out", stale metadata

**Recovery**:

```bash
# Inspect all worktrees
git worktree list

# Prune stale metadata
git worktree prune -v

# Force remove a broken worktree
git worktree remove --force ../worktrees/<name>

# Branch conflict ("already checked out")
git checkout <base-branch>
# Then re-run pipeline start

# Preferred: use cleanup script
python3 ./.trellis/scripts/multi_agent/cleanup.py <task-dir>
```

**If .current-task pointer is stale**:

```bash
cat .trellis/.current-task
python3 ./.trellis/scripts/task.py list
python3 ./.trellis/scripts/task.py start <correct-task-dir>
```

### 3) Dependency Failures

**A) `uv sync` fails**:

```bash
uv sync -v                    # Rerun with verbose output
rm -rf .venv && uv sync       # Recreate venv (reversible, costs time)
uv cache clean && uv sync -v  # Clear cache if download issues
```

**B) MATLAB not found**:

```bash
which matlab || true
matlab -batch "disp(version)" || true
```

If MATLAB is required but missing: **stop and ask a human**. If not required for the current task, proceed with Python-only and note it in the session record.

### 4) Partial Progress Recovery

When a session dies mid-implement:

```bash
# 1. Rehydrate context
python3 ./.trellis/scripts/get_context.py
git status && git diff --stat

# 2. Re-open the active task
cat .trellis/.current-task
python3 ./.trellis/scripts/task.py start <task-dir>

# 3. Re-read task artifacts
cat .trellis/tasks/<task-dir>/prd.md
cat .trellis/tasks/<task-dir>/task.json

# 4. Stash risky WIP if needed (ask human first)
git stash push -u -m "wip: <task-slug>"
```

Record a "WIP checkpoint" in the journal if stopping without a commit (include `git status` + next steps).

### 5) Git Recovery

```bash
# Discard uncommitted changes (reversible via reflog)
git restore .                   # Working tree
git restore --staged .          # Unstage

# Stash WIP (fully reversible)
git stash push -u -m "wip: <task>"
git stash pop                   # Restore later

# Undo a bad commit (prefer revert if shared)
git revert <bad-commit-sha>     # Safe: creates inverse commit
git reset --soft HEAD~1         # Local only: keeps changes staged

# Lost work? Check reflog
git reflog                      # Then cherry-pick or reset
```

> ⚠️ **Escalate before**: `reset --hard`, `clean -fd`, branch deletion.

### 6) Escalation Protocol

**Stop and ask a human when**:

- Ralph Loop hits max iterations and failure is not clearly fixable
- Verify is flaky/intermittent
- Environment/tooling issues (Python toolchain, MATLAB availability, permissions)
- About to run destructive git/file commands
- Requirements are ambiguous or fix risks changing scientific meaning

**Escalation message template**:

```
What I tried: [commands + outputs]
Current state: [git status, relevant logs]
Hypothesis: [1-2 guesses]
Safest next options: [2-3 choices for human to pick]
```

---

## Session End

### One-Click Session Recording

After code is committed:

```bash
python3 ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "abc1234" \
  --summary "Brief summary"
```

This automatically:
1. Detects current journal file
2. Creates new file if 2000-line limit exceeded
3. Appends session content
4. Updates index.md (sessions count, history table)

### Pre-end Checklist

Use `/trellis:finish-work` command to run through:
1. [OK] All code committed, commit message follows convention
2. [OK] Session recorded via `add_session.py`
3. [OK] No lint/test errors
4. [OK] Working directory clean (or WIP noted)
5. [OK] Spec docs updated if needed

---

## File Descriptions

### 1. workspace/ - Developer Workspaces

**Purpose**: Record each AI Agent session's work content

```
workspace/
|-- index.md              # Main index (Active Developers table)
\-- {developer}/          # Per-developer directory
    |-- index.md          # Personal index (with @@@auto markers)
    \-- journal-N.md      # Journal files (sequential; rotated by add_session.py)
```

### 2. spec/ - Development Guidelines

**Purpose**: Documented standards, injected to agents via JSONL + hooks

```
spec/
|-- python/             # Python docs (code-style, data-processing, etc.)
|-- matlab/             # MATLAB docs (code-style, scientific-computing, etc.)
\-- guides/             # Thinking guides (cross-layer, codebase-search, etc.)
```

### 3. tasks/ - Task Tracking

**Purpose**: Work items with phase-based execution and agent context

```
tasks/
|-- {MM}-{DD}-{slug}/
|   |-- task.json           # Metadata, phases, branch
|   |-- prd.md              # Requirements document
|   |-- implement.jsonl     # Context for implement agent
|   |-- check.jsonl         # Context for check agent
|   \-- debug.jsonl         # Context for debug agent
\-- archive/
    \-- {YYYY-MM}/
```

**Commands**:
```bash
python3 ./.trellis/scripts/task.py create "<title>" [--slug <name>]
python3 ./.trellis/scripts/task.py init-context <task-dir> <python|matlab|both>
python3 ./.trellis/scripts/task.py add-context <task-dir> <implement|check> "<file>" "<reason>"
python3 ./.trellis/scripts/task.py start <task-dir>
python3 ./.trellis/scripts/task.py complete [task-dir]
python3 ./.trellis/scripts/task.py clear-current
python3 ./.trellis/scripts/task.py finish                  # alias for clear-current
python3 ./.trellis/scripts/task.py set-status <task-dir> <status>
python3 ./.trellis/scripts/task.py archive <name>
python3 ./.trellis/scripts/task.py list
```

### 4. memory/ - Structured Memory

**Purpose**: Persistent knowledge that survives session resets and context compaction

```
memory/
|-- decisions.md        # Architecture decisions (append-only, newest first)
|-- known-issues.md     # Active issues and workarounds (remove when resolved)
|-- learnings.md        # Learning log (pattern/gotcha/convention/mistake)
\-- scratchpad.md       # Ephemeral WIP notes (gitignored, overwritten per task)
```

**Knowledge flow**:
```
Session → add_session.py --learning → learnings.md → /trellis:update-spec → spec/
Debug   → /trellis:break-loop       → known-issues.md
Design  → manual entry              → decisions.md
```

**Injection**: Memory files are automatically injected to agents via `inject-subagent-context.py`:
- `implement`/`debug`: decisions.md + known-issues.md + scratchpad.md
- `check`: decisions.md only
- Session start: lightweight summary (titles only) via `session-start.py`

---

## Best Practices

### [OK] DO

1. **Before session start**:
   - Run `python3 ./.trellis/scripts/get_context.py` for full context
   - Confirm [Non-negotiables](#non-negotiables) are satisfied (specs read, journal size ok)
   - Use semantic search (codebase-retrieval) for exploring unfamiliar code

2. **During development**:
   - Follow `.trellis/spec/` guidelines
   - For cross-layer features, use `/trellis:check-cross-layer`
   - Develop only one task at a time
   - Run lint and tests frequently

3. **After development complete**:
   - Use `/trellis:finish-work` for completion checklist
   - After fix bug, use `/trellis:break-loop` for deep analysis
   - Human commits after testing passes (Mode 1)
   - Use `add_session.py` to record progress

### [X] DON'T

> Items 1-3 from [Non-negotiables](#non-negotiables) always apply. Additional don'ts:

1. **Don't** develop multiple unrelated tasks simultaneously
2. **Don't** commit code with lint/test errors
3. **Don't** forget to update spec docs after learning something

---

## Quick Reference

### Non-negotiables Reminder

→ Read specs before coding · Journals ≤ 2000 lines · Mode 1 human commits only — [Full list](#non-negotiables)

### Mode Selection

| Task Size | Recommended Mode |
|-----------|-----------------|
| Trivial (typo, single-line) | Direct edit, no task |
| Small (single file, clear scope) | Mode 1: Direct |
| Medium (multi-file) | Mode 1 or Mode 2 |
| Complex (unclear scope, parallel) | Mode 2: Multi-Agent Pipeline |

### Must-read Before Development

| Task Type | Must-read Document |
|-----------|-------------------|
| Python work | `python/index.md` → relevant docs |
| MATLAB work | `matlab/index.md` → relevant docs |
| Code search | `guides/codebase-search-guide.md` |

### Commit Convention

```bash
git commit -m "type(scope): description"
```

**Type**: feat, fix, docs, refactor, test, chore
**Scope**: Module name (e.g., pipeline, cli, agents, literature)

### Common Commands

```bash
# Session management
python3 ./.trellis/scripts/get_context.py       # Get full context
python3 ./.trellis/scripts/add_session.py       # Record session

# Task management
python3 ./.trellis/scripts/task.py list         # List tasks
python3 ./.trellis/scripts/task.py create "X"   # Create task
python3 ./.trellis/scripts/task.py complete [dir]  # Complete task (status + cleanup)
python3 ./.trellis/scripts/task.py set-status <dir> <status>  # Update task status

# Multi-Agent Pipeline
python3 ./.trellis/scripts/multi_agent/plan.py --name <slug> --type <type> --requirement "<desc>"
python3 ./.trellis/scripts/multi_agent/start.py <task-dir>
python3 ./.trellis/scripts/multi_agent/status.py
python3 ./.trellis/scripts/multi_agent/create_pr.py
python3 ./.trellis/scripts/multi_agent/cleanup.py <task-dir>

# Slash commands
/trellis:start                  # Start session (Mode 1 flow)
/trellis:parallel               # Start session (Mode 2 flow)
/trellis:finish-work            # Pre-commit checklist
/trellis:break-loop             # Post-debug analysis
/trellis:check-cross-layer      # Cross-layer verification
/trellis:record-session         # Record completed session
```

---

## Appendix: Worked Example (Mode 1)

Real case: add a new literature search stage to the research pipeline.

### 1) Create task

```bash
TASK_DIR=$(python3 ./.trellis/scripts/task.py create \
  "Add literature search stage" --slug lit-search-stage)
```

### 2) Research codebase

```text
Task(subagent_type="research", prompt="Analyze researchclaw/pipeline/:
  - Identify existing pipeline stages and their interfaces
  - Find relevant data structures (StageResult, PipelineConfig)
  - List relevant specs in .trellis/spec/python/")
```

### 3) Configure context + activate

```bash
python3 ./.trellis/scripts/task.py init-context "$TASK_DIR" python
python3 ./.trellis/scripts/task.py add-context "$TASK_DIR" implement \
  "researchclaw/pipeline/stages.py" "Existing pipeline stages"
python3 ./.trellis/scripts/task.py add-context "$TASK_DIR" implement \
  ".trellis/spec/python/data-processing.md" "Polars patterns for data loading"
python3 ./.trellis/scripts/task.py add-context "$TASK_DIR" check \
  ".trellis/spec/python/code-style.md" "Ruff compliance rules"
python3 ./.trellis/scripts/task.py start "$TASK_DIR"
```

### 4) PRD (in `$TASK_DIR/prd.md`)

```markdown
# Add Literature Search Stage

## Goal
Implement a literature search stage that queries academic APIs.

## Target modules
- researchclaw/literature/search.py (search logic)
- researchclaw/literature/models.py (result models)
- researchclaw/pipeline/stages.py (register stage)
- tests/test_rc_literature.py (tests)

## Acceptance Criteria
- [ ] `uv run ruff check .` passes
- [ ] `uv run pytest tests/test_rc_literature.py` passes
- [ ] All public functions have docstrings
```

### 5) Implement + Check

```text
Task(subagent_type="implement", prompt="Implement per PRD. Follow injected specs.")
Task(subagent_type="check", prompt="Review changes. Fix issues. Run ruff + pytest.")
```

### 6) Self-test + Human commit

```bash
uv run ruff check . && uv run ruff format --check .
uv run pytest tests/test_rc_literature.py -q
git add researchclaw/literature/ researchclaw/pipeline/stages.py tests/test_rc_literature.py
git commit -m "feat(literature): add literature search stage"
```

### 7) Complete task

```bash
python3 ./.trellis/scripts/task.py complete "$TASK_DIR"
```

### 8) Record session

```bash
python3 ./.trellis/scripts/add_session.py \
  --title "Literature search stage" \
  --commit "$(git rev-parse --short HEAD)" \
  --summary "Added literature search stage with academic API integration; ruff/pytest pass"
```

---

## Summary

Following this workflow ensures:
- [OK] Continuity across multiple sessions
- [OK] Consistent code quality (specs injected, not remembered)
- [OK] Trackable progress (tasks + journals)
- [OK] Knowledge accumulation in spec docs
- [OK] Persistent memory across sessions (decisions, issues, learnings)
- [OK] Automated quality enforcement (Ralph Loop)
- [OK] Transparent team collaboration

**Core Philosophy**: Read before write, follow standards, record promptly, capture learnings, memory persists
