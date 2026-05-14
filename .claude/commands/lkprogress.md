Base context (path variables, behavioral rules) loaded from CLAUDE.md. Data schemas in lkschemas.md.

## `/lkprogress` — Study dashboard

**`/lkprogress`**: Overview, all active courses. Read lkschemas.md before querying progress.json.
```
Study Progress — All Active Courses
──────────────────────────────────────────────────────────────────────
Course       Units Done  Overall %  Study Streak  Nearest Exam
──────────── ─────────── ────────── ───────────── ────────────────────
BIOL 201     4/6         62%        3 days        May 21 — Midterm 1 (10d)
COMP 361     2/5         20%        1 day         Jun 5  — Lab Quiz 2 (25d)
──────────────────────────────────────────────────────────────────────
Global weak areas needing attention:
  BIOL 201: cell cycle phases, membrane transport
  COMP 361: graph algorithms, dynamic programming
```

**`/lkprogress {course_code}`**: Detailed per-unit breakdown showing each unit's status, materials ingested, quiz scores, and weak areas.
