"""Seed curated visual reasoning & primary exam exemplars into the platform question bank.

Sources:
- Classroom whiteboards (img_1.jpg to img_6.jpg)
- Primary school exam papers (WA0013, WA0063)
"""

from __future__ import annotations
import json
from pathlib import Path

from app.services.diagram_templates import (
    render_horizontal_y_fork,
    render_fraction_branch,
    render_m_network,
    render_power_fork,
    render_compass_cross,
    render_horseshoe,
    render_grid_with_ear,
    render_t_bar,
    render_triangle_puzzle,
)

def build_exemplars() -> list[dict]:
    items = []

    # 1. Primary 4 Quantitative Reasoning: Archetype A1 (Horizontal Y-Fork)
    svg_a1 = render_horizontal_y_fork(1000, 820, "?", missing="child_bottom", sample_label="Sample: (176) < [62] + [114]")
    items.append({
        "subject": "Quantitative Reasoning",
        "grade_level": "Primary 4",
        "week_index": 2,
        "exam_type": "internal",
        "source_year": 2026,
        "topic": "Number Branching and Sums",
        "difficulty": "medium",
        "question_type": "multiple_choice",
        "question_text": "Study the sample: In the sample diagram, (176) branches into [62] and [114] because 62 + 114 = 176.\n\nFind the missing number (?) in the diagram below.",
        "marks": 2,
        "options": ["A. 180", "B. 200", "C. 120", "D. 280"],
        "correct_answer": "A",
        "explanation": "The circle equals the sum of the two boxes: 1000 = 820 + ?, therefore ? = 1000 - 820 = 180.",
        "diagram_svg": svg_a1,
    })

    # 2. Primary 4 Quantitative Reasoning: Archetype A2 (Fraction Branch)
    svg_a2 = render_fraction_branch(("1", "6"), ("1", "3"), ("?", "18"), missing="frac_bottom_num", sample_label="Sample: [1/5] + [2/5] -> [3/5]")
    items.append({
        "subject": "Quantitative Reasoning",
        "grade_level": "Primary 4",
        "week_index": 4,
        "exam_type": "internal",
        "source_year": 2026,
        "topic": "Fraction Pattern Trees",
        "difficulty": "medium",
        "question_type": "multiple_choice",
        "question_text": "Study the sample: [1/5] and [2/5] branch into [3/5] because 1/5 + 2/5 = 3/5.\n\nFind the missing numerator (?) in the bottom fraction box.",
        "marks": 2,
        "options": ["A. 9", "B. 6", "C. 3", "D. 12"],
        "correct_answer": "A",
        "explanation": "1/6 + 1/3 = 3/18 + 6/18 = 9/18. The missing numerator is 9.",
        "diagram_svg": svg_a2,
    })

    # 3. Primary 4 Quantitative Reasoning: Archetype B (M-Shape Network)
    svg_b = render_m_network(6, 8, "?", 12, 16, missing="center", sample_label="Sample: M-path")
    items.append({
        "subject": "Quantitative Reasoning",
        "grade_level": "Primary 4",
        "week_index": 5,
        "exam_type": "internal",
        "source_year": 2026,
        "topic": "M-Shape Arithmetic Network",
        "difficulty": "hard",
        "question_type": "multiple_choice",
        "question_text": "Study the M-shape logic from the classroom exercise:\n\nFind the missing value (?) in the center box of the M-network below.",
        "marks": 2,
        "options": ["A. 72", "B. 48", "C. 64", "D. 80"],
        "correct_answer": "A",
        "explanation": "6 × 12 = 72, which connects the top vertices to the central junction.",
        "diagram_svg": svg_b,
    })

    # 4. Primary 4 Quantitative Reasoning: Archetype C (Power Fork)
    svg_c = render_power_fork(12, 2, 24, "?", 12, missing="fork1", sample_label="Sample: (6²) -> [12] < 6, 6")
    items.append({
        "subject": "Quantitative Reasoning",
        "grade_level": "Primary 4",
        "week_index": 6,
        "exam_type": "internal",
        "source_year": 2026,
        "topic": "Powers and Factor Forks",
        "difficulty": "medium",
        "question_type": "multiple_choice",
        "question_text": "Study the sample: (6²) connects to [12] which forks into 6 and 6 (since 6 + 6 = 12 = 6 × 2).\n\nFind the missing number (?) in the upper fork below.",
        "marks": 2,
        "options": ["A. 12", "B. 24", "C. 6", "D. 18"],
        "correct_answer": "A",
        "explanation": "For (12²), the middle box is 24 = 12 + 12. The missing fork value is 12.",
        "diagram_svg": svg_c,
    })

    # 5. Primary 4 Quantitative Reasoning: Archetype D (Compass Cross)
    svg_d = render_compass_cross(20, 15, 10, 5, 2, op_top="+", op_bot="×", missing="top", sample_label="Sample: Center 20")
    items.append({
        "subject": "Quantitative Reasoning",
        "grade_level": "Primary 4",
        "week_index": 8,
        "exam_type": "internal",
        "source_year": 2026,
        "topic": "Four-Way Operation Cross",
        "difficulty": "medium",
        "question_type": "multiple_choice",
        "question_text": "Study the cross rule: Center (20) relates to Top (15) and Left (5) by 20 - 5 = 15; and Bottom (10) relates to Right (2) by 10 × 2 = 20.\n\nFind the missing number (?) in the top box.",
        "marks": 2,
        "options": ["A. 15", "B. 25", "C. 10", "D. 30"],
        "correct_answer": "A",
        "explanation": "Center (20) minus Left (5) equals 15.",
        "diagram_svg": svg_d,
    })

    # 6. Primary 4 Quantitative Reasoning: Archetype E (Horseshoe U-Shape)
    svg_e = render_horseshoe(441, 42, "?", missing="bottom", sample_label="Sample: 400 - 330 = 70")
    items.append({
        "subject": "Quantitative Reasoning",
        "grade_level": "Primary 4",
        "week_index": 9,
        "exam_type": "internal",
        "source_year": 2026,
        "topic": "Horseshoe Difference Puzzle",
        "difficulty": "easy",
        "question_type": "multiple_choice",
        "question_text": "Study the sample: Top-left (400) minus Top-right (330) gives Bottom (70).\n\nFind the missing number (?) in the bottom trough of the horseshoe below.",
        "marks": 2,
        "options": ["A. 399", "B. 401", "C. 483", "D. 389"],
        "correct_answer": "A",
        "explanation": "441 - 42 = 399.",
        "diagram_svg": svg_e,
    })

    # 7. Primary 4 Quantitative Reasoning: Archetype F (2x2 Grid with Ear)
    svg_f = render_grid_with_ear(145, 45, 185, 85, "?", missing="ear", sample_label="Sample: Grid")
    items.append({
        "subject": "Quantitative Reasoning",
        "grade_level": "Primary 4",
        "week_index": 10,
        "exam_type": "internal",
        "source_year": 2026,
        "topic": "Grid with Side Ear",
        "difficulty": "medium",
        "question_type": "multiple_choice",
        "question_text": "Study the sample grid: 101 - 67 = 34 in the side ear.\n\nFind the missing value (?) in the circular ear on the right.",
        "marks": 2,
        "options": ["A. 100", "B. 90", "C. 110", "D. 120"],
        "correct_answer": "A",
        "explanation": "145 - 45 = 100 (and 185 - 85 = 100). The value in the ear is 100.",
        "diagram_svg": svg_f,
    })

    # 8. Primary 4 Quantitative Reasoning: Archetype G (T-Bar Multiplier)
    svg_g = render_t_bar(5, 7, "?", missing="bottom", sample_label="Sample: [6] × [5] -> [30]")
    items.append({
        "subject": "Quantitative Reasoning",
        "grade_level": "Primary 4",
        "week_index": 11,
        "exam_type": "internal",
        "source_year": 2026,
        "topic": "T-Bar Multiplier",
        "difficulty": "easy",
        "question_type": "multiple_choice",
        "question_text": "Study the sample: [6] and [5] hang down to [30] because 6 × 5 = 30.\n\nFind the missing product (?) in the bottom box.",
        "marks": 2,
        "options": ["A. 35", "B. 25", "C. 40", "D. 12"],
        "correct_answer": "A",
        "explanation": "5 × 7 = 35.",
        "diagram_svg": svg_g,
    })

    # 9. Primary 3 Quantitative Reasoning: Archetype H (Triangle Puzzle from WA0063)
    svg_h = render_triangle_puzzle(9, 4, 2, "?", missing="center", sample_label="Sample: Triangle")
    items.append({
        "subject": "Quantitative Reasoning",
        "grade_level": "Primary 3",
        "week_index": 7,
        "exam_type": "internal",
        "source_year": 2026,
        "topic": "Triangle Logic Puzzle",
        "difficulty": "medium",
        "question_type": "multiple_choice",
        "question_text": "Study the sample triangle: (Top - Left) + Right = Center: (9 - 4) + 2 = 7.\n\nFind the missing center value (?) in the triangle below.",
        "marks": 2,
        "options": ["A. 7", "B. 5", "C. 8", "D. 6"],
        "correct_answer": "A",
        "explanation": "(9 - 4) + 2 = 5 + 2 = 7.",
        "diagram_svg": svg_h,
    })

    # 10. Primary 3 Mathematics: Column Addition (from WA0013)
    items.append({
        "subject": "Mathematics",
        "grade_level": "Primary 3",
        "week_index": 2,
        "exam_type": "internal",
        "source_year": 2026,
        "topic": "Addition using Expanded Method",
        "difficulty": "easy",
        "question_type": "multiple_choice",
        "question_text": "Add the following using expanded column notation:\n\n```\n   H  T  U\n   3  4  8\n+  4  3  1\n──────────\n```\nWhat is the total sum?",
        "marks": 2,
        "options": ["A. 779", "B. 769", "C. 879", "D. 789"],
        "correct_answer": "A",
        "explanation": "300 + 400 = 700; 40 + 30 = 70; 8 + 1 = 9. Total = 779.",
        "diagram_svg": None,
    })

    # 11. Primary 3 Mathematics: Column Subtraction (from WA0013)
    items.append({
        "subject": "Mathematics",
        "grade_level": "Primary 3",
        "week_index": 3,
        "exam_type": "internal",
        "source_year": 2026,
        "topic": "Subtraction of Two-Digit Numbers",
        "difficulty": "easy",
        "question_type": "multiple_choice",
        "question_text": "Subtract the following:\n\n```\n   T  U\n   7  5\n-  2  2\n───────\n```\nWhat is the result?",
        "marks": 2,
        "options": ["A. 53", "B. 57", "C. 43", "D. 52"],
        "correct_answer": "A",
        "explanation": "5 - 2 = 3; 7 - 2 = 5. Result = 53.",
        "diagram_svg": None,
    })

    # 12. Primary 3 Mathematics: Word Problem (from WA0013)
    items.append({
        "subject": "Mathematics",
        "grade_level": "Primary 3",
        "week_index": 5,
        "exam_type": "internal",
        "source_year": 2026,
        "topic": "Word Problems on Subtraction",
        "difficulty": "easy",
        "question_type": "multiple_choice",
        "question_text": "Kafayat bought 52 fresh oranges from the market. On getting home, she found that 28 of them were bad. How many good oranges does Kafayat have left?",
        "marks": 2,
        "options": ["A. 24", "B. 26", "C. 34", "D. 22"],
        "correct_answer": "A",
        "explanation": "52 - 28 = 24 good oranges.",
        "diagram_svg": None,
    })

    return items


def main():
    items = build_exemplars()
    out_path = Path("data/visual_reasoning_exemplars.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(items, indent=2), encoding="utf-8")
    print(f"Generated {len(items)} curated exemplar questions in {out_path}")


if __name__ == "__main__":
    main()
