Standalone log format reference. Read this file before writing any log entries.

## Log Locations

- **Global**: `$savedataRoot\data\activity_log.md` — all events, all courses
- **Per-course**: `$savedataRoot\courses\{slug}\activity_log.md` — one course only

Same format, both files. Global includes course code prefix; per-course omits.

## Entry Format

Prepend after file header (newest first). Group under `## YYYY-MM-DD (Weekday)`. Today's heading exists → append; don't duplicate.

```markdown
## 2026-05-11 (Monday)
- [QUIZ]     BIOL 201 | Unit 1: Cell Structure — 16/20 (80%) | Weak: cell cycle phases, membrane transport
- [INGEST]   COMP 361 | 2 files → Unit 1: Sorting Algorithms (lecture_slides, lab_notes)
- [DEADLINE] BIOL 201 | Added: Midterm 1 on 2026-05-21 (Covers Units 1-2)
- [COURSE]   CHEM 110 | Course added — Fall 2026
```

| Type | Global format | Per-course format |
|------|--------------|-------------------|
| `[QUIZ]` | `{course_code} \| Unit N: {name} — {score}/{total} ({pct}%) \| Weak: {topics or "none"}` | same as global (omit course code prefix) |
| `[INGEST]` | `{course_code} \| {N} file(s) → {unit(s)}: {filenames, comma-separated}` | `{N} file(s) → {unit(s)}: {filenames}` |
| `[DEADLINE]` | `{course_code} \| {Added/Updated/Completed}: {title} on {date}` | `{Added/Updated/Completed}: {title} on {date}` |
| `[NOTE]` | `{course_code} \| Misc note added` | `Misc note added` |
| `[COURSE]` | `{code} \| {action: added/archived} — {brief detail}` | `Course {action} — {brief detail}` |
| `[SYNC]` | `Pushed to remote — {N} file(s) \| "{commit short}"` | *(global log only)* |

All entries one line.

## Quiz Pass Note

First quiz pass on unit (score ≥ 70%) → append to the `[QUIZ]` line: `  → Unit N marked quiz_passed`
