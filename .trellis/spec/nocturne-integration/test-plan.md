# Nocturne Memory Integration - Test Plan

> **Purpose**: Comprehensive test plan for Nocturne Memory MCP integration

## Overview

This document outlines the testing strategy for the Nocturne Memory MCP integration with the Trellis framework. Tests are organized by type and priority.

## Test Categories

| Category | Description | Priority |
|----------|-------------|----------|
| Unit Tests | Individual function testing | P0 |
| Integration Tests | Component interaction testing | P0 |
| Performance Tests | Performance validation | P1 |
| End-to-End Tests | Full workflow testing | P1 |

## Unit Tests

### nocturne_client.py

#### Test: Client Initialization
```python
def test_client_initialization():
    """Test NocturneClient can be initialized with various parameters."""
    # Test default initialization
    client = NocturneClient()
    assert client._db_path is not None

    # Test with explicit path
    client = NocturneClient("/custom/path.db")
    assert client._db_path == "/custom/path.db"

    # Test with environment variable
    os.environ["NOCTURNE_DB_PATH"] = "/env/path.db"
    client = NocturneClient()
    assert client._db_path == "/env/path.db"
```

#### Test: URI Parsing
```python
def test_parse_nocturne_uri():
    """Test URI parsing for various formats."""
    # Valid URIs
    assert NocturneClient.parse_nocturne_uri("trellis://patterns/python") == ("trellis", "patterns/python")
    assert NocturneClient.parse_nocturne_uri("core://agent") == ("core", "agent")
    assert NocturneClient.parse_nocturne_uri("trellis://domain/power-systems/reliability") == ("trellis", "domain/power-systems/reliability")

    # Invalid URIs
    with pytest.raises(ValueError):
        NocturneClient.parse_nocturne_uri("invalid")
    with pytest.raises(ValueError):
        NocturneClient.parse_nocturne_uri("://missing-domain")
```

#### Test: Database Availability
```python
def test_is_available():
    """Test database availability check."""
    # With non-existent database
    client = NocturneClient("/nonexistent/path.db")
    assert client.is_available() is False

    # With existing database (mocked)
    # ... mock setup ...
    assert client.is_available() is True
```

#### Test: Query Patterns
```python
def test_query_patterns():
    """Test pattern querying with LIKE matching."""
    client = NocturneClient()

    # Query all Python patterns
    results = client.query_patterns("trellis", "patterns/python/%")
    assert isinstance(results, list)

    # Query specific pattern
    results = client.query_patterns("trellis", "patterns/python/error-handling")
    assert all("patterns/python/" in r.uri for r in results)

    # Empty results for non-existent patterns
    results = client.query_patterns("trellis", "nonexistent/%")
    assert results == []
```

#### Test: Query by Priority
```python
def test_query_by_priority():
    """Test priority-based querying."""
    client = NocturneClient()

    # Query high priority memories
    results = client.query_by_priority("trellis", max_priority=1)
    assert all(r.priority <= 1 for r in results)

    # Query normal priority memories
    results = client.query_by_priority("trellis", max_priority=2)
    assert all(r.priority <= 2 for r in results)
```

#### Test: Get Memory by URI
```python
def test_get_memory():
    """Test retrieving specific memory by URI."""
    client = NocturneClient()

    # Existing memory
    memory = client.get_memory("trellis://patterns/python/error-handling")
    assert memory is not None
    assert memory.uri == "trellis://patterns/python/error-handling"

    # Non-existent memory
    memory = client.get_memory("trellis://nonexistent")
    assert memory is None
```

### promote-to-nocturne.py

#### Test: Entry Parsing
```python
def test_parse_learnings_entries():
    """Test parsing learnings.md entries."""
    content = """
## 2026-02-17: Test Learning

**Category**: pattern

This is a test learning.

## 2026-02-16: Another Learning

**Category**: gotcha

This is another test.
"""
    entries = parse_learnings_entries(content)
    assert len(entries) == 2
    assert entries[0].title == "Test Learning"
    assert entries[0].category == "pattern"
    assert entries[1].category == "gotcha"
```

