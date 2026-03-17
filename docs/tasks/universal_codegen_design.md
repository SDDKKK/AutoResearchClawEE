# Universal Cross-Domain Research Code Generation Framework

> Design Document v1.0 | 2026-03-17
> Status: DRAFT — 待讨论确认后实施

---

## 1. Executive Summary

当前 AutoResearchClaw 的代码生成能力集中在 ML/AI 领域，存在 **400+ 行 ML 特定硬编码**。要成为通用科研工具，需要从架构层面解决三个核心问题：

1. **领域知识获取**：面对陌生领域，如何快速学习（GitHub 搜索、文献检索、代码参考）
2. **实验范式泛化**：不同领域的实验结构差异巨大（ML 的 train/eval vs 物理的 convergence study vs 经济学的 regression table）
3. **代码质量保障**：不同领域的评估标准、依赖栈、输出格式各不相同

**核心设计理念**：不是为每个领域写死模板，而是建立一套 **"检索 → 理解 → 适配 → 生成 → 验证"** 的通用框架，让 LLM 在生成前先"做功课"。

---

## 2. 竞品分析与差距

### 2.1 现有工具对比

| 工具 | 架构 | 跨领域 | 代码搜索 | 多文件 | 验证 |
|------|------|--------|----------|--------|------|
| **AI-Scientist v2** (Sakana) | BFTS 树搜索 + 无模板 | 有限（仍需领域seed） | Semantic Scholar | 单文件为主 | 运行+自检 |
| **AI-Researcher** (HKUDS) | 6-Agent 流水线 | 理论上通用 | 文献检索 | 未知 | 分析Agent |
| **OpenHands** | 事件溯源 + 模块化SDK | 通用编程 | 无内置 | 完整支持 | 测试驱动 |
| **Devin** | 规划+沙箱+记忆 | 通用编程 | DeepWiki 索引 | 完整支持 | 交互式确认 |
| **AutoCodeRover** | AST 导航 + SBFL | Bug修复专用 | AST搜索 | 完整支持 | 测试对比 |
| **当前 AutoResearchClaw** | Blueprint → 顺序生成 | ML only | 无 | 多文件(v2) | AST+运行 |

### 2.2 关键差距

1. **无代码搜索能力**：面对陌生领域，完全依赖 LLM 内部知识，无法参考已有实现
2. **实验范式硬编码**：`baselines/ablations/training/metrics` 固定键名，无法适配其他领域
3. **依赖栈固定**：Docker 镜像只预装 ML 包，不支持 RDKit/PySCF/scanpy 等
4. **评估标准单一**：只支持 `metric: float` 格式，不支持回归表、收敛图等
5. **BenchmarkAgent 仅覆盖 13 个 ML 子领域**
6. **FigureAgent 只支持 2D 学术图表**

---

## 3. 目标领域与实验范式

### 3.1 领域实验范式差异

| 领域 | 实验范式 | 核心指标 | baseline 模式 | 依赖栈 |
|------|----------|----------|---------------|--------|
| **CV/NLP/RL** (当前) | train → eval → compare | accuracy, F1, reward | 方法对比 (A vs B) | torch, transformers, gymnasium |
| **物理/计算物理** | setup → simulate → analyze | 能量守恒, 收敛阶, 相对误差 | 方法收敛性对比 | JAX-MD, ASE, OpenMM, FEniCS |
| **计算化学** | build molecule → calculate → compare | MAE (kcal/mol), RMSE | vs DFT/CCSD(T) 参考 | RDKit, PySCF, ASE |
| **生物信息学** | load data → preprocess → cluster → DE | ARI, DEG count, F1 | vs Leiden/Wilcoxon | scanpy, anndata, BioPython |
| **经济学/计量** | clean data → estimate → robustness | 系数, SE, R², F-stat | 渐进式 (OLS → +控制变量 → +FE → +IV) | statsmodels, linearmodels |
| **计算数学** | define problem → solve → convergence | 收敛阶, L2/L∞ 误差 | 方法精度对比 | SymPy, SciPy, FEniCS |
| **安全研究** | load dataset → extract features → classify | TPR, FPR, per-class F1 | vs RF/XGB/SVM | scapy, sklearn, angr |
| **机器人/控制** | define env → train agent → evaluate | episode return, success rate | PPO/SAC/TD3 对比 | MuJoCo, PyBullet, SB3 |

### 3.2 统一抽象

虽然差异巨大，但所有领域的计算实验都可以抽象为：

