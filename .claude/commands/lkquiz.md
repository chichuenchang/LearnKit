Base context (path variables, behavioral rules, Section 1 tagging) loaded from CLAUDE.md. Data schemas in lkschemas.md. Python script protocol and data_writer.py reference in lkscripts.md. Log entry format spec in lklogging.md.

## `/lkquiz {course_code} {scope}` — Interactive adaptive quiz

Multiple active + no course → ask. Quiz: **interactive — one question at a time**.

**`{scope}` accepts:**
- `unit_01` — single unit
- `unit_01-unit_03` — contiguous range (inclusive)
- `unit_01,unit_03,unit_05` — explicit list
- `exam_1` — all units covered by exam (resolved from `course_structure.json` `exams[].units_covered`)

**Resolving exam scope**: Look up by `exam_id` or fuzzy title. Use `units_covered` as unit list. Not found: `"No exam 'exam_1' in {course_code}. Available: [list]"`. Show resolved scope: `"Units 1–3 (Exam 1 scope)"`.

No scope → ask.

---

### Step 0 — Pre-quiz setup (silent, before Q1)

Read `courses\{slug}\misc.md`: scope changes or format notes → surface: `"Note from misc.md: [entry]"`.

Read `courses\{slug}\activity_log.md`: find all past `### [QUIZ]` blocks for units in scope. Build unified topic weight table:
- `miss_rate = total_misses / total_appearances` per topic
- Recency: last session ×1.5 | two ago ×1.2 | older ×1.0
- Weighted miss_rate > 0.5 → **HIGH**: 2–3× baseline questions
- Weighted miss_rate = 0 last 2 sessions → **LOW**: 1 review question max
- Never seen → **NEUTRAL**: baseline
- No topic > 40% of total questions
- Always ≥1 question per topic linked to next upcoming exam
- `short_answer` accuracy < 60% → increase short-answer proportion

**Question count:**
- Single unit: 15–20
- Multiple units: 8–12 per unit, cap 40. Exam ≤ 14 days → scale up.

**Multi-unit material pooling**: Combine all `.md` from every unit in scope + `multi_unit\`. Distribute proportionally by volume, apply adaptive weights on top. Every unit gets ≥1 question.

**Format**: Mirror ingested practice quiz if available. Default: ~70% MCQ, ~30% short answer.

---

### Step 1 — Quiz intro (print before Q1)

Single unit:
```
Quiz — BIOL 201 | Unit 1: Cell Structure | 18 questions
Adaptive: weighted toward cell cycle phases (missed 4/5 across 2 sessions), membrane transport (missed 3/4)
Format: 13 MCQ + 5 short answer
──────────────────────────────────────────────────────
Commands during quiz: 'hint' (one clue, one per question) | 'skip' | 'end quiz' (save partial)
```

Multi-unit:
```
Quiz — BIOL 201 | Units 1–3 (Midterm 1 scope) | 25 questions
Adaptive: weighted toward cell cycle phases ×1.8 (Unit 1), enzyme kinetics ×1.5 (Unit 2)
Format: 17 MCQ + 8 short answer  |  Unit 1: 9q  Unit 2: 9q  Unit 3: 7q
──────────────────────────────────────────────────────
Commands during quiz: 'hint' (one clue, one per question) | 'skip' | 'end quiz' (save partial)
```

No prior history for any unit → `"Adaptive: baseline distribution (no prior quiz data)"`.

---

### Step 2 — Question loop (every question)

```
[Q3/18] What are the three stages of interphase?
> _
```
MCQ → labelled options A–D. Short answer → blank prompt.

Evaluate immediately after user replies:
- **Correct**: `✓ Correct. [one-sentence exam reinforcement]  [EXAM-CRITICAL]`
- **Incorrect**: `✗ Incorrect. Answer: [correct]. [explanation ≤2 sentences]  [tag]`
- **Skipped**: `→ Skipped. Answer: [correct]. [explanation ≤1 sentence]`
- **`hint`**: one-sentence clue, no answer. Mark `(H)`. One hint per question. Already used → `"Already gave a hint for this one."` Re-prompt same question after hint.
- **Correct after hint**: counts ½ for topic weight (logged `✓(H)`)

Any input (or blank) → next question.

---

### Step 3 — Results summary (after final Q or `end quiz`)

Single unit:
```
────────────────────────────────────────────────────────
Quiz Complete — BIOL 201 | Unit 1: Cell Structure
Score: 14/18 (78%)  ✓ PASS  (threshold: 70%)