#### Test: URI Generation
```python
def test_suggested_uri():
    """Test URI generation from entry."""
    entry = MemoryEntry(
        index=1,
        date="2026-02-17",
        title="Test Pattern",
        content="Content",
        source_file="learnings.md",
        category="pattern"
    )
    assert "test-pattern" in entry.suggested_uri
    assert "patterns/project" in entry.suggested_uri
```

### sync-trellis-to-nocturne.py

#### Test: Memory Creation Parameters
```python
def test_create_memory_params():
    """Test parameter generation for memory creation."""
    entry = MemoryEntry(
        index=1,
        date="2026-02-17",
        title="Test Decision",
        content="Content",
        source_file="decisions.md"
    )
    params = create_memory_params(entry)
    assert params["priority"] == 1  # Decisions are high priority
    assert "trellis://" in params["uri"]
```

## Integration Tests

### Hook Integration

#### Test: Session Start Hook
```bash
# Test session-start.py reads Nocturne context
$ python3 .claude/hooks/session-start.py
# Verify: Output contains <nocturne> section with memories
```

#### Test: Inject Subagent Context Hook
```bash
# Test inject-subagent-context.py adds Nocturne hints
$ echo '{"tool_name": "Task", "tool_input": {"subagent_type": "implement", "prompt": "test"}}' | \
  python3 .claude/hooks/inject-subagent-context.py
# Verify: Output contains Nocturne hints section
```

### Configuration Integration

#### Test: Config File Parsing
```python
def test_config_parsing():
    """Test nocturne.yaml configuration parsing."""
    import yaml

    with open(".trellis/config/nocturne.yaml") as f:
        config = yaml.safe_load(f)

    assert config["enabled"] in (True, False)
    assert "db_path" in config
    assert "project_id" in config
    assert "auto_load_patterns" in config
    assert isinstance(config["auto_load_patterns"], list)
```

#### Test: Environment Variable Substitution
```python
def test_env_substitution():
    """Test environment variable substitution in config."""
    os.environ["NOCTURNE_DB_PATH"] = "/custom/db.db"

    client = NocturneClient()
    # If config uses ${NOCTURNE_DB_PATH}, it should be expanded
```

## Performance Tests

### Session Start Overhead

#### Test: Startup Time
```bash
# Measure session-start.py execution time
$ time python3 .claude/hooks/session-start.py > /dev/null
# Expected: < 100ms
```

#### Test: Nocturne Query Performance
```python
def test_query_performance():
    """Test Nocturne query performance."""
    import time

    client = NocturneClient()

    start = time.time()
    results = client.query_patterns("trellis", "patterns/python/%", max_results=10)
    elapsed = time.time() - start

    assert elapsed < 0.5  # Should complete in < 500ms
```

### Memory Loading

#### Test: Memory Count Impact
```python
def test_memory_loading_performance():
    """Test impact of memory count on loading."""
    import time

    client = NocturneClient()

    # Test with different result counts
    for max_results in [10, 20, 50]:
        start = time.time()
        results = client.query_patterns("trellis", "%", max_results=max_results)
        elapsed = time.time() - start

        assert elapsed < 1.0  # Should complete in < 1s regardless of count
```

## End-to-End Tests

### Full Workflow

#### Test: Complete Integration Flow
```bash
#!/bin/bash
# Test complete Nocturne integration workflow

# 1. Initialize namespace
python3 .trellis/scripts/init-nocturne-namespace.py

# 2. Verify client can connect
python3 -c "from nocturne_client import NocturneClient; c = NocturneClient(); print(c.is_available())"

# 3. Test promote script (dry-run)
echo "Test learning content" > /tmp/test_learning.txt
python3 .trellis/scripts/promote-to-nocturne.py --list

# 4. Test sync script (dry-run)
python3 .trellis/scripts/sync-trellis-to-nocturne.py --dry-run

# 5. Verify hooks work
echo '{"tool_name": "Task", "tool_input": {"subagent_type": "implement", "prompt": "test"}}' | \
  python3 .claude/hooks/inject-subagent-context.py | grep -q "Nocturne"

echo "All E2E tests passed!"
```

