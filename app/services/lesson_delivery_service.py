"""Curriculum-delivery helpers kept independent from assessment generation."""
from __future__ import annotations
from app.core.llm import get_llm_service


async def generate_lesson_note(*, topic: str, subtopics: list[str], class_level: str, subject: str, guidance: str | None = None) -> str:
    extra = f"\nAdditional teacher guidance: {guidance}" if guidance else ""
    prompt = f"""You are a Nigerian classroom lesson-note assistant. Write a practical teacher lesson note.
Subject: {subject}
Class: {class_level}
Topic: {topic}
Subtopics: {', '.join(subtopics)}{extra}
Use clear headings: objectives, starter, explanation, guided practice, assessment, and differentiation. Do not invent curriculum topics outside the supplied topic."""
    result = await get_llm_service().generate(prompt=prompt, temperature=0.2, max_tokens=1800)
    return str(result.get("content") or "").strip()


def coverage_summary(rows: list[dict]) -> dict:
    total = len(rows)
    counts = {status: sum(1 for row in rows if row.get("status") == status) for status in ("planned", "in_progress", "completed", "verified")}
    return {"total": total, "counts": counts, "completion_percent": round(((counts["completed"] + counts["verified"]) / total) * 100, 1) if total else 0.0}
