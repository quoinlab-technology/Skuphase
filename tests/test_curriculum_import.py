import pytest

from app.scripts.ingest_curriculum import validate_records


def test_validate_records_normalizes_board_and_optional_fields():
    rows = validate_records(
        [{"class_level": "JSS 1", "subject": "Physics", "term": "First Term", "week": 1, "topic": "Motion"}],
        board="LAGOS_UNIFIED",
    )
    assert rows[0]["board"] == "LAGOS_UNIFIED"
    assert rows[0]["subtopics"] == []


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
