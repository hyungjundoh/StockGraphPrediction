"""Risk-management pipeline driver — synthetic-data smoke test.

Run end-to-end on synthetic factor + sector returns so you can verify the
plumbing before plugging in real data from `data/`. The LLM steps are
gated on ANTHROPIC_API_KEY being set; without it the numeric pipeline
still runs to completion.

Usage:
    python main_risk.py
    ANTHROPIC_API_KEY=sk-... python main_risk.py        # also runs LLM steps
"""
from __future__ import annotations

import json
import os
from pprint import pprint

import numpy as np
import pandas as pd

from risk import (
    estimate_factor_exposures,
    historical_factor_shocks,
    portfolio_factor_exposure,
    portfolio_summary,
    run_stress_tests,
)


# -- synthetic data ---------------------------------------------------------

SECTORS = ["Tech", "Financials", "Energy", "Healthcare", "Utilities"]
FACTORS = ["Equity", "Rates", "Credit", "Oil"]

# "True" beta matrix used to generate sector returns from factor returns.
# rows = sectors, cols = factors. Picked to be qualitatively plausible.
TRUE_BETAS = pd.DataFrame(
    [
        [1.20, -0.30, -0.40, 0.05],   # Tech
        [1.10, -0.80, -0.90, 0.00],   # Financials
        [0.90, -0.10, -0.20, 0.80],   # Energy
        [0.60, -0.20, -0.10, -0.05],  # Healthcare
        [0.40, -0.50, -0.20, 0.00],   # Utilities
    ],
    index=SECTORS,
    columns=FACTORS,
)

FACTOR_VOLS = {  # daily stdev
    "Equity": 0.011,
    "Rates": 0.004,
    "Credit": 0.006,
    "Oil": 0.020,
}

IDIOSYNCRATIC_VOL = 0.008  # daily stdev of sector residual


def _build_synthetic_data(seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate synthetic factor and sector return histories spanning real
    scenario windows (so historical_factor_shocks has data to slice)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2007-01-02", "2024-12-31")
    n = len(dates)

    factor_data = {f: rng.normal(0.0, FACTOR_VOLS[f], size=n) for f in FACTORS}
    factor_returns = pd.DataFrame(factor_data, index=dates)

    # Inject realistic shocks during known crisis windows so stress tests
    # produce non-trivial numbers.
    def _shock(start, end, factor, daily):
        mask = (factor_returns.index >= start) & (factor_returns.index <= end)
        factor_returns.loc[mask, factor] += daily

    _shock("2008-09-15", "2009-03-31", "Equity", -0.005)
    _shock("2008-09-15", "2009-03-31", "Credit", -0.003)
    _shock("2020-02-19", "2020-03-23", "Equity", -0.012)
    _shock("2020-02-19", "2020-03-23", "Oil", -0.020)
    _shock("2022-01-03", "2022-10-14", "Rates", 0.0015)
    _shock("2022-01-03", "2022-10-14", "Equity", -0.0010)
    _shock("2023-03-08", "2023-03-15", "Credit", -0.004)
    _shock("2023-03-08", "2023-03-15", "Equity", -0.003)

    F = factor_returns.to_numpy()
    B = TRUE_BETAS.to_numpy()  # sectors x factors
    eps = rng.normal(0.0, IDIOSYNCRATIC_VOL, size=(n, len(SECTORS)))
    sector_arr = F @ B.T + eps  # n x sectors
    sector_returns = pd.DataFrame(sector_arr, index=dates, columns=SECTORS)
    return factor_returns, sector_returns


# -- pipeline ---------------------------------------------------------------

def main() -> int:
    print("=" * 70)
    print("Risk pipeline smoke test (synthetic data)")
    print("=" * 70)

    factor_returns, sector_returns = _build_synthetic_data()
    print(
        f"\nGenerated {len(factor_returns)} business days of returns "
        f"({factor_returns.index.min().date()} to {factor_returns.index.max().date()}) "
        f"across {len(SECTORS)} sectors and {len(FACTORS)} factors."
    )

    # 1. Estimate factor exposures via OLS / pinv.
    betas = estimate_factor_exposures(sector_returns, factor_returns)
    print("\nEstimated betas (sectors x factors):")
    print(betas.round(3))
    print("\nTrue betas (for reference):")
    print(TRUE_BETAS.round(3))

    # 2. Build a portfolio. Equal sector weights for the smoke test.
    weights = pd.Series(
        {"Tech": 0.30, "Financials": 0.20, "Energy": 0.15, "Healthcare": 0.20, "Utilities": 0.15}
    )
    assert np.isclose(weights.sum(), 1.0), "weights must sum to 1"

    # 3. Portfolio return series and headline metrics.
    portfolio_returns = sector_returns.mul(weights, axis=1).sum(axis=1)
    summary = portfolio_summary(portfolio_returns, weights=weights.values)
    print("\nPortfolio summary:")
    pprint({k: (round(v, 6) if isinstance(v, float) else v) for k, v in summary.items()})

    # 4. Portfolio-level factor exposures.
    exposures = portfolio_factor_exposure(weights, betas)
    print("\nPortfolio factor exposures:")
    print(exposures.round(4))

    # 5. Stress tests against canonical historical windows.
    shocks = historical_factor_shocks(factor_returns)
    print("\nHistorical factor shocks (cumulative return over each window):")
    print(shocks.round(4))

    impacts = run_stress_tests(weights, betas, shocks)
    print("\nStress test impacts (estimated portfolio return per scenario):")
    print(impacts.round(4))

    # 6. Optional: LLM scenario + briefing if API key is available.
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("\n" + "-" * 70)
        print("ANTHROPIC_API_KEY detected — running LLM steps.")
        print("-" * 70)
        try:
            from llm import ClaudeClient, generate_risk_briefing, generate_scenarios

            client = ClaudeClient()
            scenarios = generate_scenarios(
                client,
                factors=FACTORS,
                n_scenarios=3,
                horizon_days=21,
                context="US large-cap equity portfolio, current date 2026-05-08.",
            )
            print("\nLLM-generated scenarios:")
            print(json.dumps(scenarios, indent=2))

            briefing = generate_risk_briefing(
                client,
                portfolio_metrics=summary,
                factor_exposures=exposures,
                stress_results=impacts,
                portfolio_label="Synthetic 5-sector portfolio",
            )
            print("\nLLM risk briefing:\n")
            print(briefing)
        except Exception as e:  # pragma: no cover — surface, don't crash
            print(f"LLM step failed: {type(e).__name__}: {e}")
    else:
        print(
            "\n(LLM steps skipped — set ANTHROPIC_API_KEY to enable "
            "scenario generation and briefing.)"
        )

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
