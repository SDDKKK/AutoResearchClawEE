#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task Management Script for Multi-Agent Pipeline.

Usage:
    python3 task.py create "<title>" [--slug <name>] [--assignee <dev>] [--priority P0|P1|P2|P3]
    python3 task.py init-context <dir> <type>   # Initialize jsonl files (type: python|matlab|both|trellis)
    python3 task.py add-context <dir> <file> <path> [reason] # Add jsonl entry
    python3 task.py validate <dir>              # Validate jsonl files
    python3 task.py list-context <dir>          # List jsonl entries
    python3 task.py start <dir>                 # Set as current task
    python3 task.py finish                      # Clear current task
    python3 task.py complete [dir]              # Complete task (status + cleanup)
    python3 task.py set-status <dir> <status>   # Set task status (state machine)
    python3 task.py set-branch <dir> <branch>   # Set git branch
    python3 task.py set-base-branch <dir> <branch>  # Set PR target branch
    python3 task.py set-scope <dir> <scope>     # Set scope for PR title
    python3 task.py create-pr [dir] [--dry-run] # Create PR from task
    python3 task.py archive <task-name>         # Archive completed task
    python3 task.py list                        # List active tasks
    python3 task.py list-archive [month]        # List archived tasks
"""

from __future__ import annotations

import sys

# IMPORTANT: Force stdout to use UTF-8 on Windows
# This fixes UnicodeEncodeError when outputting non-ASCII characters
if sys.platform == "win32":
    import io as _io

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    elif hasattr(sys.stdout, "detach"):
        sys.stdout = _io.TextIOWrapper(
            sys.stdout.detach(), encoding="utf-8", errors="replace"
        )  # type: ignore[union-attr]

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from common.cli_adapter import get_cli_adapter_auto
from common.config import get_hooks
from common.git_context import _run_git_command
from common.paths import (
    DIR_ARCHIVE,
    DIR_MEMORY,
    DIR_SPEC,
    DIR_TASKS,
    DIR_WORKFLOW,
    FILE_DECISIONS,
    FILE_KNOWN_ISSUES,
    FILE_SCRATCHPAD,
    FILE_TASK_JSON,
    clear_current_task,
    ensure_memory_dir,
    generate_task_date_prefix,
    get_current_task,
    get_developer,
    get_memory_dir,
    get_repo_root,
    get_tasks_dir,
    set_current_task,
)
from common.task_utils import (
    archive_task_complete,
    find_task_by_name,
)

# =============================================================================
# Colors
# =============================================================================


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"


def colored(text: str, color: str) -> str:
    """Apply color to text."""
    return f"{color}{text}{Colors.NC}"


# =============================================================================
# Lifecycle Hooks
# =============================================================================


def _run_hooks(event: str, task_json_path: Path, repo_root: Path) -> None:
    """Run lifecycle hooks for an event.

    Args:
        event: Event name (e.g. "after_create").
        task_json_path: Absolute path to the task's task.json.
        repo_root: Repository root for cwd and config lookup.
    """
    import os
    import subprocess

    commands = get_hooks(event, repo_root)
    if not commands:
        return

    env = {**os.environ, "TASK_JSON_PATH": str(task_json_path)}

    for cmd in commands:
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                print(
                    colored(f"[WARN] Hook failed ({event}): {cmd}", Colors.YELLOW),
                    file=sys.stderr,
                )
                if result.stderr.strip():
                    print(f"  {result.stderr.strip()}", file=sys.stderr)
        except Exception as e:
            print(
                colored(f"[WARN] Hook error ({event}): {cmd} — {e}", Colors.YELLOW),
                file=sys.stderr,
            )


# =============================================================================
# Helper Functions
# =============================================================================


def _read_json_file(path: Path) -> dict | None:
    """Read and parse a JSON file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _write_json_file(path: Path, data: dict) -> bool:
    """Write dict to JSON file."""
    try:
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return True
    except (OSError, IOError):
        return False


def _slugify(title: str) -> str:
    """Convert title to slug (only works with ASCII)."""
    result = title.lower()
    result = re.sub(r"[^a-z0-9]", "-", result)
    result = re.sub(r"-+", "-", result)
    result = result.strip("-")
    return result


def _resolve_task_dir(target_dir: str, repo_root: Path) -> Path:
    """Resolve task directory to absolute path.

    Supports:
    - Absolute path: /path/to/task
    - Relative path: .trellis/tasks/01-31-my-task
    - Task name: my-task (uses find_task_by_name for lookup)
    """
    if not target_dir:
        return Path()

    # Absolute path
    if target_dir.startswith("/"):
        return Path(target_dir)

    # Relative path (contains path separator or starts with .trellis)
    if "/" in target_dir or target_dir.startswith(".trellis"):
        return repo_root / target_dir

    # Task name - try to find in tasks directory
    tasks_dir = get_tasks_dir(repo_root)
    found = find_task_by_name(target_dir, tasks_dir)
    if found:
        return found

    # Fallback to treating as relative path
    return repo_root / target_dir


# =============================================================================
# JSONL Default Content Generators
# =============================================================================


def get_implement_base() -> list[dict]:
    """Get base implement context entries."""
    return [
        {
            "file": f"{DIR_WORKFLOW}/workflow.md",
            "reason": "Project workflow and conventions",
        },
        {
            "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/guides/index.md",
            "reason": "Search and tool routing guides",
        },
        {
            "file": f"{DIR_WORKFLOW}/{DIR_MEMORY}/{FILE_DECISIONS}",
            "reason": "Architecture decisions",
        },
        {
            "file": f"{DIR_WORKFLOW}/{DIR_MEMORY}/{FILE_KNOWN_ISSUES}",
            "reason": "Known issues and workarounds",
        },
        {
            "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/guides/verification-before-completion.md",
            "reason": "Must verify before claiming completion",
        },
    ]


