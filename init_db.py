"""Initialize database with migrations and default plans."""

import asyncio
import subprocess
import sys
from uuid import uuid4

from app.core.database import async_session_maker
from app.models import Plan


def run_migrations() -> None:
    """Apply Alembic migrations to the latest revision."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Failed to apply migrations:")
        print(result.stderr or result.stdout)
        raise SystemExit(1)
    print("Migrations applied successfully")


async def init_default_plans() -> None:
    """Create default subscription plans if absent."""
    async with async_session_maker() as session:
        from sqlalchemy import select

        result = await session.execute(select(Plan))
        if result.scalars().all():
            print("Plans already exist, skipping seed")
            return

        free_plan = Plan(
            id=uuid4(),
            name="Free",
            description="Free tier for testing",
            price_ngn=0,
            max_exams_per_month=5,
            max_refinements_per_month=10,
            max_exports_per_month=5,
            max_documents_per_month=3,
            max_embedding_tokens_per_month=10000,
            max_llm_tokens_per_month=50000,
            allow_custom_templates=False,
            allow_multiple_admins=False,
            allow_api_access=False,
        )

        pro_plan = Plan(
            id=uuid4(),
            name="Professional",
            description="Professional tier with extended limits",
            price_ngn=5000,
            max_exams_per_month=100,
            max_refinements_per_month=200,
            max_exports_per_month=100,
            max_documents_per_month=50,
            max_embedding_tokens_per_month=500000,
            max_llm_tokens_per_month=2000000,
            allow_custom_templates=True,
            allow_multiple_admins=True,
            allow_api_access=True,
        )

        enterprise_plan = Plan(
            id=uuid4(),
            name="Enterprise",
            description="Enterprise tier with unlimited access",
            price_ngn=20000,
            max_exams_per_month=999999,
            max_refinements_per_month=999999,
            max_exports_per_month=999999,
            max_documents_per_month=999999,
            max_embedding_tokens_per_month=999999999,
            max_llm_tokens_per_month=999999999,
            allow_custom_templates=True,
            allow_multiple_admins=True,
            allow_api_access=True,
        )

        session.add(free_plan)
        session.add(pro_plan)
        session.add(enterprise_plan)
        await session.commit()

        print("Default plans created:")
        print(f"  Free: {free_plan.id}")
        print(f"  Professional: {pro_plan.id}")
        print(f"  Enterprise: {enterprise_plan.id}")


async def main() -> None:
    print("Initializing SkuPhase database (migration-first)...")
    run_migrations()
    await init_default_plans()
    print("Database initialization complete")


if __name__ == "__main__":
    asyncio.run(main())
