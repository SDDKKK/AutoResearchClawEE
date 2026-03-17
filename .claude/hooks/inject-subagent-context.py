#!/usr/bin/env python3
"""
Multi-Agent Pipeline Context Injection Hook

Core Design Philosophy:
- Dispatch becomes a pure dispatcher, only responsible for "calling subagents"
- Hook is responsible for injecting all context, subagent works autonomously with complete info
- Each agent has a dedicated jsonl file defining its context
- No resume needed, no segmentation, behavior controlled by code not prompt

Trigger: PreToolUse (before Task tool call)

Context Source: .trellis/.current-task points to task directory
- implement.jsonl - Implement agent dedicated context
- check.jsonl     - Check agent dedicated context
- debug.jsonl     - Debug agent dedicated context
- research.jsonl  - Research agent dedicated context (optional, usually not needed)
- cr.jsonl        - Code review dedicated context
- prd.md          - Requirements document
- info.md         - Technical design
- codex-review-output.txt - Code Review results
"""

import json
import os
import sys
import warnings
from pathlib import Path

# Suppress Python warnings that could corrupt JSON stdout
warnings.filterwarnings("ignore")

# Windows UTF-8 stdout fix (prevents UnicodeEncodeError with CJK characters)
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Add nocturne_client to path for importing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".trellis" / "scripts"))

try:
    from nocturne_client import NocturneClient
except ImportError:
    NocturneClient = None  # type: ignore[misc,assignment]

# =============================================================================
# Path Constants (change here to rename directories)
# =============================================================================

DIR_WORKFLOW = ".trellis"
DIR_WORKSPACE = "workspace"
DIR_TASKS = "tasks"
DIR_SPEC = "spec"
FILE_CURRENT_TASK = ".current-task"
FILE_TASK_JSON = "task.json"
DIR_MEMORY = "memory"

# Agents that don't update phase (can be called at any time)
AGENTS_NO_PHASE_UPDATE = {"debug", "research", "plan"}

# Valid status transitions (Mod 5: State Machine)
VALID_STATUS_TRANSITIONS = {
    "planning": {"active", "rejected"},
    "active": {"review", "blocked"},
    "review": {"active", "completed"},
    "blocked": {"active"},
    "completed": set(),  # terminal
    "rejected": set(),  # terminal
}

# Map subagent type to expected task status
AGENT_TARGET_STATUS = {
    "implement": "active",
    "check": "review",
    "review": "review",
}

# =============================================================================
# Subagent Constants (change here to rename subagent types)
# =============================================================================

AGENT_IMPLEMENT = "implement"
AGENT_CHECK = "check"
AGENT_REVIEW = "review"
AGENT_DEBUG = "debug"
AGENT_RESEARCH = "research"
AGENT_PLAN = "plan"

# Agents that require a task directory
AGENTS_REQUIRE_TASK = (AGENT_IMPLEMENT, AGENT_CHECK, AGENT_REVIEW, AGENT_DEBUG)
# All supported agents
AGENTS_ALL = (
    AGENT_IMPLEMENT,
    AGENT_CHECK,
    AGENT_REVIEW,
    AGENT_DEBUG,
    AGENT_RESEARCH,
    AGENT_PLAN,
)

# =============================================================================
# Codex Agent Convention
# codex-{base} agents delegate to Codex CLI with same context as {base} agent.
# Adding a new codex variant only requires a new .claude/agents/codex-{base}.md
# file — no hook changes needed.
# =============================================================================

CODEX_PREFIX = "codex-"
CODEX_ALLOWED_BASES = (AGENT_IMPLEMENT, AGENT_CHECK, AGENT_DEBUG, AGENT_REVIEW)


def parse_codex_agent(subagent_type: str) -> str | None:
    """If subagent_type is codex-{base}, return base type. Otherwise None."""
    if not subagent_type.startswith(CODEX_PREFIX):
        return None
    base = subagent_type[len(CODEX_PREFIX) :]
    if base not in CODEX_ALLOWED_BASES:
        return None
    return base


def get_ccr_model_tag(repo_root: str, subagent_type: str) -> str:
    """Read agent-models.json and return CCR tag prefix if configured.
    Only injects when CCR proxy is active (ANTHROPIC_BASE_URL points to localhost).
    """
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    if "127.0.0.1" not in base_url and "localhost" not in base_url:
        return ""
    config_path = os.path.join(repo_root, DIR_WORKFLOW, "config", "agent-models.json")
    if not os.path.isfile(config_path):
        return ""
    try:
        with open(config_path, encoding="utf-8") as f:
            mapping = json.load(f)
        model = mapping.get(subagent_type, "")
        if model:
            return f"<CCR-SUBAGENT-MODEL>{model}</CCR-SUBAGENT-MODEL>\n"
    except (json.JSONDecodeError, OSError):
        pass
    return ""


def find_repo_root(start_path: str) -> str | None:
    """
    Find git repo root from start_path upwards

    Returns:
        Repo root path, or None if not found
    """
    current = Path(start_path).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
    return None


