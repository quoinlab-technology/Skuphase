"""Role-based access helpers shared across routers.

Access model (dual-mode):
- School admins drive LLM actions for their school.
- Individual teachers (personal workspaces) drive their own LLM actions.
- School staff (teachers/auditors) use proposals and review workflows.
"""

from fastapi import Depends, HTTPException
from app.core.dependencies import get_current_user
from app.models.user import User

ROLE_TEACHER = "teacher"
ROLE_SCHOOL_ADMIN = "school_admin"
ROLE_PARENT = "parent"
ROLE_AUDITOR = "auditor"

ACCOUNT_INDIVIDUAL_TEACHER = "individual_teacher"


def is_workspace_admin(user: User) -> bool:
    """True for school admins and individual teachers managing their own workspace."""
    return user.role == ROLE_SCHOOL_ADMIN or user.account_type == ACCOUNT_INDIVIDUAL_TEACHER


def allows_llm_actions(user: User) -> bool:
    """True when the user may trigger generation/refinement/export/delete for their school."""
    return is_workspace_admin(user)


def require_llm_permission():
    """Dependency factory: allow only workspace admins (school admin or individual teacher)."""

    async def _dep(current_user: User = Depends(get_current_user)) -> User:
        if not allows_llm_actions(current_user):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only school administrators or individual teachers can perform "
                    "this action"
                ),
            )
        return current_user

    return _dep


def require_roles(*roles: str):
    """Dependency factory: allow only the given roles."""

    async def _dep(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"This action requires role: {' or '.join(roles)}",
            )
        return current_user

    return _dep


def require_workspace_admin():
    """Dependency factory alias mirroring generate/refine/export gating."""

    return require_llm_permission()
