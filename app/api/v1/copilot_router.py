from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.schemas.auth import CurrentUser
from app.schemas.copilot import CopilotRequest, CopilotResponse
from app.services.copilot_service import CopilotService

router = APIRouter()

@router.post("/assist", response_model=CopilotResponse)
async def assist(request: CopilotRequest, current_user: CurrentUser = Depends(get_current_user)):
    return await CopilotService.assist(request)
