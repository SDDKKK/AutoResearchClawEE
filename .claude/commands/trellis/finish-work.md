# Finish Work - Pre-Commit Checklist

Before submitting or committing, use this checklist to ensure work completeness.

**Timing**: After code is written and tested, before commit

---

## Checklist

### 0. Fresh Verification Gate

- [ ] All verification commands re-run in THIS session (do not cite previous results)
- [ ] No "should pass" / "looks correct" language used
- [ ] Verification output pasted in report as evidence

### 1. Code Quality

```bash
# Must pass
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

- [ ] `uv run ruff check .` passes with 0 errors?
- [ ] `uv run ruff format --check .` passes with no format issues?
- [ ] Tests pass?
- [ ] No debug `print()` statements left in code?
- [ ] Docstrings present for public functions?

### 1.5. Test Coverage

Check if your change needs new or updated tests (see `.trellis/spec/unit-test/conventions.md`):
- [ ] New pure function → unit test added?
- [ ] Bug fix → regression test added?
- [ ] Changed data processing behavior → integration test added/updated?
- [ ] No logic change (text/data only) → no test needed

### 2. Documentation Sync

**Spec Docs**:
- [ ] Does `.trellis/spec/python/` need updates?
  - New patterns, new modules, new conventions
- [ ] Does `.trellis/spec/matlab/` need updates?
  - New functions, new scripts, new patterns
- [ ] Does `.trellis/spec/guides/` need updates?
  - New cross-layer flows, lessons from bugs

**Key Question**: 
> "If I fixed a bug or discovered something non-obvious, should I document it so future me (or others) won't hit the same issue?"

If YES -> Update the relevant spec doc.

### 2.5. Code-Spec Hard Block (Infra/Cross-Layer)

If this change touches infra or cross-layer contracts, this is a blocking checklist:
- [ ] Spec content is executable (real signatures/contracts), not principle-only text
- [ ] Includes file path + command/API name + payload field names
- [ ] Includes validation and error matrix
- [ ] Includes Good/Base/Bad cases
- [ ] Includes required tests and assertion points

**Block Rule**: In pipeline mode, the finish agent will automatically detect and execute spec updates when gaps are found. If running this checklist manually, ensure spec sync is complete before committing — run `/trellis:update-spec` if needed.

### 3. Data File Changes

If you modified data processing or file formats:

- [ ] Input/output data formats documented?
- [ ] Data file paths consistent?
- [ ] Python↔MATLAB data interchange verified? (.mat, .csv, .json, .h5)

### 4. Cross-Layer Verification (Python↔MATLAB)

If the change spans both languages:

- [ ] Data flows correctly between Python and MATLAB?
- [ ] Variable naming consistent across languages?
- [ ] Array indexing conventions handled? (0-based vs 1-based)
- [ ] Error handling works on both sides?

### 5. Manual Testing

- [ ] Computation results correct?
- [ ] Edge cases tested?
- [ ] Error states tested?

### 6. Memory Updates

**Local Memory** (`.trellis/memory/`, git-tracked):
- [ ] Made an architectural decision? → Update `.trellis/memory/decisions.md`
- [ ] Discovered a known issue or workaround? → Update `.trellis/memory/known-issues.md`
- [ ] Resolved a known issue? → Mark resolved in `known-issues.md`
- [ ] Any learnings to record? → `add_session.py --learning "description"`

**Global Memory** (Nocturne, cross-project persistent):

If this session produced learnings reusable across projects/sessions, promote to Nocturne:

```
# 1. Read current state
read_memory("trellis://projects/<project-id>/learnings")
# or: read_memory("trellis://tools/claude-code/agents")

# 2. Append learning
update_memory(uri, append="## Title\n\nContent...")
```

**When to promote** (at least one applies):
- [ ] Cross-language gotcha (e.g., Python falsy vs Java null)
- [ ] Agent workflow pattern or failure mode
- [ ] New verification or testing pattern
- [ ] Reusable architectural insight

**Decision rule**: `.trellis/memory/learnings.md` captures ALL learnings. Nocturne only gets learnings **reusable across sessions** — skip one-off fixes or project-specific trivia.

### 7. Task Status Update

If there is an active task, complete it after the checklist passes:

```bash
# Complete current task (sets status, records commit, clears pointer, resets scratchpad)
python3 ./.trellis/scripts/task.py complete

# Or complete a specific task
python3 ./.trellis/scripts/task.py complete ".trellis/tasks/<task-dir>"
```

- [ ] Task completed via `task.py complete`?

> **Note**: Only complete if ALL relevant checklist items above pass. If issues remain, keep the task in its current status and fix first.

### 8. Completion Options

All checks passed. Present these options to the user:

1. **Commit locally** -- Manual commit (Mode 1 default)
2. **Push and create Draft PR** -- Auto-push and create Draft PR
3. **Keep as-is** -- Leave current state, handle later
4. **Discard changes** -- Abandon all uncommitted changes (requires confirmation)

For Option 2: run `python3 ./.trellis/scripts/multi_agent/create_pr.py`
For Option 4: require user to type "discard" before executing `git restore .`

---

## Quick Check Flow

```bash
# 1. Code checks
uv run ruff check . && uv run ruff format --check .

# 2. View changes
git status
git diff --name-only

# 3. Based on changed files, check relevant items above

# 4. Complete task (if active task exists)
python3 ./.trellis/scripts/task.py complete
```

---

## Common Oversights

| Oversight | Consequence | Check |
|-----------|-------------|-------|
| Spec docs not updated | Others don't know the change | Check .trellis/spec/ |
| Spec text is abstract only | Easy regressions in infra/cross-layer changes | Require signature/contract/matrix/cases/tests |
| Data format mismatch | Python↔MATLAB interchange fails | Verify data files |
| Docstrings missing | Code undocumented | Check public functions |
| Tests not updated | False confidence | Run full test suite |
| Debug print() left in | Noisy output | Search for print() |
| Nocturne not updated | Cross-project learnings lost | Check Step 6 Global Memory |

---

## Relationship to Other Commands

```
Development Flow:
  Write code -> Test -> /trellis:finish-work -> git commit -> /trellis:record-session
                          |                              |
                   Ensure completeness              Record progress
                   
Debug Flow:
  Hit bug -> Fix -> /trellis:break-loop -> Knowledge capture
                       |
                  Deep analysis
```

- `/trellis:finish-work` - Check work completeness (this command)
- `/trellis:record-session` - Record session and commits
- `/trellis:break-loop` - Deep analysis after debugging

---

## Core Principle

> **Delivery includes not just code, but also documentation, verification, and knowledge capture.**

Complete work = Code + Docs + Tests + Verification
