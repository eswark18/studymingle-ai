import asyncio
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


def storage_client(endpoint_url: str | None = None):
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url or settings.storage_endpoint_url,
        region_name=settings.storage_region,
        aws_access_key_id=settings.storage_access_key_id,
        aws_secret_access_key=settings.storage_secret_access_key,
    )


async def ensure_bucket() -> None:
    if not settings.storage_auto_create_bucket:
        return
    client = storage_client()
    try:
        await asyncio.to_thread(client.head_bucket, Bucket=settings.storage_bucket)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code not in {"404", "NoSuchBucket", "NotFound"}:
            raise
        await asyncio.to_thread(client.create_bucket, Bucket=settings.storage_bucket)


async def upload_private_file(
    storage_key: str,
    file_object: BinaryIO,
    content_type: str,
) -> None:
    await ensure_bucket()
    file_object.seek(0)
    client = storage_client()
    await asyncio.to_thread(
        client.upload_fileobj,
        file_object,
        settings.storage_bucket,
        storage_key,
        {"ContentType": content_type},
    )


async def delete_private_file(storage_key: str) -> None:
    client = storage_client()
    await asyncio.to_thread(
        client.delete_object,
        Bucket=settings.storage_bucket,
        Key=storage_key,
    )


async def create_download_url(storage_key: str, filename: str) -> str:
    client = storage_client(settings.storage_public_endpoint_url)
    return client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.storage_bucket,
            "Key": storage_key,
            "ResponseContentDisposition": f'attachment; filename="{filename}"',
        },
        ExpiresIn=300,
    )
