Base context (path variables, behavioral rules, Section 1 tagging) loaded from CLAUDE.md. Data schemas in lkschemas.md. Python script protocol and data_writer.py reference in lkscripts.md. Log entry format spec in lklogging.md.

## `/lkingest` — Process new course materials

**Two input methods — same pipeline:**

**Method A: `raw\` folder**
Drop files in `savedata\raw\`, run `/lkingest`. Move each file out after success.

**Method B: Pasted paths (auto-detected)**
Detect Windows absolute paths in any message → ask:
```
I see N file path(s) to ingest:
  - C:\Users\{username}\Downloads\BIOL201_Week3_Slides.pptx
  - C:\Users\{username}\Downloads\biol201_syllabus.pdf

Ingest them now? [Y/n]
```
On confirm: **copy** into project. Never delete or move originals.

**Shared pipeline for each file:**

1. **Extract text**: Run `scripts\extract_text.py` (via $pythonExe and $scriptsRoot — see `lkscripts.md`). Fails → report error and skip; don't continue with that file.
   - `scanned: false` → use `data.text` as normal for all downstream steps
   - `scanned: true` → read each path in `data.image_paths` via Read tool; generate study notes from visual page content; clean up `tmp_pages/{basename}/` after notes written
   - `capped: true` → surface before proceeding: `"Note: {filename} has {page_count} pages — first 20 ingested. Re-ingest and confirm to process remaining pages."`

2. **Identify course**: Section 4 logic (CLAUDE.md).

3. **Classify file type** from filename + first 2,000 chars:
   - `syllabus` — "syllabus", "course outline", course code + "course"
   - `lecture_slides` — "lecture", ".pptx", slide deck structure
   - `lab_notes` — "lab", "laboratory"
   - `practice_quiz` — "quiz", "practice questions", "sample questions"
   - `exam_review` — "exam review", "study guide", "review sheet"
   - `assignment` — "assignment", "submit", "due date"
   - `announcement` — "announcement", "reminder", "please note", deadline language without study content
   - `other` — anything else

4. **If syllabus**: Check if `course_structure.json` has units populated. No → run **Syllabus Processing Branch** (below). Yes → offer to update.

5. **Identify unit** (non-syllabus): Compare text vs `keywords` in all units of `course_structure.json`. Assign highest overlap (minimum 2 matches). File spans multiple units → ask:
   ```
   "[filename]" appears to span multiple units.
     Unit 1 — Cell Structure: 12 keyword matches
     Unit 2 — Cell Cycle: 9 keyword matches
     Unit 3 — Genetics: 7 keyword matches

   Options:
     [1] Assign to Unit 1 (highest overlap) — add cross-reference notes to Units 2 and 3
     [2] File under multi_unit\ folder
     [3] Assign to a specific unit (type unit ID):
   ```
   Option 1 → primary unit; add `_cross_ref_{slug}.md` in each other unit: `See also: [path to primary summary]`.
   Option 2 → `courses\{slug}\materials\multi_unit\`. `/lkquiz` for any relevant unit includes `multi_unit\` files.

6. **Archive original**:
   - `raw\` method: `Move-Item` from `$savedataRoot\raw\{filename}` → `$savedataRoot\courses\{slug}\materials\{unit_slug}\source_{slug}.{ext}`
   - Path-paste: `Copy-Item` → same destination (original untouched)

7. **Generate grade-focused study notes** → `courses\{slug}\materials\{unit_slug}\{type}_{slug}.md`
   - First line: `**Source**: {filename} | **Unit**: {unit display name} | **Type**: {file_type} | **Ingested**: {date}`
   - Apply Section 1 tagging per topic
   - Group by learning objective if syllabus provides them
   - Include "Key Terms" section with definitions tagged by exam probability
   - Include "Likely Quiz/Exam Questions" section at end

8. **Fire all data writes synchronously** (silent — no output, no task notification), then print `"Done — {N} file(s) ingested."`. Sequential, no race conditions:
   ```powershell
   # --- progress ingest (one per file) ---
   & $pythonExe $writerPath progress ingest `
       --savedata $savedataRoot --course {course_id} --unit {unit_slug} | Out-Null ;
   # --- log entry (one per affected course) ---
   & $pythonExe $writerPath log entry `
       --savedata $savedataRoot --course {course_id} `
       --entry "- [INGEST] {N} file(s) -> {unit(s)}: {filenames, comma-separated}" | Out-Null
   ```

