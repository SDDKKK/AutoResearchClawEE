# Nocturne Memory Usage Guide for Agents

> **Purpose**: Comprehensive guide for agents using Nocturne long-term memory

## Overview

Nocturne is the long-term memory layer that stores cross-project patterns, domain knowledge, and tool mastery. This guide helps agents understand when and how to query Nocturne effectively.

## When to Query Nocturne

### Implement Agent

**Before starting implementation:**
1. Query `trellis://patterns/python/` for language-specific patterns
2. Query `trellis://domain/power-systems/` for domain knowledge
3. Query `trellis://tools/claude-code/` for tool usage tips

**During implementation:**
- Need error handling patterns? Query `trellis://patterns/python/error-handling`
- Working with data processing? Query `trellis://patterns/python/data-processing`
- Unsure about testing patterns? Query `trellis://patterns/python/testing`

**After implementation:**
- Check if your implementation follows established conventions
- Verify cross-layer data formats match documented patterns

### Check Agent

**Before code review:**
1. Query `trellis://patterns/python/` for verification criteria
2. Query `trellis://patterns/python/quality` for quality guidelines
3. Query `trellis://domain/power-systems/` for domain-specific rules

**During code review:**
- Checking code style? Query `trellis://patterns/python/code-style`
- Checking error handling? Query `trellis://patterns/python/error-handling`
- Checking cross-layer issues? Query `trellis://domain/power-systems/` for data format rules

**After code review:**
- Document any new patterns discovered
- Note deviations from established conventions with justifications

### Debug Agent

**Initial diagnosis:**
1. Query `trellis://projects/researchclaw/known-issues` for active issues
2. Query `trellis://patterns/python/error-handling` for error patterns
3. Query `trellis://tools/claude-code/debugging` for debugging tips

**Deep investigation:**
- Specific error type? Query `trellis://patterns/python/error-handling/<type>`
- Cross-layer data issue? Query `trellis://domain/power-systems/data-formats`
- Tool usage problem? Query `trellis://tools/claude-code/<tool>`

**After fixing:**
- Verify the fix follows established patterns
- Consider if the issue should be added to known-issues

## How to Query

### read_memory(uri)

Use for specific, known patterns when you know the exact URI.

**When to use:**
- You know the exact pattern name
- You're looking for a specific convention
- You need detailed content of a known pattern

**Examples:**
```python
# Read Python error handling patterns
read_memory("trellis://patterns/python/error-handling")

# Read specific error handling pattern
read_memory("trellis://patterns/python/error-handling/result-type")

# Read domain knowledge
read_memory("trellis://domain/power-systems/reliability/metrics")

# Read project-specific decisions
read_memory("trellis://projects/researchclaw/decisions")
```

**Return value:**
- Memory content as string if found
- None if not found

### search_memory(query, domain="trellis")

Use for discovering relevant patterns when you don't know the exact URI.

**When to use:**
- You're exploring available patterns
- You need to find patterns related to a topic
- You want to discover best practices

**Examples:**
```python
# Search for polars-related patterns
search_memory("polars dataframe", domain="trellis")

# Search for code quality patterns
search_memory("ruff type annotations", domain="trellis")

# Search for MATLAB patterns
search_memory("MATLAB vectorization", domain="trellis")

# Search for cross-layer patterns
search_memory("cross-layer validation", domain="trellis")
```

**Return value:**
- List of matching memory URIs and summaries
- Empty list if no matches

## URI Namespace Quick Reference

### Patterns

```
trellis://patterns/python/
├── idioms/              # Python idioms and best practices
├── error-handling/      # Error handling patterns
├── data-processing/     # Data processing patterns (polars, pandas)
├── testing/             # Testing patterns
├── performance/         # Performance optimization
└── quality/             # Code quality guidelines

trellis://patterns/matlab/
├── vectorization/       # Vectorization patterns
└── translation/         # MATLAB to Python migration
```

### Domain Knowledge

```
trellis://domain/power-systems/
├── reliability/         # Reliability calculation
├── topology/            # Grid topology analysis
├── load-flow/           # Load flow calculation
└── data-formats/        # Data format conventions
```

### Tools

```
trellis://tools/claude-code/
├── slash-commands/      # Slash command usage
├── hooks/               # Hook development
├── agents/              # Agent development
└── debugging/           # Debugging tips

trellis://tools/mcp/
├── tool-design/         # MCP tool design
└── error-handling/      # MCP error handling
```

### Project-Specific

