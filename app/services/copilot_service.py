"""Teacher-in-the-loop AI helpers for the manual composer."""
from __future__ import annotations
import json
from app.core.llm import get_llm_service
from app.schemas.copilot import CopilotRequest, CopilotResponse

class CopilotService:
    @staticmethod
    async def assist(request: CopilotRequest) -> CopilotResponse:
        task = {
            "options": "Generate four plausible multiple-choice options and identify the correct option.",
            "marking_guide": "Draft a concise line-by-line marking guide totaling the supplied marks.",
            "rewrite": "Rewrite the question for clarity and age-appropriate Nigerian classroom English without changing its meaning.",
            "diagram_prompt": "Suggest a precise diagram specification, labels, and hidden exam parts if a diagram would improve this question.",
        }[request.action]
        prompt = f'''You are a Nigerian examination editor. Return JSON only.
Subject: {request.subject}
Class: {request.grade_level}
Topic: {request.topic or 'not specified'}
Question: {request.question}
Marks: {request.marks}
Existing options: {json.dumps(request.options or [])}
Task: {task}
JSON shape: {{"content":"...","options":[],"marking_points":[],"diagram_prompt":null}}'''
        result = await get_llm_service().generate(prompt=prompt, temperature=0.25, max_tokens=1400)
        raw = str(result.get("content") or "").strip()
        try:
            start, end = raw.find("{"), raw.rfind("}")
            data = json.loads(raw[start:end + 1]) if start >= 0 and end > start else {"content": raw}
        except json.JSONDecodeError:
            data = {"content": raw}
        return CopilotResponse(
            action=request.action,
            content=str(data.get("content") or "").strip(),
            options=[str(x) for x in (data.get("options") or [])][:10],
            marking_points=[str(x) for x in (data.get("marking_points") or [])][:20],
            diagram_prompt=str(data.get("diagram_prompt")) if data.get("diagram_prompt") else None,
        )
