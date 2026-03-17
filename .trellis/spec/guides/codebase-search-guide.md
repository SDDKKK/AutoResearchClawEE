# Codebase Search Guide

> **Purpose**: Use the right tool for code search - semantic search vs exact match.

---

## The Problem

**Using the wrong search tool wastes time and misses relevant code.**

When you use grep/rg for semantic questions like "where is authentication handled?":
- You only find exact keyword matches
- You miss relevant code with different naming
- You need to try multiple search terms
- You still might miss the right location

**Augment Context Engine** solves this with semantic search powered by AI embeddings.

---

## Tool Selection Decision Tree

```
Need to find code?
│
├─ Do you know the EXACT identifier? (class name, function name, variable)
│  │
│  ├─ Yes → Use Grep tool
│  │    Example: grep -r "class ResearchPipeline" src/
│  │
│  └─ No, but know what it DOES → Use warpgrep (preferred) or codebase-retrieval (fallback)
│       Example: "Where is pipeline orchestration logic?"
│
└─ Need to understand how a feature works?
   │
   └─ Use warpgrep (preferred) or codebase-retrieval (fallback)
      Example: "How does the system handle outage event data?"
```

---

## Tool Overview

| Tool | Type | Best For | Fallback |
|------|------|----------|----------|
| **warpgrep** | Semantic | Broad code search, multi-turn parallel exploration | codebase-retrieval |
| **codebase-retrieval** | Semantic | Deep code understanding, complex relationships | Grep + Read |
| **Grep** | Exact | Finding exact identifiers, references | — |
| **Read** | Direct | Single file access when path known | — |

**Default priority for semantic search**: warpgrep → codebase-retrieval → manual search

---

## When to Use warpgrep (Preferred)

Use `mcp__morph-mcp__warpgrep_codebase_search` for:

### ✅ Good Use Cases

| Scenario | Example Query |
|----------|---------------|
| **Don't know file location** | "Where is the literature search implemented?" |
| **Broad exploration** | "What code handles configuration loading?" |
| **Multi-turn parallel search** | Complex queries requiring multiple exploration steps |
| **Large codebase** | When you need to search across many files efficiently |

### ❌ Bad Use Cases

| Scenario | Use Instead |
|----------|-------------|
| Deep code understanding | codebase-retrieval |
| Exact identifier search | Grep |
| Single file reading | Read |

---

## When to Use codebase-retrieval (Fallback)

Use `mcp__augment-context-engine__codebase-retrieval` when:

1. **warpgrep is unavailable** (MCP not connected)
2. **Need deep semantic understanding** of complex code relationships
3. **Cross-file logic analysis** requiring high-level context

### ✅ Good Use Cases

| Scenario | Example Query |
|----------|---------------|
| **Don't know file location** | "Where is the literature search implemented?" |
| **Understand feature** | "How does the system orchestrate research stages?" |
| **Find related code** | "What code handles configuration loading?" |
| **High-level exploration** | "What tests exist for the LLM client?" |
| **Cross-file logic** | "How is data passed between Python and MATLAB?" |

### ❌ Bad Use Cases (Use Grep instead)

| Scenario | Use Grep Instead |
|----------|------------------|
| Find definition of known class | `grep -r "class ResearchPipeline"` |
| Find all references to function | `grep -r "search_papers"` |
| Find config value | `grep -r "API_KEY"` |
| Find import statement | `grep -r "from researchclaw import"` |

---

## How to Use warpgrep (Preferred)

### Basic Usage

The tool is available in Claude Code's system:

```python
# AI calls this internally via MCP
warpgrep(
    information_request="Your natural language question",
    directory_path="/absolute/path/to/project"  # Usually project root
)
```

**You don't call this directly** - just ask the AI questions and it will use the tool automatically.

### Query Patterns

**Good queries** are specific and describe what the code does:

```
✅ "Where is the function that searches academic papers?"
✅ "What files handle pipeline stage registration?"
✅ "How is the LLM response parsed into structured output?"
✅ "Where are the quality scoring functions defined?"
```

**Bad queries** are too vague or ask for exact matches:

```
❌ "Find search_papers"  (use grep for this)
❌ "Show me code"  (too vague)
❌ "All database code"  (too broad)
```

---

## Integration with This Project

### Python Code Search

For ResearchClaw Python codebase (`researchclaw/`):

| What You Need | How to Ask |
|---------------|------------|
| Find pipeline logic | "Where is pipeline orchestration implemented?" |
| Find agent logic | "How does the code agent work?" |
| Find literature search | "Where is literature search implemented?" |
| Find LLM integration | "How does the LLM client work?" |

### MATLAB Code Search

For MATLAB codebase (`MATLAB/`):

| What You Need | How to Ask |
|---------------|------------|
| Find search logic | "Where is the literature search algorithm?" |
| Find pipeline flow | "How does the pipeline chain stages?" |
| Find report generation | "Where is report generation implemented?" |
| Find export logic | "How are research artifacts exported?" |

