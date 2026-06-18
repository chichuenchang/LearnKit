# Image-Based Anatomy Learning — Phase 1 Design Spec

**Date**: 2026-06-15
**Status**: Approved (design + survey), pending implementation plan
**Project**: LearnKit (PTStudy)
**Feature phase**: Phase 1 of 2 — *Capture* (extract illustrations + label structures + image bank + `/lkimage` review). Phase 2 (*occlusion quiz*) separate spec.

---

## Goal

Anatomy exams ask "name structure arrow points to." Text notes can't train that. Phase 1: during ingest, **extract labeled anatomy illustrations from slide PDFs**, build per-course **image bank**. Each illustration stored as image plus structured list of named structures (muscle / bone / nerve / artery / …) **with positions on image**. New `/lkimage` command lets user review these. Positions captured now because Phase 2 (occlusion quiz) masks label, asks user to name it.

---

## Decisions (brainstorm + 30-day survey)

| Decision | Choice | Basis |
|----------|--------|-------|
| Label source | **Hybrid** — printed slide labels grounded (`source:slide`); unlabeled structures may be AI-identified but **must** flag `source:ai` + `[AI — verify]` | User choice |
| Study mode | Occlusion (mask label text, keep slide's own leader line) **+** review. Phase 1 ships review; Phase 2 ships occlusion | User choice |
| Delivery | New `/lkimage` command, **2 phases**; Phase 1 = capture + review | User choice |
| **Label positions** | **OCR / PDF text-layer, NOT vision-LLM coordinates** | Survey (below) |

### Survey findings shaping this (WebSearch + `gh`, 2026-06-15)

- **Prior art validates occlusion.** Anki *Image Occlusion* (built-in + *Image Occlusion Enhanced*, 444★) = canonical "name the part" tool; modes "Hide-All-Guess-One" / "Hide-One-Guess-One" map to Phase 2.
- **Vision LLMs unreliable at bounding-box coords.** GPT-4o, Claude underperform at direct bbox regression (arxiv 2507.01955; Roboflow GPT-4V tests). Recommended: **2-stage** flow — detector/OCR produces boxes, LLM produces labels/classification.
- **Proven label-detection mechanism.** `BEST8OY/Auto-Image-Occlusion` uses **Tesseract OCR (PSM 12, sparse text)** → word boxes + confidence → group by line → filter by confidence/size. Adopt for image-only pages.
- **PyMuPDF gives exact text boxes free** when text layer exists: `page.get_text("words")` → `(x0, y0, x1, y1, word, …)`. Some decks (Arches) have text layer; scanned decks (Bones, Joints) do not.

**Consequence:** Claude used ONLY to (a) decide which detected labels are anatomy + assign `type`, (b) flagged AI-fill for unlabeled structures. Claude does NOT guess coordinates.

---

## Architecture (data flow)

```
ingested PDF
  │
  ├─(1) render pages → PNG            [fitz, reuse _safe_name]
  │
  ├─(2) detect label text + boxes per page
  │       ├─ text-layer present?  → PyMuPDF page.get_text("words")   (exact boxes, free)
  │       └─ image-only page?     → Tesseract OCR image_to_data PSM 12 (boxes + conf)
  │                                   group by line · filter low conf / tiny boxes
  │       (Tesseract absent → words=[] for that page; source:"none")
  │
  ├─(3) agent (Claude) reads page PNG + detected word list:
  │       • is this an anatomy illustration?  (skip title/text/summary pages)
  │       • for each detected label: anatomy? → keep text + its box, assign type, source:"slide"
  │       • notable UNlabeled structures → source:"ai", verified:false  (flagged)
  │       • capture slide title
  │
  ├─(4) save kept page PNGs → materials/{unit}/images/  +  records → image_bank.json
  │                                                        [data_writer image add]
  └─(5) /lkimage review
```

Steps 1–2 = new `scripts/image_extract.py`. Step 3 = agent behavior in `lkingest.md`. Step 4 = new `data_writer image add`. Step 5 = new `/lkimage` command.

---

## 1 — `scripts/image_extract.py` (new)

**Invocation:** `python image_extract.py --file <pdf> --out <dir>` → prints JSON to stdout (no temp file), mirrors `extract_text.py` conventions.

**Behavior:**
- Render every page to PNG via `fitz` at matrix 2× into `<dir>/{safe_stem}/page_{NN}.png` (reuse `_safe_name` from `extract_text.py` — move to shared spot or duplicate; see "Shared helper"). Cap at `MAX_PAGES = 60` (illustration decks can exceed 20-page scanned cap; surface `capped`).
- For each page, build `words` list of `{text, bbox, conf}`:
  - `page.get_text("words")` first. Yields ≥ `TEXTLAYER_MIN_WORDS` (e.g. 5) → `source:"textlayer"`, `conf: 1.0` each.
  - Else if `pytesseract` + Tesseract binary available → `pytesseract.image_to_data(png, config="--psm 12")`; keep level-5 (word) rows with `conf ≥ 40`; `source:"ocr"`.
  - Else → `words: []`, `source:"none"`.
- **Normalize every bbox to `[x, y, w, h]` in 0–1** relative to page-image pixel dims (resolution-independent — Phase-2 masking scales to any render size). Record `image_w`, `image_h` (pixels).
- Output:
```json
{ "success": true, "filename": "...", "pages_dir": "<dir>/<safe_stem>",
  "page_count": 22, "capped": false,
  "pages": [
    { "page": 5, "image_path": ".../page_05.png", "image_w": 1100, "image_h": 1500,
      "source": "ocr",
      "words": [ {"text":"Talus","bbox":[0.62,0.40,0.10,0.03],"conf":0.91} ] }
  ] }
```
- On exception: `{ "success": false, "error": "..." }` (same pattern as `extract_text.py`).

**Tesseract optional.** Missing binary → image-only pages return `words:[]`; agent still captures label names from vision but without precise boxes (degraded — those structures get `label_bbox: null`, Phase 2 cannot occlude). `lksetup` package check gains optional Tesseract probe (warn-only).

**Shared helper:** `_safe_name` currently lives in `extract_text.py`. Avoid divergence: move to `scripts/lib_paths.py` (new, tiny), import from both, OR duplicate with comment. Plan picks one; default = small shared module `scripts/_shared.py` with `safe_name()` + reuse in both scripts. Add unit test for shared function (existing `test_extract.py` already covers it; repoint import).

---

## 2 — `data_writer.py` subcommands (Rule 15)

### `image add`
- **Required**: `--savedata`, `--course`.
- **Input**: JSON array of image records on **stdin** (mirrors `pool add`).
- Behavior: load/default `image_bank.json`; per record — assign `image_id = img_{course}_{NNN}` (increment from max); **dedup by `(source_file, page)`** (skip dup, report); default optional fields; set `date_added`. Append, bump `last_updated`, save.
- **Output**: `{"success": true, "added": N, "skipped": M, "ids": [...]}`.

### `image remove`
- **Required**: `--savedata`, `--course`, `--image-id`. Deletes that record. `{"success": true, "removed": "<id>"}` or error if not found.

Both added to `lkscripts.md` subcommand table. Unit-tested via subprocess (mirror `test_pool.py`): add-single, id-increment, dedup-by-source+page, defaults, remove-existing, remove-missing.

---

## 3 — Storage schema: `data/image_bank.json` (per course)

Parallel to `problem_pool.json`. Images saved under `materials/{unit_slug}/images/{source_slug}_p{NN}.png`.

```json
{
  "course": "PTHER 350A", "course_id": "pther_350a", "last_updated": null,
  "images": [
    {
      "image_id": "img_pther_350a_001",
      "unit_id": "week_06", "unit_slug": "week_06_foot",
      "source_file": "source_the_bones_of_the_foot.pdf", "page": 5,
      "image_path": "materials/week_06_foot/images/source_the_bones_of_the_foot_p05.png",
      "image_w": 1100, "image_h": 1500,
      "title": "The Talus",
      "label_source": "ocr",
      "structures": [
        {"name": "Talus", "type": "bone", "source": "slide",
         "label_bbox": [0.62,0.40,0.10,0.03], "confidence": 0.91, "verified": true},
        {"name": "Dorsalis pedis a.", "type": "artery", "source": "ai",
         "label_bbox": null, "confidence": null, "verified": false}
      ],
      "date_added": null
    }
  ]
}
```

| Field | Meaning |
|-------|---------|
| `image_id` | `img_{course_id}_{NNN}` |
| `page` | 1-based page number in `source_file` |
| `image_w/h` | page-image pixel dims (so normalized bboxes can be scaled) |
| `label_source` | `textlayer` \| `ocr` \| `vision` \| `none` (box provenance) |
| `structures[].source` | `slide` (printed, grounded) \| `ai` (flagged) |
| `structures[].type` | `muscle \| bone \| nerve \| artery \| joint \| ligament \| other` |
| `structures[].label_bbox` | normalized `[x,y,w,h]` 0–1 of label text; `null` when unknown (AI w/o printed label, or Tesseract absent) |
| `structures[].confidence` | detector confidence 0–1 (`1.0` text-layer, OCR conf, `null` AI/vision) |
| `structures[].verified` | `true` for slide labels; `false` for AI |

Default empty: `{"course": null, "course_id": null, "last_updated": null, "images": []}`

---

## 4 — `/lkingest` integration (new step 7d)

After notes / raw copy / pool extraction, per ingested **PDF**:
1. Run `image_extract.py` → page PNGs + per-page detected `words`.
2. Agent reads each page PNG with its detected word list. For pages that are **labeled anatomy illustrations** (skip title/text/summary):
   - Map page → unit (file's already-assigned unit).
   - Each detected label that is anatomy structure: keep `text` + `bbox` + `confidence`, assign `type`, `source:"slide"`.
   - Add notable unlabeled structures as `source:"ai"`, `verified:false`, `label_bbox:null` (Rule 9 image exception — see §6).
   - Set `title` from slide heading; `label_source` from page's detection source.
   - Save page PNG → `materials/{unit_slug}/images/{source_slug}_p{NN}.png`.
3. Batch all kept pages → one `image add` call.
4. Surface: `"Captured N illustration(s) — S slide-labeled structures, A AI-flagged."`
5. Clean up render dir via `pages_dir` (same pattern as scanned-PDF branch).

Non-PDF files + PDFs with no illustration pages → skip silently. PPTX deferred (Phase 2+).

---

## 5 — `/lkimage` command (Phase 1 = review)

New `.claude/commands/lkimage.md`.

- `/lkimage {course}` — summary: image count per unit; total structures with slide-vs-AI tally; units with 0 images.
- `/lkimage {course} {scope}` — per image in scope: print **image file path** (user opens it), `title`, structure list as `name · type · [slide]`/`[AI — verify]`. (Terminal can't inline-render images → path + list.)
- `/lkimage {image_id}` — one image's full structure list.

Rules: multi-course + none → ask (Rule 2); never mix courses (Rule 1); log mutations (Rule 14). Missing `image_bank.json` → treat as empty.

---

## 6 — Rule 9 amendment (CLAUDE.md §10)

Rule 9 forbids hallucinated subject knowledge. Add scoped exception:

> **9a. Image structure labels** may be AI-identified **only when structure not printed on slide**, and **must** be stored `source:"ai"` with `verified:false`, surfaced as `[AI — verify]`. Printed slide labels (captured via text-layer/OCR) remain grounded default; AI-fill never overrides or invents printed label.

---

## 7 — Dependencies

- **PyMuPDF (`fitz`)** — already used by `extract_text.py`.
- **`pytesseract` + Tesseract binary** — NEW, for label boxes on image-only (scanned) pages. **Optional/graceful**: absence degrades image-only pages to no-box capture (flagged), does not block ingest. Add to `requirements.txt` (pytesseract), README (note Tesseract is system binary), optional warn-only probe in `lksetup`.
- **Pillow** — NOT needed in Phase 1 (masking is Phase 2).

---

## 8 — Documentation touched

`CLAUDE.md` (§2 `image_bank.json` + `materials/{unit}/images/`, §6 `/lkimage`, §8 `img_` naming + image file naming, §10 Rule 9a), `lkschemas.md` (image_bank schema), `lkscripts.md` (`image_extract.py` + `image add`/`image remove`), `lkingest.md` (step 7d), new `lkimage.md`, `README.md` (/lkimage + Tesseract note).

---

## 9 — Testing

- `data_writer image add`/`image remove` — `scripts/tests/test_image.py` (subprocess, mirrors `test_pool.py`).
- `image_extract.py` — smoke: text-layer PDF (Arches) → expect `source:"textlayer"` words with boxes; scanned PDF (Bones) → `source:"ocr"` if Tesseract present, else `source:"none"` (assert graceful). Reuse `materials/.../source_*.pdf` as fixture; clean render dir after.
- `safe_name` shared helper — covered by existing `test_extract.py` (repoint import).

---

## 10 — Out of scope (Phase 2 / later)

- Occlusion quiz, Pillow label-masking, `/lkimage quiz {scope}`.
- PPTX illustration capture (needs LibreOffice-class rendering).
- Export-size handling for new PNGs under `materials/**/images/` (will inflate `/lkexport`; ties to memory `export-raw-archive-excluded`).
- Vector-diagram (non-raster) structure extraction beyond what text-layer words give.

---

## Constraints honored

- **Rule 9** — amended (9a) for flagged AI image labels only; slide labels grounded.
- **Rule 15** — image bank written only via `data_writer image add`/`remove`.
- **Rule 1 / 2** — `/lkimage` asks when course ambiguous; never mixes courses.
- **Rule 14** — image-bank mutations logged.
- **Survey** — label positions from OCR/text-layer, not LLM bbox.
