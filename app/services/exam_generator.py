"""Exam generation service using RAG + LLM."""

import json
import logging
import re
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from app.models.exam import Exam, Question, ExamContext
from app.models.asset import LearningAsset, QuestionAssetRef
from app.models.document import SchoolDocument
from app.models.question import QuestionRefinement
from app.schemas.exam import ExamGenerationRequest, SectionConfig
from app.services.rag_service import RAGService
from app.services.embedding_service import EmbeddingService
from app.services.exam_quality_validator import ExamQualityValidator
from app.services.curriculum_service import CurriculumService
from app.services.few_shot_selector import FewShotSelector
from app.core.llm import get_llm_service

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class ExamGenerator:
    """Service for generating exams using RAG + LLM."""

    def __init__(self):
        """Initialize exam generator.

        Embeddings are OPTIONAL: when neither local models nor an API key
        are available we degrade gracefully (RAGService falls back to text
        search, and few-shot selection is SQL-only anyway).
        """
        try:
            self.embedding_service = EmbeddingService(use_local=True)
        except Exception as e:
            logger.warning(
                "Embedding service unavailable - RAG text fallback mode: %s", str(e)
            )
            self.embedding_service = None
        self.rag_service = RAGService(embedding_service=self.embedding_service)
        self.quality_validator = ExamQualityValidator()
        self.few_shot_selector = FewShotSelector()
        self.llm_service = get_llm_service()
    
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
        try:
            logger.info("🚀 Starting exam generation for %s - %s", request.subject, request.grade_level)

            # 1. Retrieve Curriculum / RAG context
            rag_context = await self.retrieve_context(
                school_id=school_id,
                document_ids=request.document_ids or [],
                subject=request.subject,
                grade_level=request.grade_level,
                term=request.term,
                selected_weeks=request.selected_weeks,
                db=db,
            )
            asset_context = await self.retrieve_asset_context(
                school_id=school_id,
                asset_ids=request.asset_ids or [],
                db=db,
            )

            # 2. Build dynamic prompt
            prompt = self.build_prompt(request, rag_context, asset_context)

            # 3. Single LLM call
            logger.info("📞 Calling LLM for exam generation...")
            llm_response = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=6000,
            )

            logger.info(
                "✅ LLM call successful: %s tokens, $%.6f",
                llm_response.get("tokens_used"),
                llm_response.get("cost", 0),
            )

            # 4. Parse response (section-aware)
            parsed_exam = self.parse_response(
                llm_response["content"],
                request.sections,
                asset_context=asset_context,
            )
            validation = self.quality_validator.validate_or_raise(
                parsed_exam=parsed_exam,
                request=request,
                rag_context=rag_context,
            )
            for warning in validation.warnings:
                logger.warning("Generation quality warning: %s", warning)
            logger.info("Generation quality metrics: %s", validation.metrics)

            # 5. Store exam
            exam = await self.store_exam(
                parsed_exam=parsed_exam,
                request=request,
                school_id=school_id,
                created_by_user_id=created_by_user_id,
                rag_context=rag_context,
                asset_context=asset_context,
                llm_response=llm_response,
                db=db,
                exam_id=exam_id,
            )

            logger.info("✅ Exam generated successfully: %s", exam.id)
            return exam

        except Exception as e:
            logger.error("❌ Exam generation failed: %s", str(e))
            raise ValueError(f"Exam generation failed: {str(e)}")

    async def retrieve_context(
        self,
        school_id: uuid.UUID,
        document_ids: Optional[List[uuid.UUID]],
        subject: str,
        grade_level: str,
        term: Optional[str],
        selected_weeks: Optional[List[int]],
        db: AsyncSession,
        top_k: int = 15,
    ) -> Dict[str, Any]:
        """
        Retrieve curriculum context from official Scheme of Work and optional school documents.
        """
        context_blocks: List[str] = []
        chunks: List[Dict[str, Any]] = []

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
                    lines = [f"OFFICIAL NERDC SCHEME OF WORK ({grade_level} {subject} - {term}):"]
                    for item in scheme_data:
                        lines.append(f"\n[Week {item['week_number']}: {item['topic']}]")
                        for obj in item.get("subtopics", []):
                            lines.append(f"  • {obj}")
                    context_blocks.append("\n".join(lines))
                    logger.info("Injected %s scheme-of-work weeks into prompt context", len(scheme_data))
            except Exception as e:
                logger.warning("Could not fetch scheme of work for %s %s: %s", grade_level, subject, str(e))

        # 2. Few-shot past-question examples from the shared question bank
        #    (SQL-first lookup; embeddings not required).
        try:
            examples = await self.few_shot_selector.select(
                db=db,
                subject=subject,
                grade_level=grade_level,
                week_indices=selected_weeks,
                term=term,
            )
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
                context_blocks.append("\n".join(ex_lines))
                logger.info("Injected %s few-shot past-question examples", len(examples))
        except Exception as e:
            logger.warning("Few-shot selection skipped: %s", str(e))

        # 3. Retrieve optional document chunks if document_ids provided
        if document_ids:
            try:
                query = f"Curriculum content for {subject}"
                chunks = await self.rag_service.search(
                    school_id=school_id,
                    query=query,
                    db=db,
                    document_ids=document_ids,
                    top_k=top_k,
                    use_vector=True,
                )
                if chunks:
                    doc_context = "\n\n".join([
                        f"[Document Chunk {i+1}] {chunk['content'][:500]}..."
                        for i, chunk in enumerate(chunks[:10])
                    ])
                    context_blocks.append(f"ADDITIONAL SCHOOL LESSON NOTES / MATERIALS:\n{doc_context}")
            except Exception as e:
                logger.warning("Optional RAG document retrieval notice: %s", str(e))

        if not context_blocks:
            context_blocks.append(f"Standard National Curriculum for Nigerian Schools: {subject} ({grade_level}).")

        combined_context = "\n\n═══════════════════════════════════════════════════════════════\n\n".join(context_blocks)

        return {
            "chunks": chunks,
            "combined_context": combined_context,
            "document_ids": document_ids or [],
        }

    async def retrieve_asset_context(
        self,
        school_id: uuid.UUID,
        asset_ids: List[uuid.UUID],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Retrieve approved asset metadata for prompt-side references."""
        if not asset_ids:
            return {"assets": [], "asset_map": {}}

        result = await db.execute(
            select(LearningAsset).where(
                and_(
                    LearningAsset.school_id == school_id,
                    LearningAsset.id.in_(asset_ids),
                    LearningAsset.is_active.is_(True),
                    LearningAsset.is_ai_usable.is_(True),
                    LearningAsset.processing_status == "approved",
                )
            )
        )
        assets = list(result.scalars().all())
        asset_map = {asset.reference_code: asset.id for asset in assets}
        return {
            "assets": [
                {
                    "id": str(asset.id),
                    "reference_code": asset.reference_code,
                    "asset_type": asset.asset_type,
                    "title": asset.title,
                    "description": asset.description,
                    "subject": asset.subject,
                    "grade_level": asset.grade_level,
                    "topic": asset.topic,
                }
                for asset in assets
            ],
            "asset_map": asset_map,
        }
    
    def build_prompt(
        self,
        request: ExamGenerationRequest,
        rag_context: Dict[str, Any],
        asset_context: Dict[str, Any],
    ) -> str:
        """
        Build exam generation prompt dynamically based on configuration.
        
        Args:
            request: Exam generation request
            rag_context: RAG context from documents
            
        Returns:
            Complete prompt for LLM
        """
        # Calculate totals
        total_questions = sum(s.num_questions for s in request.sections)
        total_marks = self._calculate_total_marks(request.sections)
        
        # Build section instructions
        section_instructions = self._build_section_instructions(request.sections)
        
        asset_block = self._build_asset_instructions(asset_context.get("assets", []))
        primary_layout_block = self._build_primary_layout_instructions(request)

        # Build base prompt
        prompt = f"""You are an expert Nigerian school examiner creating high-quality exam questions for {request.subject} at {request.grade_level} level.

═══════════════════════════════════════════════════════════════
SECTION 1: CURRICULUM CONTEXT
═══════════════════════════════════════════════════════════════

{rag_context['combined_context']}

→ All questions MUST align with this curriculum content.
→ Use terminology and examples from the provided context.

═══════════════════════════════════════════════════════════════
SECTION 2: NIGERIAN EDUCATION CONTEXT
═══════════════════════════════════════════════════════════════

Language & Style:
• British English spelling (colour, honour, organise, practise, realise)
• Formal but clear language appropriate for {request.grade_level}
• Command words: State, Outline, Explain, Discuss, Calculate, Describe

Cultural Context:
• Use Nigerian names: Chidi, Amina, Tunde, Ngozi, Emeka, Fatima
• Local examples: cassava farming, Lagos market, harmattan season, NEPA
• Locations: Lagos, Kano, Abuja, Ibadan, Port Harcourt
• Units: Metric system (km, kg, litres) + Naira (₦) for money

═══════════════════════════════════════════════════════════════
SECTION 3: EXAM STRUCTURE
═══════════════════════════════════════════════════════════════

Total Questions: {total_questions}
Total Marks: {total_marks}
Duration: {request.duration_minutes} minutes

{section_instructions}

{self._build_custom_instructions(request.custom_instructions)}

{asset_block}

{primary_layout_block}

═══════════════════════════════════════════════════════════════
SECTION 4: INTERNAL PLANNING
═══════════════════════════════════════════════════════════════

<internal_planning>
Before generating, analyze:
1. Main topics from curriculum context (prioritize by emphasis)
2. Appropriate question distribution for {request.grade_level}
3. Difficulty calibration (what's "easy" vs "hard" at this level)
4. Nigerian context examples that fit naturally
5. Section-specific requirements (MCQ vs theory, sub-parts, etc.)

DO NOT OUTPUT THIS SECTION.
</internal_planning>

═══════════════════════════════════════════════════════════════
SECTION 5: QUALITY STANDARDS
═══════════════════════════════════════════════════════════════

<self_check>
After generating each question, verify:
✓ Clarity: No ambiguous wording
✓ Accuracy: Factually correct based on curriculum
✓ Relevance: Directly tied to curriculum content
✓ Age-appropriate: Language matches {request.grade_level}
✓ Nigerian context: Uses local examples and British English

DO NOT OUTPUT THIS SECTION.
</self_check>

═══════════════════════════════════════════════════════════════
SECTION 6: OUTPUT FORMAT (STRICT JSON)
═══════════════════════════════════════════════════════════════

Return ONLY valid JSON in this exact format (no markdown, no preamble):

{self._build_json_example(request.sections)}

<final_output>
Generate the complete exam now. Ensure:
• All {total_questions} questions are included
• Total marks sum to exactly {total_marks}
• Questions are original, educationally sound, and Nigerian-appropriate
• Every question tests content from the curriculum
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
    
    def _build_asset_instructions(self, assets: List[Dict[str, Any]]) -> str:
        """Build prompt section for approved asset references."""
        if not assets:
            return ""

        lines = [
            "",
            "ASSET REFERENCE CONTEXT",
            "Use only the listed asset_ref values when a question depends on a figure/diagram/table/formula image.",
            "Do not invent new asset references.",
        ]
        for asset in assets:
            lines.append(
                f"- asset_ref={asset['reference_code']} | type={asset['asset_type']} | "
                f"title={asset.get('title') or '-'} | desc={asset.get('description') or '-'}"
            )
        return "\n".join(lines)

    def _build_primary_layout_instructions(self, request: ExamGenerationRequest) -> str:
        """Guidance for primary-school pattern and visual questions."""
        grade_text = (request.grade_level or "").lower()
        primary_markers = ("primary", "pri", "basic")
        looks_primary = any(marker in grade_text for marker in primary_markers)

        if not looks_primary and not request.include_diagrams:
            return ""

        return """
PRIMARY EXAM RENDERING RULES
1. Write question text in clean markdown for direct frontend rendering.
2. For pattern/shape/quantitative puzzles, use markdown tables and short bullet structures.
3. For diagram logic, Mermaid is allowed inside fenced blocks.
4. Keep each visual block compact and classroom-friendly.
5. Do not invent image links; use provided asset_ref when visuals are required.
"""

    def _build_json_example(self, sections: List[SectionConfig]) -> str:
        """Build JSON example based on sections."""
        # This is a simplified example - real implementation would be more detailed
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
          "question": "Which organelle is responsible for photosynthesis?",
          "options": ["A. Mitochondria", "B. Chloroplast", "C. Nucleus", "D. Ribosome"],
          "correct_answer": "B",
          "explanation": "Chloroplasts contain chlorophyll...",
          "asset_ref": null,
          "marks": 2,
          "difficulty": "easy",
          "bloom_level": "remember",
          "topic": "Cell Biology"
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
        asset_context: Optional[Dict[str, Any]] = None,
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
            # Extract JSON from response (handle markdown code blocks)
            json_text = response_text.strip()
            if json_text.startswith("```"):
                # Remove markdown code blocks
                lines = json_text.split("\n")
                json_text = "\n".join(lines[1:-1]) if len(lines) > 2 else json_text
            
            # Parse JSON
            data = json.loads(json_text)
            
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

            self._validate_markdown_blocks(data)

            # Validate asset reference contract (strict)
            self._validate_asset_reference_contract(
                parsed_exam=data,
                asset_context=asset_context or {"asset_map": {}},
            )
            
            logger.info(f"✅ Parsed exam: {len(data['sections'])} sections, {total_questions} questions")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            logger.error(f"Response text: {response_text[:500]}...")
            raise ValueError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"Response parsing failed: {str(e)}")
            raise ValueError(f"Failed to parse response: {str(e)}")

    def _validate_markdown_blocks(self, parsed_exam: Dict[str, Any]) -> None:
        """Ensure fenced markdown blocks are balanced for renderer safety."""
        sections = parsed_exam.get("sections", [])
        for section in sections:
            for question in section.get("questions", []):
                question_text = str(question.get("question") or "")
                if question_text.count("```") % 2 != 0:
                    raise ValueError("Question contains unbalanced markdown fenced code blocks.")

    def _validate_asset_reference_contract(
        self,
        parsed_exam: Dict[str, Any],
        asset_context: Dict[str, Any],
    ) -> None:
        """Ensure `asset_ref` usage is explicit and restricted to approved refs."""
        asset_map = asset_context.get("asset_map", {})
        allowed_refs = set(asset_map.keys())
        sections = parsed_exam.get("sections", [])
        marker_pattern = re.compile(r"asset_ref\s*[:=]\s*([A-Za-z0-9_\-]+)", re.IGNORECASE)

        for section in sections:
            for question in section.get("questions", []):
                question_text = str(question.get("question") or "")
                marker_refs = marker_pattern.findall(question_text)
                asset_ref = question.get("asset_ref")

                if asset_ref is None:
                    if marker_refs:
                        raise ValueError(
                            "Question contains inline asset_ref marker but asset_ref field is missing/null."
                        )
                    continue

                if not isinstance(asset_ref, str) or not asset_ref.strip():
                    raise ValueError("asset_ref must be a non-empty string when provided.")
                normalized_ref = asset_ref.strip()
                question["asset_ref"] = normalized_ref

                if not allowed_refs:
                    raise ValueError(
                        f"asset_ref '{normalized_ref}' was provided but no approved assets were selected."
                    )
                if normalized_ref not in allowed_refs:
                    raise ValueError(
                        f"asset_ref '{normalized_ref}' is not among selected approved asset references."
                    )
    
    async def store_exam(
        self,
        parsed_exam: Dict[str, Any],
        request: ExamGenerationRequest,
        school_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        rag_context: Dict[str, Any],
        asset_context: Dict[str, Any],
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
            rag_context: RAG context used
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
                    
                    # If this is a re-generation, clear old questions
                    await db.execute(delete(Question).where(Question.exam_id == exam_id))
                    await db.execute(delete(ExamContext).where(ExamContext.exam_id == exam_id))
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
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                db.add(exam)
            
            
            await db.flush()
            
            # Create questions (batch)
            question_number = 1
            asset_map = asset_context.get("asset_map", {})
            for section in parsed_exam["sections"]:
                for q_data in section["questions"]:
                    question = Question(
                        id=uuid.uuid4(),
                        exam_id=exam.id,
                        question_number=question_number,
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
                        created_at=utc_now(),
                        updated_at=utc_now(),
                    )
                    db.add(question)
                    asset_ref = q_data.get("asset_ref")
                    if asset_ref and asset_ref in asset_map:
                        db.add(
                            QuestionAssetRef(
                                question_id=question.id,
                                asset_id=asset_map[asset_ref],
                                usage_type="required",
                                is_mandatory=True,
                            )
                        )
                    question_number += 1
            
            # Create exam context (source citations)
            for doc_id in rag_context["document_ids"]:
                context = ExamContext(
                    id=uuid.uuid4(),
                    exam_id=exam.id,
                    document_id=doc_id,
                    relevance_score=1.0,  # Could calculate from RAG scores
                    extracted_context=rag_context["combined_context"][:1000],
                    context_type="curriculum_reference",
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                db.add(context)
            
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
