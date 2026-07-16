# Website Integration

## Phase 1 — One employee prompt → structured story

`POST /generate`

**Request**

```json
{
  "employee_prompt": "Customer had incorrect electricity billing because the meter was linked to another connection. Issue went on 3 months. I coordinated with field team and CMG, fixed mapping in 2 days, informed customer. Customer appreciated the prompt support."
}
```

**Response**

```json
{
  "challenge": "...",
  "solution_given": "...",
  "testimonial": "...",
  "combined_story": "Challenge:\n...\n\nSolution Given:\n...\n\nCustomer Testimonial:\n...",
  "character_count": 1520
}
```

**Testimonial rule**

- Generated **only** if `employee_prompt` mentions appreciation (thank, appreciated, gratitude, etc.)
- Otherwise `"testimonial": ""` and no Customer Testimonial in `combined_story`

---

## Phase 2 — Jury evaluation (unchanged)

`POST /evaluate`

```json
{
  "story": "<use combined_story from generate response>"
}
```

---

## Workflow

Employee → one prompt → `/generate` → save sections + `combined_story` → Jury → `/evaluate` with `combined_story`

---

## JavaScript example

```javascript
const gen = await fetch("http://YOUR-SERVER:8000/generate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ employee_prompt: employeeText }),
}).then((r) => r.json());

const evalRes = await fetch("http://YOUR-SERVER:8000/evaluate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ story: gen.combined_story }),
}).then((r) => r.json());
```
