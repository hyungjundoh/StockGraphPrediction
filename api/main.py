"""FastAPI app entrypoint.

Run via:
    uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .deps import init_context
from . import routes_llm, routes_portfolio, routes_stress, routes_universe


def llm_enabled() -> bool:
    return os.environ.get("ENABLE_LLM", "").lower() in ("1", "true", "yes", "on")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_context()  # build factor model once at startup
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Risk Dashboard API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(routes_universe.router)
    app.include_router(routes_portfolio.router)
    app.include_router(routes_stress.router)
    app.include_router(routes_llm.router)

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/capabilities")
    def capabilities():
        return {"llm_enabled": llm_enabled()}

    return app


app = create_app()
