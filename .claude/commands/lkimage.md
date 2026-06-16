Base context (path variables, behavioral rules) loaded from CLAUDE.md. Data schemas in lkschemas.md. Python script protocol and data_writer.py reference in lkscripts.md. Log entry format spec in lklogging.md.

## `/lkimage` — Image bank (Phase 1: review)

Reviews each course's `data\image_bank.json` — labeled diagrams/figures captured during ingest (any subject: anatomy, chemistry, geography, circuits, maps, …). Image labels are either printed slide labels (`[slide]`, grounded) or AI-identified (`[AI — verify]`, flagged). All writes go through `data_writer.py` `image add` / `image remove` (Rule 15). Multiple active courses + none specified → ask (Rule 2). Never mix courses (Rule 1). Missing `image_bank.json` → treat as empty.

### `/lkimage {course}` — summary
Read `course_structure.json` and `image_bank.json`. Print:
- Total illustrations + total structures (slide vs AI tally).
- Breakdown by unit (`display_name` → image count); units with 0 images.

```
PTHER 350A — Image Bank
Total: 12 illustrations · 84 structures (71 slide · 13 AI)
──────────────────────────────────────────────
  Week 6: Foot         12   (Bones 4, Joints 5, Arches 0, Plantar 3)
  Week 1–5             0    (none captured)
```

### `/lkimage {course} {scope}` — review
For each image whose `unit_id` ∈ scope, print: the **image file path** (user opens it), `title`, and the structure list as `name · type · [slide]` or `name · type · [AI — verify]`. Terminal cannot inline-render images, so give the path + the labels.

### `/lkimage {image_id}` — one image
Resolve the course from the id prefix (strip `img_` and trailing `_{NNN}`). Print that image's path, title, and full structure list.

### `/lkimage quiz {course} {scope}` — image MCQ quiz (Phase 2)
Generate a self-contained HTML page of "name the highlighted structure" MCQs (4 options A–D), open it in the browser. `{scope}` = same tokens as `/lkquiz` (`week_01`, ranges, lists, `exam_1`).

1. Read `image_bank.json`. **Eligible targets** = structures with `label_bbox != null` whose `unit_id` ∈ scope.
2. Pick up to ~15 targets, spread across images/units (cap at eligible count). 0 eligible → see Edge cases.
3. Per target build 4 **options**: the correct `name` + **3 distractors** — other structure names in scope, **prefer same `type`**; fall back to any scope names, then course-wide. Need ≥ 4 distinct names or skip that target. Shuffle; record `answer_index`.
4. Assemble a quiz-spec JSON and pipe it to `image_quiz.py` (see lkscripts.md):
   ```powershell
   $out = "{savedataRoot}\courses\{slug}\quiz\lkimage_quiz_{scope}_{YYYYMMDD}.html"
   $r = ($specJson | & $pythonExe (Join-Path $scriptsRoot "image_quiz.py") --out $out) | ConvertFrom-Json
   if ($r.success) { Start-Process $r.html_path }    # open in browser
   ```
5. Log per course: `- [IMAGE] Quiz generated — {N} Qs ({scope})`. No `progress.json` write (the page scores client-side).

**Edge cases**: 0 eligible targets → `"No image-bank questions for {scope}. Run /lkimage to check coverage."` · all `label_bbox` null (no OCR engine at capture) → `"No structures have label positions (boxes). Re-ingest with an OCR engine (PaddleOCR or Tesseract) installed to enable image quizzes."` · < 4 distinct names course-wide → `"Need at least 4 labeled structures to build options."`

### `/lkimage remove {image_id}` — delete a bad capture
Resolve course from the id, confirm, then `data_writer.py image remove`. Log: `[IMAGE] Removed {image_id}`.
