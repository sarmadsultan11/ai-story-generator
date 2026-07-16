# AI Story Generator

## Phase 1

Employee gives **one prompt** → AI returns:

- `challenge`
- `solution_given`
- `testimonial` (only if appreciation mentioned in prompt, else `""`)
- `combined_story` (for jury)
- `character_count` (max 2000 total)

## Phase 2

`POST /evaluate` with `combined_story` — unchanged.

## Run

```cmd
cd /d "C:\Users\saras\OneDrive\Desktop\internship project"
venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
127.0.0.1/docs
```

Test: `venv\Scripts\python.exe check_ai.py`
