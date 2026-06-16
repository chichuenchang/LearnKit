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
   - `scanned: true` → read each path in `data.image_paths` via Read tool; generate study notes from visual page content; clean up the page-image dir `data.pages_dir` after notes written
   - `capped: true` → surface before proceeding: `"Note: {filename} has {page_count} pages — first 20 ingested. Re-ingest and confirm to process remaining pages."`

2. **Identify course**: Section 4 logic (CLAUDE.md).

3. **Classify file type** from filename + first 2,000 chars:
   - `syllabus` — "syllabus", "course outline", course code + "course"
   - `lecture_slides` — "lecture", ".pptx", slide deck structure
   - `lab_notes` — "lab", "laboratory"
   - `practice_quiz` — "quiz", "practice questions", "sample questions"
   - `exam_review` — "exam review", "study guide", "review sheet"
   - `past_exam` — "midterm", "final", past "exam" with discrete numbered/lettered question structure (distinct from `exam_review`, which is a prose study guide)
   - `assignment` — "assignment", "submit", "due date"
   - `announcement` — "announcement", "reminder", "please note", deadline language without study content
   - `other` — anything else

4. **If syllabus**: Check if `course_structure.json` has units populated. No → run **Syllabus Processing Branch** (below). Yes → offer to update.

5. **Identify unit** (non-syllabus): Compare text vs `keywords` in all units of `course_structure.json`. Assign highest overlap (minimum 2 matches). File spans multiple units → ask:
   ```
   "[filename]" appears to span multiple units.
     {display_name} — Cell Structure: 12 keyword matches
     {display_name} — Cell Cycle: 9 keyword matches
     {display_name} — Genetics: 7 keyword matches

   Options:
     [1] Assign to {display_name} (highest overlap) — add cross-reference notes to others
     [2] File under multi_unit\ folder
     [3] Assign to a specific unit (type unit ID):
   ```
   Option 1 → primary unit; add `_cross_ref_{slug}.md` in each other unit: `See also: [path to primary summary]`.
   Option 2 → `courses\{slug}\materials\multi_unit\`. `/lkquiz` for any relevant unit includes `multi_unit\` files.

6. **Archive original** — the source lives in the per-course **raw archive ONLY**. `materials\` holds generated study notes + an `images\` subfolder, **never source files**.
   - `raw\` method: `Move-Item` from `$savedataRoot\raw\{filename}` → `$savedataRoot\courses\{slug}\raw\{unit_slug}\source_{slug}.{ext}`
   - Path-paste: `Copy-Item` → `$savedataRoot\courses\{slug}\raw\{unit_slug}\source_{slug}.{ext}` (original untouched)
   - The `raw\` archive mirrors the unit structure — subfolders are `{unit_slug}` (weeks/units/chapters per the course's `unit_label`, chosen at course/syllabus setup). Multi-unit files → `raw\multi_unit\`; unclassified → `raw\unclassified\`.

7a. **Render pages** (PDFs only): Run `image_extract.py --file {source} --out {scriptsRoot}\tmp_pages` (see lkscripts.md) → page PNGs in `pages_dir` + per-page label boxes (PaddleOCR / text-layer). These pages feed BOTH the image bank (7b) and the note figures (7c). Keep `pages_dir` until step 8 cleanup. Non-PDF → skip 7a–7b (no figures/illustrations).

7b. **Capture labeled diagrams/figures to the image bank** (PDFs only): from the 7a pages, for each page that is a **labeled diagram or figure** — any subject (anatomy, chemistry, geography, circuits, maps, …) — (skip title / text-only / summary pages):
   - Save the page PNG → `materials\{unit_slug}\images\{source_slug}_p{NN}.png`.
   - From the detected `words` (text-layer or OCR boxes), keep those that label a part/region/term: record `name`, `bbox`, `confidence`, a free-form subject-appropriate `type` (e.g. `bone`, `country`, `component`, `functional group`; or null), `source:"slide"`.
   - Add notable UNlabeled structures as `source:"ai"`, `verified:false`, `label_bbox:null` (Rule 9a — flagged, `[AI — verify]`). Never override a printed label or invent coordinates.
   - Set `title` (slide heading) and `label_source` (the page's `source`). Build one JSON array of all kept pages → single `image add` call (see lkscripts.md). Surface: `"Captured {N} illustration(s) — {S} slide labels, {A} AI-flagged."` No illustration pages → skip silently.

7c. **Generate the image-rich study note** and write via `notes_embed.py` (no Write tool): write a grade-focused, Section-1-tagged note. Inline — where a diagram illustrates the text — drop a figure placeholder cropped to that single figure (on 2-up handout pages, top slide ≈ `0,0,1,0.5`, bottom slide ≈ `0,0.5,1,0.5`; tighten as needed):
   ```
   {{FIG: {pages_dir}\page_{NN}.png | x,y,w,h | caption}}
   ```
   `x,y,w,h` = crop box **normalized 0–1** on that page image.
   - First line: `**Source**: {filename} | **Course**: {course_code} | **Unit**: {unit display name} | **Ingested**: {date} | **Raw material**: raw/{unit_slug}/source_{slug}.{ext}`, then `---`, then the body with `{{FIG}}` placeholders + Section 1 tagging. The `**Raw material**:` value points to the raw archive (step 6); multi-unit → `raw/multi_unit/...`, unclassified → `raw/unclassified/...`.
   - Pipe to `notes_embed.py` → self-contained `.md` (figures become inline base64):
   ```powershell
   $notesContent = @'
   {full note content with {{FIG: ...}} placeholders}
   '@
   $notesContent | & $pythonExe (Join-Path $scriptsRoot "notes_embed.py") `
       --dest "{$savedataRoot}\courses\{course_id}\materials\{unit_slug}\{type}_{slug}.md" | Out-Null
   ```
   - Non-PDF / no relevant figures → write the note with no `{{FIG}}` tokens (notes_embed passes it through). `notes_embed.py` replaces `notes write` for ALL note writing.

