import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question_number: int
    extracted_text: str
    edited_text: str | None
    confidence: float | None
    page_number: int | None


class OcrJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    worksheet_id: uuid.UUID
    status: str
    extraction_method: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    questions: list[QuestionResponse] = Field(default_factory=list)


class QuestionUpdate(BaseModel):
    text: str = Field(min_length=5, max_length=4000)
