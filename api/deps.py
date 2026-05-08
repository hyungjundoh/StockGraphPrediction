"""Application-wide risk context loaded once at startup.

The data source is pluggable: pass any `() -> (factor_returns, sector_returns)`
callable to `init_context()` to swap synthetic data for a real `data/` loader.
"""
from __future__ import annotations

from typing import Callable, Optional, Tuple

import pandas as pd

from risk import estimate_factor_exposures, historical_factor_shocks

from .synthetic import build_synthetic


DataLoader = Callable[[], Tuple[pd.DataFrame, pd.DataFrame]]


class RiskContext:
    """Holds factor + sector returns, fitted betas, and historical shocks."""

    def __init__(
        self,
        factor_returns: pd.DataFrame,
        sector_returns: pd.DataFrame,
    ) -> None:
        self.factor_returns = factor_returns
        self.sector_returns = sector_returns
        self.sectors: list[str] = list(sector_returns.columns)
        self.factors: list[str] = list(factor_returns.columns)
        self.betas = estimate_factor_exposures(sector_returns, factor_returns)
        self.historical_shocks = historical_factor_shocks(factor_returns)


_context: Optional[RiskContext] = None


def init_context(loader: DataLoader = build_synthetic) -> RiskContext:
    """Build the global RiskContext by calling `loader()`. Idempotent."""
    global _context
    fr, sr = loader()
    _context = RiskContext(fr, sr)
    return _context


def get_context() -> RiskContext:
    """FastAPI dependency: returns the cached RiskContext (lazy-init)."""
    if _context is None:
        init_context()
    assert _context is not None
    return _context
