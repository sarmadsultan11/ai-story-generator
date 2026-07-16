"""
Phase 1 — Story generation from ONE employee prompt.

AI reads the full prompt, creates Challenge + Solution Given sections,
and Testimonial ONLY if customer appreciation is mentioned.

Phase 2 /evaluate is unchanged — jury uses combined_story.
"""

import json
import re
from typing import Any

from fastapi import HTTPException
from openai import APIConnectionError, APIStatusError, RateLimitError

from ai_client import get_ai_client, get_model
from story_models import GenerateResponse

MIN_PROMPT_LENGTH = 10
MAX_SECTION_LENGTH = 2000

# Testimonial is generated only when the employee prompt mentions appreciation
APPRECIATION_SIGNALS = (
    "thank you",
    "thank",
    "thanked",
    "appreciated",
    "appreciat",
    "appreciation",
    "gratitude",
    "grateful",
    "positive feedback",
    "customer thanked",
    "customer appreciated",
    "testimonial",
    "compliment",
    "praised",
    "praise",
    "acknowledgement",
    "acknowledgment",
    "happy with",
    "satisfied",
)

STORY_SYSTEM_PROMPT = f"""You are a professional corporate writer for TP-DDL customer success stories.

The employee provides ONE description of a customer case (simple notes, not professional writing).
Read the entire input and split it into separate, detailed professional sections.

RULES:
- Use ONLY information from the employee prompt and any attachment content provided. Do NOT invent facts, names, or outcomes.
- Write in detailed, professional corporate business English.
- Expand each section with clear context, specific actions, impact, and outcomes drawn from the input.
- Each section is separate — do NOT merge into one paragraph.
- Return valid JSON only. No markdown, no code fences.

SECTION 1 — "challenge":
- Describe the customer problem, business issue, pain point, timeline, and why it mattered in detail.
- Include relevant background and impact on the customer from the employee input.

SECTION 2 — "solution_given":
- Describe in detail the actions taken, coordination, ownership, resolution steps, and customer benefit.
- Explain what the employee/team did, how the issue was resolved, and the result for the customer.

SECTION 3 — "testimonial":
- generate_testimonial flag is sent by the backend — you MUST obey it.
- If "no": return exactly "" — do NOT write any testimonial.
- If "yes": write a detailed, professional Customer Testimonial using appreciation mentioned in the input.
- NEVER invent testimonials. NEVER assume appreciation when flag is "no".

LENGTH:
- Each section ("challenge", "solution_given", "testimonial") must be {MAX_SECTION_LENGTH} characters or fewer on its own.
- Write as much useful detail as possible within each section's limit.

JSON shape:
{{
  "challenge": "...",
  "solution_given": "...",
  "testimonial": "..."
}}
"""


def has_customer_appreciation(text: str) -> bool:
    """Testimonial is required only if the single employee prompt mentions appreciation."""
    if not text or not text.strip():
        return False
    lower = text.lower()
    return any(signal in lower for signal in APPRECIATION_SIGNALS)


def combine_story_sections(challenge: str, solution_given: str, testimonial: str = "") -> str:
    """Build combined_story for POST /evaluate. Omits testimonial heading when empty."""
    parts = [
        f"Challenge:\n{challenge.strip()}",
        f"\nSolution Given:\n{solution_given.strip()}",
    ]
    if testimonial and testimonial.strip():
        parts.append(f"\nCustomer Testimonial:\n{testimonial.strip()}")
    return "\n".join(parts)


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


