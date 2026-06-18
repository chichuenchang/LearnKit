Base context (path vars, behavioral rules, Section 1 tagging) from CLAUDE.md. Schemas: lkschemas.md. Python protocol + data_writer.py: lkscripts.md. Log format: lklogging.md.

## Guiding principle — study experience first

Human crams from note alone — judge: *"can I learn topic from note alone?"* **Images are why pipeline exists**: visual subjects (esp. anatomy) — labeled figures beat prose. Make notes image-rich — embed every helpful figure, capture labeled diagrams to bank generously, never drop figures to chase text/fidelity metric (patch text instead). Rule 9 still governs text claims.

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

**Shared pipeline per file:**

0. **Auto-split large PDFs** (PDFs only): Run `pdf_split.py --file {source} --out {scriptsRoot}\tmp_split` (lkscripts.md). `split: true` → treat each `parts[]` entry as own file through steps 1–7 (text, figures, note, problems) — all parts share source's course + unit; give each part-suffixed source slug (e.g. `source_x_part02`) so image-bank/pool dedup stays unique; tag note title `Part {index}/{part_count}` (pages {from_page}–{to_page}). Archive **original** once to raw (step 6); part PDFs derived, not archived. Announce: `"{filename} has {page_count} pages — split into {part_count} parts of ≤{chunk}; ingesting each."` `split: false` → continue single file unchanged. Threshold/chunk = `auto_split_pages` (config.json, default 60). Non-PDF → skip. Clean `tmp_split` at step 8.

