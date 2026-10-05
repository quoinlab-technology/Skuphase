"""
PostgreSQL Curriculum & Scheme of Work Seeder.

Reads the normalized NERDC dataset (committed at ``data/``) and populates
PostgreSQL using bulk ON CONFLICT upserts (idempotent, fast).

Usage:
    python -m app.scripts.seed_curriculum_postgres                     # default path
    python -m app.scripts.seed_curriculum_postgres --input path.json
    python -m app.scripts.seed_curriculum_postgres --check             # dry-run, no DB
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.dialects.postgresql import insert as pg_insert

logger = logging.getLogger(__name__)

DEFAULT_INPUT = Path(__file__).resolve().parents[2] / "data" / "nerdc_scheme_database.final.json"

BATCH_SIZE = 500


async def _print_summary(records: List[Dict[str, Any]], label: str) -> None:
    counts: Counter = Counter()
    for r in records:
        counts[(r["class_level"], r["subject"], r["term"])] += 1
    print(f"\n[{label}] {len(records)} scheme-of-work rows:")
    for (cls, subj, term), cnt in sorted(counts.items()):
        print(f"  {cls:14s} {subj:35s} {term:12s} -> {cnt} weeks")


def _rows(records: List[Dict[str, Any]]):
    """Build deduplicated curriculum + scheme row payloads."""
    level_order_map = {
        "Pre-Nursery": 1, "Nursery 1": 2, "Nursery 2": 3, "Nursery 3": 4,
        "Primary 1": 5, "Primary 2": 6, "Primary 3": 7, "Primary 4": 8,
        "Primary 5": 9, "Primary 6": 10,
        "JSS 1": 11, "JSS 2": 12, "JSS 3": 13,
        "SSS 1": 14, "SSS 2": 15, "SSS 3": 16,
    }
    curriculums: Dict[tuple, Dict[str, Any]] = {}
    schemes: List[Dict[str, Any]] = []
    seen_scheme_keys = set()

    for r in records:
        key = (r["board"], r["class_level"], r["subject"].lower())
        if key not in curriculums:
            curriculums[key] = {
                "country": r.get("country", "NG"),
                "board": r["board"],
                "class_level": r["class_level"],
                "subject_name": r["subject"],
                "level_order": level_order_map.get(r["class_level"], 99),
            }

        scheme_key = (key, r["term"], r["week"])
        if scheme_key in seen_scheme_keys:
            continue
        seen_scheme_keys.add(scheme_key)
        topic = r["topic"]
        if len(topic) > 255:
            # 14 legacy rows exceed varchar(255); keep them, truncated.
            logger.warning("Truncating topic longer than 255 chars (week %s)", r["week"])
            topic = topic[:255]
        schemes.append(
            {
                "board": r["board"],
                "class_level": r["class_level"],
                "subject_key": r["subject"].lower(),
                "term": r["term"],
                "week_number": r["week"],
                "topic": topic,
                # JSONB expects a Python list. Serialising here stores a JSON
                # *string* in PostgreSQL, which later breaks curriculum
                # search result validation. Keep the structured value intact.
                "subtopics": r.get("subtopics", []) or [],
                "raw_content": r.get("raw_text"),
                "is_exam_or_break": bool(r.get("is_exam_or_break", False)),
            }
        )
    return curriculums, schemes


async def seed_curriculum_from_json(json_path: Path, check_only: bool = False) -> int:
    """Load the normalized NERDC dataset into PostgreSQL via bulk upserts."""
    if not json_path.exists():
        raise FileNotFoundError(f"Dataset not found at {json_path}")

    logger.info("Reading dataset from %s ...", json_path)
    records: List[Dict[str, Any]] = json.loads(json_path.read_text(encoding="utf-8"))
    logger.info("Loaded %s rows.", len(records))

    await _print_summary(records, "DRY-RUN CHECK" if check_only else "SEED SUMMARY")
    if check_only:
        logger.info("Check-only mode — no writes performed.")
        return 0

    from sqlalchemy import select, func
    from app.core.database import get_async_session_maker
    from app.models.curriculum import Curriculum, SchemeOfWork

    curriculums, schemes = _rows(records)
    session_maker = get_async_session_maker()

    inserted_weeks = 0
    async with session_maker() as db:
        # 1. Bulk-upsert curriculums on the unique lookup index.
        curriculum_values = list(curriculums.values())
        for i in range(0, len(curriculum_values), BATCH_SIZE):
            batch = curriculum_values[i : i + BATCH_SIZE]
            stmt = (
                pg_insert(Curriculum)
                .values(batch)
                .on_conflict_do_update(
                    index_elements=["board", "class_level", "subject_name"],
                    set_={
                        "country": pg_insert(Curriculum).excluded.country,
                        "level_order": pg_insert(Curriculum).excluded.level_order,
                        "updated_at": func.now(),
                    },
                )
            )
            await db.execute(stmt)

        # Map (board, class, lower(subject)) -> curriculum_id
        result = await db.execute(select(Curriculum))
        curr_map = {
            (c.board, c.class_level, c.subject_name.lower()): c.id for c in result.scalars()
        }

        # 2. Bulk-upsert scheme weeks on the unique (curriculum_id, term, week).
        for i in range(0, len(schemes), BATCH_SIZE):
            batch = []
            for row in schemes[i : i + BATCH_SIZE]:
                row = dict(row)
                curriculum_id = curr_map[
                    (row.pop("board"), row.pop("class_level"), row.pop("subject_key"))
                ]
                row["curriculum_id"] = curriculum_id
                batch.append(row)

            stmt = (
                pg_insert(SchemeOfWork)
                .values(batch)
                .on_conflict_do_update(
                    index_elements=["curriculum_id", "term", "week_number"],
                    set_={
                        "topic": pg_insert(SchemeOfWork).excluded.topic,
                        "subtopics": pg_insert(SchemeOfWork).excluded.subtopics,
                        "raw_content": pg_insert(SchemeOfWork).excluded.raw_content,
                        "is_exam_or_break": pg_insert(SchemeOfWork).excluded.is_exam_or_break,
                        "updated_at": func.now(),
                    },
                )
            )
            await db.execute(stmt)
            inserted_weeks += len(batch)
            logger.info("Upserted %s/%s week rows...", min(i + BATCH_SIZE, len(schemes)), len(schemes))

        await db.commit()

    logger.info("Seeding complete: %s curriculum subjects, %s week rows.", len(curriculums), inserted_weeks)
    return inserted_weeks


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed NERDC curriculum into PostgreSQL")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to normalized JSON")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Dry-run: validate + print summary without writing to DB",
    )
    args = parser.parse_args()

    path = Path(args.input)

    if args.check:
        # Fully offline check: no DB connection required.
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found at {path}")
        records = json.loads(path.read_text(encoding="utf-8"))
        await _print_summary(records, "DRY-RUN CHECK")
        logger.info("Check-only mode — no writes performed, no DB required.")
        return

    inserted = await seed_curriculum_from_json(path, check_only=False)
    logger.info("Done. Week rows upserted: %s", inserted)


if __name__ == "__main__":
    import sys as _sys

    from dotenv import load_dotenv

    load_dotenv()
    asyncio.run(main())
