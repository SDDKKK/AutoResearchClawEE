# MATLAB Code Style

## Execution Environment (WSL/Linux)

```bash
# Standard execution
cd /path/to/MATLAB/dir && matlab -nodesktop -nosplash -batch "run('filename.m'); exit"

# Simplified
matlab -nodesktop -r filename

# With log
matlab -nodesktop -logfile output.log -r filename
```

## checkcode Enforcement

Every `.m` file must pass checkcode validation:

```bash
cd MATLAB && matlab -batch "checkcode('filename.m')"
```

## Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Functions | camelCase or snake_case (match existing) | `RunOptimization.m`, `ProcessData.m` |
| Variables | descriptive, camelCase | `lineData`, `busMatrix` |
| Constants | UPPER_CASE | `MAX_ITERATIONS` |
| Index functions | `idx_` prefix | `idx_bus.m`, `idx_line.m` |

## Architecture

- Flat script structure — no complex OOP hierarchies
- One function per file for reusable functions
- Main scripts call helper functions directly
- Avoid deep try-catch nesting

## Operator Precedence

Mixed `||`/`&&` must use explicit parentheses:

```matlab
% BAD — relies on precedence, poor readability
if isempty(val) || isjava(val) && isempty(char(val))

% GOOD — explicit parentheses
if isempty(val) || (isjava(val) && isempty(char(val)))
```

## Key Script Categories

| Category | Examples |
|----------|---------|
| Optimization | `RunOptimization.m`, `SolveModel.m` |
| Test Data | `case33mg.m` |
| Optimization | `optimization_solver.py` |
| Data I/O | `config.json`, `config_utils.py` |
| Results | `result_utils.py` |
