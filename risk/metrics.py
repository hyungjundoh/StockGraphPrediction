"""Portfolio risk metrics.

Conventions:
    - `returns` is a pd.Series (or array-like) of *simple* periodic returns.
    - VaR / CVaR are returned in *loss convention*: a return of -3% becomes a
      loss of +0.03. A negative value means the tail outcome is a gain.
    - Annualization assumes 252 trading days unless overridden.
"""
from __future__ import annotations

from typing import Iterable, Mapping, Optional

import numpy as np
import pandas as pd


def _as_series(returns) -> pd.Series:
    s = pd.Series(returns).astype(float).dropna()
    return s


def value_at_risk(returns, alpha: float = 0.95, method: str = "historical") -> float:
    """One-period VaR at confidence `alpha` (e.g. 0.95 → 5% tail).

    Returned as a positive loss magnitude under typical conditions.
    """
    r = _as_series(returns)
    if len(r) == 0:
        return float("nan")
    if method == "historical":
        q = float(np.quantile(r.values, 1.0 - alpha))
    elif method == "parametric":
        from scipy.stats import norm

        mu = float(r.mean())
        sigma = float(r.std(ddof=1))
        q = mu + sigma * float(norm.ppf(1.0 - alpha))
    else:
        raise ValueError(f"unknown VaR method: {method!r}")
    return -q


def conditional_var(returns, alpha: float = 0.95) -> float:
    """CVaR / Expected Shortfall at confidence `alpha` (positive = loss)."""
    r = _as_series(returns)
    if len(r) == 0:
        return float("nan")
    threshold = float(np.quantile(r.values, 1.0 - alpha))
    tail = r[r <= threshold]
    if len(tail) == 0:
        return -threshold
    return -float(tail.mean())


def ewma_volatility(
    returns,
    lambda_: float = 0.94,
    annualize: bool = True,
    periods_per_year: int = 252,
) -> float:
    """RiskMetrics-style EWMA volatility (latest value).

    Recursion: sigma_t^2 = lambda * sigma_{t-1}^2 + (1 - lambda) * r_{t-1}^2.
    Implemented via pandas .ewm with adjust=False (equivalent form).
    """
    r = _as_series(returns)
    if len(r) == 0:
        return float("nan")
    var = r.pow(2).ewm(alpha=1.0 - lambda_, adjust=False).mean()
    sigma = float(np.sqrt(var.iloc[-1]))
    if annualize:
        sigma *= float(np.sqrt(periods_per_year))
    return sigma


def max_drawdown(returns) -> float:
    """Maximum peak-to-trough drawdown of the cumulative wealth curve.

    Returned as a positive magnitude (e.g. 0.30 for a 30% drawdown).
    """
    r = _as_series(returns)
    if len(r) == 0:
        return float("nan")
    wealth = (1.0 + r).cumprod()
    peak = wealth.cummax()
    dd = (wealth - peak) / peak
    return float(-dd.min())


def sharpe_ratio(returns, rf: float = 0.0, periods_per_year: int = 252) -> float:
    """Annualized Sharpe ratio. `rf` is an *annual* risk-free rate."""
    r = _as_series(returns)
    if len(r) < 2:
        return float("nan")
    excess = r - rf / periods_per_year
    sigma = float(excess.std(ddof=1))
    if sigma == 0 or np.isnan(sigma):
        return float("nan")
    return float(excess.mean() / sigma * np.sqrt(periods_per_year))


def sortino_ratio(
    returns,
    rf: float = 0.0,
    periods_per_year: int = 252,
    target: float = 0.0,
) -> float:
    """Annualized Sortino ratio (downside-deviation denominator)."""
    r = _as_series(returns)
    if len(r) < 2:
        return float("nan")
    excess = r - rf / periods_per_year
    downside = excess[excess < target]
    if len(downside) == 0:
        return float("nan")
    dd_std = float(np.sqrt((downside.pow(2)).mean()))
    if dd_std == 0:
        return float("nan")
    return float(excess.mean() / dd_std * np.sqrt(periods_per_year))


def calmar_ratio(returns, periods_per_year: int = 252) -> float:
    """Annualized return divided by max drawdown."""
    r = _as_series(returns)
    if len(r) == 0:
        return float("nan")
    cum = float((1.0 + r).prod())
    if cum <= 0:
        return float("nan")
    annual = cum ** (periods_per_year / len(r)) - 1.0
    mdd = max_drawdown(r)
    if not np.isfinite(mdd) or mdd == 0:
        return float("nan")
    return float(annual / mdd)


def effective_n(weights: Iterable[float]) -> float:
    """Inverse Herfindahl: 1 / sum(w_i^2). Measures effective # of holdings."""
    w = np.asarray(list(weights), dtype=float)
    w = w[~np.isnan(w)]
    s = float((w ** 2).sum())
    if s == 0:
        return float("nan")
    return 1.0 / s


def portfolio_summary(
    returns,
    weights: Optional[Iterable[float]] = None,
    alpha: float = 0.95,
    periods_per_year: int = 252,
    rf: float = 0.0,
) -> Mapping[str, float]:
    """Bundle of headline metrics for a portfolio return series."""
    r = _as_series(returns)
    out: dict = {
        "n_obs": int(len(r)),
        "mean_return": float(r.mean()) if len(r) else float("nan"),
        "vol_annualized": (
            float(r.std(ddof=1) * np.sqrt(periods_per_year)) if len(r) > 1 else float("nan")
        ),
        "ewma_vol_annualized": ewma_volatility(r, periods_per_year=periods_per_year),
        f"var_{int(alpha*100)}": value_at_risk(r, alpha=alpha),
        f"cvar_{int(alpha*100)}": conditional_var(r, alpha=alpha),
        "max_drawdown": max_drawdown(r),
        "sharpe": sharpe_ratio(r, rf=rf, periods_per_year=periods_per_year),
        "sortino": sortino_ratio(r, rf=rf, periods_per_year=periods_per_year),
        "calmar": calmar_ratio(r, periods_per_year=periods_per_year),
    }
    if weights is not None:
        w = np.asarray(list(weights), dtype=float)
        out["effective_n"] = effective_n(w)
        out["n_assets"] = int(np.sum(np.abs(w) > 0))
        out["max_weight"] = float(np.max(np.abs(w))) if w.size else float("nan")
    return out
