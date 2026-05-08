"""Pydantic request / response schemas."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


WEIGHT_TOLERANCE = 0.01


class WeightsBody(BaseModel):
    """Body containing portfolio weights keyed by sector name."""

    weights: Dict[str, float]

    @model_validator(mode="after")
    def _check_sum(self) -> "WeightsBody":
        if not self.weights:
            raise ValueError("weights must not be empty")
        s = sum(self.weights.values())
        if abs(s - 1.0) > WEIGHT_TOLERANCE:
            raise ValueError(
                f"weights must sum to ~1.0 (got {s:.4f}, tolerance {WEIGHT_TOLERANCE})"
            )
        return self


class HypotheticalShockBody(WeightsBody):
    """Weights + a vector of factor-level shocks (decimal returns)."""

    shocks: Dict[str, float]


class ScenarioRequest(BaseModel):
    macro_context: str = ""
    n_scenarios: int = Field(3, ge=1, le=10)


class BriefingRequest(BaseModel):
    summary: Dict[str, float]
    exposures: Dict[str, float]
    stress_results: Dict[str, float]
    macro_context: Optional[str] = None


class UniverseResponse(BaseModel):
    sectors: List[str]
    factors: List[str]
