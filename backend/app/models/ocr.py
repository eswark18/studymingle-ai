import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.tutor import TutorSession
    from app.models.worksheet import Worksheet


class OcrJob(TimestampMixin, Base):
    __tablename__ = "ocr_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    worksheet_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("worksheets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True, nullable=False)
    extraction_method: Mapped[str | None] = mapped_column(String(32))
    raw_text: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(String(500))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    worksheet: Mapped["Worksheet"] = relationship(back_populates="ocr_jobs")
    questions: Mapped[list["ExtractedQuestion"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="ExtractedQuestion.question_number",
    )


class ExtractedQuestion(TimestampMixin, Base):
    __tablename__ = "extracted_questions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("ocr_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    edited_text: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    page_number: Mapped[int | None] = mapped_column(Integer)

    job: Mapped["OcrJob"] = relationship(back_populates="questions")
    tutor_sessions: Mapped[list["TutorSession"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )
