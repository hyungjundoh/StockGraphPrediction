from typing import Dict

import math
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from risk import apply_shock, run_stress_tests

from .deps import RiskContext, get_context
from .schemas import HypotheticalShockBody, WeightsBody


router = APIRouter()


def _validate_sectors(weights: Dict[str, float], ctx: RiskContext) -> None:
    unknown = sorted(set(weights) - set(ctx.sectors))
    if unknown:
        raise HTTPException(status_code=400, detail=f"unknown sectors: {unknown}")


def _validate_factors(shocks: Dict[str, float], ctx: RiskContext) -> None:
    unknown = sorted(set(shocks) - set(ctx.factors))
    if unknown:
        raise HTTPException(status_code=400, detail=f"unknown factors: {unknown}")


def _safe(v: float):
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


@router.post("/stress/historical")
def post_historical(
    body: WeightsBody,
    ctx: RiskContext = Depends(get_context),
):
    _validate_sectors(body.weights, ctx)
    w = pd.Series(body.weights).reindex(ctx.sectors).fillna(0.0)
    impacts = run_stress_tests(w, ctx.betas, ctx.historical_shocks)
    return {k: _safe(float(v)) for k, v in impacts.items()}


@router.post("/stress/hypothetical")
def post_hypothetical(
    body: HypotheticalShockBody,
    ctx: RiskContext = Depends(get_context),
):
    _validate_sectors(body.weights, ctx)
    _validate_factors(body.shocks, ctx)
    w = pd.Series(body.weights).reindex(ctx.sectors).fillna(0.0)
    s = pd.Series(body.shocks).reindex(ctx.factors).fillna(0.0)
    impact = apply_shock(w, ctx.betas, s)
    return {"impact": _safe(float(impact))}