def get_implement_python() -> list[dict]:
    """Get Python implement context entries."""
    return [
        {
            "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/python/index.md",
            "reason": "Python development guide",
        },
        {
            "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/python/code-style.md",
            "reason": "Code style conventions",
        },
        {
            "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/python/quality-guidelines.md",
            "reason": "Code quality requirements",
        },
    ]


def get_implement_matlab() -> list[dict]:
    """Get MATLAB implement context entries."""
    return [
        {
            "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/matlab/index.md",
            "reason": "MATLAB development guide",
        },
        {
            "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/matlab/code-style.md",
            "reason": "MATLAB code style",
        },
    ]


def get_implement_trellis() -> list[dict]:
    """Get Trellis self-modification implement context entries."""
    return [
        {
            "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/guides/spec-integration-checklist.md",
            "reason": "Spec integration checklist — injection points for new tools/specs",
        },
        {"file": ".claude/agents/implement.md", "reason": "Implement agent definition"},
        {"file": ".claude/agents/check.md", "reason": "Check agent definition"},
        {"file": ".claude/agents/research.md", "reason": "Research agent definition"},
        {"file": ".claude/agents/debug.md", "reason": "Debug agent definition"},
        {"file": ".claude/agents/dispatch.md", "reason": "Dispatch agent definition"},
        {"file": ".claude/agents/plan.md", "reason": "Plan agent definition"},
        {
            "file": ".claude/hooks/inject-subagent-context.py",
            "reason": "Hook: spec injection into sub-agents",
        },
    ]


def get_check_context(dev_type: str, repo_root: Path) -> list[dict]:
    """Get check context entries."""
    adapter = get_cli_adapter_auto(repo_root)

    entries = [
        {
            "file": adapter.get_trellis_command_path("finish-work"),
            "reason": "Finish work checklist",
        },
        {
            "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/guides/index.md",
            "reason": "Search and tool routing guides",
        },
        {
            "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/guides/verification-before-completion.md",
            "reason": "Must verify before claiming completion",
        },
    ]

    if dev_type in ("python", "both"):
        entries.append(
            {
                "file": adapter.get_trellis_command_path("check-python"),
                "reason": "Python check spec",
            }
        )
    if dev_type in ("matlab", "both"):
        entries.append(
            {
                "file": adapter.get_trellis_command_path("check-matlab"),
                "reason": "MATLAB check spec",
            }
        )
    if dev_type == "trellis":
        entries.append(
            {
                "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/guides/spec-integration-checklist.md",
                "reason": "Spec integration checklist",
            }
        )

    return entries


def get_review_context(dev_type: str, repo_root: Path) -> list[dict]:
    """Get review context entries."""
    adapter = get_cli_adapter_auto(repo_root)

    entries = [
        {
            "file": adapter.get_trellis_command_path("check-cross-layer"),
            "reason": "Cross-layer check dimensions",
        },
        {
            "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/guides/verification-before-completion.md",
            "reason": "Must verify before claiming completion",
        },
    ]

    if dev_type in ("python", "both"):
        entries.append(
            {
                "file": adapter.get_trellis_command_path("check-python"),
                "reason": "Python quality spec",
            }
        )
        entries.append(
            {
                "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/python/code-style.md",
                "reason": "Code clarity and style spec",
            }
        )
    if dev_type in ("matlab", "both"):
        entries.append(
            {
                "file": adapter.get_trellis_command_path("check-matlab"),
                "reason": "MATLAB quality spec",
            }
        )
    if dev_type == "trellis":
        entries.append(
            {
                "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/guides/spec-integration-checklist.md",
                "reason": "Spec integration checklist",
            }
        )

    return entries


def get_debug_context(dev_type: str, repo_root: Path) -> list[dict]:
    """Get debug context entries."""
    adapter = get_cli_adapter_auto(repo_root)

    entries = [
        {
            "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/guides/index.md",
            "reason": "Search and tool routing guides",
        },
        {
            "file": f"{DIR_WORKFLOW}/{DIR_MEMORY}/{FILE_KNOWN_ISSUES}",
            "reason": "Known issues and workarounds",
        },
        {
            "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/guides/receiving-review.md",
            "reason": "Verify feedback before implementing fixes",
        },
    ]

    if dev_type in ("python", "both"):
        entries.append(
            {
                "file": adapter.get_trellis_command_path("check-python"),
                "reason": "Python check spec",
            }
        )
    if dev_type in ("matlab", "both"):
        entries.append(
            {
                "file": adapter.get_trellis_command_path("check-matlab"),
                "reason": "MATLAB check spec",
            }
        )
    if dev_type == "trellis":
        entries.append(
            {
                "file": f"{DIR_WORKFLOW}/{DIR_SPEC}/guides/spec-integration-checklist.md",
                "reason": "Spec integration checklist",
            }
        )

    return entries


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    """Write entries to JSONL file."""
    lines = [json.dumps(entry, ensure_ascii=False) for entry in entries]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# =============================================================================
# Task Operations
# =============================================================================


def ensure_tasks_dir(repo_root: Path) -> Path:
    """Ensure tasks directory exists."""
    tasks_dir = get_tasks_dir(repo_root)
    archive_dir = tasks_dir / "archive"

    if not tasks_dir.exists():
        tasks_dir.mkdir(parents=True)
        print(
            colored(f"Created tasks directory: {tasks_dir}", Colors.GREEN),
            file=sys.stderr,
        )

    if not archive_dir.exists():
        archive_dir.mkdir(parents=True)

    return tasks_dir


# =============================================================================
# Command: create
# =============================================================================


