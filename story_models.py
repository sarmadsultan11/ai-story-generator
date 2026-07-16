"""
Phase 1 — Pydantic models for story generation.

Employee provides ONE prompt (simple notes). AI splits it into professional sections.
"""

from pydantic import BaseModel, Field, field_validator


class GenerateRequest(BaseModel):
    """Single employee prompt — messy notes describing the full customer case."""

    employee_prompt: str = Field(
        ...,
        description="One detailed description: challenge, solution, and any customer appreciation",
        min_length=1,
        max_length=4000,
    )

    @field_validator("employee_prompt")
    @classmethod
    def strip_and_reject_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("employee_prompt cannot be empty.")
        return cleaned


class GenerateResponse(BaseModel):
    """Professional sections plus combined_story for jury evaluation."""

    challenge: str = Field(..., description="Professional Challenge section")
    solution_given: str = Field(..., description="Professional Solution Given section")
    testimonial: str = Field(
        default="",
        description="Professional testimonial only if appreciation was in the prompt; else empty",
    )
    combined_story: str = Field(
        ...,
        description="Formatted story for POST /evaluate",
    )
    character_count: int = Field(
        ...,
        description="Total characters in challenge + solution_given + testimonial (each section max 2000)",
    )
