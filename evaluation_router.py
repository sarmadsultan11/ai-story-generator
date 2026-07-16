"""
Phase 2 — Jury evaluation API routes.

Separate from Phase 1 story generation. Mounted on the same FastAPI app.
"""

from fastapi import APIRouter

from evaluation_models import EvaluateRequest, EvaluateResponse
from evaluation_service import evaluate_story

router = APIRouter(prefix="", tags=["Jury Evaluation"])


@router.post(
    "/evaluate",
    response_model=EvaluateResponse,
    summary="AI-assisted jury evaluation of a saved story",
)
def evaluate(request: EvaluateRequest) -> EvaluateResponse:
    """
    Jury workflow: evaluate a locked saved story.

    The AI assists jury members with scores and feedback — it is NOT the final decision.
    overall_score is calculated server-side as the sum of five criteria (max 50).
    """
    return evaluate_story(request.story.strip())
