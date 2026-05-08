"""Synthetic factor + sector return generator (default data source).

Mirrors the construction in main_risk.py so the dashboard runs without a
real `data/` loader plumbed in. Swap this for a real loader by passing a
different callable to `init_context()`.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd


SECTORS = ["Tech", "Financials", "Energy", "Healthcare", "Utilities"]
FACTORS = ["Equity", "Rates", "Credit", "Oil"]

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

FACTOR_VOLS = {"Equity": 0.011, "Rates": 0.004, "Credit": 0.006, "Oil": 0.020}
IDIOSYNCRATIC_VOL = 0.008


def build_synthetic(seed: int = 7) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2007-01-02", "2024-12-31")
    n = len(dates)
    factor_returns = pd.DataFrame(
        {f: rng.normal(0.0, FACTOR_VOLS[f], size=n) for f in FACTORS},
        index=dates,
    )

    def _shock(start: str, end: str, factor: str, daily: float) -> None:
        m = (factor_returns.index >= start) & (factor_returns.index <= end)
        factor_returns.loc[m, factor] += daily

    _shock("2008-09-15", "2009-03-31", "Equity", -0.005)
    _shock("2008-09-15", "2009-03-31", "Credit", -0.003)
    _shock("2020-02-19", "2020-03-23", "Equity", -0.012)
    _shock("2020-02-19", "2020-03-23", "Oil", -0.020)
    _shock("2022-01-03", "2022-10-14", "Rates", 0.0015)
    _shock("2022-01-03", "2022-10-14", "Equity", -0.0010)
    _shock("2023-03-08", "2023-03-15", "Credit", -0.004)
    _shock("2023-03-08", "2023-03-15", "Equity", -0.003)

    F = factor_returns.to_numpy()
    B = TRUE_BETAS.to_numpy()
    eps = rng.normal(0.0, IDIOSYNCRATIC_VOL, size=(n, len(SECTORS)))
    sector_returns = pd.DataFrame(F @ B.T + eps, index=dates, columns=SECTORS)
    return factor_returns, sector_returns
