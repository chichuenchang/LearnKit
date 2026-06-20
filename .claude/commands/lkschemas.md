Standalone data schema reference. Read before querying or interpreting JSON data files.

## `data\courses_index.json` (global)
**active_courses[]**: `course_id`, `course_code`, `course_name`, `semester`, `folder` (relative), `status: "active"`, `created_date`, `syllabus_ingested` (bool)
**archived_courses[]**: `course_id`, `course_code`, `course_name`, `semester`, `folder`, `status: "archived"`, `archived_date`
Default empty: `{"last_updated": null, "active_courses": [], "archived_courses": []}`

## Per-course `data\course_structure.json`
**top-level**: `unit_label` — display label for `display_name` gen and `unit_id` prefix. Valid values (default `"Unit"`). `image_quiz_ratio` (float 0–1, default `null`) — fraction of quiz questions that should be image-based; `null` → agent estimates from scope image-richness.

| `unit_label` | `unit_id` prefix |
|---|---|
| `"Unit"` | `unit_NN` |
| `"Week"` | `week_NN` |
| `"Chapter"` | `chap_NN` |
| `"Module"` | `mod_NN` |
| `"Topic"` | `topic_NN` |
| `"Lecture"` | `lec_NN` |
| `"Book"` | `book_NN` |

**units[]**: `unit_id`, `display_name`, `slug`, `weeks` (array), `topics` (array), `associated_exams` (array), `keywords` (8–15 subject-specific terms — drives unit assignment)
**exams[]**: `exam_id`, `title`, `units_covered` (array), `date`, `time`, `location`
Default empty: `{"course": null, "course_id": null, "unit_label": "Unit", "image_quiz_ratio": null, "built_from": null, "last_updated": null, "units": [], "exams": []}`

## Per-course `data\problem_pool.json`
Past quiz/exam problems. Served verbatim by `/lkquiz`; used as style exemplars to generate gap-filling questions. Written only via `data_writer.py pool add` / `pool remove`.

**top-level**: `course`, `course_id`, `last_updated`, `problems[]`
**problems[]**: `problem_id` (`prob_{course_id}_{NNN}`), `unit_id` (or null), `unit_slug` (or null), `topic` (subject-specific topic term), `question_type` (`mcq` | `short_answer` | `matching` | `labeling` | `true_false` | `essay`), `question`, `options` (array; `[]` unless mcq), `answer`, `rationale` (or null), `tags` (Section 1 tags), `source` (label e.g. "Midterm 1 2025"), `source_file` (filename or "manual"), `source_type` (`past_exam` | `practice_quiz` | `exam_review` | `manual`), `verbatim` (bool), `figure` (or null), `date_added`
**figure** (image-based problems, else null): `image_path` (PNG under `materials\{unit}\images\`), `bbox` (normalized `[x,y,w,h]` display crop, or null = whole image), `caption`. Served as HTML quiz via `image_quiz.py` (figure embedded; no mask). Persisted by `pool add` only when `image_path` present.
Default empty: `{"course": null, "course_id": "<slug>", "last_updated": null, "problems": []}` (`course_id` seeded with course slug on first `pool add`)

## Per-course `data\image_bank.json`
Labeled diagrams/figures extracted during ingest (any subject — anatomy, chemistry, geography, circuits, …). Image + label positions for `/lkimage` review and (Phase 2) occlusion quizzes. Written only via `data_writer.py image add` / `image remove`.

**top-level**: `course`, `course_id`, `last_updated`, `images[]`
**images[]**: `image_id` (`img_{course_id}_{NNN}`), `unit_id`, `unit_slug`, `source_file`, `page` (1-based), `image_path` (under `materials\{unit}\images\`), `image_w`, `image_h` (pixels), `title`, `label_source` (`textlayer` | `ocr` | `vision` | `none`), `structures[]`, `date_added`
**structures[]**: `name`, `type` (free-form, course-appropriate — e.g. `bone`, `country`, `component`, `functional group`; or null), `source` (`slide` = printed/grounded | `ai` = flagged, show `[AI — verify]`), `label_bbox` (normalized `[x,y,w,h]` 0–1 of label text, or null), `confidence` (0–1 or null), `verified` (bool; true for slide)
Default empty: `{"course": null, "course_id": "<slug>", "last_updated": null, "images": []}` (`course_id` seeded with course slug on first `image add`)
Dedup key: `(source_file, page, image_path)` — same page may yield multiple distinct crops.
