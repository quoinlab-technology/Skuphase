from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.v1.lesson_plans_router import _can_plan
from app.schemas.lesson_plan import LessonPlanCreate, LessonPlanUpdate


def test_lesson_plan_create_is_scheme_grounded_and_normalized():
    payload = LessonPlanCreate(
        curriculum_id=uuid4(),
        scheme_id=uuid4(),
        title="Introduction to fractions",
        learning_objectives=[" Add fractions ", "", "Compare denominators"],
    )
    assert payload.learning_objectives == ["Add fractions", "Compare denominators"]


def test_lesson_plan_status_is_bounded():
    with pytest.raises(ValidationError):
        LessonPlanUpdate(status="published")


def test_only_staff_roles_can_view_worksheet_answer_keys():
    assert _can_plan(SimpleNamespace(role="teacher", account_type="school_staff"))
    assert _can_plan(SimpleNamespace(role="school_admin", account_type="school_staff"))
    assert not _can_plan(SimpleNamespace(role="parent", account_type="school_staff"))