```
实验 = {
    问题定义 (Problem),        # 要解决什么
    方法/条件 (Conditions),    # 用什么方法（可能多个）
    数据/输入 (Inputs),        # 输入数据或初始条件
    执行过程 (Execution),      # 怎么跑
    输出/结果 (Outputs),       # 产出什么
    评估标准 (Evaluation),     # 怎么评判好坏
    呈现方式 (Presentation)    # 表格 / 图 / 统计检验
}
```

---

## 4. 架构设计

### 4.1 总体架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Universal CodeGen Pipeline                    │
│                                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐       │
│  │  Domain   │    │  Code    │    │ Blueprint │    │Sequential│       │
│  │ Detector  │───▶│ Searcher │───▶│ Generator │───▶│ CodeGen  │       │
│  │ & Adapter │    │ (NEW)    │    │(Enhanced) │    │  (v2)    │       │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘       │
│       │               │               │               │              │
│       ▼               ▼               ▼               ▼              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐       │
│  │ Domain   │    │Reference │    │ Domain   │    │ Domain   │       │
│  │ Profile  │    │  Code    │    │ Prompt   │    │Validator │       │
│  │ Registry │    │  Cache   │    │ Adapter  │    │ Adapter  │       │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘       │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │              Flexible Sandbox Execution Engine                │    │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐             │    │
│  │  │  ML    │  │Physics │  │Bio/Chem│  │Generic │  ...         │    │
│  │  │ Image  │  │ Image  │  │ Image  │  │ Image  │             │    │
│  │  └────────┘  └────────┘  └────────┘  └────────┘             │    │
│  └──────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 核心模块设计

#### Module 1: Domain Detector & Adapter

**目标**：自动识别研究领域，加载对应的领域配置。

```python
# researchclaw/domains/detector.py

class DomainProfile:
    """领域配置文件，YAML 格式"""
    domain_id: str               # e.g., "computational_physics"
    display_name: str            # e.g., "Computational Physics"
    parent_domain: str | None    # e.g., "physics"

    # 实验范式
    experiment_paradigm: str     # "comparison" | "convergence" | "progressive_spec" | "simulation"
    condition_terminology: dict  # {"baseline": "reference_method", "ablation": "variant", ...}

    # 代码结构
    typical_file_structure: dict # 典型的文件组织方式
    entry_point: str             # "main.py" | "run.py" | "train.py"

    # 依赖与环境
    core_libraries: list[str]    # 核心依赖包
    docker_image: str            # 对应的 Docker 镜像
    gpu_required: bool

    # 指标与评估
    metric_types: list[MetricType]  # scalar, table, convergence_curve, ...
    standard_baselines: list[str]   # 该领域的标准 baseline
    evaluation_protocol: str        # 评估协议描述
    statistical_tests: list[str]    # 适用的统计检验

    # 输出与呈现
    output_formats: list[str]       # "latex_table" | "convergence_plot" | "regression_table"
    figure_types: list[str]         # 领域特定的图表类型

    # 搜索关键词
    github_search_terms: list[str]  # 用于 GitHub 搜索的关键词
    paper_keywords: list[str]       # 用于文献搜索的关键词
```

**领域检测逻辑**：
```python
def detect_domain(topic: str, hypotheses: str, literature: str) -> DomainProfile:
    """
    三级检测：
    1. 关键词匹配 → 快速命中已知领域
    2. LLM 分类 → 对模糊主题进行分类
    3. 混合领域 → 如 "physics-informed neural networks" 同时匹配 physics + ML
    """
```

**已知领域配置文件** (YAML)：
```
researchclaw/domains/profiles/
├── ml_vision.yaml
├── ml_nlp.yaml
├── ml_rl.yaml
├── ml_tabular.yaml
├── ml_graph.yaml
├── physics_simulation.yaml
├── physics_pde.yaml
├── chemistry_qm.yaml
├── chemistry_molprop.yaml
├── biology_singlecell.yaml
├── biology_genomics.yaml
├── economics_empirical.yaml
├── mathematics_numerical.yaml
├── security_detection.yaml
├── robotics_control.yaml
└── _generic.yaml              # 通用 fallback
```

#### Module 2: Code Searcher (全新模块)

**目标**：面对陌生领域时，从 GitHub 搜索类似项目，学习代码结构和 API 用法。

