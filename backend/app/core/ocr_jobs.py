import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionFactory
from app.core.ocr import extract_document_text, parse_questions
from app.core.storage import download_private_file
from app.models import ExtractedQuestion, OcrJob


async def process_ocr_job(job_id: uuid.UUID) -> None:
    async with SessionFactory() as database:
        job = await database.scalar(
            select(OcrJob)
            .where(OcrJob.id == job_id)
            .options(selectinload(OcrJob.worksheet))
        )
        if job is None or job.status not in {"queued", "retrying"}:
            return

        job.status = "processing"
        job.started_at = datetime.now(UTC)
        job.error_message = None
        job.worksheet.status = "processing"
        await database.commit()

        suffix = {
            "application/pdf": ".pdf",
            "image/png": ".png",
            "image/jpeg": ".jpg",
        }.get(job.worksheet.content_type, ".bin")

        try:
            with TemporaryDirectory(prefix="studymingle-job-") as directory:
                document_path = Path(directory) / f"worksheet{suffix}"
                with document_path.open("w+b") as document:
                    await download_private_file(job.worksheet.storage_key, document)
                result = await asyncio.to_thread(
                    extract_document_text,
                    document_path,
                    job.worksheet.content_type,
                )
            parsed = parse_questions(result.text)
            if not parsed:
                raise ValueError("No reviewable questions were found in this worksheet.")

            for number, question_text in parsed[:50]:
                database.add(
                    ExtractedQuestion(
                        job_id=job.id,
                        question_number=number,
                        extracted_text=question_text,
                        confidence=None,
                    )
                )
            job.status = "completed"
            job.extraction_method = result.method
            job.raw_text = result.text[:100_000]
            job.completed_at = datetime.now(UTC)
            job.worksheet.status = "extracted"
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)[:500]
            job.completed_at = datetime.now(UTC)
            job.worksheet.status = "failed"
        await database.commit()