def cmd_create(args: argparse.Namespace) -> int:
    """Create a new task."""
    repo_root = get_repo_root()

    if not args.title:
        print(colored("Error: title is required", Colors.RED), file=sys.stderr)
        return 1

    # Default assignee to current developer
    assignee = args.assignee
    if not assignee:
        assignee = get_developer(repo_root)
        if not assignee:
            print(
                colored(
                    "Error: No developer set. Run init_developer.py first or use --assignee",
                    Colors.RED,
                ),
                file=sys.stderr,
            )
            return 1

    ensure_tasks_dir(repo_root)

    # Get current developer as creator
    creator = get_developer(repo_root) or assignee

    # Generate slug if not provided
    slug = args.slug or _slugify(args.title)
    if not slug:
        print(
            colored("Error: could not generate slug from title", Colors.RED),
            file=sys.stderr,
        )
        return 1

    # Create task directory with MM-DD-slug format
    tasks_dir = get_tasks_dir(repo_root)
    date_prefix = generate_task_date_prefix()
    dir_name = f"{date_prefix}-{slug}"
    task_dir = tasks_dir / dir_name
    task_json_path = task_dir / FILE_TASK_JSON

    if task_dir.exists():
        print(
            colored(
                f"Warning: Task directory already exists: {dir_name}", Colors.YELLOW
            ),
            file=sys.stderr,
        )
    else:
        task_dir.mkdir(parents=True)

    today = datetime.now().strftime("%Y-%m-%d")

    # Record current branch as base_branch (PR target)
    _, branch_out, _ = _run_git_command(["branch", "--show-current"], cwd=repo_root)
    current_branch = branch_out.strip() or "main"

    task_data = {
        "id": slug,
        "name": slug,
        "title": args.title,
        "description": args.description or "",
        "status": "planning",
        "dev_type": None,
        "scope": None,
        "priority": args.priority,
        "creator": creator,
        "assignee": assignee,
        "createdAt": today,
        "completedAt": None,
        "branch": None,
        "base_branch": current_branch,
        "worktree_path": None,
        "current_phase": 0,
        "next_action": [
            {"phase": 1, "action": "implement"},
            {"phase": 2, "action": "check"},
            {"phase": 3, "action": "finish"},
            {"phase": 4, "action": "create-pr"},
        ],
        "status_history": [],
        "commit": None,
        "pr_url": None,
        "subtasks": [],
        "relatedFiles": [],
        "notes": "",
    }

    _write_json_file(task_json_path, task_data)

    print(colored(f"Created task: {dir_name}", Colors.GREEN), file=sys.stderr)
    print("", file=sys.stderr)
    print(colored("Next steps:", Colors.BLUE), file=sys.stderr)
    print("  1. Create prd.md with requirements", file=sys.stderr)
    print("  2. Run: python3 task.py init-context <dir> <dev_type>", file=sys.stderr)
    print("  3. Run: python3 task.py start <dir>", file=sys.stderr)
    print("", file=sys.stderr)

    # Output relative path for script chaining
    print(f"{DIR_WORKFLOW}/{DIR_TASKS}/{dir_name}")

    _run_hooks("after_create", task_json_path, repo_root)
    return 0


# =============================================================================
# Command: init-context
# =============================================================================


def cmd_init_context(args: argparse.Namespace) -> int:
    """Initialize JSONL context files for a task."""
    repo_root = get_repo_root()
    target_dir = _resolve_task_dir(args.dir, repo_root)
    dev_type = args.type

    if not dev_type:
        print(colored("Error: Missing arguments", Colors.RED))
        print("Usage: python3 task.py init-context <task-dir> <dev_type>")
        print("  dev_type: python | matlab | both | trellis | test | docs")
        return 1

    if not target_dir.is_dir():
        print(colored(f"Error: Directory not found: {target_dir}", Colors.RED))
        return 1

    print(colored("=== Initializing Agent Context Files ===", Colors.BLUE))
    print(f"Target dir: {target_dir}")
    print(f"Dev type: {dev_type}")
    print()

    # implement.jsonl
    print(colored("Creating implement.jsonl...", Colors.CYAN))
    implement_entries = get_implement_base()
    if dev_type in ("python", "test"):
        implement_entries.extend(get_implement_python())
    elif dev_type == "matlab":
        implement_entries.extend(get_implement_matlab())
    elif dev_type == "both":
        implement_entries.extend(get_implement_python())
        implement_entries.extend(get_implement_matlab())
    elif dev_type == "trellis":
        implement_entries.extend(get_implement_trellis())

    implement_file = target_dir / "implement.jsonl"
    _write_jsonl(implement_file, implement_entries)
    print(f"  {colored('✓', Colors.GREEN)} {len(implement_entries)} entries")

    # check.jsonl
    print(colored("Creating check.jsonl...", Colors.CYAN))
    check_entries = get_check_context(dev_type, repo_root)
    check_file = target_dir / "check.jsonl"
    _write_jsonl(check_file, check_entries)
    print(f"  {colored('✓', Colors.GREEN)} {len(check_entries)} entries")

    # review.jsonl
    print(colored("Creating review.jsonl...", Colors.CYAN))
    review_entries = get_review_context(dev_type, repo_root)
    review_file = target_dir / "review.jsonl"
    _write_jsonl(review_file, review_entries)
    print(f"  {colored('✓', Colors.GREEN)} {len(review_entries)} entries")

    # debug.jsonl
    print(colored("Creating debug.jsonl...", Colors.CYAN))
    debug_entries = get_debug_context(dev_type, repo_root)
    debug_file = target_dir / "debug.jsonl"
    _write_jsonl(debug_file, debug_entries)
    print(f"  {colored('✓', Colors.GREEN)} {len(debug_entries)} entries")

    print()
    print(colored("✓ All context files created", Colors.GREEN))
    print()
    print(colored("Next steps:", Colors.BLUE))
    print(
        "  1. Add task-specific specs: python3 task.py add-context <dir> <jsonl> <path>"
    )
    print("  2. Set as current: python3 task.py start <dir>")

    return 0


# =============================================================================
# Command: add-context
# =============================================================================


