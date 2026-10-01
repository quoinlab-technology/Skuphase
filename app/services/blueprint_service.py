"""Exam blueprint/Table-of-Specification validation and summaries."""
from app.schemas.assessment_studio import BlueprintRequest, BlueprintResponse

def build_blueprint(request: BlueprintRequest) -> BlueprintResponse:
    warnings: list[str] = []
    q_total = sum(s.questions for s in request.sections)
    m_total = sum(s.marks for s in request.sections)
    if q_total != request.total_questions:
        warnings.append(f"Question allocation is {q_total}; target is {request.total_questions}.")
    if m_total != request.total_marks:
        warnings.append(f"Marks allocation is {m_total}; target is {request.total_marks}.")
    topic_totals: dict[str, int] = {}
    bloom_totals: dict[str, int] = {}
    for section in request.sections:
        topic_totals[section.topic] = topic_totals.get(section.topic, 0) + section.marks
        bloom_totals[section.bloom] = bloom_totals.get(section.bloom, 0) + section.marks
    if len(bloom_totals) == 1:
        warnings.append("Blueprint uses only one Bloom taxonomy level.")
    return BlueprintResponse(
        subject=request.subject,
        grade_level=request.grade_level,
        total_questions=q_total,
        total_marks=m_total,
        sections=request.sections,
        topic_totals=topic_totals,
        bloom_totals=bloom_totals,
        warnings=warnings,
    )
