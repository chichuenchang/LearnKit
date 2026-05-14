Base context (path variables, behavioral rules) loaded from CLAUDE.md. Log entry format spec in lklogging.md.

## `/lklog` — View activity log

**`/lklog`** — Last 7 days, all courses. Reads all per-course `activity_log.md` files, merges entries, sorts by date descending.
**`/lklog {course_code}`** — Last 7 days, one course (`courses\{slug}\activity_log.md`).
**`/lklog {N}d`** — Last N days, e.g. `/lklog 14d` or `/lklog 30d`.
**`/lklog quiz {unit_id}`** — All past quiz blocks for unit from `courses\{slug}\activity_log.md`, newest first. Multiple active courses → ask which course.

Read lklogging.md to understand log entry formats when presenting output.
