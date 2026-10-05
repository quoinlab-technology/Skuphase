"""Small, deterministic question-bank exchange formats.

The exchange layer deliberately operates on plain dictionaries so it can be
used by API uploads, admin tools, and future DOCX adapters without coupling
those transports to SQLAlchemy models.
"""
from __future__ import annotations

import csv
import io
import json
import re
from xml.etree.ElementTree import Element, SubElement, tostring, fromstring


_XML_ILLEGAL_CONTROLS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def _xml_safe_text(value) -> str:
    """Remove only characters that XML 1.0 (and therefore DOCX) forbids."""
    return _XML_ILLEGAL_CONTROLS.sub("", str(value or ""))


CSV_FIELDS = (
    "question_number", "type", "question_text", "marks", "options",
    "correct_answer", "explanation", "marking_scheme", "content_blocks",
)


def export_csv(questions: list[dict]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for question in questions:
        row = {field: question.get(field, "") for field in CSV_FIELDS}
        for field in ("options", "marking_scheme", "content_blocks"):
            value = row[field]
            row[field] = json.dumps(value, ensure_ascii=False) if value not in (None, "") else ""
        writer.writerow(row)
    return output.getvalue()


def import_csv(payload: str) -> list[dict]:
    rows = []
    for row in csv.DictReader(io.StringIO(payload)):
        item = dict(row)
        item["question_number"] = int(item.get("question_number") or len(rows) + 1)
        item["marks"] = int(item.get("marks") or 1)
        for field in ("options", "marking_scheme", "content_blocks"):
            raw = item.get(field) or ""
            item[field] = json.loads(raw) if raw else None
        rows.append(item)
    return rows


def export_gift(questions: list[dict]) -> str:
    blocks = []
    for question in questions:
        stem = str(question.get("question_text") or "").replace("=", "\\=")
        options = question.get("options") or []
        if options:
            correct = str(question.get("correct_answer") or "").strip().upper()
            choices = []
            for index, option in enumerate(options):
                letter = chr(65 + index)
                prefix = "=" if correct in {letter, f"{letter}."} else "~"
                choices.append(f"{prefix}{str(option).lstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ. ')}")
            body = " {" + " ".join(choices) + "}"
        else:
            body = " {}"
        blocks.append(f"::Q{question.get('question_number', len(blocks) + 1)}::{stem}{body}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def import_gift(payload: str) -> list[dict]:
    questions = []
    pattern = re.compile(r"::[^:]+::(.*?)(?:\{(.*?)\})?(?:\n|$)", re.DOTALL)
    for match in pattern.finditer(payload):
        stem = match.group(1) or ""
        choices = match.group(2) or ""
        options, correct = [], None
        for choice in choices.split(" "):
            choice = choice.strip()
            if not choice:
                continue
            marker, text = choice[0], choice[1:]
            options.append(text)
            if marker == "=":
                correct = chr(64 + len(options))
        questions.append({
            "question_number": len(questions) + 1,
            "type": "multiple_choice" if options else "short_answer",
            "question_text": stem.strip(), "marks": 1,
            "options": options or None, "correct_answer": correct,
        })
    return questions


def export_qti(questions: list[dict]) -> str:
    root = Element("assessmentItem", {"identifier": "skuphase-export", "title": "SkuPhase Questions"})
    for index, question in enumerate(questions, 1):
        item = SubElement(root, "item", {"identifier": f"q{index}", "title": f"Question {index}"})
        body = SubElement(item, "itemBody")
        SubElement(body, "p").text = str(question.get("question_text") or "")
        response = SubElement(item, "responseDeclaration", {"identifier": "RESPONSE", "cardinality": "single", "baseType": "identifier"})
        correct = str(question.get("correct_answer") or "")
        SubElement(response, "correctResponse").append(Element("value"))
        response[0][0].text = correct
    return tostring(root, encoding="unicode")


def import_qti(payload: str) -> list[dict]:
    root = fromstring(payload)
    questions = []
    for item in root.findall(".//item"):
        paragraph = item.find("./itemBody/p")
        correct = item.find("./responseDeclaration/correctResponse/value")
        questions.append({
            "question_number": len(questions) + 1,
            "type": "short_answer", "question_text": paragraph.text if paragraph is not None else "",
            "marks": 1, "options": None, "correct_answer": correct.text if correct is not None else None,
        })
    return questions


def export_docx(questions: list[dict]) -> bytes:
    """Create a portable DOCX question list (requires python-docx)."""
    from docx import Document

    document = Document()
    for index, question in enumerate(questions, 1):
        paragraph = document.add_paragraph()
        paragraph.add_run(f"{index}. ").bold = True
        paragraph.add_run(_xml_safe_text(question.get("question_text")))
        for option in question.get("options") or []:
            document.add_paragraph(_xml_safe_text(option), style="List Bullet")
        if question.get("marking_scheme"):
            document.add_paragraph("Marking scheme:")
            for point in question["marking_scheme"]:
                document.add_paragraph(_xml_safe_text(point), style="List Bullet 2")
    stream = io.BytesIO()
    document.save(stream)
    return stream.getvalue()


def import_docx(payload: bytes) -> list[dict]:
    """Read the plain question structure produced by :func:`export_docx`."""
    from docx import Document

    document = Document(io.BytesIO(payload))
    questions = []
    current = None
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        match = re.match(r"^(\d+)\.\s+(.*)$", text)
        if match:
            current = {
                "question_number": int(match.group(1)), "type": "short_answer",
                "question_text": match.group(2), "marks": 1, "options": [],
            }
            questions.append(current)
        elif current is not None and paragraph.style.name.startswith("List"):
            current.setdefault("marking_scheme", []).append(text)
    return questions