---

## Comparison: warpgrep vs codebase-retrieval vs Grep vs Read

| Task | Best Tool | Reason |
|------|-----------|--------|
| "Find where papers are searched" | **warpgrep** (preferred) or **codebase-retrieval** (fallback) | Semantic - finds logic even with different names |
| "Find all uses of `search_papers()`" | **Grep** | Exact match - need all references |
| "Understand `pipeline.py` module" | **Read** then ask AI | Direct file access |
| "How does Python call MATLAB?" | **warpgrep** (preferred) or **codebase-retrieval** (fallback) | Cross-file, high-level understanding |
| "Find config value `API_BASE_URL`" | **Grep** | Exact string match |
| "Explore large codebase structure" | **warpgrep** | Multi-turn parallel search |

**Fallback Strategy**: If warpgrep MCP is unavailable, use codebase-retrieval for semantic search. If codebase-retrieval is also unavailable, use Grep + Read manually.

---

## Performance Tips

### 1. Be Specific in Queries

```
❌ Vague:    "database code"
✅ Specific: "Where is the pipeline configuration defined?"
```

### 2. Describe Functionality, Not Names

```
❌ Name-based: "Find ResearchPipeline class"  (use Grep)
✅ Functional:  "Where are reliability metrics calculated?"
```

### 3. Use for Cross-Cutting Concerns

```
✅ "How does error handling work across pipeline stages?"
✅ "What's the data flow from LLM output to report?"
```

---

## When NOT to Use codebase-retrieval

### Case 1: Exact Identifier Known

If you know the exact name, use Grep:

```bash
# Faster and more accurate for exact matches
grep -r "class ResearchPipeline" src/
grep -r "def search_papers" src/
```

### Case 2: File Already Known

If you know the file, just read it:

```bash
# Direct file access is faster
cat src/core/pipeline.py
```

### Case 3: Pattern Matching

For regex patterns, use Grep:

```bash
# Find all functions starting with "export_"
grep -r "def export_" src/
```

---

## Real Project Examples

### Example 1: Understanding Literature Search Flow

**Question**: "How does the system search for papers?"

**What codebase-retrieval finds**:
- Literature search modules (`arxiv_client.py`, `semantic_scholar.py`)
- Search orchestration in `search.py`
- Cache storage of search results

**Alternative with Grep** (less effective):
- You'd need to try: `arxiv`, `semantic scholar`, `paper search`
- Might miss relevant code with different naming

### Example 2: Finding Config Schema

**Question**: "Where is the config schema defined?"

**What codebase-retrieval finds**:
- Config definition in `researchclaw/config.py`
- YAML loading logic
- Validation logic

**Using Grep** (also good for this):
```bash
grep -r "class.*Config" src/
```

### Example 3: Pipeline Data Flow

**Question**: "How does data flow between pipeline stages?"

**What codebase-retrieval finds**:
- Stage input/output contracts
- JSON serialization between stages
- Artifact export (PDF, Markdown)

**Using Grep** (harder):
- Would need multiple searches: `StageResult`, `pipeline`, `artifacts`

---

## Common Mistakes

### Mistake 1: Using for Exact Matches

```
❌ codebase-retrieval: "Find function search_papers"
✅ Grep: grep -r "def search_papers" src/
```

### Mistake 2: Too Broad Queries

```
❌ "Show me all Python code"
✅ "Where is search ranking calculated in the literature module?"
```

### Mistake 3: Not Following Up

```
✅ codebase-retrieval → Read suggested files → Grep for references
```

---

## Integration with Development Workflow

### During Task Research Phase

```
1. Use codebase-retrieval to understand feature area
   "How does the system currently handle reliability indices?"

2. Read suggested files

3. Use Grep to find all references
   grep -r "search_papers" src/

4. Start implementation
```

### During Bug Investigation

```
1. Use codebase-retrieval for high-level understanding
   "Where is LLM API error handling?"

2. Read relevant files

3. Use Grep for specific error messages
   grep -r "LLMClientError" src/
```

---

## Summary: Quick Decision Guide

**Ask yourself**: "Do I know the exact identifier?"

| Condition | Primary Tool | Fallback |
|-----------|-------------|----------|
| **Don't know exact identifier** | warpgrep (preferred) | codebase-retrieval |
| **Need deep understanding** | codebase-retrieval | Grep + Read |
| **Know exact identifier** | Grep | — |
| **File path known** | Read | — |

**Default priority for semantic search**: warpgrep → codebase-retrieval → manual search

---

## Core Principle

> **Use warpgrep for broad semantic exploration (preferred).**
>
> **Use codebase-retrieval for deep understanding (fallback).**
>
> **Use exact search (Grep) for finding references.**
>
> **Use direct access (Read) when you know the file.**
>
> **If warpgrep MCP unavailable, codebase-retrieval covers all semantic search needs.**

