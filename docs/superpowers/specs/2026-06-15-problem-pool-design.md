# Problem Pool — Design Spec

**Date**: 2026-06-15
**Status**: Approved (design), pending implementation plan
**Project**: LearnKit (PTStudy)

---

## Goal

Each course gets structured **problem pool** holding actual problems from that course's past quizzes/exams. Pool used two ways at once:

1. **Served verbatim** — real past problems appear directly in quizzes.
2. **Read as style exemplars** — LearnKit studies pool style, generates fresh questions in *same style* to cover scope topics pool does **not** cover (gap-filling).

Mock quiz = verbatim pool problems + generated, style-matched gap-fillers.

---

## Design decisions (resolved during brainstorming)

| Decision | Choice |
|----------|--------|
| Mock behavior | Serve verbatim pool problems **and** generate fresh gap-fillers in same style for uncovered areas |
| Population | Auto-extract during `/lkingest` (quiz/exam/practice files) **plus** manual `/lkpool add` path |
| Quiz integration | **Augment existing `/lkquiz`** (no separate command); `mock` scope keyword = verbatim-heavy + full coverage |
| Storage | Per-course file `data\problem_pool.json` (one-file-per-concern, parallel to `course_structure.json` / `progress.json`) |

---

## 1 — Storage and schema

New per-course file: `savedata\courses\{slug}\data\problem_pool.json`.

```json
{
  "course": "PTHER 350A",
  "course_id": "pther_350a",
  "last_updated": "2026-06-15T10:00:00",
  "problems": [
    {
      "problem_id": "prob_pther_350a_001",
      "unit_id": "week_03",
      "unit_slug": "week_03_hip_joint_gluteal_region",
      "topic": "Nerves of gluteal region",
      "question_type": "mcq",
      "question": "Which nerve innervates gluteus medius?",
      "options": ["Superior gluteal nerve", "Inferior gluteal nerve", "Sciatic nerve", "Femoral nerve"],
      "answer": "Superior gluteal nerve",
      "rationale": "Superior gluteal nerve supplies medius, minimus, TFL.",
      "tags": ["EXAM-CRITICAL"],
      "source": "Midterm 1 2025",
      "source_file": "source_midterm1.pdf",
      "source_type": "past_exam",
      "verbatim": true,
      "date_added": "2026-06-15"
    }
  ]
}
```

### Field reference

| Field | Meaning |
|-------|---------|
| `problem_id` | `prob_{course_id}_{NNN}`, zero-padded 3 digits, incremented from current max in this course's pool |
| `unit_id` | Primary unit (matches `course_structure.json` `units[].unit_id`); `null` if unmappable |
| `unit_slug` | Matching `units[].slug`; `null` if unmappable |
| `topic` | Topic label — **same vocabulary** as `progress.json` `weak_topics`, so adaptive weighting and coverage maps line up |
| `question_type` | `mcq` \| `short_answer` \| `matching` \| `labeling` \| `true_false` \| `essay` |
| `options` | Array of choice strings for `mcq`; `[]` for all other types |
| `answer` | Correct answer (string) |
| `rationale` | Optional, ≤ 1–2 sentences |
| `tags` | Section 1 tags, e.g. `["EXAM-CRITICAL"]` |
| `source` | Human-readable source label, e.g. `"Midterm 1 2025"` |
| `source_file` | Ingested source filename, or `"manual"` |
| `source_type` | `past_exam` \| `practice_quiz` \| `exam_review` \| `manual` |
| `verbatim` | `true` = exact past wording (servable as-is); `false` = reconstructed/manual |
| `date_added` | ISO date |

**Default empty file**: `{"course": null, "course_id": null, "last_updated": null, "problems": []}`

---

## 2 — Population

### Auto (inside `/lkingest`)

- Add new file type to classifier: **`past_exam`** — matches "midterm" / "final" / "exam" together with discrete question structure (distinct from `exam_review`, prose study guide).
- For file types in `{practice_quiz, exam_review, past_exam}`: after study notes written (unchanged), attempt to **extract discrete Q+A pairs** from extracted text.
  - Map each problem to unit via keyword overlap (reuse existing unit-identification logic). Unmappable → `unit_id: null`.
  - Assign `topic` label drawn from unit's topics / weak-topic vocabulary.
  - Set `source_type` from file classification, `verbatim: true`, `source_file` = ingested filename, `source` = inferred label (e.g. "Practice Quiz — Week 3").
  - Batch-write all extracted problems to pool in one `pool add` call.
- **No discrete Q+A** found (prose study guide) → skip pool — notes only.
- All extracted content from ingested file only (Behavioral Rule 9 — no hallucinated subject matter).

### Manual (`/lkpool add`)

- User pastes one problem (question, type, options, answer, optional topic/unit).
- Written as single-element batch. `source_type: manual`, `verbatim: false`, `source_file: "manual"`.

### Dedup

- Before appending, skip any problem whose **normalized** question text (lowercased, whitespace-collapsed) already exists in this course's pool.
- Report `"N added, M duplicates skipped"`.

---

## 3 — `data_writer.py` subcommands

All structured writes go through `data_writer.py` (Behavioral Rule 15). Two new subcommands under new `pool` group.

### `pool add`

