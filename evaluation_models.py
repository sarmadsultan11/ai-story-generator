"""
Phase 2 — Pydantic models for jury story evaluation.

Independent from Phase 1 story generation models.
"""

from pydantic import BaseModel, Field, field_validator


class EvaluateRequest(BaseModel):
    """Saved story text submitted by a jury member for AI-assisted evaluation."""

    story: str = Field(
        ...,
        description="Complete saved story text (locked employee submission)",
        min_length=1,
        max_length=10000,
    )

    @field_validator("story")
    @classmethod
    def strip_and_reject_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("story cannot be empty or whitespace only.")
        return cleaned


class CriterionScore(BaseModel):
    """Score and brief justification for one evaluation parameter."""

    score: int = Field(..., ge=1, le=10, description="Score from 1 to 10")
    reason: str = Field(..., min_length=1, description="Brief justification for the score")


class EvaluateResponse(BaseModel):
    """Structured jury evaluation returned to the company backend."""

    customer_delight_impact: CriterionScore
    going_extra_mile: CriterionScore
    safety_ethics_tata_values: CriterionScore
    customer_testimonials_feedback: CriterionScore
    creativity_innovation: CriterionScore
    overall_score: int = Field(..., ge=5, le=50, description="Sum of all criterion scores (max 50)")
    strengths: list[str] = Field(..., min_length=1, description="Key strengths identified in the story")
    improvement_areas: list[str] = Field(
        ..., min_length=1, description="Areas where the story could be stronger"
    )
