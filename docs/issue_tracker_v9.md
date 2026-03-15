# AutoResearchClaw — Issue Tracker v9

> Created: 2026-03-15
> Status: **Active** — tracking all known issues from Phase 0-3 regression tests
> Covers: Run 7-13 findings, V8 merge improvements, upstream sync

---

## Issue Summary

| Category | Total | Fixed | Partial | Open |
|----------|-------|-------|---------|------|
| LaTeX & Title | 5 | 5 | 0 | 0 |
| Experiment Quality | 6 | 5 | 1 | 0 |
| Code Generation | 4 | 3 | 1 | 0 |
| Writing Quality | 5 | 5 | 0 | 0 |
| Literature & Citations | 4 | 4 | 0 | 0 |
| Infrastructure (Docker) | 5 | 5 | 0 | 0 |
| Pipeline Logic | 3 | 1 | 1 | 1 |
| **New Feature Requests** | 1 | 1 | 0 | 0 |
| **Total** | **33** | **29** | **3** | **1** |

---

## 1. LaTeX & Title Issues

### I-01: Title extraction fails on `##` headings (FIXED)
- **Severity**: High
- **Status**: FIXED — v9 patch
- **Root Cause**: `_extract_paper_title()` in `executor.py:242` only matched `# ` (H1). When LLM generates `## Title ...` (H2), no candidates were found → returned `"Untitled Paper"`.
- **Affected Runs**: Run 12 (`\title{Untitled Paper}`)
- **Files**:
  - `researchclaw/pipeline/executor.py:240-253` — regex now matches `#{1,2}`, strips "Title " prefix
  - `researchclaw/templates/converter.py:429-451` — `_extract_title()` now handles level 1 and 2
- **Fix**: Added H2 fallback; handles `## Title <actual title>` pattern by stripping literal "Title " prefix.

### I-02: Converter `_extract_title` also level-1 only (FIXED)
- **Severity**: Medium
- **Status**: FIXED — v9 patch (same fix as I-01)
- **File**: `researchclaw/templates/converter.py:434,442,447` — `sec.level in (1, 2)` + "Title " prefix strip
- **Note**: Both I-01 and I-02 fixed together.

### I-03: LaTeX outer fence not stripped (FIXED)
- **Severity**: High
- **Status**: FIXED — commit `3792fd6`
- **File**: `converter.py:107-117`
- **Fix**: Greedy regex + boundary strip

### I-04: Metric values 16 decimal places (FIXED)
- **Severity**: Medium
- **Status**: FIXED — commit `3792fd6`
- **File**: `converter.py:119-133`
- **Fix**: `_round_raw_metrics()` rounds to 4 places

### I-05: Duplicate tables in LaTeX output (FIXED)
- **Severity**: Medium
- **Status**: FIXED — IMP-30, commit `b88aba2`
- **File**: `converter.py:542-575`
- **Fix**: `_deduplicate_tables()` by header row matching

---

## 2. Experiment Quality Issues

### I-06: Experiments only run n=1 seeds (FIXED)
- **Severity**: High
- **Status**: FIXED — v9 patch
- **Evidence**: Run 11 (n=1), Run 12 (n=1), Run 13 (n=1)
- **Root Cause**: Time budget pressure + weak enforcement in prompts.
- **Fix**: Added `multi_seed_enforcement` block in `prompts.py` with mandatory implementation pattern (3-5 seeds), adaptive seed count, and concrete code template. Injected into code_generation for all sandbox/docker experiments via `executor.py`.
- **Files**: `prompts.py` (new `multi_seed_enforcement` block), `executor.py:2145-2149`

### I-07: Ablation methods produce identical outputs (PARTIAL)
- **Severity**: High
- **Status**: PARTIAL — detection exists, prevention incomplete
- **Evidence**: Run 12 — ablation checker flagged many identical conditions
- **Files**:
  - `executor.py:3776-3815` — identical condition detection (WORKS)
  - `executor.py:4491-4560` — `_check_ablation_effectiveness()` (WORKS)
  - `prompts.py:969+` — stronger ablation guidance (HELPS, not sufficient)
- **Root Cause**: LLM code generation creates `class AblationB(Baseline): pass` empty subclasses
- **Fix**: Deeper AST validation that ablation class overrides at least one method.

