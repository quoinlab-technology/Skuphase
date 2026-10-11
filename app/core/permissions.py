"""Role-based access helpers shared across routers.

Access model (teacher autonomy):
- School admins manage budgets, settings, staff, and oversight.
- Teachers (school_staff) fully own their teaching work: generate, refine,
  edit, approve/self-approve, export, and delete exams within their school.
- Auditors are read-only oversight (no LLM/mutation actions).
- Individual teachers (personal workspaces) drive their own LLM actions.
"""

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user
from app.core.database import get_db_session
from app.models.user import User
from app.models.platform import PlatformMembership

ROLE_TEACHER = "teacher"
ROLE_SCHOOL_ADMIN = "school_admin"
ROLE_PARENT = "parent"
ROLE_AUDITOR = "auditor"

ACCOUNT_INDIVIDUAL_TEACHER = "individual_teacher"

PLATFORM_OWNER = "platform_owner"
PLATFORM_ADMIN = "platform_admin"
PLATFORM_SUPPORT = "support_agent"
PLATFORM_ANALYST = "analyst"
PLATFORM_CONTENT_OPERATOR = "content_operator"
PLATFORM_ROLES = {
    PLATFORM_OWNER,
    PLATFORM_ADMIN,
    PLATFORM_SUPPORT,
    PLATFORM_ANALYST,
    PLATFORM_CONTENT_OPERATOR,
}


def is_workspace_admin(user: User) -> bool:
    """True for school admins and individual teachers managing their own workspace."""
    return user.role == ROLE_SCHOOL_ADMIN or user.account_type == ACCOUNT_INDIVIDUAL_TEACHER


def _role_of(user: User) -> str:
    return getattr(user, "role", None) or ""


def _account_type_of(user: User) -> str:
    return getattr(user, "account_type", None) or ""


def allows_llm_actions(user: User) -> bool:
    """True when the user may trigger generation/refinement/export/delete for their school.

    Teacher autonomy: any active school staff teacher plus workspace admins.
    Auditors/parents remain read-only.
    """
    if _account_type_of(user) == ACCOUNT_INDIVIDUAL_TEACHER:
        return True
    return _role_of(user) in {ROLE_TEACHER, ROLE_SCHOOL_ADMIN}


def can_modify_exam(user: User, exam=None) -> bool:
    """Teachers may modify exams in their school; admins may modify any school exam.

    When an exam is provided and the user is a teacher (non-admin), they may
    only modify exams they created. Admins bypass the ownership check.
    """
    if is_workspace_admin(user):
        return True
    if _role_of(user) != ROLE_TEACHER:
        return False
    if exam is None:
        return True
    creator_id = getattr(exam, "created_by_user_id", None)
    user_id = getattr(user, "user_id", None) or getattr(user, "id", None)
    if creator_id is None:
        return True
    return str(creator_id) == str(user_id)


def require_llm_permission():
    """Dependency factory: teachers and workspace admins may use LLM actions."""

    async def _dep(current_user: User = Depends(get_current_user)) -> User:
        if not allows_llm_actions(current_user):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only teachers and school administrators can perform "
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


async def get_current_platform_membership(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PlatformMembership:
    """Require an explicit active company-platform membership.

    This intentionally does not infer platform access from school ownership,
    email domain, or the user's school role.
    """
    membership = await db.scalar(
        select(PlatformMembership).where(
            PlatformMembership.user_id == current_user.user_id,
            PlatformMembership.is_active.is_(True),
        )
    )
    if membership is None or membership.role not in PLATFORM_ROLES:
        raise HTTPException(status_code=403, detail="Platform access is not enabled for this account")
    return membership


def require_platform_roles(*roles: str):
    """Dependency factory for private platform endpoints."""
    invalid = set(roles) - PLATFORM_ROLES
    if invalid:
        raise ValueError(f"Unknown platform role(s): {', '.join(sorted(invalid))}")

    async def _dep(
        membership: PlatformMembership = Depends(get_current_platform_membership),
    ) -> PlatformMembership:
        if roles and membership.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"This action requires platform role: {' or '.join(roles)}",
            )
        return membership

    return _dep


def require_workspace_admin():
    """Dependency factory alias mirroring generate/refine/export gating."""

    return require_llm_permission()
