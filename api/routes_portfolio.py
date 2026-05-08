from typing import Dict

import math
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from risk import portfolio_factor_exposure, portfolio_summary

from .deps import RiskContext, get_context
from .schemas import WeightsBody


router = APIRouter()


def _validate_sectors(weights: Dict[str, float], ctx: RiskContext) -> None:
    unknown = sorted(set(weights) - set(ctx.sectors))
    if unknown:
        raise HTTPException(status_code=400, detail=f"unknown sectors: {unknown}")


def _portfolio_returns(weights: Dict[str, float], ctx: RiskContext) -> pd.Series:
    w = pd.Series(weights).reindex(ctx.sectors).fillna(0.0)
    return ctx.sector_returns.mul(w, axis=1).sum(axis=1)


def _sanitize(d: Dict[str, float]) -> Dict[str, float]:
    """Replace NaN/inf with None so JSON encoding doesn't choke."""
    out: Dict[str, float] = {}
    for k, v in d.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            out[k] = None  # type: ignore
        else:
            out[k] = v
    return out


@router.post("/portfolio/summary")
def post_summary(
    body: WeightsBody,
    ctx: RiskContext = Depends(get_context),
):
    _validate_sectors(body.weights, ctx)
    pr = _portfolio_returns(body.weights, ctx)
    w = pd.Series(body.weights).reindex(ctx.sectors).fillna(0.0)
    summary = portfolio_summary(pr, weights=w.values)
    return _sanitize(dict(summary))


@router.post("/portfolio/exposures")
def post_exposures(
    body: WeightsBody,
    ctx: RiskContext = Depends(get_context),
):
    _validate_sectors(body.weights, ctx)
    w = pd.Series(body.weights).reindex(ctx.sectors).fillna(0.0)
    exposures = portfolio_factor_exposure(w, ctx.betas)
    return _sanitize({k: float(v) for k, v in exposures.items()})
