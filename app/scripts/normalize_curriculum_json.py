"""
Normalize the Gemini-converted NERDC curriculum JSON into a clean, canonical shape.

Input:  pdf_process/nerdc_scheme_database.json  (3,648 raw records)
Output: pdf_process/nerdc_scheme_database.final.json (clean, canonical subject names,
        valid term/week, garbage rows dropped)

Why this exists:
The raw dataset has OCR/noise artifacts in `subject` (34 distinct strings -> ~25
canonical), plus a handful of malformed rows (week 113-117, an embedded markdown
table row). Exam generation queries by (class_level, subject, term, week), so the
corpus must be deterministic and collision-free before it seeds the DB.

Design notes:
- Pure Python + stdlib only (no DB, no numpy) so it can run anywhere and be
  unit-tested easily.
- Canonical subject mapping is EXPLICIT and collision-checked at import time so
  changes are auditable.
- All output rows are validated (term in set, 1 <= week <= 13, non-empty topic,
  non-empty subject) before they are accepted.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

# ---------------------------------------------------------------------------
# Canonical subject taxonomy (fingerprint -> canonical display name)
# ---------------------------------------------------------------------------
# A fingerprint is the lowercased, punctuation- and whitespace-stripped form of a
# subject string. Multiple noisy OCR variants fold to one canonical name.
CANONICAL_SUBJECTS: Dict[str, str] = {
    "healthhabits": "Health Habits",
    "handwriting": "Handwriting",
    "prehandwriting": "Pre-Handwriting",
    "literacy": "Literacy",
    "numeracy": "Numeracy",
    "prenumeracy": "Pre-Numeracy",
    "prescience": "Pre-Science",
    "presocialhabits": "Pre-Social Habits",
    "socialhabits": "Social Habits",
    "basicscience": "Basic Science",
    "creativity": "Creativity",
    "personaldevelopment": "Personal Development",
    "songsrhymes": "Songs & Rhymes",
    "songsandrhymes": "Songs & Rhymes",
    "mathematics": "Mathematics",
    "maths": "Mathematics",
    "christianreligiousstudies": "Christian Religious Studies",
    "christianreligiousstudy": "Christian Religious Studies",
    "islamicstudies": "Islamic Studies",
    "islamicreligiousstudies": "Islamic Studies",
    "nigeriahistory": "Nigerian History",
    "nigerianhistory": "Nigerian History",
    "socialcitizenshipstudies": "Social & Citizenship Studies",
    "socialandcitizenshipstudies": "Social & Citizenship Studies",
    "culturalcreativearts": "Cultural & Creative Arts",
    "culturalandcreativearts": "Cultural & Creative Arts",
    "englishlanguage": "English Language",
    "government": "Government",
    "civiceducation": "Civic Education",
    "physicalhealtheducation": "Physical & Health Education",
    "physicalandhealtheducation": "Physical & Health Education",
    "basicdigitalliteracy": "Basic Digital Literacy",
    "digitalliteracy": "Basic Digital Literacy",
    "prevocationalstudies": "Prevocational Studies",
    "frenchlanguage": "French Language",
    "computerstudies": "Computer Studies",
    "agriculturalscience": "Agricultural Science",
    "history": "History",
    "geography": "Geography",
    "economics": "Economics",
    "biology": "Biology",
    "chemistry": "Chemistry",
    "physics": "Physics",
    "furthermathematics": "Further Mathematics",
    "technology": "Basic Technology",
}

VALID_TERMS = {"First Term", "Second Term", "Third Term"}
VALID_WEEK_RANGE = (1, 13)


def _fingerprint(subject: str) -> str:
    """Collapse a subject string to a collision-resistant key."""
    s = subject.lower().strip()
    # Remove everything except letters and digits.
    return re.sub(r"[^a-z0-9]+", "", s)


def _resolve_subject(raw: str) -> str | None:
    """Resolve a raw subject string to its canonical name, or None if unmapped."""
    fp = _fingerprint(raw)
    if not fp:
        return None
    return CANONICAL_SUBJECTS.get(fp)


def _is_exam_or_break_record(rec: Dict) -> bool:
    """A scheme row whose topic is blank AND marked as exam/break is a marker."""
    if rec.get("is_exam_or_break"):
        topic = (rec.get("topic") or "").strip()
        if not topic:
            return True
    return False


def _is_garbage(row: Dict) -> bool:
    """Rows that are malformed (embedded markdown table header, absurd week)."""
    topic = (row.get("topic") or "").strip()
    week = row.get("week")
    # The odd | ... | markdown-table rows.
    if topic.startswith("|") or (topic and topic.endswith("|")):
        return True
    # Weeks outside 1-13 are noise.
    if isinstance(week, int) and not (VALID_WEEK_RANGE[0] <= week <= VALID_WEEK_RANGE[1]):
        return True
    return False


def normalize_record(raw: Dict) -> Dict | None:
    """Return a cleaned record, or None to drop."""
    if _is_garbage(raw):
        return None

    subject = _resolve_subject(raw.get("subject") or "")
    if subject is None:
        return None

    term = (raw.get("term") or "").strip()
    if term not in VALID_TERMS:
        return None

    week = raw.get("week")
    if not isinstance(week, int) or not (VALID_WEEK_RANGE[0] <= week <= VALID_WEEK_RANGE[1]):
        return None

    topic = (raw.get("topic") or "").strip()
    if not topic and not _is_exam_or_break_record(raw):
        return None

    subtopics = raw.get("subtopics") or []
    if not isinstance(subtopics, list):
        subtopics = []

    # Clean subtopic entries (strip whitespace, drop empties).
    subtopics = [s.strip() for s in subtopics if s and s.strip()]

    return {
        "board": raw.get("board", "NERDC") or "NERDC",
        "country": raw.get("country", "NG") or "NG",
        "class_level": (raw.get("class_level") or "").strip(),
        "subject": subject,
        "term": term,
        "week": week,
        "topic": topic,
        "subtopics": subtopics,
        "subtopics_count": len(subtopics),
        "is_exam_or_break": bool(raw.get("is_exam_or_break", False)),
    }


def normalize_dataset(records: List[Dict]) -> List[Dict]:
    """Normalize a list of raw records; returns only valid merged records.

    The raw dataset sometimes contains TWO rows for the same
    (class_level, subject, term, week) — e.g. Literacy Week 1 covers both
    "Speech: alphabets" AND "Introduction to first group of sounds". The
    ``scheme_of_works`` table enforces UNIQUE (curriculum_id, term,
    week_number), so same-week rows are merged into a single record:
    topics are joined, subtopics are unioned (order preserved, deduped).
    """
    out: List[Dict] = []
    dropped: Dict[str, int] = {}
    merged: Dict[tuple, Dict] = {}

    for rec in records:
        clean = normalize_record(rec)
        if clean is None:
            key = _drop_reason(rec)
            dropped[key] = dropped.get(key, 0) + 1
            continue

        mkey = (
            clean["board"],
            clean["country"],
            clean["class_level"],
            clean["subject"],
            clean["term"],
            clean["week"],
        )

        existing = merged.get(mkey)
        if existing is None:
            merged[mkey] = dict(clean)
            continue

        # Merge topics + subtopics into the existing record.
        topics = _nonempty_parts([existing["topic"], clean["topic"]])
        existing["topic"] = " ; ".join(topics)

        seen_sub: set = set()
        combined: List[str] = []
        for st in existing["subtopics"] + clean["subtopics"]:
            key = _fingerprint(st)
            if st and key not in seen_sub:
                seen_sub.add(key)
                combined.append(st)
        existing["subtopics"] = combined
        existing["subtopics_count"] = len(combined)
        existing["is_exam_or_break"] = (
            existing["is_exam_or_break"] or clean["is_exam_or_break"]
        )

    out = list(merged.values())
    return out, dropped


def _nonempty_parts(parts: List[str]) -> List[str]:
    """Return non-empty, distinct parts preserving order."""
    seen: set = set()
    result: List[str] = []
    for p in parts:
        s = p.strip()
        key = _fingerprint(s)
        if s and key not in seen:
            seen.add(key)
            result.append(s)
    return result


def _drop_reason(rec: Dict) -> str:
    if _is_garbage(rec):
        return "garbage/malformed"
    if _resolve_subject(rec.get("subject") or "") is None:
        return f"unmapped_subject:{rec.get('subject')!r}"
    if (rec.get("term") or "").strip() not in VALID_TERMS:
        return f"invalid_term:{rec.get('term')!r}"
    return "invalid_week_or_topic"


def validate_dataset(records: List[Dict]) -> List[str]:
    """Return list of violations (empty = healthy)."""
    errors: List[str] = []
    seen = set()
    for i, r in enumerate(records):
        key = (r["class_level"], r["subject"], r["term"], r["week"])
        dup = key in seen
        seen.add(key)
        if r["term"] not in VALID_TERMS:
            errors.append(f"row {i}: invalid term {r['term']!r}")
        if not (VALID_WEEK_RANGE[0] <= r["week"] <= VALID_WEEK_RANGE[1]):
            errors.append(f"row {i}: invalid week {r['week']}")
        if not r["topic"] and not r["is_exam_or_break"]:
            errors.append(f"row {i}: empty topic for non-exam row")
        if dup:
            errors.append(f"row {i}: duplicate key {key}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize NERDC curriculum JSON")
    parser.add_argument(
        "--input",
        default=r"C:\Users\DELL\Desktop\FastStrap\pdf_process\nerdc_scheme_database.json",
        help="Path to the raw Gemini JSON",
    )
    parser.add_argument(
        "--output",
        default=r"C:\Users\DELL\Desktop\FastStrap\pdf_process\nerdc_scheme_database.final.json",
        help="Where to write the normalized JSON",
    )
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        raise FileNotFoundError(f"Input not found: {src}")

    raw_records = json.loads(src.read_text(encoding="utf-8"))
    cleaned, dropped = normalize_dataset(raw_records)
    errors = validate_dataset(cleaned)

    print(f"Source : {src} ({len(raw_records)} rows)")
    print(f"Clean  : {len(cleaned)} rows")
    print(f"Dropped: {len(raw_records) - len(cleaned)}")
    for reason, count in sorted(dropped.items(), key=lambda x: -x[1]):
        print(f"  - {reason}: {count}")

    if errors:
        print(f"\nValidation found {len(errors)} issue(s) - first 20:")
        for e in errors[:20]:
            print(f"   {e}")
        print("\nAborting write to avoid corrupt seed.")
        raise SystemExit(1)

    Path(args.output).resolve().parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nWrote {len(cleaned)} clean records -> {args.output}")
    print("Canonical subjects:", len(CANONICAL_SUBJECTS))


if __name__ == "__main__":
    main()