from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.document import DocumentUploadResponse


def test_document_upload_response_accepts_valid_status():
    payload = DocumentUploadResponse(
        message="ok",
        document_id=uuid4(),
        file_name="curriculum.pdf",
        processing_status="pending",
    )
    assert payload.processing_status == "pending"


def test_document_upload_response_rejects_invalid_status():
    with pytest.raises(ValidationError):
        DocumentUploadResponse(
            message="ok",
            document_id=uuid4(),
            file_name="curriculum.pdf",
            processing_status="processing",  # old/invalid value
        )
