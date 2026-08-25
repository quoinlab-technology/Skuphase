"""Curriculum mapping models linking a school to the shared curriculum it uses."""

import uuid

from sqlalchemy import Boolean, Column, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import BaseModel


class CurriculumMapping(BaseModel):
    """School-scoped assignment to a (shared, platform-owned) curriculum.

    The corpus itself (curriculums + scheme_of_works) is global. This table is
    the ONLY school-scoped row in the curriculum domain — it records which
    official curriculum a school has selected, along with any local overrides.
    """

    __tablename__ = "curriculum_mappings"

    school_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    curriculum_id = Column(
        UUID(as_uuid=True),
        ForeignKey("curriculums.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    active = Column(Boolean, nullable=False, default=True)
    local_overrides = Column(JSONB, default=dict, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<CurriculumMapping(school_id={self.school_id}, "
            f"curriculum_id={self.curriculum_id}, active={self.active})>"
        )