"""Canonical curriculum labels shared by ingestion, APIs, and the UI.

NERDC source documents use a mixture of abbreviations, punctuation, and
spacing (especially across the JSS/SSS volume).  Keeping the vocabulary in one
place prevents a seeded subject from disappearing simply because a selector
uses a different spelling.
"""

from __future__ import annotations

import re


CLASS_LEVELS = (
    "Pre-Nursery",
    "Nursery 1",
    "Nursery 2",
    "Primary 1",
    "Primary 2",
    "Primary 3",
    "Primary 4",
    "Primary 5",
    "Primary 6",
    "JSS 1",
    "JSS 2",
    "JSS 3",
    "SSS 1",
    "SSS 2",
    "SSS 3",
)

PRIMARY_SUBJECTS = (
    "English Studies",
    "Mathematics",
    "Basic Science",
    "Social & Citizenship Studies",
    "Cultural & Creative Arts",
    "Physical & Health Education",
    "Christian Religious Studies",
    "Islamic Religious Studies",
    "Agricultural Science",
    "Computer Studies",
)

SECONDARY_SUBJECTS = (
    "English Language",
    "Mathematics",
    "Further Mathematics",
    "Basic Science",
    "Basic Technology",
    "Biology",
    "Chemistry",
    "Physics",
    "Agricultural Science",
    "Economics",
    "Government",
    "Geography",
    "Literature in English",
    "Civic Education",
    "Social Studies",
    "Computer Studies",
    "Data Processing",
    "Financial Accounting",
    "Commerce",
    "Marketing",
    "Food & Nutrition",
    "Home Economics",
    "Technical Drawing",
    "French Language",
    "Yoruba",
    "Igbo",
    "Hausa",
    "Christian Religious Studies",
    "Islamic Religious Studies",
    "Physical & Health Education",
    "Music",
    "Visual Arts",
)

ALL_SUBJECTS = tuple(dict.fromkeys((*PRIMARY_SUBJECTS, *SECONDARY_SUBJECTS)))


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


_CLASS_ALIASES = {
    "prenursery": "Pre-Nursery",
    "nursery1": "Nursery 1",
    "nursery2": "Nursery 2",
    "jss1": "JSS 1",
    "jss2": "JSS 2",
    "jss3": "JSS 3",
    "ss1": "SSS 1",
    "ss2": "SSS 2",
    "ss3": "SSS 3",
}
_CLASS_ALIASES.update({_key(label): label for label in CLASS_LEVELS})

_SUBJECT_ALIASES = {
    "english": "English Language",
    "englishstudies": "English Studies",
    "basictechnology": "Basic Technology",
    "agriculturalscience": "Agricultural Science",
    "literatureinenglish": "Literature in English",
    "literatureenglish": "Literature in English",
    "french": "French Language",
    "culturalandcreativearts": "Cultural & Creative Arts",
    "culturalcreativearts": "Cultural & Creative Arts",
    "physicalandhealtheducation": "Physical & Health Education",
    "physicalhealth education": "Physical & Health Education",
    "christianreligiousstudies": "Christian Religious Studies",
    "islamicreligiousstudies": "Islamic Religious Studies",
    "socialandcitizenshipstudies": "Social & Citizenship Studies",
    "socialcitizenshipstudies": "Social & Citizenship Studies",
    "furthermathematics": "Further Mathematics",
    "dataprocessing": "Data Processing",
    "foodandnutrition": "Food & Nutrition",
}
_SUBJECT_ALIASES.update({_key(label): label for label in ALL_SUBJECTS})


def canonical_class_level(value: str) -> str:
    """Return the canonical class label while preserving unknown values."""
    text = str(value or "").strip()
    return _CLASS_ALIASES.get(_key(text), text)


def canonical_subject(value: str) -> str:
    """Return the canonical subject label while preserving unknown values."""
    text = str(value or "").strip()
    return _SUBJECT_ALIASES.get(_key(text), text)

