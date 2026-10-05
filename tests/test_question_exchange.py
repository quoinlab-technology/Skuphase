from app.services.question_exchange import (
    export_csv,
    export_gift,
    export_qti,
    import_csv,
    import_gift,
    import_qti,
    export_docx,
    import_docx,
)


def _questions():
    return [{
        "question_number": 1,
        "type": "multiple_choice",
        "question_text": "What is 2 + 2?",
        "marks": 1,
        "options": ["4", "5"],
        "correct_answer": "A",
        "marking_scheme": ["Correct value"],
        "content_blocks": [{"type": "math", "latex": "2+2=4"}],
    }]


def test_csv_round_trip_preserves_structured_fields():
    result = import_csv(export_csv(_questions()))
    assert result[0]["question_text"] == "What is 2 + 2?"
    assert result[0]["content_blocks"][0]["latex"] == "2+2=4"


def test_gift_round_trip_preserves_correct_choice():
    result = import_gift(export_gift(_questions()))
    assert result[0]["options"] == ["4", "5"]
    assert result[0]["correct_answer"] == "A"


def test_qti_round_trip_is_valid_xml():
    result = import_qti(export_qti(_questions()))
    assert result[0]["question_text"] == "What is 2 + 2?"
    assert result[0]["correct_answer"] == "A"


def test_docx_round_trip_preserves_question_text():
    result = import_docx(export_docx(_questions()))
    assert result[0]["question_text"] == "What is 2 + 2?"


def test_docx_export_removes_xml_illegal_control_characters():
    payload = _questions()
    payload[0]["question_text"] = "Clean\x00 this\x07 pasted text"
    payload[0]["options"] = ["A\x0b", "B"]

    result = import_docx(export_docx(payload))
    assert result[0]["question_text"] == "Clean this pasted text"