def cmd_add_context(args: argparse.Namespace) -> int:
    """Add entry to JSONL context file."""
    repo_root = get_repo_root()
    target_dir = _resolve_task_dir(args.dir, repo_root)

    jsonl_name = args.file
    path = args.path
    reason = args.reason or "Added manually"

    if not target_dir.is_dir():
        print(colored(f"Error: Directory not found: {target_dir}", Colors.RED))
        return 1

    # Support shorthand
    if not jsonl_name.endswith(".jsonl"):
        jsonl_name = f"{jsonl_name}.jsonl"

    jsonl_file = target_dir / jsonl_name
    full_path = repo_root / path

    is_reference = getattr(args, "reference", False)

    entry_type = "file"
    if is_reference:
        entry_type = "reference"
        # Normalize directory path
        if full_path.is_dir() and not path.endswith("/"):
            path = f"{path}/"
    elif full_path.is_dir():
        entry_type = "directory"
        if not path.endswith("/"):
            path = f"{path}/"
    elif not full_path.is_file():
        print(colored(f"Error: Path not found: {path}", Colors.RED))
        return 1

    # Check if already exists
    if jsonl_file.is_file():
        content = jsonl_file.read_text(encoding="utf-8")
        if f'"{path}"' in content:
            print(colored(f"Warning: Entry already exists for {path}", Colors.YELLOW))
            return 0

    # Add entry
    entry: dict
    if entry_type in ("directory", "reference"):
        entry = {"file": path, "type": entry_type, "reason": reason}
    else:
        entry = {"file": path, "reason": reason}

    with jsonl_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(colored(f"Added {entry_type}: {path}", Colors.GREEN))
    return 0


