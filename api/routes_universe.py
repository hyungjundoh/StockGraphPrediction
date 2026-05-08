from fastapi import APIRouter, Depends

from .deps import RiskContext, get_context
from .schemas import UniverseResponse


router = APIRouter()


@router.get("/universe", response_model=UniverseResponse)
def get_universe(ctx: RiskContext = Depends(get_context)) -> UniverseResponse:
    return UniverseResponse(sectors=ctx.sectors, factors=ctx.factors)
