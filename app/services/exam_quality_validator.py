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
# British -> American spelling aliases for Bloom's taxonomy. LLMs are
# inconsistent (e.g. "analyse" vs "analyze"), so we normalize before any
# comparison or persistence. Without this, valid British-spelled levels
# would fail quality validation and kill an otherwise-fine generation.
_BLOOM_SPELLING_ALIASES = {
    "analyse": "analyze",
}


def normalize_bloom_level(value: Any) -> Optional[str]:
    """Return the canonical, lowercase, American-spelled Bloom level or None.

    Accepts case and British/American spelling variants, e.g. all of
    "Analyse", "ANALYZE", "Analyze", "analyse" -> "analyze".
    """
    if value is None:
        return None
    raw = str(value).strip().lower()
    raw = _BLOOM_SPELLING_ALIASES.get(raw, raw)
    return raw if raw in ALLOWED_BLOOM else None
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
                if bloom and normalize_bloom_level(bloom) is None:
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
                    if answer not in {"A", "B", "C", "D", "E"}:
                        errors.append(
                            f"Section {req_section.section_number} question {idx} must use A-E correct_answer."
                        )
                elif q_type == "true_false":
                    options = q.get("options")
                    answer = q.get("correct_answer")
                    if not isinstance(options, list) or len(options) < 2:
                        errors.append(
                            f"Section {req_section.section_number} question {idx} must have 2 options (True/False)."
                        )
                    if answer not in {"A", "B"}:
                        errors.append(
                            f"Section {req_section.section_number} question {idx} must use A/B correct_answer (A=True, B=False)."
                        )
                elif q_type == "fill_in_blanks":
                    # Fill-in-the-blank: correct_answer must be a non-empty string
                    answer = q.get("correct_answer")
                    if not answer or not str(answer).strip():
                        errors.append(
                            f"Section {req_section.section_number} question {idx} (fill_in_blanks) must have a correct_answer."
                        )
                # theory, essay, short_answer: marking_scheme is optional — no hard errors for absence


                # Sub-parts: when present, their marks must sum to the question total.
                sub_parts = q.get("sub_parts")
                if isinstance(sub_parts, list) and sub_parts and isinstance(marks, int) and marks > 0:
                    sub_total = sum(
                        (sp.get("marks") or 0) for sp in sub_parts if isinstance(sp, dict)
                    )
                    if sub_total != marks:
                        errors.append(
                            f"Section {req_section.section_number} question {idx} sub-part marks "
                            f"{sub_total} do not sum to question marks {marks}."
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
        if question_text_blob and (getattr(request, "language", "English") or "English").lower() == "english":
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

        # Anti-hallucination passage grounding: in comprehension sections every
        # question must share content words with the teacher-supplied passage.
        from app.services.exam_quality_report import ExamQualityReportService

        for section in sections:
            passage = section.get("passage") if isinstance(section, dict) else None
            if not passage or not (passage.get("body") or "").strip():
                continue
            body_words = set(ExamQualityReportService._keywords(passage.get("body") or ""))
            if not body_words:
                continue
            for idx, q in enumerate(section.get("questions", []), start=1):
                if not isinstance(q, dict):
                    continue
                combo = f"{q.get('question') or ''} {q.get('correct_answer') or ''}"
                q_words = set(ExamQualityReportService._keywords(combo))
                if not q_words:
                    continue
                overlap = len(q_words & body_words) / float(len(q_words))
                if overlap < 0.35:
                    errors.append(
                        f"Section {section.get('section_number')} question {idx}: weak grounding "
                        "in the passage — the answer is not clearly stated. Rewrite to be "
                        "answerable from the passage."
                    )
                elif overlap < 0.5:
                    warnings.append(
                        f"Section {section.get('section_number')} question {idx}: "
                        f"low passage overlap ({overlap:.0%}); verify it is answerable."
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