```python
# researchclaw/agents/code_searcher/

class CodeSearchAgent:
    """
    代码搜索 Agent —— 在生成代码前先"做功课"

    搜索策略：
    1. GitHub API 搜索 (REST API, 10 req/min)
    2. 本地参考代码缓存 (避免重复搜索)
    3. LLM 过滤与摘要 (从搜索结果中提取关键模式)
    """

    async def search_reference_code(
        self,
        topic: str,
        domain: DomainProfile,
        specific_needs: list[str],  # e.g., ["PySCF DFT calculation", "RDKit fingerprint"]
    ) -> CodeSearchResult:
        """
        执行多源搜索，返回参考代码片段

        流程：
        1. 生成搜索 query (LLM 根据 topic + domain 生成 3-5 个搜索词)
        2. GitHub REST API 搜索 repos + code
        3. 过滤：按 stars, 活跃度, 相关性排序
        4. 读取 top-K 仓库的关键文件 (README, main script, requirements.txt)
        5. LLM 提取：从参考代码中提取可复用的模式
        """

    async def search_github_repos(self, query: str, language: str = "Python") -> list[RepoInfo]:
        """
        GitHub REST API: GET /search/repositories
        - 按 stars 排序
        - 过滤最近 2 年内更新过的
        - 最多返回 10 个结果
        """

    async def search_github_code(self, query: str, language: str = "Python") -> list[CodeSnippet]:
        """
        GitHub REST API: GET /search/code
        - 搜索特定 API 用法 (e.g., "pyscf.scf.RHF")
        - 返回文件路径 + 代码片段
        - 注意：10 req/min 限制
        """

    async def read_repo_structure(self, repo: RepoInfo) -> RepoAnalysis:
        """
        读取仓库关键文件：
        - README.md → 理解项目目的
        - requirements.txt / setup.py → 依赖列表
        - main script → 代码结构模式
        - 测试文件 → 评估方法
        """

    async def extract_patterns(self, code_snippets: list[CodeSnippet]) -> CodePatterns:
        """
        LLM 从参考代码中提取：
        - API 调用模式 (如何使用某个库)
        - 文件组织模式 (项目结构)
        - 数据处理模式 (数据加载/预处理)
        - 评估模式 (如何计算和报告指标)
        """
```

**搜索结果缓存**：
```python
# 缓存在 researchclaw/data/code_search_cache/ 下
# 按 domain + topic hash 组织
# TTL = 30 天
# 格式：
{
    "query": "PySCF DFT hartree fock",
    "timestamp": "2026-03-17T10:00:00Z",
    "repos": [...],
    "patterns": {
        "api_usage": ["from pyscf import gto, scf\nmol = gto.M(atom='H 0 0 0; H 0 0 0.74', basis='sto-3g')\nmf = scf.RHF(mol)\nmf.kernel()"],
        "file_structure": {"main.py": "...", "molecule.py": "..."},
        "evaluation": "MAE of energy vs reference CCSD(T) values"
    }
}
```

**为什么这个功能很关键？**

- AI-Scientist-v2 仍然依赖 LLM 内部知识来写代码。对于 2024 年以前的主流库（PyTorch, NumPy），这足够了。但对于小众领域（比如 PySCF 的特定 API、scanpy 的某个新特性），LLM 可能知识过时或不准确。
- Devin 的 DeepWiki 只索引已有仓库，不会主动搜索新仓库。
- GitHub 搜索 API 虽然有 10 req/min 限制，但对于一次代码生成任务来说完全够用（通常只需 3-5 次搜索）。

#### Module 3: Enhanced Blueprint Generator

**改进 Blueprint 生成**：加入领域上下文和参考代码。

```python
# 新的 Blueprint 生成流程

async def generate_blueprint(
    self,
    topic: str,
    exp_plan: dict,
    domain: DomainProfile,
    reference_code: CodeSearchResult | None,
) -> Blueprint:
    """
    Enhanced Blueprint = 当前 Blueprint + 领域适配 + 参考代码

    新增内容：
    1. 文件结构建议（来自 domain profile + 参考代码）
    2. 库 API 用法示例（来自 code search）
    3. 领域特定的评估协议（来自 domain profile）
    4. 统计检验要求（来自 domain profile）
    """
```

**Blueprint 模板按领域差异化**：

```yaml
# ML 领域 Blueprint 结构
files:
  - config.py: "Hyperparameters and model configuration"
  - data.py: "Dataset loading with train/val/test splits"
  - model.py: "Model architecture definition"
  - train.py: "Training loop with metric tracking"
  - main.py: "Entry point: setup → train → evaluate → report"

# 物理模拟 Blueprint 结构
files:
  - config.py: "Simulation parameters (grid, timestep, boundary conditions)"
  - system.py: "Physical system definition (potentials, Hamiltonian)"
  - integrator.py: "Numerical integrator implementation"
  - analysis.py: "Observable computation from simulation data"
  - main.py: "Entry point: setup → simulate → analyze → report"

# 经济学 Blueprint 结构
files:
  - config.py: "Specification definitions and variable lists"
  - data_prep.py: "Data cleaning, variable construction, panel setup"
  - models.py: "Regression specifications (OLS, FE, IV)"
  - robustness.py: "Robustness checks and sensitivity analysis"
  - main.py: "Entry point: load → estimate → robustness → tables"
```

