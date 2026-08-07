import pytest

from app.core.uploads import safe_filename, validate_file_signature


@pytest.mark.parametrize(
    ("content_type", "header", "extension"),
    [
        ("application/pdf", b"%PDF-1.7", ".pdf"),
        ("image/png", b"\x89PNG\r\n\x1a\ncontent", ".png"),
        ("image/jpeg", b"\xff\xd8\xffcontent", ".jpg"),
    ],
)
def test_file_signatures(content_type: str, header: bytes, extension: str) -> None:
    assert validate_file_signature(content_type, header) == extension


def test_mismatched_signature_is_rejected() -> None:
    with pytest.raises(ValueError):
        validate_file_signature("application/pdf", b"not a pdf")


def test_filename_removes_paths_and_header_characters() -> None:
    assert safe_filename('../../unsafe\n"name.pdf') == "unsafename.pdf"
