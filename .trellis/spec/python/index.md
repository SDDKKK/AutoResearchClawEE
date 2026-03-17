# Python Development Guidelines

> Conventions for Python development in ResearchClaw project.

## Overview

This project is an **autonomous research pipeline** (自主学术研究管线). Python >=3.11, managed by `uv`, validated by `ruff`. Core modules: `researchclaw/` (pipeline, agents, literature, llm, writing), `tests/`.

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Code Style](./code-style.md) | ruff, typing, concise architecture | Active |
| [Data Processing](./data-processing.md) | polars > pandas, file I/O | Active |
| [Quality Guidelines](./quality-guidelines.md) | ruff check, uv run, pytest | Active |
| [Docstring](./docstring.md) | 输入/输出 format, comment rules | Active |
| [Scientific Visualization](./scientific-visualization.md) | matplotlib/seaborn, publication-quality figures | Active |
| [MarkItDown](./markitdown.md) | PDF/DOCX/XLSX → Markdown conversion | Active |

## Quick Rules

1. **Run**: Always use `uv run` for any `.py` execution
2. **Lint**: `uv run ruff check .` must pass before commit
3. **Data**: polars for all data logic, pandas only for legacy compatibility
4. **Style**: Concise, no redundancy, no deep try-except nesting
5. **Comments**: No decorative lines, docstring for functions/classes only
