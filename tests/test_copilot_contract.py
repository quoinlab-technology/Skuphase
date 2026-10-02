from app.schemas.copilot import CopilotRequest

def test_copilot_request_is_bounded():
    request = CopilotRequest(action="marking_guide", subject="Physics", grade_level="SSS 1", question="Calculate force", marks=4)
    assert request.action == "marking_guide"
    assert request.marks == 4