1. **Extract text**: Run `scripts\extract_text.py` (via $pythonExe and $scriptsRoot — `lkscripts.md`). Fails → report error, skip; don't continue that file.
   - `scanned: false` → use `data.text` normally for all downstream steps
   - `scanned: true` → read each `data.image_paths` path via Read tool; generate notes from visual page content; clean page-image dir `data.pages_dir` after notes written
   - `capped: true` → only fires if auto-split off (`auto_split_pages: 0`) or single part still exceeds render cap; surface: `"Note: {filename} has {page_count} pages — first 60 ingested. Re-ingest with --max-pages 0 (or higher N) to process all pages."`
   - `file_type: "html"` → `data.text` is readable text; `data.images[]` (`{path, alt}`, saved in `data.pages_dir`) are figures — **no** 7a render for HTML, these `images` replace it (feed note 7c, image bank 7b, figure-problems 7d). Surface if `data.images_skipped > 0`: `"Note: {N} image(s) skipped (remote URLs / SVG) — for image-rich quizzes, Save-as-PDF gives more reliable figures."` Before step 8 cleanup of `data.pages_dir`, copy any kept image to `materials\{unit_slug}\images\`.

2. **Identify course**: Section 4 logic (CLAUDE.md).

3. **Classify file type** from filename + first 2,000 chars:
   - `syllabus` — "syllabus", "course outline", course code + "course"
   - `lecture_slides` — "lecture", ".pptx", slide deck structure
   - `lab_notes` — "lab", "laboratory"
   - `practice_quiz` — "quiz", "practice questions", "sample questions"
   - `exam_review` — "exam review", "study guide", "review sheet"
   - `past_exam` — "midterm", "final", past "exam" with discrete numbered/lettered question structure (distinct from `exam_review`, a prose study guide)
   - `assignment` — "assignment", "submit", "due date"
   - `announcement` — "announcement", "reminder", "please note", deadline language without study content
   - `other` — anything else

4. **If syllabus**: Check `course_structure.json` units populated. No → run **Syllabus Processing Branch** (below). Yes → offer update.

5. **Identify unit** (non-syllabus): Compare text vs `keywords` in all `course_structure.json` units. Assign highest overlap (min 2 matches). Spans multiple units → ask:
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

6. **Archive original** — source lives in per-course **raw archive ONLY**. `materials\` holds generated notes + `images\` subfolder, **never source files**.
   - `raw\` method: `Move-Item` from `$savedataRoot\raw\{filename}` → `$savedataRoot\courses\{slug}\raw\{unit_slug}\source_{slug}.{ext}`
   - Path-paste: `Copy-Item` → `$savedataRoot\courses\{slug}\raw\{unit_slug}\source_{slug}.{ext}` (original untouched)
   - `raw\` archive mirrors unit structure — subfolders are `{unit_slug}` (weeks/units/chapters per course's `unit_label`, chosen at course/syllabus setup). Multi-unit → `raw\multi_unit\`; unclassified → `raw\unclassified\`.

7a. **Render pages** (PDFs only): Run `image_extract.py --file {source} --out {scriptsRoot}\tmp_pages` (lkscripts.md) → page PNGs in `pages_dir` + per-page label boxes (PaddleOCR / text-layer). Pages feed BOTH image bank (7b) and note figures (7c). Keep `pages_dir` until step 8 cleanup. **HTML** → skip render; use `data.images[]` from step 1 as figures (each whole standalone image, no label boxes). Other non-PDF (pptx/docx/txt/md) → skip 7a–7b (no figures).

7b. **Capture labeled diagrams/figures to image bank** (PDFs only): from 7a pages, for each page that is a **labeled diagram or figure** — any subject (anatomy, chemistry, geography, circuits, maps, …) — (skip title / text-only / summary pages):
   - Save page PNG → `materials\{unit_slug}\images\{source_slug}_p{NN}.png`.
   - From detected `words` (text-layer or OCR boxes), keep those labeling a part/region/term: record `name`, `bbox`, `confidence`, free-form subject-appropriate `type` (e.g. `bone`, `country`, `component`, `functional group`; or null), `source:"slide"`.
   - Add notable UNlabeled structures as `source:"ai"`, `verified:false`, `label_bbox:null` (Rule 9a — flagged, `[AI — verify]`). Never override printed label or invent coordinates.
   - Set `title` (slide heading) and `label_source` (page's `source`). Build one JSON array of all kept pages → single `image add` call (lkscripts.md). Surface: `"Captured {N} illustration(s) — {S} slide labels, {A} AI-flagged."` No illustration pages → skip silently.
   - **HTML source**: instead of 7a pages, use `data.images[]`. Each figure worth banking → copy to `materials\{unit_slug}\images\`, add record with `label_source:"none"`, `image_path` = copied PNG, `title` from nearby heading / `alt` text; no text-layer boxes (structures may be AI-flagged per Rule 9a). Same single `image add` call.

7c. **Generate image-rich study note**, write via `notes_embed.py` (no Write tool): grade-focused, Section-1-tagged note. Inline — where diagram illustrates text — drop figure placeholder cropped to that single figure (2-up handout pages: top slide ≈ `0,0,1,0.5`, bottom slide ≈ `0,0.5,1,0.5`; tighten as needed):
   ```
   {{FIG: {pages_dir}\page_{NN}.png | x,y,w,h | caption}}
   ```
   `x,y,w,h` = crop box **normalized 0–1** on that page image.
   - First line: `**Source**: {filename} | **Course**: {course_code} | **Unit**: {unit display name} | **Ingested**: {date} | **Raw material**: raw/{unit_slug}/source_{slug}.{ext}`, then `---`, then body with `{{FIG}}` placeholders + Section 1 tagging. `**Raw material**:` value points to raw archive (step 6); multi-unit → `raw/multi_unit/...`, unclassified → `raw/unclassified/...`.
   - Pipe to `notes_embed.py` → self-contained `.md` (figures become inline base64):
   ```powershell
   $notesContent = @'
   {full note content with {{FIG: ...}} placeholders}
   '@
   $notesContent | & $pythonExe (Join-Path $scriptsRoot "notes_embed.py") `
       --dest "{$savedataRoot}\courses\{course_id}\materials\{unit_slug}\{type}_{slug}.md" | Out-Null
   ```
   - **HTML source**: embed `data.images[]` with whole-image FIG tokens — `{{FIG: {image path} | 0,0,1,1 | caption}}` (no crop; use `alt` text or nearby heading as caption). Point at persisted `materials\...\images\` copies so self-contained `.md` survives `pages_dir` cleanup.
   - Non-PDF / no relevant figures → write note with no `{{FIG}}` tokens (notes_embed passes through). `notes_embed.py` replaces `notes write` for ALL note writing.

7d. **Extract problems to pool** (only when file type ∈ `{practice_quiz, exam_review, past_exam}`): Scan extracted text for discrete Q+A pairs. None found (prose study guide) → skip, notes only. Per problem found:
   - Map to unit by keyword overlap (step 5 logic). Unmappable → `unit_id`/`unit_slug` null.
   - Assign `topic` label from unit's `topics` / weak-topic vocabulary.
   - Set `question_type`, `options` (mcq only), `answer`, optional `rationale` and Section 1 `tags`. All content strictly from file — no invented problems (Rule 9).
   - Set `source_type` = file classification, `verbatim: true`, `source_file` = ingested filename, `source` = inferred label (e.g. "Practice Quiz — Week 3").
   - **Image-based problem** (figure part of question — diagram, X-ray, "identify the structure"): copy figure to **persistent** PNG under `materials\{unit_slug}\images\` (PDF → 7a page PNG, reuse 7b's; HTML → `data.images[]` file), set problem's `figure` (shape in lkschemas.md) with `image_path` = that PNG. Never reference `tmp_*` path (cleaned at step 8). Text-only → omit `figure`.

   Build one JSON array of all problems, write via single `pool add` call (lkscripts.md). Surface: `"Extracted {added} problem(s) to {course_code} pool ({skipped} duplicate(s) skipped, {F} with figures)."`

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
   Step 7d added problems → also log per affected course: `- [POOL] Extracted {N} problem(s) from {filename} -> {unit(s)}`.
   Step 7b captured illustrations → also log per course: `- [IMAGE] Captured {N} illustration(s) from {filename} -> {unit}`.
   Finally clean temp render dirs: 7a render dir (`pages_dir` from `image_extract.py`), HTML image dir (`data.pages_dir` from `extract_text.py`, under `tmp_html`), and `tmp_split` dir if step 0 split. Persisted figures already live under `materials\...\images\`.

---

## Syllabus Processing Branch

Entered from step 4 when: file type = `syllabus` AND `course_structure.json` has no units.

1. **Extract from syllabus text**:
   - Course code and name
   - Semester
   - Instructor name
   - Grading breakdown (components + weights)
   - Unit/topic structure (week schedule → logical units)
   - Exam/quiz schedule (titles, dates, times, locations, coverage)
   - Assignment and lab deadlines

2. **Build `course_structure.json`**: Map weeks → units. Extract 8-15 subject-specific keywords per unit (terminology, procedure names, key concepts). Drive course ID and unit assignment.
   - **Determine `unit_label` field**: Count occurrences of each label pattern in syllabus text: "Week N", "Unit N", "Chapter N", "Module N", "Topic N", "Lecture N", "Book N". Highest-frequency label wins if >60% of matches → set automatically (note: `"Auto-detected: {label}-based organization"`). Else ask:
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
   - **Generate `display_name`**: `"{unit_label} N: {title}"` — e.g. `"Week 1: Vertebral Column"`, `"Chapter 3: Enzymes"`.
   - **Generate `unit_id`**: Derive prefix from `unit_label` per mapping in lkschemas.md (e.g. `"Week"` → `week_NN`, `"Chapter"` → `chap_NN`). Zero-padded two digits.

3. **Initialize `progress.json`**: Per unit: `status: "not_started"`, `materials_ingested: 0`, `quiz_history: []`, `weak_areas: []`, `confidence_level: 0`.

4. **Write deadlines** to `data\global_deadlines.json`. Apply duplicate detection (Section 6, CLAUDE.md).

5. **Update `courses_index.json`**: Set `syllabus_ingested: true` on course entry.

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

7. **Ensure `misc.md` and `activity_log.md` exist**: Course created inline (not via `/lkcourse add`) → create both using `/lkcourse add` templates in Section 6, CLAUDE.md (steps 6–7).

8. **Confirm**:
   ```
   Syllabus processed — {course_code}
   Units loaded   : {N}
   Deadlines added: {N} ({breakdown, e.g. 2 exams, 1 lab practical, 1 assignment})
   Next exam      : {title} on {date} ({N} days)
   ```

9. **Unclassified materials exist**: `"You have N unclassified files from before syllabus load. Re-classify now? [Y/n]"` Y → run unit identification against new keywords, move to correct folders.

Return to main pipeline at step 7 (generate notes) after branch completes.

---

**Edge cases:**
- **Path doesn't exist**: `Test-Path` before processing → `"File not found: {path}" — skipped`
- **Unsupported type** (.xlsx, .zip, etc.): Report and skip.
- **Python fails**: Report error, skip file, continue. First file fails with env error → stop, ask user to check Python path via `/lksetup`.
- **No course structure**: Ingest but assign to `unclassified`. Note: `"No course structure for {course_code} — filed as unclassified. Ingest syllabus to enable unit assignment."`
- **Scanned PDF**: Detected when text yield < `scanned_words_per_page_threshold` words/page (config.json, default 50). Pages converted to images by `extract_text.py`, read by agent via Read tool. Notes generated from visual content. First line of notes: `**Source**: {filename} | **Unit**: {unit} | **Type**: {type} | **Ingested**: {date} | **Raw material**: raw/{unit_slug}/source_{slug}.{ext} | **Note**: Scanned PDF — content read from page images`
