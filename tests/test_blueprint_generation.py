from app.schemas.exam import ExamGenerationRequest

def test_generation_request_accepts_blueprint():
    request = ExamGenerationRequest(
        subject="Physics", grade_level="SSS 1", sections=[{
            "section_number": 1, "section_title": "Section A",
            "question_type": "multiple_choice", "num_questions": 2,
            "marks_per_question": 1,
        }],
        blueprint={"subject": "Physics", "grade_level": "SSS 1", "total_questions": 2, "total_marks": 2, "sections": [{"topic": "Motion", "bloom": "application", "questions": 2, "marks": 2}]},
    )
    assert request.blueprint.sections[0].topic == "Motion"
