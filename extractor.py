from __future__ import annotations

import io
from pathlib import Path

from schemas import ExtractionResult


SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


def _decode_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1255", "iso-8859-8"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_txt(data: bytes) -> str:
    return _decode_bytes(data)


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover
        return f"PDF extraction failed: missing dependency pypdf ({exc})"

    reader = PdfReader(io.BytesIO(data))
    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        pages.append(page.extract_text() or f"[empty page {i + 1}]")
    return "\n\n".join(pages)


def _extract_docx(data: bytes) -> str:
    try:
        from docx import Document
    except Exception as exc:  # pragma: no cover
        return f"DOCX extraction failed: missing dependency python-docx ({exc})"

    document = Document(io.BytesIO(data))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def extract_text_from_upload(filename: str, data: bytes) -> ExtractionResult:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        return ExtractionResult(
            text="",
            status=f"Unsupported file type: {extension}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            filename=filename,
        )

    if extension == ".txt":
        text = _extract_txt(data)
    elif extension == ".pdf":
        text = _extract_pdf(data)
    else:
        text = _extract_docx(data)

    status = "ok" if text.strip() else "warning: empty extracted text"
    return ExtractionResult(text=text, status=status, filename=filename)
