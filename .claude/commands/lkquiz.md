Base context (path variables, behavioral rules, Section 1 tagging) loaded from CLAUDE.md. Data schemas in lkschemas.md. Python script protocol and data_writer.py reference in lkscripts.md. Log entry format spec in lklogging.md.

## `/lkquiz {course_code} {scope}` — Interactive adaptive quiz

Multiple active + no course → ask. Quiz: **interactive — one question at a time**.

**`{scope}` accepts:**
- `unit_01` — single unit
- `unit_01-unit_03` — contiguous range (inclusive)
- `unit_01,unit_03,unit_05` — explicit list
- `exam_1` — all units covered by exam (resolved from `course_structure.json` `exams[].units_covered`)
- `exam_1 mock` (or any scope + `mock`) — mock mode: verbatim-heavy, every covered topic represented; preserves real exam format (may include short answer)
- `written` (or any scope + `written`) — include short-answer / manual-input questions. **Without flag, quiz all multiple-choice.**
- `--html` (or `images`) — render image-based pool problems as self-contained HTML page via `image_quiz.py` (Step 2b) instead of terminal loop. **Required for figure-bearing problems** — terminal can't show images.

**Resolving exam scope**: Look up by `exam_id` or fuzzy title. Use `units_covered` as unit list. Not found: `"No exam 'exam_1' in {course_code}. Available: [list]"`. Show resolved scope using `unit_label` from `course_structure.json` pluralized: `"Units 1–3 (Exam 1 scope)"`, `"Weeks 1–3 (Exam 1 scope)"`, `"Chapters 1–3 (Exam 1 scope)"`, etc.

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
- `short_answer` accuracy < 60% → increase short-answer proportion (applies only when `written`/`mock` active; default quiz no short answer)

**Problem pool sourcing**: Read `courses\{slug}\data\problem_pool.json`. For problems whose `unit_id` ∈ scope:
- **Coverage map** — split scope topics into pool-covered vs not.
- **Verbatim problems** — serve pool problems directly (count toward question total). Prioritize `EXAM-CRITICAL` tags and topics tied to next upcoming exam. **Default (MCQ-only)**: serve only `mcq`-type pool problems; skip non-mcq types unless `written`/`mock` active.
- **Generated gap-fillers** — for scope topics with no pool problem, generate fresh questions matching pool's observed style (question-type mix, phrasing, difficulty). Adaptive weights still apply.
- **Format mirror** — only when `written`/`mock` active: derive MCQ/short-answer ratio from pool. Default (no flag) → all MCQ regardless of pool ratio.
- **Mix** — normal scope: blend, capping verbatim share so fresh practice remains. `mock` keyword: verbatim-heavy, ensure every covered topic appears (verbatim where available, generated otherwise).
- **Figure-bearing problems** — pool problems with non-null `figure` can't run in terminal loop (no inline images). Served only under `--html` (Step 2b). Default terminal quiz skips them; if scope contains figure-problems and `--html` not passed, note once: `"{N} image-based problem(s) in scope — re-run with --html to include them."`
- **Empty or absent pool** → behavior unchanged (materials-only).

**Question count:**
- Single unit: 15–20
- Multiple units: 8–12 per unit, cap 40. Exam ≤ 14 days → scale up.

**Multi-unit material pooling**: Combine all `.md` from every unit in scope + `multi_unit\`. Distribute proportionally by volume, apply adaptive weights on top. Every unit gets ≥1 question.

**Format**: **Default — all multiple-choice (100% MCQ)**, 4 options each. Short-answer / manual-input questions appear only when `written` scope keyword passed, or in `mock` mode (exam simulation preserves real format). With `written`: mirror ingested practice quiz if available, else ~70% MCQ / ~30% short answer.

---

### Step 1 — Quiz intro (print before Q1)

Single unit — use `display_name` from `course_structure.json`:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Quiz  ·  BIOL 201  ·  {display_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Multi-unit — pluralize `unit_label` from `course_structure.json → unit_label` (e.g. "Unit" → "Units", "Week" → "Weeks", "Chapter" → "Chapters"):
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Quiz  ·  BIOL 201  ·  {unit_label}s 1–3 (Midterm 1 scope)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Step 2 — Question loop (every question)

Print `──────────────────────────────────────────────────────────` before every question (visual reset after feedback or intro). Then header line, blank line, bold question text, blank line, options, prompt:

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
- **Topic label**: topic this question tests — assigned at question generation time from adaptive weight table (Step 0)
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

### Step 2b — Image-based problems (`--html` only)

Pool problems in scope with non-null `figure` → build ONE `image_quiz.py` spec (fields in lkscripts.md): `crop_bbox` = `figure.bbox`, **no** `target_bbox` (unmasked), `stem`/`options` verbatim, `answer_index` = index of `answer` in `options`. Skip non-mcq (HTML quiz MCQ-only). Adaptive weighting (Step 0) still applies.

Write page to `courses\{slug}\materials\{unit_slug}\quiz_images_{scope}_{YYYYMMDD}.html` (multi-unit → first unit in scope), then `Start-Process` it. Page scores client-side — **no `progress.json` write** for HTML portion (same as `/lkimage quiz`). Log per course: `- [QUIZ] Image quiz ({scope}) — {N} figure problem(s) -> HTML`. When terminal portion also ran, this is in addition to Step 4 write.

---

### Step 3 — Results summary (after final Q or `end quiz`)

Print one line, then proceed to Step 4:

```
Done — 14/18  78%  ✓ PASS
```

FAIL:
```
Done — 9/18  50%  ✗ FAIL
```

If 0 questions answered → print nothing.

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
    --entry "- [QUIZ] {display_name} — {score}/{total} ({pct}%) | Weak: {topics or 'none'}" | Out-Null
```
Multi-unit entry format: `- [QUIZ] {Units/Weeks} 1–3 (Midterm 1) — 19/25 (76%) | Weak: enzyme kinetics ({display_name_2}), DNA replication ({display_name_3})`

When pool problems served, append ` (mock)` (mock scope) or ` (pool-augmented)` (normal scope) to `{display_name}` segment of log entry, e.g. `- [QUIZ] {display_name} (pool-augmented) — {score}/{total} ({pct}%) | Weak: ...`.
