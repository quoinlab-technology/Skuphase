from app.schemas.exam import ManualQuestionInput


def test_manual_question_accepts_structured_faststrap_blocks():
    question = ManualQuestionInput(
        question_number=1,
        type="short_answer",
        question_text="Solve the equation.",
        marks=2,
        content_blocks={
            "blocks": [
                {"type": "text", "text": "Solve for x:"},
                {"type": "math", "latex": "x^2 - 4 = 0", "display": True},
                {"type": "table", "rows": [["x", "2"], ["x^2", "4"]]},
            ]
        },
    )
    assert [block.type for block in question.content_blocks.blocks] == [
        "text",
        "math",
        "table",
    ]
