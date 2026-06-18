# Problem Pool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each LearnKit course structured `problem_pool.json` of past quiz/exam problems. `/lkquiz` serves verbatim, uses as style exemplars to generate gap-filling questions.

**Architecture:** New per-course `data\problem_pool.json`. Written only through two new `data_writer.py` subcommands (`pool add` reads JSON array from stdin, `pool remove`). `/lkingest` auto-extracts problems; new `/lkpool` command manages manually; `/lkquiz` Step 0 reads pool to blend verbatim + generated questions, with new `mock` scope keyword.

**Tech Stack:** Python 3.11 stdlib (`argparse`, `json`, `pathlib`); `unittest` + `subprocess` for tests; Markdown command/skill files under `.claude/commands/`.

**Spec:** `docs/superpowers/specs/2026-06-15-problem-pool-design.md`

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `scripts/data_writer.py` | Add `pool add` / `pool remove` subcommands + helpers | Modify |
| `scripts/tests/test_pool.py` | Unittest suite for pool subcommands | Create |
| `.claude/commands/lkschemas.md` | Document `problem_pool.json` schema | Modify |
| `.claude/commands/lkscripts.md` | Document `pool` subcommands | Modify |
| `CLAUDE.md` | Section 2 data list, Section 6 `/lkpool`, Section 8 `prob_` naming | Modify |
| `.claude/commands/lkpool.md` | New `/lkpool` command spec | Create |
| `.claude/commands/lkingest.md` | `past_exam` file type + extraction step | Modify |
| `.claude/commands/lkquiz.md` | Pool sourcing in Step 0 + `mock` scope token | Modify |

Tasks 1–2 code (TDD). Tasks 3–8 documentation/spec edits, verified by read-back.

---

### Task 1: `pool add` subcommand

**Files:**
- Create: `scripts/tests/test_pool.py`
- Modify: `scripts/data_writer.py`

- [ ] **Step 1: Write failing test**

Create `scripts/tests/test_pool.py`:

