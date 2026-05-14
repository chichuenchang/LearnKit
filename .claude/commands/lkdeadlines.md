Base context (path variables, behavioral rules) loaded from CLAUDE.md. Data schemas in lkschemas.md. Python script protocol and data_writer.py reference in lkscripts.md. Log entry format spec in lklogging.md.

## `/lkdeadlines` — View and manage deadlines

**`/lkdeadlines`**: All incomplete deadlines, all active courses, sorted by date.
```
Upcoming Deadlines — All Courses
─────────────────────────────────────────────────────────────────────────
  Date       Course      Type          Title                        Days
  ────────── ─────────── ───────────── ──────────────────────────── ────
  2026-05-15 BIOL 201    EXAM          Midterm 1 — Cell Biology       2  ← CRITICAL
  2026-05-21 COMP 361    EXAM          Midterm 1 — Algorithms        10  ← URGENT
  2026-05-24 COMP 361    ASSIGNMENT    Lab Report 2                  13
  2026-05-28 BIOL 201    LAB PRAC      Lab Practical 2               17
  2026-06-05 COMP 361    QUIZ          Quiz 2 — Algorithms           25
─────────────────────────────────────────────────────────────────────────
Mark as completed: /lkdeadlines complete {deadline_id}
```
≤ 3 days → `← CRITICAL`. 4–14 days → `← URGENT`.

**`/lkdeadlines {course_code}`**: Filtered to one course.

**`/lkdeadlines add`**: User-initiated deadline parse from pasted announcement text.

**`/lkdeadlines complete {deadline_id}`**: Set `completed: true` in `global_deadlines.json` via `deadline complete --deadline-id`. Recalculate `next_deadline_date` in `courses_index.json` via `index update`. Read lklogging.md, write `[DEADLINE]` log entry to the course's `activity_log.md`.

**Duplicate detection before saving any deadline:**
1. Exact match (same `type + title + date`, same course) → skip silently: `"'{title} on {date}' already recorded — skipping duplicate"`
2. Same title + course, different date → ask: `"'{title}' already recorded on {date1}. Update to {date2}? [Y/n]"` — modify in place
3. Same title + course, different details → ask: `"'{title}' already recorded but scope changed. Update? [Y/n]"` — modify `details` in place
