Base context (path variables, behavioral rules) loaded from CLAUDE.md. Data schemas in lkschemas.md. Python script protocol and data_writer.py reference in lkscripts.md. Log entry format spec in lklogging.md.

## `/lkpool` — Problem pool management

Manages each course's `data\problem_pool.json` — the bank of past quiz/exam problems that `/lkquiz` serves verbatim and mines for style. All writes go through `data_writer.py` `pool add` / `pool remove` (Rule 15). Multiple active courses + none specified → ask (Rule 2). Never mix courses (Rule 1). Log every mutation (Rule 14).

### `/lkpool {course}` — summary
Read `course_structure.json` and `problem_pool.json` (missing pool file → treat as empty, 0 problems). Print:
- Total problem count.
- Breakdown by unit (`display_name` → count) and by `source_type`.
- **Coverage map**: for each unit's `topics`, mark `✓` if ≥1 pool problem has that `topic` (or maps to that unit), `—` if none. This shows where `/lkquiz` will generate gap-fillers vs serve verbatim.

```
PTHER 350A — Problem Pool
Total: 47 problems   (past_exam 31 · practice_quiz 12 · manual 4)
──────────────────────────────────────────────
  Week 1: Vertebral Column      18   ✓ covered
  Week 2: Bony Pelvis            9   ◑ partial (Sacral plexus: —)
  Week 3: Hip Joint             20   ✓ covered
  Week 4: Thigh & Knee           0   — none (all generated)
  Week 5: Leg & Ankle            0   — none (all generated)
```

### `/lkpool add {course}` — manual add
Prompt for: question text, `question_type` (mcq/short_answer/matching/labeling/true_false/essay), options (if mcq), answer, optional topic and unit. Build a one-element JSON array, pipe to `pool add`:

```powershell
$problemsJson = @'
[ { "question": "...", "answer": "...", "question_type": "short_answer", "topic": "...", "unit_id": "week_03", "source": "Instructor note", "verbatim": false } ]
'@
$r = ($problemsJson | & $pythonExe $writerPath pool add --savedata $savedataRoot --course "{slug}") | ConvertFrom-Json
if (-not $r.success) { Write-Host "Failed: $($r.error)" }
```
`source_type` defaults to `manual`, `verbatim` to false. Confirm: `"Added {id} to {course_code} pool."` Then log: `[POOL] Added 1 problem (manual) -> {unit or 'unmapped'}`.

### `/lkpool list {course} [unit]` — list
Read `problem_pool.json`. Print a table: `problem_id`, `question_type`, `topic`, `source`. Optional unit filter (match `unit_id` or `unit_slug`). Truncate question preview to ~60 chars if shown.

### `/lkpool remove {problem_id}` — delete
Derive course slug from the id: strip the `prob_` prefix and the trailing `_{NNN}` segment (NNN is always the 3-digit final segment) → remainder is the course slug. Show the problem, confirm, then:

```powershell
$r = (& $pythonExe $writerPath pool remove --savedata $savedataRoot --course "{slug}" --problem-id "{problem_id}") | ConvertFrom-Json
if (-not $r.success) { Write-Host "Failed: $($r.error)" }
```
Confirm: `"Removed {id}."` Log: `[POOL] Removed {id}`.
