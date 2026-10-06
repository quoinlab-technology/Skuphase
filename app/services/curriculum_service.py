"""Curriculum and Scheme of Work Query Service."""

import logging
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import String, and_, cast, func, or_, select

from app.models.curriculum import Curriculum, SchemeOfWork, SchemeOfWorkOverride
from app.schemas.curriculum import (
    CurriculumSubjectResponse,
    SchemeOfWorkDetailResponse,
    SchemeOfWorkOverrideRequest,
    SchemeOfWorkResponse,
    CurriculumSearchResult,
)

logger = logging.getLogger(__name__)


class CurriculumService:
    """Service for querying Nigerian Curriculums and Schemes of Work."""

    @staticmethod
    async def get_boards(db: AsyncSession) -> List[str]:
        """Return distinct boards, with the canonical board first."""
        result = await db.execute(
            select(Curriculum.board).where(Curriculum.board.is_not(None)).distinct()
        )
        boards = sorted({row[0] for row in result.fetchall() if row[0]})
        if "NERDC" in boards:
            boards.remove("NERDC")
            boards.insert(0, "NERDC")
        return boards

    @staticmethod
    async def get_all_classes(db: AsyncSession, board: str = "NERDC") -> List[str]:
        """Get distinct available class levels ordered by ``level_order``.

        Ordering is DATA-DRIVEN (curriculums.level_order, seeded by
        ``seed_curriculum_postgres``) so adding JSS/SSS later requires data
        only — no code change (audit D-NEW-2).
        """
        stmt = (
            select(Curriculum.class_level)
            .where(Curriculum.board == board)
            .group_by(Curriculum.class_level)
            .order_by(func.coalesce(func.min(Curriculum.level_order), 99))
        )
        result = await db.execute(stmt)
        return [r[0] for r in result.fetchall()]

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
        board: Optional[str] = None,
        limit: int = 20,
    ) -> List[CurriculumSearchResult]:
        """Search topics and subtopics in the curriculum."""
        conditions = [
            or_(
                SchemeOfWork.topic.ilike(f"%{query}%"),
                # ``func.text`` is a SQL function object, not a SQLAlchemy
                # type. Use a typed cast for PostgreSQL JSONB keyword search.
                cast(SchemeOfWork.subtopics, String).ilike(f"%{query}%"),
            )
        ]

        if class_level:
            conditions.append(Curriculum.class_level == class_level)
        if subject_name:
            conditions.append(func.lower(Curriculum.subject_name) == subject_name.lower().strip())
        if board:
            conditions.append(Curriculum.board == board)

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


# ---------------------------------------------------------------------------
# School-scoped overrides
# ---------------------------------------------------------------------------

#: Roles that may amend shared curriculum text (topic / subtopics).
CANONICAL_EDIT_ROLES = {"school_admin"}
#: Roles that may attach school-local notes and resources.
LOCAL_EDIT_ROLES = {"school_admin", "teacher"}


