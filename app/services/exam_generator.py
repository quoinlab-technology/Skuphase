"""Exam generation service — curriculum-first SQL retrieval + single LLM call."""

import json
import logging
import re
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from app.models.exam import Exam, Question, ExamPassage
from app.models.question import QuestionRefinement
from app.schemas.exam import ExamGenerationRequest, SectionConfig
from app.services.exam_quality_validator import (
    ExamQualityValidator,
    normalize_bloom_level,
)
from app.services.curriculum_service import CurriculumService
from app.services.few_shot_selector import FewShotSelector
from app.core.llm import get_llm_service
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _attach_authoritative_passages(parsed, sections):
    """Attach the teacher-supplied passage to each parsed section.

    The LLM never rewrites the passage; the authoritative requested text wins.
    The validator uses it for anti-hallucination grounding and store_exam
    persists it.
    """
    by_number = {s.section_number: s for s in sections}
    for sec in parsed.get("sections", []):
        cfg = by_number.get(sec.get("section_number"))
        if cfg and getattr(cfg, "passage", None):
            sec["passage"] = {"title": cfg.passage.title or "", "body": cfg.passage.body}


def _normalize_exam_bloom_levels(parsed):
    """Canonicalize every question's bloom_level after LLM parsing.

    LLMs are inconsistent about case and British/American spelling (e.g.
    "Analyse" vs "analyze"). We normalize here so the value persisted via
    store_exam and compared during quality validation is always canonical;
    this prevents a valid British-spelled level from failing validation.
    """
    for section in parsed.get("sections", []):
        for q in section.get("questions", []):
            normalized = normalize_bloom_level(q.get("bloom_level"))
            if normalized is not None:
                q["bloom_level"] = normalized


# Characters that may legally follow a closing string quote in JSON.
_JSON_STRUCTURAL_CHARS = (",", ":", "}", "]")


def _repair_json_text(text: str) -> str:
    """Best-effort repair of common LLM JSON defects (string-aware).

    Single pass over the text that fixes:
    * Invalid backslash escapes inside strings — e.g. LaTeX ``\\ce{...}`` or
      ``\\frac{...}`` emitted with a single backslash, which ``json.loads``
      rejects with "Invalid \\escape".
    * Unescaped quote characters embedded inside string values, which
      otherwise close the string early and produce "Expecting ',' delimiter".
    * Trailing commas before ``]`` / ``}``.

    Returns the repaired text, or the input unchanged when nothing looked
    broken so callers can detect "no repair possible".
    """
    out: List[str] = []
    i = 0
    n = len(text)
    in_str = False
    changed = False
    while i < n:
        ch = text[i]
        if in_str:
            if ch == "\\":
                nxt = text[i + 1] if i + 1 < n else ""
                if nxt in ('"', "\\", "/", "b", "f", "n", "r", "t"):
                    out.append(ch)
                    out.append(nxt)
                    i += 2
                    continue
                if (
                    nxt == "u"
                    and i + 5 < n
                    and all(c in "0123456789abcdefABCDEF" for c in text[i + 2 : i + 6])
                ):
                    out.append(text[i : i + 6])
                    i += 6
                    continue
                # Invalid escape (or dangling backslash): keep it literal by
                # escaping the backslash, e.g. \ce{X} -> \\ce{X}.
                out.append("\\\\")
                changed = True
                i += 1
                continue
            if ch == '"':
                # Closing quote, or an unescaped quote embedded in the value?
                # Peek ahead: only a structural character (or EOF) may legally
                # follow a real closing quote; anything else means the quote
                # was part of the value and must be escaped.
                j = i + 1
                while j < n and text[j] in " \t\r\n":
                    j += 1
                if j >= n or text[j] in _JSON_STRUCTURAL_CHARS:
                    in_str = False
                    out.append(ch)
                    i += 1
                    continue
                out.append('\\"')
                changed = True
                i += 1
                continue
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == ",":
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j >= n or text[j] in "]}":
                # Trailing comma with nothing after it: drop it.
                changed = True
                i += 1
                continue
        out.append(ch)
        i += 1
    return "".join(out) if changed else text