```
trellis://projects/researchclaw/
├── decisions/           # Architecture decisions
├── learnings/           # Project learnings
└── known-issues/        # Known issues and workarounds
```

## Query Patterns by Task Type

### Python Development Tasks

**Before coding:**
```python
read_memory("trellis://patterns/python/code-style")
read_memory("trellis://patterns/python/idioms")
```

**Error handling:**
```python
read_memory("trellis://patterns/python/error-handling")
search_memory("exception handling", domain="trellis")
```

**Data processing:**
```python
read_memory("trellis://patterns/python/data-processing")
search_memory("polars best practices", domain="trellis")
```

### MATLAB Development Tasks

**Before coding:**
```python
read_memory("trellis://patterns/matlab/vectorization")
```

**Code style:**
```python
search_memory("MATLAB checkcode", domain="trellis")
```

### Cross-Layer Tasks

**Data formats:**
```python
read_memory("trellis://domain/power-systems/data-formats")
```

**Validation:**
```python
search_memory("cross-layer validation", domain="trellis")
```

### Debugging Tasks

**Known issues:**
```python
read_memory("trellis://projects/researchclaw/known-issues")
search_memory("workaround", domain="trellis")
```

**Error patterns:**
```python
read_memory("trellis://patterns/python/error-handling")
```

## Best Practices

### Do

1. **Query before implementing** - Check if patterns exist before reinventing
2. **Be specific in searches** - Use specific terms for better results
3. **Read related patterns** - One pattern often references others
4. **Apply patterns appropriately** - Adapt patterns to your specific context
5. **Document deviations** - If you deviate from a pattern, document why

### Don't

1. **Don't query for every small task** - Use Nocturne for patterns, not syntax
2. **Don't blindly follow patterns** - Understand the rationale first
3. **Don't ignore context** - Patterns are context-dependent
4. **Don't forget to verify** - After applying a pattern, verify it works

## Examples

### Example 1: Implementing Error Handling

```python
# 1. Query for error handling patterns
patterns = read_memory("trellis://patterns/python/error-handling")

# 2. Read specific pattern if available
result_type = read_memory("trellis://patterns/python/error-handling/result-type")

# 3. Apply the pattern in your implementation
def my_function() -> ResultType:
    # Implementation following the pattern
    pass
```

### Example 2: Reviewing Cross-Layer Code

```python
# 1. Query for cross-layer validation rules
rules = read_memory("trellis://domain/power-systems/data-formats")

# 2. Search for related patterns
patterns = search_memory("cross-layer", domain="trellis")

# 3. Verify code against patterns
# - Check data format conversions
# - Verify index conventions (0-based vs 1-based)
# - Validate file path handling
```

### Example 3: Debugging a Data Issue

```python
# 1. Query known issues
known_issues = read_memory("trellis://projects/researchclaw/known-issues")

# 2. Search for similar issues
similar = search_memory("data format error", domain="trellis")

# 3. Query error handling patterns
error_patterns = read_memory("trellis://patterns/python/error-handling")

# 4. Apply the fix following established patterns
```

## Troubleshooting Queries

### Query Returns None

- Check the URI format: `domain://path` (e.g., `trellis://patterns/python`)
- Try a broader search with `search_memory()`
- The memory may not exist yet

### Search Returns Empty

- Try different keywords
- Use more general terms
- Check if the domain is correct

### Pattern Doesn't Apply

- Patterns are guidelines, not rules
- Document why you're deviating
- Consider if the pattern needs updating

## Integration with Workflow

### Implement Agent Workflow

1. Receive task
2. **Query Nocturne** for relevant patterns
3. Understand requirements and patterns
4. Implement following patterns
5. Self-check against patterns
6. Report completion

### Check Agent Workflow

1. Receive task
2. Get code changes
3. **Query Nocturne** for verification patterns
4. Check code against patterns
5. Fix issues or document deviations
6. Run verification

### Debug Agent Workflow

1. Receive task with issues
2. **Query Nocturne** for known issues and patterns
3. Analyze issues
4. Fix following patterns
5. Verify fixes
6. Report resolution

## Summary

Nocturne is your long-term memory for:
- **Patterns**: Reusable solutions to common problems
- **Domain knowledge**: Power systems expertise
- **Tool mastery**: Claude Code and MCP best practices
- **Project context**: Decisions, learnings, and known issues

Query Nocturne when you need:
- Guidance on how to implement something
- Verification criteria for code review
- Solutions to debugging problems
- Context about project decisions

Remember: Nocturne complements your existing knowledge. Use it to enhance your work, not replace your judgment.
