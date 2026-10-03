"""Database models package."""

from app.models.base import BaseModel
from app.models.school import School, SchoolSettings
from app.models.user import User
from app.models.plan import Plan, SchoolSubscription
from app.models.exam import Exam, Question, ExamPassage
from app.models.usage_log import UsageLog
from app.models.question import QuestionRefinement, ExamAuditComment
from app.models.proposal import ExamGenerationProposal
from app.models.quality import ExamQualitySnapshot
from app.models.question_bank import QuestionBankItem
from app.models.curriculum import Curriculum, SchemeOfWork
from app.models.curriculum_mapping import CurriculumMapping
from app.models.job import GenerationJob
from app.models.login_attempt import LoginAttempt
from app.models.api_key import ApiKey
from app.models.lesson_plan import LessonPlan

__all__ = [
    "BaseModel",
    "School",
    "SchoolSettings",
    "User",
    "Plan",
    "SchoolSubscription",
    "Exam",
    "Question",
    "ExamPassage",
    "UsageLog",
    "QuestionRefinement",
    "ExamAuditComment",
    "ExamGenerationProposal",
    "ExamQualitySnapshot",
    "QuestionBankItem",
    "Curriculum",
    "SchemeOfWork",
    "CurriculumMapping",
    "GenerationJob",
    "LoginAttempt",
    "ApiKey",
    "LessonPlan",
]
