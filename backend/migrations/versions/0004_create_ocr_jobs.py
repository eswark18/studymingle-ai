"""Create OCR jobs and extracted questions.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ocr_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("worksheet_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("extraction_method", sa.String(length=32), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["worksheet_id"], ["worksheets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ocr_jobs_worksheet_id", "ocr_jobs", ["worksheet_id"], unique=False)
    op.create_index("ix_ocr_jobs_status", "ocr_jobs", ["status"], unique=False)

    op.create_table(
        "extracted_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("question_number", sa.Integer(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("edited_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["ocr_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_extracted_questions_job_id",
        "extracted_questions",
        ["job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_extracted_questions_job_id", table_name="extracted_questions")
    op.drop_table("extracted_questions")
    op.drop_index("ix_ocr_jobs_status", table_name="ocr_jobs")
    op.drop_index("ix_ocr_jobs_worksheet_id", table_name="ocr_jobs")
    op.drop_table("ocr_jobs")
