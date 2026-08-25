"""
PostgreSQL Curriculum & Scheme of Work Seeder.
Reads the normalized NERDC dataset and populates the PostgreSQL database.

Usage:
    python -m app.scripts.seed_curriculum_postgres                     # default path
    python -m app.scripts.seed_curriculum_postgres --input path.json
    python -m app.scripts.seed_curriculum_postgres --check             # dry-run, no writes
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Any

# NOTE: app.core.database is imported LAZILY inside seed_curriculum_from_json.
# Importing it at module load requires DATABASE_URL to be configured, which
# breaks the fully-offline --check mode.

logger = logging.getLogger(__name__)

DEFAULT_INPUT = r"C:\Users\DELL\Desktop\FastStrap\pdf_process\nerdc_scheme_database.final.json"


async def _summary(records: List[Dict[str, Any]]) -> Dict[str, int]:
    """Build a counts summary grouped by (class_level, subject)."""
    from collections import Counter
    counts: Counter = Counter()
    for r in records:
        counts[(r["class_level"], r["subject"], r["term"])] += 1
    return dict(counts)


async def _print_summary(records: List[Dict[str, Any]], label: str) -> None:
    summary = await _summary(records)
    print(f"\n[{label}] {len(records)} scheme-of-work rows:")
    for (cls, subj, term), cnt in sorted(summary.items()):
        print(f"  {cls:14s} {subj:35s} {term:12s} -> {cnt} weeks")


async def seed_curriculum_from_json(json_path: Path, check_only: bool = False) -> int:
    """Load normalized NERDC dataset into PostgreSQL.

    Returns the number of new scheme-of-work week rows inserted (0 if check_only).
    """
    if not json_path.exists():
        raise FileNotFoundError(f"Dataset not found at {json_path}")

    logger.info("Reading dataset from %s ...", json_path)
    with open(json_path, "r", encoding="utf-8") as f:
        records: List[Dict[str, Any]] = json.load(f)

    logger.info("Loaded %s rows. Initializing database...", len(records))

    # Lazy imports — require a configured DATABASE_URL (and a migrated DB).
    from sqlalchemy import select
    from app.core.database import async_session_maker
    from app.models.curriculum import Curriculum, SchemeOfWork

    async with async_session_maker() as db:
        # Check existing curriculums and build an in-memory lookup.
        existing_currs = (await db.execute(select(Curriculum))).scalars().all()
        curr_map: Dict[tuple, Any] = {
            (c.board, c.class_level, c.subject_name.lower()): c.id
            for c in existing_currs
        }

        # 1. Seed Curriculums (platform-owned, shared, no school_id)
        new_curriculums = 0
        for r in records:
            key = (r["board"], r["class_level"], r["subject"].lower())
            if key not in curr_map:
                curr = Curriculum(
                    country=r.get("country", "NG"),
                    board=r["board"],
                    class_level=r["class_level"],
                    subject_name=r["subject"],
                    category=None,
                )
                db.add(curr)
                await db.flush()
                curr_map[key] = curr.id
                new_curriculums += 1

        logger.info(
            "Curriculum subjects ready. New subjects created: %s, Total: %s",
            new_curriculums,
            len(curr_map),
        )

        if check_only:
            await _print_summary(records, "DRY-RUN CHECK")
            logger.info("Check-only mode — no writes performed.")
            return 0

        # 2. Seed / upsert Scheme of Work weeks
        logger.info("Seeding scheme of work weekly records...")
        inserted_weeks = 0
        batch_size = 200

        for idx, r in enumerate(records):
            key = (r["board"], r["class_level"], r["subject"].lower())
            curr_id = curr_map[key]

            existing_week = await db.execute(
                select(SchemeOfWork).where(
                    SchemeOfWork.curriculum_id == curr_id,
                    SchemeOfWork.term == r["term"],
                    SchemeOfWork.week_number == r["week"],
                )
            )
            scheme_obj = existing_week.scalar_one_or_none()

            if scheme_obj is None:
                db.add(
                    SchemeOfWork(
                        curriculum_id=curr_id,
                        term=r["term"],
                        week_number=r["week"],
                        topic=r["topic"],
                        subtopics=r.get("subtopics", []),
                        raw_content=r.get("raw_text"),
                        is_exam_or_break=r.get("is_exam_or_break", False),
                    )
                )
                inserted_weeks += 1
            else:
                scheme_obj.topic = r["topic"]
                scheme_obj.subtopics = r.get("subtopics", [])
                scheme_obj.is_exam_or_break = r.get("is_exam_or_break", False)

            if (idx + 1) % batch_size == 0:
                await db.commit()
                logger.info("Processed %s/%s records...", idx + 1, len(records))

        await db.commit()
        logger.info(
            "Successfully seeded %s new scheme of work week records into PostgreSQL!",
            inserted_weeks,
        )
        await _print_summary(records, "SEED SUMMARY")
        return inserted_weeks


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed NERDC curriculum into PostgreSQL")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to normalized JSON")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Dry-run: validate + print summary without writing to DB",
    )
    args = parser.parse_args()

    path = Path(args.input)

    # Fully offline check: validate the data file + print a summary. No DB
    # connection, no migration requirement — useful before wiring up Postgres.
    if args.check:
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found at {path}")
        records = json.loads(path.read_text(encoding="utf-8"))
        await _print_summary(records, "DRY-RUN CHECK")
        logger.info("Check-only mode — no writes performed, no DB required.")
        return

    inserted = await seed_curriculum_from_json(path, check_only=False)
    logger.info("Done. New scheme-of-work weeks inserted: %s", inserted)


if __name__ == "__main__":
    asyncio.run(main())