7d. **Extract problems to the pool** (only when file type ∈ `{practice_quiz, exam_review, past_exam}`): Scan the extracted text for discrete Q+A pairs. None found (prose study guide) → skip, notes only. For each problem found:
   - Map to a unit by keyword overlap (same logic as step 5). Unmappable → `unit_id`/`unit_slug` null.
   - Assign a `topic` label from the unit's `topics` / weak-topic vocabulary.
   - Set `question_type`, `options` (mcq only), `answer`, optional `rationale` and Section 1 `tags`. All content strictly from the file — no invented problems (Rule 9).
   - Set `source_type` = file classification, `verbatim: true`, `source_file` = ingested filename, `source` = inferred label (e.g. "Practice Quiz — Week 3").

   Build one JSON array of all problems and write via a single `pool add` call (see lkscripts.md). Surface: `"Extracted {added} problem(s) to {course_code} pool ({skipped} duplicate(s) skipped)."`

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
   When step 7d added problems, also log per affected course: `- [POOL] Extracted {N} problem(s) from {filename} -> {unit(s)}`.
   When step 7b captured illustrations, also log per course: `- [IMAGE] Captured {N} illustration(s) from {filename} -> {unit}`.
   Finally, clean up the 7a render dir (`pages_dir` from `image_extract.py`).

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
   - **Determine `unit_label` field**: Count occurrences of each label pattern in syllabus text: "Week N", "Unit N", "Chapter N", "Module N", "Topic N", "Lecture N", "Book N". Highest-frequency label wins if it accounts for >60% of matches → set automatically (note: `"Auto-detected: {label}-based organization"`). Otherwise ask:
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
   - **Generate `display_name`**: Use `"{unit_label} N: {title}"` — e.g. `"Week 1: Vertebral Column"`, `"Chapter 3: Enzymes"`.
   - **Generate `unit_id`**: Derive prefix from `unit_label` using the mapping in lkschemas.md (e.g. `"Week"` → `week_NN`, `"Chapter"` → `chap_NN`). Zero-padded two digits.

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
   | {Unit/Week} | Weeks | Topics | Exam |
   |-------------|-------|--------|------|
   | {display_name} | Week 1-3 | {topics} | Exam 1 |

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
- **Scanned PDF**: Detected when text yield < 50 words/page. Pages converted to images by `extract_text.py`, read by agent via Read tool. Notes generated from visual content. First line of notes: `**Source**: {filename} | **Unit**: {unit} | **Type**: {type} | **Ingested**: {date} | **Raw material**: raw/{unit_slug}/source_{slug}.{ext} | **Note**: Scanned PDF — content read from page images`
