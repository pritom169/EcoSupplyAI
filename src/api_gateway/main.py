"""EcoSupplyAI API Gateway — central entry point for all client requests."""

from __future__ import annotations

import signal
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import make_asgi_app

from src.api_gateway.config import get_settings
from src.api_gateway.routes import analytics, chat, suppliers
from src.shared.database import close_db, init_db

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info("api_gateway.starting", host=settings.HOST, port=settings.PORT)

    # Initialise database connection pool
    await init_db()
    logger.info("api_gateway.database_ready")

    # Graceful shutdown on SIGTERM
    def _handle_signal(sig: int, _frame: object) -> None:
        logger.info("api_gateway.signal_received", signal=sig)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    yield

    # Cleanup
    await close_db()
    logger.info("api_gateway.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="EcoSupplyAI",
        description="Sustainable Supply Chain Intelligence Platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — restrict to configured origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    # RFC 7807 Problem Details error handler
    @app.exception_handler(Exception)
    async def problem_details_handler(request: Request, exc: Exception) -> JSONResponse:
        status_code = getattr(exc, "status_code", 500)
        return JSONResponse(
            status_code=status_code,
            content={
                "type": "about:blank",
                "title": type(exc).__name__,
                "status": status_code,
                "detail": str(exc),
                "instance": str(request.url),
            },
        )

    # Prometheus metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # OpenTelemetry
    FastAPIInstrumentor.instrument_app(app)

    # Routers
    app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
    app.include_router(suppliers.router, prefix="/api/v1", tags=["suppliers"])
    app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])

    @app.get("/health")
    async def health() -> dict:
        return {"status": "healthy", "service": "api-gateway"}

    @app.get("/ready")
    async def ready() -> dict:
        return {"status": "ready"}

    return app


app = create_app()