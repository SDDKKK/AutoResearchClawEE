# Learnings

This file tracks insights from development sessions. Review these when updating specs.

---

## 2026-03-18: Upstream Merge Strategy

**Context**: Merged upstream v0.3.0+ (112 commits) into EE fork while preserving customizations

**Key Insights**:

### 1. Strategy C (Hybrid Merge) is Most Effective

**Problem**: Fork diverged significantly from upstream (10 ahead, 112 behind)

**Solutions Tried**:
- Strategy A: Fresh clone + re-apply modifications (10-15h, high risk of missing features)
- Strategy B: Continue merging (8-12h, complex history)
- Strategy C: Upstream-First + Cherry-pick EE commits (7-12h, clean history) ✅

**Decision**: Strategy C proved optimal
- Creates clean history based on latest upstream
- Each EE commit is verified individually
- Future merges are easier (no accumulated debt)

**Implementation**:
```bash
# 1. Create branch from latest upstream
git checkout -b strategy-c-integration upstream/main

# 2. Cherry-pick EE commits in dependency order
git cherry-pick <commit-1>
git cherry-pick <commit-2>
# ...

# 3. Resolve conflicts toward EE direction
# 4. Test after each commit
```

**Critical Learning**: When both EE and upstream modify the same file (e.g., `executor.py`), use **Upstream-First**:
1. Start with upstream version as base
2. Add EE features incrementally
3. Preserves upstream's architectural improvements

---

### 2. Git History Security - Removing Sensitive Files

**Problem**: API key accidentally committed to git history

**Wrong Approach**:
- Just delete file and commit (still in history!)
- `git rm` (still in history!)

**Correct Approach**:
```bash
# 1. Remove from ALL history
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch config.power_systems.yaml' \
  --prune-empty --tag-name-filter cat -- --all

# 2. Clean up internal references
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 3. Force push cleaned history
git push origin main --force

# 4. Rotate compromised keys immediately!
```

**Prevention**:
- Add sensitive files to `.gitignore` BEFORE first commit
- Use `.gitignore` patterns: `config.*.yaml`, `*.local.yaml`
- Provide example files: `config.example.yaml`

---

### 3. Provider Pool Pattern - Multi-Provider Resilience

**Context**: LLM APIs have rate limits (429 errors) and transient failures

**Pattern**:
```python
# Build pool at init
def __init__(self, config):
    self._pool = []
    self._pool_index = 0

    if config.provider_pool:
        for p in config.provider_pool:
            for m in p.models:
                self._pool.append((p.name, p.base_url, p.api_key, m))

    # Fallback to single provider
    if not self._pool:
        self._pool = [("default", config.base_url, config.api_key, config.primary_model)]

# Round-robin with retry
def chat(self, messages, model=None):
    pool = [filter pool if model specified]

    for i in range(len(pool)):
        idx = (self._pool_index + i) % len(pool)
        name, base_url, api_key, m = pool[idx]

        try:
            resp = self._call_with_retry(m, messages, base_url=base_url, api_key=api_key)
            self._pool_index = idx  # Sticky on success
            return resp
        except HTTPError as e:
            if e.code == 429 and i < len(pool) - 1:
                continue  # Rotate to next provider
            raise
        except OSError as e:
            if e.errno in _TRANSIENT_ERRNOS and i < len(pool) - 1:
                continue  # Retry with next
            raise
```

**Key Properties**:
- Backward compatible (empty pool → single provider)
- Sticky rotation (remembers last successful provider)
- Handles rate limits (429) and connection errors
- Config-driven (no code changes to add providers)

**Configuration**:
```yaml
llm:
  provider_pool:
    - name: "openai-main"
      base_url: "https://api.openai.com/v1"
      api_key: "${OPENAI_API_KEY}"
      models: ["gpt-4o", "gpt-4o-mini"]
    - name: "openrouter"
      base_url: "https://openrouter.ai/api/v1"
      api_key: "${OPENROUTER_API_KEY}"
      models: ["anthropic/claude-sonnet-4"]
```

---

## When to Promote to Spec

- **Upstream merge strategy**: → Create `guides/fork-maintenance-guide.md`
- **Git security**: → Update `python/quality-guidelines.md` with security section
- **Provider pool**: → Document in architecture or client spec

---

## Tags

`upstream-merge` `fork-workflow` `git-security` `provider-pool` `llm-resilience`
