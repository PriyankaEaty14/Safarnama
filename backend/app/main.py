import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.adapters.ml_adapter import UnavailableAdapter
from app.adapters.historical_demand import load_historical_demand
from app.api.historical_demand import router as historical_demand_router
from app.api.health import router as health_router
from app.api.stops import router as stops_router
from app.api.routes import router as routes_router
from app.api.crowding import router as crowding_router
from app.api.analytics import router as analytics_router
from app.api.journeys import router as journeys_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db import models  # noqa: F401 - register tables with metadata
from app.db.database import make_engine, make_session_factory
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    engine = make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(engine)
        try:
            app.state.historical_demand = load_historical_demand(settings.historical_artifact_dir, engine)
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="SAFARNAMA API", version="0.1.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.analytics = AnalyticsService(engine)
    app.state.historical_demand = None
    app.state.crowding_adapter = UnavailableAdapter()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
    )
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(stops_router, prefix="/api/v1")
    app.include_router(routes_router, prefix="/api/v1")
    app.include_router(crowding_router, prefix="/api/v1")
    app.include_router(historical_demand_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")
    app.include_router(journeys_router, prefix="/api/v1")

    @app.exception_handler(SQLAlchemyError)
    async def database_error(_request: Request, error: SQLAlchemyError):
        logger.exception("Database operation failed", exc_info=error)
        return JSONResponse(status_code=503, content={"detail": "Transit database unavailable"})

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, error: Exception):
        logger.exception("Unhandled API error", exc_info=error)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()
