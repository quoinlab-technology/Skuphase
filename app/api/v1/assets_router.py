"""Learning asset management endpoints."""

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_current_user
from app.models.asset import LearningAsset
from app.schemas.asset import (
    LearningAssetBatchReviewRequest,
    LearningAssetListResponse,
    LearningAssetResponse,
    LearningAssetReviewRequest,
    LearningAssetUpdateRequest,
)
from app.schemas.auth import CurrentUser


router = APIRouter()

UPLOAD_DIR = Path("uploads/assets")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_ASSET_TYPES = {"image", "diagram", "formula", "table"}
ALLOWED_ASSET_SOURCES = {"lesson_note", "exam_requirement", "question_bank", "manual"}


def _require_teacher_or_admin(current_user: CurrentUser) -> None:
    if current_user.role not in {"teacher", "school_admin"}:
        raise HTTPException(
            status_code=403,
            detail="Only teachers or school administrators can manage assets",
        )


def _require_admin(current_user: CurrentUser) -> None:
    if current_user.role != "school_admin":
        raise HTTPException(
            status_code=403,
            detail="Only school administrators can review assets",
        )


@router.post(
    "/upload",
    response_model=LearningAssetResponse,
    status_code=201,
    summary="Upload learning asset",
    tags=["Assets"],
)
async def upload_asset(
    file: UploadFile = File(...),
    asset_type: str = Form(...),
    asset_source: str = Form("manual"),
    reference_code: str = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    grade_level: Optional[str] = Form(None),
    topic: Optional[str] = Form(None),
    source_document_id: Optional[uuid.UUID] = Form(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> LearningAssetResponse:
    """Upload a visual/formula asset used by lesson notes and exam questions."""
    _require_teacher_or_admin(current_user)

    if asset_type not in ALLOWED_ASSET_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid asset_type: {asset_type}")
    if asset_source not in ALLOWED_ASSET_SOURCES:
        raise HTTPException(status_code=400, detail=f"Invalid asset_source: {asset_source}")
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a name")

    existing = await db.execute(
        select(LearningAsset).where(
            and_(
                LearningAsset.school_id == current_user.school_id,
                LearningAsset.reference_code == reference_code,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="reference_code already exists for this school",
        )

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Asset file exceeds 20MB limit")

    asset_id = uuid.uuid4()
    asset_dir = UPLOAD_DIR / str(current_user.school_id) / str(asset_id)
    asset_dir.mkdir(parents=True, exist_ok=True)
    file_path = asset_dir / file.filename
    with open(file_path, "wb") as fh:
        fh.write(content)

    asset = LearningAsset(
        id=asset_id,
        school_id=current_user.school_id,
        uploaded_by_user_id=current_user.user_id,
        source_document_id=source_document_id,
        asset_type=asset_type,
        asset_source=asset_source,
        file_name=file.filename,
        file_path=str(file_path).replace("\\", "/"),
        mime_type=file.content_type,
        reference_code=reference_code.strip(),
        title=title,
        description=description,
        subject=subject,
        grade_level=grade_level,
        topic=topic,
        tags=[],
        processing_status="needs_review",
        is_ai_usable=False,
        is_active=True,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.get(
    "/",
    response_model=LearningAssetListResponse,
    summary="List learning assets",
    tags=["Assets"],
)
async def list_assets(
    subject: Optional[str] = Query(None),
    grade_level: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> LearningAssetListResponse:
    """List school assets with simple filters."""
    query = select(LearningAsset).where(LearningAsset.school_id == current_user.school_id)
    if not include_inactive:
        query = query.where(LearningAsset.is_active.is_(True))
    if subject:
        query = query.where(LearningAsset.subject == subject)
    if grade_level:
        query = query.where(LearningAsset.grade_level == grade_level)
    if topic:
        query = query.where(LearningAsset.topic == topic)
    if asset_type:
        query = query.where(LearningAsset.asset_type == asset_type)

    count_query = select(func.count()).select_from(LearningAsset).where(
        LearningAsset.school_id == current_user.school_id
    )
    if not include_inactive:
        count_query = count_query.where(LearningAsset.is_active.is_(True))
    if subject:
        count_query = count_query.where(LearningAsset.subject == subject)
    if grade_level:
        count_query = count_query.where(LearningAsset.grade_level == grade_level)
    if topic:
        count_query = count_query.where(LearningAsset.topic == topic)
    if asset_type:
        count_query = count_query.where(LearningAsset.asset_type == asset_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    result = await db.execute(query.order_by(LearningAsset.created_at.desc()).offset(skip).limit(limit))
    assets = list(result.scalars().all())
    return LearningAssetListResponse(total=total, assets=assets)


@router.patch(
    "/{asset_id}",
    response_model=LearningAssetResponse,
    summary="Update asset metadata",
    tags=["Assets"],
)
async def update_asset(
    asset_id: uuid.UUID,
    request: LearningAssetUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> LearningAssetResponse:
    """Update teacher-maintained metadata fields."""
    _require_teacher_or_admin(current_user)
    result = await db.execute(
        select(LearningAsset).where(
            and_(
                LearningAsset.id == asset_id,
                LearningAsset.school_id == current_user.school_id,
            )
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(asset, key, value)

    await db.commit()
    await db.refresh(asset)
    return asset


@router.patch(
    "/{asset_id}/review",
    response_model=LearningAssetResponse,
    summary="Review asset for AI usage",
    tags=["Assets"],
)
async def review_asset(
    asset_id: uuid.UUID,
    request: LearningAssetReviewRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> LearningAssetResponse:
    """Admin marks asset as approved/rejected for prompt usage."""
    _require_admin(current_user)
    if request.processing_status not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="processing_status must be approved or rejected")

    result = await db.execute(
        select(LearningAsset).where(
            and_(
                LearningAsset.id == asset_id,
                LearningAsset.school_id == current_user.school_id,
            )
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.processing_status = request.processing_status
    asset.is_ai_usable = request.is_ai_usable

    await db.commit()
    await db.refresh(asset)
    return asset


@router.post(
    "/review-batch",
    response_model=dict,
    summary="Batch review assets for AI usage",
    tags=["Assets"],
)
async def review_assets_batch(
    request: LearningAssetBatchReviewRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Admin batch review for extracted assets by ids or source document."""
    _require_admin(current_user)
    if request.processing_status not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="processing_status must be approved or rejected")
    if not request.asset_ids and not request.source_document_id:
        raise HTTPException(
            status_code=400,
            detail="Provide asset_ids or source_document_id",
        )

    query = select(LearningAsset).where(LearningAsset.school_id == current_user.school_id)
    if request.asset_ids:
        query = query.where(LearningAsset.id.in_(request.asset_ids))
    if request.source_document_id:
        query = query.where(LearningAsset.source_document_id == request.source_document_id)

    result = await db.execute(query)
    assets = list(result.scalars().all())
    if not assets:
        raise HTTPException(status_code=404, detail="No matching assets found")

    updated = 0
    for asset in assets:
        asset.processing_status = request.processing_status
        asset.is_ai_usable = request.is_ai_usable
        updated += 1

    await db.commit()
    return {
        "message": "Asset batch review applied",
        "updated_count": updated,
        "processing_status": request.processing_status,
        "is_ai_usable": request.is_ai_usable,
    }


@router.delete(
    "/{asset_id}",
    response_model=dict,
    summary="Archive asset",
    tags=["Assets"],
)
async def archive_asset(
    asset_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Soft-delete an asset from active catalog."""
    _require_teacher_or_admin(current_user)
    result = await db.execute(
        select(LearningAsset).where(
            and_(
                LearningAsset.id == asset_id,
                LearningAsset.school_id == current_user.school_id,
            )
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.is_active = False
    await db.commit()
    return {"message": "Asset archived successfully", "asset_id": str(asset_id)}