#### Module 4: Domain-Aware Prompt Adapter

**目标**：将当前 prompts.py 中的 ML 硬编码提取为可插拔的领域适配器。

```python
# researchclaw/domains/prompt_adapter.py

class PromptAdapter:
    """
    根据领域动态组装 prompt blocks

    当前硬编码的 blocks:
    - compute_budget_block     → 领域化 (ML: epochs, Physics: timesteps, Econ: specifications)
    - dataset_guidance_block   → 领域化 (ML: torchvision, Physics: initial conditions, Bio: h5ad)
    - hp_reporting_block       → 领域化 (ML: lr/batch_size, Physics: dt/grid_size, Econ: cluster_se)
    - rl_step_guidance_block   → ML-RL 专用，其他领域替换
    - llm_training_block       → ML-LLM 专用，其他领域替换
    - writing_structure_block  → 通用，但需要领域化 (经济学的表格约定 vs ML 的图表约定)
    """

    def get_code_generation_prompt(self, domain: DomainProfile, context: dict) -> str:
        """
        组装代码生成 prompt

        = 通用规则 (代码质量, 错误处理, 时间控制)
        + 领域特定规则 (来自 domain profile)
        + 参考代码示例 (来自 code search, 如果有)
        + 实验计划 (来自 Stage 9)
        """

    def get_experiment_design_prompt(self, domain: DomainProfile) -> str:
        """
        实验设计 prompt

        关键改变：
        - 不再使用固定的 "baselines/ablations" 键名
        - 使用 domain.condition_terminology 动态替换
        - 例如物理领域：{"baseline": "reference_solver", "ablation": "parameter_variation"}
        """

    def get_result_analysis_prompt(self, domain: DomainProfile) -> str:
        """
        结果分析 prompt

        关键改变：
        - 不再假设 paired t-test
        - 根据 domain.statistical_tests 选择检验方法
        - 经济学：Hausman test, robust SE
        - 物理：convergence order fitting
        - 生物：Wilcoxon rank-sum, FDR correction
        """
```

**实现策略：渐进式抽取**

不需要一次性重写所有 prompt。分三步：

1. **Step 1**：将现有 ML prompt blocks 封装为 `ml_adapter.py`，保持现有行为不变
2. **Step 2**：创建 `_generic_adapter.py` 作为通用 fallback
3. **Step 3**：逐领域添加 adapter（physics, chemistry, biology, economics, ...）

#### Module 5: Flexible Metric System

**目标**：支持多种指标类型，不局限于 `metric: float`。

```python
# researchclaw/experiment/metrics.py

class MetricType(Enum):
    SCALAR = "scalar"                # 单个浮点数 (accuracy: 0.95)
    TABLE = "table"                  # 回归表 (经济学)
    CONVERGENCE = "convergence"      # 收敛曲线 (数学/物理)
    LEARNING_CURVE = "learning_curve" # 学习曲线 (ML/RL)
    CONFUSION_MATRIX = "confusion"   # 混淆矩阵 (安全/分类)
    STRUCTURED = "structured"        # JSON 结构化结果
    PARETO = "pareto"               # 多目标 Pareto 前沿

class UniversalMetricParser:
    """
    通用指标解析器

    解析优先级：
    1. results.json (JSON 结构化输出, 推荐)
    2. results.csv (表格化输出)
    3. stdout 正则匹配 (兼容现有格式)
    """

    def parse(self, run_dir: Path) -> ExperimentResults:
        # 1. 尝试 JSON
        results_json = run_dir / "results.json"
        if results_json.exists():
            return self._parse_json(results_json)

        # 2. 尝试 CSV
        results_csv = run_dir / "results.csv"
        if results_csv.exists():
            return self._parse_csv(results_csv)

        # 3. Fallback: stdout 解析 (兼容现有行为)
        return self._parse_stdout(run_dir / "stdout.log")
```

**统一结果输出规范**：

