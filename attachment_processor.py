"""
Extract readable text from optional employee attachments for story generation.

Supported: .jpg, .jpeg, .png, .pdf, .doc, .docx, .txt
"""

from __future__ import annotations

import base64
import io
import re
from typing import Iterable

from docx import Document
from fastapi import HTTPException, UploadFile
from openai import APIConnectionError, APIStatusError, RateLimitError
from pypdf import PdfReader

from ai_client import get_ai_client

MAX_FILES = 10
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_CHARS = 8000
VISION_MODEL = "llama-3.2-11b-vision-preview"

ALLOWED_EXTENSIONS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _normalize_extension(filename: str) -> str:
    if not filename or "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def _extract_txt(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _extract_pdf(raw: bytes) -> str:
    reader = PdfReader(io.BytesIO(raw))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text and text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts)


def _extract_docx(raw: bytes) -> str:
    document = Document(io.BytesIO(raw))
    parts = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n".join(parts)


def _extract_legacy_doc(raw: bytes) -> str:
    utf16_chunks: list[str] = []
    i = 0
    while i < len(raw) - 1:
        chunk_chars: list[str] = []
        j = i
        while j < len(raw) - 1:
            code = raw[j] | (raw[j + 1] << 8)
            if 32 <= code <= 126 or code in (10, 13, 9):
                chunk_chars.append(chr(code))
                j += 2
            else:
                break
        if len(chunk_chars) >= 4:
            utf16_chunks.append("".join(chunk_chars))
            i = j
        else:
            i += 1

    if utf16_chunks:
        return " ".join(utf16_chunks)

    latin = raw.decode("latin-1", errors="ignore")
    ascii_parts = re.findall(r"[\x20-\x7E]{4,}", latin)
    return " ".join(ascii_parts)


def _extract_image(raw: bytes, mime_type: str) -> str:
    client = get_ai_client()
    encoded = base64.b64encode(raw).decode("ascii")
    prompt = (
        "Extract all readable text from this image exactly as written. "
        "Return plain text only with no commentary. "
        "If there is no text, return an empty string."
    )
    try:
        completion = client.chat.completions.create(
            model=VISION_MODEL,
            temperature=0,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                        },
                    ],
                }
            ],
        )
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail="AI rate limit reached. Try again shortly.") from exc
    except APIConnectionError as exc:
        raise HTTPException(status_code=503, detail="Could not reach AI service.") from exc
    except APIStatusError as exc:
        raise HTTPException(status_code=502, detail=f"AI API error: {exc.message}") from exc

    if not completion.choices or not completion.choices[0].message.content:
        return ""
    return completion.choices[0].message.content.strip()


def _extract_file_content(filename: str, raw: bytes) -> str:
    ext = _normalize_extension(filename)
    if ext == ".txt":
        return _extract_txt(raw).strip()
    if ext == ".pdf":
        return _extract_pdf(raw).strip()
    if ext == ".docx":
        return _extract_docx(raw).strip()
    if ext == ".doc":
        return _extract_legacy_doc(raw).strip()
    if ext in IMAGE_EXTENSIONS:
        mime = ALLOWED_EXTENSIONS[ext]
        return _extract_image(raw, mime).strip()
    return ""


async def _read_upload(file: UploadFile) -> tuple[str, bytes]:
    filename = (file.filename or "attachment").strip()
    ext = _normalize_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext or filename}'. Allowed: {allowed}",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail=f"Attachment '{filename}' is empty.")
    if len(raw) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Attachment '{filename}' exceeds the {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB limit.",
        )
    return filename, raw


async def extract_attachment_context(files: Iterable[UploadFile]) -> str | None:
    """
    Extract and merge text from uploaded attachments.

    Returns None when no files are provided so callers keep the original code path.
    """
    uploads = [file for file in files if file and file.filename]
    if not uploads:
        return None
    if len(uploads) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many attachments. Maximum allowed is {MAX_FILES}.",
        )

    sections: list[str] = []
    total_chars = 0

    for upload in uploads:
        filename, raw = await _read_upload(upload)
        extracted = _extract_file_content(filename, raw)
        if not extracted:
            continue

        header = f"--- Attachment: {filename} ---"
        block = f"{header}\n{extracted}"
        remaining = MAX_EXTRACTED_CHARS - total_chars
        if remaining <= 0:
            break
        if len(block) > remaining:
            block = block[:remaining].rstrip() + "…"
        sections.append(block)
        total_chars += len(block)

    if not sections:
        return None

    return "\n\n".join(sections)
