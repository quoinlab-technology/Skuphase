"""Tests for curriculum JSON normalization (pure functions, no DB)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\DELL\Desktop\FastStrap\skuphase")

from app.scripts.normalize_curriculum_json import (  # noqa: E402
    _fingerprint,
    _is_garbage,
    normalize_dataset,
    validate_dataset,
)


def _raw(subject="Mathematics", cls="Primary 4", term="First Term", week=1, topic="Addition"):
    return {
        "board": "NERDC",
        "country": "NG",
        "class_level": cls,
        "subject": subject,
        "term": term,
        "week": week,
        "topic": topic,
        "subtopics": ["Count objects", "Group numbers"],
        "subtopics_count": 2,
        "is_exam_or_break": False,
    }


def test_noisy_subject_variants_fold_to_canonical():
    raws = [
        _raw(subject="Healthhabits"),
        _raw(subject="Socialandcitizenship Studies"),
        _raw(subject="Physical Andhealtheducation"),
        _raw(subject="Christian Religiousstudies"),
    ]
    cleaned, dropped = normalize_dataset(raws)
    assert len(cleaned) == 4
    subjects = {r["subject"] for r in cleaned}
    assert subjects == {
        "Health Habits",
        "Social & Citizenship Studies",
        "Physical & Health Education",
        "Christian Religious Studies",
    }


def test_garbage_rows_dropped():
    raws = [
        _raw(),  # valid baseline
        _raw(subject="| Healthhabits Third Term | | | | | |", topic="| x |"),
        _raw(week=115),
    ]
    cleaned, dropped = normalize_dataset(raws)
    assert len(cleaned) == 1
    assert dropped.get("garbage/malformed") == 2


def test_invalid_term_and_week_dropped():
    cleaned, _ = normalize_dataset([_raw(term="Fourth Term"), _raw(week=0), _raw()])
    assert len(cleaned) == 1


def test_same_week_duplicates_merged_not_dropped():
    """Two topics in one week merge into a single scheme row (DB has UNIQUE constraint)."""
    raws = [
        _raw(topic="Speech: Alphabets"),
        _raw(topic="First group of sounds: s, a, t"),
    ]
    cleaned, _ = normalize_dataset(raws)
    assert len(cleaned) == 1
    merged = cleaned[0]
    assert "Speech" in merged["topic"] and "sounds" in merged["topic"]
    assert " ; " in merged["topic"]


def test_merge_unions_subtopics_without_duplicates():
    a = _raw(topic="Topic A")
    b = _raw(topic="Topic B")
    b["subtopics"] = ["Count objects", "New objective"]
    cleaned, _ = normalize_dataset([a, b])
    assert cleaned[0]["subtopics"].count("Count objects") == 1
    assert "New objective" in cleaned[0]["subtopics"]
    assert cleaned[0]["subtopics_count"] == 3


def test_validate_clean_output_has_zero_errors():
    raws = [_raw(), _raw(week=2, topic="Subtraction"), _raw(cls="Primary 5")]
    cleaned, _ = normalize_dataset(raws)
    assert validate_dataset(cleaned) == []


def test_fingerprint_is_collision_resistant():
    assert _fingerprint("Songs & Rhymes") == _fingerprint("songs rhymes")
    assert _fingerprint("Mathematics") != _fingerprint("Numeracy")
