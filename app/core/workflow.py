"""Exam lifecycle state definitions and legal transitions.

workflow_state values:
    generation_requested -> teacher_review | (stays on failure)
    refinement_requested -> teacher_review
    teacher_review       -> final_submitted_by_teacher | refinement_requested
    final_submitted_by_teacher -> approved | teacher_review
    approved             -> (terminal)

exam.status vocabulary: draft, under_review, approved, failed.
"""

from typing import Dict, Set

VALID_WORKFLOW_TRANSITIONS: Dict[str, Set[str]] = {
    "generation_requested": {"teacher_review", "refinement_requested"},
    "refinement_requested": {"teacher_review"},
    "teacher_review": {"final_submitted_by_teacher", "refinement_requested"},
    "final_submitted_by_teacher": {"approved", "teacher_review"},
    "approved": set(),
}

EXAM_STATUSES = {"draft", "under_review", "approved", "failed"}

# Statuses that may be set directly via the generic update endpoint.
# "approved" is intentionally excluded: approval must go through the
# governed approve endpoint (preflight + workflow checks).
MUTABLE_STATUSES = {"draft", "under_review"}


def can_transition(current_state: str, target_state: str) -> bool:
    """Return True when current -> target is a legal workflow transition."""
    return target_state in VALID_WORKFLOW_TRANSITIONS.get(current_state, set())
