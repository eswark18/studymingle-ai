import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TutorStartRequest(BaseModel):
    education_track: Literal["school", "engineering"]
    grade_or_year: str = Field(min_length=2, max_length=64)
    subject: str = Field(min_length=2, max_length=120)


class TutorAttemptRequest(BaseModel):
    attempt_text: str = Field(min_length=3, max_length=4000)


class TutorGeneration(BaseModel):
    message: str = Field(min_length=3, max_length=4000)
    hint_type: Literal["question", "concept", "method", "feedback"]
    is_correct: bool | None = None
    misconception: str | None = Field(default=None, max_length=500)
    next_action: Literal["attempt", "request_hint", "revise", "complete"]


class TutorHintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence_number: int
    hint_type: str
    hint_text: str
    created_at: datetime


class TutorAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attempt_text: str
    feedback_text: str
    misconception: str | None
    is_correct: bool | None
    created_at: datetime


class TutorSessionResponse(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    source_text: str
    learning_text: str
    education_track: str
    grade_or_year: str
    subject: str
    status: str
    hints: list[TutorHintResponse]
    attempts: list[TutorAttemptResponse]
    can_request_hint: bool
    created_at: datetime
