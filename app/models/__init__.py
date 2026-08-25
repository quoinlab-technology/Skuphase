"""Database models package."""

from app.models.base import BaseModel
from app.models.school import School, SchoolSettings
from app.models.user import User
from app.models.plan import Plan, SchoolSubscription
from app.models.exam import Exam, Question, ExamContext
from app.models.document import SchoolDocument, DocumentChunk
from app.models.usage_log import UsageLog
from app.models.question import QuestionRefinement, ExamAuditComment
from app.models.proposal import ExamGenerationProposal
from app.models.quality import ExamQualitySnapshot
from app.models.question_bank import QuestionBankItem
from app.models.asset import LearningAsset, DocumentVisualRef, QuestionAssetRef
from app.models.curriculum import Curriculum, SchemeOfWork
from app.models.curriculum_mapping import CurriculumMapping

__all__ = [
    "BaseModel",
    "School",
    "SchoolSettings",
    "User",
    "Plan",
    "SchoolSubscription",
    "Exam",
    "Question",
    "ExamContext",
    "SchoolDocument",
    "DocumentChunk",
    "UsageLog",
    "QuestionRefinement",
    "ExamAuditComment",
    "ExamGenerationProposal",
    "ExamQualitySnapshot",
    "QuestionBankItem",
    "LearningAsset",
    "DocumentVisualRef",
    "QuestionAssetRef",
    "Curriculum",
    "SchemeOfWork",
    "CurriculumMapping",
]
