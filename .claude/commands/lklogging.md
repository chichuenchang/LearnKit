Standalone log format reference. Read this file before writing any log entries.

## Log Location

**Per-course only**: `$savedataRoot\courses\{slug}\activity_log.md`

## Entry Format

Prepend after file header (newest first). Group under `## YYYY-MM-DD (Weekday)`. Today's heading exists → append; don't duplicate.

```markdown
## 2026-05-11 (Monday)
- [QUIZ]     {display_name} — 16/20 (80%) | Weak: cell cycle phases, membrane transport
- [INGEST]   2 files → {display_name} (lecture_slides, lab_notes)
- [DEADLINE] Added: Midterm 1 on 2026-05-21 (Covers {Units/Weeks} 1-2)
- [COURSE]   Course added — Fall 2026
```

| Type | Format |
|------|--------|
| `[QUIZ]` | `{display_name} — {score}/{total} ({pct}%) \| Weak: {topics or "none"}` |
| `[INGEST]` | `{N} file(s) → {unit(s)}: {filenames, comma-separated}` |
| `[DEADLINE]` | `{Added/Updated/Completed}: {title} on {date}` |
| `[NOTE]` | `Misc note added` |
| `[COURSE]` | `Course {action: added/archived} — {brief detail}` |

All entries one line. `{display_name}` = value from `course_structure.json` (e.g. `"Week 1: Vertebral Column"` or `"Unit 1: Cell Structure"`).

## Quiz Pass Note

First quiz pass on unit (score ≥ 70%) → append to the `[QUIZ]` line: `  → {display_name} marked quiz_passed`
