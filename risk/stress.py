"""Historical and hypothetical stress tests.

A "shock" is a vector of cumulative factor returns over a scenario window.
Portfolio impact = w' B s, where w is the sector weight vector, B is the
sector x factor beta matrix, and s is the factor shock vector.
"""
from __future__ import annotations

from typing import Mapping, Tuple

import numpy as np
import pandas as pd


# Canonical historical scenario windows (start_date, end_date), inclusive.
SCENARIO_WINDOWS: Mapping[str, Tuple[str, str]] = {
    "GFC_2008": ("2008-09-01", "2009-03-31"),
    "COVID_2020": ("2020-02-19", "2020-03-23"),
    "RateHikes_2022": ("2022-01-03", "2022-10-14"),
    "SVB_2023": ("2023-03-08", "2023-03-15"),
}


def _cumulative_return(window: pd.DataFrame) -> pd.Series:
    """Compound a DataFrame of simple returns to total return per column."""
    if window.empty:
        return pd.Series(dtype=float, index=window.columns)
    return (1.0 + window).prod(axis=0) - 1.0


def historical_factor_shocks(
    factor_returns: pd.DataFrame,
    scenarios: Mapping[str, Tuple[str, str]] = SCENARIO_WINDOWS,
) -> pd.DataFrame:
    """Cumulative factor returns over each historical scenario window.

    Returns a DataFrame indexed by scenario name with columns = factors.
    Scenarios with no overlapping data are dropped (with a row of NaN).
    """
    if not isinstance(factor_returns.index, pd.DatetimeIndex):
        factor_returns = factor_returns.copy()
        factor_returns.index = pd.to_datetime(factor_returns.index)

    rows = {}
    for name, (start, end) in scenarios.items():
        window = factor_returns.loc[
            (factor_returns.index >= pd.Timestamp(start))
            & (factor_returns.index <= pd.Timestamp(end))
        ]
        if window.empty:
            rows[name] = pd.Series(np.nan, index=factor_returns.columns)
        else:
            rows[name] = _cumulative_return(window)
    return pd.DataFrame(rows).T


def apply_shock(
    weights: pd.Series,
    betas: pd.DataFrame,
    shock: pd.Series,
) -> float:
    """Estimated portfolio P&L (as a return) under a factor-shock vector.

    weights: pd.Series indexed by sector.
    betas:   DataFrame [sector x factor].
    shock:   pd.Series indexed by factor.
    """
    if not isinstance(weights, pd.Series):
        weights = pd.Series(weights)
    if not isinstance(shock, pd.Series):
        shock = pd.Series(shock)

    w = weights.reindex(betas.index).fillna(0.0).to_numpy()
    s = shock.reindex(betas.columns).fillna(0.0).to_numpy()
    B = betas.to_numpy()
    return float(w @ B @ s)


def run_stress_tests(
    weights: pd.Series,
    betas: pd.DataFrame,
    shocks: pd.DataFrame,
) -> pd.Series:
    """Apply each row of `shocks` (scenario x factor) to the portfolio.

    Returns a pd.Series of portfolio impacts indexed by scenario name.
    """
    impacts = {}
    for name, row in shocks.iterrows():
        if row.isna().all():
            impacts[name] = float("nan")
        else:
            impacts[name] = apply_shock(weights, betas, row.fillna(0.0))
    return pd.Series(impacts, name="portfolio_impact")
