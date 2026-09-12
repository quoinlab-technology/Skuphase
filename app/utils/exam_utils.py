"""Exam utility functions shared between frontend rendering and PDF export."""

from typing import List

MCQ_LETTERS = ["A", "B", "C", "D", "E"]


def format_mcq_option(opt: str, idx: int) -> str:
    """Format a multiple-choice option with letter prefix (A., B., etc.) if missing.

    Handles prefixes like 'A.', 'A)', 'A -' appropriately.
    """
    opt_str = str(opt).strip()
    if not opt_str:
        return ""
    # Check if option already starts with standard letter prefix e.g. A. or A) or A:
    if len(opt_str) >= 2 and opt_str[0].upper() in "ABCDE" and opt_str[1] in ".):- ":
        return opt_str

    prefix = f"{MCQ_LETTERS[idx % len(MCQ_LETTERS)]}. "
    return prefix + opt_str
