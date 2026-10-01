from fastapi import APIRouter, Query
from app.schemas.assessment_studio import BlueprintRequest, BlueprintResponse
from app.services.blueprint_service import build_blueprint
from app.services.constants_catalog import list_constants

router = APIRouter()

@router.get("/constants")
async def constants(subject: str | None = Query(None), q: str | None = Query(None)):
    return list_constants(subject=subject, query=q)

@router.post("/blueprints", response_model=BlueprintResponse)
async def blueprint(request: BlueprintRequest):
    return build_blueprint(request)
