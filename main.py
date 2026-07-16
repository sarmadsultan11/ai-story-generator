"""
AI Story Generator — FastAPI Backend

Phase 1: POST /generate — employee notes → professional sections + combined_story
Phase 2: POST /evaluate — jury AI-assisted evaluation (unchanged)
"""

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from evaluation_router import router as evaluation_router
from story_router import router as story_router

load_dotenv()

app = FastAPI(
    title="AI Story Generator",
    description=(
        "Phase 1: POST /generate — challenge_input, solution_input, optional testimonial_input "
        "→ professional sections + combined_story. "
        "Phase 2: POST /evaluate — jury evaluation of combined_story (unchanged)."
    ),
    version="3.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phase 1 — structured story generation
app.include_router(story_router)

# Phase 2 — jury evaluation (unchanged)
app.include_router(evaluation_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "AI Story Generator is running.",
        "phase_1": "POST /generate — one employee_prompt → sections + combined_story",
        "phase_2": "POST /evaluate — combined saved story → jury scores",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
