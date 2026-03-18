"""IEEE Transactions on Power Systems writing knowledge base.

Structured tips from IEEE TPWRS/TSG best practices, reviewer feedback
analysis, and accepted paper patterns. Can be loaded and injected into
prompts at runtime, allowing updates without modifying prompt YAML.
"""

from __future__ import annotations

CONFERENCE_WRITING_TIPS: dict[str, list[str]] = {
    "title": [
        "Keep it concise and descriptive, typically under 15 words",
        "Avoid generic phrases like 'A Study of...' or 'An Investigation into...'",
        "Include method name and application context",
        "Use standard abbreviations: OPF, MILP, SOCP, DER, DG, BESS, ADN",
        "Pattern: 'MethodName: Descriptive Application in Distribution Networks'",
        "Examples: 'MILP-Based Reconfiguration for Loss Minimization in Active Distribution Networks'",
    ],
    "abstract": [
        "150-250 words, no equations or citations",
        "Structure: (1) Problem importance and motivation, (2) Limitations of existing methods, "
        "(3) Proposed approach and key features, (4) Quantitative results with specific test systems, (5) Practical significance",
        "Must include specific test system names (e.g., 'IEEE 33-bus', 'IEEE 123-bus')",
        "Report improvement percentages with baseline comparison",
        "Include key metrics: losses (kW), minimum voltage (pu), solve time (s), optimality gap (%)",
    ],
    "nomenclature": [
        "REQUIRED section in IEEE TPWRS - must list all mathematical symbols",
        "Organize by categories: Sets/Indices, Parameters, Decision Variables",
        "Place immediately before Introduction",
        "Example structure: Sets (N, E, T), Parameters (P_d, V_min, R_ij), Variables (x_ij, P_ij, v_i)",
        "Include units for all physical quantities (kW, kV, pu, Ω)",
    ],
    "introduction": [
        "800-1200 words, typically 4-5 paragraphs",
        "Paragraph 1: Power system problem background and motivation (why it matters)",
        "Paragraph 2: Existing methods and their limitations (literature gap)",
        "Paragraph 3: Overview of proposed method (high-level approach)",
        "Paragraph 4: Specific contributions as 3-4 bullet points (be explicit)",
        "Final paragraph: Paper organization overview (Section II presents..., Section III formulates...)",
    ],
    "problem_formulation": [
        "Complete mathematical model with objective function and all constraints",
        "Each constraint must have physical meaning explained in text",
        "Explicitly state linearization/relaxation assumptions and their validity",
        "Include complexity analysis: number of variables, constraints, and non-zero elements",
        "Use DistFlow (Branch Flow) model for radial distribution networks",
        "Verify radial topology constraints if applicable",
        "Document Big-M values - must be derived from physical parameters, not arbitrary large numbers",
    ],
    "experiments": [
        "IEEE standard: 'Case Studies' not 'Experiments'",
        "Test system description: bus count, line data source, base values",
        "Minimum requirement: 2 different scale systems (e.g., 33-bus + 123-bus)",
        "Solver configuration: Gurobi version, time limit, MIP gap, threads",
        "Hardware/software environment: CPU, RAM, OS",
        "Comparison methods: cite original papers, use fair settings (same solver/timeout)",
        "Required result table columns: Method, Losses(kW), MinV(pu), Reduction(%), Time(s), Gap(%)",
        "Sensitivity analysis: load levels (70%/100%/130%), DG penetration (0-80%)",
    ],
    "figures": [
        "Voltage profile: bus number vs. voltage (pu), before/after optimization comparison",
        "Convergence curves: time vs. objective value and optimality gap",
        "System topology: single-line diagram showing switches and DG locations",
        "Sensitivity analysis: bar charts for parameter variations",
        "Use 3.5-inch width (single column) or 7-inch (double column)",
        "Font size 8-10pt, consistent with main text",
        "Clear labels with units, legend inside figure when possible",
    ],
    "common_rejections": [
        "Incomplete or incorrect mathematical model",
        "Testing only on small systems (must show scalability)",
        "Unfair comparison with baselines (different solvers or parameters)",
        "Missing sensitivity analysis",
        "Linearization/relaxation error not quantified",
        "Missing Nomenclature section",
        "No power flow verification of results",
        "Insufficient literature review (IEEE expects 25-50 references)",
    ],
    "references": [
        "Numbered citations: [1], [2], [3]",
        "IEEE journal abbreviations: 'IEEE Trans. Power Syst.' not full name",
        "25-50 references, majority from peer-reviewed journals",
        "Prioritize recent work: 60% from last 5 years",
        "Include seminal papers even if older (Baran & Wu 1989 for 33-bus)",
        "Key venues: TPWRS, TSG, TPD, EPSR, IJEPES, Applied Energy",
    ],
}


def format_writing_tips(categories: list[str] | None = None) -> str:
    """Format writing tips as a prompt-injectable string.

    Parameters
    ----------
    categories:
        Subset of tip categories to include. If *None*, include all.

    Returns
    -------
    str
        Formatted markdown-style tips block.
    """
    lines: list[str] = ["## IEEE Transactions on Power Systems Writing Best Practices"]
    cats = categories or list(CONFERENCE_WRITING_TIPS.keys())
    for cat in cats:
        tips = CONFERENCE_WRITING_TIPS.get(cat, [])
        if not tips:
            continue
        lines.append(f"\n### {cat.replace('_', ' ').title()}")
        for tip in tips:
            lines.append(f"- {tip}")
    return "\n".join(lines)
