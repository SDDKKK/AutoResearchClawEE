# Nocturne Memory MCP Integration - Product Requirements Document

> **Goal**: Implement "方案 C：分层职责" - Layered architecture integrating Nocturne long-term memory with Trellis project-local memory.

---

## 1. Overview

### 1.1 Problem Statement

Current Trellis memory system (`memory/*.md`) has limitations:
- **Project-local only**: Knowledge doesn't transfer across projects
- **Flat structure**: No hierarchical organization of patterns
- **No versioning**: Changes to decisions lose history
- **Manual management**: No automated promotion of learnings

### 1.2 Solution

Integrate **Nocturne Memory MCP** as the long-term memory layer:
- **Nocturne**: Cross-project patterns, domain knowledge, tool mastery
- **Trellis memory/*.md**: Project-local decisions, active issues, ephemeral WIP
- **Trellis agents**: Can read/write Nocturne via MCP tools

### 1.3 Success Criteria

- [ ] Session start reads relevant Nocturne memories (< 100ms overhead)
- [ ] Agents can query Nocturne for patterns during implementation
- [ ] Valuable learnings can be promoted from Trellis to Nocturne
- [ ] 100% backward compatible with existing Trellis workflow
- [ ] All writes to Nocturne are versioned and reviewable

---

## 2. Requirements

### 2.1 Functional Requirements

#### FR1: Session Start Integration
- **FR1.1**: `session-start.py` reads relevant Nocturne memories
- **FR1.2**: Direct SQLite query (Hook cannot use MCP)
- **FR1.3**: Query `trellis://patterns/` for relevant patterns
- **FR1.4**: Query `trellis://projects/{id}/` for project memories
- **FR1.5**: Graceful degradation if Nocturne unavailable

#### FR2: Agent Context Injection
- **FR2.1**: `inject-subagent-context.py` adds Nocturne query hints
- **FR2.2**: Implement agent gets pattern query suggestions
- **FR2.3**: Check agent gets verification pattern suggestions
- **FR2.4**: Debug agent gets troubleshooting pattern suggestions

#### FR3: Agent MCP Integration
- **FR3.1**: Agents can call `read_memory()` via MCP
- **FR3.2**: Agents can call `search_memory()` via MCP
- **FR3.3**: Agents can call `create_memory()` for new patterns
- **FR3.4**: Agents can call `update_memory()` for existing patterns

#### FR4: URI Namespace Setup
- **FR4.1**: Create `trellis://` domain in Nocturne
- **FR4.2**: Define `trellis://patterns/` hierarchy
- **FR4.3**: Define `trellis://domain/` hierarchy
- **FR4.4**: Define `trellis://tools/` hierarchy
- **FR4.5**: Define `trellis://projects/` hierarchy

#### FR5: Knowledge Promotion
- **FR5.1**: `learnings.md` entries can be promoted to Nocturne
- **FR5.2**: `decisions.md` entries can be mirrored to Nocturne
- **FR5.3**: Promotion requires explicit user confirmation
- **FR5.4**: Promotion preserves original metadata (date, category)

### 2.2 Non-Functional Requirements

#### NFR1: Performance
- **NFR1.1**: Session start overhead < 100ms
- **NFR1.2**: MCP read operations < 500ms
- **NFR1.3**: MCP write operations < 1s

#### NFR2: Reliability
- **NFR2.1**: System works without Nocturne (graceful degradation)
- **NFR2.2**: SQLite connection failures don't crash hooks
- **NFR2.3**: MCP failures don't block agent execution

#### NFR3: Security
- **NFR3.1**: No API keys stored in Nocturne
- **NFR3.2**: No sensitive business data in Nocturne
- **NFR3.3**: All writes versioned and reviewable

#### NFR4: Maintainability
- **NFR4.1**: Clear separation between Hook (read) and Agent (write)
- **NFR4.2**: Well-documented URI namespace
- **NFR4.3**: Unit tests for SQLite client

---

## 3. Acceptance Criteria

### AC1: Session Start
```gherkin
Given Nocturne is configured and available
When a new Claude Code session starts
Then session-start.py reads relevant patterns from trellis://patterns/
And includes them in the injected context
And completes within 100ms
```

### AC2: Agent Query
```gherkin
Given an Implement Agent is executing a task
When the agent encounters a pattern it has seen before
Then it can call read_memory("trellis://patterns/...") to recall it
And use the pattern in implementation
```

### AC3: Knowledge Promotion
```gherkin
Given a learning entry exists in learnings.md
When the user confirms promotion
Then the agent creates a memory in trellis://patterns/ or trellis://domain/
With appropriate priority and disclosure
```

### AC4: Graceful Degradation
```gherkin
Given Nocturne is unavailable or misconfigured
When session starts or agent runs
Then the system continues without Nocturne
And logs a warning message
```

---

## 4. Implementation Phases

### Phase 1: Foundation (Week 1)

**Goal**: Set up infrastructure and test connectivity

#### Tasks

1. **P1-T1**: Create `nocturne_client.py` module
   - File: `.trellis/scripts/nocturne_client.py`
   - Purpose: SQLite client for reading Nocturne (Hook layer)
   - Functions:
     - `get_db_path()` - Resolve Nocturne database path
     - `query_patterns(domain, prefix)` - Query patterns by prefix
     - `query_project_memories(project_id)` - Query project memories
     - `is_available()` - Check if Nocturne is accessible

2. **P1-T2**: Create URI namespace initializer
   - File: `.trellis/scripts/init-nocturne-namespace.py`
   - Purpose: Create trellis:// domain structure in Nocturne
   - Creates:
     - `trellis://patterns/python/idioms`
     - `trellis://patterns/matlab/vectorization`
     - `trellis://domain/power-systems/reliability`
     - `trellis://tools/claude-code/slash-commands`
     - `trellis://projects/researchclaw/decisions`

3. **P1-T3**: Test connectivity
   - Verify Hook can read SQLite directly
   - Verify Agent can call MCP tools
   - Document any environment-specific issues

#### Deliverables
- [ ] `nocturne_client.py` with tests
- [ ] `init-nocturne-namespace.py` script
- [ ] Test report confirming connectivity

---

### Phase 2: Hook Integration (Week 1-2)

**Goal**: Enhance hooks to read from Nocturne

#### Tasks

1. **P2-T1**: Enhance `session-start.py`
   - Add `get_nocturne_context()` function
   - Query `trellis://patterns/` for high-priority patterns
   - Query `trellis://projects/{id}/` for project context
   - Add context under `<nocturne>` XML tag
   - Handle errors gracefully (log warning, continue)

2. **P2-T2**: Enhance `inject-subagent-context.py`
   - Add `get_nocturne_hints()` function
   - Add Nocturne query hints to implement context
   - Add Nocturne query hints to check context
   - Add Nocturne query hints to debug context

3. **P2-T3**: Configuration
   - Add `.trellis/config/nocturne.yaml`:
     ```yaml
     enabled: true
     db_path: "${NOCTURNE_DB_PATH}"
     project_id: "researchclaw"
     auto_load_patterns:
       - "trellis://patterns/python/*"
       - "trellis://domain/power-systems/*"
     ```

#### Deliverables
- [ ] Enhanced `session-start.py`
- [ ] Enhanced `inject-subagent-context.py`
- [ ] `nocturne.yaml` configuration

---

### Phase 3: Agent Integration (Week 2)

**Goal**: Enable agents to query Nocturne

#### Tasks

1. **P3-T1**: Update Implement Agent prompt template
   - Add "Long-Term Memory (Nocturne)" section
   - Document available MCP tools
   - Provide query examples
   - Add to `inject-subagent-context.py` `build_implement_prompt()`

2. **P3-T2**: Update Check Agent prompt template
   - Add Nocturne section for verification patterns
   - Document how to query for best practices
   - Add to `build_check_prompt()`

3. **P3-T3**: Update Debug Agent prompt template
   - Add Nocturne section for troubleshooting patterns
   - Document how to query for known solutions
   - Add to `build_debug_prompt()`

4. **P3-T4**: Create example memories
   - Seed `trellis://patterns/python/error-handling/result-type`
   - Seed `trellis://domain/power-systems/reliability/metrics`
   - Seed `trellis://tools/claude-code/agents/context-injection`

#### Deliverables
- [ ] Updated agent prompts with Nocturne integration
- [ ] Example memories in Nocturne
- [ ] Documentation for agents

---

### Phase 4: Write Integration (Week 3)

**Goal**: Enable knowledge promotion from Trellis to Nocturne

#### Tasks

1. **P4-T1**: Create `promote-to-nocturne.py` script
   - File: `.trellis/scripts/promote-to-nocturne.py`
   - Purpose: Promote learnings/decisions to Nocturne
   - Arguments:
     - `--source learnings.md` or `--source decisions.md`
     - `--entry "YYYY-MM-DD: Title"` (specific entry)
     - `--dry-run` (preview only)
   - Interactive confirmation before writing

2. **P4-T2**: Create slash command
   - File: `.claude/commands/trellis/promote-learning.md`
   - Purpose: Interactive command to promote current learning
   - Workflow:
     1. List recent learnings
     2. User selects entry
     3. Suggest target URI
     4. User confirms
     5. Call `create_memory()`

3. **P4-T3**: Auto-suggest promotion
   - During `add_session.py`, analyze learnings
   - Suggest which entries might be worth promoting
   - Show suggestion to user

#### Deliverables
- [ ] `promote-to-nocturne.py` script
- [ ] `/trellis:promote-learning` slash command
- [ ] Auto-suggestion in `add_session.py`

---

### Phase 5: Testing & Documentation (Week 3-4)

**Goal**: Ensure quality and document usage

#### Tasks

1. **P5-T1**: Unit tests
   - Test `nocturne_client.py` functions
   - Test Hook integration (mock SQLite)
   - Test error handling

2. **P5-T2**: Integration tests
   - End-to-end session start test
   - Agent query test
   - Knowledge promotion test

3. **P5-T3**: Documentation
   - Update `workflow.md` with Nocturne integration
   - Create `spec/nocturne-integration/usage-guide.md`
   - Document URI namespace conventions
   - Add troubleshooting section

4. **P5-T4**: Performance validation
   - Measure session start overhead
   - Measure MCP call latency
   - Verify against NFRs

#### Deliverables
- [ ] Test suite with > 80% coverage
- [ ] Updated documentation
- [ ] Performance report

---

## 5. Technical Specifications

### 5.1 Data Model

#### Nocturne SQLite Schema (Read-Only for Hooks)

```sql
-- Memories table (content storage)
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    deprecated BOOLEAN DEFAULT FALSE,
    migrated_to INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Paths table (URI to memory mapping)
CREATE TABLE paths (
    domain VARCHAR(64),
    path VARCHAR(512),
    memory_id INTEGER NOT NULL,
    priority INTEGER DEFAULT 0,
    disclosure TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (domain, path),
    FOREIGN KEY (memory_id) REFERENCES memories(id)
);
```

#### Hook Query Patterns

```python
# Query patterns by domain and prefix
SELECT p.path, p.priority, p.disclosure, m.content
FROM paths p
JOIN memories m ON p.memory_id = m.id
WHERE p.domain = 'trellis'
  AND p.path LIKE 'patterns/python/%'
  AND m.deprecated = FALSE
ORDER BY p.priority ASC

# Query project memories
SELECT p.path, m.content
FROM paths p
JOIN memories m ON p.memory_id = m.id
WHERE p.domain = 'trellis'
  AND p.path LIKE 'projects/researchclaw/%'
  AND m.deprecated = FALSE
```

### 5.2 Configuration

#### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NOCTURNE_DB_PATH` | Path to Nocturne SQLite DB | `~/.nocturne/memory.db` |
| `NOCTURNE_ENABLED` | Enable Nocturne integration | `true` |
| `NOCTURNE_PROJECT_ID` | Project identifier for trellis://projects/ | (from git) |

#### Config File (`.trellis/config/nocturne.yaml`)

```yaml
# Nocturne Memory Integration Configuration

enabled: true

# Database path (can use env var substitution)
db_path: "${NOCTURNE_DB_PATH:-~/.nocturne/memory.db}"

# Project identifier (used for trellis://projects/{id}/)
project_id: "researchclaw"

# Auto-load patterns on session start
auto_load:
  patterns:
    - domain: "trellis"
      path_prefix: "patterns/python/"
      max_results: 10
    - domain: "trellis"
      path_prefix: "domain/power-systems/"
      max_results: 5

# Priority threshold (only load priority <= threshold)
priority_threshold: 2
```

### 5.3 Error Handling

#### Hook Layer Errors

| Error | Handling |
|-------|----------|
| Database not found | Log warning, continue without Nocturne |
| Permission denied | Log warning, continue without Nocturne |
| Query timeout | Abort query, continue without results |
| Schema mismatch | Log error, disable Nocturne for session |

#### Agent Layer Errors

| Error | Handling |
|-------|----------|
| MCP not available | Continue without Nocturne query |
| read_memory fails | Log error, continue without that memory |
| create_memory fails | Report to user, suggest retry |

### 5.4 Security Considerations

1. **Database Access**: Hook only needs read access
2. **No Secrets**: Never store API keys, passwords in Nocturne
3. **Content Filtering**: Review before promoting to Nocturne
4. **Audit Trail**: All writes versioned with author info

---

## 6. Migration Strategy

### 6.1 Existing Trellis Users

1. **Phase 1**: Nocturne integration is optional
2. **Phase 2**: Users can enable via config
3. **Phase 3**: Gradually populate Nocturne with valuable patterns
4. **Phase 4**: Eventually make default (with opt-out)

### 6.2 Knowledge Migration

```
Existing learnings.md
         │
         ▼
   Review each entry
         │
    ┌────┴────┐
    ▼         ▼
 通用模式    项目特定
    │         │
    ▼         ▼
trellis://  保留在
patterns/   learnings.md
```

---

## 7. Open Questions

1. **Q**: Should we cache Nocturne queries in Trellis?
   - **Options**: No cache / Session cache / Persistent cache
   - **Consideration**: Cache invalidation vs performance

2. **Q**: How to handle Nocturne schema changes?
   - **Options**: Version check / Migration script / Graceful fallback
   - **Consideration**: Maintenance burden

3. **Q**: Should we support multiple Nocturne instances?
   - **Options**: Single / Multiple with priority / Project-specific
   - **Consideration**: Complexity vs flexibility

---

## 8. Appendix

### 8.1 Related Documents

- `architecture.md` - High-level architecture
- `usage-guide.md` - User-facing documentation (to be created)
- Nocturne Memory README - External system documentation

### 8.2 Glossary

| Term | Definition |
|------|------------|
| Nocturne | Long-term memory MCP server |
| Trellis | AI workflow framework |
| Hook | Claude Code lifecycle script |
| Agent | Task-specific AI sub-agent |
| MCP | Model Context Protocol |
| URI | Unified Resource Identifier (e.g., `trellis://patterns/python`) |
| Promotion | Moving knowledge from Trellis to Nocturne |

### 8.3 Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-17 | 0.1 | Initial PRD |
