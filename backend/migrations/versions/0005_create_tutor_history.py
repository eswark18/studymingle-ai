"""Create tutor sessions, hints, and attempts.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "tutor_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("education_track", sa.String(32), nullable=False),
        sa.Column("grade_or_year", sa.String(64), nullable=False),
        sa.Column("subject", sa.String(120), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["question_id"], ["extracted_questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tutor_sessions_user_id", "tutor_sessions", ["user_id"])
    op.create_index("ix_tutor_sessions_question_id", "tutor_sessions", ["question_id"])
    op.create_index("ix_tutor_sessions_status", "tutor_sessions", ["status"])

    op.create_table(
        "tutor_hints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("hint_type", sa.String(32), nullable=False),
        sa.Column("hint_text", sa.Text(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["session_id"], ["tutor_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "sequence_number"),
    )
    op.create_index("ix_tutor_hints_session_id", "tutor_hints", ["session_id"])

    op.create_table(
        "tutor_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_text", sa.Text(), nullable=False),
        sa.Column("feedback_text", sa.Text(), nullable=False),
        sa.Column("misconception", sa.String(500), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["session_id"], ["tutor_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tutor_attempts_session_id", "tutor_attempts", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_tutor_attempts_session_id", table_name="tutor_attempts")
    op.drop_table("tutor_attempts")
    op.drop_index("ix_tutor_hints_session_id", table_name="tutor_hints")
    op.drop_table("tutor_hints")
    op.drop_index("ix_tutor_sessions_status", table_name="tutor_sessions")
    op.drop_index("ix_tutor_sessions_question_id", table_name="tutor_sessions")
    op.drop_index("ix_tutor_sessions_user_id", table_name="tutor_sessions")
    op.drop_table("tutor_sessions")
