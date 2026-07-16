"""
Phase 1 — Story generation API routes.

One employee prompt → professional sections + combined_story.
Optional attachment enriches context when provided.
"""

from fastapi import APIRouter, File, Form, UploadFile

from attachment_processor import extract_attachment_context
from story_models import GenerateResponse
from story_service import generate_story_sections

router = APIRouter(prefix="", tags=["Story Generation"])


@router.post(
    "/generate",
    response_model=GenerateResponse,
    summary="Generate story sections from one employee prompt",
)
async def generate(
    employee_prompt: str = Form(
        ...,
        description="One detailed description of the customer case",
        min_length=1,
    ),
    attachment: UploadFile | None = File(
        default=None,
        description="Optional attachment (image, PDF, DOC, DOCX, TXT)",
    ),
) -> GenerateResponse:
    """
    Employee enters ONE prompt describing the customer case.

    Optionally upload one attachment to enrich context. If no attachment is
    provided, story generation behaves exactly as before.

    AI generates Challenge, Solution Given, and Testimonial (only if appreciation
    is mentioned in the prompt or attachment). Returns combined_story for jury /evaluate.
    """
    uploads: list[UploadFile] = []
    if attachment is not None and attachment.filename:
        uploads.append(attachment)

    attachment_context = await extract_attachment_context(uploads)
    return generate_story_sections(
        employee_prompt.strip(),
        attachment_context=attachment_context,
    )
