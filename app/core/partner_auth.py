from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.services.api_key_service import ApiKeyService


async def get_partner_key(
    x_api_key: str | None = Header(None),
    db: AsyncSession = Depends(get_db_session),
):
    key = await ApiKeyService.verify(db, x_api_key or "")
    if not key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired partner API key")
    return key


def require_partner_scope(scope: str):
    async def dependency(key=Depends(get_partner_key)):
        if scope not in (key.scopes or []):
            raise HTTPException(status_code=403, detail=f"API key lacks scope: {scope}")
        return key
    return dependency
