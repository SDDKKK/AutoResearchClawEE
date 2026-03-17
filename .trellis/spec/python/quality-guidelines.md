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

## Forbidden

- Skip ruff check before commit
- Run `.py` without `uv run`
- Leave temp/debug files in repo
- 在 `/mnt/` 路径上直接运行 IO 密集脚本（先拷贝到 WSL 本地）