```python
# 所有领域的实验代码都应输出 results.json
# 格式如下：

{
    "experiment_type": "comparison",  # or "convergence", "progressive_spec", ...
    "conditions": {
        "proposed_method": {
            "seed_42": {"primary_metric": 0.95, "secondary_metric": 0.87},
            "seed_123": {"primary_metric": 0.94, "secondary_metric": 0.86}
        },
        "baseline_1": { ... }
    },
    # 或者对于收敛研究：
    "convergence": {
        "proposed_method": [
            {"h": 0.1, "error": 0.05},
            {"h": 0.05, "error": 0.012},
            {"h": 0.025, "error": 0.003}
        ]
    },
    # 或者对于回归表：
    "regression_table": {
        "spec_1_ols": {"coeff": 0.15, "se": 0.03, "p": 0.001, "n": 5000, "r2": 0.12},
        "spec_2_fe": {"coeff": 0.11, "se": 0.02, "p": 0.001, "n": 5000, "r2": 0.35}
    },
    "metadata": {
        "domain": "computational_physics",
        "total_runtime_sec": 1200,
        "hardware": "RTX 6000 Ada"
    }
}
```

#### Module 6: Flexible Sandbox

**目标**：支持多种 Docker 镜像，按领域选择。

```yaml
# researchclaw/data/docker_profiles.yaml

profiles:
  ml_base:
    image: "researchclaw/sandbox-ml:latest"
    packages: [torch, torchvision, transformers, datasets, scikit-learn, ...]
    gpu: true
    datasets: [CIFAR-10, CIFAR-100, MNIST, FashionMNIST, STL-10, SVHN]

  physics:
    image: "researchclaw/sandbox-physics:latest"
    packages: [jax, jax-md, ase, fenics, findiff, scipy, numpy]
    gpu: optional

  chemistry:
    image: "researchclaw/sandbox-chemistry:latest"
    packages: [rdkit, pyscf, ase, deepchem, numpy, scipy]
    gpu: false

  biology:
    image: "researchclaw/sandbox-biology:latest"
    packages: [scanpy, anndata, biopython, leidenalg, scikit-learn]
    gpu: false
    memory: "16G"  # 单细胞数据可能很大

  economics:
    image: "researchclaw/sandbox-economics:latest"
    packages: [statsmodels, linearmodels, pandas, scipy, pyreadstat]
    gpu: false

  math:
    image: "researchclaw/sandbox-math:latest"
    packages: [sympy, scipy, numpy, findiff, matplotlib]
    gpu: false

  security:
    image: "researchclaw/sandbox-security:latest"
    packages: [scapy, scikit-learn, xgboost, pandas, numpy]
    gpu: false
    network: "none"  # 安全研究绝对禁止网络

  robotics:
    image: "researchclaw/sandbox-robotics:latest"
    packages: [mujoco, gymnasium, stable-baselines3, torch]
    gpu: true
    extra: [xvfb]  # 无头渲染

  generic:
    image: "researchclaw/sandbox-generic:latest"
    packages: [numpy, scipy, matplotlib, pandas, scikit-learn]
    gpu: false
```

**实现策略**：用一个 base image + 领域层叠加

```dockerfile
# Dockerfile.base — 所有领域共用
FROM python:3.11-slim
RUN pip install numpy scipy matplotlib pandas seaborn tqdm pyyaml

# Dockerfile.physics — 物理领域叠加
FROM researchclaw/sandbox-base:latest
RUN pip install jax jaxlib ase findiff
```

---

## 5. Code Searcher 详细设计

### 5.1 为什么需要 Code Search？

| 场景 | 不用搜索 | 用搜索 |
|------|----------|--------|
| LLM 熟悉的 API (PyTorch, NumPy) | 能正确生成 | 不需要搜索 |
| LLM 不熟悉的 API (PySCF, scanpy 新版) | 可能用错 API、幻觉 | 找到正确用法 |
| 全新领域 (量子计算, 天体物理) | 代码结构不合理 | 参考类似项目 |
| 特定任务 (如 "scanpy 伪时间分析") | 可能缺少关键步骤 | 找到完整 workflow |

### 5.2 搜索流程

```
输入: topic + domain + experiment_plan
       │
       ▼
┌──────────────┐
│ Query 生成    │  LLM 生成 3-5 个搜索 query
│ (LLM)        │  e.g., "PySCF DFT example", "hartree fock python tutorial"
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│ GitHub Repo  │     │ GitHub Code  │  并行搜索
│ Search       │     │ Search       │
│ (10 req/min) │     │ (10 req/min) │
└──────┬───────┘     └──────┬───────┘
       │                     │
       ▼                     ▼
┌──────────────────────────────────┐
│ 过滤与排序                        │
│ - stars > 50                     │
│ - 最近 2 年内更新                  │
│ - Python 语言                     │
│ - 与 topic 相关度 (LLM 评分)      │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ 关键文件读取 (Top 3 repos)        │
│ - README.md                      │
│ - main script (main.py / run.py) │
│ - requirements.txt               │
│ - 核心库调用的文件                  │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ Pattern 提取 (LLM)               │
│ - API 调用模式                    │
│ - 文件组织模式                    │
│ - 数据处理模式                    │
│ - 评估/报告模式                   │
└──────────────┬───────────────────┘
               │
               ▼
输出: CodeSearchResult {
    api_patterns: list[str],       # 关键 API 用法示例
    file_structure: dict,          # 推荐的文件结构
    library_versions: dict,        # 推荐的库版本
    evaluation_patterns: list[str] # 评估方法示例
}
```