```python
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = str(pathlib.Path(__file__).resolve().parents[1] / "data_writer.py")


def _run(args, stdin=None):
    proc = subprocess.run(
        [sys.executable, SCRIPT, *args],
        input=stdin, capture_output=True, text=True,
    )
    return json.loads(proc.stdout)


def add(savedata, course, problems):
    return _run(
        ["pool", "add", "--savedata", savedata, "--course", course],
        stdin=json.dumps(problems),
    )


def remove(savedata, course, pid):
    return _run(
        ["pool", "remove", "--savedata", savedata, "--course", course,
         "--problem-id", pid],
    )


def read_pool(savedata, course):
    p = (pathlib.Path(savedata) / "courses" / course / "data"
         / "problem_pool.json")
    return json.loads(p.read_text(encoding="utf-8"))


MCQ = {
    "question": "Which nerve innervates gluteus medius?",
    "answer": "Superior gluteal nerve",
    "question_type": "mcq",
    "options": ["Superior gluteal nerve", "Sciatic nerve"],
    "unit_id": "week_03",
    "topic": "Nerves of gluteal region",
    "source": "Midterm 1 2025",
    "source_file": "source_midterm1.pdf",
    "source_type": "past_exam",
    "verbatim": True,
}


class PoolAddTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sd = self._tmp.name
        self.course = "test_101"

    def tearDown(self):
        self._tmp.cleanup()

    def test_add_single(self):
        res = add(self.sd, self.course, [MCQ])
        self.assertTrue(res["success"])
        self.assertEqual(res["added"], 1)
        self.assertEqual(res["skipped"], 0)
        pool = read_pool(self.sd, self.course)
        self.assertEqual(len(pool["problems"]), 1)
        prob = pool["problems"][0]
        self.assertEqual(prob["problem_id"], "prob_test_101_001")
        self.assertEqual(prob["options"], MCQ["options"])
        self.assertEqual(prob["course_id"], None) if False else None

    def test_id_increment_across_calls(self):
        add(self.sd, self.course, [MCQ])
        q2 = dict(MCQ, question="Second question?")
        q3 = dict(MCQ, question="Third question?")
        res = add(self.sd, self.course, [q2, q3])
        self.assertEqual(res["added"], 2)
        self.assertEqual(res["ids"], ["prob_test_101_002", "prob_test_101_003"])

    def test_dedup_same_question(self):
        add(self.sd, self.course, [MCQ])
        res = add(self.sd, self.course, [dict(MCQ)])
        self.assertEqual(res["added"], 0)
        self.assertEqual(res["skipped"], 1)
        self.assertEqual(len(read_pool(self.sd, self.course)["problems"]), 1)

    def test_invalid_question_type(self):
        bad = dict(MCQ, question_type="fill_blank")
        res = add(self.sd, self.course, [bad])
        self.assertFalse(res["success"])
        self.assertIn("question_type", res["error"])

    def test_defaults_for_minimal_short_answer(self):
        minimal = {
            "question": "Name the hip flexors.",
            "answer": "Iliopsoas, rectus femoris",
            "question_type": "short_answer",
        }
        add(self.sd, self.course, [minimal])
        prob = read_pool(self.sd, self.course)["problems"][0]
        self.assertEqual(prob["options"], [])
        self.assertEqual(prob["source_file"], "manual")
        self.assertEqual(prob["source_type"], "manual")
        self.assertEqual(prob["verbatim"], False)
        self.assertEqual(prob["tags"], [])

    def test_empty_stdin_fails(self):
        res = _run(["pool", "add", "--savedata", self.sd,
                    "--course", self.course], stdin="")
        self.assertFalse(res["success"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test, verify it fails**

Run: `python -m unittest scripts.tests.test_pool -v` (from repo root)
Expected: FAIL — `pool` not registered subcommand, so `data_writer.py` exits via argparse, stdout not valid JSON → `json.loads` raises. Failures/errors on every test.

- [ ] **Step 3: Add helpers + `cmd_pool_add` to `data_writer.py`**

Add constant next to existing `VALID_DEADLINE_TYPES` (near line 22):

```python
VALID_QUESTION_TYPES = {"mcq", "short_answer", "matching", "labeling", "true_false", "essay"}
```

Add helpers after `progress_path` / `unit_default` (near line 71):

```python
def pool_path(savedata: pathlib.Path, course: str) -> pathlib.Path:
    return savedata / "courses" / course / "data" / "problem_pool.json"


def pool_default(course: str) -> dict:
    return {"course": None, "course_id": course, "last_updated": None, "problems": []}


def _normalize_q(text: str) -> str:
    return " ".join((text or "").lower().split())
```

Add command function (e.g. after `cmd_progress_ingest`, near line 146):

```python
# ── pool add ──────────────────────────────────────────────────────────────────