### I-08: RL training steps insufficient (FIXED)
- **Severity**: High
- **Status**: FIXED — v9 patch
- **Evidence**: Run 13 PPO/SAC/TD3 all near-zero reward after 60k steps
- **Root Cause**: RL algorithms need 500k-1M+ steps for MuJoCo tasks
- **Fix**: Added `rl_step_guidance` block in `prompts.py` with per-algorithm minimum steps table (PPO MuJoCo: 500K min / 1M-3M recommended, SAC/TD3: 300K min, etc.), step budget allocation strategy, and evaluation protocol. Auto-detected via topic keywords and injected into both experiment_design and code_generation prompts.
- **Files**: `prompts.py` (new `rl_step_guidance` block), `executor.py:2161-2174` (code_gen), `executor.py:1960-1963` (exp_design)

### I-09: All experiment methods fail (zero metrics) (FIXED)
- **Severity**: Critical
- **Status**: FIXED — Run 7-10 all had this, Runs 11-12 improved
- **Fixes applied**: Docker deps (commit `787172d`), training epochs (commit `787172d`), anti-simulation rules (commit `44151b1`)
- **Verification**: Run 11 still has 0 metrics (QLoRA instability), Run 12 has valid metrics

### I-10: `.ptp()` NumPy 2.0 API removed (FIXED)
- **Severity**: High
- **Status**: FIXED — commit `44151b1`
- **File**: `validator.py` — forbidden patterns detection
- **Fix**: Detect and replace deprecated NumPy APIs before execution

### I-11: Experiment results not framed correctly in paper (FIXED)
- **Severity**: Medium
- **Status**: FIXED — IMP-10 contradiction detection
- **File**: `executor.py:_detect_result_contradictions()`
- **Fix**: Auto-frames null results, warns about negative results

---

## 3. Code Generation Issues

### I-12: Code too simplistic / lazy implementations (FIXED)
- **Severity**: Critical
- **Status**: FIXED — commit `cb4af26`
- **Files**: `validator.py` (AST analysis), `executor.py` (LLM code review stage 10.5)
- **Fix**: Minimum 50 lines per algorithm class, empty subclass detection

### I-13: dict[key] crashes without .get() (FIXED)
- **Severity**: Medium
- **Status**: FIXED — commit `44151b1`
- **File**: `validator.py` — forbidden patterns
- **Fix**: Detect unsafe dict access in generated code

### I-14: LLM tasks use synthetic simulation (FIXED)
- **Severity**: Critical
- **Status**: FIXED — commit `44151b1`
- **File**: `prompts.py` — CRITICAL NO SIMULATION rule
- **Fix**: Prohibit fake training loops with synthetic loss values

### I-15: Missing experiment harness integration (PARTIAL)
- **Severity**: Medium
- **Status**: PARTIAL — harness injection works, but generated code doesn't always use it
- **File**: `docker_sandbox.py:149-156` — `_inject_harness()`
- **Evidence**: Some runs produce code that ignores the harness and reports metrics differently

---

## 4. Writing Quality Issues

### I-16: Academic style violations (FIXED)
- **Status**: FIXED — IMP-20, commit `b88aba2`
- **File**: `prompts.py` — `academic_style_guide` block

### I-17: Hedging language throughout paper (FIXED)
- **Status**: FIXED — IMP-31, commit `b88aba2`
- **File**: `prompts.py` — `anti_hedging_rules` block

### I-18: Number repetition across sections (FIXED)
- **Status**: FIXED — IMP-24, commit `b88aba2`
- **File**: `prompts.py` — `anti_repetition_rules` block

### I-19: Title too long / not formatted (FIXED)
- **Status**: FIXED — `title_guidelines` rewrite, commit `b88aba2`
- **File**: `prompts.py` — 14-word limit, MethodName: Subtitle format

### I-20: Abstract too verbose (FIXED)
- **Status**: FIXED — `abstract_structure` rewrite, commit `b88aba2`
- **File**: `prompts.py` — PMR+ format, 180-220 words

---

## 5. Literature & Citation Issues

### I-21: Hallucinated citations (FIXED)
- **Status**: FIXED — Run 11: 90% verified, Run 12: 97.1% verified
- **Files**: `literature/verify.py`, `literature/search.py`