# =============================================================================
# Command: validate
# =============================================================================


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate JSONL context files."""
    repo_root = get_repo_root()
    target_dir = _resolve_task_dir(args.dir, repo_root)

    if not target_dir.is_dir():
        print(colored("Error: task directory required", Colors.RED))
        return 1

    print(colored("=== Validating Context Files ===", Colors.BLUE))
    print(f"Target dir: {target_dir}")
    print()

    total_errors = 0
    for jsonl_name in ["implement.jsonl", "check.jsonl", "review.jsonl", "debug.jsonl"]:
        jsonl_file = target_dir / jsonl_name
        errors = _validate_jsonl(jsonl_file, repo_root)
        total_errors += errors

    print()
    if total_errors == 0:
        print(colored("✓ All validations passed", Colors.GREEN))
        return 0
    else:
        print(colored(f"✗ Validation failed ({total_errors} errors)", Colors.RED))
        return 1


def _validate_jsonl(jsonl_file: Path, repo_root: Path) -> int:
    """Validate a single JSONL file."""
    file_name = jsonl_file.name
    errors = 0

    if not jsonl_file.is_file():
        print(f"  {colored(f'{file_name}: not found (skipped)', Colors.YELLOW)}")
        return 0

    line_num = 0
    for line in jsonl_file.read_text(encoding="utf-8").splitlines():
        line_num += 1
        if not line.strip():
            continue

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            print(f"  {colored(f'{file_name}:{line_num}: Invalid JSON', Colors.RED)}")
            errors += 1
            continue

        file_path = data.get("file")
        entry_type = data.get("type", "file")

        if not file_path:
            print(
                f"  {colored(f'{file_name}:{line_num}: Missing file field', Colors.RED)}"
            )
            errors += 1
            continue

        full_path = repo_root / file_path
        if entry_type == "directory":
            if not full_path.is_dir():
                print(
                    f"  {colored(f'{file_name}:{line_num}: Directory not found: {file_path}', Colors.RED)}"
                )
                errors += 1
        else:
            if not full_path.is_file():
                print(
                    f"  {colored(f'{file_name}:{line_num}: File not found: {file_path}', Colors.RED)}"
                )
                errors += 1

    if errors == 0:
        print(f"  {colored(f'{file_name}: ✓ ({line_num} entries)', Colors.GREEN)}")
    else:
        print(f"  {colored(f'{file_name}: ✗ ({errors} errors)', Colors.RED)}")

    return errors


# =============================================================================
# Command: list-context
# =============================================================================


def cmd_list_context(args: argparse.Namespace) -> int:
    """List JSONL context entries."""
    repo_root = get_repo_root()
    target_dir = _resolve_task_dir(args.dir, repo_root)

    if not target_dir.is_dir():
        print(colored("Error: task directory required", Colors.RED))
        return 1

    print(colored("=== Context Files ===", Colors.BLUE))
    print()

    for jsonl_name in ["implement.jsonl", "check.jsonl", "review.jsonl", "debug.jsonl"]:
        jsonl_file = target_dir / jsonl_name
        if not jsonl_file.is_file():
            continue

        print(colored(f"[{jsonl_name}]", Colors.CYAN))

        count = 0
        for line in jsonl_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            count += 1
            file_path = data.get("file", "?")
            entry_type = data.get("type", "file")
            reason = data.get("reason", "-")

            if entry_type == "directory":
                print(f"  {colored(f'{count}.', Colors.GREEN)} [DIR] {file_path}")
            else:
                print(f"  {colored(f'{count}.', Colors.GREEN)} {file_path}")
            print(f"     {colored('→', Colors.YELLOW)} {reason}")

        print()

    return 0


# =============================================================================
# Command: start / finish
# =============================================================================


def cmd_start(args: argparse.Namespace) -> int:
    """Set current task."""
    repo_root = get_repo_root()
    task_input = args.dir

    if not task_input:
        print(colored("Error: task directory or name required", Colors.RED))
        return 1

    # Resolve task directory (supports task name, relative path, or absolute path)
    full_path = _resolve_task_dir(task_input, repo_root)

    if not full_path.is_dir():
        print(colored(f"Error: Task not found: {task_input}", Colors.RED))
        print(
            "Hint: Use task name (e.g., 'my-task') or full path (e.g., '.trellis/tasks/01-31-my-task')"
        )
        return 1

    # Convert to relative path for storage
    try:
        task_dir = str(full_path.relative_to(repo_root))
    except ValueError:
        task_dir = str(full_path)

    if set_current_task(task_dir, repo_root):
        print(colored(f"✓ Current task set to: {task_dir}", Colors.GREEN))

        # Initialize scratchpad with task info (Mod 2: Session Context Freshness)
        memory_dir = ensure_memory_dir(repo_root)
        scratchpad = memory_dir / FILE_SCRATCHPAD
        task_json_path = full_path / FILE_TASK_JSON
        task_title = "unknown"
        if task_json_path.is_file():
            data = _read_json_file(task_json_path)
            if data:
                task_title = data.get("title") or data.get("name") or "unknown"
        today = datetime.now().strftime("%Y-%m-%d")
        scratchpad.write_text(
            f"# Scratchpad\n\n"
            f"> Task: {task_title}\n"
            f"> Started: {today}\n"
            f"> Directory: {task_dir}\n\n"
            f"## Current Focus\n(Add WIP notes here)\n\n"
            f"## Open Questions\n(Add questions here)\n",
            encoding="utf-8",
        )
        print(colored("✓ Scratchpad initialized for task", Colors.CYAN))

        print()
        print(
            colored(
                "The hook will now inject context from this task's jsonl files.",
                Colors.BLUE,
            )
        )

        _run_hooks("after_start", task_json_path, repo_root)
        return 0
    else:
        print(colored("Error: Failed to set current task", Colors.RED))
        return 1


def _reset_scratchpad(repo_root: Path) -> None:
    """Reset scratchpad to inactive state."""
    memory_dir = get_memory_dir(repo_root)
    if memory_dir.is_dir():
        scratchpad = memory_dir / FILE_SCRATCHPAD
        scratchpad.write_text(
            "# Scratchpad\n\n"
            "> Ephemeral WIP notes. Overwritten when new task starts.\n\n"
            "(No active task)\n",
            encoding="utf-8",
        )


def cmd_finish(args: argparse.Namespace) -> int:
    """Clear current task."""
    repo_root = get_repo_root()
    current = get_current_task(repo_root)

    if not current:
        print(colored("No current task set", Colors.YELLOW))
        return 0

    # Resolve task.json path before clearing
    task_json_path = repo_root / current / FILE_TASK_JSON

    clear_current_task(repo_root)
    print(colored(f"✓ Cleared current task (was: {current})", Colors.GREEN))

    # Reset scratchpad (Mod 2: Session Context Freshness)
    _reset_scratchpad(repo_root)
    print(colored("✓ Scratchpad reset", Colors.CYAN))

    if task_json_path.is_file():
        _run_hooks("after_finish", task_json_path, repo_root)
    return 0


# =============================================================================
# Command: complete
# =============================================================================

# Valid status transitions (state machine)
VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "planning": {"active", "rejected"},
    "active": {"review", "blocked"},
    "review": {"active", "completed"},
    "blocked": {"active"},
    "completed": set(),
    "rejected": set(),
}


def cmd_complete(args: argparse.Namespace) -> int:
    """Complete a task (status + cleanup)."""
    repo_root = get_repo_root()

    target_input = args.dir
    if not target_input:
        # Try current task
        current = get_current_task(repo_root)
        if not current:
            print(
                colored(
                    "Error: No task directory specified and no current task set",
                    Colors.RED,
                )
            )
            print("Usage: python3 task.py complete <task-dir>")
            return 1
        target_input = current

    target_dir = _resolve_task_dir(target_input, repo_root)
    task_json_path = target_dir / FILE_TASK_JSON

    if not task_json_path.is_file():
        print(colored(f"Error: task.json not found at {target_dir}", Colors.RED))
        return 1

    data = _read_json_file(task_json_path)
    if not data:
        return 1

    dir_name = target_dir.name
    task_title = data.get("title") or data.get("name") or "unknown"
    current_status = data.get("status", "planning")

    print(colored("=== Completing Task ===", Colors.BLUE))
    print(f"Task: {task_title}")
    print(f"Directory: {dir_name}")
    print(f"Current status: {current_status}")
    print()

    # Validate transition
    if current_status == "completed":
        print(colored("Task is already completed", Colors.YELLOW))
        return 0

    if current_status == "active":
        print(
            colored(
                "Note: Skipping 'review' phase (active -> completed)", Colors.YELLOW
            )
        )
    elif current_status != "review":
        print(
            colored(
                f"Error: Cannot complete task with status '{current_status}'",
                Colors.RED,
            )
        )
        print("Task must be in 'active' or 'review' status to complete.")
        return 1

    # 1. Get latest commit hash
    _, commit_out, _ = _run_git_command(["rev-parse", "--short", "HEAD"], cwd=repo_root)
    commit_hash = commit_out.strip() or "unknown"

    # 2. Update task.json
    now = datetime.now().strftime("%Y-%m-%d")
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    developer = get_developer(repo_root) or "manual"

    data["status"] = "completed"
    data["completedAt"] = now
    data["commit"] = commit_hash
    if "status_history" not in data:
        data["status_history"] = []
    data["status_history"].append(
        {
            "from": current_status,
            "to": "completed",
            "at": now_utc,
            "by": developer,
        }
    )
    _write_json_file(task_json_path, data)

    print(colored(f"✓ Status: {current_status} -> completed", Colors.GREEN))
    print(colored(f"✓ Commit: {commit_hash}", Colors.GREEN))

    # 3. Clear current task pointer if this is the current task
    current = get_current_task(repo_root)
    relative_dir = f"{DIR_WORKFLOW}/{DIR_TASKS}/{dir_name}"
    if current and (current == relative_dir or dir_name in current):
        clear_current_task(repo_root)
        print(colored("✓ Cleared current task pointer", Colors.GREEN))

    # 4. Reset scratchpad
    _reset_scratchpad(repo_root)
    print(colored("✓ Scratchpad reset", Colors.GREEN))

    print()
    print(colored("=== Task Completed ===", Colors.GREEN))
    print()
    print(colored("Archive this task now?", Colors.CYAN))
    print(f"  Run: python3 task.py archive {dir_name}")

    _run_hooks("after_finish", task_json_path, repo_root)
    return 0


# =============================================================================
# Command: set-status (State Machine)
# =============================================================================


def cmd_set_status(args: argparse.Namespace) -> int:
    """Set task status with state machine validation."""
    repo_root = get_repo_root()
    target_dir = _resolve_task_dir(args.dir, repo_root)
    new_status = args.status

    if not new_status:
        print(colored("Error: Missing arguments", Colors.RED))
        _print_status_help()
        return 1

    task_json_path = target_dir / FILE_TASK_JSON
    if not task_json_path.is_file():
        print(colored(f"Error: task.json not found at {target_dir}", Colors.RED))
        return 1

    data = _read_json_file(task_json_path)
    if not data:
        return 1

    current_status = data.get("status", "planning")

    # Validate transition
    allowed = VALID_STATUS_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        print(
            colored(
                f"Error: Invalid transition: {current_status} -> {new_status}",
                Colors.RED,
            )
        )
        allowed_str = (
            ", ".join(sorted(allowed))
            if allowed
            else "(terminal state, no transitions)"
        )
        print(f"Allowed from '{current_status}': {allowed_str}")
        return 1

    # Update status and append to history
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    developer = get_developer(repo_root) or "manual"

    data["status"] = new_status
    if "status_history" not in data:
        data["status_history"] = []
    data["status_history"].append(
        {
            "from": current_status,
            "to": new_status,
            "at": now_utc,
            "by": developer,
        }
    )
    _write_json_file(task_json_path, data)

    print(colored(f"✓ Status: {current_status} -> {new_status}", Colors.GREEN))
    return 0


def _print_status_help() -> None:
    """Print set-status help text."""
    print("Usage: python3 task.py set-status <task-dir> <status>")
    print("  Valid statuses: planning, active, review, blocked, completed, rejected")
    print()
    print("  Valid transitions:")
    print("    planning  -> active, rejected")
    print("    active    -> review, blocked")
    print("    review    -> active, completed")
    print("    blocked   -> active")


# =============================================================================
# Command: archive
# =============================================================================


def cmd_archive(args: argparse.Namespace) -> int:
    """Archive completed task."""
    repo_root = get_repo_root()
    task_name = args.name

    if not task_name:
        print(colored("Error: Task name is required", Colors.RED), file=sys.stderr)
        return 1

    tasks_dir = get_tasks_dir(repo_root)

    # Find task directory
    task_dir = find_task_by_name(task_name, tasks_dir)

    if not task_dir or not task_dir.is_dir():
        print(
            colored(f"Error: Task not found: {task_name}", Colors.RED), file=sys.stderr
        )
        print("Active tasks:", file=sys.stderr)
        cmd_list(argparse.Namespace(mine=False, status=None))
        return 1

    dir_name = task_dir.name
    task_json_path = task_dir / FILE_TASK_JSON

    # Update status before archiving
    today = datetime.now().strftime("%Y-%m-%d")
    if task_json_path.is_file():
        data = _read_json_file(task_json_path)
        if data:
            data["status"] = "completed"
            data["completedAt"] = today
            _write_json_file(task_json_path, data)

    # Clear if current task
    current = get_current_task(repo_root)
    if current and dir_name in current:
        clear_current_task(repo_root)

    # Archive
    result = archive_task_complete(task_dir, repo_root)
    if "archived_to" in result:
        archive_dest = Path(result["archived_to"])
        year_month = archive_dest.parent.name
        print(
            colored(f"Archived: {dir_name} -> archive/{year_month}/", Colors.GREEN),
            file=sys.stderr,
        )

        # Return the archive path
        print(f"{DIR_WORKFLOW}/{DIR_TASKS}/{DIR_ARCHIVE}/{year_month}/{dir_name}")

        # Run hooks with the archived path
        archived_json = archive_dest / FILE_TASK_JSON
        _run_hooks("after_archive", archived_json, repo_root)
        return 0

    return 1


# =============================================================================
# Command: list
# =============================================================================


def cmd_list(args: argparse.Namespace) -> int:
    """List active tasks."""
    repo_root = get_repo_root()
    tasks_dir = get_tasks_dir(repo_root)
    current_task = get_current_task(repo_root)
    developer = get_developer(repo_root)
    filter_mine = args.mine
    filter_status = args.status

    if filter_mine:
        if not developer:
            print(
                colored(
                    "Error: No developer set. Run init_developer.py first", Colors.RED
                ),
                file=sys.stderr,
            )
            return 1
        print(colored(f"My tasks (assignee: {developer}):", Colors.BLUE))
    else:
        print(colored("All active tasks:", Colors.BLUE))
    print()

    count = 0
    if tasks_dir.is_dir():
        for d in sorted(tasks_dir.iterdir()):
            if not d.is_dir() or d.name == "archive":
                continue

            dir_name = d.name
            task_json = d / FILE_TASK_JSON
            status = "unknown"
            assignee = "-"
            relative_path = f"{DIR_WORKFLOW}/{DIR_TASKS}/{dir_name}"

            if task_json.is_file():
                data = _read_json_file(task_json)
                if data:
                    status = data.get("status", "unknown")
                    assignee = data.get("assignee", "-")

            # Apply --mine filter
            if filter_mine and assignee != developer:
                continue

            # Apply --status filter
            if filter_status and status != filter_status:
                continue

            marker = ""
            if relative_path == current_task:
                marker = f" {colored('<- current', Colors.GREEN)}"

            if filter_mine:
                print(f"  - {dir_name}/ ({status}){marker}")
            else:
                print(
                    f"  - {dir_name}/ ({status}) [{colored(assignee, Colors.CYAN)}]{marker}"
                )
            count += 1

    if count == 0:
        if filter_mine:
            print("  (no tasks assigned to you)")
        else:
            print("  (no active tasks)")

    print()
    print(f"Total: {count} task(s)")
    return 0


# =============================================================================
# Command: list-archive
# =============================================================================


def cmd_list_archive(args: argparse.Namespace) -> int:
    """List archived tasks."""
    repo_root = get_repo_root()
    tasks_dir = get_tasks_dir(repo_root)
    archive_dir = tasks_dir / "archive"
    month = args.month

    print(colored("Archived tasks:", Colors.BLUE))
    print()

    if month:
        month_dir = archive_dir / month
        if month_dir.is_dir():
            print(f"[{month}]")
            for d in sorted(month_dir.iterdir()):
                if d.is_dir():
                    print(f"  - {d.name}/")
        else:
            print(f"  No archives for {month}")
    else:
        if archive_dir.is_dir():
            for month_dir in sorted(archive_dir.iterdir()):
                if month_dir.is_dir():
                    month_name = month_dir.name
                    count = sum(1 for d in month_dir.iterdir() if d.is_dir())
                    print(f"[{month_name}] - {count} task(s)")

    return 0


# =============================================================================
# Command: set-branch
# =============================================================================


def cmd_set_branch(args: argparse.Namespace) -> int:
    """Set git branch for task."""
    repo_root = get_repo_root()
    target_dir = _resolve_task_dir(args.dir, repo_root)
    branch = args.branch

    if not branch:
        print(colored("Error: Missing arguments", Colors.RED))
        print("Usage: python3 task.py set-branch <task-dir> <branch-name>")
        return 1

    task_json = target_dir / FILE_TASK_JSON
    if not task_json.is_file():
        print(colored(f"Error: task.json not found at {target_dir}", Colors.RED))
        return 1

    data = _read_json_file(task_json)
    if not data:
        return 1

    data["branch"] = branch
    _write_json_file(task_json, data)

    print(colored(f"✓ Branch set to: {branch}", Colors.GREEN))
    print()
    print(colored("Now you can start the multi-agent pipeline:", Colors.BLUE))
    print(f"  python3 ./.trellis/scripts/multi_agent/start.py {args.dir}")
    return 0


# =============================================================================
# Command: set-base-branch
# =============================================================================


def cmd_set_base_branch(args: argparse.Namespace) -> int:
    """Set the base branch (PR target) for task."""
    repo_root = get_repo_root()
    target_dir = _resolve_task_dir(args.dir, repo_root)
    base_branch = args.base_branch

    if not base_branch:
        print(colored("Error: Missing arguments", Colors.RED))
        print("Usage: python3 task.py set-base-branch <task-dir> <base-branch>")
        print("Example: python3 task.py set-base-branch <dir> develop")
        print()
        print(
            "This sets the target branch for PR (the branch your feature will merge into)."
        )
        return 1

    task_json = target_dir / FILE_TASK_JSON
    if not task_json.is_file():
        print(colored(f"Error: task.json not found at {target_dir}", Colors.RED))
        return 1

    data = _read_json_file(task_json)
    if not data:
        return 1

    data["base_branch"] = base_branch
    _write_json_file(task_json, data)

    print(colored(f"✓ Base branch set to: {base_branch}", Colors.GREEN))
    print(f"  PR will target: {base_branch}")
    return 0


# =============================================================================
# Command: set-scope
# =============================================================================


def cmd_set_scope(args: argparse.Namespace) -> int:
    """Set scope for PR title."""
    repo_root = get_repo_root()
    target_dir = _resolve_task_dir(args.dir, repo_root)
    scope = args.scope

    if not scope:
        print(colored("Error: Missing arguments", Colors.RED))
        print("Usage: python3 task.py set-scope <task-dir> <scope>")
        return 1

    task_json = target_dir / FILE_TASK_JSON
    if not task_json.is_file():
        print(colored(f"Error: task.json not found at {target_dir}", Colors.RED))
        return 1

    data = _read_json_file(task_json)
    if not data:
        return 1

    data["scope"] = scope
    _write_json_file(task_json, data)

    print(colored(f"✓ Scope set to: {scope}", Colors.GREEN))
    return 0


# =============================================================================
# Command: create-pr (delegates to multi-agent script)
# =============================================================================


def cmd_create_pr(args: argparse.Namespace) -> int:
    """Create PR from task - delegates to multi_agent/create_pr.py."""
    import subprocess

    script_dir = Path(__file__).parent
    create_pr_script = script_dir / "multi_agent" / "create_pr.py"

    cmd = [sys.executable, str(create_pr_script)]
    if args.dir:
        cmd.append(args.dir)
    if args.dry_run:
        cmd.append("--dry-run")

    result = subprocess.run(cmd)
    return result.returncode


# =============================================================================
# Help
# =============================================================================


def show_usage() -> None:
    """Show usage help."""
    print("""Task Management Script for Multi-Agent Pipeline