def cmd_pool_add(args):
    savedata = pathlib.Path(args.savedata)
    path = pool_path(savedata, args.course)
    data = load_json(path, pool_default(args.course))
    data.setdefault("problems", [])

    raw = sys.stdin.buffer.read().decode("utf-8-sig").strip()
    if not raw:
        fail("no input on stdin (expected JSON array of problems)")
    try:
        incoming = json.loads(raw)
    except Exception as e:
        fail(f"invalid JSON on stdin: {e}")
    if not isinstance(incoming, list):
        fail("stdin JSON must be an array of problem objects")

    existing_norm = {_normalize_q(p.get("question", "")) for p in data["problems"]}
    prefix = f"prob_{args.course}_"
    maxnum = 0
    for p in data["problems"]:
        pid = p.get("problem_id", "")
        if pid.startswith(prefix):
            try:
                maxnum = max(maxnum, int(pid[len(prefix):]))
            except ValueError:
                pass

    added_ids = []
    skipped = 0
    for prob in incoming:
        if not isinstance(prob, dict):
            fail("each problem must be a JSON object")
        q = (prob.get("question") or "").strip()
        qtype = prob.get("question_type")
        if not q:
            fail("problem missing 'question'")
        if qtype not in VALID_QUESTION_TYPES:
            fail(f"invalid question_type: {qtype!r}. Valid: {sorted(VALID_QUESTION_TYPES)}")
        norm = _normalize_q(q)
        if norm in existing_norm:
            skipped += 1
            continue
        existing_norm.add(norm)
        maxnum += 1
        pid = f"{prefix}{maxnum:03d}"
        data["problems"].append({
            "problem_id": pid,
            "unit_id": prob.get("unit_id"),
            "unit_slug": prob.get("unit_slug"),
            "topic": prob.get("topic"),
            "question_type": qtype,
            "question": q,
            "options": prob.get("options") or [],
            "answer": prob.get("answer"),
            "rationale": prob.get("rationale"),
            "tags": prob.get("tags") or [],
            "source": prob.get("source"),
            "source_file": prob.get("source_file") or "manual",
            "source_type": prob.get("source_type") or "manual",
            "verbatim": bool(prob.get("verbatim", False)),
            "date_added": today_str(),
        })
        added_ids.append(pid)

    data["last_updated"] = now_iso()
    save_json(path, data)
    out({"success": True, "added": len(added_ids), "skipped": skipped, "ids": added_ids})
```

Wire argparse in `main()` after `progress` block (near line 293), before `deadline`:

```python
    # pool
    plg = sub.add_parser("pool")
    plg_sub = plg.add_subparsers(dest="action")

    pa = plg_sub.add_parser("add")
    pa.add_argument("--savedata", required=True)
    pa.add_argument("--course", required=True)

    pr = plg_sub.add_parser("remove")
    pr.add_argument("--savedata", required=True)
    pr.add_argument("--course", required=True)
    pr.add_argument("--problem-id", required=True)
```

Add dispatch in `try` block (near line 337), after `progress` branch:

```python
        elif args.group == "pool":
            if args.action == "add":
                cmd_pool_add(args)
            elif args.action == "remove":
                cmd_pool_remove(args)
```

(Note: `cmd_pool_remove` added in Task 2; dispatch line referencing it added now but only exercised in Task 2. `pool add` tests pass regardless.)

- [ ] **Step 4: Run test, verify add tests pass**

Run: `python -m unittest scripts.tests.test_pool.PoolAddTests -v`
Expected: PASS (6 tests). `test_id_increment_across_calls`, `test_dedup_same_question`, `test_defaults_for_minimal_short_answer`, `test_add_single`, `test_invalid_question_type`, `test_empty_stdin_fails`.

- [ ] **Step 5: Commit**

```bash
git add scripts/data_writer.py scripts/tests/test_pool.py
git commit -m "feat: add pool add subcommand to data_writer"
```

---

### Task 2: `pool remove` subcommand

**Files:**
- Modify: `scripts/data_writer.py`
- Modify: `scripts/tests/test_pool.py`

- [ ] **Step 1: Add failing test**

Append to `scripts/tests/test_pool.py` (before `if __name__` line):

```python
class PoolRemoveTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sd = self._tmp.name
        self.course = "test_101"
        add(self.sd, self.course, [MCQ, dict(MCQ, question="Second?")])

    def tearDown(self):
        self._tmp.cleanup()

    def test_remove_existing(self):
        res = remove(self.sd, self.course, "prob_test_101_001")
        self.assertTrue(res["success"])
        self.assertEqual(res["removed"], "prob_test_101_001")
        ids = [p["problem_id"] for p in read_pool(self.sd, self.course)["problems"]]
        self.assertEqual(ids, ["prob_test_101_002"])

    def test_remove_missing(self):
        res = remove(self.sd, self.course, "prob_test_101_999")
        self.assertFalse(res["success"])
        self.assertIn("not found", res["error"])
