"""Main FastAPI application entry point."""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1 import (
    assets_router,
    auth_router,
    curriculum_router,
    documents_router,
    exams_router,
    ops_router,
    rag_router,
    schools_router,
    users_router,
)
from app.config.settings import get_settings
from app.core.database import init_db, close_db
from app.core.request_context import RequestIdFilter, set_request_id

settings = get_settings()
 
# Setup logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s",
)
for handler in logging.getLogger().handlers:
    handler.addFilter(RequestIdFilter())

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for app startup and shutdown."""
    # Startup
    logger.info("Starting SkuPhase application...")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down SkuPhase application...")
    await close_db()
    logger.info("Database connection closed")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered exam generation platform for Nigerian schools",
    docs_url="/docs" if settings.enable_swagger else None,
    redoc_url="/redoc" if settings.enable_swagger else None,
    openapi_url="/openapi.json" if settings.enable_swagger else None,
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# Trusted Host Middleware
if settings.app_env == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["skuphase.com", "www.skuphase.com"],
    )


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Inject request IDs and emit structured request completion logs."""
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    set_request_id(request_id)
    started = time.perf_counter()

    response = await call_next(request)

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["x-request-id"] = request_id
    logger.info(
        "event=request_completed method=%s path=%s status_code=%s duration_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(curriculum_router.router, prefix="/api/v1/curriculum", tags=["Curriculum"])
app.include_router(users_router.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(schools_router.router, prefix="/api/v1/schools", tags=["Schools"])
app.include_router(documents_router.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(rag_router.router, prefix="/api/v1/rag", tags=["RAG"])
app.include_router(exams_router.router, prefix="/api/v1/exams", tags=["Exams"])
app.include_router(assets_router.router, prefix="/api/v1/assets", tags=["Assets"])
app.include_router(ops_router.router, prefix="/api/v1/ops", tags=["Operations"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }



