# SkuPhase API v1
# Versioned API structure for scalability and maintainability

from . import (
    auth_router,
    curriculum_router,
    exams_router,
    ops_router,
    schools_router,
    users_router,
    partner_router,
    assessment_router,
)

__all__ = [
    "auth_router",
    "curriculum_router",
    "users_router",
    "schools_router",
    "exams_router",
    "ops_router",
    "partner_router",
    "assessment_router",
]