### I-22: Invalid citation markers [?key:NOT_IN_BIB] (FIXED)
- **Status**: FIXED — IMP-29, silent removal
- **File**: `executor.py`

### I-23: Missing seminal papers (FIXED)
- **Status**: FIXED — `data/seminal_papers.yaml` seed library
- **File**: `researchclaw/data/seminal_papers.yaml`

### I-24: Rate-limited API searches (FIXED)
- **Status**: FIXED — commit `63c5a7d`
- **Files**: `arxiv_client.py` (circuit breaker), `openalex_client.py` (new), `semantic_scholar.py` (batch API)

---

## 6. Infrastructure Issues

### I-25: Docker missing ML packages (FIXED)
- **Status**: FIXED — transformers, peft, trl, bitsandbytes, MuJoCo, etc.
- **Commits**: `e72a818`, `787172d`

### I-26: HF cache mount duplication (FIXED)
- **Status**: FIXED — commit `44151b1`
- **File**: `docker_sandbox.py`

### I-27: Dataset pre-caching (FIXED)
- **Status**: FIXED — CIFAR-10/100, FashionMNIST, MNIST in Docker image
- **Commits**: `787172d`

### I-28: Time budget too short for LLM tasks (FIXED)
- **Status**: FIXED — adaptive time budget by task type
- **File**: `executor.py:2145-2160`

### I-29: Non-root pip install failure in Docker (FIXED)
- **Status**: FIXED — `--break-system-packages` flag
- **File**: `docker_sandbox.py`

---

## 7. Pipeline Logic Issues

### I-30: Pipeline proceeds after MAX_DECISION_PIVOTS=2 (BY DESIGN)
- **Severity**: Medium
- **Status**: BY DESIGN — prevents infinite loops
- **File**: `executor.py`
- **Note**: Pipeline writes paper even if experiment quality is low after 2 pivots

### I-31: LLM code review JSON parsing failure (FIXED)
- **Status**: FIXED — commit `44151b1`
- **File**: `executor.py:2300-2330`
- **Fix**: Markdown fence stripping, graceful fallback

### I-32: Topic quality not validated against trends (OPEN)
- **Severity**: Medium
- **Status**: OPEN — IMP-35 adds pre-evaluation but no trend checking
- **File**: `executor.py` (topic quality pre-evaluation)
- **Potential Fix**: Phase 4 — benchmark discovery system

---

## 8. New Feature Requests

### F-01: Training Framework Documentation Retrieval (FIXED — Phase 1)
- **Severity**: High — impacts LLM fine-tuning code quality
- **Status**: FIXED (Phase 1: static docs) — v9 patch
- **Description**: When the pipeline needs to generate code using training frameworks (LlamaFactory, TRL, Axolotl), the backbone LLM may not know the correct API usage. The pipeline should:
  1. Detect which framework is needed based on the experiment design
  2. Fetch the framework's official API documentation and example code
  3. Inject relevant documentation into the code generation prompt
  4. Generate code that correctly uses the framework APIs
- **Current Problem**: Generated training code may use incorrect or outdated API calls, leading to experiment failures (e.g., Run 11 QLoRA training diverged)
- **Proposed Approaches**:
  - **Option A: Static doc snippets** — Bundle curated API reference snippets for common frameworks in `researchclaw/data/framework_docs/`. Simple, fast, but requires manual updates.
  - **Option B: Context7-style MCP** — Use Context7 (upstash/context7) to fetch live documentation at runtime via MCP protocol. Always up-to-date, but adds network dependency.
  - **Option C: Git clone + extract** — Clone framework repos at pipeline startup, extract README/docs/examples, summarize via LLM, inject into prompts. Most complete, but slow and requires network.
  - **Option D: Hybrid** — Bundle static docs for top frameworks + fallback to web fetch for unknown ones.
- **Reference Tools**: Cursor `@Docs`, Context7 MCP, Aider web context, OpenHands SDK
- **Target**: Phase 4 or Phase 5
- **Dependencies**: Network access during code generation stage

### F-01 Detailed Design: Framework Doc-RAG

#### Problem Statement

