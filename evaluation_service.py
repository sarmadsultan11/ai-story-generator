"""
Phase 2 — Jury evaluation service.

Uses the same Groq client as Phase 1. AI scores five criteria (1–10);
overall_score is calculated in Python (not by the AI).
"""

import json
import re
from typing import Any

from fastapi import HTTPException
from openai import APIConnectionError, APIStatusError, RateLimitError

from ai_client import get_ai_client, get_model
from evaluation_models import CriterionScore, EvaluateResponse

# Minimum story length before calling the AI
MIN_STORY_LENGTH = 50

# Evaluation criteria keys (must match response JSON from AI)
CRITERION_KEYS = (
    "customer_delight_impact",
    "going_extra_mile",
    "safety_ethics_tata_values",
    "customer_testimonials_feedback",
    "creativity_innovation",
)

EVALUATION_SYSTEM_PROMPT = """You are an experienced TP-DDL jury member evaluating customer success stories.

Your role is to ASSIST jury members — you are NOT the final decision maker.

Evaluate ONLY using information explicitly present or reasonably implied in the story.
Do NOT assume facts, metrics, testimonials, or outcomes not mentioned.
Be objective, fair, and consistent across criteria.

SCORING (each criterion):
1 = Very weak / not demonstrated
5 = Adequate / partially demonstrated
10 = Exceptional / clearly and strongly demonstrated

CRITERIA:
1. customer_delight_impact — Customer problem significance and positive outcome for the customer
2. going_extra_mile — Effort beyond routine duty (coordination, persistence, personal ownership)
3. safety_ethics_tata_values — Ethical conduct, safety awareness, integrity, Tata values alignment
4. customer_testimonials_feedback — Quality of customer feedback or testimonial evidence in the story
5. creativity_innovation — Novel or creative approach (score lower if standard/routine resolution)

For EACH criterion provide:
- "score": integer from 1 to 10
- "reason": one or two brief objective sentences citing story evidence (or noting absence)

Also provide:
- "strengths": array of 2–4 short strings (key positives from the story)
- "improvement_areas": array of 1–3 short strings (gaps or weaknesses for jury consideration)

IMPORTANT:
- Do NOT include overall_score — the backend calculates it.
- Return valid JSON only. No markdown, no code fences, no extra text.

JSON shape:
{
  "customer_delight_impact": {"score": 8, "reason": "..."},
  "going_extra_mile": {"score": 7, "reason": "..."},
  "safety_ethics_tata_values": {"score": 7, "reason": "..."},
  "customer_testimonials_feedback": {"score": 6, "reason": "..."},
  "creativity_innovation": {"score": 5, "reason": "..."},
  "strengths": ["...", "..."],
  "improvement_areas": ["...", "..."]
}
"""


def validate_story_length(story: str) -> None:
    if len(story) < MIN_STORY_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=(
                f"story is too short for meaningful evaluation. "
                f"Provide at least {MIN_STORY_LENGTH} characters (you sent {len(story)})."
            ),
        )


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI returned invalid JSON. Please try again. Parse error: {exc.msg}",
        ) from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="AI response must be a JSON object.")
    return data


def _parse_criterion(raw: dict[str, Any], key: str) -> CriterionScore:
    block = raw.get(key)
    if not isinstance(block, dict):
        raise HTTPException(status_code=502, detail=f"AI response missing or invalid field: {key}")

    score = block.get("score")
    reason = block.get("reason")

    if not isinstance(score, int) or not 1 <= score <= 10:
        try:
            score = int(float(score))
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Invalid score for {key}. Expected integer 1–10.",
            ) from exc
        if not 1 <= score <= 10:
            raise HTTPException(
                status_code=502,
                detail=f"Score for {key} must be between 1 and 10.",
            )

    if not isinstance(reason, str) or not reason.strip():
        raise HTTPException(status_code=502, detail=f"Missing reason for {key}.")

    return CriterionScore(score=score, reason=reason.strip())


def _parse_string_list(raw: dict[str, Any], key: str) -> list[str]:
    items = raw.get(key)
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=502, detail=f"AI response missing or empty list: {key}")

    result: list[str] = []
    for item in items:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
    if not result:
        raise HTTPException(status_code=502, detail=f"No valid strings in {key}.")
    return result


def _call_evaluation_ai(story: str) -> dict[str, Any]:
    try:
        client = get_ai_client()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    user_message = (
        "Evaluate the following saved customer success story as a TP-DDL jury assistant.\n\n"
        f"Story:\n{story}"
    )

    try:
        completion = client.chat.completions.create(
            model=get_model(),
            temperature=0.3,
            max_tokens=1200,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
    except RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="AI rate limit reached. Wait a moment and try again.",
        ) from exc
    except APIConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not reach AI service. Check internet connection.",
        ) from exc
    except APIStatusError as exc:
        raise HTTPException(status_code=502, detail=f"AI API error: {exc.message}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(exc)}") from exc

    if not completion.choices or not completion.choices[0].message.content:
        raise HTTPException(status_code=502, detail="AI returned an empty evaluation.")

    return _extract_json(completion.choices[0].message.content)


def evaluate_story(story: str) -> EvaluateResponse:
    """
    Phase 2 entry point: evaluate a saved story and return structured jury assistance data.
    """
    validate_story_length(story)
    raw = _call_evaluation_ai(story)

    criteria = {key: _parse_criterion(raw, key) for key in CRITERION_KEYS}

    # overall_score is computed in Python — never trust AI for this
    overall_score = sum(c.score for c in criteria.values())

    return EvaluateResponse(
        customer_delight_impact=criteria["customer_delight_impact"],
        going_extra_mile=criteria["going_extra_mile"],
        safety_ethics_tata_values=criteria["safety_ethics_tata_values"],
        customer_testimonials_feedback=criteria["customer_testimonials_feedback"],
        creativity_innovation=criteria["creativity_innovation"],
        overall_score=overall_score,
        strengths=_parse_string_list(raw, "strengths"),
        improvement_areas=_parse_string_list(raw, "improvement_areas"),
    )
