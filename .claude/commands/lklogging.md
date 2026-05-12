Standalone log format reference. Read this file before writing any log entries.

## Log Locations

- **Global**: `$savedataRoot\data\activity_log.md` — all events, all courses
- **Per-course**: `$savedataRoot\courses\{slug}\activity_log.md` — one course only

Same format, both files. Global includes course code prefix; per-course omits.

## Entry Format

Prepend after file header (newest first). Group under `## YYYY-MM-DD (Weekday)`. Today's heading exists → append; don't duplicate.

```markdown
## 2026-05-11 (Monday)
- [STUDY]    BIOL 201 | Unit 2: Cell Cycle — mitosis, meiosis, checkpoints
- [QUIZ]     BIOL 201 | Unit 1: Cell Structure — 16/20 (80%) | Weak: cell cycle phases, membrane transport
- [INGEST]   COMP 361 | 2 files → Unit 1: Sorting Algorithms (lecture_slides, lab_notes)
- [DEADLINE] BIOL 201 | Added: Midterm 1 on 2026-05-21 (Covers Units 1-2)
- [COURSE]   CHEM 110 | Course added — Fall 2026
```

| Type | Global format | Per-course format |
|------|--------------|-------------------|
| `[STUDY]` | `{course_code} \| Unit N: {name} — {topic summary, ≤8 words}` | `Unit N: {name} — {topic summary}` |
| `[QUIZ]` | `{course_code} \| Unit N: {name} — {score}/{total} ({pct}%) \| Weak: {topics or "none"}` | **rich block** — see below |
| `[INGEST]` | `{course_code} \| {N} file(s) → {unit(s)}: {filenames, comma-separated}` | `{N} file(s) → {unit(s)}: {filenames}` |
| `[DEADLINE]` | `{course_code} \| {Added/Updated/Completed}: {title} on {date}` | `{Added/Updated/Completed}: {title} on {date}` |
| `[NOTE]` | `{course_code} \| Misc note added` | `Misc note added` |
| `[COURSE]` | `{code} \| {action: added/archived} — {brief detail}` | `Course {action} — {brief detail}` |
| `[SYNC]` | `Pushed to remote — {N} file(s) \| "{commit short}"` | *(global log only)* |

All entries one line — except `[QUIZ]` in per-course log (rich block below).

## Per-Course Quiz Block Format

```markdown
### [QUIZ] 2026-05-11 — Unit 1: Cell Structure
**Score**: 14/18 (78%) PASS | **Adaptive**: yes | **Format**: 13 MCQ + 5 short answer | **Partial**: no

| # | Topic | Question (≤80 chars) | Answer Given | Result |
|---|-------|----------------------|-------------|--------|
| 1 | cell membrane | What is the fluid mosaic model? | Described correctly | ✓ |
| 2 | cell cycle | Name all phases of mitosis | Named 3, missed telophase | ✗ |
| 3 | membrane transport | Difference: active vs passive transport? | Partially correct | ✗ (H) |
| 4 | ATP synthesis | Where does ATP synthesis occur? | skipped | → |
...

**MCQ**: 12/13 (92%) | **Short answer**: 2/5 (40%)
**Persistent weak topics** (≥2 sessions): cell cycle phases, membrane transport
**New weak topics** (first miss): ATP synthesis location
**Adaptive weights applied**: cell cycle ×1.8, membrane transport ×1.5
**Next quiz**: +2 cell cycle | +2 membrane transport | +1 ATP synthesis | +short answer practice
```

Result codes: `✓` correct | `✗` incorrect | `✓(H)` correct after hint (counts ½) | `✗(H)` incorrect after hint | `→` skipped

## Quiz Pass Note

First quiz pass on unit (score ≥ 70%) → append note on quiz's `[QUIZ]` line: `  → Unit N marked quiz_passed`
