"""
Owner curation tool: promote/reject school-contributed question bank items.

D-NEW-1 policy: teachers and pilot testers save questions to their school bank
(``owner_type='school'``, ``review_status='pending'``). The owner reviews the
pending queue locally and explicitly promotes the good ones into the shared
platform corpus (``owner_type='platform'``, ``school_id=NULL``), where
FewShotSelector immediately picks them up for all schools.

SAFETY INVARIANT: only ``owner_type='school'`` rows can ever be promoted, and
promotion is the ONLY code path that sets platform ownership besides the
offline ``ingest_platform_questions`` script. School rows can never leak into
other schools' prompts without this explicit owner action.

Usage (local, against the live DB):
    python -m app.scripts.promote_bank_items --list-pending
    python -m app.scripts.promote_bank_items --approve <id1> <id2>
    python -m app.scripts.promote_bank_items --reject <id1>
    add --dry-run to preview without writing
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select

from app.models.question_bank import QuestionBankItem

logger = logging.getLogger(__name__)

VALID_REVIEW_STATUSES = {"pending", "approved", "rejected"}


async def list_pending() -> List[QuestionBankItem]:
    from app.core.database import get_async_session_maker

    session_maker = get_async_session_maker()
    async with session_maker() as db:
        result = await db.execute(
            select(QuestionBankItem)
            .where(
                QuestionBankItem.owner_type == "school",
                QuestionBankItem.review_status == "pending",
            )
            .order_by(QuestionBankItem.created_at.asc())
        )
        items = list(result.scalars().all())

    for item in items:
        preview = (item.question_text or "")[:90].replace("\n", " ")
        print(
            f"{item.id}  {item.subject} | {item.grade_level} | week={item.week_index} "
            f"| type={item.question_type} | {preview}"
        )
    print(f"\n{len(items)} pending item(s).")
    return items


async def _set_status(
    ids: List[uuid.UUID],
    *,
    promote: bool,
    rejected: bool,
    dry_run: bool,
) -> int:
    from app.core.database import get_async_session_maker

    if not ids:
        print("No item ids supplied.")
        return 0

    session_maker = get_async_session_maker()
    now = datetime.now(timezone.utc)
    changed = 0

    async with session_maker() as db:
        result = await db.execute(
            select(QuestionBankItem).where(QuestionBankItem.id.in_(ids))
        )
        items = list(result.scalars().all())
        found_ids = {item.id for item in items}
        missing = [str(i) for i in ids if i not in found_ids]
        if missing:
            print(f"WARNING: {len(missing)} id(s) not found: {', '.join(missing)}")

        for item in items:
            if item.owner_type != "school":
                print(
                    f"SKIP {item.id}: owner_type={item.owner_type!r} "
                    "(only school-contributed rows can be curated)"
                )
                continue
            if promote:
                print(f"PROMOTE {item.id}: {item.subject} / {item.grade_level}")
                item.owner_type = "platform"
                item.school_id = None
                item.review_status = "approved"
                item.created_by_user_id = None
            elif rejected:
                print(f"REJECT  {item.id}: {item.subject} / {item.grade_level}")
                item.review_status = "rejected"
            else:  # pragma: no cover - argparse keeps this unreachable
                continue
            item.updated_at = now
            changed += 1

        if dry_run:
            await db.rollback()
            print(f"\n[DRY-RUN] {changed} item(s) would change. Nothing written.")
        else:
            await db.commit()
            print(f"\n{changed} item(s) updated.")

    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Curate school question-bank submissions")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--list-pending", action="store_true", help="List pending school items")
    action.add_argument("--approve", nargs="+", help="Promote item ids to the platform corpus")
    action.add_argument("--reject", nargs="+", help="Mark item ids rejected")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv()

    async def _run() -> None:
        if args.list_pending:
            await list_pending()
            return
        ids = [uuid.UUID(raw) for raw in (args.approve or args.reject or [])]
        await _set_status(
            ids,
            promote=bool(args.approve),
            rejected=bool(args.reject),
            dry_run=args.dry_run,
        )

    asyncio.run(_run())


if __name__ == "__main__":
    main()

