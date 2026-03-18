# Python Quality Guidelines

## Execution Environment

All `.py` files must be run via `uv`:

```bash
uv run src/main.py
uv run scripts/analysis/some_script.py
```

## Lint & Format

Must pass before commit:

```bash
# Lint check
uv run ruff check .

# Format check
uv run ruff format --check .

# Auto-fix
uv run ruff check --fix .
uv run ruff format .
```

## Testing

```bash
uv run pytest tests/
uv run pytest tests/ -v --tb=short
```

## Temporary Scripts

- Prefer inline execution, avoid creating temp files:

```bash
uv run python -c "
import polars as pl
df = pl.read_csv('data/input.csv')
print(df.describe())
"
```

- If temp file is unavoidable: `rm -f` after use

## Pre-Commit Checklist

- [ ] `uv run ruff check .` passes
- [ ] `uv run ruff format --check .` passes
- [ ] Manual testing of changed functionality
- [ ] No new pandas usage in data logic (use polars)

## WSL 环境注意事项

本项目运行在 WSL 中，数据文件位于 `/mnt/e/`（Windows 挂载盘）。

### IO 性能

`/mnt/` 路径的磁盘 IO 比 WSL 本地文件系统慢 **5-20 倍**。
对于 IO 密集操作，建议先拷贝到 WSL 本地：

```bash
# 大文件批量读写（CSV/Excel 批处理）
cp data/input.csv /tmp/ && uv run python scripts/process.py /tmp/input.csv
```

### 适用判断

| 场景 | 方案 |
|------|------|
| 大文件批量读写（CSV/Excel） | 先 cp 到 `/tmp/` |
| 小文件常规读写 | 直接在 `/mnt/` 路径操作即可 |

## Security - Git History Cleanup

### Problem

Sensitive data (API keys, passwords) accidentally committed to git history remains accessible even after deletion:

```bash
# ❌ Wrong - file still in history
rm config.yaml
git commit -m "Remove config"

# ❌ Wrong - file still in history
git rm config.yaml
git commit -m "Remove config"
```

### Solution

Use `git filter-branch` to remove from ALL history:

```bash
# 1. Remove file from all commits
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch config.yaml' \
  --prune-empty --tag-name-filter cat -- --all

# 2. Clean internal references
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 3. Force push (⚠️ rewrites history)
git push origin main --force

# 4. ⚠️ ROTATE COMPROMISED KEYS IMMEDIATELY
```

### Prevention

**Before first commit**:

```bash
# Add to .gitignore
echo "config.*.yaml" >> .gitignore
echo "*.local.yaml" >> .gitignore
git add .gitignore
git commit -m "chore: ignore sensitive config files"
```

**Provide example configs**:

```bash
# Create template
cp config.yaml config.example.yaml
# Remove sensitive data
sed -i 's/api_key:.*/api_key: "YOUR_API_KEY_HERE"/' config.example.yaml
git add config.example.yaml
```

### Detection

Check if sensitive files are tracked:

```bash
# List all tracked files
git ls-files | grep -E "config.*\.yaml|.*key.*\.pem"

# Search history for sensitive patterns
git log --all --full-history -- "*config*.yaml"
git log -p | grep -i "api.*key\|password"
```

### When to Use

- API keys committed (rotate immediately!)
- Database credentials exposed
- Private keys pushed to public repo
- Passwords in config files

**⚠️ Critical**: After `filter-branch`, ALL collaborators must re-clone. Old clones still have sensitive data in reflog.

---

## Forbidden

- Skip ruff check before commit
- Run `.py` without `uv run`
- Leave temp/debug files in repo
- 在 `/mnt/` 路径上直接运行 IO 密集脚本（先拷贝到 WSL 本地）
- Commit sensitive files (use `.gitignore` + example templates)