Usage:
  python3 task.py create <title>                     Create new task directory
  python3 task.py init-context <dir> <dev_type>      Initialize jsonl files
  python3 task.py add-context <dir> <jsonl> <path> [reason]  Add entry to jsonl
  python3 task.py validate <dir>                     Validate jsonl files
  python3 task.py list-context <dir>                 List jsonl entries
  python3 task.py start <dir>                        Set as current task
  python3 task.py finish                             Clear current task
  python3 task.py complete [dir]                     Complete task (status + cleanup)
  python3 task.py set-status <dir> <status>          Set task status (state machine)
  python3 task.py set-branch <dir> <branch>          Set git branch for multi-agent
  python3 task.py set-scope <dir> <scope>            Set scope for PR title
  python3 task.py create-pr [dir] [--dry-run]        Create PR from task
  python3 task.py archive <task-name>                Archive completed task
  python3 task.py list [--mine] [--status <status>]  List tasks
  python3 task.py list-archive [YYYY-MM]             List archived tasks

Arguments:
  dev_type: python | matlab | both | trellis | test | docs

Status transitions (state machine):
  planning  -> active, rejected
  active    -> review, blocked
  review    -> active, completed
  blocked   -> active

List options:
  --mine, -m           Show only tasks assigned to current developer
  --status, -s <s>     Filter by status (planning, active, review, completed, blocked)

