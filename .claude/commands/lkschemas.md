Standalone data schema reference. Read this file when querying or interpreting JSON data files.

## `data\courses_index.json` (global)
**active_courses[]**: `course_id`, `course_code`, `course_name`, `semester`, `folder` (relative), `status: "active"`, `created_date`, `syllabus_ingested` (bool)
**archived_courses[]**: `course_id`, `course_code`, `course_name`, `semester`, `folder`, `status: "archived"`, `archived_date`
Default empty: `{"last_updated": null, "active_courses": [], "archived_courses": []}`

## `data\global_deadlines.json` (global)
**deadlines[]**: `id`, `course_id`, `course_code`, `type`, `title`, `date`, `time`, `location`, `details`, `source_date`, `completed` (bool)
Valid `type`: `exam`, `quiz`, `assignment`, `lab`, `lab_practical`, `presentation`, `other`
Default empty: `{"last_updated": null, "deadlines": []}`

## `data\materials_manifest.json` (global)
**files[]**: `manifest_id`, `course_id`, `course_code`, `original_filename`, `ingestion_method` (`"raw_folder"` or `"path_paste"`), `original_path` (null if raw_folder), `ingestion_date`, `file_type`, `unit_assigned` (slug, `"unclassified"`, `"multi_unit"`, or `"syllabus"`), `confidence` (`"high"`, `"medium"`, `"low"`, `"user_assigned"`), `filed_path`, `summary_path`, `page_count`, `word_count`, `summary_generated` (bool)
Default empty: `{"last_updated": null, "total_files": 0, "files": []}`

## Per-course `data\course_structure.json`
**units[]**: `unit_id`, `display_name`, `slug`, `weeks` (array), `topics` (array), `associated_exams` (array), `keywords` (8–15 subject-specific terms — drives unit assignment and adaptive quiz weighting)
**exams[]**: `exam_id`, `title`, `units_covered` (array), `date`, `time`, `location`
Default empty: `{"course": null, "course_id": null, "built_from": null, "last_updated": null, "units": [], "exams": []}`

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
