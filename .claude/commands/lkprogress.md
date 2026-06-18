Base context (path vars, behavioral rules) from CLAUDE.md. Data schemas in lkschemas.md.

## `/lkprogress` — Dashboard

**`/lkprogress`**: Overview, all active courses. Read lkschemas.md before querying progress.json.
```
Study Progress — All Active Courses
──────────────────────────────────────────────────────────────────────
Course       Study Streak  Nearest Exam
──────────── ───────────── ────────────────────
BIOL 201     3 days        May 21 — Midterm 1 (10d)
COMP 361     1 day         Jun 5  — Lab Quiz 2 (25d)
──────────────────────────────────────────────────────────────────────
Global weak areas needing attention:
  BIOL 201: cell cycle phases, membrane transport
  COMP 361: graph algorithms, dynamic programming
```

**`/lkprogress {course_code}`**: Per-unit breakdown. Each unit: status, materials ingested, quiz scores, weak areas.
