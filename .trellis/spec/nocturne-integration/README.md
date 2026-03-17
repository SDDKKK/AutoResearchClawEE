# Nocturne Memory MCP Integration

> **Purpose**: Integration of Nocturne long-term memory with Trellis framework

## Overview

This integration connects the Trellis framework with Nocturne Memory MCP, providing a layered memory architecture:

```
Layer 3: Nocturne (Long-Term)
    - Cross-project patterns
    - Domain knowledge
    - Tool mastery

Layer 2: Trellis Memory (Project-Local)
    - decisions.md
    - known-issues.md
    - learnings.md
    - scratchpad.md

Layer 1: Session (Context Window)
    - Active code
    - Current task
    - Agent prompts
```

## Architecture

See [architecture.md](./architecture.md) for detailed architecture documentation.

## Quick Start

### 1. Verify Installation

```bash
# Check if Nocturne client is available
python3 -c "from nocturne_client import NocturneClient; print('OK')"

# Check if Nocturne database is accessible
python3 -c "
from nocturne_client import NocturneClient
c = NocturneClient()
print(f'Available: {c.is_available()}')
"
```

### 2. Initialize Namespace (Optional)

```bash
# Create trellis:// namespace structure in Nocturne
python3 .trellis/scripts/init-nocturne-namespace.py
```

### 3. Verify Hook Integration

```bash
# Check session start includes Nocturne context
python3 .claude/hooks/session-start.py 2>&1 | grep -A3 "<nocturne>"

# Check agent prompts include Nocturne hints
echo '{"tool_name": "Task", "tool_input": {"subagent_type": "implement", "prompt": "test"}}' | \
  python3 .claude/hooks/inject-subagent-context.py | grep -o "Nocturne"
```

## Components

### Python Modules

| File | Purpose |
|------|---------|
| `.trellis/scripts/nocturne_client.py` | SQLite client for reading Nocturne |
| `.trellis/scripts/promote-to-nocturne.py` | Promote learnings/decisions to Nocturne |
| `.trellis/scripts/sync-trellis-to-nocturne.py` | Batch sync memories to Nocturne |
| `.trellis/scripts/init-nocturne-namespace.py` | Initialize Nocturne namespace |

### Hooks

| File | Purpose |
|------|---------|
| `.claude/hooks/session-start.py` | Inject Nocturne memories on session start |
| `.claude/hooks/inject-subagent-context.py` | Add Nocturne hints to agent prompts |

### Configuration

| File | Purpose |
|------|---------|
| `.trellis/config/nocturne.yaml` | Nocturne integration configuration |

### Documentation

| File | Purpose |
|------|---------|
| `agent-guide.md` | Guide for agents using Nocturne |
| `test-plan.md` | Testing strategy and test cases |
| `troubleshooting.md` | Common issues and solutions |
| `architecture.md` | Detailed architecture documentation |
| `prd.md` | Product requirements document |

## Usage

### For Agents

Agents can query Nocturne using MCP tools:

```python
# Read a specific memory
read_memory("trellis://patterns/python/error-handling")

# Search for relevant patterns
search_memory("polars dataframe", domain="trellis")
```

See [agent-guide.md](./agent-guide.md) for detailed usage instructions.

### For Users

#### Promote a Learning to Nocturne

```bash
# List available entries
python3 .trellis/scripts/promote-to-nocturne.py --list

# Promote a learning (interactive mode)
python3 .trellis/scripts/promote-to-nocturne.py --learning 5

# Promote with auto-generated URI
python3 .trellis/scripts/promote-to-nocturne.py --learning 5 --auto-uri --priority 2
```

#### Sync All Memories

```bash
# Preview what would be synced
python3 .trellis/scripts/sync-trellis-to-nocturne.py --dry-run

# Sync all new entries
python3 .trellis/scripts/sync-trellis-to-nocturne.py

# Force overwrite existing entries
python3 .trellis/scripts/sync-trellis-to-nocturne.py --force
```

#### Record Session with Learning Promotion

```bash
# Record session and promote learning
python3 ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --learning "Learned something important" \
  --promote-learning
```

## Configuration

### nocturne.yaml

```yaml
# Enable/disable Nocturne integration
enabled: true

# Path to Nocturne SQLite database
db_path: "${NOCTURNE_DB_PATH:-~/.nocturne/memory.db}"

# Project identifier
project_id: "researchclaw"

# Auto-load patterns on session start
auto_load_patterns:
  - domain: "trellis"
    path_prefix: "patterns/python/%"
    max_results: 10

# Priority threshold (only load priority <= threshold)
priority_threshold: 2
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NOCTURNE_DB_PATH` | Path to Nocturne SQLite database | `~/.nocturne/memory.db` |
| `NOCTURNE_ENABLED` | Enable Nocturne integration | `true` |

## URI Namespace

### Patterns

- `trellis://patterns/python/...` - Python coding patterns
- `trellis://patterns/matlab/...` - MATLAB patterns
- `trellis://patterns/architecture/...` - Architecture patterns

### Domain Knowledge

- `trellis://domain/power-systems/...` - Power systems knowledge

### Tools

- `trellis://tools/claude-code/...` - Claude Code usage tips
- `trellis://tools/mcp/...` - MCP tool usage

### Project-Specific

- `trellis://projects/researchclaw/decisions/...` - Architecture decisions
- `trellis://projects/researchclaw/learnings/...` - Project learnings
- `trellis://projects/researchclaw/known-issues/...` - Known issues

## Troubleshooting

See [troubleshooting.md](./troubleshooting.md) for common issues and solutions.

Quick checks:

```bash
# Check Nocturne availability
python3 -c "from nocturne_client import NocturneClient; c = NocturneClient(); print(c.is_available())"

# Check configuration
cat .trellis/config/nocturne.yaml

# Test hooks
python3 .claude/hooks/session-start.py 2>&1 | head -20
```

## Testing

See [test-plan.md](./test-plan.md) for detailed testing information.

Run tests:

```bash
# Run unit tests
python3 .trellis/scripts/test_nocturne_client.py

# Run integration tests
python3 .trellis/scripts/test_nocturne_integration.py
```

## Performance

Target metrics:

| Metric | Target | Status |
|--------|--------|--------|
| Session start overhead | < 100ms | ✓ |
| MCP read operations | < 500ms | ✓ |
| MCP write operations | < 1s | ✓ |

## Security

- No API keys stored in Nocturne
- All writes versioned and reviewable
- Graceful degradation if Nocturne unavailable

## Contributing

When adding new features:

1. Update relevant documentation
2. Add tests to test-plan.md
3. Update troubleshooting.md if needed
4. Run ruff check and ruff format

## References

- [Nocturne Memory MCP](https://github.com/...) - External MCP server
- [Trellis Workflow](../../workflow.md) - Main Trellis documentation
- [Architecture](./architecture.md) - Detailed architecture
