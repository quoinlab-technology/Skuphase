"""SkuPhase API entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.core.database import init_db
from app.api.v1 import auth_router, users_router, schools_router
from app.api.v1 import exams_router, ops_router, curriculum_router, library_router, partner_router, assessment_router, copilot_router, lesson_plans_router
from app.core.observability import RequestCorrelationMiddleware


logging.basicConfig(level=get_settings().log_level.upper())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown: verify DB migrations, start background workers."""
    await init_db()
    logger.info("Database verification passed")

    from app.services.job_queue import start_worker, stop_worker

    await start_worker()
    logger.info("Background job worker started")

    yield

    await stop_worker()
    logger.info("Background job worker stopped")


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Curriculum-first AI exam generation for Nigerian primary schools. "
        "Coverage: Pre-Nursery to Primary 6 (JSS/SSS planned)."
    ),
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_swagger else None,
    redoc_url="/redoc" if settings.enable_swagger else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)
app.add_middleware(RequestCorrelationMiddleware)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "environment": settings.app_env, "version": settings.app_version}


# API v1 routers
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users_router.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(schools_router.router, prefix="/api/v1/schools", tags=["Schools"])
app.include_router(exams_router.router, prefix="/api/v1/exams", tags=["Exams"])
app.include_router(ops_router.router, prefix="/api/v1/ops", tags=["Operations"])
app.include_router(curriculum_router.router, prefix="/api/v1/curriculum", tags=["Curriculum"])
app.include_router(library_router.router, prefix="/api/v1/library", tags=["Library"])
app.include_router(partner_router.router, prefix="/api/v1/partner", tags=["Partner API"])
app.include_router(assessment_router.router, prefix="/api/v1/assessment", tags=["Assessment Studio"])
app.include_router(copilot_router.router, prefix="/api/v1/copilot", tags=["Teacher AI Copilot"])
app.include_router(lesson_plans_router.router, prefix="/api/v1/lesson-plans", tags=["Curriculum Delivery"])

# Frontend (FastHTML + Faststrap) — mounted LAST so /api/v1/*, /docs and
# /health keep precedence; the UI owns "/" (FRONTEND_SPEC.md §2.1).
from app.frontend.app import frontend_app  # noqa: E402

app.mount("/", frontend_app)
