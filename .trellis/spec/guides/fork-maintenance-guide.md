# Fork Maintenance Guide

> **Purpose**: When maintaining a fork with custom modifications, how to integrate upstream updates while preserving your changes.

---

## When to Use This Guide

- [ ] You forked a repo and made custom modifications
- [ ] Upstream has new commits you want to incorporate
- [ ] You need to preserve your custom features
- [ ] Git shows: "Your branch is X commits ahead, Y commits behind upstream"

---

## Strategy Selection

| Strategy | Effort | Risk | History | Future Maintenance |
|----------|--------|------|---------|-------------------|
| **A: Fresh Clone** | 10-15h | High (易遗漏) | Clean | Easy |
| **B: Continue Merge** | 8-12h | Medium | Complex | Hard |
| **C: Hybrid** | 7-12h | Medium (可控) | Clean | Easy ✅ |

**Recommendation**: **Strategy C (Hybrid)** for most cases

---

## Strategy C: Hybrid (Upstream-First + Cherry-Pick)

### Core Principle

> **Upstream-First**: Start from latest upstream, then add your customizations incrementally.

This preserves upstream's architectural improvements while maintaining your features.

### Process

#### 1. Prepare

```bash
# Ensure upstream is configured
git remote -v
# origin    git@github.com:YOU/fork.git (fetch)
# upstream  git@github.com:ORIGINAL/repo.git (fetch)

# Fetch latest
git fetch upstream

# Create integration branch from upstream
git checkout -b strategy-c-integration upstream/main
```

#### 2. Identify Your Custom Commits

```bash
# List commits unique to your fork
git log upstream/main..HEAD --oneline --no-merges

# Example output:
# e8c556b feat: add power systems support
# 8ccf746 fix: correct IEEE BibTeX classification
# 12b0edb feat: add domain-specific templates
```

#### 3. Cherry-Pick in Dependency Order

```bash
# Cherry-pick one by one
git cherry-pick e8c556b

# If conflicts occur:
# 1. Resolve manually
# 2. Test: pytest tests/
# 3. Stage: git add <files>
# 4. Continue: git cherry-pick --continue
```

**⚠️ Important**: Test after EACH commit, not just at the end.

#### 4. Handle Conflicts

When both upstream and your fork modified the same file:

**Approach A: Merge Both**
```bash
# Accept upstream version as base
git checkout --theirs researchclaw/executor.py

# Manually add your features back
# Edit file...
git add researchclaw/executor.py
git cherry-pick --continue
```

**Approach B: Upstream-First (Recommended)**
```python
# For complex files (e.g., executor.py):
# 1. Use upstream version as base (preserves their architecture)
# 2. Add your features incrementally:

# Upstream version has:
def _detect_domain(topic: str) -> str:
    # ... 7 domains ...

# Your version added:
_DOMAIN_KEYWORDS["power_systems"] = (
    ["power systems", "smart grid", ...],
    "power systems engineering",
    "IEEE Transactions on Power Systems"
)

# Merge: Add your domain to upstream's structure
```

#### 5. Test

```bash
# Run tests after each commit
pytest tests/ -v

# If failures:
# 1. Check if test expectations changed
# 2. Update tests if needed
# 3. Re-run to verify
```

#### 6. Push

```bash
# Push to your fork
git checkout main
git reset --hard strategy-c-integration
git push origin main --force-with-lease

# Clean up
git branch -d strategy-c-integration
```

---

## Conflict Resolution Patterns

### Pattern 1: Both Added to Same List

```python
# Upstream added:
_JOURNAL_KEYWORDS = ("transactions", "journal")

# Your fork added:
_JOURNAL_KEYWORDS = ("transactions", "journal", "power systems", "smart grid")

# Merge:
_JOURNAL_KEYWORDS = (
    "transactions", "journal",
    # Upstream new additions:
    "emnlp", "naacl", "eccv",
    # Your additions:
    "power systems", "smart grid", "ieee",
)
```

### Pattern 2: Function Signature Changed

```python
# Upstream changed signature:
def chat(self, messages, model=None, max_tokens=4096):
    # New implementation...

# Your fork had:
def chat(self, messages, model=None):
    # Provider pool rotation logic...

# Merge:
def chat(self, messages, model=None, max_tokens=4096):
    # Provider pool rotation (your logic)
    pool = self._build_pool(model)

    for name, base_url, api_key, m in pool:
        try:
            # Upstream's new implementation
            resp = self._call_with_retry(m, messages, max_tokens)
            return resp
        except HTTPError as e:
            if e.code == 429:
                continue  # Your rotation logic
```

