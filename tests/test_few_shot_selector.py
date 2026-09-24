"""Tests for the SQL-first FewShotSelector."""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.services.few_shot_selector import EXAM_TYPE_PRIORITY, FewShotSelector, _tokens


def _qb_item(
    item_id,
    text="What is 2 + 2?",
    week=1,
    exam_type="WAEC",
    year=2020,
    subject="Mathematics",
    grade="Primary 4",
):
    return SimpleNamespace(
        id=item_id,
        question_text=text,
        question_type="multiple_choice",
        marks=2,
        options=["A. 3", "B. 4"],
        correct_answer="B",
        topic="Addition",
        exam_type=exam_type,
        source_year=year,
        subject=subject,
        grade_level=grade,
        owner_type="platform",
        is_active=True,
        week_index=week,
        diagram_svg=None,
    )


def _mock_db(items):
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_select_returns_empty_when_no_items():
    db = _mock_db([])
    selector = FewShotSelector(k=6)
    out = await selector.select(db, "Mathematics", "Primary 4", week_indices=[1])
    assert out == []


@pytest.mark.asyncio
async def test_select_ranks_week_match_first():
    """A question matching the requested week must outrank a higher-provenance one."""
    strong_exam_wrong_week = _qb_item("a", week=None, exam_type="WAEC", year=2023)
    weak_exam_right_week = _qb_item("b", week=3, exam_type="internal", year=2015)
    db = _mock_db([strong_exam_wrong_week, weak_exam_right_week])

    out = await FewShotSelector(k=2).select(
        db, "Mathematics", "Primary 4", week_indices=[3], k=2
    )

    assert [o["id"] for o in out] == ["b", "a"]


@pytest.mark.asyncio
async def test_select_respects_k_and_diversity():
    """Diversity pass should drop >60% token-overlap duplicates."""
    items = [
        _qb_item(f"dup{i}", text="Calculate the perimeter of a rectangle width 5 length 6", week=1)
        for i in range(5)
    ] + [_qb_item("distinct", text="Explain photosynthesis in green plants", week=2)]
    db = _mock_db(items)

    out = await FewShotSelector(k=3).select(db, "Science", "Primary 4", k=3)

    texts = {o["question_text"] for o in out}
    # Near-duplicates must collapse to one; the distinct question must survive.
    assert len(out) == 2
    assert any("photosynthesis" in t.lower() for t in texts)
    assert any("perimeter" in t.lower() for t in texts)


@pytest.mark.asyncio
async def test_select_builds_source_tag():
    db = _mock_db([_qb_item("x", exam_type="NECO", year=2019)])
    out = await FewShotSelector(k=1).select(db, "Mathematics", "Primary 4")
    assert out[0]["source_tag"] == "NECO 2019"


def test_exam_type_priority_ordering():
    assert EXAM_TYPE_PRIORITY["waec"] > EXAM_TYPE_PRIORITY["mock"]
    assert EXAM_TYPE_PRIORITY["mock"] > EXAM_TYPE_PRIORITY["internal"]


def test_tokens_normalization():
    assert _tokens("What is 2 + 2?") == {"what", "is", "2"}
