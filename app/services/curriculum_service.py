"""Curriculum and Scheme of Work Query Service."""

import logging
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_

from app.models.curriculum import Curriculum, SchemeOfWork
from app.schemas.curriculum import (
    CurriculumSubjectResponse,
    SchemeOfWorkResponse,
    CurriculumSearchResult,
)

logger = logging.getLogger(__name__)


class CurriculumService:
    """Service for querying Nigerian Curriculums and Schemes of Work."""

    @staticmethod
    async def get_all_classes(db: AsyncSession, board: str = "NERDC") -> List[str]:
        """Get distinct available class levels ordered from Pre-Nursery to Primary 6."""
        stmt = (
            select(Curriculum.class_level)
            .where(Curriculum.board == board)
            .distinct()
        )
        result = await db.execute(stmt)
        raw_classes = [r[0] for r in result.fetchall()]

        # Sort logically
        order_map = {
            "Pre-Nursery": 1,
            "Nursery 1": 2,
            "Nursery 2": 3,
            "Nursery 3": 4,
            "Primary 1": 5,
            "Primary 2": 6,
            "Primary 3": 7,
            "Primary 4": 8,
            "Primary 5": 9,
            "Primary 6": 10,
            "JSS 1": 11,
            "JSS 2": 12,
            "JSS 3": 13,
            "SSS 1": 14,
            "SSS 2": 15,
            "SSS 3": 16,
        }
        return sorted(raw_classes, key=lambda c: order_map.get(c, 99))

    @staticmethod
    async def get_subjects_by_class(
        class_level: str,
        db: AsyncSession,
        board: str = "NERDC",
    ) -> List[CurriculumSubjectResponse]:
        """Get available subjects for a specific class level."""
        stmt = (
            select(Curriculum)
            .where(
                and_(
                    Curriculum.board == board,
                    Curriculum.class_level == class_level,
                )
            )
            .order_by(Curriculum.subject_name)
        )
        result = await db.execute(stmt)
        curriculums = result.scalars().all()
        return [CurriculumSubjectResponse.model_validate(c) for c in curriculums]

    @staticmethod
    async def get_terms() -> List[str]:
        """Get academic terms."""
        return ["First Term", "Second Term", "Third Term"]

    @staticmethod
    async def get_weeks_by_subject(
        class_level: str,
        subject_name: str,
        term: str,
        db: AsyncSession,
        board: str = "NERDC",
    ) -> List[SchemeOfWorkResponse]:
        """Get weekly breakdown of topics and learning objectives."""
        stmt = (
            select(SchemeOfWork)
            .join(Curriculum, SchemeOfWork.curriculum_id == Curriculum.id)
            .where(
                and_(
                    Curriculum.board == board,
                    Curriculum.class_level == class_level,
                    func.lower(Curriculum.subject_name) == subject_name.lower().strip(),
                    SchemeOfWork.term == term,
                )
            )
            .order_by(SchemeOfWork.week_number)
        )
        result = await db.execute(stmt)
        schemes = result.scalars().all()
        return [SchemeOfWorkResponse.model_validate(s) for s in schemes]

    @staticmethod
    async def get_objectives_for_weeks(
        class_level: str,
        subject_name: str,
        term: str,
        selected_weeks: List[int],
        db: AsyncSession,
        board: str = "NERDC",
    ) -> List[Dict[str, Any]]:
        """Fetch topics and learning objectives for specific selected weeks."""
        stmt = (
            select(SchemeOfWork)
            .join(Curriculum, SchemeOfWork.curriculum_id == Curriculum.id)
            .where(
                and_(
                    Curriculum.board == board,
                    Curriculum.class_level == class_level,
                    func.lower(Curriculum.subject_name) == subject_name.lower().strip(),
                    SchemeOfWork.term == term,
                    SchemeOfWork.week_number.in_(selected_weeks),
                )
            )
            .order_by(SchemeOfWork.week_number)
        )
        result = await db.execute(stmt)
        schemes = result.scalars().all()

        output = []
        for s in schemes:
            output.append({
                "week_number": s.week_number,
                "topic": s.topic,
                "subtopics": s.subtopics or [],
                "is_exam_or_break": s.is_exam_or_break,
            })
        return output

    @staticmethod
    async def search_topics(
        query: str,
        db: AsyncSession,
        class_level: Optional[str] = None,
        subject_name: Optional[str] = None,
        limit: int = 20,
    ) -> List[CurriculumSearchResult]:
        """Search topics and subtopics in the curriculum."""
        conditions = [
            or_(
                SchemeOfWork.topic.ilike(f"%{query}%"),
                func.cast(SchemeOfWork.subtopics, func.text).ilike(f"%{query}%"),
            )
        ]

        if class_level:
            conditions.append(Curriculum.class_level == class_level)
        if subject_name:
            conditions.append(func.lower(Curriculum.subject_name) == subject_name.lower().strip())

        stmt = (
            select(SchemeOfWork, Curriculum)
            .join(Curriculum, SchemeOfWork.curriculum_id == Curriculum.id)
            .where(and_(*conditions))
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.all()

        results = []
        for scheme, curr in rows:
            results.append(
                CurriculumSearchResult(
                    id=scheme.id,
                    board=curr.board,
                    class_level=curr.class_level,
                    subject_name=curr.subject_name,
                    term=scheme.term,
                    week_number=scheme.week_number,
                    topic=scheme.topic,
                    subtopics=scheme.subtopics or [],
                )
            )
        return results
