from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.core.dependencies import get_current_user
from app.schemas.auth import CurrentUser
from app.schemas.api_key import ApiKeyCreateRequest, ApiKeyCreatedResponse, ApiKeyResponse
from app.services.api_key_service import ApiKeyService
from app.models.api_key import ApiKey
from sqlalchemy import select, update
from datetime import datetime, timezone

router = APIRouter()

def _admin(user: CurrentUser):
    if user.role not in {"admin", "school_admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="Only school administrators can manage API keys")

@router.post("/keys", response_model=ApiKeyCreatedResponse)
async def create_key(request: ApiKeyCreateRequest, user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    _admin(user)
    try:
        record, secret = await ApiKeyService.create(db, user.school_id, request.name, request.scopes, request.quota_monthly, request.expires_at)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    data = ApiKeyResponse.model_validate(record).model_dump()
    data["key"] = secret
    return data

@router.get("/keys", response_model=list[ApiKeyResponse])
async def list_keys(user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    _admin(user)
    result = await db.execute(select(ApiKey).where(ApiKey.school_id == user.school_id).order_by(ApiKey.created_at.desc()))
    return list(result.scalars())

@router.post("/keys/{key_id}/revoke", response_model=ApiKeyResponse)
async def revoke_key(key_id: str, user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    _admin(user)
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id, ApiKey.school_id == user.school_id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(key)
    return key
