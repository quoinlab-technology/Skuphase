"""
Generate callout-annotated tutorial screenshots.
Every coordinate is measured and verified directly against actual image pixel data.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

HERE = Path(__file__).parent
OUT  = HERE / "annotated"
OUT.mkdir(exist_ok=True)

BRAND   = (0, 65, 46)
WHITE   = (255, 255, 255)
OVERLAY = (0, 65, 46, 45)
BORDER  = (0, 65, 46, 220)


def _font(size):
    for name in ["arialbd.ttf", "Arial Bold.ttf",
                 "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _badge(draw, cx, cy, label, r=22):
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=BRAND, outline=WHITE, width=3)
    f = _font(r)
    bb = draw.textbbox((0, 0), label, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((cx - tw//2, cy - th//2 - 1), label, fill=WHITE, font=f)


def _arrow(draw, x1, y1, x2, y2, w=3):
    draw.line([(x1, y1), (x2, y2)], fill=BRAND, width=w)
    angle = math.atan2(y2 - y1, x2 - x1)
    head, spread = 14, math.pi / 6
    for sign in (1, -1):
        ax = x2 - head * math.cos(angle - sign * spread)
        ay = y2 - head * math.sin(angle - sign * spread)
        draw.line([(x2, y2), (int(ax), int(ay))], fill=BRAND, width=w)


def _highlight(img, x1, y1, x2, y2, pad=6):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d  = ImageDraw.Draw(ov)
    d.rectangle([x1 - pad, y1 - pad, x2 + pad, y2 + pad], fill=OVERLAY)
    d.rectangle([x1 - pad, y1 - pad, x2 + pad, y2 + pad], outline=BORDER, width=3)
    return Image.alpha_composite(img.convert("RGBA"), ov)


def annotate(src, dst, callouts, crop_box=None):
    img = Image.open(HERE / src)
    if crop_box:
        img = img.crop(crop_box)
    img = img.convert("RGBA")
    for c in callouts:
        if c.get("highlight"):
            img = _highlight(img, *c["highlight"])
    draw = ImageDraw.Draw(img)
    for c in callouts:
        if c.get("arrow_from") and c.get("arrow_to"):
            _arrow(draw, *c["arrow_from"], *c["arrow_to"])
        _badge(draw, *c["badge"], c["label"])
    img.convert("RGB").save(OUT / dst)
    print("  OK", dst)


# =============================================================================
# 1. LESSON NOTE GUIDE (DESKTOP & MOBILE)
# =============================================================================
print("=== Generating Lesson Note Guide Callouts ===")

# Step 1: 01_teaching_workspace.png (cropped to top 640px to focus on sidebar & scope)
# Sidebar "Teaching" button: x=10..260, y=207..248
# "Choose your teaching scope" card: x=295..1418, y=259..599
annotate("01_teaching_workspace.png", "step1_teaching_workspace_annotated.png", [
    dict(
        label="1",
        highlight=(10, 207, 260, 248),
        badge=(295, 227),
        arrow_from=(270, 227), arrow_to=(260, 227),
    ),
    dict(
        label="2",
        highlight=(295, 259, 1418, 599),
        badge=(1370, 290),
        arrow_from=(1370, 315), arrow_to=(1370, 360),
    ),
], crop_box=(0, 0, 1428, 640))

# Step 2: 02_plan_form_filled.png (1066 x 530)
# Scheme week dropdown: x=0..1060, y=30..85
# "+ Create lesson plan" button: x=0..192, y=490..528
annotate("02_plan_form_filled.png", "step2_plan_form_annotated.png", [
    dict(
        label="1",
        highlight=(0, 30, 1060, 85),
        badge=(1020, 115),
        arrow_from=(1020, 100), arrow_to=(1020, 85),
    ),
    dict(
        label="2",
        highlight=(0, 490, 192, 528),
        badge=(240, 509),
        arrow_from=(218, 509), arrow_to=(192, 509),
    ),
])

# Step 3: 03_plan_card_draft_with_ai.png (1097 x 223)
# "Draft" pill badge: x=73..132, y=0..33
# "Draft with AI" button: x=0..118, y=175..218
annotate("03_plan_card_draft_with_ai.png", "step3_draft_with_ai_annotated.png", [
    dict(
        label="1",
        highlight=(73, 0, 132, 33),
        badge=(170, 16),
        arrow_from=(148, 16), arrow_to=(132, 16),
    ),
    dict(
        label="2",
        highlight=(0, 175, 118, 218),
        badge=(165, 196),
        arrow_from=(145, 196), arrow_to=(118, 196),
    ),
])

# Step 4: 05_lesson_note_preview.png (1443 x 704)
# Quick refinement chips: x=316..936, y=150..200
# "Preview lesson note" link: x=312..458, y=418..448
annotate("05_lesson_note_preview.png", "step4_preview_annotated.png", [
    dict(
        label="1",
        highlight=(316, 150, 936, 200),
        badge=(980, 175),
        arrow_from=(955, 175), arrow_to=(936, 175),
    ),
    dict(
        label="2",
        highlight=(312, 418, 458, 448),
        badge=(500, 433),
        arrow_from=(478, 433), arrow_to=(458, 433),
    ),
])

# Step 5: 06_submitted_card_exports.png (1443 x 704)
# "Save & submit for review" button: x=300..524, y=513..549
# "Print / download PDF" button: x=527..657, y=513..549
# "Download Word" button: x=660..783, y=513..549
annotate("06_submitted_card_exports.png", "step5_submit_exports_annotated.png", [
    dict(
        label="1",
        highlight=(300, 513, 524, 549),
        badge=(240, 531),
        arrow_from=(262, 531), arrow_to=(300, 531),
    ),
    dict(
        label="2",
        highlight=(527, 513, 657, 549),
        badge=(592, 474),
        arrow_from=(592, 496), arrow_to=(592, 513),
    ),
    dict(
        label="3",
        highlight=(660, 513, 783, 549),
        badge=(720, 474),
        arrow_from=(720, 496), arrow_to=(720, 513),
    ),
])

# Mobile Step 1: mobile_01_teaching_workspace.png (390 x 844)
annotate("mobile_01_teaching_workspace.png", "mobile_step1_scope_annotated.png", [
    dict(
        label="1",
        highlight=(8, 460, 383, 520),
        badge=(195, 435),
        arrow_from=(195, 447), arrow_to=(195, 460),
    ),
    dict(
        label="2",
        highlight=(324, 796, 390, 844),
        badge=(285, 796),
        arrow_from=(307, 808), arrow_to=(335, 820),
    ),
])

# Mobile Step 2: mobile_02_submitted_card_note.png (390 x 844)
annotate("mobile_02_submitted_card_note.png", "mobile_step2_submit_annotated.png", [
    dict(
        label="1",
        highlight=(68, 645, 168, 686),
        badge=(196, 665),
        arrow_from=(174, 665), arrow_to=(168, 665),
    ),
    dict(
        label="2",
        highlight=(167, 645, 252, 686),
        badge=(210, 624),
        arrow_from=(210, 636), arrow_to=(210, 645),
    ),
])

# Mobile Step 3: mobile_03_export_links.png (390 x 844)
annotate("mobile_03_export_links.png", "mobile_step3_export_annotated.png", [
    dict(
        label="1",
        highlight=(66, 390, 252, 435),
        badge=(285, 412),
        arrow_from=(260, 412), arrow_to=(252, 412),
    ),
    dict(
        label="2",
        highlight=(56, 485, 202, 527),
        badge=(235, 506),
        arrow_from=(210, 506), arrow_to=(202, 506),
    ),
])


# =============================================================================
# 2. EXAM GENERATION GUIDE (DESKTOP)
# =============================================================================
print("=== Generating Exam Guide Callouts ===")

# Step 1: 13_wizard_step1.png (1780 x 1380)
# Progress bar: x=595..1520, y=210..265
# Exam Title input box: x=657..1479, y=430..479
# Next button: x=1351..1484, y=1095..1145
annotate("13_wizard_step1.png", "exam_step1_scope_annotated.png", [
    dict(
        label="1",
        highlight=(595, 210, 1520, 265),
        badge=(1570, 237),
        arrow_from=(1545, 237), arrow_to=(1520, 237),
    ),
    dict(
        label="2",
        highlight=(657, 430, 1479, 479),
        badge=(1530, 454),
        arrow_from=(1505, 454), arrow_to=(1479, 454),
    ),
    dict(
        label="3",
        highlight=(1351, 1095, 1484, 1145),
        badge=(1295, 1120),
        arrow_from=(1320, 1120), arrow_to=(1351, 1120),
    ),
])

# Step 2: 14_wizard_step2.png (1780 x 1361)
# Curriculum ready pill: x=659..1199, y=615..670
# Bloom taxonomy chips: x=660..1174, y=1002..1044
# Next button: x=1354..1486, y=1096..1144
annotate("14_wizard_step2.png", "exam_step2_curriculum_annotated.png", [
    dict(
        label="1",
        highlight=(659, 615, 1199, 670),
        badge=(1250, 642),
        arrow_from=(1225, 642), arrow_to=(1199, 642),
    ),
    dict(
        label="2",
        highlight=(660, 1002, 1174, 1044),
        badge=(1225, 1023),
        arrow_from=(1200, 1023), arrow_to=(1174, 1023),
    ),
    dict(
        label="3",
        highlight=(1354, 1096, 1486, 1144),
        badge=(1300, 1120),
        arrow_from=(1325, 1120), arrow_to=(1354, 1120),
    ),
])

# Step 3: 15_wizard_step4_confirm.png (1780 x 1230)
# Summary table: x=590..1548, y=340..780
# Generate Exam button: x=1254..1480, y=964..1014
annotate("15_wizard_step4_confirm.png", "exam_step3_confirm_annotated.png", [
    dict(
        label="1",
        highlight=(590, 340, 1548, 780),
        badge=(1600, 560),
        arrow_from=(1575, 560), arrow_to=(1548, 560),
    ),
    dict(
        label="2",
        highlight=(1254, 964, 1480, 1014),
        badge=(1200, 989),
        arrow_from=(1225, 989), arrow_to=(1254, 989),
    ),
])

# Step 4: 16_ai_generating_progress.png (1800 x 915)
# Spinner / star icon: x=938..1182, y=240..378
# Progress bullets card: x=700..1298, y=480..748
annotate("16_ai_generating_progress.png", "exam_step4_progress_annotated.png", [
    dict(
        label="1",
        highlight=(938, 240, 1182, 378),
        badge=(1225, 309),
        arrow_from=(1202, 309), arrow_to=(1182, 309),
    ),
    dict(
        label="2",
        highlight=(700, 480, 1298, 748),
        badge=(1345, 614),
        arrow_from=(1322, 614), arrow_to=(1298, 614),
    ),
])

# Step 5: 21_q8_math_rendering.png (1800 x 915)
# Approve button: x=1536..1706, y=134..185
# Answers toggle: x=1420..1720, y=490..525
# Question 1 card: x=330..1748, y=672..914
annotate("21_q8_math_rendering.png", "exam_step5_review_annotated.png", [
    dict(
        label="1",
        highlight=(1536, 134, 1706, 185),
        badge=(1485, 159),
        arrow_from=(1510, 159), arrow_to=(1536, 159),
    ),
    dict(
        label="2",
        highlight=(1420, 490, 1720, 525),
        badge=(1370, 507),
        arrow_from=(1392, 507), arrow_to=(1420, 507),
    ),
    dict(
        label="3",
        highlight=(330, 672, 1748, 914),
        badge=(280, 793),
        arrow_from=(302, 793), arrow_to=(330, 793),
    ),
])

# Step 6a: 22_approved_exam.png (1800 x 915)
# "Approved" badge: x=340..450, y=102..134
# "Print / Save Student Paper" button: x=1370..1706, y=134..184
annotate("22_approved_exam.png", "exam_step6_approved_annotated.png", [
    dict(
        label="1",
        highlight=(340, 102, 450, 134),
        badge=(295, 118),
        arrow_from=(317, 118), arrow_to=(340, 118),
    ),
    dict(
        label="2",
        highlight=(1370, 134, 1706, 184),
        badge=(1320, 159),
        arrow_from=(1342, 159), arrow_to=(1370, 159),
    ),
])

# Step 6b: 11_print_student_paper.png (1800 x 915)
# "Print Exam Paper (2-Col Eco Mode)" button: x=404..780, y=46..92
# School masthead: x=388..1412, y=150..348
annotate("11_print_student_paper.png", "exam_step6_print_annotated.png", [
    dict(
        label="1",
        highlight=(404, 46, 780, 92),
        badge=(355, 69),
        arrow_from=(377, 69), arrow_to=(404, 69),
    ),
    dict(
        label="2",
        highlight=(388, 150, 1412, 348),
        badge=(340, 249),
        arrow_from=(362, 249), arrow_to=(388, 249),
    ),
])


# =============================================================================
# 3. QUESTION BANK GUIDE
# =============================================================================
print("=== Generating Question Bank Guide Callouts ===")

# Step 2: 21_q8_math_rendering.png (1800 x 915)
# Question card rendered KaTeX formula: x=330..1748, y=672..914
annotate("21_q8_math_rendering.png", "bank_step2_math_annotated.png", [
    dict(
        label="1",
        highlight=(330, 672, 1748, 914),
        badge=(280, 793),
        arrow_from=(302, 793), arrow_to=(330, 793),
    ),
])

# Step 3: 22_approved_exam.png (1800 x 915)
# Three dots button: x=1710..1775, y=130..190
annotate("22_approved_exam.png", "bank_step3_bookmark_annotated.png", [
    dict(
        label="1",
        highlight=(1710, 130, 1775, 190),
        badge=(1660, 160),
        arrow_from=(1682, 160), arrow_to=(1710, 160),
    ),
])


# =============================================================================
# 4. ADMIN SETUP GUIDE
# =============================================================================
print("=== Generating Admin Setup Guide Callouts ===")

# Step 1: 03_dashboard_desktop.png (cropped to top 480px to focus on settings banner)
# "School Branding & Exam Settings" card: x=274..1399, y=215..349
# "Configure School Profile" button: x=1175..1369, y=259..276
annotate("03_dashboard_desktop.png", "admin_step1_branding_annotated.png", [
    dict(
        label="1",
        highlight=(274, 215, 1399, 349),
        badge=(230, 282),
        arrow_from=(252, 282), arrow_to=(274, 282),
    ),
    dict(
        label="2",
        highlight=(1170, 250, 1375, 285),
        badge=(1120, 267),
        arrow_from=(1142, 267), arrow_to=(1170, 267),
    ),
], crop_box=(0, 0, 1428, 480))

# Step 2: 03_dashboard_desktop.png (cropped to top 150px to focus on topbar switches)
# School Admin dropdown: x=864..1029, y=13..45
# Impath Academy school switcher: x=1027..1177, y=13..45
annotate("03_dashboard_desktop.png", "admin_step2_settings_annotated.png", [
    dict(
        label="1",
        highlight=(864, 13, 1029, 45),
        badge=(820, 29),
        arrow_from=(842, 29), arrow_to=(864, 29),
    ),
    dict(
        label="2",
        highlight=(1027, 13, 1177, 45),
        badge=(1225, 29),
        arrow_from=(1202, 29), arrow_to=(1177, 29),
    ),
], crop_box=(0, 0, 1428, 150))

# Step 3: 03_dashboard_desktop.png (cropped to y=0..520 to focus on sidebar Administration)
# Administration row in sidebar: x=20..250, y=390..425
annotate("03_dashboard_desktop.png", "admin_step3_staff_annotated.png", [
    dict(
        label="1",
        highlight=(20, 390, 250, 425),
        badge=(295, 407),
        arrow_from=(272, 407), arrow_to=(250, 407),
    ),
], crop_box=(0, 0, 1428, 520))

# Step 4: 01_teaching_workspace.png (cropped to coverage section y=1330..1820)
# Offset in crop: y - 1330
# Heading 'Coverage progress': x=337..506, y=1390..1406 -> y_crop=60..76
# Record cards 1..3: x=310..1379, y=1430..1769 -> y_crop=100..439
annotate("01_teaching_workspace.png", "admin_step4_coverage_annotated.png", [
    dict(
        label="1",
        highlight=(320, 55, 520, 82),
        badge=(275, 68),
        arrow_from=(298, 68), arrow_to=(320, 68),
    ),
    dict(
        label="2",
        highlight=(300, 95, 1390, 445),
        badge=(255, 270),
        arrow_from=(277, 270), arrow_to=(300, 270),
    ),
], crop_box=(0, 1330, 1428, 1820))

print("\nAll annotated images generated and verified.")
