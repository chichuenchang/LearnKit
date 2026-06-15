# Image MCQ Quiz — Phase 2 Design Spec

**Date**: 2026-06-15
**Status**: Approved (design), pending implementation plan
**Project**: LearnKit (PTStudy)
**Feature phase**: Phase 2 of the image-learning feature. Phase 1 (capture → `image_bank.json` + `/lkimage` review) is shipped. This phase = the **image MCQ quiz**.

---

## Goal

Turn the image bank into the exam format the user described: **show an image with one structure highlighted, ask "what is the name of the highlighted structure?", give 4 options (A–D), pick one.** Delivered as a **self-contained HTML page** opened in the browser (terminals can't render images inline), matching LearnKit's MCQ-default philosophy.

---

## Decisions (from brainstorm)

| Decision | Choice |
|----------|--------|
| Delivery | Self-contained **HTML page**, auto-opened in browser |
| Question format | **MCQ, 4 options A–D** — "name the highlighted structure" |
| Highlight | Mask the target's label text + draw a highlight marker; the slide's own **leader line stays**, pointing at the structure |
| Distractors | 3 other structure names in scope, **prefer same `type`**; fallback course-wide |
| Scoring | In-page JS score + summary; **no write-back** to `progress.json` (client-side page). LearnKit logs that a quiz was generated |
| Dependency | **Pillow** (already installed) — no new dep |

---

## Architecture (separation of concerns)

```
/lkimage quiz {course} {scope}
  │
  ├─ AGENT (Claude): judgment
  │    • read image_bank.json, filter to scope + eligible (label_bbox != null)
  │    • pick ~15 targets, spread across images/units
  │    • per target: build 4 options = correct label + 3 distractors
  │      (prefer same `type`, from scope → course-wide fallback), shuffle, note answer index
  │    • assemble a quiz-spec JSON
  │
  ├─ SCRIPT image_quiz.py: deterministic render
  │    • per question: load image_path, mask+highlight target_bbox (Pillow),
  │      base64-encode, embed in HTML
  │    • render ONE self-contained .html (template + vanilla JS) with all cards
  │    • write to --out, print {success, html_path, question_count}
  │
  └─ AGENT: Start-Process the .html (opens browser) + log [IMAGE] Quiz generated
```

The agent does semantic work (selection, plausible distractors). The script does mechanical work (image masking, base64, HTML). Clean, testable boundary.

---

## 1 — Command: `/lkimage quiz {course} {scope}`

New variant on `/lkimage`. `{scope}` accepts the same tokens as `/lkquiz` (`week_01`, ranges, lists, `exam_1`). Resolves scope → unit list → images whose `unit_id` ∈ scope. Multi-course + none → ask. Empty/eligible-too-few → message (see Edge cases).

---

## 2 — `scripts/image_quiz.py` (new)

**Invocation:** `python image_quiz.py --out <html_path>` ; reads a **quiz-spec JSON on stdin**.

**Quiz-spec schema (stdin):**
```json
{
  "title": "PTHER 350A — Week 6: Foot (image quiz)",
  "questions": [
    {
      "image_path": "savedata/.../images/source_the_bones_of_the_foot_p05.png",
      "image_w": 1100, "image_h": 1500,
      "target_bbox": [0.62, 0.40, 0.10, 0.03],
      "stem": "What is the name of the highlighted structure?",
      "options": ["Talus", "Calcaneus", "Navicular", "Cuboid"],
      "answer_index": 0
    }
  ]
}
```

**Behavior per question:**
- Load `image_path` (Pillow). Denormalize `target_bbox` → pixel rect `(x*W, y*H, w*W, h*H)`.
- **Mask + highlight**: draw a filled rectangle over the label text (opaque, e.g. light gray), then a bright outline (e.g. red, 3px) around it and a `?` glyph centered — so the user sees WHICH item is asked. The slide's leader line (outside the box) is untouched and still points to the structure.
- Encode the modified image as PNG → base64 → `data:image/png;base64,...`.
- Emit a question block (image + stem + 4 lettered options) into the HTML; mark the correct option via `data-correct` on the `answer_index` option.

**Output:** writes the self-contained `.html` to `--out`; prints `{"success": true, "html_path": "...", "question_count": N}`. On error: `{"success": false, "error": "..."}`.

**Encoding note:** like `image_extract.py`, emit ASCII-safe JSON to stdout (`json.dumps` default) so option text with non-cp1252 glyphs never crashes a Windows console.

---

## 3 — HTML / JS (self-contained)

One file, no external assets, no network. Structure:
- `<style>`: card layout, option buttons, correct/incorrect colors, score bar, responsive image (`max-width:100%`).
- For each question: a `<section class="card">` with `<img src="data:image/png;base64,…">`, the stem, and 4 `<button class="opt">` (A/B/C/D + option text); the correct one carries `data-correct="1"`.
- `<script>` (vanilla JS): show one card at a time; on option click → lock the card, color chosen + correct, increment score on match, reveal a Next control; last card → show a **summary** (score `n/N`, %). A small progress indicator (`Q k / N`).
- Letters A–D rendered as labels; clicking is the answer (keyboard `a/b/c/d` also bound for convenience).

No build step, no framework. Plain HTML5 + inline CSS/JS.

---

## 4 — Agent responsibilities (in `lkimage.md`)

- **Eligibility**: a structure is a valid target only if `label_bbox != null` (need a box to mask/highlight). `source:"slide"` and `source:"ai"` (verified) both allowed if they have a box.
- **Selection**: up to ~15 targets across scope; spread across images and units; don't reuse the same target twice; cap at the number of eligible targets.
- **Distractors (per target)**: 3 names ≠ correct, drawn from other structures in scope; **prefer same `type`**; if fewer than 3 same-type available, fill from any scope names, then course-wide. Need ≥4 distinct names total or the question is skipped. Shuffle the 4; record `answer_index`.
- Assemble quiz-spec JSON; pipe to `image_quiz.py`; then `Start-Process {html_path}`; log.

---

## 5 — Storage, open, logging

- HTML saved to `savedata\courses\{slug}\quiz\lkimage_quiz_{scope}_{YYYYMMDD}.html`.
- Auto-open: `Start-Process "{html_path}"` (default browser).
- Log (per course): `- [IMAGE] Quiz generated — {N} Qs ({scope})`. (Reuses the existing `[IMAGE]` tag; add this phrasing to `lklogging.md`.)
- No `progress.json` write (the page is client-side; score lives in the browser). The user may report a score to log manually if desired.

---

## 6 — Edge cases

- **No images in scope** → `"No image-bank questions for {scope}. Ingest labeled diagrams first (/lkimage to check)."`
- **< 4 distinct names in scope** → pull distractors course-wide; if still < 4 total names in the whole course, `"Need at least 4 labeled structures to build options; only {n} available."`
- **Pillow load failure for an image** → skip that question, continue, note count.
- **No eligible targets (all `label_bbox` null — e.g. Tesseract was absent at capture)** → `"No structures have label positions (boxes). Re-ingest with Tesseract installed to enable image quizzes."`

---

## 7 — Testing

- `scripts/tests/test_image_quiz.py` (subprocess): feed a quiz-spec with 2 questions referencing a real captured PNG (render one via `image_extract` in setup, or a tiny generated PNG), assert: HTML file created; contains 2 `class="card"` blocks; each has 4 `class="opt"`; exactly one `data-correct="1"` per card; an embedded `data:image/png;base64,` per card; stdout `question_count == 2`.
- Self-contained check: assert the HTML has no `http://`/`https://` `src`/`href` (fully offline).
- Error path: missing `image_path` → question skipped or `success:false` (assert graceful).

---

## 8 — Out of scope

- Write-back to `progress.json` / adaptive weighting from image-quiz results.
- Targets without a `label_bbox` (no box to highlight).
- Occlusion-recall (type-the-name) and Anki-style reveal modes — superseded by MCQ.
- Export-size handling for the HTML files (base64 images inflate them; they live under gitignored `savedata`).

---

## Constraints honored

- **Rule 15** — no structured JSON writes here; the HTML is a generated artifact (like notes), and the log goes through `data_writer log entry`.
- **Rule 5 (materials-only)** — options come from the image bank (ingested materials); distractors are real structure names from the course, not invented.
- **Rule 1 / 2** — `/lkimage quiz` asks when course ambiguous; never mixes courses.
- **MCQ-default** — image questions are MCQ, consistent with `/lkquiz`.
