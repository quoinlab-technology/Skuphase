"""Validate and import additional curriculum datasets.

The importer deliberately accepts the same small, portable JSON shape as the
NERDC seed file.  That lets a school add a state-board or examination-board
dataset without changing the application code.

Example::

    python -m app.scripts.ingest_curriculum --input data/lagos_scheme.json --check
    python -m app.scripts.ingest_curriculum --input data/lagos_scheme.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, Iterable

from app.scripts.seed_curriculum_postgres import seed_curriculum_from_json

REQUIRED_FIELDS = ("class_level", "subject", "term", "week", "topic")
VALID_TERMS = {"First Term", "Second Term", "Third Term"}


def validate_records(records: Iterable[dict[str, Any]], *, board: str | None = None) -> list[dict[str, Any]]:
    """Validate and normalize import rows without requiring a database."""
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(records, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"row {index}: expected an object")
        missing = [field for field in REQUIRED_FIELDS if raw.get(field) in (None, "")]
        if missing:
            raise ValueError(f"row {index}: missing {', '.join(missing)}")
        week = raw["week"]
        if isinstance(week, bool) or not isinstance(week, int) or week < 1 or week > 60:
            raise ValueError(f"row {index}: week must be an integer from 1 to 60")
        term = str(raw["term"]).strip()
        if term not in VALID_TERMS:
            raise ValueError(f"row {index}: unsupported term {term!r}")
        item = dict(raw)
        item["board"] = str(board or raw.get("board") or "NERDC").strip().upper()
        item["class_level"] = str(raw["class_level"]).strip()
        item["subject"] = str(raw["subject"]).strip()
        item["term"] = term
        item["topic"] = str(raw["topic"]).strip()
        item["subtopics"] = list(raw.get("subtopics") or [])
        normalized.append(item)
    if not normalized:
        raise ValueError("dataset must contain at least one row")
    return normalized


def load_and_validate(path: Path, *, board: str | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found at {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("dataset root must be a JSON array")
    return validate_records(payload, board=board)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Validate/import a curriculum dataset")
    parser.add_argument("--input", required=True, help="Path to a curriculum JSON array")
    parser.add_argument("--board", help="Override board code for every row")
    parser.add_argument("--check", action="store_true", help="Validate and summarize without writing")
    args = parser.parse_args()
    path = Path(args.input)
    records = load_and_validate(path, board=args.board)
    if args.check:
        print(f"Valid curriculum dataset: {len(records)} rows, board={records[0]['board']}")
        return
    # Write a normalized temporary file beside the source, then use the
    # existing idempotent PostgreSQL bulk-upsert implementation.
    normalized = path.with_suffix(path.suffix + ".normalized.tmp")
    normalized.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    try:
        await seed_curriculum_from_json(normalized)
    finally:
        normalized.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