async def _raw_weeks(
    db: AsyncSession,
    *,
    class_level: str,
    subject_name: str,
    term: str,
    board: str,
) -> List[SchemeOfWork]:
    """Fetch seeded scheme weeks without applying any school override."""
    result = await db.execute(
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
    return list(result.scalars().all())


class CurriculumAuthoringService:
    """Create, update, and revert a school's own curriculum corrections.

    Seeded :class:`SchemeOfWork` rows are shared across every tenant, so all
    writes land in :class:`SchemeOfWorkOverride` instead. Read paths call
    :meth:`get_weeks_for_school` so lesson planning and exam generation see the
    same corrected text the teacher sees.
    """

    @staticmethod
    async def _load_overrides(
        db: AsyncSession, school_id: uuid.UUID, scheme_ids: List[uuid.UUID]
    ) -> Dict[uuid.UUID, SchemeOfWorkOverride]:
        if not scheme_ids:
            return {}
        result = await db.execute(
            select(SchemeOfWorkOverride).where(
                SchemeOfWorkOverride.school_id == school_id,
                SchemeOfWorkOverride.scheme_of_work_id.in_(scheme_ids),
            )
        )
        return {row.scheme_of_work_id: row for row in result.scalars().all()}

    @staticmethod
    def apply_overrides(
        schemes: List[SchemeOfWork],
        overrides: Dict[uuid.UUID, SchemeOfWorkOverride],
    ) -> List[SchemeOfWorkResponse]:
        """Return scheme weeks with the school's corrections merged in.

        Builds copies, so the shared ORM rows are never mutated.
        """
        merged: List[SchemeOfWorkResponse] = []
        for scheme in schemes:
            response = SchemeOfWorkResponse.model_validate(scheme)
            override = overrides.get(scheme.id)
            if override is not None:
                # Keep the shared text visible so the UI can show what changed.
                response.seeded_topic = scheme.topic
                response.has_override = True
                response.is_archived = override.is_archived
                response.teacher_notes = override.teacher_notes
                response.resources = list(override.resources or [])
                if override.topic:
                    response.topic = override.topic
                if override.subtopics is not None:
                    response.subtopics = list(override.subtopics)
            merged.append(response)
        return merged

    @staticmethod
    async def get_weeks_for_school(
        db: AsyncSession,
        *,
        school_id: uuid.UUID,
        class_level: str,
        subject_name: str,
        term: str,
        board: str = "NERDC",
    ) -> List[SchemeOfWorkResponse]:
        """Weeks with the school's overrides applied; archived weeks hidden."""
        schemes = await _raw_weeks(
            db,
            class_level=class_level,
            subject_name=subject_name,
            term=term,
            board=board,
        )
        overrides = await CurriculumAuthoringService._load_overrides(
            db, school_id, [s.id for s in schemes]
        )
        merged = CurriculumAuthoringService.apply_overrides(schemes, overrides)
        return [
            week
            for week in merged
            if not (overrides.get(week.id) and overrides[week.id].is_archived)
        ]

    @staticmethod
    async def get_detail(
        db: AsyncSession, *, school_id: uuid.UUID, scheme_id: uuid.UUID, role: str
    ) -> SchemeOfWorkDetailResponse:
        """Seeded week merged with this school's overlay, plus permission hints."""
        scheme = await db.scalar(select(SchemeOfWork).where(SchemeOfWork.id == scheme_id))
        if scheme is None:
            raise ValueError("Scheme week not found")
        override = await db.scalar(
            select(SchemeOfWorkOverride).where(
                SchemeOfWorkOverride.school_id == school_id,
                SchemeOfWorkOverride.scheme_of_work_id == scheme_id,
            )
        )
        detail = SchemeOfWorkDetailResponse(
            id=scheme.id,
            curriculum_id=scheme.curriculum_id,
            term=scheme.term,
            week_number=scheme.week_number,
            topic=scheme.topic,
            subtopics=list(scheme.subtopics or []),
            raw_content=scheme.raw_content,
            is_exam_or_break=bool(scheme.is_exam_or_break),
            seeded_topic=scheme.topic,
            seeded_subtopics=list(scheme.subtopics or []),
            has_override=override is not None,
            is_archived=bool(override.is_archived) if override else False,
            teacher_notes=override.teacher_notes if override else None,
            resources=list(override.resources or []) if override else [],
            updated_by_user_id=override.updated_by_user_id if override else None,
            can_edit_canonical=role in CANONICAL_EDIT_ROLES,
            can_edit_local=role in LOCAL_EDIT_ROLES,
        )
        if override is not None:
            if override.topic:
                detail.topic = override.topic
            if override.subtopics is not None:
                detail.subtopics = list(override.subtopics)
        return detail

    @staticmethod
    async def upsert(
        db: AsyncSession,
        *,
        school_id: uuid.UUID,
        scheme_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        payload: SchemeOfWorkOverrideRequest,
    ) -> SchemeOfWorkDetailResponse:
        """Create or update the school's override for one scheme week."""
        scheme = await db.scalar(select(SchemeOfWork).where(SchemeOfWork.id == scheme_id))
        if scheme is None:
            raise ValueError("Scheme week not found")
        if role not in LOCAL_EDIT_ROLES:
            raise PermissionError("You do not have access to curriculum authoring")

        data = payload.model_dump(exclude_unset=True)
        if any(data.get(f) is not None for f in ("topic", "subtopics")) and role not in CANONICAL_EDIT_ROLES:
            raise PermissionError(
                "Only a school administrator can correct shared curriculum text"
            )

        override = await db.scalar(
            select(SchemeOfWorkOverride).where(
                SchemeOfWorkOverride.school_id == school_id,
                SchemeOfWorkOverride.scheme_of_work_id == scheme_id,
            )
        )
        if override is None:
            override = SchemeOfWorkOverride(
                school_id=school_id,
                scheme_of_work_id=scheme_id,
                created_by_user_id=user_id,
            )
            db.add(override)

        if "topic" in data:
            override.topic = data["topic"]
        if "subtopics" in data:
            override.subtopics = data["subtopics"]
        if "teacher_notes" in data:
            override.teacher_notes = data["teacher_notes"]
        if "resources" in data:
            override.resources = data["resources"]
        if "is_archived" in data:
            if role not in CANONICAL_EDIT_ROLES:
                raise PermissionError("Only a school administrator can archive or restore a week")
            override.is_archived = bool(data["is_archived"])

        override.updated_by_user_id = user_id
        await db.commit()
        await db.refresh(override)
        return await CurriculumAuthoringService.get_detail(
            db, school_id=school_id, scheme_id=scheme_id, role=role
        )

    @staticmethod
    async def revert(
        db: AsyncSession, *, school_id: uuid.UUID, scheme_id: uuid.UUID, role: str
    ) -> SchemeOfWorkDetailResponse:
        """Drop the school's override, restoring the seeded text."""
        if role not in LOCAL_EDIT_ROLES:
            raise PermissionError("You do not have access to curriculum authoring")
        override = await db.scalar(
            select(SchemeOfWorkOverride).where(
                SchemeOfWorkOverride.school_id == school_id,
                SchemeOfWorkOverride.scheme_of_work_id == scheme_id,
            )
        )
        if override is None:
            raise ValueError("This week has no school corrections to revert")
        if role not in CANONICAL_EDIT_ROLES and (override.topic is not None or override.subtopics is not None or override.is_archived):
            raise PermissionError("Only a school administrator can revert canonical curriculum corrections")
        await db.delete(override)
        await db.commit()
        return await CurriculumAuthoringService.get_detail(
            db, school_id=school_id, scheme_id=scheme_id, role=role
        )
