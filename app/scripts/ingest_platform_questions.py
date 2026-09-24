"""
Platform question-bank ingestion (ADMIN/OWNER tool — run locally, never exposed via API).

Loads curated past-question items from JSON into ``question_bank_items`` as
``owner_type='platform'`` rows. These form the shared few-shot corpus used by
ExamGenerator. Per owner decision D2, this script is the ONLY way platform
rows are created — school saves can never enter the shared corpus.

Input format (JSON list):
[
  {
    "subject": "Mathematics",            // canonical display name
    "grade_level": "Primary 4",
    "week_index": 3,                     // optional scheme week alignment
    "exam_type": "WAEC",                 // WAEC | NECO | common entrance | mock | internal
    "source_year": 2019,                 // optional
    "topic": "Fractions",                // optional
    "difficulty": "easy",                // easy | medium | hard (optional)
    "question_type": "multiple_choice",  // multiple_choice | short_answer | essay
    "question_text": "Which fraction equals one half?",
    "marks": 2,
    "options": ["A. 1/2", "B. 1/3", "C. 1/4", "D. 2/3"],
    "correct_answer": "A",
    "explanation": "...",                // optional
    "marking_scheme": ["..."],           // optional (list of strings)
    "sub_parts": [{"part": "a", "question": "...", "marks": 2}]  // optional
  }
]

Usage:
    python -m app.scripts.ingest_platform_questions --input questions.json
    python -m app.scripts.ingest_platform_questions --input questions.json --dry-run

Copyright policy (CP4): only ingest items you have the right to publish —
NERDC teacher-guide samples, teacher-contributed work under ToS, or original
items. Do NOT ingest verbatim WAEC/NECO papers.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

VALID_OWNER = "platform"
VALID_QUESTION_TYPES = {"multiple_choice", "short_answer", "essay"}


def validate(items: List[Dict[str, Any]]) -> List[str]:
    """Return a list of human-readable validation errors."""
    errors: List[str] = []
    for i, item in enumerate(items, start=1):
        for required in ("subject", "grade_level", "question_type", "question_text", "marks"):
            if not item.get(required):
                errors.append(f"item {i}: missing required field '{required}'")
        if item.get("question_type") not in VALID_QUESTION_TYPES:
            errors.append(
                f"item {i}: question_type must be one of {sorted(VALID_QUESTION_TYPES)}"
            )
        if item.get("question_type") == "multiple_choice":
            options = item.get("options")
            answer = item.get("correct_answer")
            if not isinstance(options, list) or len(options) < 4:
                errors.append(f"item {i}: MCQ needs >= 4 options")
            if answer not in {"A", "B", "C", "D"}:
                errors.append(f"item {i}: MCQ correct_answer must be A-D")
        marks = item.get("marks")
        if marks is not None and (not isinstance(marks, int) or marks <= 0):
            errors.append(f"item {i}: marks must be a positive integer")
    return errors


async def ingest(json_path: Path, dry_run: bool = False) -> int:
    records: List[Dict[str, Any]] = json.loads(json_path.read_text(encoding="utf-8"))
    errors = validate(records)
    if errors:
        for e in errors:
            logger.error("Validation failed: %s", e)
        raise SystemExit(f"{len(errors)} invalid item(s); nothing ingested")

    print(f"[DRY-RUN] {len(records)} valid platform items ready for ingestion"
          if dry_run else f"Ingesting {len(records)} platform items ...")
    if dry_run:
        return 0

    from uuid import uuid4

    from sqlalchemy import select
    from app.core.database import get_async_session_maker
    from app.models.curriculum import Curriculum
    from app.models.question_bank import QuestionBankItem

    session_maker = get_async_session_maker()
    now = datetime.now(timezone.utc)

    async with session_maker() as db:
        result = await db.execute(select(Curriculum))
        curriculum_map = {
            (c.class_level.lower(), c.subject_name.lower()): c.id
            for c in result.scalars()
        }

        inserted = 0
        for item in records:
            curriculum_id = curriculum_map.get(
                (item["grade_level"].lower(), item["subject"].lower())
            )
            db.add(
                QuestionBankItem(
                    id=uuid4(),
                    school_id=None,
                    owner_type=VALID_OWNER,
                    source_exam_id=None,
                    source_question_id=None,
                    created_by_user_id=None,
                    curriculum_id=curriculum_id,
                    week_index=item.get("week_index"),
                    exam_type=item.get("exam_type"),
                    source_year=item.get("source_year"),
                    subject=item["subject"],
                    grade_level=item["grade_level"],
                    topic=item.get("topic"),
                    difficulty=item.get("difficulty"),
                    question_type=item["question_type"],
                    question_text=item["question_text"],
                    marks=item["marks"],
                    options=item.get("options"),
                    correct_answer=item.get("correct_answer"),
                    explanation=item.get("explanation"),
                    marking_scheme=item.get("marking_scheme"),
                    sub_parts=item.get("sub_parts"),
                    diagram_svg=item.get("diagram_svg"),
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
            inserted += 1

        await db.commit()

    print(f"Ingested {inserted} platform-owned question bank items.")
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest platform question bank items")
    parser.add_argument("--input", required=True, help="Path to curated JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Validate only")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv()
    asyncio.run(ingest(Path(args.input), dry_run=args.dry_run))


if __name__ == "__main__":
    main()
