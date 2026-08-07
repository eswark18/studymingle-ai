from pathlib import Path

ALLOWED_UPLOADS = {
    "application/pdf": (".pdf", b"%PDF-"),
    "image/png": (".png", b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": (".jpg", b"\xff\xd8\xff"),
}


def safe_filename(filename: str | None) -> str:
    cleaned = (
        Path(filename or "worksheet")
        .name.replace('"', "")
        .replace("\r", "")
        .replace("\n", "")
        .strip()
    )
    return cleaned[:255] or "worksheet"


def validate_file_signature(content_type: str | None, header: bytes) -> str:
    if content_type not in ALLOWED_UPLOADS:
        raise ValueError("Only PDF, PNG, and JPEG worksheets are accepted.")
    extension, signature = ALLOWED_UPLOADS[content_type]
    if not header.startswith(signature):
        raise ValueError("The file contents do not match the declared file type.")
    return extension
