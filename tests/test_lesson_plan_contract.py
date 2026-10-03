from uuid import uuid4

import pytest
from pydantic import ValidationError

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