### 5.3 GitHub API 使用限制与应对

```
限制：
- Code Search: 10 req/min (authenticated)
- Repo Search: 30 req/min (authenticated)
- 每次搜索最多返回 1000 条
- query 最长 256 字符

应对：
- 预缓存常见领域的搜索结果 (TTL 30天)
- 一次实验最多 5 次 code search + 3 次 repo search
- 用 GitHub token 认证 (需要用户配置)
- 如果限流，graceful degradation: 跳过搜索，使用 LLM 内部知识
```

### 5.4 替代方案 / 增强

1. **Sourcegraph API**: 更强大的代码搜索，但需要企业账号或自建实例
2. **grep.app**: 可以搜索 50万+ 公开仓库，但没有 API
3. **本地向量数据库**: 缓存搜索结果到本地 embedding DB，后续可以语义搜索
4. **arXiv + Papers with Code**: 搜索论文时直接获取关联的代码仓库

---

## 6. 实验范式泛化

### 6.1 统一实验设计 Schema

替换当前固定的 `baselines/proposed_methods/ablations` 键名：

```yaml
# 新的 exp_plan.yaml 格式 (通用版)

experiment:
  type: "comparison"  # comparison | convergence | progressive_spec | simulation | ablation_study

  problem:
    description: "..."
    domain: "computational_physics"

  conditions:
    - name: "verlet_integrator"
      role: "reference"        # 替代 "baseline"
      description: "Standard Verlet integration"
    - name: "symplectic_4th"
      role: "proposed"         # 替代 "proposed_method"
      description: "4th order symplectic integrator"
    - name: "symplectic_4th_adaptive"
      role: "variant"          # 替代 "ablation"
      description: "Adaptive timestep variant"
      varies_from: "symplectic_4th"
      variation: "adaptive_dt"

  inputs:
    type: "generated"          # "benchmark_dataset" | "generated" | "loaded"
    description: "N-body problem with 100 particles"

  evaluation:
    primary_metric:
      name: "energy_drift"
      direction: "minimize"
      unit: "relative"
    secondary_metrics:
      - name: "wall_clock_time"
        direction: "minimize"
        unit: "seconds"
    protocol: "Run at 5 different timestep sizes, measure energy drift after 1000 steps"
    statistical_test: "convergence_order_fit"  # 替代固定的 paired t-test

  presentation:
    main_figure: "convergence_plot"  # log-log error vs dt
    main_table: "comparison_table"   # method × metric
```

### 6.2 条件术语映射

```yaml
# researchclaw/domains/terminology.yaml

ml_classification:
  baseline: "baseline"
  proposed: "proposed method"
  variant: "ablation"
  input: "dataset"
  metric: "accuracy/loss"

computational_physics:
  baseline: "reference solver"
  proposed: "proposed method"
  variant: "parameter variant"
  input: "initial conditions"
  metric: "error norm"

economics:
  baseline: "specification (1)"
  proposed: "full specification"
  variant: "robustness check"
  input: "sample"
  metric: "coefficient estimate"

biology:
  baseline: "standard pipeline"
  proposed: "proposed method"
  variant: "sensitivity analysis"
  input: "dataset"
  metric: "ARI / DEG count"
```

---

## 7. 实施计划

### Phase 1: 基础设施 (2-3 周)

**目标**：不破坏现有功能的情况下，建立跨领域架构骨架。

| Task | 文件 | 工作量 | 优先级 |
|------|------|--------|--------|
| 1.1 Domain Profile 数据结构 + ML adapter | `domains/detector.py`, `domains/profiles/` | 3天 | P0 |
| 1.2 PromptAdapter 接口 + ML adapter (封装现有) | `domains/prompt_adapter.py` | 3天 | P0 |
| 1.3 统一实验设计 Schema | `domains/experiment_schema.py` | 2天 | P0 |
| 1.4 UniversalMetricParser (JSON + CSV + stdout) | `experiment/metrics.py` | 2天 | P0 |
| 1.5 测试：确保 ML 领域行为不变 | `tests/test_domain_adapter.py` | 2天 | P0 |