Correct   (14): Q1, Q2, Q4, Q5, Q7, Q8, Q10–Q14, Q16, Q17
Incorrect  (3): Q3 cell cycle phases | Q6 membrane transport | Q9 ATP synthesis
Skipped    (1): Q18

MCQ accuracy    : 12/13 (92%)
Short answer    : 2/5 (40%)  ← needs work

Persistent weak topics (missed in ≥2 sessions): cell cycle phases, membrane transport
New weak topics (first miss today): ATP synthesis pathway
────────────────────────────────────────────────────────
Next quiz will weight: cell cycle phases ×1.8 | membrane transport ×1.5 | ATP synthesis ×1.3
```

Multi-unit — add per-unit breakdown before weak topics:
```
────────────────────────────────────────────────────────
Quiz Complete — BIOL 201 | Units 1–3 (Midterm 1 scope)
Score: 19/25 (76%)  ✓ PASS  (threshold: 70%)

  Unit 1 — Cell Structure : 8/9  (89%)
  Unit 2 — Cell Cycle     : 6/9  (67%)  ← weak
  Unit 3 — Genetics       : 5/7  (71%)

MCQ accuracy    : 14/17 (82%)
Short answer    : 5/8  (63%)  ← needs work

Persistent weak topics: cell cycle phases (Unit 1), enzyme kinetics (Unit 2)
New weak topics: DNA replication steps (Unit 3)
────────────────────────────────────────────────────────
```

Early `end quiz` → append `(partial — ended at Q{N})` to header line.

---

### Step 4 — Data updates (after results)

Use `data_writer.py` for all writes. Run in this order:

**1. Per unit in scope — `progress quiz`** (one call per unit):
```powershell
$result = (& $pythonExe $writerPath progress quiz `
    --savedata $savedataRoot --course {course_id} --unit {unit_slug} `
    --score-pct {unit_pct} --correct {n} --total {n} --incorrect {n} --skipped {n} `
    [--partial] [--adaptive] `
    [--weak-topics "topic1,topic2"] `
    [--mcq "correct/total"] [--sa "correct/total"]) | ConvertFrom-Json
```
Script advances `status` to `quiz_passed` if unit score ≥ 70%, updates `weak_areas` and `confidence_level`.

**2. Recalculate index — `index update`**:
```powershell
$result = (& $pythonExe $writerPath index update `
    --savedata $savedataRoot --course {course_id}) | ConvertFrom-Json
```

**3. Global one-liner — `log entry`**:
```powershell
$result = (& $pythonExe $writerPath log entry `
    --savedata $savedataRoot --course {course_id} `
    --entry "- [QUIZ] {course_code} | {scope} — {score}/{total} ({pct}%) | Weak: {topics or 'none'}") | ConvertFrom-Json
```
Multi-unit entry format: `- [QUIZ] BIOL 201 | Units 1–3 (Midterm 1) — 19/25 (76%) | Weak: enzyme kinetics (Unit 2), DNA replication (Unit 3)`

**4. Rich per-course quiz block** — agent writes directly to `courses\{slug}\activity_log.md`. Read `lklogging.md` for format spec before writing. This is narrative markdown — not schema data, not routed through data_writer.py.
Header: `### [QUIZ] {YYYY-MM-DD} — Units 1–3 (Midterm 1 scope)` or `### [QUIZ] {YYYY-MM-DD} — Unit 1: Cell Structure`