def get_current_task(repo_root: str) -> str | None:
    """
    Read current task directory path from .trellis/.current-task

    Returns:
        Task directory relative path (relative to repo_root)
        None if not set
    """
    current_task_file = os.path.join(repo_root, DIR_WORKFLOW, FILE_CURRENT_TASK)
    if not os.path.exists(current_task_file):
        return None

    try:
        with open(current_task_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content if content else None
    except Exception:
        return None


def update_current_phase(repo_root: str, task_dir: str, subagent_type: str) -> None:
    """
    Update current_phase in task.json based on subagent_type.

    This ensures phase tracking is always accurate, regardless of whether
    dispatch agent remembers to update it.

    Logic:
    - Read next_action array from task.json
    - Find the next phase whose action matches subagent_type
    - Only move forward, never backward
    - Some agents (debug, research) don't update phase
    """
    if subagent_type in AGENTS_NO_PHASE_UPDATE:
        return

    task_json_path = os.path.join(repo_root, task_dir, FILE_TASK_JSON)
    if not os.path.exists(task_json_path):
        return

    try:
        with open(task_json_path, "r", encoding="utf-8") as f:
            task_data = json.load(f)

        current_phase = task_data.get("current_phase", 0)
        next_actions = task_data.get("next_action", [])

        # Map action names to subagent types
        # "implement" -> "implement", "check" -> "check", "finish" -> "check"
        # "codex-implement" -> "implement", etc. (codex-* delegates to base)
        action_to_agent = {
            "implement": "implement",
            "check": "check",
            "review": "review",
            "finish": "check",  # finish uses check agent
            "codex-implement": "implement",
            "codex-check": "check",
            "codex-debug": "debug",
            "codex-review": "review",
        }

        # Find the next phase that matches this subagent_type
        new_phase = None
        for action in next_actions:
            phase_num = action.get("phase", 0)
            action_name = action.get("action", "")
            expected_agent = action_to_agent.get(action_name)

            # Only consider phases after current_phase
            if phase_num > current_phase and expected_agent == subagent_type:
                new_phase = phase_num
                break

        if new_phase is not None:
            task_data["current_phase"] = new_phase

            with open(task_json_path, "w", encoding="utf-8") as f:
                json.dump(task_data, f, indent=2, ensure_ascii=False)
    except Exception:
        # Don't fail the hook if phase update fails
        pass


def read_file_content(base_path: str, file_path: str) -> str | None:
    """Read file content, return None if file doesn't exist"""
    full_path = os.path.join(base_path, file_path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None
    return None


def read_directory_contents(
    base_path: str, dir_path: str, max_files: int = 20
) -> list[tuple[str, str]]:
    """
    Read all .md files in a directory

    Args:
        base_path: Base path (usually repo_root)
        dir_path: Directory relative path
        max_files: Max files to read (prevent huge directories)

    Returns:
        [(file_path, content), ...]
    """
    full_path = os.path.join(base_path, dir_path)
    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return []

    results = []
    try:
        # Only read .md files, sorted by filename
        md_files = sorted(
            [
                f
                for f in os.listdir(full_path)
                if f.endswith(".md") and os.path.isfile(os.path.join(full_path, f))
            ]
        )

        for filename in md_files[:max_files]:
            file_full_path = os.path.join(full_path, filename)
            relative_path = os.path.join(dir_path, filename)
            try:
                with open(file_full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    results.append((relative_path, content))
            except Exception:
                continue
    except Exception:
        pass

    return results


def read_jsonl_entries(base_path: str, jsonl_path: str) -> list[tuple[str, str]]:
    """
    Read all file/directory contents referenced in jsonl file

    Schema:
        {"file": "path/to/file.md", "reason": "..."}
        {"file": "path/to/dir/", "type": "directory", "reason": "..."}
        {"file": "path/to/dir/", "type": "reference", "reason": "..."}
        {"file": "path/to/file.md", "type": "reference", "reason": "..."}

    Returns:
        [(path, content), ...]
    """
    full_path = os.path.join(base_path, jsonl_path)
    if not os.path.exists(full_path):
        return []

    results = []
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    file_path = item.get("file") or item.get("path")
                    entry_type = item.get("type", "file")

                    if not file_path:
                        continue

                    if entry_type == "directory":
                        # Read all .md files in directory
                        dir_contents = read_directory_contents(base_path, file_path)
                        results.extend(dir_contents)
                    elif entry_type == "reference":
                        # Reference mode: inject only index.md from directory,
                        # or file with hint suffix
                        full_target = os.path.join(base_path, file_path)
                        if os.path.isdir(full_target):
                            index_path = os.path.join(file_path, "index.md")
                            content = read_file_content(base_path, index_path)
                            if content:
                                content += (
                                    "\n\n> This is a reference index. "
                                    "Use Read tool to access detailed "
                                    "sub-files when needed."
                                )
                                results.append((index_path, content))
                            else:
                                # Fallback: read first .md file
                                md_files = sorted(
                                    f
                                    for f in os.listdir(full_target)
                                    if f.endswith(".md")
                                )
                                if md_files:
                                    fb_path = os.path.join(file_path, md_files[0])
                                    fb_content = read_file_content(base_path, fb_path)
                                    if fb_content:
                                        results.append((fb_path, fb_content))
                        else:
                            content = read_file_content(base_path, file_path)
                            if content:
                                content += (
                                    "\n\n> This is a reference summary. "
                                    "Use Read tool to access detailed "
                                    "files listed above."
                                )
                                results.append((file_path, content))
                    else:
                        # Read single file
                        content = read_file_content(base_path, file_path)
                        if content:
                            results.append((file_path, content))
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    return results


def get_memory_context(repo_root: str, agent_type: str) -> str:
    """
    Get memory context for agents (Mod 1: Structured Memory).

    - implement/debug: decisions.md + known-issues.md + scratchpad.md
    - check: decisions.md only (understand architecture context)
    - others: no memory injection
    """
    if agent_type not in ("implement", "check", "debug"):
        return ""

    memory_dir = os.path.join(repo_root, DIR_WORKFLOW, DIR_MEMORY)
    if not os.path.isdir(memory_dir):
        return ""

    parts = []
    memory_files = []

    if agent_type in ("implement", "debug"):
        memory_files = ["decisions.md", "known-issues.md", "scratchpad.md"]
    elif agent_type == "check":
        memory_files = ["decisions.md"]

    for filename in memory_files:
        filepath = os.path.join(memory_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    rel_path = f"{DIR_WORKFLOW}/{DIR_MEMORY}/{filename}"
                    parts.append(f"=== {rel_path} (Memory) ===\n{content}")
            except Exception:
                continue

    return "\n\n".join(parts)


def get_nocturne_hints(subagent_type: str) -> str:
    """
    Get Nocturne query hints for the specified agent type.

    Returns agent-specific hints about using Nocturne long-term memory.
    Agents can call MCP tools to read/search Nocturne memories.

    Args:
        subagent_type: Type of subagent (implement, check, debug, etc.)

    Returns:
        Formatted hints string, or empty string for unsupported agent types
    """
    if subagent_type not in (AGENT_IMPLEMENT, AGENT_CHECK, AGENT_REVIEW, AGENT_DEBUG):
        return ""

    # Common header for all agents
    hints = """## Long-Term Memory (Nocturne)

You have access to long-term memories via MCP tools:
- `read_memory(uri)` - Read a specific memory by URI
- `search_memory(query, domain="trellis")` - Search memories

Available URI namespaces:
- `trellis://patterns/python/...` - Python coding patterns
- `trellis://patterns/matlab/...` - MATLAB patterns
- `trellis://domain/power-systems/...` - Power system domain knowledge
- `trellis://domain/cim/...` - CIM standard knowledge
- `trellis://tools/claude-code/...` - Claude Code usage tips
- `trellis://projects/anhui-cim/...` - Project-specific memories
"""

    # Agent-specific guidance
    if subagent_type == AGENT_IMPLEMENT:
        hints += """
### When to Query Nocturne (Implement Agent)

**Before starting implementation:**
1. Query `trellis://patterns/python/` for language-specific patterns
2. Query `trellis://domain/power-systems/` or `trellis://domain/cim/` for domain knowledge
3. Query `trellis://tools/claude-code/` for tool usage tips

**During implementation:**
- Need error handling patterns? Query `trellis://patterns/python/error-handling`
- Working with data processing? Query `trellis://patterns/python/data-processing`
- Unsure about testing patterns? Query `trellis://patterns/python/testing`

**Common URI patterns to try:**
```
read_memory("trellis://patterns/python/idioms")
read_memory("trellis://patterns/python/error-handling/result-type")
read_memory("trellis://domain/power-systems/reliability/metrics")
read_memory("trellis://domain/cim/topology-processing/bus-branch")
```

**Search examples:**
```
search_memory("polars dataframe", domain="trellis")
search_memory("ruff type annotations", domain="trellis")
search_memory("MATLAB vectorization", domain="trellis")
```

**How to apply patterns:**
1. Read the pattern content
2. Understand the context and rationale
3. Adapt to your specific use case
4. Follow any referenced conventions
"""
    elif subagent_type in (AGENT_CHECK, AGENT_REVIEW):
        hints += """
### When to Query Nocturne (Check/Review Agent)

**Before code review:**
1. Query `trellis://patterns/python/` for verification criteria
2. Query `trellis://patterns/python/quality` for quality guidelines
3. Query `trellis://domain/power-systems/` for domain-specific rules

**During code review:**
- Checking code style? Query `trellis://patterns/python/code-style`
- Checking error handling? Query `trellis://patterns/python/error-handling`
- Checking cross-layer issues? Query `trellis://domain/power-systems/` for data format rules

**Common URI patterns to try:**
```
read_memory("trellis://patterns/python/quality-guidelines")
read_memory("trellis://patterns/python/code-style/ruff")
read_memory("trellis://domain/power-systems/data-formats")
read_memory("trellis://projects/anhui-cim/decisions")
```

**Search examples:**
```
search_memory("ruff polars", domain="trellis")
search_memory("cross-layer validation", domain="trellis")
search_memory("MATLAB checkcode", domain="trellis")
```

**How to verify against patterns:**
1. Query relevant quality patterns
2. Check if code follows documented conventions
3. Verify domain-specific rules are respected
4. Note any deviations and their justifications
"""
    elif subagent_type == AGENT_DEBUG:
        hints += """
### When to Query Nocturne (Debug Agent)

**Initial diagnosis:**
1. Query `trellis://projects/anhui-cim/known-issues` for active issues
2. Query `trellis://patterns/python/error-handling` for error patterns
3. Query `trellis://tools/claude-code/debugging` for debugging tips

**Deep investigation:**
- Specific error type? Query `trellis://patterns/python/error-handling/<type>`
- Cross-layer data issue? Query `trellis://domain/power-systems/data-formats`
- Tool usage problem? Query `trellis://tools/claude-code/<tool>`

**Common URI patterns to try:**
```
read_memory("trellis://projects/anhui-cim/known-issues")
read_memory("trellis://patterns/python/error-handling/result-type")
read_memory("trellis://patterns/python/error-handling/exceptions")
read_memory("trellis://tools/claude-code/debugging")
```

**Search examples:**
```
search_memory("common errors", domain="trellis")
search_memory("troubleshooting", domain="trellis")
search_memory("workaround", domain="trellis")
```

**How to use patterns for debugging:**
1. Search for similar issues in known-issues
2. Read relevant error handling patterns
3. Check if the fix follows established patterns
4. Verify the solution doesn't introduce new issues
"""

    return hints


def validate_status_transition(
    repo_root: str, task_dir: str, subagent_type: str
) -> None:
    """
    Validate and update task status based on subagent type (Mod 5: State Machine).

    Warns on invalid transitions but does not block (gradual introduction).
    """
    if subagent_type not in AGENT_TARGET_STATUS:
        return

    task_json_path = os.path.join(repo_root, task_dir, FILE_TASK_JSON)
    if not os.path.exists(task_json_path):
        return

    try:
        with open(task_json_path, "r", encoding="utf-8") as f:
            task_data = json.load(f)

        current_status = task_data.get("status", "planning")
        target_status = AGENT_TARGET_STATUS[subagent_type]

        # Already at target status, no transition needed
        if current_status == target_status:
            return

        allowed = VALID_STATUS_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            print(
                f"WARNING: Invalid status transition {current_status} → {target_status} "
                f"(triggered by {subagent_type} agent)",
                file=sys.stderr,
            )
            return

        # Valid transition: update status and append to history
        task_data["status"] = target_status

        # Append to status_history
        history = task_data.get("status_history", [])
        from datetime import datetime, timezone

        history.append(
            {
                "from": current_status,
                "to": target_status,
                "at": datetime.now(timezone.utc).isoformat(),
                "by": subagent_type,
            }
        )
        task_data["status_history"] = history

        with open(task_json_path, "w", encoding="utf-8") as f:
            json.dump(task_data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def get_agent_context(repo_root: str, task_dir: str, agent_type: str) -> str:
    """
    Get complete context for specified agent

    Prioritize agent-specific jsonl, fallback to spec.jsonl if not exists
    """
    context_parts = []

    # 1. Try agent-specific jsonl
    agent_jsonl = f"{task_dir}/{agent_type}.jsonl"
    agent_entries = read_jsonl_entries(repo_root, agent_jsonl)

    # 2. If agent-specific jsonl doesn't exist or empty, fallback to spec.jsonl
    if not agent_entries:
        agent_entries = read_jsonl_entries(repo_root, f"{task_dir}/spec.jsonl")

    # 3. Add all files from jsonl
    for file_path, content in agent_entries:
        context_parts.append(f"=== {file_path} ===\n{content}")

    return "\n\n".join(context_parts)


def get_implement_context(repo_root: str, task_dir: str) -> str:
    """
    Complete context for Implement Agent

    Read order:
    1. All files in implement.jsonl (dev specs)
    2. prd.md (requirements)
    3. info.md (technical design)
    """
    context_parts = []

    # 1. Read implement.jsonl (or fallback to spec.jsonl)
    base_context = get_agent_context(repo_root, task_dir, "implement")
    if base_context:
        context_parts.append(base_context)

    # 2. Requirements document
    prd_content = read_file_content(repo_root, f"{task_dir}/prd.md")
    if prd_content:
        context_parts.append(f"=== {task_dir}/prd.md (Requirements) ===\n{prd_content}")

    # 3. Technical design
    info_content = read_file_content(repo_root, f"{task_dir}/info.md")
    if info_content:
        context_parts.append(
            f"=== {task_dir}/info.md (Technical Design) ===\n{info_content}"
        )

    # 4. Memory context (decisions + known-issues + scratchpad)
    memory_context = get_memory_context(repo_root, "implement")
    if memory_context:
        context_parts.append(memory_context)

    # 5. TDD context (conditional: only when task.json has tdd=true)
    task_json_path = os.path.join(repo_root, task_dir, FILE_TASK_JSON)
    if os.path.exists(task_json_path):
        try:
            with open(task_json_path, "r", encoding="utf-8") as f:
                task_config = json.load(f)
            if task_config.get("tdd", False):
                tdd_files = [
                    (
                        f"{DIR_WORKFLOW}/{DIR_SPEC}/guides/tdd-guide.md",
                        "TDD mode enabled",
                    ),
                    (
                        f"{DIR_WORKFLOW}/{DIR_SPEC}/unit-test/testing-anti-patterns.md",
                        "Testing anti-patterns",
                    ),
                ]
                for file_path, reason in tdd_files:
                    content = read_file_content(repo_root, file_path)
                    if content:
                        context_parts.append(
                            f"=== {file_path} ({reason}) ===\n{content}"
                        )
        except (json.JSONDecodeError, OSError):
            pass

    return "\n\n".join(context_parts)


def get_check_context(repo_root: str, task_dir: str) -> str:
    """
    Complete context for Check Agent

    Read order:
    1. All files in check.jsonl (check specs + dev specs)
    2. prd.md (for understanding task intent)
    """
    context_parts = []

    # 1. Read check.jsonl (or fallback to spec.jsonl + hardcoded check files)
    check_entries = read_jsonl_entries(repo_root, f"{task_dir}/check.jsonl")

    if check_entries:
        for file_path, content in check_entries:
            context_parts.append(f"=== {file_path} ===\n{content}")
    else:
        # Fallback: use hardcoded check files + spec.jsonl
        check_files = [
            (".claude/commands/trellis/finish-work.md", "Finish work checklist"),
            (".claude/commands/trellis/check-cross-layer.md", "Cross-layer check spec"),
            (".claude/commands/trellis/check-python.md", "Python check spec"),
            (".claude/commands/trellis/check-matlab.md", "MATLAB check spec"),
        ]
        for file_path, description in check_files:
            content = read_file_content(repo_root, file_path)
            if content:
                context_parts.append(f"=== {file_path} ({description}) ===\n{content}")

        # Add spec.jsonl
        spec_entries = read_jsonl_entries(repo_root, f"{task_dir}/spec.jsonl")
        for file_path, content in spec_entries:
            context_parts.append(f"=== {file_path} (Dev spec) ===\n{content}")

    # 2. Requirements document (for understanding task intent)
    prd_content = read_file_content(repo_root, f"{task_dir}/prd.md")
    if prd_content:
        context_parts.append(
            f"=== {task_dir}/prd.md (Requirements - for understanding intent) ===\n{prd_content}"
        )

    # 3. Memory context (decisions only for check)
    memory_context = get_memory_context(repo_root, "check")
    if memory_context:
        context_parts.append(memory_context)

    return "\n\n".join(context_parts)


def get_review_context(repo_root: str, task_dir: str) -> str:
    """
    Complete context for Review Agent.

    Read order:
    1. All files in review.jsonl (or fallback to check.jsonl)
    2. prd.md (for understanding task intent)
    """
    context_parts = []

    review_entries = read_jsonl_entries(repo_root, f"{task_dir}/review.jsonl")

    if review_entries:
        for file_path, content in review_entries:
            context_parts.append(f"=== {file_path} ===\n{content}")
    else:
        # Fallback: use check.jsonl entries
        check_entries = read_jsonl_entries(repo_root, f"{task_dir}/check.jsonl")
        for file_path, content in check_entries:
            context_parts.append(f"=== {file_path} ===\n{content}")

    prd_content = read_file_content(repo_root, f"{task_dir}/prd.md")
    if prd_content:
        context_parts.append(
            f"=== {task_dir}/prd.md (Requirements - for understanding intent) ===\n{prd_content}"
        )

    memory_context = get_memory_context(repo_root, "check")
    if memory_context:
        context_parts.append(memory_context)

    return "\n\n".join(context_parts)


def get_finish_context(repo_root: str, task_dir: str) -> str:
    """
    Complete context for Finish phase (final check before PR)

    Read order:
    1. All files in finish.jsonl (if exists)
    2. Fallback to finish-work.md only (lightweight final check)
    3. update-spec.md (for active spec sync — ALWAYS injected)
    4. prd.md (for verifying requirements are met)
    """
    context_parts = []

    # 1. Try finish.jsonl first
    finish_entries = read_jsonl_entries(repo_root, f"{task_dir}/finish.jsonl")

    if finish_entries:
        for file_path, content in finish_entries:
            context_parts.append(f"=== {file_path} ===\n{content}")
    else:
        # Fallback: only finish-work.md (lightweight)
        finish_work = read_file_content(
            repo_root, ".claude/commands/trellis/finish-work.md"
        )
        if finish_work:
            context_parts.append(
                f"=== .claude/commands/trellis/finish-work.md (Finish checklist) ===\n{finish_work}"
            )

    # 2. ALWAYS inject update-spec.md (for active spec sync)
    update_spec = read_file_content(
        repo_root, ".claude/commands/trellis/update-spec.md"
    )
    if update_spec:
        context_parts.append(
            f"=== .claude/commands/trellis/update-spec.md (Spec update process) ===\n{update_spec}"
        )

    # 3. Requirements document (for verifying requirements are met)
    prd_content = read_file_content(repo_root, f"{task_dir}/prd.md")
    if prd_content:
        context_parts.append(
            f"=== {task_dir}/prd.md (Requirements - verify all met) ===\n{prd_content}"
        )

    return "\n\n".join(context_parts)


def get_debug_context(repo_root: str, task_dir: str) -> str:
    """
    Complete context for Debug Agent

    Read order:
    1. All files in debug.jsonl (specs needed for fixing)
    2. codex-review-output.txt (Codex Review results)
    """
    context_parts = []

    # 1. Read debug.jsonl (or fallback to spec.jsonl + hardcoded check files)
    debug_entries = read_jsonl_entries(repo_root, f"{task_dir}/debug.jsonl")

    if debug_entries:
        for file_path, content in debug_entries:
            context_parts.append(f"=== {file_path} ===\n{content}")
    else:
        # Fallback: use spec.jsonl + hardcoded check files
        spec_entries = read_jsonl_entries(repo_root, f"{task_dir}/spec.jsonl")
        for file_path, content in spec_entries:
            context_parts.append(f"=== {file_path} (Dev spec) ===\n{content}")

        check_files = [
            (".claude/commands/trellis/check-python.md", "Python check spec"),
            (".claude/commands/trellis/check-matlab.md", "MATLAB check spec"),
            (".claude/commands/trellis/check-cross-layer.md", "Cross-layer check spec"),
        ]
        for file_path, description in check_files:
            content = read_file_content(repo_root, file_path)
            if content:
                context_parts.append(f"=== {file_path} ({description}) ===\n{content}")

    # 2. Codex review output (if exists)
    codex_output = read_file_content(repo_root, f"{task_dir}/codex-review-output.txt")
    if codex_output:
        context_parts.append(
            f"=== {task_dir}/codex-review-output.txt (Codex Review Results) ===\n{codex_output}"
        )

    # 3. Memory context (decisions + known-issues + scratchpad)
    memory_context = get_memory_context(repo_root, "debug")
    if memory_context:
        context_parts.append(memory_context)

    return "\n\n".join(context_parts)


def build_implement_prompt(
    original_prompt: str, context: str, nocturne_hints: str = ""
) -> str:
    """Build complete prompt for Implement"""
    nocturne_section = f"\n{nocturne_hints}\n" if nocturne_hints else ""
    return f"""# Implement Agent Task

You are the Implement Agent in the Multi-Agent Pipeline.

## Your Context

All the information you need has been prepared for you:

{context}
{nocturne_section}
---

## Your Task

{original_prompt}

---

## Workflow

1. **Understand specs** - All dev specs are injected above, understand them
2. **Understand requirements** - Read requirements document and technical design
3. **Implement feature** - Implement following specs and design
4. **Self-check** - Ensure code quality against check specs

## Important Constraints

- Do NOT execute git commit, only code modifications
- Follow all dev specs injected above
- Report list of modified/created files when done"""


def build_check_prompt(
    original_prompt: str, context: str, nocturne_hints: str = ""
) -> str:
    """Build complete prompt for Check"""
    nocturne_section = f"\n{nocturne_hints}\n" if nocturne_hints else ""
    return f"""# Check Agent Task

You are the Check Agent in the Multi-Agent Pipeline (code and cross-layer checker).

## Your Context

All check specs and dev specs you need:

{context}
{nocturne_section}
---

## Your Task

{original_prompt}

---

## Workflow

1. **Get changes** - Run `git diff --name-only` and `git diff` to get code changes
2. **Check against specs** - Check item by item against specs above
3. **Self-fix** - Fix issues directly, don't just report
4. **Run verification** - Run project's lint and typecheck commands

## Important Constraints

- Fix issues yourself, don't just report
- Must execute complete checklist in check specs
- Pay special attention to impact radius analysis (L1-L5)"""


def build_review_prompt(
    original_prompt: str, context: str, nocturne_hints: str = ""
) -> str:
    """Build complete prompt for Review"""
    nocturne_section = f"\n{nocturne_hints}\n" if nocturne_hints else ""
    return f"""# Review Agent Task

You are the Review Agent in the Multi-Agent Pipeline (semantic code reviewer).

## Your Context

All review specs you need:

{context}
{nocturne_section}
---

## Your Task

{original_prompt}

---

## Workflow

1. **Get changes** - Run `git diff --name-only` and `git diff` to get code changes
2. **Review 4 dimensions** - D1 Scientific, D2 Cross-Layer, D4 Performance, D5 Data Integrity
3. **Self-fix** - Fix issues directly, don't just report
4. **Output markers** - Output all 4 completion markers when verified

## Important Constraints

- Fix issues yourself, don't just report
- Output SCIENTIFIC_FINISH, CROSSLAYER_FINISH, PERFORMANCE_FINISH, DATAINTEGRITY_FINISH when done
- If a dimension is N/A, still output the marker with a note"""


def build_finish_prompt(original_prompt: str, context: str) -> str:
    """Build complete prompt for Finish (final check before PR)"""
    return f"""# Finish Agent Task

You are performing the final check before creating a PR.

## Your Context

Finish checklist and requirements:

{context}

---

## Your Task

{original_prompt}

---

## Workflow

1. **Review changes** - Run `git diff --name-only` to see all changed files
2. **Verify requirements** - Check each requirement in prd.md is implemented
3. **Spec sync** - Analyze whether changes introduce new patterns, contracts, or conventions
   - If new pattern/convention found: read target spec file -> update it -> update index.md
   - If infra/cross-layer change: follow the 7-section mandatory template from update-spec.md
   - If pure code fix with no new patterns: skip this step
4. **Run final checks** - Execute finish-work.md checklist
5. **Confirm ready** - Ensure code is ready for PR

## Important Constraints

- You MAY update spec files when gaps are detected (use update-spec.md as guide)
- MUST read the target spec file BEFORE editing (avoid duplicating existing content)
- Do NOT update specs for trivial changes (typos, formatting, obvious fixes)
- If critical CODE issues found, report them clearly (fix specs, not code)
- Verify all acceptance criteria in prd.md are met"""


def build_debug_prompt(
    original_prompt: str, context: str, nocturne_hints: str = ""
) -> str:
    """Build complete prompt for Debug"""
    nocturne_section = f"\n{nocturne_hints}\n" if nocturne_hints else ""
    return f"""# Debug Agent Task

You are the Debug Agent in the Multi-Agent Pipeline (issue fixer).

## Your Context

Dev specs and Codex Review results:

{context}
{nocturne_section}
---

## Your Task

{original_prompt}

---

## Workflow

1. **Understand issues** - Analyze issues pointed out in Codex Review
2. **Locate code** - Find positions that need fixing
3. **Fix against specs** - Fix issues following dev specs
4. **Verify fixes** - Run typecheck to ensure no new issues

## Important Constraints

- Do NOT execute git commit, only code modifications
- Run typecheck after each fix to verify
- Report which issues were fixed and which files were modified"""


def get_research_context(repo_root: str, task_dir: str | None) -> str:
    """
    Context for Research Agent

    Research doesn't need much preset context, only needs:
    1. Project structure overview (where spec directories are)
    2. Optional research.jsonl (if there are specific search needs)
    """
    context_parts = []

    # 1. Project structure overview (uses constants for paths)
    spec_path = f"{DIR_WORKFLOW}/{DIR_SPEC}"
    project_structure = f"""## Project Spec Directory Structure

```
{spec_path}/
├── python/      # Python standards (scientific computing, ruff, polars)
├── matlab/      # MATLAB standards (code style, checkcode)
├── guides/      # Thinking guides (cross-layer, code reuse, etc.)

{DIR_WORKFLOW}/big-question/  # Known issues and pitfalls
```

## Search Tips (Four-Layer External Search + Local Codebase)

- Spec files: `{spec_path}/**/*.md`
- Known issues: `{DIR_WORKFLOW}/big-question/`
- **GitHub repo analysis**: Read `{spec_path}/guides/github-analysis-guide.md` first, then follow its methodology (multi-source, tool selection, output checklist)
- **Local code search (semantic)**: Use `mcp__morph-mcp__warpgrep_codebase_search` (preferred, multi-turn parallel) or `mcp__augment-context-engine__codebase-retrieval` (fallback)
- Local code search (exact match): Use Grep tool
- Layer 0 (Library docs): Use mcp__context7__resolve-library-id then mcp__context7__query-docs
- Layer 1 (Quick answer): Use mcp__perplexity__perplexity_ask
- Layer 2 (Structured search): Use mcp__perplexity__perplexity_search then web_fetch.py for key URLs
- Layer 3 (Deep research): Use mcp__perplexity__perplexity_research then web_fetch.py for verification
- Web search (Grok): Use Bash("python3 .trellis/scripts/search/web_search.py '<query>'")
- Web content (Grok): Use Bash("python3 .trellis/scripts/search/web_fetch.py '<url>'")
- Escalation: Layer 0 → 1 → 2 → 3. Start at lowest sufficient layer.
- Fallback: If morph-mcp unavailable, use codebase-retrieval for all semantic search needs"""

    context_parts.append(project_structure)

    # 2. If task directory exists, try reading research.jsonl (optional)
    if task_dir:
        research_entries = read_jsonl_entries(repo_root, f"{task_dir}/research.jsonl")
        if research_entries:
            context_parts.append(
                "\n## Additional Search Context (from research.jsonl)\n"
            )
            for file_path, content in research_entries:
                context_parts.append(f"=== {file_path} ===\n{content}")

    return "\n\n".join(context_parts)


def build_research_prompt(original_prompt: str, context: str) -> str:
    """Build complete prompt for Research"""
    return f"""# Research Agent Task

You are the Research Agent in the Multi-Agent Pipeline (search researcher).

## Core Principle

**You do one thing: find and explain information.**

You are a documenter, not a reviewer.

## Project Info

{context}

---

## Your Task

{original_prompt}

---

## Workflow

1. **Understand query** - Determine search type (internal/external) and scope
2. **Plan search** - List search steps for complex queries
3. **Execute search** - Execute multiple independent searches in parallel
4. **Organize results** - Output structured report

## Search Tools (Four-Layer External Search)

| Tool | Purpose | Layer | Fallback if Unavailable |
|------|---------|-------|------------------------|
| Glob | Search by filename pattern | Local | — |
| Grep | Search by content (exact match) | Local | — |
| Read | Read file content | Local | — |
| mcp__morph-mcp__warpgrep_codebase_search | Broad semantic code search (multi-turn parallel) | Local | mcp__augment-context-engine__codebase-retrieval |
| mcp__augment-context-engine__codebase-retrieval | Deep semantic code understanding | Local | Grep + Read (manual) |
| mcp__context7__resolve-library-id | Resolve library name to Context7 ID | 0 | perplexity_ask |
| mcp__context7__query-docs | Query library documentation and examples | 0 | perplexity_ask |
| mcp__perplexity__perplexity_ask | Quick answer, fact-check, concept explanation | 1 | web_search.py |
| mcp__perplexity__perplexity_search | Multi-source structured search with URLs | 2 | web_search.py + web_fetch.py |
| mcp__perplexity__perplexity_research | Deep research with comprehensive citations | 3 | Multiple web_search.py rounds |
| Bash("python3 .trellis/scripts/search/web_search.py '<query>'") | Platform-targeted web search (--platform github) | Grok | perplexity_search |
| Bash("python3 .trellis/scripts/search/web_fetch.py '<url>'") | Fetch full webpage content as Markdown | Grok | (no equivalent - try all tiers) |
| Bash("python3 ~/.claude/skills/with-codex/scripts/codex_bridge.py ...") | Cross-model analysis (slow, 300s timeout) | Codex | Own analysis (skip Codex) |

Escalation: Layer 0 → 1 → 2 → 3. Start at lowest sufficient layer.
Tool Selection: Exact identifier → Grep. Broad semantic → warpgrep. Deep understanding → codebase-retrieval.

## Strict Boundaries

**Only allowed**: Describe what exists, where it is, how it works

**Forbidden** (unless explicitly asked):
- Suggest improvements
- Criticize implementation
- Recommend refactoring
- Modify any files

## Report Format

Provide structured search results including:
- List of files found (with paths)
- Code pattern analysis (if applicable)
- Related spec documents
- External references (if any)"""


def get_plan_context(repo_root: str, task_dir: str | None) -> str:
    """
    Context for Plan Agent.

    Plan agent evaluates requirements and configures task directories.
    It needs:
    1. Project spec directory overview (available categories)
    2. Optional plan.jsonl (if task directory exists)
    """
    context_parts = []

    # 1. Project spec directory overview
    spec_path = f"{DIR_WORKFLOW}/{DIR_SPEC}"
    spec_base = os.path.join(repo_root, spec_path)
    categories = []
    if os.path.isdir(spec_base):
        for entry in sorted(os.listdir(spec_base)):
            entry_path = os.path.join(spec_base, entry)
            if os.path.isdir(entry_path):
                index_file = os.path.join(entry_path, "index.md")
                has_index = os.path.exists(index_file)
                categories.append(
                    f"  ├── {entry}/" + (" (has index.md)" if has_index else "")
                )

    category_tree = "\n".join(categories) if categories else "  (no categories found)"
    project_structure = f"""## Project Spec Directory

```
{spec_path}/
{category_tree}
```

## Available Dev Types

- `python` — Python development (scientific computing)
- `matlab` — MATLAB development
- `both` — Cross-layer Python + MATLAB"""

    context_parts.append(project_structure)

    # 2. If task directory exists, try reading plan.jsonl (optional)
    if task_dir:
        plan_entries = read_jsonl_entries(repo_root, f"{task_dir}/plan.jsonl")
        if plan_entries:
            context_parts.append("\n## Additional Plan Context (from plan.jsonl)\n")
            for file_path, content in plan_entries:
                context_parts.append(f"=== {file_path} ===\n{content}")

    return "\n\n".join(context_parts)


def build_plan_prompt(original_prompt: str, context: str) -> str:
    """Build complete prompt for Plan Agent."""
    return f"""# Plan Agent Task

You are the Plan Agent in the Multi-Agent Pipeline (requirement evaluator & task configurator).

## Project Info

{context}

---

## Your Task

{original_prompt}

---

## Workflow

1. **Evaluate requirement** - Check if the requirement is clear, specific, and feasible
2. **Reject or accept** - Reject if vague, too large, or harmful; accept if actionable
3. **Research codebase** - Call research agent to find relevant specs and patterns
4. **Configure task** - Create jsonl files, prd.md, and set metadata
5. **Validate** - Ensure all referenced files exist

## Important Constraints

- You have the power to REJECT unclear requirements
- Do NOT execute git commit
- Always call research agent before configuring context
- Validate all file paths in jsonl entries"""


# =============================================================================
# Codex context getter mapping (base_type → getter function)
# =============================================================================

CODEX_CONTEXT_GETTERS: dict[str, object] = {}  # populated after function defs


def _init_codex_context_getters() -> None:
    """Populate CODEX_CONTEXT_GETTERS after all getter functions are defined."""
    CODEX_CONTEXT_GETTERS.update(
        {
            AGENT_IMPLEMENT: get_implement_context,
            AGENT_CHECK: get_check_context,
            AGENT_DEBUG: get_debug_context,
            AGENT_REVIEW: get_review_context,
        }
    )


_init_codex_context_getters()


def build_codex_prompt(
    base_type: str, original_prompt: str, context: str, nocturne_hints: str = ""
) -> str:
    """Build prompt for codex-{base} wrapper agents.

    Scheme C: Hook pre-assembles full context into temp file, wrapper passes
    it via --context-file. Codex receives complete context (specs + prd + memory).
    """
    base_constraints = {
        "implement": "Do NOT execute git commit. Only code modifications.",
        "check": "Fix issues found by linting/formatting. Run ruff check + format.",
        "debug": "Precise fixes only. Do not refactor unrelated code.",
        "review": "Review for correctness and consistency. Fix issues directly.",
    }
    base_mode = {
        "implement": "exec",
        "check": "exec",
        "debug": "exec",
        "review": "review",
    }

    constraint = base_constraints.get(base_type, "")
    mode = base_mode.get(base_type, "exec")

    # Assemble full context content (including Nocturne hints)
    ctx_content = context
    if nocturne_hints:
        ctx_content += f"\n\n{nocturne_hints}"

    # Write to temp file with PID + timestamp for concurrency safety
    import time as _time

    ctx_path = f"/tmp/trellis-codex-ctx-{os.getpid()}-{int(_time.time())}.md"
    with open(ctx_path, "w", encoding="utf-8") as f:
        f.write(ctx_content)

    return f"""# Codex {base_type.title()} Agent Task

You are a Codex Wrapper Agent. Your job is to delegate the task to Codex CLI
via codex_bridge.py, then report the results.

## How It Works

1. Hook has pre-assembled full context (specs + prd + memory) into a temp file
2. Your prompt includes the --context-file path below
3. You call codex_bridge.py with that path — Codex receives complete context
4. You collect results and report back

## Context File Location

**{ctx_path}**

This file contains the complete assembled context. Do NOT modify it.

## Execution Steps

1. **Understand the task** from the context file and original request below
2. **Call codex_bridge.py** using Bash (note the --context-file):

```bash
python3 ~/.claude/skills/with-codex/scripts/codex_bridge.py \\
  --mode {mode} \\
  --cd "$(pwd)" \\
  --full-auto \\
  --context-file {ctx_path} \\
  --timeout 600 \\
  --PROMPT "<summarize the task from original request below>"
```

3. **Parse the JSON output** — check `success`, `agent_messages`, `partial`
4. **Verify file changes** — run `git diff --stat` to see what Codex modified
5. **Report results** using the format below
6. **Cleanup** — remove the temp context file

## Original Request

{original_prompt}

## Constraints

- {constraint}
- If Codex fails (success=false), report the error — do NOT retry automatically
- If Codex returns partial results (partial=true), report what was completed
- If codex_bridge.py is not found or Codex CLI is not installed, report the error clearly

## Cleanup (Required)

After Codex completes, remove the temp context file:

```bash
rm -f {ctx_path}
```

## Report Format

```markdown
## Codex {base_type.title()} Complete

### Codex Output Summary
<brief summary of agent_messages>

### Files Modified
- `path/to/file.py` - description

### Verification
- git diff stat: <output>

### Cleanup
- Context file removed: {ctx_path}

### Issues (if any)
- <any problems encountered>
```"""


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")

    if tool_name not in ("Task", "Agent"):
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    subagent_type = tool_input.get("subagent_type", "")
    original_prompt = tool_input.get("prompt", "")
    cwd = input_data.get("cwd", os.getcwd())

    # Check for codex-* prefix first
    codex_base = parse_codex_agent(subagent_type)

    # Only handle known subagent types or codex-* agents
    if subagent_type not in AGENTS_ALL and codex_base is None:
        sys.exit(0)

    # Find repo root
    repo_root = find_repo_root(cwd)
    if not repo_root:
        sys.exit(0)

    # Get current task directory (research/plan don't require it)
    task_dir = get_current_task(repo_root)

    # Determine effective agent type for task/phase/status checks
    effective_type = codex_base or subagent_type

    # implement/check/debug need task directory (codex-* inherits from base)
    if effective_type in AGENTS_REQUIRE_TASK:
        if not task_dir or not os.path.exists(os.path.join(repo_root, task_dir)):
            # No task dir — still inject CCR model tag if configured, then exit
            ccr_tag = get_ccr_model_tag(repo_root, subagent_type)
            if ccr_tag:
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "updatedInput": {
                            **tool_input,
                            "prompt": ccr_tag + original_prompt,
                        },
                    }
                }
                print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)
        # Update current_phase in task.json (system-level enforcement)
        update_current_phase(repo_root, task_dir, effective_type)

        # Validate and update status (Mod 5: State Machine)
        validate_status_transition(repo_root, task_dir, effective_type)

    # --- Codex agent path: use base agent's context + codex prompt builder ---
    if codex_base is not None:
        assert task_dir is not None  # codex agents always require task
        getter = CODEX_CONTEXT_GETTERS.get(codex_base)
        if getter is None:
            sys.exit(0)
        context = getter(repo_root, task_dir)
        nocturne_hints = get_nocturne_hints(codex_base)
        new_prompt = build_codex_prompt(
            codex_base, original_prompt, context, nocturne_hints
        )
    else:
        # --- Standard agent path (unchanged) ---

        # Check for [finish] marker in prompt (check agent with finish context)
        is_finish_phase = "[finish]" in original_prompt.lower()

        # Get Nocturne hints for relevant agents
        nocturne_hints = get_nocturne_hints(subagent_type)

        # Get context and build prompt based on subagent type
        if subagent_type == AGENT_IMPLEMENT:
            assert task_dir is not None  # validated above
            context = get_implement_context(repo_root, task_dir)
            new_prompt = build_implement_prompt(
                original_prompt, context, nocturne_hints
            )
        elif subagent_type == AGENT_CHECK:
            assert task_dir is not None  # validated above
            if is_finish_phase:
                context = get_finish_context(repo_root, task_dir)
                new_prompt = build_finish_prompt(original_prompt, context)
            else:
                context = get_check_context(repo_root, task_dir)
                new_prompt = build_check_prompt(
                    original_prompt, context, nocturne_hints
                )
        elif subagent_type == AGENT_DEBUG:
            assert task_dir is not None  # validated above
            context = get_debug_context(repo_root, task_dir)
            new_prompt = build_debug_prompt(original_prompt, context, nocturne_hints)
        elif subagent_type == AGENT_REVIEW:
            assert task_dir is not None  # validated above
            context = get_review_context(repo_root, task_dir)
            new_prompt = build_review_prompt(original_prompt, context, nocturne_hints)
        elif subagent_type == AGENT_RESEARCH:
            context = get_research_context(repo_root, task_dir)
            new_prompt = build_research_prompt(original_prompt, context)
        elif subagent_type == AGENT_PLAN:
            context = get_plan_context(repo_root, task_dir)
            new_prompt = build_plan_prompt(original_prompt, context)
        else:
            sys.exit(0)

    # Empty context check: for standard agents, exit early. For codex agents,
    # proceed with empty context (temp file already written; PRD edge case #2).
    if not context and codex_base is None:
        sys.exit(0)

    # Prepend CCR subagent model tag if configured
    ccr_tag = get_ccr_model_tag(repo_root, subagent_type)
    if ccr_tag:
        new_prompt = ccr_tag + new_prompt

    # Return updated input
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {**tool_input, "prompt": new_prompt},
        }
    }

    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
