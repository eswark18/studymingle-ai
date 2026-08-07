import hashlib
import tempfile
import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.config import settings
from app.core.storage import create_download_url, delete_private_file, upload_private_file
from app.core.uploads import safe_filename, validate_file_signature
from app.models import Worksheet
from app.schemas.worksheet import DownloadResponse, WorksheetResponse

router = APIRouter(prefix="/worksheets", tags=["worksheets"])


async def owned_worksheet(
    worksheet_id: uuid.UUID,
    user: CurrentUser,
    database: DatabaseSession,
) -> Worksheet:
    worksheet = await database.scalar(
        select(Worksheet)
        .where(Worksheet.id == worksheet_id)
        .where(Worksheet.user_id == user.id)
        .where(Worksheet.deleted_at.is_(None))
    )
    if worksheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worksheet not found.")
    return worksheet


@router.post("", response_model=WorksheetResponse, status_code=status.HTTP_201_CREATED)
async def upload_worksheet(
    user: CurrentUser,
    database: DatabaseSession,
    file: Annotated[UploadFile, File()],
) -> Worksheet:
    filename = safe_filename(file.filename)
    digest = hashlib.sha256()
    size = 0

    with tempfile.SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b") as temporary:
        try:
            first_chunk = await file.read(64 * 1024)
            try:
                extension = validate_file_signature(file.content_type, first_chunk)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=str(exc),
                ) from exc

            chunk = first_chunk
            while chunk:
                size += len(chunk)
                if size > settings.upload_max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Worksheet exceeds the 10 MB upload limit.",
                    )
                digest.update(chunk)
                temporary.write(chunk)
                chunk = await file.read(64 * 1024)

            worksheet_id = uuid.uuid4()
            storage_key = f"{user.id}/{worksheet_id}{extension}"
            try:
                await upload_private_file(storage_key, temporary, file.content_type or "")
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Worksheet storage is temporarily unavailable.",
                ) from exc
        finally:
            await file.close()

    worksheet = Worksheet(
        id=worksheet_id,
        user_id=user.id,
        original_filename=filename,
        storage_key=storage_key,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        sha256=digest.hexdigest(),
        status="uploaded",
    )
    database.add(worksheet)
    try:
        await database.commit()
    except Exception:
        await database.rollback()
        await delete_private_file(storage_key)
        raise
    await database.refresh(worksheet)
    return worksheet


@router.get("", response_model=list[WorksheetResponse])
async def list_worksheets(user: CurrentUser, database: DatabaseSession) -> list[Worksheet]:
    result = await database.scalars(
        select(Worksheet)
        .where(Worksheet.user_id == user.id)
        .where(Worksheet.deleted_at.is_(None))
        .order_by(Worksheet.created_at.desc())
        .limit(50)
    )
    return list(result)


@router.get("/{worksheet_id}/download", response_model=DownloadResponse)
async def download_worksheet(
    worksheet_id: uuid.UUID,
    user: CurrentUser,
    database: DatabaseSession,
) -> DownloadResponse:
    worksheet = await owned_worksheet(worksheet_id, user, database)
    url = await create_download_url(worksheet.storage_key, worksheet.original_filename)
    return DownloadResponse(url=url)


@router.delete("/{worksheet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_worksheet(
    worksheet_id: uuid.UUID,
    user: CurrentUser,
    database: DatabaseSession,
) -> None:
    worksheet = await owned_worksheet(worksheet_id, user, database)
    try:
        await delete_private_file(worksheet.storage_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worksheet storage is temporarily unavailable.",
        ) from exc
    await database.delete(worksheet)
    await database.commit()