def _trim_to_limit(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    trimmed = text[:limit]
    last_period = max(trimmed.rfind(". "), trimmed.rfind(".\n"), trimmed.rfind("."))
    if last_period > limit // 2:
        return trimmed[: last_period + 1].strip()
    return trimmed.rstrip() + "…"


def _enforce_section_lengths(challenge: str, solution_given: str, testimonial: str) -> tuple[str, str, str]:
    challenge = _trim_to_limit(challenge.strip(), MAX_SECTION_LENGTH)
    solution_given = _trim_to_limit(solution_given.strip(), MAX_SECTION_LENGTH)
    testimonial = _trim_to_limit(testimonial.strip(), MAX_SECTION_LENGTH) if testimonial else ""
    return challenge, solution_given, testimonial


def _parse_sections(raw: dict[str, Any], allow_testimonial: bool) -> tuple[str, str, str]:
    challenge = raw.get("challenge")
    solution_given = raw.get("solution_given")
    testimonial = raw.get("testimonial", "")

    if not isinstance(challenge, str) or not challenge.strip():
        raise HTTPException(status_code=502, detail="AI response missing valid 'challenge' section.")
    if not isinstance(solution_given, str) or not solution_given.strip():
        raise HTTPException(status_code=502, detail="AI response missing valid 'solution_given' section.")

    if not allow_testimonial:
        testimonial = ""
    elif not isinstance(testimonial, str):
        testimonial = str(testimonial).strip() if testimonial else ""
    else:
        testimonial = testimonial.strip()

    return challenge.strip(), solution_given.strip(), testimonial


def generate_story_sections(
    employee_prompt: str,
    attachment_context: str | None = None,
) -> GenerateResponse:
    """
    One employee prompt → Challenge, Solution Given, Testimonial (if needed), combined_story.

    When attachment_context is provided, extracted attachment text is merged into the
    AI input. With no attachments, behavior is identical to the original implementation.
    """
    employee_prompt = employee_prompt.strip()
    if len(employee_prompt) < MIN_PROMPT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"employee_prompt is too short (minimum {MIN_PROMPT_LENGTH} characters).",
        )

    has_attachments = bool(attachment_context and attachment_context.strip())

    # Backend decides whether testimonial is allowed — no fake testimonials
    if has_attachments:
        appreciation_source = f"{employee_prompt}\n{attachment_context}"
    else:
        appreciation_source = employee_prompt
    generate_testimonial = has_customer_appreciation(appreciation_source)

    try:
        client = get_ai_client()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if has_attachments:
        user_message = (
            "Read the employee case below and return professional JSON sections.\n\n"
            f"Employee prompt:\n{employee_prompt}\n\n"
            "Extracted attachment content:\n"
            f"{attachment_context.strip()}\n\n"
            "Use only facts from the employee prompt and attachment content above. "
            "Do not invent information.\n\n"
            f'generate_testimonial: {"yes" if generate_testimonial else "no"}'
        )
    else:
        user_message = (
            "Read the employee case below and return professional JSON sections.\n\n"
            f"Employee prompt:\n{employee_prompt}\n\n"
            f'generate_testimonial: {"yes" if generate_testimonial else "no"}'
        )

    try:
        completion = client.chat.completions.create(
            model=get_model(),
            temperature=0.7,
            max_tokens=3000,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": STORY_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail="AI rate limit reached. Try again shortly.") from exc
    except APIConnectionError as exc:
        raise HTTPException(status_code=503, detail="Could not reach AI service.") from exc
    except APIStatusError as exc:
        raise HTTPException(status_code=502, detail=f"AI API error: {exc.message}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(exc)}") from exc

    if not completion.choices or not completion.choices[0].message.content:
        raise HTTPException(status_code=502, detail="AI returned an empty response.")

    raw = _extract_json(completion.choices[0].message.content)
    challenge, solution_given, testimonial = _parse_sections(raw, generate_testimonial)
    challenge, solution_given, testimonial = _enforce_section_lengths(
        challenge, solution_given, testimonial
    )

    combined_story = combine_story_sections(challenge, solution_given, testimonial)

    return GenerateResponse(
        challenge=challenge,
        solution_given=solution_given,
        testimonial=testimonial,
        combined_story=combined_story,
        character_count=len(challenge) + len(solution_given) + len(testimonial),
    )
