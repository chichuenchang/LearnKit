Base context (path variables, behavioral rules) loaded from CLAUDE.md. Data schemas in lkschemas.md. Python script protocol and data_writer.py reference in lkscripts.md. Log entry format spec in lklogging.md.

## `/lkcourse` — Course management

### `/lkcourse add {code} {name}`

Ask: `"Semester (e.g., Fall 2026):"`

1. Generate slug: `BIOL 201` → `biol_201`
2. Check for slug collision → warn and confirm if similar exists
3. Add entry to `courses_index.json` (`active_courses`)
4. Create directory skeleton under `$savedataRoot\courses\{slug}\`:
   ```
   courses\{slug}\
   courses\{slug}\materials\
   courses\{slug}\materials\multi_unit\
   courses\{slug}\data\
   ```
5. Create default empty JSON: `course_structure.json`, `progress.json` (see lkschemas.md for default empty values)
6. Create `courses\{slug}\activity_log.md`:
   ```markdown
   # {course_code} — Activity Log
   **Course**: {course_code} — {course_name} | **Semester**: {semester}
   <!-- Entries are prepended below this line. Newest entries appear first. -->

   ---
   ```
7. Create `courses\{slug}\misc.md`:
   ```markdown
   # {course_code} — Notes & Miscellaneous
   **Course**: {course_code} — {course_name} | **Semester**: {semester} | **Created**: {date}

   > Use this file for anything important that doesn't fit elsewhere: deadline changes,
   > instructor announcements, reminders, exam format updates, etc.
   > Agent reads this at the start of every study and quiz session.

   ---

   ```
8. Read lklogging.md. Write `[COURSE]` log entry. Print:
   ```
   Course added: {course_code} — {course_name}
   Folder: savedata\courses\{slug}\
   Next step: Drop the syllabus into savedata\raw\ or paste its path to load the course structure.
   ```

---

### `/lkcourse complete {code}` — Archive completed course

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
     Final completion: N%
     Global weak areas at archive time: [list]
     ```
   - Move entry: `active_courses` → `archived_courses` in `courses_index.json`
   - Remove course deadlines from `global_deadlines.json`
   - Read lklogging.md. Write `[COURSE]` to both logs: `"{course_code} archived — {final_completion_pct}% complete after {N} quizzes"`
   - Print: `"{course_code} archived. Deadlines removed from tracker."`

---

### `/lkcourse list`

Table of all active + archived courses with status, progress, semester.