---

## Syllabus Processing Branch

Entered from step 4 above when: file type = `syllabus` AND `course_structure.json` has no units.

1. **Extract from syllabus text**:
   - Course code and name
   - Semester
   - Instructor name
   - Grading breakdown (components + weights)
   - Unit/topic structure (week schedule → logical units)
   - Exam/quiz schedule (titles, dates, times, locations, coverage)
   - Assignment and lab deadlines

2. **Build `course_structure.json`**: Map weeks → units. Extract 8-15 subject-specific keywords per unit (terminology, procedure names, key concepts). Drive course ID and unit assignment.

3. **Initialize `progress.json`**: Per unit: `status: "not_started"`, `materials_ingested: 0`, `quiz_history: []`, `weak_areas: []`, `confidence_level: 0`.

4. **Write deadlines** to `data\global_deadlines.json`. Apply duplicate detection (Section 6 of CLAUDE.md).

5. **Update `courses_index.json`**: Set `syllabus_ingested: true` directly on the course entry.

6. **Write `courses\{slug}\materials\syllabus\course_overview.md`**:
   ```markdown
   # {Course Code} — {Course Name}
   **Semester**: {semester} | **Instructor**: {instructor} | **Ingested**: {date}

   ## Grading
   | Component | Weight | Notes |
   |-----------|--------|-------|
   | {component} | {pct}% | |

   ## Unit Structure
   | Unit | Weeks | Topics | Exam |
   |------|-------|--------|------|
   | Unit 1: {name} | Week 1-3 | {topics} | Exam 1 |

   ## Exam & Quiz Schedule
   | Assessment | Covers | Date | Time | Location |
   |------------|--------|------|------|----------|
   | Exam 1 | Units 1-2 | May 21 | 10:00 | GH 150 |

   ## Key Policies
   [Attendance, late policy, exam format, anything that affects grades]
   ```

7. **Ensure `misc.md` and `activity_log.md` exist**: Course created inline (not via `/lkcourse add`) → create both using the `/lkcourse add` templates in Section 6 of CLAUDE.md (steps 6–7).

8. **Confirm**:
   ```
   Syllabus processed — {course_code}
   Units loaded   : {N}
   Deadlines added: {N} ({breakdown, e.g. 2 exams, 1 lab practical, 1 assignment})
   Next exam      : {title} on {date} ({N} days)
   ```

9. **Unclassified materials exist**: `"You have N unclassified files from before syllabus load. Re-classify now? [Y/n]"` Y → run unit identification against new keywords, move to correct folders.

Return to main pipeline at step 7 (generate study notes) after branch completes.

---

**Edge cases:**
- **Path doesn't exist**: `Test-Path` before processing → `"File not found: {path}" — skipped`
- **Unsupported type** (.xlsx, .zip, etc.): Report and skip.
- **Python fails**: Report error, skip file, continue. First file fails with env error → stop and ask user to check Python path via `/lksetup`.
- **No course structure**: Ingest but assign to `unclassified`. Note: `"No course structure for {course_code} — filed as unclassified. Ingest syllabus to enable unit assignment."`
- **Scanned PDF**: Detected when text yield < 50 words/page. Pages converted to images by `extract_text.py`, read by agent via Read tool. Notes generated from visual content. First line of notes: `**Source**: {filename} | **Unit**: {unit} | **Type**: {type} | **Ingested**: {date} | **Note**: Scanned PDF — content read from page images`
