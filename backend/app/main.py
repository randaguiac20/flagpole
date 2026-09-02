"""Application factory. Spec: 001-flagpole-api (plan §Project Structure; research R6).

Run with `uvicorn app.main:create_app --factory`.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_client import CollectorRegistry
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import Settings, get_settings
from app.db import make_engine, make_sessionmaker
from app.metrics import EVALUATIONS
from app.routers import audit, evaluate, flags, health


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Flagpole API",
        version="0.1.0",
        description="Feature flags with per-environment state and deterministic evaluation.",
    )
    app.state.settings = settings
    # Read now, not at the first request: a service issuer configured with an unreadable key is a
    # deployment mistake, and a container that refuses to start says so far more clearly than one
    # that serves errors (FR-019).
    settings.read_service_public_keys()
    app.state.engine = make_engine(settings.database_url)
    app.state.sessionmaker = make_sessionmaker(app.state.engine)

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", ()) if p != "body")
        msg = first.get("msg", "invalid")
        return JSONResponse(status_code=400, content={"detail": f"invalid input: {loc}: {msg}"})

    app.include_router(flags.router)
    app.include_router(evaluate.router)
    app.include_router(audit.router)
    app.include_router(health.router)

    # One registry per app (FR-013): no process-global state, every app gets /metrics.
    registry = CollectorRegistry()
    registry.register(EVALUATIONS)
    Instrumentator(registry=registry).instrument(app).expose(
        app, endpoint="/metrics", include_in_schema=False
    )
    return app