```

- [ ] **Step 2: Run test, verify it fails**

Run: `python -m unittest scripts.tests.test_pool.PoolRemoveTests -v`
Expected: FAIL — `cmd_pool_remove` referenced in dispatch but not defined → subprocess raises `NameError`, stdout empty, `json.loads` fails. (Both tests error.)

- [ ] **Step 3: Implement `cmd_pool_remove`**

Add after `cmd_pool_add` in `data_writer.py`:

```python
# ── pool remove ───────────────────────────────────────────────────────────────

def cmd_pool_remove(args):
    savedata = pathlib.Path(args.savedata)
    path = pool_path(savedata, args.course)
    data = load_json(path, pool_default(args.course))
    data.setdefault("problems", [])

    before = len(data["problems"])
    data["problems"] = [p for p in data["problems"]
                        if p.get("problem_id") != args.problem_id]
    if len(data["problems"]) == before:
        fail(f"problem id not found: {args.problem_id!r}")
    data["last_updated"] = now_iso()
    save_json(path, data)
    out({"success": True, "removed": args.problem_id})
```

- [ ] **Step 4: Run full suite**

Run: `python -m unittest scripts.tests.test_pool -v`
Expected: PASS (8 tests total).

- [ ] **Step 5: Commit**

```bash
git add scripts/data_writer.py scripts/tests/test_pool.py
git commit -m "feat: add pool remove subcommand to data_writer"
```

---

### Task 3: Schema + scripts docs

**Files:**
- Modify: `.claude/commands/lkschemas.md`
- Modify: `.claude/commands/lkscripts.md`

- [ ] **Step 1: Append pool schema to `lkschemas.md`**

Add at end of file:

```markdown

## Per-course `data\problem_pool.json`
Past quiz/exam problems. Served verbatim by `/lkquiz` and used as style exemplars to generate gap-filling questions. Written only via `data_writer.py pool add` / `pool remove`.