**关键原则**：现有 ML 路径必须零回归。所有新代码走 adapter 模式。

### Phase 2: Code Searcher (2-3 周)

**目标**：实现 GitHub 搜索 + 参考代码提取。

| Task | 文件 | 工作量 | 优先级 |
|------|------|--------|--------|
| 2.1 GitHub API 客户端 (repo + code search) | `agents/code_searcher/github_client.py` | 3天 | P0 |
| 2.2 搜索 query 生成 (LLM) | `agents/code_searcher/query_gen.py` | 2天 | P0 |
| 2.3 参考代码分析 (LLM 提取 patterns) | `agents/code_searcher/pattern_extractor.py` | 3天 | P0 |
| 2.4 搜索结果缓存 | `agents/code_searcher/cache.py` | 1天 | P1 |
| 2.5 集成到 Blueprint 生成流程 | `pipeline/code_agent.py` | 2天 | P0 |
| 2.6 测试 | `tests/test_code_searcher.py` | 2天 | P0 |

### Phase 3: 第一个非 ML 领域 (2 周)

**推荐先做：计算物理 / 计算数学**（原因：依赖简单、LLM 知识充足、评估清晰）

| Task | 文件 | 工作量 | 优先级 |
|------|------|--------|--------|
| 3.1 physics_simulation.yaml 领域配置 | `domains/profiles/` | 1天 | P0 |
| 3.2 物理领域 PromptAdapter | `domains/adapters/physics.py` | 3天 | P0 |
| 3.3 物理领域 Docker 镜像 | `docker/Dockerfile.physics` | 1天 | P0 |
| 3.4 convergence study 评估逻辑 | `experiment/evaluators/convergence.py` | 2天 | P0 |
| 3.5 端到端测试 (PDE solver 主题) | 测试脚本 | 3天 | P0 |

### Phase 4: 更多领域 (每个领域 1-2 周)

按优先级：
1. 计算化学 (RDKit + PySCF, 依赖栈相对独立)
2. 经济学 (statsmodels, 评估范式最不同)
3. 生物信息学 (scanpy, 数据格式最不同)
4. 安全研究 (sklearn, 相对简单)
5. 机器人/控制 (gymnasium, 与 RL 有重叠)

### Phase 5: 高级功能 (持续迭代)

- 混合领域支持 (e.g., physics-informed neural networks)
- 代码搜索结果的向量化缓存
- 自动 Docker 镜像构建 (按需安装依赖)
- Multi-language 支持 (R, Julia)
- 论文写作的领域适配

---

## 8. 关键架构决策

### 8.1 Adapter 模式 vs 全面重写

**选择：Adapter 模式**

理由：
- 现有 ML 路径已经经过多轮测试和修复，不应破坏
- 每个领域的差异主要在 prompt、评估、和依赖栈，核心流程（Blueprint → 生成 → 验证 → 修复）是通用的
- Adapter 模式允许渐进式添加新领域，无需一次性重构

### 8.2 GitHub Search vs 向量数据库

**选择：先 GitHub Search，后加向量数据库**

理由：
- GitHub Search 零基础设施成本，只需要一个 token
- 向量数据库需要 embedding 模型 + 存储，增加复杂度
- 首先验证"搜索 → 参考 → 生成"的模式是否有效，再优化搜索质量

### 8.3 多 Docker 镜像 vs 单镜像 + pip install

**选择：多镜像 (按领域分)**

理由：
- 部分库（RDKit, MuJoCo）安装复杂，pip install 不可靠
- 预装依赖可以节省实验启动时间
- 不同领域的基础依赖可能冲突（如 JAX vs PyTorch 版本）
- 但需要一个 generic 镜像作为 fallback（pip install everything at runtime）

### 8.4 固定领域列表 vs LLM 自动适配

**选择：固定列表 + LLM fallback**

理由：
- 8-10 个领域覆盖 90%+ 的计算科研
- 固定列表保证质量（每个领域的 adapter 都经过测试）
- LLM fallback 处理未知领域（使用 generic adapter + code search）
- 随着使用增加，持续扩展领域列表

---

## 9. 与 AI-Scientist-v2 的核心差异

| 维度 | AI-Scientist-v2 | 本方案 |
|------|-----------------|--------|
| **代码搜索** | 无 | GitHub Search + 缓存 |
| **领域适配** | 无（依赖 LLM 内部知识） | 领域 Profile + Prompt Adapter |
| **代码生成** | 单文件为主 | 多文件 DAG 顺序生成 (CodeAgent v2) |
| **验证** | 运行 + 自检 | AST 硬门 + 运行 + 定向修复 |
| **探索** | BFTS 树搜索 | 单路 + 修复循环 |
| **论文写作** | VLM 审图 + 重写 | 7维 AI-Scientist 评审 + 反抄袭 |

