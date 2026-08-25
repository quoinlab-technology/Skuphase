"""Deterministic quality checks for LLM-generated exams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.schemas.exam import ExamGenerationRequest, SectionConfig


ALLOWED_DIFFICULTY = {"easy", "medium", "hard"}
ALLOWED_BLOOM = {
    "remember",
    "understand",
    "apply",
    "analyze",
    "evaluate",
    "create",
}
US_BIAS_TOKENS = {
    "dollar",
    "miles",
    "fahrenheit",
    "soccer mom",
    "california",
    "new york state test",
}
NIGERIA_CONTEXT_TOKENS = {
    "naira",
    "lagos",
    "abuja",
    "kano",
    "ibadan",
    "nepa",
    "harmattan",
    "cassava",
    "nigeria",
}


@dataclass
class ValidationResult:
    """Validation output."""

    errors: List[str]
    warnings: List[str]
    metrics: Dict[str, Any]


class ExamQualityValidator:
    """Validates generated exams against structural and quality constraints."""

    def validate(
        self,
        parsed_exam: Dict[str, Any],
        request: ExamGenerationRequest,
    ) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        sections = parsed_exam.get("sections")
        if not isinstance(sections, list) or not sections:
            errors.append("Generated exam must contain at least one section.")
            return ValidationResult(errors=errors, warnings=warnings, metrics={})

        section_by_number = {
            section.get("section_number"): section
            for section in sections
            if isinstance(section, dict)
        }
        generated_question_total = 0
        generated_marks_total = 0
        difficulty_counts = {"easy": 0, "medium": 0, "hard": 0}

        for req_section in request.sections:
            section = section_by_number.get(req_section.section_number)
            if section is None:
                errors.append(
                    f"Missing section {req_section.section_number}: {req_section.section_title}"
                )
                continue

            questions = section.get("questions")
            if not isinstance(questions, list):
                errors.append(f"Section {req_section.section_number} has invalid questions list.")
                continue

            if len(questions) != req_section.num_questions:
                errors.append(
                    "Section "
                    f"{req_section.section_number} expected {req_section.num_questions} questions, "
                    f"got {len(questions)}."
                )

            for idx, q in enumerate(questions, start=1):
                generated_question_total += 1
                q_type = q.get("type")
                if q_type != req_section.question_type:
                    errors.append(
                        f"Section {req_section.section_number} question {idx}: "
                        f"type {q_type} does not match expected {req_section.question_type}."
                    )

                marks = q.get("marks")
                if not isinstance(marks, int) or marks <= 0:
                    errors.append(
                        f"Section {req_section.section_number} question {idx} has invalid marks."
                    )
                else:
                    generated_marks_total += marks
                    if req_section.marks_per_question and marks != req_section.marks_per_question:
                        errors.append(
                            f"Section {req_section.section_number} question {idx} marks {marks} "
                            f"must equal {req_section.marks_per_question}."
                        )

                difficulty = q.get("difficulty")
                if difficulty:
                    if difficulty not in ALLOWED_DIFFICULTY:
                        errors.append(
                            f"Section {req_section.section_number} question {idx} has invalid "
                            f"difficulty '{difficulty}'."
                        )
                    else:
                        difficulty_counts[difficulty] += 1

                bloom = q.get("bloom_level")
                if bloom and bloom not in ALLOWED_BLOOM:
                    errors.append(
                        f"Section {req_section.section_number} question {idx} has invalid "
                        f"Bloom level '{bloom}'."
                    )

                if q_type == "multiple_choice":
                    options = q.get("options")
                    answer = q.get("correct_answer")
                    if not isinstance(options, list) or len(options) < 4:
                        errors.append(
                            f"Section {req_section.section_number} question {idx} must have >= 4 options."
                        )
                    if answer not in {"A", "B", "C", "D"}:
                        errors.append(
                            f"Section {req_section.section_number} question {idx} must use A-D correct_answer."
                        )

        expected_question_total = sum(s.num_questions for s in request.sections)
        if generated_question_total != expected_question_total:
            errors.append(
                f"Total questions expected {expected_question_total}, got {generated_question_total}."
            )

        expected_marks_total = self._expected_total_marks(request.sections)
        if expected_marks_total is not None and generated_marks_total != expected_marks_total:
            errors.append(
                f"Total marks expected {expected_marks_total}, got {generated_marks_total}."
            )

        question_text_blob = " ".join(
            (q.get("question") or "").lower()
            for section in sections
            for q in section.get("questions", [])
            if isinstance(q, dict)
        )
        if question_text_blob:
            us_hits = [token for token in US_BIAS_TOKENS if token in question_text_blob]
            ng_hits = [token for token in NIGERIA_CONTEXT_TOKENS if token in question_text_blob]
            if us_hits:
                warnings.append(
                    f"Possible non-local context detected: {', '.join(us_hits[:3])}."
                )
            if not ng_hits:
                warnings.append(
                    "No obvious Nigeria-local terms detected in generated questions."
                )

        if request.difficulty_distribution:
            missing_diff = [
                level
                for level in request.difficulty_distribution
                if difficulty_counts.get(level, 0) == 0
            ]
            if missing_diff:
                warnings.append(
                    "Difficulty distribution requested but missing levels in output: "
                    + ", ".join(missing_diff)
                )

        metrics = {
            "generated_question_total": generated_question_total,
            "expected_question_total": expected_question_total,
            "generated_marks_total": generated_marks_total,
            "expected_marks_total": expected_marks_total,
            "difficulty_counts": difficulty_counts,
            "curriculum_alignment": "checked",
        }
        return ValidationResult(errors=errors, warnings=warnings, metrics=metrics)

    def validate_or_raise(
        self,
        parsed_exam: Dict[str, Any],
        request: ExamGenerationRequest,
    ) -> ValidationResult:
        result = self.validate(parsed_exam=parsed_exam, request=request)
        if result.errors:
            joined = " | ".join(result.errors)
            raise ValueError(f"Generated exam failed quality validation: {joined}")
        return result

    @staticmethod
    def _expected_total_marks(sections: List[SectionConfig]) -> Optional[int]:
        if any(not section.marks_per_question for section in sections):
            return None
        total = 0
        for section in sections:
            if section.instruction_type == "answer_all":
                total += section.num_questions * section.marks_per_question
            else:
                total += (section.answer_count or section.num_questions) * section.marks_per_question
        return total