**top-level**: `course`, `course_id`, `last_updated`, `problems[]`
**problems[]**: `problem_id` (`prob_{course_id}_{NNN}`), `unit_id` (or null), `unit_slug` (or null), `topic` (same vocabulary as progress.json `weak_topics`), `question_type` (`mcq` | `short_answer` | `matching` | `labeling` | `true_false` | `essay`), `question`, `options` (array; `[]` unless mcq), `answer`, `rationale` (or null), `tags` (Section 1 tags), `source` (label e.g. "Midterm 1 2025"), `source_file` (filename or "manual"), `source_type` (`past_exam` | `practice_quiz` | `exam_review` | `manual`), `verbatim` (bool), `date_added`
Default empty: `{"course": null, "course_id": null, "last_updated": null, "problems": []}`
```

- [ ] **Step 2: Add `pool` subcommands to `lkscripts.md`**

In "Complete subcommand reference" table, add rows after `progress ingest` row:

```markdown
| `pool add` | `--savedata --course` | — (reads JSON array of problems from stdin) |
| `pool remove` | `--savedata --course --problem-id` | — |
```

Then add block after existing flag notes (before "Log entry format" heading):

````markdown
**`pool add` — batch problem write (reads stdin, like `notes write`):**
```powershell
$problemsJson = @'
[ { "question": "Which nerve innervates gluteus medius?", "answer": "Superior gluteal nerve", "question_type": "mcq", "options": ["Superior gluteal nerve","Sciatic nerve"], "unit_id": "week_03", "unit_slug": "week_03_hip_joint_gluteal_region", "topic": "Nerves of gluteal region", "source": "Midterm 1 2025", "source_file": "source_midterm1.pdf", "source_type": "past_exam", "verbatim": true } ]
'@
$result = ($problemsJson | & $pythonExe $writerPath pool add `
    --savedata $savedataRoot --course "pther_350a") | ConvertFrom-Json
if (-not $result.success) { Write-Host "Pool write failed: $($result.error)" }
# success → { added, skipped, ids[] }
```
`--course` is course slug. Each problem one object in array; one call writes many. `question_type` validated against allowed set; duplicate question text (normalized) skipped.
````

- [ ] **Step 2b: Verify**

Run: `grep -n "problem_pool" .claude/commands/lkschemas.md && grep -n "pool add" .claude/commands/lkscripts.md`
Expected: matches in both files.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/lkschemas.md .claude/commands/lkscripts.md
git commit -m "docs: document problem_pool schema and pool subcommands"
```

---

### Task 4: CLAUDE.md updates

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add pool file to Section 2 per-course data list**

In Section 2, under `PER-COURSE DATA (...)`, after `data\progress.json` line, add:

```
  data\problem_pool.json      — past quiz/exam problems (pool); served + style-exemplar source for /lkquiz
```

- [ ] **Step 2: Add `/lkpool` command entry to Section 6**

After `/lkprogress` command block (and before `/lkcourse`), insert:

```markdown
### `/lkpool` — Problem pool management
Full spec in `.claude/commands/lkpool.md`. Variants: `/lkpool {course}` (summary + coverage map), `/lkpool add {course}`, `/lkpool list {course} [unit]`, `/lkpool remove {problem_id}`. Holds past quiz/exam problems used by `/lkquiz`.

---
```

- [ ] **Step 3: Add problem-id naming convention to Section 8**

After `Deadline ID` bullet, add:

```markdown
- **Problem ID**: `prob_{course_id}_{NNN}` — e.g. `prob_pther_350a_001` (increment from current max in that course's `problem_pool.json`)
```

- [ ] **Step 4: Verify**

Run: `grep -n "problem_pool.json\|/lkpool\|Problem ID" CLAUDE.md`
Expected: three matches (Section 2, Section 6, Section 8).

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: register problem pool in CLAUDE.md (data, command, naming)"
```

---

### Task 5: New `/lkpool` command spec

**Files:**
- Create: `.claude/commands/lkpool.md`

- [ ] **Step 1: Write command file**

Create `.claude/commands/lkpool.md`:

```markdown
Base context (path variables, behavioral rules) loaded from CLAUDE.md. Data schemas in lkschemas.md. Python script protocol and data_writer.py reference in lkscripts.md. Log entry format spec in lklogging.md.

## `/lkpool` — Problem pool management

Manages each course's `data\problem_pool.json` — bank of past quiz/exam problems `/lkquiz` serves verbatim and mines for style. All writes go through `data_writer.py` `pool add` / `pool remove` (Rule 15). Multiple active courses + none specified → ask (Rule 2). Never mix courses (Rule 1). Log every mutation (Rule 14).

### `/lkpool {course}` — summary
Read `course_structure.json` and `problem_pool.json`. Print:
- Total problem count.
- Breakdown by unit (`display_name` → count) and by `source_type`.
- **Coverage map**: for each unit's `topics`, mark `✓` if ≥1 pool problem has that `topic` (or maps to that unit), `—` if none. Shows where `/lkquiz` generates gap-fillers vs serves verbatim.

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
Prompt for: question text, `question_type` (mcq/short_answer/matching/labeling/true_false/essay), options (if mcq), answer, optional topic and unit. Build one-element JSON array, pipe to `pool add`:

```powershell
$problemsJson = @'
[ { "question": "...", "answer": "...", "question_type": "short_answer", "topic": "...", "unit_id": "week_03", "source": "Instructor note", "verbatim": false } ]
'@
$r = ($problemsJson | & $pythonExe $writerPath pool add --savedata $savedataRoot --course "{slug}") | ConvertFrom-Json
if (-not $r.success) { Write-Host "Failed: $($r.error)" }
```
`source_type` defaults to `manual`, `verbatim` to false. Confirm: `"Added {id} to {course_code} pool."` Then log: `[POOL] Added 1 problem (manual) -> {unit or 'unmapped'}`.

### `/lkpool list {course} [unit]` — list
Read `problem_pool.json`. Print table: `problem_id`, `question_type`, `topic`, `source`. Optional unit filter (match `unit_id` or `unit_slug`). Truncate question preview to ~60 chars if shown.

### `/lkpool remove {problem_id}` — delete
Derive course slug from id: strip `prob_` prefix and trailing `_{NNN}` segment (NNN always 3-digit final segment) → remainder is course slug. Show problem, confirm, then:

```powershell
$r = (& $pythonExe $writerPath pool remove --savedata $savedataRoot --course "{slug}" --problem-id "{problem_id}") | ConvertFrom-Json
if (-not $r.success) { Write-Host "Failed: $($r.error)" }
```
Confirm: `"Removed {id}."` Log: `[POOL] Removed {id}`.
```

- [ ] **Step 2: Verify**

Run: `grep -n "lkpool\|pool add\|pool remove\|Coverage map" .claude/commands/lkpool.md`
Expected: matches present.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/lkpool.md
git commit -m "feat: add /lkpool command spec"
```

---

### Task 6: `/lkingest` extraction step

**Files:**
- Modify: `.claude/commands/lkingest.md`

- [ ] **Step 1: Add `past_exam` to classifier**

In step 3 ("Classify file type"), add bullet after `exam_review` line:

```markdown
   - `past_exam` — "midterm", "final", past "exam" with discrete numbered/lettered question structure (distinct from `exam_review`, which is a prose study guide)
```

- [ ] **Step 2: Add extraction step**

After step 7 ("Generate grade-focused study notes...") and before step 8 ("Fire all data writes..."), insert new step 7b:

````markdown
7b. **Extract problems to the pool** (only when file type ∈ `{practice_quiz, exam_review, past_exam}`): Scan the extracted text for discrete Q+A pairs. None found (prose study guide) → skip, notes only. For each problem found:
   - Map to a unit by keyword overlap (same logic as step 5). Unmappable → `unit_id`/`unit_slug` null.
   - Assign a `topic` label from the unit's `topics` / weak-topic vocabulary.
   - Set `question_type`, `options` (mcq only), `answer`, optional `rationale` and Section 1 `tags`. All content strictly from the file — no invented problems (Rule 9).
   - Set `source_type` = file classification, `verbatim: true`, `source_file` = ingested filename, `source` = inferred label (e.g. "Practice Quiz — Week 3").

   Build one JSON array of all problems and write via a single `pool add` call (see lkscripts.md). Surface: `"Extracted {added} problem(s) to {course_code} pool ({skipped} duplicate(s) skipped)."`
````

- [ ] **Step 3: Add log line for extraction**

In step 8's log-entry block, after existing `[INGEST]` entry, add (only when problems extracted):

```markdown
   - When step 7b added problems, also: `- [POOL] Extracted {N} problem(s) from {filename} -> {unit(s)}`
```

- [ ] **Step 4: Verify**

Run: `grep -n "past_exam\|7b\|Extract problems" .claude/commands/lkingest.md`
Expected: matches present.

- [ ] **Step 5: Commit**

```bash
git add .claude/commands/lkingest.md
git commit -m "feat: extract problems to pool during /lkingest"
```

---

### Task 7: `/lkquiz` pool sourcing + `mock` scope

**Files:**
- Modify: `.claude/commands/lkquiz.md`

- [ ] **Step 1: Add `mock` to scope grammar**

In `{scope} accepts:` list, add:

```markdown
- `exam_1 mock` (or any scope + `mock`) — mock mode: verbatim-heavy, every covered topic represented
```

- [ ] **Step 2: Add pool sourcing to Step 0**

In "Step 0 — Pre-quiz setup", after `progress.json` adaptive-weighting paragraph, add:

````markdown
**Problem pool sourcing**: Read `courses\{slug}\data\problem_pool.json`. For problems whose `unit_id` ∈ scope:
- **Coverage map** — split scope topics into pool-covered vs not.
- **Verbatim problems** — serve pool problems directly (count toward the question total). Prioritize `EXAM-CRITICAL` tags and topics tied to the next upcoming exam.
- **Generated gap-fillers** — for scope topics with no pool problem, generate fresh questions matching the pool's observed style (question-type mix, phrasing, difficulty). Adaptive weights still apply.
- **Format mirror** — when the pool covers the scope, derive the MCQ/short-answer ratio from the pool (overrides the ~70/30 default below).
- **Mix** — normal scope: blend, capping the verbatim share so fresh practice remains. `mock` keyword: verbatim-heavy, and ensure every covered topic appears (verbatim where available, generated otherwise).
- **Empty pool** → behavior unchanged (materials-only).
````

- [ ] **Step 3: Note pool usage in Step 4 log entry**

In "Step 4 — Data updates", change log `--entry` to append mode suffix when pool contributed:

```markdown
Append ` (mock)` or ` (pool-augmented)` to the log entry's `{display_name}` segment when pool problems were served, e.g. `- [QUIZ] {display_name} (pool-augmented) — {score}/{total} ...`.
```

- [ ] **Step 4: Verify**

Run: `grep -n "mock\|problem_pool\|Verbatim problems\|gap-filler" .claude/commands/lkquiz.md`
Expected: matches present.

- [ ] **Step 5: Commit**

```bash
git add .claude/commands/lkquiz.md
git commit -m "feat: source problem pool in /lkquiz with mock scope"
```

---

### Task 8: Full-suite verification

**Files:** none (verification only)

- [ ] **Step 1: Run whole test suite**

Run: `python -m unittest discover -s scripts/tests -v`
Expected: PASS (8 tests).

- [ ] **Step 2: End-to-end smoke against scratch dir**

Run:
```bash
python - <<'PY'
import json, subprocess, sys, tempfile, pathlib
sd = tempfile.mkdtemp()
prob = [{"question":"Smoke?","answer":"Yes","question_type":"short_answer","unit_id":"week_01","topic":"t"}]
r = subprocess.run([sys.executable,"scripts/data_writer.py","pool","add","--savedata",sd,"--course","smoke_1"],
                   input=json.dumps(prob),capture_output=True,text=True)
print("ADD:", r.stdout.strip())
f = pathlib.Path(sd)/"courses"/"smoke_1"/"data"/"problem_pool.json"
print("FILE:", f.read_text())
PY
```
Expected: `ADD: {"success": true, "added": 1, "skipped": 0, "ids": ["prob_smoke_1_001"]}` and well-formed pool file.

- [ ] **Step 3: Confirm no stray writes to real savedata**

Run: `git status --porcelain savedata/`
Expected: empty (no real course data touched by tests/smoke).

---

## Self-Review

**Spec coverage:**
- §1 schema → Task 3 (schema doc) + Tasks 1–2 (writer produces exactly these fields). ✓
- §2 population (auto + manual + dedup) → Task 6 (ingest), Task 5 (`/lkpool add`), Task 1 (dedup). ✓
- §3 `data_writer.py` subcommands → Tasks 1–2. ✓
- §4 `/lkpool` command → Task 5; registered in CLAUDE.md Task 4. ✓
- §5 `/lkquiz` integration + `mock` → Task 7. ✓
- §6 doc updates → Tasks 3, 4, 6, 7. ✓

**Placeholder scan:** No TBD/TODO; all code and insertion text literal. ✓

**Type consistency:** `pool add` / `pool remove`, flags `--savedata --course --problem-id`, `problem_id` = `prob_{course}_{NNN}`, output keys `added`/`skipped`/`ids`/`removed` identical across plan, tests, docs. Dispatch line referencing `cmd_pool_remove` added in Task 1 but function defined in Task 2 — Task 1's tests only exercise `pool add`, so safe; Task 2 completes pair. ✓

**Note:** `test_add_single` contains deliberately inert `... if False else None` line guarding a field check that does not apply (per-problem object has no `course_id`); no-op, can be deleted during implementation. (Implementer: just remove that line.)
