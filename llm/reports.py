"""LLM-driven scenario generation and prose risk briefings.

Architectural rule: the LLM does no math and makes no trade decisions. It
only enumerates scenarios (as structured JSON for downstream code) and
writes prose summaries of metrics that have already been computed.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

import pandas as pd


_NO_ADVICE_CLAUSE = (
    "You MUST NOT recommend trades, hedges, rebalancing, position sizing, "
    "buy/sell/hold actions, or specific securities. You MUST NOT prescribe "
    "actions of any kind. If asked for a recommendation, decline and instead "
    "describe the risk. Your role is descriptive, not prescriptive."
)


SCENARIO_SYSTEM = (
    "You are a macro risk scenario generator for an institutional portfolio "
    "risk team. Given a list of factor names, you propose adverse but "
    "*plausible* scenarios as structured JSON shocks expressed in decimal "
    "returns over the scenario horizon (e.g. -0.20 for a 20% drop).\n\n"
    + _NO_ADVICE_CLAUSE
    + "\n\nReturn ONLY a single JSON object matching this schema:\n"
    "{\n"
    '  "scenarios": [\n'
    "    {\n"
    '      "name": "<short label>",\n'
    '      "narrative": "<2-4 sentence description of the macro story>",\n'
    '      "horizon_days": <integer>,\n'
    '      "shocks": {"<factor_name>": <decimal return>, ...}\n'
    "    }\n"
    "  ]\n"
    "}\n"
    "Every factor in the input list must appear in every scenario's shocks. "
    "Do not include any keys outside this schema."
)


BRIEFING_SYSTEM = (
    "You are a risk briefing writer for an institutional portfolio team. "
    "You translate already-computed quantitative risk metrics into clear, "
    "concise prose for a portfolio manager. You do not perform calculations; "
    "trust the numbers given. Quote figures verbatim with appropriate units "
    "(% for returns, days for horizons).\n\n"
    + _NO_ADVICE_CLAUSE
    + "\n\nStructure the briefing with short labelled sections: "
    "**Headline**, **Volatility & Tail Risk**, **Factor Exposure**, "
    "**Stress Tests**, **Concentration**. Keep the entire briefing under "
    "350 words."
)


def generate_scenarios(
    client,
    factors: Iterable[str],
    n_scenarios: int = 3,
    horizon_days: int = 21,
    context: Optional[str] = None,
) -> Any:
    """Ask Claude for `n_scenarios` adverse factor-shock scenarios.

    Returns the parsed JSON dict. Caller is responsible for validating the
    shocks before passing to risk.stress.apply_shock.
    """
    factor_list = list(factors)
    user = (
        f"Factors available: {factor_list}\n"
        f"Horizon: {horizon_days} trading days\n"
        f"Number of scenarios: {n_scenarios}\n"
    )
    if context:
        user += f"\nAdditional context:\n{context}\n"
    user += (
        "\nReturn the JSON object now. Each scenario's shocks must include "
        "every factor listed above."
    )
    return client.complete_json(prompt=user, system=SCENARIO_SYSTEM)


def _format_metrics_block(metrics: Mapping[str, float]) -> str:
    lines = []
    for k, v in metrics.items():
        if isinstance(v, float):
            lines.append(f"  {k}: {v:.6g}")
        else:
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def _format_series(label: str, s: pd.Series) -> str:
    lines = [f"{label}:"]
    for k, v in s.items():
        lines.append(f"  {k}: {float(v):.6g}")
    return "\n".join(lines)


def generate_risk_briefing(
    client,
    portfolio_metrics: Mapping[str, float],
    factor_exposures: pd.Series,
    stress_results: pd.Series,
    portfolio_label: str = "Portfolio",
) -> str:
    """Turn pre-computed numeric risk outputs into a prose briefing."""
    block_metrics = _format_metrics_block(portfolio_metrics)
    block_factors = _format_series("Factor exposures", factor_exposures)
    block_stress = _format_series("Stress test impacts (return)", stress_results)

    prompt = (
        f"{portfolio_label} risk snapshot. All numbers are pre-computed; do not "
        "recompute them.\n\n"
        f"Headline metrics:\n{block_metrics}\n\n"
        f"{block_factors}\n\n"
        f"{block_stress}\n\n"
        "Write the briefing now."
    )
    return client.complete(prompt=prompt, system=BRIEFING_SYSTEM, temperature=0.2)
