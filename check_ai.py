"""Test: one employee prompt → sections + combined_story."""

import os
import sys

from dotenv import load_dotenv

from story_service import generate_story_sections

TEST_PROMPT = (
    "Customer had incorrect electricity billing because the meter number was linked to "
    "another connection. The issue remained unresolved for three months. I coordinated "
    "with the field team and CMG team, corrected the mapping within two days and informed "
    "the customer. The customer appreciated the prompt support."
)


def main() -> None:
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

    if not os.getenv("GROQ_API_KEY", "").strip() or "your" in os.getenv("GROQ_API_KEY", "").lower():
        print("FAIL: Add GROQ_API_KEY=gsk_... in .env")
        sys.exit(1)

    print("Testing one-prompt story generation...\n")

    try:
        result = generate_story_sections(TEST_PROMPT)
    except Exception as exc:
        print(f"FAIL: {exc}")
        sys.exit(1)

    print("--- CHALLENGE ---\n", result.challenge)
    print("\n--- SOLUTION GIVEN ---\n", result.solution_given)
    print("\n--- TESTIMONIAL ---\n", result.testimonial or "(empty — no appreciation in prompt)")
    print(f"\n--- character_count: {result.character_count} / 2000 ---")
    print("\n--- COMBINED STORY ---\n", result.combined_story)
    print("\nOK: AI is working.")


if __name__ == "__main__":
    main()
