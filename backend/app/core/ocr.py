import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import pytesseract
from PIL import Image, ImageFilter, ImageOps
from pypdf import PdfReader

from app.core.config import settings


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    method: str


def extract_image_text(path: Path) -> str:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        prepared = ImageOps.grayscale(image)
        if prepared.width < 2000:
            scale = 2000 / prepared.width
            prepared = prepared.resize(
                (2000, round(prepared.height * scale)),
                Image.Resampling.LANCZOS,
            )
        prepared = ImageOps.autocontrast(prepared, cutoff=1).filter(ImageFilter.SHARPEN)
        return pytesseract.image_to_string(prepared, config="--oem 3 --psm 4")


def extract_pdf_text(path: Path) -> ExtractionResult:
    reader = PdfReader(path)
    if len(reader.pages) > settings.ocr_max_pages:
        raise ValueError(f"PDF exceeds the {settings.ocr_max_pages}-page OCR limit.")
    native_text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    if len(native_text) >= 50:
        return ExtractionResult(text=native_text, method="pdf_text")

    with TemporaryDirectory(prefix="studymingle-ocr-") as directory:
        output_prefix = Path(directory) / "page"
        subprocess.run(
            [
                "pdftoppm",
                "-png",
                "-r",
                "200",
                "-f",
                "1",
                "-l",
                str(settings.ocr_max_pages),
                str(path),
                str(output_prefix),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        pages = sorted(Path(directory).glob("page-*.png"))
        page_text = [extract_image_text(page) for page in pages]
    return ExtractionResult(text="\n".join(page_text).strip(), method="tesseract_pdf")


def extract_document_text(path: Path, content_type: str) -> ExtractionResult:
    if content_type == "application/pdf":
        return extract_pdf_text(path)
    if content_type in {"image/png", "image/jpeg"}:
        return ExtractionResult(text=extract_image_text(path).strip(), method="tesseract_image")
    raise ValueError("Unsupported worksheet type.")


NUMBER_LINE = re.compile(r"^\s*0?(\d{1,2})[.)]?\s*$")
INLINE_QUESTION = re.compile(r"^\s*0?(\d{1,2})[.)]\s+(.{15,})$")
QUESTION_INTENT = re.compile(
    r"\b(what|which|why|how|calculate|solve|find|determine|explain|describe|define|"
    r"identify|compare|evaluate|simplify|prove|show|write|resolve)\b",
    re.IGNORECASE,
)


def _clean_question(lines: list[str]) -> str:
    useful = []
    for line in lines:
        cleaned = " ".join(line.split())
        if cleaned.startswith("Original StudyMingle") or cleaned == "Hints before answers":
            break
        if cleaned.upper().startswith(
            ("LEARNING MODE", "LEARNNG MODE", "NAME DATE", "COURSE /SECTION")
        ):
            continue
        if not cleaned or (cleaned.isupper() and len(cleaned) < 60):
            continue
        useful.append(cleaned)
    return " ".join(useful).strip()


def parse_questions(text: str) -> list[tuple[int, str]]:
    lines = text.splitlines()
    questions: list[tuple[int, str]] = []
    active_number: int | None = None
    active_lines: list[str] = []

    def finish() -> None:
        if active_number is None:
            return
        question_text = _clean_question(active_lines)
        if len(question_text) >= 15:
            questions.append((active_number, question_text[:4000]))

    for line in lines:
        inline = INLINE_QUESTION.match(line)
        marker = NUMBER_LINE.match(line)
        if inline:
            finish()
            active_number = int(inline.group(1))
            active_lines = [inline.group(2)]
        elif marker:
            finish()
            active_number = int(marker.group(1))
            active_lines = []
        elif active_number is not None:
            active_lines.append(line)
    finish()

    if questions:
        return questions

    paragraphs = re.split(r"\n\s*\n", text)
    reviewable = []
    for paragraph in paragraphs:
        cleaned = _clean_question(paragraph.splitlines())
        looks_like_question = QUESTION_INTENT.search(cleaned) or cleaned.endswith(("?", "."))
        if len(cleaned) >= 35 and looks_like_question:
            reviewable.append(cleaned[:4000])
    if len(reviewable) >= 2:
        return list(enumerate(reviewable[:50], start=1))

    sentences = re.split(r"(?<=[?.])\s+(?=[A-Z])", " ".join(text.split()))
    return [
        (index, sentence[:4000])
        for index, sentence in enumerate(sentences, start=1)
        if len(sentence) >= 20 and sentence.endswith(("?", "."))
    ][:50]
