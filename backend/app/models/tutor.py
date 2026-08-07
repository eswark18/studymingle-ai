import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.ocr import ExtractedQuestion
    from app.models.user import User


class TutorSession(TimestampMixin, Base):
    __tablename__ = "tutor_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("extracted_questions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    education_track: Mapped[str] = mapped_column(String(32), nullable=False)
    grade_or_year: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True, nullable=False)

    user: Mapped["User"] = relationship()
    question: Mapped["ExtractedQuestion"] = relationship(back_populates="tutor_sessions")
    hints: Mapped[list["TutorHint"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="TutorHint.sequence_number"
    )
    attempts: Mapped[list["TutorAttempt"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="TutorAttempt.created_at"
    )


class TutorHint(TimestampMixin, Base):
    __tablename__ = "tutor_hints"
    __table_args__ = (UniqueConstraint("session_id", "sequence_number"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tutor_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    hint_type: Mapped[str] = mapped_column(String(32), nullable=False)
    hint_text: Mapped[str] = mapped_column(Text, nullable=False)

    session: Mapped["TutorSession"] = relationship(back_populates="hints")


class TutorAttempt(TimestampMixin, Base):
    __tablename__ = "tutor_attempts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tutor_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    attempt_text: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_text: Mapped[str] = mapped_column(Text, nullable=False)
    misconception: Mapped[str | None] = mapped_column(String(500))
    is_correct: Mapped[bool | None] = mapped_column(Boolean)

    session: Mapped["TutorSession"] = relationship(back_populates="attempts")
