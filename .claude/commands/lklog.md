Base context (path vars, behavioral rules) from CLAUDE.md. Log entry format spec in lklogging.md.

## `/lklog` — View activity log

**`/lklog`** — Last 7 days, all courses. Read all per-course `activity_log.md` files, merge entries, sort by date descending.
**`/lklog {course_code}`** — Last 7 days, one course (`courses\{slug}\activity_log.md`).
**`/lklog {N}d`** — Last N days. E.g. `/lklog 14d`, `/lklog 30d`.
**`/lklog quiz {unit_id}`** — All past quiz blocks for unit from `courses\{slug}\activity_log.md`, newest first. Multiple active courses → ask which.

Read lklogging.md for log entry formats when presenting output.
