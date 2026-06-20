# Unified `/lkquiz` + Removal of Progress Feature — Design

**Date**: 2026-06-19
**Scope**: Two intertwined changes to LearnKit, both touching the quiz path.

---

## Change A — Unify image quiz into `/lkquiz` (auto-adapting)

### Goal
One quiz command. No `--html` flag, no separate `/lkimage quiz`. `/lkquiz` decides on its
own whether to include image-based problems based on how image-rich the scope's materials are.

### Behavior
- `/lkquiz {course} {scope}` — no image flags.
- Compute an **image proportion** for the scope, then an image-problem count.
- **0 image problems** → existing interactive **terminal** loop (text MCQ), unchanged.
- **>0 image problems** → render the **entire quiz** (text + image MCQs interleaved) as **one
  self-contained HTML page** via `image_quiz.py`, opened in browser, scored client-side.

### Image proportion
- Optional field `image_quiz_ratio` (float 0–1) in `course_structure.json` (per course).
  `pther_350a` → `0.20`.
- Field absent → agent estimates from scope image-richness (eligible image items ÷ material
  volume), clamped to ≤ 0.40.
- No eligible image items → ratio 0 → terminal text quiz.

### Image problem sources (blended)
- `image_bank.json` targets with `label_bbox != null` whose `unit_id` ∈ scope →
  "name the highlighted structure" MCQ (`target_bbox` = `label_bbox`, masked).
- `problem_pool.json` problems with `figure != null` whose `unit_id` ∈ scope →
  verbatim figure MCQ (`crop_bbox` = `figure.bbox`, unmasked, `stem`/`options` verbatim).
- MCQ-only for the HTML page (skip non-mcq pool problems).

### Removals
- `/lkquiz`: drop `--html`/`images` keyword and Step 2b special-case.
- `/lkimage`: remove the `quiz` subcommand. Keep summary / review / `remove`.
- `problem_pool` figure problems remain as data — served via the unified flow, not a flag.

### `image_quiz.py` change (code)
- Current: every question REQUIRES a valid `image_path`; image-less questions are skipped
  (`scripts/image_quiz.py:126-133`).
- New: support **image-less cards** (pure text MCQ) — a question with no `image_path` renders
  a card with no `<img>` element, options + scoring identical. Keeps single-file/offline output.
- Add a regression test in `scripts/tests/test_image_quiz.py` covering a mixed spec
  (one image question + one text-only question → both render, total = 2).

---

## Change B — Remove the progress feature entirely

The progress feature (`progress.json`, `/lkprogress`, history-based adaptive weighting,
per-unit status / `materials_ingested` tracking) is removed. Quizzes become **stateless**:
selection driven by materials + pool only, no learning from past attempts.

**KEEP** the in-quiz visual progress bar in the question header (`answered / total`) — it is
unrelated to `progress.json`.

### Code — `scripts/data_writer.py`
Remove:
- `progress quiz` and `progress ingest` subcommands (parser + dispatch).
- `cmd_progress_quiz`, `cmd_progress_ingest`, `progress_path`, `progress_default`.
- `STATUS_PROGRESSION` and any status-merge helper used only by progress.
- Module docstring lines describing the two subcommands.

Verify the script still parses (`--help`) and all other subcommands work after removal.

### Docs — scrub all progress references
- **`lkprogress.md`** — delete file entirely.
- **`CLAUDE.md`** — remove `/lkprogress` from §6; remove `data\progress.json` from §2 per-course
  data list; remove Rule 10 ("Immediate progress updates"); renumber following rules; scrub any
  startup/§ references to progress.json.
- **`lkquiz.md`** — remove the `progress.json` / `quiz_history` adaptive-weighting block in
  Step 0 (replace with stateless selection: even spread across scope topics + pool priority for
  `EXAM-CRITICAL` and next-exam-linked topics); remove the `progress quiz` write in Step 4 (keep
  the `log entry` write). Also apply Change A here.
- **`lkschemas.md`** — delete the `progress.json` schema section; add `image_quiz_ratio` (float,
  default `null`) to the `course_structure.json` schema.
- **`lkingest.md`** — remove the `progress ingest` call and the "Initialize progress.json" step.
- **`lkscripts.md`** — remove the two `progress` rows from the `data_writer.py` flag table, the
  `progress quiz` PowerShell example, and the `progress` mention in the `--course` note.
- **`lksave.md`** — remove `progress.json` rows/lines from the reconcile table and examples.
- **`lkcourse.md`** — stop creating `progress.json` in the course skeleton; drop the "progress"
  column from `/lkcourse list`.
- **`lkexport.md`** — drop `progress` from the exported-files note.
- **`lksetup.md`** — reword line 63 ("back up your progress") to "back up your data".
- **`lkimage.md`** — remove the `quiz` subcommand (Change A); the `progress.json` mention there
  disappears with it.
- **`README.md`** — remove `/lkprogress` row, "tracks progress" / "adaptive quizzes" wording,
  and progress/quiz-history mentions in the directory + restore sections.

### Out of scope
- Historical design docs under `docs/superpowers/**` — left as-is (records).
- `savedata/` — not edited here, EXCEPT setting `pther_350a` `image_quiz_ratio: 0.20`
  (confirmed separately as a savedata write).

---

## Verification
1. `grep -ri progress` over tracked non-`docs/superpowers`, non-`savedata` files → only the
   in-quiz visual "progress bar" header reference remains.
2. `python scripts/data_writer.py --help` parses; a smoke `pool add` / `log entry` still works.
3. `pytest scripts/tests/test_image_quiz.py` passes incl. new mixed-spec test.
4. No doc references `--html`, `images` keyword, `/lkimage quiz`, or `/lkprogress`.