def utc_now() -> datetime:
    """Timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class ExamGenerator:
    """Service for generating exams from official scheme-of-work objectives,
    curated few-shot examples and one LLM call."""

    def __init__(self):
        self.quality_validator = ExamQualityValidator()
        self.few_shot_selector = FewShotSelector()
        self.llm_service = get_llm_service()

    @staticmethod
    def _resolve_optimal_provider(subject: str, grade_level: str, total_questions: int) -> str:
        """
        Class level, subject, and question volume aware provider routing.

        - Senior Secondary STEM (SSS 1-3 Physics, Chemistry, Further Maths, Technical Drawing, Biology):
          Requires deep equation balancing, stoichiometry, calculus, and scientific accuracy -> Gemini.
        - High question volume (> 30 questions):
          Requires high token headroom (up to 8,192 tokens) -> Gemini.
        - Primary & Junior Secondary (Primary 1-6, JSS 1-3) with <= 30 questions:
          Requires rapid turnaround and low complexity -> Groq (sub-6s LPU inference).
        """
        subj = (subject or "").lower()
        grade = (grade_level or "").lower()

        is_senior = any(s in grade for s in ["sss", "ss 1", "ss 2", "ss 3", "ss1", "ss2", "ss3", "senior"])
        is_stem = any(s in subj for s in [
            "physics", "chemistry", "further math", "technical drawing", "biology",
            "calculus", "organic", "mechanics"
        ])

        if is_senior and is_stem:
            return "gemini"

        if total_questions > 30:
            return "gemini"

        return "groq"

    async def generate_exam(
        self,
        request: ExamGenerationRequest,
        school_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        db: AsyncSession,
        exam_id: Optional[uuid.UUID] = None,
    ) -> Exam:
        """
        Generate exam with flexible configuration.

        Args:
            request: Exam generation request with sections
            school_id: School ID for data isolation
            created_by_user_id: User creating the exam
            db: Database session

        Returns:
            Generated exam with questions

        Raises:
            ValueError: If generation fails
        """
        stage = "initialise"
        request_exam_id = str(exam_id) if exam_id else "unknown"
        total_questions = sum(s.num_questions for s in request.sections)
        try:
            logger.info(
                "generation.start exam_id=%s subject=%s grade=%s term=%s questions=%s sections=%s",
                request_exam_id,
                request.subject,
                request.grade_level,
                request.term,
                total_questions,
                len(request.sections),
            )

            # 1. Retrieve curriculum context (scheme of work + few-shot examples)
            stage = "retrieve_context"
            curriculum_context = await self.retrieve_context(
                subject=request.subject,
                grade_level=request.grade_level,
                term=request.term,
                selected_weeks=request.selected_weeks,
                db=db,
            )
            logger.info(
                "generation.context_ready exam_id=%s scheme=%s few_shot=%s",
                request_exam_id,
                curriculum_context.get("has_scheme_data"),
                curriculum_context.get("few_shot_count"),
            )

            # 2. Build dynamic prompt
            stage = "build_prompt"
            prompt = self.build_prompt(request, curriculum_context)
            logger.info("generation.prompt_ready exam_id=%s prompt_chars=%s", request_exam_id, len(prompt))

            # Release the read transaction so no DB connection/lock is held
            # across the long LLM await (session discipline).
            await db.commit()

            # 3. Single LLM call
            # Validate total question count against configured admin limit
            max_allowed = getattr(settings, "max_questions_per_exam", 50)
            if total_questions > max_allowed:
                raise ValueError(
                    f"Total questions ({total_questions}) exceeds the configured limit of {max_allowed} questions per exam. "
                    "Please reduce questions or generate in separate sections."
                )

            # Intelligent Class & Subject Router
            stage = "llm_provider_selection"
            preferred_provider = self._resolve_optimal_provider(
                subject=request.subject,
                grade_level=request.grade_level,
                total_questions=total_questions,
            )

            # Dynamic token budget:
            # - Gemini has no strict OTPM ceiling and uses output tokens for internal reasoning + comprehensive JSON.
            #   Give Gemini the full 8,192 tokens so it never truncates mid-exam.
            # - Groq has strict 6K OTPM limits; cap at 5,100 to stay safely below rate limits.
            if preferred_provider == "gemini":
                dynamic_max_tokens = 8192
            else:
                max_token_ceiling = 7500 if getattr(self.llm_service, "gemini_api_key", None) else 5100
                dynamic_max_tokens = min(max_token_ceiling, max(1200, total_questions * 180 + 400))

            logger.info(
                "generation.llm_selected exam_id=%s provider=%s subject=%s grade=%s questions=%s max_tokens=%s",
                request_exam_id,
                preferred_provider.upper(),
                request.subject,
                request.grade_level,
                total_questions,
                dynamic_max_tokens,
            )

            stage = f"llm_call:{preferred_provider}"
            llm_response = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=dynamic_max_tokens,
                preferred_provider=preferred_provider,
            )

            logger.info(
                "generation.llm_succeeded exam_id=%s provider=%s model=%s tokens=%s cost=%s content_chars=%s content_shape=%s",
                request_exam_id,
                llm_response.get("provider", preferred_provider),
                llm_response.get("model"),
                llm_response.get("tokens_used"),
                llm_response.get("cost", 0),
                len(llm_response.get("content") or ""),
                "json_object" if (llm_response.get("content") or "").lstrip().startswith("{") else "non_json_or_empty",
            )

            # 4. Parse response (section-aware)
            stage = "parse_response"
            try:
                parsed_exam = self.parse_response(
                    llm_response["content"],
                    request.sections,
                )
            except ValueError as parse_error:
                # A provider can return a successful HTTP response while
                # still emitting malformed JSON. Retry once with a stricter
                # instruction rather than storing a partial paper or failing
                # immediately. The bounded retry is intentionally here, after
                # transport/provider retries, so it cannot multiply outages.
                logger.warning(
                    "generation.parse_retry exam_id=%s provider=%s error=%s",
                    request_exam_id,
                    llm_response.get("provider", preferred_provider),
                    str(parse_error)[:240],
                )
                retry_prompt = (
                    prompt
                    + "\n\nIMPORTANT RECOVERY INSTRUCTION: Your previous response was not valid JSON. "
                    "Return ONLY one complete JSON object matching the requested schema. "
                    "Do not use markdown fences, comments, ellipses, or trailing text. "
                    "Complete every requested question before closing the JSON object."
                )
                llm_response = await self.llm_service.generate(
                    prompt=retry_prompt,
                    temperature=0.2,
                    max_tokens=dynamic_max_tokens,
                    preferred_provider=preferred_provider,
                )
                parsed_exam = self.parse_response(
                    llm_response["content"],
                    request.sections,
                )
            logger.info("generation.response_parsed exam_id=%s sections=%s", request_exam_id, len(parsed_exam.get("sections", [])))
            stage = "quality_validation"
            validation = self.quality_validator.validate_or_raise(
                parsed_exam=parsed_exam,
                request=request,
            )
            for warning in validation.warnings:
                logger.warning("Generation quality warning: %s", warning)
            logger.info("Generation quality metrics: %s", validation.metrics)

            # 5. Store exam
            stage = "store_exam"
            exam = await self.store_exam(
                parsed_exam=parsed_exam,
                request=request,
                school_id=school_id,
                created_by_user_id=created_by_user_id,
                llm_response=llm_response,
                db=db,
                exam_id=exam_id,
            )

            logger.info("generation.succeeded exam_id=%s", exam.id)
            return exam

        except Exception as e:
            logger.exception(
                "generation.failed exam_id=%s stage=%s subject=%s grade=%s questions=%s error_type=%s",
                request_exam_id,
                stage,
                request.subject,
                request.grade_level,
                total_questions,
                type(e).__name__,
            )
            raise ValueError(f"Exam generation failed at {stage}: {str(e)}") from e

    async def retrieve_context(
        self,
        subject: str,
        grade_level: str,
        term: Optional[str],
        selected_weeks: Optional[List[int]],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Retrieve curriculum context: official NERDC Scheme of Work objectives
        plus curated few-shot past-question examples (SQL-only lookups).
        """
        context_blocks: List[str] = []
        has_scheme_data = False
        few_shot_count = 0

        # 1. Fetch official NERDC Scheme of Work objectives if weeks/term specified
        if selected_weeks and term:
            try:
                scheme_data = await CurriculumService.get_objectives_for_weeks(
                    class_level=grade_level,
                    subject_name=subject,
                    term=term,
                    selected_weeks=selected_weeks,
                    db=db,
                )
                if scheme_data:
                    has_scheme_data = True
                    lines = [f"OFFICIAL NERDC SCHEME OF WORK ({grade_level} {subject} - {term}):"]
                    for item in scheme_data:
                        lines.append(f"\n[Week {item['week_number']}: {item['topic']}]")
                        for obj in item.get("subtopics", []):
                            lines.append(f"  • {obj}")
                    context_blocks.append("\n".join(lines))
                    logger.info("Injected %s scheme-of-work weeks into prompt context", len(scheme_data))
            except Exception as e:
                logger.warning("Could not fetch scheme of work for %s %s: %s", grade_level, subject, str(e))

        # 2. Few-shot examples from the PLATFORM question bank only
        #    (owner_type='platform'; school-contributed items never leak here).
        try:
            examples = await self.few_shot_selector.select(
                db=db,
                subject=subject,
                grade_level=grade_level,
                week_indices=selected_weeks,
                term=term,
            )
            few_shot_count = len(examples)
            if examples:
                ex_lines = [
                    f"PAST QUESTION EXAMPLES ({grade_level} {subject}):",
                    "Match the style, difficulty and phrasing of these real questions:",
                ]
                for i, ex in enumerate(examples, start=1):
                    tag = ex.get("source_tag", "Question Bank")
                    week_bit = (
                        f" [Week {ex['week_index']}]" if ex.get("week_index") else ""
                    )
                    ex_lines.append(f"\nExample {i} ({tag}{week_bit}):")
                    ex_lines.append(ex["question_text"])
                    if ex.get("options"):
                        for opt in ex["options"]:
                            ex_lines.append(f"  {opt}")
                    elif ex.get("question_type") == "essay":
                        marks_bit = f" ({ex['marks']} marks)" if ex.get("marks") else ""
                        ex_lines.append(f"  [Essay question{marks_bit}]")
                    if ex.get("diagram_svg"):
                        ex_lines.append(f"  [Diagram SVG]: {ex['diagram_svg']}")
                context_blocks.append("\n".join(ex_lines))
                logger.info("Injected %s few-shot past-question examples", len(examples))
        except Exception as e:
            logger.warning("Few-shot selection skipped: %s", str(e))

        if not context_blocks:
            context_blocks.append(f"Standard National Curriculum for Nigerian Schools: {subject} ({grade_level}).")

        combined_context = "\n\n═══════════════════════════════════════════════════════════════\n\n".join(context_blocks)

        return {
            "combined_context": combined_context,
            "has_scheme_data": has_scheme_data,
            "few_shot_count": few_shot_count,
        }
    
    def build_prompt(
        self,
        request: ExamGenerationRequest,
        curriculum_context: Dict[str, Any],
    ) -> str:
        """
        Build exam generation prompt dynamically based on configuration.

        Args:
            request: Exam generation request
            curriculum_context: Curriculum context from scheme of work + few-shot

        Returns:
            Complete prompt for LLM
        """
        # Calculate totals
        total_questions = sum(s.num_questions for s in request.sections)
        total_marks = self._calculate_total_marks(request.sections)

        # Build section instructions
        section_instructions = self._build_section_instructions(request.sections)

        difficulty_block = self._build_difficulty_instructions(request.difficulty_distribution)
        primary_layout_block = self._build_primary_layout_instructions(request)
        language_block = self._build_language_instructions(request.language)
        blueprint_block = ""
        if request.blueprint:
            blueprint = request.blueprint
            blueprint_block = "\nBLUEPRINT CONSTRAINT (MUST FOLLOW):\n" + "\n".join(
                f"- Topic: {s.topic}; Bloom: {s.bloom}; Questions: {s.questions}; Marks: {s.marks}"
                for s in blueprint.sections
            ) + "\nDo not substitute topics or Bloom levels without stating a warning.\n"

        # Build base prompt
        prompt = f"""You are an expert Nigerian school examiner creating high-quality exam questions for {request.subject} at {request.grade_level} level.

═══════════════════════════════════════════════════════════════
SECTION 1: CURRICULUM CONTEXT
═══════════════════════════════════════════════════════════════

{curriculum_context['combined_context']}

→ All questions MUST align with this curriculum content.
→ Use terminology and examples from the provided context.

═══════════════════════════════════════════════════════════════
SECTION 2: NIGERIAN EDUCATION CONTEXT & PEDAGOGY
═══════════════════════════════════════════════════════════════

Language & Style:
• British English spelling (colour, honour, organise, practise, realise)
• Formal but clear language appropriate for {request.grade_level}
• Command words: State, Outline, Explain, Discuss, Calculate, Describe

Cultural Context:
• Use Nigerian names: Chidi, Amina, Tunde, Ngozi, Emeka, Fatima
• Local examples: agriculture, commerce, harmattan season, geographical zones
• Locations: Lagos, Kano, Abuja, Ibadan, Port Harcourt, Enugu, Kaduna
• Units: Metric system (km, kg, litres) + Naira (₦) for money

Pedagogy & Distractor Craft (Strict Standard):
• For Multiple Choice Questions, distractors MUST be plausible and based on common student misconceptions or typical calculation missteps.
• NEVER use absurd options or lazy filler distractors.
• For Chemistry formulas, ALWAYS use mhchem notation inside LaTeX: $\\ce{{...}}$ (e.g. $\\ce{{H2SO4}}$, $\\ce{{CuSO4}}$, $\\ce{{2H2 + O2 -> 2H2O}}$).
• For Mathematics, write formulas in clean LaTeX: e.g. $x = \\frac{{-b \\pm \\sqrt{{b^2 - 4ac}}}}{{2a}}$.
• Explanations must be concise and pedagogical (1 to 2 clear sentences maximum per question). Do not output lengthy, verbose essays for explanations.

═══════════════════════════════════════════════════════════════
SECTION 3: EXAM STRUCTURE
═══════════════════════════════════════════════════════════════

Total Questions: {total_questions}
Total Marks: {total_marks}
Duration: {request.duration_minutes} minutes

{section_instructions}

{difficulty_block}

{self._build_custom_instructions(request.custom_instructions)}

{language_block}

{primary_layout_block}

{blueprint_block}

═══════════════════════════════════════════════════════════════
SECTION 4: OUTPUT FORMAT (STRICT JSON)
═══════════════════════════════════════════════════════════════

Return ONLY valid JSON in this exact format (no markdown, no preamble):

{self._build_json_example(request.sections)}

<internal_planning>
Before producing the JSON, silently verify curriculum coverage, mark totals,
question-type constraints, answer keys, and age-appropriate Nigerian context.
Do not include this planning or these tags in the response.
</internal_planning>

<final_output>
Generate the complete exam now. Ensure:
• All {total_questions} questions are included
• Total marks sum to exactly {total_marks}
• Questions are original, educationally sound, and Nigerian-appropriate
• Every question tests content from the curriculum
• Explanations are crisp, clear, and limited to 1-2 sentences per question
• JSON is valid and parseable
• Follow section-specific instructions exactly

Output ONLY the JSON. No additional text before or after.
</final_output>
"""
        
        return prompt
    
    def _build_section_instructions(self, sections: List[SectionConfig]) -> str:
        """Build section-specific instructions for prompt."""
        instructions = []
        
        for section in sections:
            inst = f"""
SECTION {section.section_number}: {section.section_title}
{'─'*60}
• Question Type: {section.question_type}
• Number of Questions: {section.num_questions}
"""
            
            # Add instruction type
            if section.instruction_type == "answer_all":
                inst += "• Instruction: Answer ALL questions\n"
            elif section.instruction_type == "answer_any_n":
                inst += f"• Instruction: Answer ANY {section.answer_count} questions\n"
            elif section.instruction_type == "compulsory_plus_optional":
                compulsory = ", ".join(map(str, section.compulsory_questions))
                optional_count = section.answer_count - len(section.compulsory_questions)
                inst += f"• Instruction: Answer Question(s) {compulsory} (compulsory) and any other {optional_count} question(s)\n"
            
            # Add sub-part style
            if section.sub_part_style != "none":
                style_map = {
                    "roman": "(i), (ii), (iii), (iv)",
                    "letter": "(a), (b), (c), (d)",
                    "number": "(1), (2), (3), (4)"
                }
                inst += f"• Sub-part Style: {style_map[section.sub_part_style]}\n"
                if section.sub_parts_per_question:
                    inst += f"• Sub-parts per Question: {section.sub_parts_per_question}\n"
            
            # Add marks
            if section.marks_per_question:
                inst += f"• Marks per Question: {section.marks_per_question}\n"
            
            # Teacher-supplied reading passage (comprehension sections).
            if section.passage:
                p = section.passage
                inst += "\nREADING PASSAGE (teacher-supplied):\n"
                inst += f"Title: {p.title or '(no title)'}\n"
                inst += f"{p.body}\n"
                inst += "\u2022 Base EVERY question in this section on the passage above.\n"
                inst += "\u2022 Every answer MUST be directly findable in the passage text alone.\n"
            if section.allow_sub_parts and section.question_type in ("short_answer", "essay", "theory"):
                inst += "\u2022 Split each question into sub-parts (a), (b)... whose marks "
                inst += "sum exactly to the question's total marks.\n"
            # Type-specific output guidance
            if section.question_type == "theory":
                inst += (
                    "\u2022 Theory questions: omit 'options' and 'correct_answer'. "
                    "Provide a 'marking_scheme' list with key points (strings) the model answer must cover.\n"
                )
            elif section.question_type == "fill_in_blanks":
                inst += (
                    "\u2022 Fill-in-the-blanks questions: omit 'options'. "
                    "Write the question with a blank shown as _______. "
                    "Set 'correct_answer' to the exact word or phrase that fills the blank.\n"
                )
            elif section.question_type in ("essay", "short_answer"):
                inst += (
                    "\u2022 Open-ended questions: omit 'options'. "
                    "Provide a 'marking_scheme' list with key marking points.\n"
                )
            instructions.append(inst)

        
        return "\n".join(instructions)
    
    def _build_custom_instructions(self, custom_instructions: Optional[str]) -> str:
        """Build custom instructions section."""
        if not custom_instructions:
            return ""
        
        return f"""
═══════════════════════════════════════════════════════════════
TEACHER'S CUSTOM INSTRUCTIONS
═══════════════════════════════════════════════════════════════

{custom_instructions}

→ Prioritize these specific requirements in your generation.
"""
    
    def _build_difficulty_instructions(self, difficulty_distribution) -> str:
        """Turn the requested difficulty mix into explicit prompt instructions (CP5)."""
        if not difficulty_distribution:
            return ""

        allowed = ("easy", "medium", "hard")
        parts = []
        for level, share in difficulty_distribution.items():
            level_l = str(level).lower()
            if level_l not in allowed or not isinstance(share, (int, float)):
                continue
            parts.append(f"{int(round(share * 100))}% {level_l}")
        if not parts:
            return ""

        return (
            "\nDIFFICULTY DISTRIBUTION (REQUIRED)\n"
            + "\n".join(f"• {p} of all questions" for p in parts)
            + "\nTag every question's difficulty field accordingly; the exam is "
            "validated against this mix.\n"
        )

    def _build_primary_layout_instructions(self, request: ExamGenerationRequest) -> str:
        """Guidance for primary-school pattern, quantitative reasoning, and visual questions."""
        subj_text = (request.subject or "").lower()
        grade_text = (request.grade_level or "").lower()
        primary_markers = ("primary", "pri", "basic")
        looks_primary = any(marker in grade_text for marker in primary_markers)
        is_reasoning = any(m in subj_text for m in ("reasoning", "quantitative", "verbal", "aptitude"))

        if not looks_primary and not request.include_diagrams and not is_reasoning:
            return ""

        instructions = [
            "PRIMARY & VISUAL REASONING RENDERING RULES:",
            "1. For Quantitative Reasoning questions, follow the Nigerian classroom standard:",
            "   • Always include a 'Sample' pattern rule in the question text or prompt so the student understands the logic.",
            "   • Example: 'Sample: In the sample diagram, (176) branches into [62] and [114] because 62 + 114 = 176. Study the sample and find the missing value (?) in the diagram below.'",
            "2. Whenever a question involves a visual puzzle, generate a clean, self-contained SVG diagram in the 'diagram_svg' field.",
            "   Standard Nigerian Visual Reasoning Archetypes:",
            "   • A1. Horizontal Y-Fork: Circle on left branching right to 2 boxes: (Parent) < [Child 1] & [Child 2].",
            "   • A2. Fraction Branch: Two top fraction boxes with horizontal fraction bars branching down into a bottom result fraction box.",
            "   • B. M-Shape Network: 5 nodes connected along an 'M' path (Top-Left, Bottom-Left, Center, Top-Right, Bottom-Right).",
            "   • C. Power-Circle + Box + Fork: Circle with power (e.g. 6²) connected to a middle box [12], branching into two numbers (6 and 6).",
            "   • D. 4-Way Compass Cross: Center circle hub with Top, Bottom, Left, and Right arms with math operators (+, -, ×, ÷).",
            "   • E. Horseshoe (U-Shape) & Arc (C-Shape): Curved paths connecting peripheral nodes to a result node.",
            "   • F. 2×2 Grid with Result Ear: 4 cells with an attached side circle 'ear' containing the computed difference or sum.",
            "   • G. T-Bar Multiplier: Two top boxes on a horizontal bar with a vertical hanging stem to the product box.",
            "   • H. Triangle Puzzle: Triangle with numbers on 3 vertices and a center value.",
            "3. SVG Specification for 'diagram_svg':",
            "   • Always use viewBox (e.g., viewBox='0 0 220 120' or '0 0 220 150').",
            "   • Use clean crisp strokes: stroke='#222' stroke-width='2.5', fill='#ffffff'.",
            "   • Mark the missing slot with a light yellow fill (fill='#fff9db') containing '?' or an empty box [ ].",
            "   • Center all text with text-anchor='middle', font-size='13' or '14', font-weight='bold', font-family='Arial, sans-serif'.",
            "4. For arithmetic place-value columns (H T U / T U addition and subtraction), format cleanly using markdown preformatted blocks or tables.",
            "5. If a question is purely textual, set 'diagram_svg': null.",
        ]
        return "\n" + "\n".join(instructions) + "\n"

    def _build_language_instructions(self, language):
        """Return prompt guidance for non-English language-of-instruction papers."""
        if not language or language.strip().lower() == "english":
            return ""
        lang = language.strip()
        return (
            "LANGUAGE OF INSTRUCTION: " + lang + "\n"
            "• ALL questions, options, correct answers, explanations and "
            "marking schemes MUST be written in " + lang + ".\n"
            "• Keep British-English exam conventions, but the working language "
            "is " + lang + ".\n"
            "• Do NOT translate questions back to English unless explicitly "
            "required by the subject.\n"
        )

    def _build_json_example(self, sections: List[SectionConfig]) -> str:
        """Build JSON example based on sections."""
        return """{
  "sections": [
    {
      "section_number": 1,
      "section_title": "SECTION A: OBJECTIVES",
      "instruction": "Answer ALL questions",
      "questions": [
        {
          "id": 1,
          "type": "multiple_choice",
          "question": "Study the sample and find the missing value (?) in the diagram below:\\nSample: (176) branches into [62] and [114] because 62 + 114 = 176.",
          "options": ["A. 85", "B. 92", "C. 78", "D. 95"],
          "correct_answer": "B",
          "explanation": "Parent circle equals sum of the two boxes: 130 = ? + 38, so ? = 130 - 38 = 92.",
          "asset_ref": null,
          "diagram_svg": "<svg width='220' height='120' viewBox='0 0 220 120' xmlns='http://www.w3.org/2000/svg'><line x1='72' y1='60' x2='135' y2='35' stroke='#222' stroke-width='2.5'/><line x1='72' y1='60' x2='135' y2='85' stroke='#222' stroke-width='2.5'/><circle cx='48' cy='60' r='26' stroke='#222' stroke-width='2.5' fill='#ffffff'/><text x='48' y='65' text-anchor='middle' font-size='14' font-weight='bold' font-family='Arial, sans-serif' fill='#111'>130</text><rect x='135' y='18' width='56' height='34' rx='4' stroke='#222' stroke-width='2.5' fill='#fff9db'/><text x='163' y='40' text-anchor='middle' font-size='14' font-weight='bold' font-family='Arial, sans-serif' fill='#111'>?</text><rect x='135' y='68' width='56' height='34' rx='4' stroke='#222' stroke-width='2.5' fill='#ffffff'/><text x='163' y='90' text-anchor='middle' font-size='14' font-weight='bold' font-family='Arial, sans-serif' fill='#111'>38</text></svg>",
          "marks": 2,
          "difficulty": "medium",
          "bloom_level": "apply",
          "topic": "Quantitative Reasoning Patterns"
        }
      ]
    }
  ]
}"""
    
    def _calculate_total_marks(self, sections: List[SectionConfig]) -> int:
        """Calculate total marks from sections."""
        total = 0
        for section in sections:
            if section.marks_per_question:
                if section.instruction_type == "answer_all":
                    total += section.num_questions * section.marks_per_question
                elif section.instruction_type in ["answer_any_n", "compulsory_plus_optional"]:
                    total += (section.answer_count or section.num_questions) * section.marks_per_question
        
        return total if total > 0 else 100  # Default to 100 if not specified
    
    def parse_response(
        self,
        response_text: str,
        sections: List[SectionConfig],
    ) -> Dict[str, Any]:
        """
        Parse LLM response into structured exam data.

        Args:
            response_text: Raw LLM response
            sections: Section configuration

        Returns:
            Parsed exam data

        Raises:
            ValueError: If parsing fails
        """
        try:
            # Strip reasoning-model chain-of-thought wrappers (<think>…</think>).
            # Qwen3 and some gpt-oss models emit these before the JSON payload.
            json_text = re.sub(
                r"<think>.*?</think>", "", response_text, flags=re.DOTALL
            ).strip()

            # Robust JSON extraction:
            # 1. Search for markdown code block (```json ... ``` or ``` ... ```)
            fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", json_text)
            if fence_match:
                json_text = fence_match.group(1).strip()
            else:
                # 2. Extract from first '{' to last '}' to ignore any conversational intro/outro text
                first_brace = json_text.find("{")
                last_brace = json_text.rfind("}")
                if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                    json_text = json_text[first_brace : last_brace + 1].strip()

            # Parse JSON with strict=False to allow unescaped newlines/control characters in strings
            try:
                data = json.loads(json_text, strict=False)
            except json.JSONDecodeError:
                # Second chance: repair common LLM JSON defects (invalid
                # backslash escapes such as LaTeX \ce{...}, trailing commas)
                # before giving up on an otherwise complete response.
                repaired = _repair_json_text(json_text)
                if repaired == json_text:
                    raise
                logger.warning("Attempting repair of malformed LLM JSON before salvage")
                data = json.loads(repaired, strict=False)

            # Validate structure
            if "sections" not in data:
                raise ValueError("Response missing 'sections' key")

            # Validate section count
            if len(data["sections"]) != len(sections):
                logger.warning(f"Expected {len(sections)} sections, got {len(data['sections'])}")

            # Validate total questions
            total_questions = sum(len(s["questions"]) for s in data["sections"])
            expected_questions = sum(s.num_questions for s in sections)

            if total_questions != expected_questions:
                logger.warning(f"Expected {expected_questions} questions, got {total_questions}")

            _attach_authoritative_passages(data, sections)
            _normalize_exam_bloom_levels(data)

            self._validate_markdown_blocks(data)

            logger.info(f"✅ Parsed exam: {len(data['sections'])} sections, {total_questions} questions")

            return data

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            logger.error(f"Response text (first 500 chars): {response_text[:500]}...")

            # --- Truncation salvage: try to recover complete sections ---
            salvaged = self._salvage_truncated_json(response_text, sections)
            if salvaged:
                logger.warning(
                    "⚠️ Truncated LLM response salvaged: %s/%s sections recovered",
                    len(salvaged.get("sections", [])),
                    len(sections),
                )
                return salvaged

            raise ValueError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"Response parsing failed: {str(e)}")
            raise ValueError(f"Failed to parse response: {str(e)}")

    def _salvage_truncated_json(
        self,
        raw: str,
        sections: List[SectionConfig],
    ) -> Optional[Dict[str, Any]]:
        """
        Best-effort recovery when the LLM JSON is cut off mid-stream.

        Strategy:
        1. Strip markdown fences.
        2. Find the last *complete* question object (ends with ``}``) using a
           regex scan — everything after that is discarded.
        3. Close open arrays/objects until we have valid JSON.
        4. Only return the salvaged data if at least one complete section is
           present; otherwise return None so the caller can raise.
        """
        try:
            text = raw.strip()
            # Strip markdown fences if present
            fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)(?:```|$)", text)
            if fence_match:
                text = fence_match.group(1).strip()
            else:
                first_brace = text.find("{")
                if first_brace != -1:
                    text = text[first_brace:].strip()

            # Find the position of the last closing brace of a complete question
            # by scanning for `}` preceded by a complete "topic" or "marks" field
            # (simple heuristic — works even on deeply nested structures).
            last_good = -1
            depth = 0
            in_str = False
            escape_next = False
            for i, ch in enumerate(text):
                if escape_next:
                    escape_next = False
                    continue
                if ch == "\\" and in_str:
                    escape_next = True
                    continue
                if ch == '"' and not escape_next:
                    in_str = not in_str
                if in_str:
                    continue
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth >= 2:  # still inside sections/questions arrays
                        last_good = i

            if last_good == -1:
                return None

            # Truncate to last good position and close open structures
            truncated = text[: last_good + 1]
            # Count unclosed brackets/braces
            opens_sq = truncated.count("[") - truncated.count("]")
            opens_br = truncated.count("{") - truncated.count("}")
            # Strip trailing commas before closing
            truncated = re.sub(r",\s*$", "", truncated.rstrip())
            # Close arrays and objects in reverse nesting order
            truncated += "]" * max(opens_sq, 0)
            truncated += "}" * max(opens_br, 0)

            data = json.loads(_repair_json_text(truncated), strict=False)
            if "sections" not in data or not data["sections"]:
                return None

            # Remove any section that has zero questions (incompletely written)
            data["sections"] = [
                s for s in data["sections"] if s.get("questions")
            ]
            if not data["sections"]:
                return None

            # A partial salvage is not a valid examination. Returning it would
            # let downstream validation/store code produce an incomplete paper
            # with missing sections or questions. Force the caller to retry
            # the provider response instead.
            expected_questions = sum(s.num_questions for s in sections)
            recovered_questions = sum(
                len(section.get("questions") or []) for section in data["sections"]
            )
            if len(data["sections"]) != len(sections) or recovered_questions != expected_questions:
                logger.warning(
                    "Discarding incomplete JSON salvage: sections=%s/%s questions=%s/%s",
                    len(data["sections"]),
                    len(sections),
                    recovered_questions,
                    expected_questions,
                )
                return None

            _attach_authoritative_passages(data, sections)
            _normalize_exam_bloom_levels(data)
            return data

        except Exception as salvage_err:
            logger.debug("Salvage attempt failed: %s", salvage_err)
            return None


    def _validate_markdown_blocks(self, parsed_exam: Dict[str, Any]) -> None:
        """Ensure fenced markdown blocks are balanced for renderer safety."""
        sections = parsed_exam.get("sections", [])
        for section in sections:
            for question in section.get("questions", []):
                question_text = str(question.get("question") or "")
                if question_text.count("```") % 2 != 0:
                    raise ValueError("Question contains unbalanced markdown fenced code blocks.")

    async def store_exam(
        self,
        parsed_exam: Dict[str, Any],
        request: ExamGenerationRequest,
        school_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        llm_response: Dict[str, Any],
        db: AsyncSession,
        exam_id: Optional[uuid.UUID] = None,
    ) -> Exam:
        """
        Store generated exam in database.

        Args:
            parsed_exam: Parsed exam data
            request: Original request
            school_id: School ID
            created_by_user_id: User ID
            llm_response: LLM response metadata
            db: Database session
            exam_id: Optional existing exam ID to update

        Returns:
            Stored exam
        """
        try:
            # Calculate total marks
            total_marks = sum(
                sum(q.get("marks", 0) for q in section["questions"])
                for section in parsed_exam["sections"]
            )
            
            # Create or update exam
            if exam_id:
                # Update existing exam
                result = await db.execute(select(Exam).where(Exam.id == exam_id))
                exam = result.scalar_one_or_none()
                
                if exam:
                    exam.total_marks = total_marks
                    exam.status = "under_review"
                    exam.workflow_state = "teacher_review"
                    exam.updated_at = utc_now()
                    exam.language = request.language

                    # If this is a re-generation, clear old questions
                    await db.execute(delete(Question).where(Question.exam_id == exam_id))
                    await db.execute(delete(ExamPassage).where(ExamPassage.exam_id == exam_id))
                else:
                    logger.warning(f"Exam {exam_id} not found for update, creating new.")
                    exam = Exam(
                        id=exam_id,
                        school_id=school_id,
                        created_by_user_id=created_by_user_id,
                        subject=request.subject,
                        grade_level=request.grade_level,
                        status="under_review",
                        workflow_state="teacher_review",
                        total_marks=total_marks,
                        duration_minutes=request.duration_minutes,
                        instructions=self._build_exam_instructions(request.sections),
                        language=request.language,
                        created_at=utc_now(),
                        updated_at=utc_now(),
                    )
                    db.add(exam)
            else:
                # Create new exam
                exam = Exam(
                    id=uuid.uuid4(),
                    school_id=school_id,
                    created_by_user_id=created_by_user_id,
                    subject=request.subject,
                    grade_level=request.grade_level,
                    status="under_review",
                    workflow_state="teacher_review",
                    total_marks=total_marks,
                    duration_minutes=request.duration_minutes,
                    instructions=self._build_exam_instructions(request.sections),
                        language=request.language,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                db.add(exam)
            
            
            await db.flush()
            # Persist teacher-supplied passages (authoritative) and map each
            # section number to its passage id so questions can link below.
            passage_ids_by_section = {}
            for section in parsed_exam["sections"]:
                passage = section.get("passage")
                if not passage or not (passage.get("body") or "").strip():
                    continue
                exam_passage = ExamPassage(
                    id=uuid.uuid4(),
                    exam_id=exam.id,
                    title=((passage.get("title") or "")[:500] or None),
                    body=passage.get("body", ""),
                    section_number=int(section.get("section_number", 1)),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                db.add(exam_passage)
                passage_ids_by_section[int(section.get("section_number", 1))] = exam_passage.id

            
            # Create questions (batch)
            question_number = 1
            for section in parsed_exam["sections"]:
                sec_num = int(section.get("section_number", 1))
                sec_name = section.get("section_title") or f"Section {chr(64 + sec_num)}"
                for q_data in section["questions"]:
                    question = Question(
                        id=uuid.uuid4(),
                        exam_id=exam.id,
                        question_number=question_number,
                        section_number=sec_num,
                        section_name=sec_name,
                        type=q_data.get("type", "multiple_choice"),
                        question_text=q_data.get("question", ""),
                        marks=q_data.get("marks", 0),
                        difficulty=q_data.get("difficulty"),
                        bloom_level=q_data.get("bloom_level"),
                        topic=q_data.get("topic"),
                        options=q_data.get("options"),
                        correct_answer=q_data.get("correct_answer"),
                        explanation=q_data.get("explanation"),
                        marking_scheme=q_data.get("marking_scheme"),
                        sub_parts=q_data.get("sub_parts"),
                        diagram_svg=q_data.get("diagram_svg"),
                        passage_id=passage_ids_by_section.get(section.get("section_number")),
                        created_at=utc_now(),
                        updated_at=utc_now(),
                    )
                    db.add(question)
                    question_number += 1

            await db.commit()
            await db.refresh(exam)
            
            logger.info(f"✅ Stored exam {exam.id} with {question_number-1} questions")
            
            return exam
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to store exam: {str(e)}")
            raise ValueError(f"Failed to store exam: {str(e)}")
    
    def _build_exam_instructions(self, sections: List[SectionConfig]) -> str:
        """Build exam instructions from sections."""
        instructions = []
        
        for section in sections:
            if section.passage:
                instructions.append(f"{section.section_title}: Read the passage, then answer the questions that follow.")
            if section.instruction_type == "answer_all":
                instructions.append(f"{section.section_title}: Answer ALL questions")
            elif section.instruction_type == "answer_any_n":
                instructions.append(f"{section.section_title}: Answer ANY {section.answer_count} questions")
            elif section.instruction_type == "compulsory_plus_optional":
                compulsory = ", ".join(map(str, section.compulsory_questions))
                optional_count = section.answer_count - len(section.compulsory_questions)
                instructions.append(
                    f"{section.section_title}: Answer Question(s) {compulsory} (compulsory) "
                    f"and any other {optional_count} question(s)"
                )
        
        return "\n".join(instructions)

    async def refine_exam(
        self,
        exam_id: uuid.UUID,
        school_id: uuid.UUID,
        feedback: str,
        refined_by_user_id: uuid.UUID,
        db: AsyncSession,
        question_ids: Optional[List[uuid.UUID]] = None,
    ) -> Dict[str, Any]:
        """
        Refine specific questions (or all exam questions) based on teacher feedback.
        """
        exam_result = await db.execute(
            select(Exam).where(and_(Exam.id == exam_id, Exam.school_id == school_id))
        )
        exam = exam_result.scalar_one_or_none()
        if not exam:
            raise ValueError("Exam not found")

        question_query = select(Question).where(Question.exam_id == exam_id)
        if question_ids:
            question_query = question_query.where(Question.id.in_(question_ids))
        question_query = question_query.order_by(Question.question_number)

        question_result = await db.execute(question_query)
        questions = question_result.scalars().all()
        if not questions:
            raise ValueError("No questions found for refinement")

        question_payload = [
            {
                "id": str(q.id),
                "question_number": q.question_number,
                "type": q.type,
                "question_text": q.question_text,
                "marks": q.marks,
            }
            for q in questions
        ]

        # Release the read transaction before the LLM await (session
        # discipline: no idle-in-transaction during provider calls).
        await db.commit()

        prompt = f"""You are refining exam questions for {exam.subject} ({exam.grade_level}).

Teacher feedback:
{feedback}

Questions to refine (JSON):
{json.dumps(question_payload, ensure_ascii=False)}

Return ONLY valid JSON with this exact shape:
{{
  "refinements": [
    {{"id": "question-uuid", "refined_text": "updated question text"}}
  ]
}}
"""

        llm_response = await self.llm_service.generate(
            prompt=prompt,
            temperature=0.3,
            max_tokens=2500,
        )

        raw = llm_response["content"].strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1]) if len(lines) > 2 else raw

        try:
            data = json.loads(raw)
        except Exception as e:
            raise ValueError(f"Refinement response was not valid JSON: {str(e)}")

        refinements = data.get("refinements", [])
        if not isinstance(refinements, list):
            raise ValueError("Refinement response missing refinements list")

        refinement_by_id: Dict[str, str] = {}
        for item in refinements:
            qid = item.get("id")
            refined_text = item.get("refined_text")
            if qid and refined_text:
                refinement_by_id[qid] = refined_text.strip()

        if not refinement_by_id:
            raise ValueError("No valid refinements were returned")

        updated_ids: List[str] = []
        for question in questions:
            new_text = refinement_by_id.get(str(question.id))
            if not new_text:
                continue

            history = QuestionRefinement(
                question_id=question.id,
                refined_by_user_id=refined_by_user_id,
                feedback=feedback,
                original_text=question.question_text,
                refined_text=new_text,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(history)

            question.question_text = new_text
            question.updated_at = utc_now()
            updated_ids.append(str(question.id))

        if not updated_ids:
            raise ValueError("No matching question refinements were applied")

        exam.status = "under_review"
        exam.updated_at = utc_now()
        await db.commit()

        return {
            "message": "Exam questions refined successfully",
            "exam_id": str(exam_id),
            "updated_questions": len(updated_ids),
            "updated_question_ids": updated_ids,
            "provider": llm_response.get("provider"),
            "tokens_used": llm_response.get("tokens_used"),
        }