- **Required flags**: `--savedata`, `--course` (slug).
- **Input**: **JSON array of problem objects read from stdin** (mirrors existing `notes write` stdin pattern). One call writes many problems — midterm of 30+ problems = single invocation.
- Behavior: load (or default) `problem_pool.json`; for each incoming problem — validate `question_type` against allowed set; normalize-dedup against existing questions; assign `problem_id` = `prob_{course}_{NNN}` (increment from current max); default missing optional fields (`options: []`, `tags: []`, `rationale: null`, `verbatim` as provided or `false`); set `date_added`. Append survivors, bump `last_updated`, save.
- **Output**: `{"success": true, "added": N, "skipped": M, "ids": [...]}`.

Example invocation (batch from agent):

```powershell
$problemsJson = @'
[ { "question": "...", "answer": "...", "question_type": "mcq", "options": ["...","..."], "unit_id": "week_03", "topic": "...", "source": "Midterm 1 2025", "source_file": "source_midterm1.pdf", "source_type": "past_exam", "verbatim": true } ]
'@
$result = ($problemsJson | & $pythonExe $writerPath pool add `
    --savedata $savedataRoot --course "pther_350a") | ConvertFrom-Json
if (-not $result.success) { Write-Host "Pool write failed: $($result.error)" }
```

### `pool remove`

- **Required flags**: `--savedata`, `--course`, `--problem-id`.
- Deletes matching problem; bumps `last_updated`. Not found → `{"success": false, "error": "..."}`.
- **Output**: `{"success": true, "removed": "<id>"}`.

### Subcommand reference additions (for `lkscripts.md`)

| Subcommand | Required flags | Optional flags |
|------------|---------------|----------------|
| `pool add` | `--savedata --course` | — (problem objects read from stdin as JSON array) |
| `pool remove` | `--savedata --course --problem-id` | — |

---

## 4 — `/lkpool` command

New file `.claude/commands/lkpool.md` (plain markdown, same convention as existing `lk*` commands; first line is base-context pointer line).

Variants:

- `/lkpool {course}` — summary: total problem count, breakdown by unit and by `source_type`, and **coverage map** (which course topics have ≥1 pool problem vs none).
- `/lkpool add {course}` — interactive: prompt for question, type, options (if mcq), answer, optional topic/unit; build one-element batch; call `pool add`.
- `/lkpool list {course} [unit]` — table of problems: `problem_id`, `question_type`, `topic`, `source`. Optional unit filter.
- `/lkpool remove {problem_id}` — resolve course from id prefix, confirm, call `pool remove`.

Rules: multiple active courses + none specified → ask (Behavioral Rule 2). Never mix courses (Rule 1). Log every mutation (Rule 14).

---

## 5 — `/lkquiz` integration

Augment **Step 0 (pre-quiz setup)** of `lkquiz.md`. No new quiz command.

- Also read `problem_pool.json` for units in scope.
- **Coverage map** — split scope topics into those with pool problems and those without.
- **Verbatim pool problems** — pull problems where `unit_id ∈ scope`. Count toward question total. Prioritize `EXAM-CRITICAL` tags and topics tied to next upcoming exam.
- **Generated gap-fillers** — for scope topics **not** in pool, generate fresh questions matching pool's observed style (question-type mix, phrasing, difficulty). Existing adaptive-weight table (from `progress.json` quiz history) still applies on top.
- **Format mirror** — when pool has problems for scope, derive MCQ / short-answer ratio from pool (overrides current default ~70/30).
- **Mix policy**:
  - Normal scope → blend; cap verbatim share so user still gets fresh practice.
  - `mock` keyword (new scope token, e.g. `/lkquiz pther_350a exam_1 mock`) → verbatim-heavy, ensure every exam topic covered (verbatim where available, generated otherwise).
- **Empty pool** → behavior identical to today (materials-only).

Scope grammar in `lkquiz.md` gains `mock` token. Step 4 log entry notes `(mock)` or `(pool-augmented)` when pool contributed.

---

## 6 — Documentation updates

| File | Change |
|------|--------|
| `.claude/commands/lkschemas.md` | Add `problem_pool.json` schema section |
| `CLAUDE.md` | Section 2 per-course data list (+`problem_pool.json`); Section 6 (+`/lkpool` entry); Section 8 (+`prob_{course_id}_{NNN}` naming) |
| `.claude/commands/lkscripts.md` | Add `pool add` / `pool remove` to subcommand reference |
| `.claude/commands/lkingest.md` | Add `past_exam` file type; add problem-extraction step for quiz/exam/practice files |
| `.claude/commands/lkquiz.md` | Add pool sourcing to Step 0; add `mock` scope token |
| `.claude/commands/lkpool.md` | **New** command file |

---

## Constraints honored

- **Rule 5** (quizzes materials-only) — pool problems ARE ingested materials; no web content.
- **Rule 9** (no hallucinated subject matter) — extraction strictly from ingested files; manual adds user-supplied.
- **Rule 15** (writes via `data_writer.py`) — new `pool add` / `pool remove` subcommands; no direct JSON writes.
- **Rule 1 / 2** (never mix or silently pick a course) — `/lkpool` asks when ambiguous.
- **Rule 14** (log every action) — pool mutations logged.

---

## Out of scope (YAGNI)

- No cross-course shared pools.
- No difficulty scoring model beyond mirroring observed style.
- No editing existing problem in place (remove + re-add covers it).
- No spaced-repetition scheduling on individual problems.
