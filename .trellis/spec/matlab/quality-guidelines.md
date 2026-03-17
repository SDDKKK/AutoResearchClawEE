# MATLAB Quality Guidelines

## checkcode Validation Flow

```
Modify .m file → Run checkcode → Review output → Fix issues → Re-check → Commit
```

### Execution

```bash
cd MATLAB && matlab -batch "checkcode('filename.m')"
```

### Severity Levels

| Level | Action |
|-------|--------|
| L1 (Error) | Must fix before commit |
| L2 (Warning) | Must fix before commit |
| L3 (Performance) | Fix when practical |
| L4 (Style) | Fix when practical |
| L5 (Info) | Optional |

### Workflow

- ✅ Modify → checkcode → confirm no L1/L2 → commit
- ⚠️ L1/L2 found → list line numbers + fix
- 🚫 Never skip checkcode or commit with L1/L2 errors

## Temporary Scripts

Prefer inline execution:

```bash
matlab -batch "
% validation logic
disp('test passed');
exit
"
```

If temp file created: delete after use.

## Pre-Commit Checklist

- [ ] `checkcode('filename.m')` shows no L1/L2
- [ ] Script runs without error: `matlab -batch "run('filename.m')"`
- [ ] Output data verified (spot check Excel/CSV output)
- [ ] No temp/debug files left in MATLAB/

## Review Checklist (Check Agent)

Review in this order:

1. **PRD coverage** — verify each requirement in prd.md is implemented
2. **Cross-language API validation** — if calling Python, verify function signatures, column counts, types
3. **Regression safety** — new logic must be inside conditional branches; default path unchanged
4. **docstring.md** — format (`%` line comments), `输入：`/`输出：` labels
5. **code-style.md** — naming, parentheses, architecture
6. **scientific-computing.md** — vectorization, preallocation, I/O patterns