### Pattern 3: Architectural Refactor

```python
# Upstream refactored executor.py:
# - Extracted domain detection to separate module
# - Added MetaClaw integration
# - Changed stage execution flow

# Your fork had:
# - Power systems fallback logic in executor.py
# - JSON type guards
# - Domain-specific prompts

# Solution: Upstream-First
# 1. Accept upstream's new structure
# 2. Add your features to new locations:
#    - Power systems domain → _DOMAIN_KEYWORDS
#    - JSON guards → _safe_json_loads()
#    - Domain prompts → Separate prompt file
```

---

## Decision Tree: When to Use Upstream-First

```
Did upstream refactor the file?
├─ YES → Use Upstream-First
│   ├─ Accept upstream's architecture
│   └─ Add your features incrementally
│
└─ NO → Merge Both
    ├─ Keep both changes
    └─ Manually resolve conflicts
```

**Rule of Thumb**: If upstream's version has significantly different structure (new classes, renamed functions, extracted modules), use Upstream-First.

---

## Post-Merge Checklist

- [ ] All custom features still present
- [ ] All tests passing
- [ ] No regression in custom functionality
- [ ] Config files intact
- [ ] Documentation updated (if needed)
- [ ] `.gitignore` preserves sensitive files

---

## Common Mistakes

### ❌ Mistake 1: Cherry-Pick All at Once

```bash
# DON'T: Cherry-pick all commits, resolve conflicts at the end
git cherry-pick commit1 commit2 commit3 ... commitN
# → Complex conflicts, hard to debug which commit broke what
```

**Instead**:
```bash
# DO: Cherry-pick one by one, test after each
git cherry-pick commit1
pytest tests/
git cherry-pick commit2
pytest tests/
```

### ❌ Mistake 2: Blindly Accept Your Version

```bash
# DON'T: Always keep your changes
git checkout --ours executor.py
# → Loses upstream's improvements
```

**Instead**:
```bash
# DO: Review upstream changes first
git diff HEAD...upstream/main -- executor.py
# Then decide: merge, upstream-first, or hybrid
```

### ❌ Mistake 3: Skip Testing

```bash
# DON'T: Assume "it should work"
git cherry-pick commit1 commit2 commit3
git push  # Without testing
```

**Instead**:
```bash
# DO: Test after each commit
for commit in commit1 commit2 commit3; do
    git cherry-pick $commit
    pytest tests/ || exit 1
done
```

---

## Future Maintenance

### Sync Frequency

- **Small upstream releases** (v0.3.0 → v0.3.1): Sync every 2-3 months
- **Major upstream releases** (v0.3.0 → v0.4.0): Sync within 1 month
- **Critical security fixes**: Sync immediately

### Reducing Future Conflicts

1. **Isolate customizations**:
   ```python
   # Instead of modifying executor.py directly:
   # Create researchclaw/extensions/power_systems.py
   # Import in executor.py
   ```

2. **Use feature flags**:
   ```python
   if config.enable_power_systems_domain:
       from researchclaw.extensions.power_systems import add_power_systems_domain
       add_power_systems_domain(_DOMAIN_KEYWORDS)
   ```

3. **Contribute to upstream**:
   - Generic features (domain detection) → Submit PR
   - Project-specific features → Keep in fork

---

## Quick Reference

```bash
# 1. Create integration branch
git checkout -b integration upstream/main

# 2. Cherry-pick custom commits (one by one!)
git cherry-pick <commit-sha>
pytest tests/

# 3. Resolve conflicts (upstream-first for complex files)
git checkout --theirs <file>  # Use upstream as base
# Edit to add your features...
git add <file>

# 4. Push to fork
git checkout main
git reset --hard integration
git push origin main --force-with-lease
```

---

## Related Guides

- [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md) - When fork has multi-language components
- [Git Security](../python/quality-guidelines.md#security---git-history-cleanup) - Handling sensitive data
- [Verification Before Completion](./verification-before-completion.md) - Testing checklist

---

## Core Principle

> **Upstream-First preserves architectural evolution while maintaining your value-add.**
>
> Don't fight upstream's improvements—adapt your features to their new structure.
