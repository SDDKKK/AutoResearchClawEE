# MATLAB Development Guidelines

> Conventions for MATLAB development in ResearchClaw project.

## Overview

MATLAB scripts handle numerical computation, optimization modeling, and data analysis. Located under `MATLAB/` (to be created when needed).

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Code Style](./code-style.md) | checkcode, naming, execution | Active |
| [Quality Guidelines](./quality-guidelines.md) | checkcode L1-L5 validation | Active |
| [Docstring](./docstring.md) | MATLAB % docstring format | Active |
| [Scientific Computing](./scientific-computing.md) | Matrix ops, plotting, data I/O, performance | Active |

## Quick Rules

1. **Validate**: `matlab -batch "checkcode('filename.m')"` must pass (no L1/L2 errors)
2. **Execute**: `matlab -nodesktop -nosplash -batch "run('filename.m'); exit"`
3. **Comments**: No decorative lines, use `%` block headers with blank lines
4. **Data exchange**: CSV/Excel for Python↔MATLAB, `.mat` for internal state
