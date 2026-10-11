"""Grant or revoke private platform-console access for an existing user.

Run this only from a trusted operator environment with the production
DATABASE_URL configured. It never accepts or prints passwords or tokens.

Examples:
    python scripts/grant_platform_membership.py admin@example.com platform_owner
    python scripts/grant_platform_membership.py support@example.com support_agent --revoke
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import func, select

from app.core.database import get_async_session_maker
from app.core.permissions import PLATFORM_ROLES
from app.models.platform import PlatformMembership
from app.models.user import User


async def grant(email: str, role: str, revoke: bool = False) -> None:
    if role not in PLATFORM_ROLES:
        allowed = ", ".join(sorted(PLATFORM_ROLES))
        raise SystemExit(f"Unknown platform role {role!r}. Allowed roles: {allowed}")

    session_maker = get_async_session_maker()
    async with session_maker() as db:
        user = await db.scalar(select(User).where(func.lower(User.email) == email.lower()))
        if user is None:
            raise SystemExit(f"No user found for {email}")

        membership = await db.scalar(
            select(PlatformMembership).where(PlatformMembership.user_id == user.id)
        )
        if membership is None:
            if revoke:
                print(f"No platform membership exists for {email}; nothing changed.")
                return
            membership = PlatformMembership(user_id=user.id, role=role, is_active=True)
            db.add(membership)
            action = "granted"
        else:
            membership.role = role
            membership.is_active = not revoke
            action = "revoked" if revoke else "updated"

        await db.commit()
        print(f"Platform access {action} for {email} ({role}).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage SkuPhase platform-console membership")
    parser.add_argument("email")
    parser.add_argument("role", choices=sorted(PLATFORM_ROLES))
    parser.add_argument("--revoke", action="store_true", help="deactivate the membership")
    args = parser.parse_args()
    asyncio.run(grant(args.email, args.role, args.revoke))


if __name__ == "__main__":
    main()