### Agent Integration

#### Test: Implement Agent Receives Hints
```python
def test_implement_agent_hints():
    """Test that implement agent receives Nocturne hints."""
    from inject_subagent_context import build_implement_prompt

    context = "Test context"
    nocturne_hints = "Test Nocturne hints"
    original_prompt = "Implement a feature"

    prompt = build_implement_prompt(original_prompt, context, nocturne_hints)

    assert "Nocturne" in prompt
    assert "read_memory" in prompt
    assert "search_memory" in prompt
```

#### Test: Check Agent Receives Hints
```python
def test_check_agent_hints():
    """Test that check agent receives Nocturne hints."""
    from inject_subagent_context import build_check_prompt

    context = "Test context"
    nocturne_hints = "Test Nocturne hints"
    original_prompt = "Check the code"

    prompt = build_check_prompt(original_prompt, context, nocturne_hints)

    assert "Nocturne" in prompt
    assert "verification" in prompt.lower()
```

## Test Data

### Sample Memories

```yaml
# Test data for unit tests
test_memories:
  - uri: "trellis://patterns/python/test-pattern"
    content: "Test pattern content"
    priority: 2
    disclosure: "when testing"

  - uri: "trellis://domain/power-systems/test-domain"
    content: "Test domain content"
    priority: 1
    disclosure: "when testing domain"

  - uri: "trellis://projects/researchclaw/test-project"
    content: "Test project content"
    priority: 0
    disclosure: "when testing project"
```

### Sample Memory Files

```markdown
<!-- test_learnings.md -->
## 2026-02-17: Test Learning Pattern

**Category**: pattern

This is a test learning for unit tests.

## 2026-02-16: Test Learning Gotcha

**Category**: gotcha

This is a test gotcha for unit tests.
```

```markdown
<!-- test_decisions.md -->
## 2026-02-17: Test Architecture Decision

**Context**: Test context
**Decision**: Test decision
**Rationale**: Test rationale
**Consequences**: Test consequences
```

## Test Execution

### Running Tests

```bash
# Run all tests
cd /home/hcx/github/AutoResearchClaw
python3 -m pytest .trellis/scripts/test_nocturne_client.py -v

# Run specific test category
python3 -m pytest .trellis/scripts/test_nocturne_client.py::test_query_patterns -v

# Run with coverage
python3 -m pytest .trellis/scripts/test_nocturne_client.py --cov=nocturne_client --cov-report=html
```

### Continuous Integration

```yaml
# .github/workflows/test-nocturne.yml
name: Test Nocturne Integration
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install pyyaml pytest
      - name: Run tests
        run: python3 -m pytest .trellis/scripts/test_nocturne_client.py -v
```

## Success Criteria

| Test Type | Target | Status |
|-----------|--------|--------|
| Unit Tests | > 80% coverage | Pending |
| Integration Tests | All pass | Pending |
| Performance Tests | < 100ms startup | Pending |
| End-to-End Tests | All pass | Pending |

## Known Limitations

1. **MCP Tool Testing**: Actual MCP tool calls (`create_memory`, etc.) cannot be tested in unit tests. These require integration with Claude Code.

2. **Database State**: Tests should use a temporary database or mocking to avoid affecting production data.

3. **Environment Dependencies**: Some tests depend on environment variables and file system state.

## Future Improvements

- [ ] Add mock MCP server for testing
- [ ] Add property-based testing for URI parsing
- [ ] Add load testing for concurrent queries
- [ ] Add chaos testing for error handling
