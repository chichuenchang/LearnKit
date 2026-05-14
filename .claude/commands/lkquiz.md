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

Read `courses\{slug}\data\progress.json`: find all past `quiz_history` entries for units in scope. Build unified topic weight table from `weak_topics` and `score_pct` per session:
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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Quiz  ·  BIOL 201  ·  Unit 1: Cell Structure
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Multi-unit:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Quiz  ·  BIOL 201  ·  Units 1–3 (Midterm 1 scope)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Step 2 — Question loop (every question)

Print `──────────────────────────────────────────────────────────` before every question (visual reset after feedback or intro). Then the header line, blank line, bold question text, blank line, options, prompt:

MCQ:
```
──────────────────────────────────────────────────────────
Q 3 / 18   Cell Cycle Phases              ▓▓░░░░░░░░  17%   Score: 2/2

**What are the three stages of interphase?**

  `A)`  Prophase, Metaphase, Anaphase
  `B)`  G1, S phase, G2
  `C)`  Division, Rest, Synthesis
  `D)`  Interphase has only two stages

>
```

Short answer:
```
──────────────────────────────────────────────────────────
Q 5 / 18   Membrane Transport             ▓▓▓▓░░░░░░  33%   Score: 4/4

**Describe the difference between active and passive transport.**

>
```

**Header fields:**
- **Topic label**: topic this question tests — assigned at question generation time from the adaptive weight table (Step 0)
- **Progress bar**: 10-char `▓░` bar. `▓` count = `floor((answered / total) × 10)` where `answered` = questions already evaluated (Q1 → 0 answered, Q2 → 1, etc.)
- **Percentage**: `floor(answered / total × 100)%`
- **Score**: `correct / answered`. At Q1 (0 answered) → show `Score: —`

Evaluate immediately after user replies:

**Correct:**
```
✓  Correct.
   [one-sentence exam reinforcement]  [EXAM-CRITICAL]
```

**Incorrect:**
```
✗  Incorrect.
   [explanation ≤2 sentences]  [tag]
   ╌╌╌╌╌╌╌╌╌╌╌╌
   Correct: [correct answer]
```

**Skipped:**
```
→  Skipped.  [explanation ≤1 sentence]
   ╌╌╌╌╌╌╌╌╌╌╌╌
   Answer: [correct answer]
```

Any input (or blank) → next question.

---

### Step 3 — Results summary (after final Q or `end quiz`)

Single unit:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Quiz Complete  ·  BIOL 201  ·  Unit 1: Cell Structure
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Score    14 / 18   78%   ✓ PASS   (threshold: 70%)

  Correct   (14)  Q1  Q2  Q4  Q5  Q7  Q8  Q10–Q14  Q16  Q17
  Incorrect  (3)  Q3 cell cycle phases  ·  Q6 membrane transport  ·  Q9 ATP synthesis
  Skipped    (1)  Q18

  MCQ       12/13   92%
  Short ans   2/5   40%  ← needs work
```

Multi-unit — add per-unit breakdown after the score line:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Quiz Complete  ·  BIOL 201  ·  Units 1–3 (Midterm 1 scope)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Score    19 / 25   76%   ✓ PASS   (threshold: 70%)

  Unit 1 — Cell Structure    8/9   89%
  Unit 2 — Cell Cycle        6/9   67%  ← weak
  Unit 3 — Genetics          5/7   71%

  Correct   (19)  Q1  Q2  Q3 ...
  Incorrect  (5)  Q4 cell cycle phases  ·  Q8 enzyme kinetics ...
  Skipped    (1)  Q25

  MCQ       14/17   82%
  Short ans   5/8   63%  ← needs work
```

Early `end quiz` → append `(partial — ended at Q{N})` after the title line.

---

### Step 4 — Data updates (after results)

Use `data_writer.py`. Fire silently — single synchronous PowerShell call, no narration, no announcement:

```powershell
& $pythonExe $writerPath progress quiz `
    --savedata $savedataRoot --course {course_id} --unit {unit_slug} `
    --score-pct {unit_pct} --correct {n} --total {n} --incorrect {n} --skipped {n} `
    [--partial] [--adaptive] `
    [--weak-topics "topic1,topic2"] `
    [--mcq "correct/total"] [--sa "correct/total"] | Out-Null ;
& $pythonExe $writerPath log entry `
    --savedata $savedataRoot --course {course_id} `
    --entry "- [QUIZ] Unit N: {name} — {score}/{total} ({pct}%) | Weak: {topics or 'none'}" | Out-Null
```
Multi-unit entry format: `- [QUIZ] Units 1–3 (Midterm 1) — 19/25 (76%) | Weak: enzyme kinetics (Unit 2), DNA replication (Unit 3)`
