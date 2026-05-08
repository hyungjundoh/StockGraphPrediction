"""LLM endpoints: scenario JSON + streamed prose briefing.

The wider `llm/` package is consumed read-only. For streaming the briefing
we call the Anthropic SDK directly (the existing `ClaudeClient.complete()`
is non-streaming and we're not allowed to touch llm/), but reuse the
BRIEFING_SYSTEM prompt constant to keep the behavioural guardrails (no
trade recommendations) in one place.
"""
from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from .deps import RiskContext, get_context
from .schemas import BriefingRequest, ScenarioRequest


router = APIRouter()


def _require_enabled() -> None:
    from .main import llm_enabled

    if not llm_enabled():
        raise HTTPException(status_code=404, detail="Not Found")


@router.post("/llm/scenarios")
def post_scenarios(
    body: ScenarioRequest,
    ctx: RiskContext = Depends(get_context),
):
    _require_enabled()
    from llm import ClaudeClient, generate_scenarios  # lazy import

    try:
        client = ClaudeClient()
        return generate_scenarios(
            client,
            factors=ctx.factors,
            n_scenarios=body.n_scenarios,
            context=body.macro_context,
        )
    except Exception as e:  # surface upstream errors as 502
        raise HTTPException(status_code=502, detail=f"LLM error: {e!s}") from e


def _format_kv(d: Dict[str, float]) -> str:
    parts = []
    for k, v in d.items():
        if v is None:
            parts.append(f"  {k}: n/a")
        elif isinstance(v, float):
            parts.append(f"  {k}: {v:.6g}")
        else:
            parts.append(f"  {k}: {v}")
    return "\n".join(parts)


@router.post("/llm/briefing")
def post_briefing(body: BriefingRequest):
    _require_enabled()
    # Lazy imports so the module loads even without anthropic installed.
    import anthropic
    from llm.reports import BRIEFING_SYSTEM

    user_prompt = (
        "Risk snapshot. All numbers below are pre-computed; do not recompute.\n\n"
        f"Headline metrics:\n{_format_kv(body.summary)}\n\n"
        f"Factor exposures:\n{_format_kv(body.exposures)}\n\n"
        f"Stress test impacts (return):\n{_format_kv(body.stress_results)}\n"
    )
    if body.macro_context:
        user_prompt += f"\nMacro context: {body.macro_context}\n"
    user_prompt += "\nWrite the briefing now."

    client = anthropic.Anthropic()

    def gen():
        try:
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                temperature=0.2,
                system=BRIEFING_SYSTEM,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:  # surface mid-stream errors as visible text
            yield f"\n\n[stream error: {type(e).__name__}: {e}]\n"

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")
