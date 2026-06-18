Base context (path variables, behavioral rules) from CLAUDE.md. Data schemas in lkschemas.md. Python script protocol + data_writer.py reference in lkscripts.md. Log entry format in lklogging.md.

## `/lkpool` — Problem pool management

Manages each course's `data\problem_pool.json` — bank of past quiz/exam problems `/lkquiz` serves verbatim + mines for style. All writes through `data_writer.py` `pool add` / `pool remove` (Rule 15). Multiple active courses + none specified → ask (Rule 2). Never mix courses (Rule 1). Log every mutation (Rule 14).

### `/lkpool {course}` — summary
Read `course_structure.json` + `problem_pool.json` (missing pool file → empty, 0 problems). Print:
- Total problem count.
- Breakdown by unit (`display_name` → count) + by `source_type`.
- **Coverage map**: for each unit's `topics`, `✓` if ≥1 pool problem has that `topic` (or maps to that unit), `—` if none. Shows where `/lkquiz` generates gap-fillers vs serves verbatim.

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
Prompt for: question text, `question_type` (mcq/short_answer/matching/labeling/true_false/essay), options (if mcq), answer, optional topic + unit. Build one-element JSON array, pipe to `pool add`:

```powershell
$problemsJson = @'
[ { "question": "...", "answer": "...", "question_type": "short_answer", "topic": "...", "unit_id": "week_03", "source": "Instructor note", "verbatim": false } ]
'@
$r = ($problemsJson | & $pythonExe $writerPath pool add --savedata $savedataRoot --course "{slug}") | ConvertFrom-Json
if (-not $r.success) { Write-Host "Failed: $($r.error)" }
```
`source_type` defaults `manual`, `verbatim` false. Confirm: `"Added {id} to {course_code} pool."` Log: `[POOL] Added 1 problem (manual) -> {unit or 'unmapped'}`. Image-based problem → include `figure` object (`image_path` to persistent PNG under `materials\{unit}\images`, optional `bbox`/`caption`) — see lkschemas.md; image problems usually captured during `/lkingest` (step 7d), not added manually.

### `/lkpool list {course} [unit]` — list
Read `problem_pool.json`. Print table: `problem_id`, `question_type`, `topic`, `source`. Mark rows with non-null `figure` with `[img]` tag (studied via `/lkquiz --html`). Optional unit filter (match `unit_id` or `unit_slug`). Truncate question preview to ~60 chars if shown.

### `/lkpool remove {problem_id}` — delete
Derive course slug from id: strip `prob_` prefix + trailing `_{NNN}` segment (NNN always 3-digit final segment) → remainder is course slug. Show problem, confirm, then:

```powershell
$r = (& $pythonExe $writerPath pool remove --savedata $savedataRoot --course "{slug}" --problem-id "{problem_id}") | ConvertFrom-Json
if (-not $r.success) { Write-Host "Failed: $($r.error)" }
```
Confirm: `"Removed {id}."` Log: `[POOL] Removed {id}`.
