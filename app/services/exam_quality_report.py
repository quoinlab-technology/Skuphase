"""Exam quality and curriculum coverage analysis utilities."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, Iterable, List


STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "into",
    "what",
    "which",
    "when",
    "where",
    "your",
    "their",
    "about",
    "have",
    "will",
    "were",
    "been",
    "are",
    "was",
    "why",
    "how",
    "all",
    "any",
    "can",
    "you",
}


class ExamQualityReportService:
    """Computes quality and context coverage metrics for an exam."""

    @staticmethod
    def build_report(
        *,
        subject: str,
        grade_level: str,
        questions: Iterable[Any],
        context_text: str,
    ) -> Dict[str, Any]:
        question_list = list(questions)
        question_count = len(question_list)
        total_marks = sum(getattr(q, "marks", 0) or 0 for q in question_list)

        type_counts = Counter((getattr(q, "type", "unknown") or "unknown") for q in question_list)
        difficulty_counts = Counter(
            (getattr(q, "difficulty", "unspecified") or "unspecified")
            for q in question_list
        )
        bloom_counts = Counter(
            (getattr(q, "bloom_level", "unspecified") or "unspecified")
            for q in question_list
        )

        quality_flags: List[str] = []
        for q in question_list:
            q_text = (getattr(q, "question_text", "") or "").strip()
            if len(q_text) < 20:
                quality_flags.append(
                    f"Question {getattr(q, 'question_number', '?')} appears too short."
                )
            if getattr(q, "type", None) == "multiple_choice":
                options = getattr(q, "options", None)
                answer = getattr(q, "correct_answer", None)
                if not isinstance(options, list) or len(options) < 4:
                    quality_flags.append(
                        f"MCQ {getattr(q, 'question_number', '?')} has fewer than 4 options."
                    )
                if answer not in {"A", "B", "C", "D"}:
                    quality_flags.append(
                        f"MCQ {getattr(q, 'question_number', '?')} missing valid A-D answer."
                    )

        question_words = ExamQualityReportService._keywords(
            " ".join((getattr(q, "question_text", "") or "") for q in question_list)
        )
        context_words = ExamQualityReportService._keywords(context_text)

        overlap = sorted(set(question_words) & set(context_words))
        coverage_ratio = (len(overlap) / max(len(set(question_words)), 1)) if question_words else 0.0
        coverage_score = round(coverage_ratio * 100, 2)
        low_coverage = coverage_score < 35
        if low_coverage:
            quality_flags.append(
                "Low curriculum alignment signal from lexical overlap; review source alignment."
            )

        quality_status = ExamQualityReportService._traffic_light_status(
            coverage_score=coverage_score,
            quality_flags_count=len(quality_flags),
        )
        overall_score = ExamQualityReportService._overall_score(
            coverage_score=coverage_score,
            quality_flags_count=len(quality_flags),
        )

        return {
            "subject": subject,
            "grade_level": grade_level,
            "question_count": question_count,
            "total_marks": total_marks,
            "distribution": {
                "question_types": dict(type_counts),
                "difficulty": dict(difficulty_counts),
                "bloom_levels": dict(bloom_counts),
            },
            "coverage": {
                "score": coverage_score,
                "matched_keyword_count": len(overlap),
                "matched_keywords_sample": overlap[:20],
                "context_keyword_count": len(set(context_words)),
                "question_keyword_count": len(set(question_words)),
            },
            "quality_status": quality_status,
            "overall_score": overall_score,
            "quality_flags": quality_flags,
            "status": "needs_review" if quality_flags else "good",
        }

    @staticmethod
    def _keywords(text: str) -> List[str]:
        tokens = re.findall(r"[a-zA-Z]{4,}", (text or "").lower())
        return [token for token in tokens if token not in STOP_WORDS]

    @staticmethod
    def _overall_score(*, coverage_score: float, quality_flags_count: int) -> float:
        penalty = min(quality_flags_count * 8, 50)
        return round(max(0.0, coverage_score - penalty), 2)

    @staticmethod
    def _traffic_light_status(*, coverage_score: float, quality_flags_count: int) -> str:
        if coverage_score >= 60 and quality_flags_count <= 1:
            return "green"
        if coverage_score >= 35 and quality_flags_count <= 4:
            return "amber"
        return "red"
