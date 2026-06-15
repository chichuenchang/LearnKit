Standalone data schema reference. Read this file when querying or interpreting JSON data files.

## `data\courses_index.json` (global)
**active_courses[]**: `course_id`, `course_code`, `course_name`, `semester`, `folder` (relative), `status: "active"`, `created_date`, `syllabus_ingested` (bool)
**archived_courses[]**: `course_id`, `course_code`, `course_name`, `semester`, `folder`, `status: "archived"`, `archived_date`
Default empty: `{"last_updated": null, "active_courses": [], "archived_courses": []}`

## `data\global_deadlines.json` (global)
**deadlines[]**: `id`, `course_id`, `course_code`, `type`, `title`, `date`, `time`, `location`, `details`, `source_date`, `completed` (bool)
Valid `type`: `exam`, `quiz`, `assignment`, `lab`, `lab_practical`, `presentation`, `other`
Default empty: `{"last_updated": null, "deadlines": []}`

## Per-course `data\course_structure.json`
**top-level**: `unit_label` — display label used in `display_name` generation, `unit_id` prefix, and quiz filenames. Valid values (default `"Unit"`):

| `unit_label` | `unit_id` prefix | quiz short code |
|---|---|---|
| `"Unit"` | `unit_NN` | `u01` |
| `"Week"` | `week_NN` | `w01` |
| `"Chapter"` | `chap_NN` | `ch01` |
| `"Module"` | `mod_NN` | `m01` |
| `"Topic"` | `topic_NN` | `t01` |
| `"Lecture"` | `lec_NN` | `l01` |
| `"Book"` | `book_NN` | `b01` |

**units[]**: `unit_id`, `display_name`, `slug`, `weeks` (array), `topics` (array), `associated_exams` (array), `keywords` (8–15 subject-specific terms — drives unit assignment and adaptive quiz weighting)
**exams[]**: `exam_id`, `title`, `units_covered` (array), `date`, `time`, `location`
Default empty: `{"course": null, "course_id": null, "unit_label": "Unit", "built_from": null, "last_updated": null, "units": [], "exams": []}`

## Per-course `data\progress.json`
`status` progression: `not_started` → `in_progress` → `materials_complete` → `quiz_passed` → `mastered`

```json
{
  "course": null,
  "course_id": null,
  "last_updated": null,
  "weak_areas_global": [],
  "units": {
    "{unit_slug}": {
      "status": "not_started",
      "materials_ingested": 0,
      "confidence_level": 0,
      "weak_areas": [],
      "quiz_history": [
        {
          "quiz_id": "", "date": "", "score_pct": 0,
          "total_questions": 0, "correct": 0, "incorrect": 0, "skipped": 0,
          "partial": false, "adaptive_used": false,
          "weak_topics": [],
          "question_type_accuracy": {"mcq": "", "short_answer": ""}
        }
      ]
    }
  }
}
```

## Per-course `data\problem_pool.json`
Past quiz/exam problems. Served verbatim by `/lkquiz` and used as style exemplars to generate gap-filling questions. Written only via `data_writer.py pool add` / `pool remove`.

**top-level**: `course`, `course_id`, `last_updated`, `problems[]`
**problems[]**: `problem_id` (`prob_{course_id}_{NNN}`), `unit_id` (or null), `unit_slug` (or null), `topic` (same vocabulary as progress.json `weak_topics`), `question_type` (`mcq` | `short_answer` | `matching` | `labeling` | `true_false` | `essay`), `question`, `options` (array; `[]` unless mcq), `answer`, `rationale` (or null), `tags` (Section 1 tags), `source` (label e.g. "Midterm 1 2025"), `source_file` (filename or "manual"), `source_type` (`past_exam` | `practice_quiz` | `exam_review` | `manual`), `verbatim` (bool), `date_added`
Default empty: `{"course": null, "course_id": null, "last_updated": null, "problems": []}`
