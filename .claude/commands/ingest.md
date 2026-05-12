Base context (path variables, schemas, behavioral rules, Section 1 tagging, Section 11 logging) loaded from CLAUDE.md.

## `/ingest` — Process new course materials

**Two input methods — same pipeline:**

**Method A: `raw\` folder**
Drop files in `savedata\raw\`, run `/ingest`. Move each file out after success.

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

1. **Extract text**: Run `scripts\extract_text.py` (via $pythonExe and $scriptsRoot — see Section 9 of CLAUDE.md). Fails → report error and skip; don't continue with that file.
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

4. **If syllabus**: Check if `course_structure.json` has units populated. No → run Section 7 (CLAUDE.md). Yes → offer to update.

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
   Option 2 → `courses\{slug}\materials\multi_unit\`. `/study` and `/quiz` for any relevant unit includes `multi_unit\` files.

6. **Archive original**:
   - `raw\` method: `Move-Item` from `$savedataRoot\raw\{filename}` → `$savedataRoot\courses\{slug}\materials\{unit_slug}\source_{slug}.{ext}`
   - Path-paste: `Copy-Item` → same destination (original untouched)

7. **Generate grade-focused study notes** → `courses\{slug}\materials\{unit_slug}\{type}_{slug}.md`
   - First line: `**Source**: {filename} | **Unit**: {unit display name} | **Type**: {file_type} | **Ingested**: {date}`
   - Apply Section 1 tagging per topic
   - Group by learning objective if syllabus provides them
   - Include "Key Terms" section with definitions tagged by exam probability
   - Include "Likely Quiz/Exam Questions" section at end

8. **Update data files** via `data_writer.py` (run for each successfully ingested file):

   ```powershell
   # Register file in manifest
   $result = (& $pythonExe $writerPath manifest add `
       --savedata $savedataRoot --course-id {course_id} --course-code {course_code} `
       --filename {original_filename} --method {raw_folder|path_paste} `
       [--original-path {abs_path}] --file-type {file_type} --unit {unit_slug} `
       --confidence {high|medium|low|user_assigned} `
       --filed-path {relative_filed_path} --summary-path {relative_summary_path} `
       [--page-count N] [--word-count N]) | ConvertFrom-Json

   # Increment materials_ingested (advances not_started → in_progress)
   $result = (& $pythonExe $writerPath progress ingest `
       --savedata $savedataRoot --course {course_id} --unit {unit_slug}) | ConvertFrom-Json

   # Recalculate units_completed + next_deadline in courses_index
   $result = (& $pythonExe $writerPath index update `
       --savedata $savedataRoot --course {course_id}) | ConvertFrom-Json
   ```

   After all files processed, write log (one call per course, grouped):
   ```powershell
   $result = (& $pythonExe $writerPath log entry `
       --savedata $savedataRoot --course {course_id} `
       --entry "- [INGEST] {course_code} | {N} file(s) → {unit(s)}: {filenames}") | ConvertFrom-Json
   ```

9. **Ingestion report**:
   ```
   Ingestion complete — 4 files processed
   ──────────────────────────────────────────────────────
   BIOL 201 — Introductory Cell Biology
     ✓ biol201_syllabus.pdf         → syllabus (course structure loaded: 6 units)
     ✓ Week3_CellCycle.pptx         → Unit 2 — lecture_slides (45 slides, 3,200 words)
   COMP 361
     ✓ lab_report_template.docx     → Unit 1 — assignment
   Skipped
     ✗ random_notes.txt             → could not identify course (user skipped)
   ──────────────────────────────────────────────────────
   ```

10. **Write log entries** after report. One entry per course (grouped) to both `data\activity_log.md` and each affected course's `activity_log.md`. See Section 11 of CLAUDE.md.

**Edge cases:**
- **Path doesn't exist**: `Test-Path` before processing → `"File not found: {path}" — skipped`
- **Unsupported type** (.xlsx, .zip, etc.): Report and skip.
- **Python fails**: Report error, skip file, continue. First file fails with env error → stop and ask user to check Python path via `/setup`.
- **No course structure**: Ingest but assign to `unclassified`. Note: `"No course structure for {course_code} — filed as unclassified. Ingest syllabus to enable unit assignment."`
- **Scanned PDF**: Detected when text yield < 50 words/page. Pages converted to images by `extract_text.py`, read by agent via Read tool. Notes generated from visual content. First line of notes: `**Source**: {filename} | **Unit**: {unit} | **Type**: {type} | **Ingested**: {date} | **Note**: Scanned PDF — content read from page images`