When the pipeline generates experiment code that uses ML training frameworks (LlamaFactory, TRL, Axolotl, transformers Trainer), the backbone LLM (GPT-5.1/GPT-4.1) may not know current API signatures, default parameters, or correct usage patterns. This leads to:

1. **Incorrect API calls** — using removed or renamed functions
2. **Missing config fields** — e.g. LlamaFactory YAML missing required keys
3. **Wrong training patterns** — e.g. calling `Trainer.train()` without `TrainingArguments`
4. **Version mismatch** — framework APIs change between versions installed in Docker vs LLM training data

Evidence: Run 11 (QLoRA) — all 8 methods diverged; likely caused by incorrect training setup.

#### Industry Survey

| Tool | Approach | Pros | Cons |
|------|----------|------|------|
| **DocPrompting** (ICLR 2023) | BM25/dense retrieval over docs → inject into code gen prompt | Academic validation (+2.85% pass@1), open source | Requires pre-built index |
| **Cursor @Docs** | User adds doc URLs, IDE crawls/indexes, injects relevant snippets into LLM context | Real-time, version-aware | Requires IDE, manual URL management |
| **Context7 MCP** | MCP server with 9000+ pre-indexed libraries, `resolve-library-id` + `query-docs` tools | Automatic, 9k libraries, version-specific | Network dependency, closed backend |
| **DSPy DocLearner** | BeautifulSoup scraper → LLM analysis → code generation chain | Fully automated pipeline | Slow, brittle scraping |
| **llms.txt** | Standardized `/llms.txt` markdown file in project root for LLM consumption | Simple, no crawling needed | Requires framework authors to adopt |
| **AI Scientist v2** | No templates, relies purely on LLM knowledge + tree search debugging | Zero setup | Lower success rate, no doc awareness |
| **Continue + MCP** | DeepWiki for GitHub repos + Context7 for docs + `.continue/rules` | Extensible MCP ecosystem | Complex setup |
| **AGENTS.md** | Project-level instructions for AI agents (60k+ projects adopted) | No infra needed | Only project conventions, not API docs |

**Key finding**: No existing autonomous research agent (AI Scientist v1/v2, CodeScientist) dynamically reads documentation at runtime. They all rely on pre-built templates or LLM training data. **Doc-RAG would be a differentiating feature for AutoResearchClaw.**

**Academic evidence**: IBM study shows well-structured documentation improves AI response accuracy by up to **47%**.

#### Available Framework Documentation

| Framework | Docs URL | Format | Key Content |
|-----------|----------|--------|-------------|
| **TRL** | `huggingface.co/docs/trl` | HTML/MD | SFTTrainer, DPOTrainer, GRPOTrainer, RewardTrainer |
| **LlamaFactory** | `llamafactory.readthedocs.io` | HTML/RST | YAML config, CLI, SFT/DPO/RLHF/KTO/ORPO |
| **Axolotl** | `docs.axolotl.ai` | HTML/MD | YAML config, LoRA/QLoRA/GPTQ, full/DPO/GRPO |
| **PEFT** | `huggingface.co/docs/peft` | HTML/MD | LoRA/QLoRA config, get_peft_model |
| **transformers** | `huggingface.co/docs/transformers` | HTML/MD | Trainer, TrainingArguments, AutoModel |

#### Recommended Implementation: Hybrid Static + Web Fetch

**Phase 1 (Static — immediate):**
- Create `researchclaw/data/framework_docs/` directory
- Bundle curated API snippets for top 5 frameworks:
  - `trl.md` — SFTTrainer, DPOTrainer, PPOTrainer usage + config
  - `llamafactory.md` — YAML config format, CLI usage, dataset format
  - `transformers_trainer.md` — TrainingArguments, Trainer, PEFT integration
  - `peft.md` — LoRA/QLoRA config, get_peft_model, prepare_model_for_kbit_training
  - `axolotl.md` — YAML config format, training modes
- In `executor.py:_execute_code_generation()`, detect framework from experiment design
- Inject matching doc snippet into code generation prompt as `{framework_reference}`
- **Effort**: ~4 hours, no network dependency

