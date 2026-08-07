import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WorksheetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    status: str
    created_at: datetime


class DownloadResponse(BaseModel):
    url: str
    expires_in: int = 300
