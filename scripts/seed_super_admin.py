"""Create or update the private SkuPhase company super-admin account.

Credentials are supplied through environment variables or command-line flags;
no password is stored in this script or printed. The account receives a
personal operations workspace plus an explicit ``platform_owner`` membership.

Example (trusted deployment environment):
    $env:SUPERADMIN_PASSWORD = "..."
    python scripts/seed_super_admin.py --email service.quoinlab@gmail.com
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from app.core.database import get_async_session_maker
from app.core.security import get_password_hash
from app.models.platform import PlatformMembership
from app.models.school import School, SchoolSettings
from app.models.user import User
from app.utils.email import normalize_email


DEFAULT_EMAIL = "service.quoinlab@gmail.com"


async def seed(email: str, password: str) -> None:
    email = normalize_email(email)
    if len(password) < 8:
        raise SystemExit("SUPERADMIN_PASSWORD must contain at least 8 characters")
    session_maker = get_async_session_maker()
    async with session_maker() as db:
        user = await db.scalar(select(User).where(func.lower(User.email) == email))
        if user is None:
            school = await db.scalar(select(School).where(func.lower(School.contact_email) == email))
            if school is None:
                school = School(name="Quoinlab Operations", contact_email=email, is_personal_workspace=True, is_active=True)
                db.add(school)
                await db.flush()
                db.add(SchoolSettings(school_id=school.id, primary_color="#006047", secondary_color="#A5C99A", primary_llm_provider="groq", fallback_llm_provider="openrouter", exam_format="nigerian"))
            user = User(school_id=school.id, email=email, full_name="Quoinlab Super Admin", hashed_password=get_password_hash(password), role="school_admin", account_type="superadmin", is_active=True, is_verified=True)
            db.add(user)
            await db.flush()
            action = "created"
        else:
            user.hashed_password = get_password_hash(password)
            user.role = "school_admin"
            user.account_type = "superadmin"
            user.is_active = True
            user.is_verified = True
            action = "updated"
        membership = await db.scalar(select(PlatformMembership).where(PlatformMembership.user_id == user.id))
        if membership is None:
            db.add(PlatformMembership(user_id=user.id, role="platform_owner", is_active=True))
        else:
            membership.role = "platform_owner"
            membership.is_active = True
        await db.commit()
        print(f"Super-admin {action}: {email} (platform_owner)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the private SkuPhase super-admin")
    parser.add_argument("--email", default=os.getenv("SUPERADMIN_EMAIL", DEFAULT_EMAIL))
    parser.add_argument("--password", default=os.getenv("SUPERADMIN_PASSWORD"))
    args = parser.parse_args()
    if not args.password:
        raise SystemExit("Provide --password or SUPERADMIN_PASSWORD in the trusted environment")
    asyncio.run(seed(args.email, args.password))


if __name__ == "__main__":
    main()