**Phase 2 (Web Fetch — later):**
- Add `FrameworkDocFetcher` class in `researchclaw/literature/framework_docs.py`
- On experiment_design detection of framework name:
  1. Check if `llms.txt` exists at framework's docs URL
  2. If yes, fetch and extract relevant sections
  3. If no, fall back to static bundle
- Cache fetched docs locally (`.researchclaw_cache/framework_docs/`)
- TTL: 7 days (frameworks don't change API that often)
- **Effort**: ~8 hours, requires network during code gen stage

**Phase 3 (Context7 MCP — optional):**
- Integrate Context7 MCP client for automatic library discovery
- `resolve-library-id("trl")` → `"/huggingface/trl"`
- `query-docs("/huggingface/trl", "SFTTrainer config")` → relevant docs
- Most complete solution but adds external service dependency

#### Phase 1 Implementation (COMPLETED — v9 patch)

- Created `researchclaw/data/framework_docs/` with 5 curated API reference files:
  - `trl.md` — SFTTrainer, DPOTrainer, GRPOTrainer, PPOTrainer, PEFT integration
  - `peft.md` — LoRA, QLoRA, DoRA configs, save/load, target_modules by model
  - `transformers_training.md` — TrainingArguments, Trainer, tokenization, causal LM
  - `llamafactory.md` — YAML config, CLI, dataset formats, DPO, export
  - `axolotl.md` — YAML config, dataset formats, DPO, multi-GPU
- Added `detect_frameworks()` and `load_framework_docs()` in `researchclaw/data/__init__.py`
- Injected into both `experiment_design` and `code_generation` stages in `executor.py`
- Auto-detection based on topic + hypothesis + experiment plan keywords
- Max 8000 chars for code_generation, 4000 chars for experiment_design (to avoid context overflow)

#### Integration Point in Pipeline

```
Stage 9: experiment_design → detects framework (e.g., "use TRL SFTTrainer")
                ↓
Stage 10: code_generation prompt += framework_reference doc snippet
                ↓
Stage 10.5: code_review → validates API calls against doc snippet
                ↓
Stage 12: execution → framework is already installed in Docker
```

#### Framework Detection Heuristics

```python
FRAMEWORK_KEYWORDS = {
    "trl": ["SFTTrainer", "DPOTrainer", "PPOTrainer", "trl", "RewardTrainer"],
    "llamafactory": ["LlamaFactory", "llama_factory", "llamafactory"],
    "peft": ["LoRA", "QLoRA", "get_peft_model", "PeftConfig"],
    "transformers": ["Trainer", "TrainingArguments", "AutoModelForCausalLM"],
    "axolotl": ["axolotl"],
}
```

---

## Appendix A: Issue-to-Run Mapping

| Run | Issues Hit | Quality Score |
|-----|-----------|---------------|
| Run 7 | I-03, I-04, I-09, I-12, I-16-I-20 | 3/10 |
| Run 8-10 | I-09, I-10, I-25, I-27 | Not scored |
| Run 11 | I-01 (OK), I-06, I-09 (QLoRA diverge) | 7/10 |
| Run 12 | I-01, I-06, I-07, I-15 | 7.5/10 |
| Run 13 | I-06, I-08 | Running... |

## Appendix B: Fix Commit Reference

| Commit | Description | Issues Fixed |
|--------|-------------|-------------|
| `3792fd6` | V4 improvements | I-03, I-04 |
| `cb4af26` | Phase 1 code quality | I-12 |
| `e72a818` | Phase 2 LLM fine-tuning | I-25, I-28 |
| `787172d` | Phase 0 diagnostics | I-09, I-10, I-27 |
| `44151b1` | Phase 3 regression fixes | I-13, I-14, I-26, I-29, I-31 |
| `b88aba2` | V8 merge | I-05, I-16-I-20, I-22 |
| `63c5a7d` | Rate-limit defense | I-24 |

## Appendix C: Files Most Frequently Modified

| File | Issue Count | Lines |
|------|------------|-------|
| `researchclaw/pipeline/executor.py` | 14 | ~6000 |
| `researchclaw/prompts.py` | 10 | ~2500 |
| `researchclaw/templates/converter.py` | 5 | ~1200 |
| `researchclaw/experiment/docker_sandbox.py` | 3 | ~420 |
| `researchclaw/docker/Dockerfile` | 3 | ~45 |