**本方案的独特优势**：
1. Code Search 让 LLM 在生成代码前有"参考资料"
2. Domain Adapter 确保不同领域的实验范式正确
3. 多文件顺序生成比单文件更适合真实科研代码
4. 硬验证门可以在运行前拦截结构性错误

**AI-Scientist-v2 的优势（我们可以借鉴）**：
1. BFTS 树搜索 → 探索多个实验方向，找到最好的
2. Semantic Scholar 集成 → 更好的文献搜索
3. VLM 审图循环 → 图表质量更高

---

## 10. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| GitHub API 限流 | 搜索失败 | 缓存 + graceful degradation |
| 新领域 Docker 镜像维护成本 | 持续投入 | 只维护高需求领域，其他用 generic |
| 领域 adapter 质量不够 | 生成代码有领域错误 | Code Search 补充 + 人工审核 |
| LLM 对小众领域知识不足 | 代码逻辑错误 | Code Search + 参考代码 |
| 过度工程化 | 开发周期过长 | Phase 1-3 先做最小可行版本 |
| ML 路径回归 | 破坏现有功能 | 完整测试覆盖 + adapter 隔离 |

---

## 11. 成功标准

### MVP (Phase 1-3 完成)
- [ ] ML 领域所有 1284 个测试继续通过
- [ ] 计算物理领域：能生成 PDE solver 代码并成功运行
- [ ] Code Searcher：能找到相关 GitHub 仓库并提取 API 用法
- [ ] 领域检测：准确率 > 90% (在 50 个主题上测试)

### V1.0 (Phase 1-4 完成)
- [ ] 支持 5+ 领域 (ML, Physics, Chemistry, Economics, Biology)
- [ ] 每个领域能端到端生成可运行的实验代码
- [ ] Code Searcher 缓存命中率 > 70% (同领域重复主题)
- [ ] 与 AI-Scientist-v2 对比：代码通过率 (run without crash) 显著提升

---

## Appendix A: 当前代码中 ML 硬编码清单

> 详见调研报告，此处列出最关键的需要改动的位置

### prompts.py (39,158 lines)
- L313-343: `compute_budget_block` — 引用 CIFAR-10/ResNet/CNN/epochs
- L369-440: `dataset_guidance_block` — torchvision/HuggingFace datasets API
- L444-475: `setup_script_guidance` — 三阶段执行假设
- L476-488: `hp_reporting_block` — HYPERPARAMETERS dict 格式
- L541-600: `rl_step_guidance_block` — RL 环境/算法/步数表
- L1701-2058: `code_generation` — torch API, loss, optimizer, model.eval()
- L2059-2170: `result_analysis` — monotonicity/ablation/degenerate 检查
- L2201-2330: `paper_draft` — 学习方法写作要求

### executor.py
- L2254-2255: Stage 9 期望 `baselines|proposed_methods|ablations` 键
- L2477-2523: 硬编码 ML 包列表
- L2617-2665: 框架检测 (PyTorch/JAX/TF) + LLM/RL 关键词
- L2757-2761: metric_direction hint (minimize/maximize 二选一)
- L4349-4395: 指标按 "condition/" 前缀分组
- L4464-4519: paired t-test 计算
- L5208-5213: 章节字数检查

### sandbox.py
- L22-30: metric regex 只匹配 `metric: float`
- L112-147: PAIRED output 格式 (paired t-test)
- L150-189: NaN/Inf 检测 hardcoded "loss" metric

### code_agent.py
- L608-627: 验证检查假设 ablation/training/metrics
- L6-8: Blueprint 假设 "tensor shapes"

### benchmark_knowledge.yaml
- 845 lines, 13 ML 子领域，0 非 ML 领域

### dataset_registry.yaml
- 162 lines, 全部 torchvision/HuggingFace datasets

---

## Appendix B: 参考资源

- [AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2) — 无模板 BFTS 探索
- [AI-Researcher](https://github.com/HKUDS/AI-Researcher) — 6-Agent 架构
- [OpenHands](https://github.com/OpenHands/OpenHands) — 事件溯源 SDK
- [SWE-agent](https://github.com/SWE-agent/SWE-agent) — ACI 设计
- [AutoCodeRover](https://github.com/AutoCodeRoverSG/auto-code-rover) — AST 导航
- [RAG for Code Survey](https://arxiv.org/abs/2510.04905) — 代码检索综述
- [GitHub REST API](https://docs.github.com/en/rest/search/search) — 搜索 API 文档
