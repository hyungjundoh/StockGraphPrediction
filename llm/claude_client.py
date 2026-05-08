"""Minimal Anthropic SDK wrapper.

The wrapper is intentionally thin: business logic stays in `llm/reports.py`,
and this module just deals with auth, request shape, and JSON extraction.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

DEFAULT_MODEL = "claude-sonnet-4-6"


def _extract_json(text: str) -> Any:
    """Pull the first JSON object/array out of a model response.

    Handles plain JSON, ```json fenced blocks, and stray prose around the
    JSON. Raises ValueError if nothing parseable is found.
    """
    if text is None:
        raise ValueError("empty response from model")

    fence = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    if fence:
        candidate = fence.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fall back: find the largest balanced {...} or [...] block.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            chunk = text[start : end + 1]
            try:
                return json.loads(chunk)
            except json.JSONDecodeError:
                continue

    raise ValueError(f"could not extract JSON from model output:\n{text[:500]}")


class ClaudeClient:
    """Thin convenience wrapper around `anthropic.Anthropic`."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        max_tokens: int = 2000,
    ):
        try:
            import anthropic  # imported lazily so the rest of the package works without it
        except ImportError as e:
            raise ImportError(
                "anthropic SDK not installed. `pip install anthropic` "
                "or `pip install -r requirements-risk.txt`."
            ) from e

        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set. Export it or pass api_key= explicitly."
            )

        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=key)
        self.model = model
        self.max_tokens = max_tokens

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.2,
    ) -> str:
        """Single-turn text completion. Returns the assistant text."""
        kwargs = dict(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system
        msg = self.client.messages.create(**kwargs)
        # `content` is a list of blocks; collect any text blocks.
        parts = []
        for block in msg.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "".join(parts)

    def complete_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0,
    ) -> Any:
        """Like `complete`, but parse the response as JSON."""
        text = self.complete(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return _extract_json(text)
