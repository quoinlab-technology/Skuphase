import pytest
from unittest.mock import AsyncMock

from app.services.curriculum_service import CurriculumService


@pytest.mark.asyncio
async def test_search_topics_builds_typed_jsonb_cast_without_type_error():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=type("Result", (), {"all": lambda self: []})())

    result = await CurriculumService.search_topics("water", db, limit=3)

    assert result == []
    db.execute.assert_awaited_once()
