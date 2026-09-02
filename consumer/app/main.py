"""Application factory. Spec: 003-flagpole-consumer (plan §Project Structure).

Same shape as flagpole-api: create_app(settings) with its own metrics registry, settings on
app.state, and no module-level app — a module-level instance would claim the default Prometheus
registry at import time, which cost 001 an afternoon.
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from prometheus_client import CollectorRegistry
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import Settings, get_settings
from app.routers import health, page
from app.tokens import ServiceTokenSigner

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    app = FastAPI(title="flagpole-consumer", version="0.1.0")
    app.state.settings = settings
    # Signing key read here: a missing or unreadable key must stop startup, not a page load.
    app.state.signer = ServiceTokenSigner(settings)
    app.state.templates = Jinja2Templates(directory=str(TEMPLATES))

    app.include_router(page.router)
    app.include_router(health.router)

    instrumentator = Instrumentator(registry=CollectorRegistry())
    instrumentator.instrument(app).expose(app, include_in_schema=False)
    return app
