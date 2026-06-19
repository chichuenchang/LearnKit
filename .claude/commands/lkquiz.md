Base context (path variables, behavioral rules, Section 1 tagging) loaded from CLAUDE.md. Data schemas in lkschemas.md. Python script protocol and data_writer.py reference in lkscripts.md. Log entry format spec in lklogging.md.

## `/lkquiz {course_code} {scope}` — Interactive quiz

Multiple active + no course → ask. Quiz is **stateless** — selection driven by materials + problem pool only, no history-based weighting.

The command **auto-adapts to how image-rich the scope is**. Text-only materials → interactive terminal quiz. Image-rich materials → a share of image-based questions, and the whole quiz renders as one self-contained HTML page (terminal can't show images). No flags decide this — it is computed in Step 0.

**`{scope}` accepts:**
- `unit_01` — single unit
- `unit_01-unit_03` — contiguous range (inclusive)
- `unit_01,unit_03,unit_05` — explicit list
- `exam_1` — all units covered by exam (resolved from `course_structure.json` `exams[].units_covered`)
- `exam_1 mock` (or any scope + `mock`) — mock mode: verbatim-heavy, every covered topic represented; preserves real exam format (may include short answer)
- `written` (or any scope + `written`) — include short-answer / manual-input questions. **Without flag, quiz all multiple-choice.**

**Resolving exam scope**: Look up by `exam_id` or fuzzy title. Use `units_covered` as unit list. Not found: `"No exam 'exam_1' in {course_code}. Available: [list]"`. Show resolved scope using `unit_label` from `course_structure.json` pluralized: `"Units 1–3 (Exam 1 scope)"`, `"Weeks 1–3 (Exam 1 scope)"`, `"Chapters 1–3 (Exam 1 scope)"`, etc.

No scope → ask.

---

### Step 0 — Pre-quiz setup (silent, before Q1)

Read `courses\{slug}\misc.md`: scope changes or format notes → surface: `"Note from misc.md: [entry]"`.

**Topic selection (stateless):**
- Spread questions across the scope's topics (from `course_structure.json` + ingested notes), every topic represented.
- Prioritize `EXAM-CRITICAL` tagged content and topics tied to the next upcoming exam — always ≥1 question per topic linked to that exam.
- No topic > 40% of total questions.

**Problem pool sourcing**: Read `courses\{slug}\data\problem_pool.json`. For problems whose `unit_id` ∈ scope:
- **Coverage map** — split scope topics into pool-covered vs not.
- **Verbatim problems** — serve pool problems directly (count toward question total). Prioritize `EXAM-CRITICAL` tags and topics tied to next upcoming exam. **Default (MCQ-only)**: serve only `mcq`-type pool problems; skip non-mcq types unless `written`/`mock` active.
- **Generated gap-fillers** — for scope topics with no pool problem, generate fresh questions matching pool's observed style (question-type mix, phrasing, difficulty).
- **Format mirror** — only when `written`/`mock` active: derive MCQ/short-answer ratio from pool. Default (no flag) → all MCQ regardless of pool ratio.
- **Mix** — normal scope: blend, capping verbatim share so fresh practice remains. `mock` keyword: verbatim-heavy, ensure every covered topic appears (verbatim where available, generated otherwise).
- **Empty or absent pool** → behavior unchanged (materials-only).

**Image proportion** (decides terminal vs HTML output):
- **Eligible image items** = `image_bank.json` targets with `label_bbox != null` whose `unit_id` ∈ scope (name-the-structure) **+** `problem_pool.json` problems with `figure != null` whose `unit_id` ∈ scope (figure problems).
- **Ratio** = `course_structure.json → image_quiz_ratio` if set (e.g. `pther_350a` = 0.20). If `null`, estimate from scope image-richness (share of scope material that is figure-heavy), clamp ≤ 0.40. No eligible items → ratio 0.
- **Image count** = `round(ratio × total questions)`, capped by the number of eligible items.
- Select image questions blended across both sources, applying the same `EXAM-CRITICAL` / next-exam priority. Remaining questions are text.
- Image questions are **MCQ-only** (HTML page can't take typed answers). Under `written`/`mock`, short-answer items stay in the text portion; if the quiz goes to HTML (see Step 1b) the short-answer items are dropped with a one-line note: `"{N} short-answer item(s) omitted — HTML quiz is MCQ-only."`

**Question count:**
- Single unit: 15–20
- Multiple units: 8–12 per unit, cap 40. Exam ≤ 14 days → scale up.

**Multi-unit material pooling**: Combine all `.md` from every unit in scope + `multi_unit\`. Distribute proportionally by volume. Every unit gets ≥1 question.

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

### Step 1b — Output mode

- **Image count = 0** → run the interactive terminal loop (Step 2).
- **Image count > 0** → render the **whole quiz** (text + image MCQs interleaved) as one self-contained HTML page (Step 2-HTML). Skip the terminal loop.

---

### Step 2 — Question loop (terminal, every question)

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
- **Topic label**: topic this question tests — assigned at question generation time (Step 0).
- **Progress bar**: 10-char `▓░` bar. `▓` count = `floor((answered / total) × 10)` where `answered` = questions already evaluated (Q1 → 0 answered, Q2 → 1, etc.). (This is an in-quiz visual aid, unrelated to any stored data.)
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

### Step 2-HTML — Image-inclusive quiz (when image count > 0)

Build ONE `image_quiz.py` spec (fields in lkscripts.md) holding **all** selected questions in order, then `Start-Process` the page. Per question:
- **Text MCQ** → omit `image_path`; set `stem`, `options`, `answer_index`. Renders as a text-only card.
- **Image-bank (name-the-structure)** → `image_path` = structure's image, `target_bbox` = its `label_bbox` (blanks + highlights the label), generated stem/options, `answer_index`.
- **Pool figure problem** → `image_path` = figure image, `crop_bbox` = `figure.bbox` (unmasked), `stem`/`options` verbatim, `answer_index` = index of `answer` in `options`.

MCQ-only. Write page to `courses\{slug}\quiz\quiz_{scope}_{YYYYMMDD}.html` (course-level `quiz\` dir; create if absent), then open it:
```powershell
$out = "{savedataRoot}\courses\{slug}\quiz\quiz_{scope}_{YYYYMMDD}.html"
$r = ($specJson | & $pythonExe (Join-Path $scriptsRoot "image_quiz.py") --out $out) | ConvertFrom-Json
if ($r.success) { Start-Process $r.html_path }
```
Page scores **client-side** — nothing is written back. Log per course (Step 4 log entry only): `- [QUIZ] {scope} — {N} Q ({img_n} image) -> HTML`.

---

### Step 3 — Results summary (terminal quiz only, after final Q or `end quiz`)

Print one line, then proceed to Step 4:

```
Done — 14/18  78%  ✓ PASS
```

FAIL:
```
Done — 9/18  50%  ✗ FAIL
```

If 0 questions answered → print nothing. (HTML quizzes score in the browser — no terminal summary.)

---

### Step 4 — Log entry (after results)

The only write. Fire silently — single synchronous PowerShell call, no narration:

```powershell
& $pythonExe $writerPath log entry `
    --savedata $savedataRoot --course {course_id} `
    --entry "- [QUIZ] {display_name} — {score}/{total} ({pct}%)" | Out-Null
```
Multi-unit entry format: `- [QUIZ] {Units/Weeks} 1–3 (Midterm 1) — 19/25 (76%)`.

When pool problems served, append ` (mock)` (mock scope) or ` (pool-augmented)` (normal scope) to the `{display_name}` segment, e.g. `- [QUIZ] {display_name} (pool-augmented) — {score}/{total} ({pct}%)`.

For an HTML quiz (Step 2-HTML) there is no terminal score — use the HTML log line from Step 2-HTML instead.
