import pytest

from app.scripts.ingest_curriculum import validate_records
from app.scripts.seed_curriculum_postgres import _rows


def test_validate_records_normalizes_board_and_optional_fields():
    rows = validate_records(
        [{"class_level": "JSS 1", "subject": "Physics", "term": "First Term", "week": 1, "topic": "Motion"}],
        board="LAGOS_UNIFIED",
    )
    assert rows[0]["board"] == "LAGOS_UNIFIED"
    assert rows[0]["subtopics"] == []


def test_postgres_seed_keeps_subtopics_as_structured_json_values():
    _, schemes = _rows([
        {
            "board": "NERDC",
            "class_level": "JSS 1",
            "subject": "Physics",
            "term": "First Term",
            "week": 1,
            "topic": "Motion",
            "subtopics": ["Distance", "Displacement"],
        }
    ])
    assert schemes[0]["subtopics"] == ["Distance", "Displacement"]


@pytest.mark.parametrize(
    "row, message",
    [
        ({"class_level": "JSS 1", "subject": "Physics", "term": "First Term", "week": 0, "topic": "Motion"}, "week"),
        ({"class_level": "JSS 1", "subject": "Physics", "term": "Holiday", "week": 1, "topic": "Motion"}, "term"),
        ({"class_level": "JSS 1", "subject": "Physics", "term": "First Term", "week": 1}, "missing"),
    ],
)
def test_validate_records_rejects_bad_rows(row, message):
    with pytest.raises(ValueError, match=message):
        validate_records([row])
