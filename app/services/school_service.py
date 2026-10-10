"""School service module."""

import uuid
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.school import School, SchoolSettings
from app.schemas.school import (
    SchoolSettingsUpdate,
    SchoolSettingsResponse,
    SchoolDetailResponse,
    SchoolUpdateRequest,
)


class SchoolService:
    """Service for school management operations."""

    @staticmethod
    async def get_school(
        school_id: uuid.UUID,
        db: AsyncSession,
    ) -> SchoolDetailResponse:
        """
        Get school details including settings.

        Args:
            school_id: The school ID
            db: Database session

        Returns:
            SchoolDetailResponse with full school information

        Raises:
            ValueError: If school not found
        """
        result = await db.execute(
            select(School).filter(School.id == school_id)
        )
        school = result.scalar_one_or_none()

        if not school:
            raise ValueError(f"School {school_id} not found")

        # Get settings
        settings_result = await db.execute(
            select(SchoolSettings).filter(SchoolSettings.school_id == school_id)
        )
        settings = settings_result.scalar_one_or_none()

        return SchoolDetailResponse(
            school_id=school.id,
            name=school.name,
            contact_email=school.contact_email,
            contact_phone=school.contact_phone or "",
            address=school.address,
            is_active=school.is_active,
            created_at=school.created_at,
            updated_at=school.updated_at,
            settings=(
                SchoolSettingsResponse(
                    school_id=settings.school_id,
                    logo_url=settings.logo_url,
                    logo_storage_path=settings.logo_storage_path,
                    colors={
                        "primary": settings.primary_color,
                        "secondary": settings.secondary_color,
                    },
                    llm_provider=settings.primary_llm_provider,
                    exam_format=settings.exam_format,
                    document_style=settings.document_style or {},
                    created_at=settings.created_at,
                    updated_at=settings.updated_at,
                )
                if settings
                else None
            ),
        )

    @staticmethod
    async def update_school(
        school_id: uuid.UUID,
        request: SchoolUpdateRequest,
        db: AsyncSession,
    ) -> SchoolDetailResponse:
        """
        Update school information.

        Args:
            school_id: The school ID
            request: Update request with new school info
            db: Database session

        Returns:
            Updated SchoolDetailResponse

        Raises:
            ValueError: If school not found
        """
        result = await db.execute(
            select(School).filter(School.id == school_id)
        )
        school = result.scalar_one_or_none()

        if not school:
            raise ValueError(f"School {school_id} not found")

        try:
            # Update school fields
            update_data = {}
            if request.name:
                update_data["name"] = request.name
            if request.contact_email:
                update_data["contact_email"] = request.contact_email
            if request.contact_phone:
                update_data["contact_phone"] = request.contact_phone
            if request.address:
                update_data["address"] = request.address

            update_data["updated_at"] = datetime.utcnow()

            await db.execute(
                update(School)
                .where(School.id == school_id)
                .values(**update_data)
            )
            await db.commit()

            # Return updated school
            return await SchoolService.get_school(school_id, db)

        except Exception as e:
            await db.rollback()
            raise ValueError(f"Failed to update school: {str(e)}")

    @staticmethod
    async def get_settings(
        school_id: uuid.UUID,
        db: AsyncSession,
    ) -> SchoolSettingsResponse:
        """
        Get school settings.

        Args:
            school_id: The school ID
            db: Database session

        Returns:
            SchoolSettingsResponse with current settings

        Raises:
            ValueError: If settings not found
        """
        result = await db.execute(
            select(SchoolSettings).filter(SchoolSettings.school_id == school_id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            raise ValueError(f"Settings for school {school_id} not found")

        return SchoolSettingsResponse(
            school_id=settings.school_id,
            logo_url=settings.logo_url,
            logo_storage_path=settings.logo_storage_path,
            colors={
                "primary": settings.primary_color,
                "secondary": settings.secondary_color,
            },
            llm_provider=settings.primary_llm_provider,
            exam_format=settings.exam_format,
            document_style=settings.document_style or {},
            created_at=settings.created_at,
            updated_at=settings.updated_at,
        )

    @staticmethod
    async def update_settings(
        school_id: uuid.UUID,
        request: SchoolSettingsUpdate,
        db: AsyncSession,
    ) -> SchoolSettingsResponse:
        """
        Update school settings.

        Args:
            school_id: The school ID
            request: Update request with new settings
            db: Database session

        Returns:
            Updated SchoolSettingsResponse

        Raises:
            ValueError: If settings not found
        """
        result = await db.execute(
            select(SchoolSettings).filter(SchoolSettings.school_id == school_id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            raise ValueError(f"Settings for school {school_id} not found")

        try:
            # Update settings fields
            update_data = {}
            if "logo_url" in request.model_fields_set:
                update_data["logo_url"] = request.logo_url
            if request.logo_storage_path is not None:
                update_data["logo_storage_path"] = request.logo_storage_path
            if request.colors and "primary" in request.colors:
                update_data["primary_color"] = request.colors["primary"]
            if request.colors and "secondary" in request.colors:
                update_data["secondary_color"] = request.colors["secondary"]
            if request.llm_provider:
                update_data["primary_llm_provider"] = request.llm_provider
            if request.exam_format:
                update_data["exam_format"] = request.exam_format
            if request.document_style is not None:
                update_data["document_style"] = {
                    str(k): v for k, v in request.document_style.items()
                    if str(k) in {
                        "page_size", "margin_mm", "top_margin_mm", "bottom_margin_mm",
                        "font_size", "line_spacing", "question_spacing_mm",
                        "compact_options", "show_page_numbers", "accent_color",
                    }
                }

            update_data["updated_at"] = datetime.utcnow()

            await db.execute(
                update(SchoolSettings)
                .where(SchoolSettings.school_id == school_id)
                .values(**update_data)
            )
            await db.commit()

            # Return updated settings
            return await SchoolService.get_settings(school_id, db)

        except Exception as e:
            await db.rollback()
            raise ValueError(f"Failed to update settings: {str(e)}")

    @staticmethod
    async def initialize_settings(
        school_id: uuid.UUID,
        db: AsyncSession,
    ) -> SchoolSettings:
        """
        Initialize default settings for a new school.

        Args:
            school_id: The school ID
            db: Database session

        Returns:
            Created SchoolSettings object
        """
        settings = SchoolSettings(
            school_id=school_id,
            logo_url=None,
            primary_color="#0066CC",
            secondary_color="#00CC99",
            primary_llm_provider="openai",
            exam_format="multiple_choice",
        )

        db.add(settings)
        await db.commit()
        await db.refresh(settings)

        return settings