Examples:
  python3 task.py create "Add feature" --slug add-feature
  python3 task.py init-context .trellis/tasks/01-21-add-feature python
  python3 task.py add-context <dir> implement .trellis/spec/python/code-style.md "Code style"
  python3 task.py set-branch <dir> feature/add-feature
  python3 task.py start .trellis/tasks/01-21-add-feature
  python3 task.py complete                           # Complete current task
  python3 task.py set-status <dir> active            # Transition status
  python3 task.py create-pr                          # Uses current task
  python3 task.py create-pr <dir> --dry-run          # Preview without changes
  python3 task.py finish
  python3 task.py archive add-feature
  python3 task.py list                               # List all active tasks
  python3 task.py list --mine                        # List my tasks only
""")


# =============================================================================
# Main Entry
# =============================================================================


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Task Management Script for Multi-Agent Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # create
    p_create = subparsers.add_parser("create", help="Create new task")
    p_create.add_argument("title", help="Task title")
    p_create.add_argument("--slug", "-s", help="Task slug")
    p_create.add_argument("--assignee", "-a", help="Assignee developer")
    p_create.add_argument("--priority", "-p", default="P2", help="Priority (P0-P3)")
    p_create.add_argument("--description", "-d", help="Task description")

    # init-context
    p_init = subparsers.add_parser("init-context", help="Initialize context files")
    p_init.add_argument("dir", help="Task directory")
    p_init.add_argument("type", help="Dev type: python|matlab|both|trellis|test|docs")

    # add-context
    p_add = subparsers.add_parser("add-context", help="Add context entry")
    p_add.add_argument("dir", help="Task directory")
    p_add.add_argument("file", help="JSONL file (implement|check|debug)")
    p_add.add_argument("path", help="File path to add")
    p_add.add_argument("reason", nargs="?", help="Reason for adding")
    p_add.add_argument(
        "--reference",
        action="store_true",
        help="Add as reference type (inject only index.md from directory)",
    )

    # validate
    p_validate = subparsers.add_parser("validate", help="Validate context files")
    p_validate.add_argument("dir", help="Task directory")

    # list-context
    p_listctx = subparsers.add_parser("list-context", help="List context entries")
    p_listctx.add_argument("dir", help="Task directory")

    # start
    p_start = subparsers.add_parser("start", help="Set current task")
    p_start.add_argument("dir", help="Task directory")

    # finish / clear-current
    subparsers.add_parser("finish", help="Clear current task")
    subparsers.add_parser("clear-current", help="Clear current task (alias for finish)")

    # complete
    p_complete = subparsers.add_parser(
        "complete", help="Complete task (status + cleanup)"
    )
    p_complete.add_argument(
        "dir", nargs="?", help="Task directory (defaults to current task)"
    )

    # set-status
    p_setstatus = subparsers.add_parser("set-status", help="Set task status")
    p_setstatus.add_argument("dir", help="Task directory")
    p_setstatus.add_argument("status", help="New status")

    # set-branch
    p_branch = subparsers.add_parser("set-branch", help="Set git branch")
    p_branch.add_argument("dir", help="Task directory")
    p_branch.add_argument("branch", help="Branch name")

    # set-base-branch
    p_base = subparsers.add_parser("set-base-branch", help="Set PR target branch")
    p_base.add_argument("dir", help="Task directory")
    p_base.add_argument("base_branch", help="Base branch name (PR target)")

    # set-scope
    p_scope = subparsers.add_parser("set-scope", help="Set scope")
    p_scope.add_argument("dir", help="Task directory")
    p_scope.add_argument("scope", help="Scope name")

    # create-pr
    p_pr = subparsers.add_parser("create-pr", help="Create PR")
    p_pr.add_argument("dir", nargs="?", help="Task directory")
    p_pr.add_argument("--dry-run", action="store_true", help="Dry run mode")

    # archive
    p_archive = subparsers.add_parser("archive", help="Archive task")
    p_archive.add_argument("name", help="Task name")

    # list
    p_list = subparsers.add_parser("list", help="List tasks")
    p_list.add_argument("--mine", "-m", action="store_true", help="My tasks only")
    p_list.add_argument("--status", "-s", help="Filter by status")

    # list-archive
    p_listarch = subparsers.add_parser("list-archive", help="List archived tasks")
    p_listarch.add_argument("month", nargs="?", help="Month (YYYY-MM)")

    args = parser.parse_args()

    if not args.command:
        show_usage()
        return 1

    commands = {
        "create": cmd_create,
        "init-context": cmd_init_context,
        "add-context": cmd_add_context,
        "validate": cmd_validate,
        "list-context": cmd_list_context,
        "start": cmd_start,
        "finish": cmd_finish,
        "clear-current": cmd_finish,
        "complete": cmd_complete,
        "set-status": cmd_set_status,
        "set-branch": cmd_set_branch,
        "set-base-branch": cmd_set_base_branch,
        "set-scope": cmd_set_scope,
        "create-pr": cmd_create_pr,
        "archive": cmd_archive,
        "list": cmd_list,
        "list-archive": cmd_list_archive,
    }

    if args.command in commands:
        return commands[args.command](args)
    else:
        show_usage()
        return 1


if __name__ == "__main__":
    sys.exit(main())
