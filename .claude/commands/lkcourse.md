Base context (path vars, behavioral rules) from CLAUDE.md. Data schemas in lkschemas.md. Python script protocol + data_writer.py ref in lkscripts.md. Log format spec in lklogging.md.

## `/lkcourse` — Course management

### `/lkcourse add {code} {name}`

Ask: `"Semester (e.g., Fall 2026):"`
Ask:
```
How is this course organized?
  [1] Units (Unit 1, Unit 2, ...)       ← default
  [2] Weeks (Week 1, Week 2, ...)
  [3] Chapters (Chapter 1, Chapter 2, ...)
  [4] Modules (Module 1, Module 2, ...)
  [5] Topics (Topic 1, Topic 2, ...)
  [6] Lectures (Lecture 1, Lecture 2, ...)
  [7] Books (Book 1, Book 2, ...)
```
Store as `unit_label: "{chosen label}"` in course_structure.json (prefix/short-code mapping: lkschemas.md).

1. Make slug: `BIOL 201` → `biol_201`
2. Check slug collision → warn + confirm if similar exists
3. Add entry to `courses_index.json` (`active_courses`)
4. Make directory skeleton under `$savedataRoot\courses\{slug}\`:
   ```
   courses\{slug}\
   courses\{slug}\materials\
   courses\{slug}\materials\multi_unit\
   courses\{slug}\data\
   ```
5. Make default empty JSON: `course_structure.json`, `progress.json`, `problem_pool.json` (default empty values: lkschemas.md)
6. Make `courses\{slug}\activity_log.md`:
   ```markdown
   # {course_code} — Activity Log
   **Course**: {course_code} — {course_name} | **Semester**: {semester}
   <!-- Entries are prepended below this line. Newest entries appear first. -->

   ---
   ```
7. Make `courses\{slug}\misc.md`:
   ```markdown
   # {course_code} — Notes & Miscellaneous
   **Course**: {course_code} — {course_name} | **Semester**: {semester} | **Created**: {date}

   > Use this file for anything important that doesn't fit elsewhere: deadline changes,
   > instructor announcements, reminders, exam format updates, etc.
   > Agent reads this at the start of every study and quiz session.

   ---

   ```
8. Read lklogging.md. Write `[COURSE]` log entry to `courses\{slug}\activity_log.md`. Print:
   ```
   Course added: {course_code} — {course_name}
   Folder: savedata\courses\{slug}\
   Next step: Drop the syllabus into savedata\raw\ or paste its path to load the course structure.
   ```

---

### `/lkcourse complete {code}` — Archive done course

1. Show confirmation:
   ```
   Archive {course_code} — {course_name}?
   This will move savedata\courses\{slug}\ → savedata\archive\{slug}\ and stop tracking its deadlines.
   Contents: 14 material files, 8 quizzes, 3 data files.
   Type YES to confirm:
   ```
2. On "YES":
   - `Move-Item "$savedataRoot\courses\{slug}" "$savedataRoot\archive\{slug}"`
   - Write `archive\{slug}\archive_summary.md`:
     ```
     # {course_code} — Archive Summary
     Archived: {date}
     Semester: {semester}
     Materials ingested: N files
     Quizzes completed: N
     Global weak areas at archive time: [list]
     ```
   - Move entry: `active_courses` → `archived_courses` in `courses_index.json`
   - Remove course deadlines from `global_deadlines.json`
   - Read lklogging.md. Write `[COURSE]` to `courses\{slug}\activity_log.md` BEFORE moving: `"Course archived — {N} quizzes completed"`
   - Print: `"{course_code} archived. Deadlines removed from tracker."`

---

### `/lkcourse list`

Table of all active + archived courses: status, progress, semester.
