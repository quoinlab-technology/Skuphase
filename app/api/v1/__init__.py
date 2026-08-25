# SkuPhase API v1
# Versioned API structure for scalability and maintainability

from . import (
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

__all__ = [
    "auth_router",
    "assets_router",
    "curriculum_router",
    "users_router",
    "schools_router",
    "documents_router",
    "rag_router",
    "exams_router",
    "ops_router",
]
