"""Linear factor model: sector returns regressed on macro factor returns.

Uses numpy's pseudo-inverse for OLS — more robust than `pandas` matmul on
matrices with NaNs or near-collinear columns, which silently propagate to
NaN coefficients.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd


def estimate_factor_exposures(
    sector_returns: pd.DataFrame,
    factor_returns: pd.DataFrame,
    add_intercept: bool = True,
) -> pd.DataFrame:
    """OLS factor exposures: betas[sector, factor].

    Aligns on the inner index, drops rows with any NaN, then solves
    Y = X B via the Moore-Penrose pseudo-inverse.

    Returns a DataFrame indexed by sector, columns by factor (intercept dropped).
    """
    if not isinstance(sector_returns, pd.DataFrame):
        raise TypeError("sector_returns must be a DataFrame")
    if not isinstance(factor_returns, pd.DataFrame):
        raise TypeError("factor_returns must be a DataFrame")

    df = sector_returns.join(factor_returns, how="inner", rsuffix="_factor").dropna()
    sectors = list(sector_returns.columns)
    factors = list(factor_returns.columns)

    Y = df[sectors].to_numpy(dtype=float)
    F = df[factors].to_numpy(dtype=float)

    if add_intercept:
        X = np.column_stack([np.ones(F.shape[0]), F])
    else:
        X = F

    # B = pinv(X) @ Y. Shape: (K[+1]) x N.
    coef = np.linalg.pinv(X) @ Y
    if add_intercept:
        betas = coef[1:, :]
    else:
        betas = coef
    return pd.DataFrame(betas.T, index=sectors, columns=factors)


def estimate_factor_exposures_full(
    sector_returns: pd.DataFrame,
    factor_returns: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Same as estimate_factor_exposures but also returns alphas and residuals."""
    df = sector_returns.join(factor_returns, how="inner", rsuffix="_factor").dropna()
    sectors = list(sector_returns.columns)
    factors = list(factor_returns.columns)

    Y = df[sectors].to_numpy(dtype=float)
    F = df[factors].to_numpy(dtype=float)
    X = np.column_stack([np.ones(F.shape[0]), F])

    coef = np.linalg.pinv(X) @ Y
    alphas = pd.Series(coef[0, :], index=sectors, name="alpha")
    betas = pd.DataFrame(coef[1:, :].T, index=sectors, columns=factors)
    fitted = X @ coef
    resid = pd.DataFrame(Y - fitted, index=df.index, columns=sectors)
    return betas, alphas, resid


def portfolio_factor_exposure(
    weights: pd.Series,
    betas: pd.DataFrame,
) -> pd.Series:
    """Aggregate sector betas into portfolio-level factor exposures.

    weights: pd.Series indexed by sector.
    betas:   DataFrame indexed by sector, columns = factors.
    Returns: pd.Series indexed by factor.
    """
    if not isinstance(weights, pd.Series):
        weights = pd.Series(weights)
    aligned = weights.reindex(betas.index).fillna(0.0)
    # numpy multiplication to sidestep pandas alignment surprises.
    exposure = betas.to_numpy().T @ aligned.to_numpy()
    return pd.Series(exposure, index=betas.columns, name="factor_exposure")
