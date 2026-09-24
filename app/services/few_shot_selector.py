"""SQL-first few-shot selector for past-question examples.

Retrieves K relevant ``question_bank_items`` for exam generation using pure
indexed SQL lookups — no vector search required:

    WHERE lower(subject) = :subject AND lower(grade_level) = :grade_level
      AND owner_type = 'platform' AND is_active

then ranked in-app by:
    1. exact ``week_index`` match against the selected scheme-of-work weeks,
    2. exam provenance quality (WAEC/NECO > mock > internal),
    3. recency (source_year DESC),

and finally passed through a light token-overlap diversity pass so we never
return K near-identical questions.

Design rationale: candidates per (subject, class) are tiny (tens), so an
in-app re-rank is sub-millisecond; pgvector adds cost/latency with zero recall
benefit at this grain.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Set
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question_bank import QuestionBankItem

logger = logging.getLogger(__name__)

# Higher = preferred in ordering (exam provenance quality).
EXAM_TYPE_PRIORITY = {
    "waec": 3,
    "neco": 3,
    "bece": 2,
    "mock": 2,
    "internal": 1,
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> Set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


def _to_dict(item: QuestionBankItem) -> Dict:
    source_bits = [
        b for b in [(item.exam_type or "").upper(), str(item.source_year or "")] if b
    ]
    return {
        "id": str(item.id),
        "question_text": item.question_text,
        "question_type": item.question_type,
        "marks": item.marks,
        "options": item.options,
        "correct_answer": item.correct_answer,
        "topic": item.topic,
        "exam_type": item.exam_type,
        "source_year": item.source_year,
        "source_tag": " ".join(source_bits) or "Question Bank",
        "week_index": item.week_index,
        "diagram_svg": item.diagram_svg,
    }


class FewShotSelector:
    """Selects K diverse past-question examples for prompt injection."""

    def __init__(self, k: int = 6):
        self.k = k

    async def select(
        self,
        db: AsyncSession,
        subject: str,
        grade_level: str,
        week_indices: Optional[List[int]] = None,
        curriculum_id: Optional[UUID] = None,
        term: Optional[str] = None,
        k: Optional[int] = None,
        diversity: bool = True,
    ) -> List[Dict]:
        """Return up to K question-bank dicts matching subject/class/weeks.

        Args:
            db: Async database session.
            subject: Subject name (matched case-insensitively).
            grade_level: Class level e.g. "Primary 4".
            week_indices: Preferred scheme-of-work weeks (ranking boost).
            curriculum_id: Alternative alignment filter (unused for ranking).
            term: Reserved for future term-aware ranking.
            k: Override instance default number of examples.
            diversity: Apply token-overlap diversity pass.

        Returns:
            List of dicts (see ``_to_dict``).
        """
        limit = k or self.k

        conditions = [
            func.lower(QuestionBankItem.subject) == subject.lower().strip(),
            func.lower(QuestionBankItem.grade_level) == grade_level.lower().strip(),
            QuestionBankItem.owner_type == "platform",
            QuestionBankItem.is_active.is_(True),
        ]
        if curriculum_id and not week_indices:
            conditions.append(QuestionBankItem.curriculum_id == curriculum_id)

        stmt = select(QuestionBankItem).where(and_(*conditions)).limit(200)
        result = await db.execute(stmt)
        items: List[QuestionBankItem] = list(result.scalars().all())

        if not items:
            logger.info(
                "FewShotSelector: no bank items for %s %s weeks=%s",
                subject,
                grade_level,
                week_indices,
            )
            return []

        # Rank: exact week match first, then exam provenance, then recency.
        wanted_weeks = set(week_indices or [])

        def _rank(item: QuestionBankItem) -> tuple:
            week_match = 1 if (wanted_weeks and item.week_index in wanted_weeks) else 0
            type_priority = EXAM_TYPE_PRIORITY.get((item.exam_type or "").lower(), 0)
            year = item.source_year or 0
            return (week_match, type_priority, year)

        ranked = sorted(items, key=_rank, reverse=True)

        if diversity and len(ranked) > limit:
            selected: List[QuestionBankItem] = []
            selected_tokens: List[Set[str]] = []
            for item in ranked:
                toks = _tokens(item.question_text)
                redundant = any(
                    len(toks & prev) / max(len(toks | prev), 1) > 0.6
                    for prev in selected_tokens
                )
                if redundant:
                    continue
                selected.append(item)
                selected_tokens.append(toks)
                if len(selected) >= limit:
                    break
            # Fall back only if diversity rejected everything (should not
            # happen - the first candidate always survives); otherwise keep
            # the smaller, diverse set. Fewer-but-varied beats padding with
            # near-identical examples.
            if not selected:
                selected = ranked[:limit]
        else:
            selected = ranked[:limit]

        return [_to_dict(item) for item in selected]