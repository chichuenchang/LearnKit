# Image-Based Anatomy Learning — Phase 1 Implementation Plan

> **Agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Implement task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Git:** user manages git for this feature. `Commit` steps below = reference points; do NOT run this session — leave working tree for user.

**Goal:** During ingest, extract labeled anatomy illustrations from slide PDFs into per-course `image_bank.json` (image + structures with positions); add `/lkimage` review command.

**Architecture:** `image_extract.py` renders PDF pages (fitz), detects label text+boxes via PyMuPDF text-layer words (exact) or Tesseract OCR (image-only, optional/graceful). Agent classifies which labels are anatomy, does flagged AI-fill, writes records via new `data_writer.py image add`. Vision-LLM never guesses coordinates (survey finding).

**Tech Stack:** Python 3.11 stdlib; PyMuPDF (`fitz`, installed); `pytesseract`+Tesseract (optional, absent here → graceful `source:"none"`); `unittest`+`subprocess` for tests; Markdown command files.

**Spec:** `docs/superpowers/specs/2026-06-15-image-anatomy-phase1-design.md`

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `scripts/data_writer.py` | `image add` / `image remove` subcommands | Modify |
| `scripts/image_extract.py` | Render pages + detect label words (textlayer/ocr/none) | Create |
| `scripts/tests/test_image.py` | Unittest for image subcommands | Create |
| `scripts/tests/test_image_extract.py` | Smoke test for `image_extract.py` | Create |
| `.claude/commands/lkschemas.md` | `image_bank.json` schema | Modify |
| `.claude/commands/lkscripts.md` | `image_extract.py` + `image` subcommands | Modify |
| `.claude/commands/lkingest.md` | Step 7d (illustration capture) | Modify |
| `.claude/commands/lkimage.md` | New `/lkimage` command | Create |
| `CLAUDE.md` | §2 data list, §6 cmd, §8 naming, §10 Rule 9a | Modify |
| `README.md` | `/lkimage` + Tesseract note | Modify |
| `scripts/requirements.txt` | add `pytesseract` (optional) | Modify |

---

### Task 1: `image add` / `image remove` subcommands

**Files:**
- Create: `scripts/tests/test_image.py`
- Modify: `scripts/data_writer.py`

- [ ] **Step 1: Write failing test**

Create `scripts/tests/test_image.py`:

```python
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = str(pathlib.Path(__file__).resolve().parents[1] / "data_writer.py")


def _run(args, stdin=None):
    proc = subprocess.run([sys.executable, SCRIPT, *args],
                          input=stdin, capture_output=True, text=True)
    return json.loads(proc.stdout)


def add(sd, course, images):
    return _run(["image", "add", "--savedata", sd, "--course", course],
                stdin=json.dumps(images))


def remove(sd, course, iid):
    return _run(["image", "remove", "--savedata", sd, "--course", course,
                 "--image-id", iid])


def read_bank(sd, course):
    p = (pathlib.Path(sd) / "courses" / course / "data" / "image_bank.json")
    return json.loads(p.read_text(encoding="utf-8"))


REC = {
    "unit_id": "week_06", "unit_slug": "week_06_foot",
    "source_file": "source_the_bones_of_the_foot.pdf", "page": 5,
    "image_path": "materials/week_06_foot/images/source_the_bones_of_the_foot_p05.png",
    "image_w": 1100, "image_h": 1500, "title": "The Talus", "label_source": "ocr",
    "structures": [
        {"name": "Talus", "type": "bone", "source": "slide",
         "label_bbox": [0.62, 0.40, 0.10, 0.03], "confidence": 0.91},
        {"name": "Dorsalis pedis a.", "type": "artery", "source": "ai",
         "label_bbox": None, "confidence": None, "verified": False},
    ],
}


class ImageAddTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sd = self._tmp.name
        self.course = "test_101"

    def tearDown(self):
        self._tmp.cleanup()

    def test_add_single(self):
        res = add(self.sd, self.course, [REC])
        self.assertTrue(res["success"])
        self.assertEqual(res["added"], 1)
        bank = read_bank(self.sd, self.course)
        img = bank["images"][0]
        self.assertEqual(img["image_id"], "img_test_101_001")
        self.assertEqual(img["page"], 5)
        self.assertEqual(img["structures"][0]["verified"], True)   # slide default
        self.assertEqual(img["structures"][1]["verified"], False)  # ai

    def test_dedup_by_source_and_page(self):
        add(self.sd, self.course, [REC])
        same = dict(REC)            # same source_file + page 5
        other = dict(REC, page=6)   # same source, different page
        res = add(self.sd, self.course, [same, other])
        self.assertEqual(res["added"], 1)
        self.assertEqual(res["skipped"], 1)
        self.assertEqual(res["ids"], ["img_test_101_002"])

    def test_invalid_structure_type(self):
        bad = dict(REC, structures=[{"name": "X", "type": "tendon", "source": "slide"}])
        res = add(self.sd, self.course, [bad])
        self.assertFalse(res["success"])
        self.assertIn("type", res["error"])

    def test_empty_stdin_fails(self):
        res = _run(["image", "add", "--savedata", self.sd,
                    "--course", self.course], stdin="")
        self.assertFalse(res["success"])


class ImageRemoveTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sd = self._tmp.name
        self.course = "test_101"
        add(self.sd, self.course, [REC, dict(REC, page=6)])

    def tearDown(self):
        self._tmp.cleanup()

    def test_remove_existing(self):
        res = remove(self.sd, self.course, "img_test_101_001")
        self.assertTrue(res["success"])
        ids = [i["image_id"] for i in read_bank(self.sd, self.course)["images"]]
        self.assertEqual(ids, ["img_test_101_002"])

    def test_remove_missing(self):
        res = remove(self.sd, self.course, "img_test_101_999")
        self.assertFalse(res["success"])
        self.assertIn("not found", res["error"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test, verify fails**

Run: `python scripts/tests/test_image.py -v`
Expected: FAIL/ERROR on all (argparse rejects `image` group → stdout not JSON → `json.loads` raises).

- [ ] **Step 3: Add constant + helpers + commands to `data_writer.py`**

Add constant after `VALID_QUESTION_TYPES` (near line 23):

```python
VALID_STRUCTURE_TYPES = {"muscle", "bone", "nerve", "artery", "joint", "ligament", "other"}
```

Add helpers after `pool_default` helper:

```python
def image_bank_path(savedata: pathlib.Path, course: str) -> pathlib.Path:
    return savedata / "courses" / course / "data" / "image_bank.json"


def image_bank_default(course: str) -> dict:
    return {"course": None, "course_id": course, "last_updated": None, "images": []}
```

Add command functions after `cmd_pool_remove`:

```python
# ── image add ─────────────────────────────────────────────────────────────────

def cmd_image_add(args):
    savedata = pathlib.Path(args.savedata)
    path = image_bank_path(savedata, args.course)
    data = load_json(path, image_bank_default(args.course))
    data.setdefault("images", [])

    raw = sys.stdin.buffer.read().decode("utf-8-sig").strip()
    if not raw:
        fail("no input on stdin (expected JSON array of image records)")
    try:
        incoming = json.loads(raw)
    except Exception as e:
        fail(f"invalid JSON on stdin: {e}")
    if not isinstance(incoming, list):
        fail("stdin JSON must be an array of image records")

    existing_keys = {(im.get("source_file"), im.get("page")) for im in data["images"]}
    prefix = f"img_{args.course}_"
    maxnum = 0
    for im in data["images"]:
        iid = im.get("image_id", "")
        if iid.startswith(prefix):
            try:
                maxnum = max(maxnum, int(iid[len(prefix):]))
            except ValueError:
                pass

    added_ids = []
    skipped = 0
    for rec in incoming:
        if not isinstance(rec, dict):
            fail("each image record must be a JSON object")
        src = rec.get("source_file")
        page = rec.get("page")
        if src is None or page is None:
            fail("image record missing source_file or page")
        key = (src, page)
        if key in existing_keys:
            skipped += 1
            continue
        existing_keys.add(key)

        norm_structs = []
        for s in (rec.get("structures") or []):
            stype = s.get("type")
            if stype not in VALID_STRUCTURE_TYPES:
                fail(f"invalid structure type: {stype!r}. Valid: {sorted(VALID_STRUCTURE_TYPES)}")
            ssource = s.get("source") or "slide"
            norm_structs.append({
                "name": s.get("name"),
                "type": stype,
                "source": ssource,
                "label_bbox": s.get("label_bbox"),
                "confidence": s.get("confidence"),
                "verified": bool(s.get("verified", ssource == "slide")),
            })

        maxnum += 1
        iid = f"{prefix}{maxnum:03d}"
        data["images"].append({
            "image_id": iid,
            "unit_id": rec.get("unit_id"),
            "unit_slug": rec.get("unit_slug"),
            "source_file": src,
            "page": int(page),
            "image_path": rec.get("image_path"),
            "image_w": rec.get("image_w"),
            "image_h": rec.get("image_h"),
            "title": rec.get("title"),
            "label_source": rec.get("label_source"),
            "structures": norm_structs,
            "date_added": today_str(),
        })
        added_ids.append(iid)

    data["last_updated"] = now_iso()
    save_json(path, data)
    out({"success": True, "added": len(added_ids), "skipped": skipped, "ids": added_ids})


# ── image remove ──────────────────────────────────────────────────────────────

def cmd_image_remove(args):
    savedata = pathlib.Path(args.savedata)
    path = image_bank_path(savedata, args.course)
    data = load_json(path, image_bank_default(args.course))
    data.setdefault("images", [])

    before = len(data["images"])
    data["images"] = [im for im in data["images"] if im.get("image_id") != args.image_id]
    if len(data["images"]) == before:
        fail(f"image id not found: {args.image_id!r}")
    data["last_updated"] = now_iso()
    save_json(path, data)
    out({"success": True, "removed": args.image_id})
```

Wire argparse after `pool` block in `main()`:

```python
    # image
    img = sub.add_parser("image")
    img_sub = img.add_subparsers(dest="action")

    ia = img_sub.add_parser("add")
    ia.add_argument("--savedata", required=True)
    ia.add_argument("--course", required=True)

    ir = img_sub.add_parser("remove")
    ir.add_argument("--savedata", required=True)
    ir.add_argument("--course", required=True)
    ir.add_argument("--image-id", required=True)
```

Add dispatch after `pool` branch in `try`:

```python
        elif args.group == "image":
            if args.action == "add":
                cmd_image_add(args)
            elif args.action == "remove":
                cmd_image_remove(args)
```

Add to module docstring subcommand list (after `pool remove` line):

```python
  image add         Append image records (JSON array on stdin) to image_bank.json
  image remove      Delete an image record from image_bank.json
```

- [ ] **Step 4: Run test, verify passes**

Run: `python scripts/tests/test_image.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit** *(reference only — git user-managed; skip this session)*

```bash
git add scripts/data_writer.py scripts/tests/test_image.py
git commit -m "feat: add image add/remove subcommands to data_writer"
```

---

### Task 2: `scripts/image_extract.py`

**Files:**
- Create: `scripts/image_extract.py`
- Create: `scripts/tests/test_image_extract.py`

- [ ] **Step 1: Write failing test**

Create `scripts/tests/test_image_extract.py`:

```python
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = str(REPO / "scripts" / "image_extract.py")
TEXT_PDF = REPO / "savedata/courses/pther_350a/materials/week_06_foot/source_the_arches_of_the_foot.pdf"
SCANNED_PDF = REPO / "savedata/courses/pther_350a/materials/week_06_foot/source_the_bones_of_the_foot.pdf"


def run_extract(pdf, out_dir):
    proc = subprocess.run([sys.executable, SCRIPT, "--file", str(pdf), "--out", out_dir],
                          capture_output=True, text=True)
    return json.loads(proc.stdout)


class ImageExtractTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    @unittest.skipUnless(TEXT_PDF.exists(), "text-layer fixture missing")
    def test_textlayer_pdf(self):
        res = run_extract(TEXT_PDF, self.out)
        self.assertTrue(res["success"], res.get("error"))
        self.assertGreater(res["page_count"], 0)
        tl = [p for p in res["pages"] if p["source"] == "textlayer" and p["words"]]
        self.assertTrue(tl, "expected at least one text-layer page with words")
        bbox = tl[0]["words"][0]["bbox"]
        self.assertEqual(len(bbox), 4)
        self.assertTrue(all(0.0 <= v <= 1.5 for v in bbox), bbox)  # normalized

    @unittest.skipUnless(SCANNED_PDF.exists(), "scanned fixture missing")
    def test_scanned_pdf_graceful(self):
        res = run_extract(SCANNED_PDF, self.out)
        self.assertTrue(res["success"], res.get("error"))
        self.assertGreater(len(res["pages"]), 0)
        for p in res["pages"]:
            self.assertIn(p["source"], {"textlayer", "ocr", "none"})

    def test_missing_file(self):
        res = run_extract(REPO / "nope_does_not_exist.pdf", self.out)
        self.assertFalse(res["success"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test, verify fails**

Run: `python scripts/tests/test_image_extract.py -v`
Expected: FAIL — `image_extract.py` does not exist (subprocess stdout empty → `json.loads` raises).

- [ ] **Step 3: Create `scripts/image_extract.py`**

```python
"""Render PDF pages to PNG and detect label text + boxes for the image bank.

Usage: python image_extract.py --file <pdf> --out <dir>
Output: JSON to stdout. Tesseract OCR is OPTIONAL (graceful degrade to source:"none").
"""
import argparse
import json
import os
import pathlib

from extract_text import _safe_name  # reuse the path-component sanitizer

TEXTLAYER_MIN_WORDS = 5
MAX_PAGES = 60
OCR_MIN_CONF = 40


def _norm_bbox(x0, y0, x1, y1, w, h):
    if w <= 0 or h <= 0:
        return None
    return [round(x0 / w, 4), round(y0 / h, 4),
            round((x1 - x0) / w, 4), round((y1 - y0) / h, 4)]


def _ocr_words(png_path):
    """Return [{text,bbox,conf}] via Tesseract, or None if OCR unavailable."""
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return None
    try:
        img = Image.open(png_path)
        data = pytesseract.image_to_data(
            img, config="--psm 12", output_type=pytesseract.Output.DICT)
    except Exception:
        return None
    words = []
    W, H = img.size
    for i in range(len(data["text"])):
        txt = (data["text"][i] or "").strip()
        try:
            conf = float(data["conf"][i])
        except ValueError:
            conf = -1.0
        if not txt or conf < OCR_MIN_CONF:
            continue
        x, y, w, h = (data["left"][i], data["top"][i],
                      data["width"][i], data["height"][i])
        words.append({"text": txt, "bbox": _norm_bbox(x, y, x + w, y + h, W, H),
                      "conf": round(conf / 100, 2)})
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    result = {"success": False, "filename": os.path.basename(args.file),
              "pages_dir": None, "page_count": 0, "capped": False,
              "pages": [], "error": None}
    try:
        import fitz
        if not os.path.exists(args.file):
            raise FileNotFoundError(f"File not found: {args.file}")

        stem = _safe_name(pathlib.Path(args.file).stem)
        out_dir = pathlib.Path(args.out) / stem
        out_dir.mkdir(parents=True, exist_ok=True)
        result["pages_dir"] = str(out_dir)

        doc = fitz.open(args.file)
        total = len(doc)
        result["page_count"] = total
        result["capped"] = total > MAX_PAGES
        mat = fitz.Matrix(2, 2)  # 2x render; PDF points -> pixels = *2

        for i in range(min(total, MAX_PAGES)):
            page = doc[i]
            pix = page.get_pixmap(matrix=mat)
            img_path = out_dir / f"page_{i + 1:03d}.png"
            pix.save(str(img_path))
            W, H = pix.width, pix.height

            tw = page.get_text("words")  # (x0,y0,x1,y1,word,block,line,wordno)
            words = []
            source = "none"
            if len(tw) >= TEXTLAYER_MIN_WORDS:
                source = "textlayer"
                for x0, y0, x1, y1, word, *_ in tw:
                    txt = (word or "").strip()
                    if not txt:
                        continue
                    words.append({"text": txt,
                                  "bbox": _norm_bbox(x0 * 2, y0 * 2, x1 * 2, y1 * 2, W, H),
                                  "conf": 1.0})
            else:
                ocr = _ocr_words(str(img_path))
                if ocr is not None:
                    source, words = "ocr", ocr

            result["pages"].append({"page": i + 1, "image_path": str(img_path),
                                    "image_w": W, "image_h": H,
                                    "source": source, "words": words})
        doc.close()
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test, verify passes**

Run: `python scripts/tests/test_image_extract.py -v`
Expected: PASS (3 tests; `test_scanned_pdf_graceful` confirms `source` is `none` here since Tesseract absent).

- [ ] **Step 5: Commit** *(reference only — skip this session)*

```bash
git add scripts/image_extract.py scripts/tests/test_image_extract.py
git commit -m "feat: add image_extract.py page render + label detection"
```

---

### Task 3: Schema + scripts docs

**Files:**
- Modify: `.claude/commands/lkschemas.md`
- Modify: `.claude/commands/lkscripts.md`

- [ ] **Step 1: Append image_bank schema to `lkschemas.md`**

Add at end of file:

```markdown

## Per-course `data\image_bank.json`
Labeled anatomy illustrations extracted during ingest. Image + structure labels (with positions) for `/lkimage` review and (Phase 2) occlusion quizzes. Written only via `data_writer.py image add` / `image remove`.

**top-level**: `course`, `course_id`, `last_updated`, `images[]`
**images[]**: `image_id` (`img_{course_id}_{NNN}`), `unit_id`, `unit_slug`, `source_file`, `page` (1-based), `image_path` (under `materials\{unit}\images\`), `image_w`, `image_h` (pixels), `title`, `label_source` (`textlayer` | `ocr` | `vision` | `none`), `structures[]`, `date_added`
**structures[]**: `name`, `type` (`muscle` | `bone` | `nerve` | `artery` | `joint` | `ligament` | `other`), `source` (`slide` = printed/grounded | `ai` = flagged, show `[AI — verify]`), `label_bbox` (normalized `[x,y,w,h]` 0–1 of the label text, or null), `confidence` (0–1 or null), `verified` (bool; true for slide)
Default empty: `{"course": null, "course_id": null, "last_updated": null, "images": []}`
Dedup key: `(source_file, page)`.
```

- [ ] **Step 2: Add `image` subcommands + `image_extract.py` to `lkscripts.md`**

In "Complete subcommand reference" table, add after `pool remove` row:

```markdown
| `image add` | `--savedata --course` | — (reads JSON array of image records from stdin) |
| `image remove` | `--savedata --course --image-id` | — |
```

Then add this block before "Log entry format" heading:

````markdown
**`image_extract.py` — render pages + detect label boxes (for the image bank):**
```powershell
$r = (& $pythonExe (Join-Path $scriptsRoot "image_extract.py") `
    --file "C:\full\path\source.pdf" --out (Join-Path $scriptsRoot "tmp_pages")) | ConvertFrom-Json
# $r.pages[] = { page, image_path, image_w, image_h, source(textlayer|ocr|none), words[] }
# words[] = { text, bbox [x,y,w,h normalized 0-1], conf }
# Clean up $r.pages_dir after building image records.
```
Label boxes come from the PDF text layer (`source:"textlayer"`, exact) or Tesseract OCR (`source:"ocr"`). Tesseract absent → image-only pages return `source:"none"` with no boxes (graceful). The agent classifies which words are anatomy structures and does the flagged AI-fill; it does NOT invent coordinates.

**`image add` — batch image-record write (reads stdin, like `pool add`):** one JSON array of image records → `image_bank.json`; assigns `img_{course}_{NNN}`, dedups by `(source_file, page)`.
````

- [ ] **Step 3: Verify**

Run: `grep -c "image_bank" .claude/commands/lkschemas.md && grep -c "image add\|image_extract" .claude/commands/lkscripts.md`
Expected: matches in both.

- [ ] **Step 4: Commit** *(reference only — skip this session)*

```bash
git add .claude/commands/lkschemas.md .claude/commands/lkscripts.md
git commit -m "docs: document image_bank schema and image subcommands"
```

---

### Task 4: `/lkingest` capture step (7d)

**Files:**
- Modify: `.claude/commands/lkingest.md`

- [ ] **Step 1: Add step 7d after step 7c**

Find step `7c.` block (pool extraction step) and line that follows. Immediately before step `8.` ("Fire all data writes synchronously"), insert:

```markdown
7d. **Capture anatomy illustrations to the image bank** (PDFs only): Run `image_extract.py --file {source} --out {scriptsRoot}\tmp_pages` (see lkscripts.md). For each returned page that is a **labeled anatomy illustration** (skip title / text-only / summary pages):
   - Save the page PNG → `materials\{unit_slug}\images\{source_slug}_p{NN}.png`.
   - From the page's detected `words` (text-layer or OCR boxes), keep those that are anatomy structures: record `name`, `bbox`, `confidence`, assign `type` (`muscle`/`bone`/`nerve`/`artery`/`joint`/`ligament`/`other`), `source:"slide"`.
   - Add notable UNlabeled structures as `source:"ai"`, `verified:false`, `label_bbox:null` (Rule 9a — flagged, surfaced `[AI — verify]`). Never override a printed label.
   - Set `title` (slide heading) and `label_source` (the page's `source`). NEVER invent coordinates — use only the detected boxes.

   Build one JSON array of all kept pages and write via a single `image add` call (see lkscripts.md). Then clean up the render dir via the returned `pages_dir`. Surface: `"Captured {N} illustration(s) — {S} slide-labeled structures, {A} AI-flagged."` No illustration pages → skip silently.
```

- [ ] **Step 2: Add log line in step 8**

After existing `[POOL]` log note in step 8, add:

```markdown
   When step 7d captured illustrations, also log per course: `- [IMAGE] Captured {N} illustration(s) from {filename} -> {unit}`
```

- [ ] **Step 3: Verify**

Run: `grep -c "7d\|image bank\|image_extract\|IMAGE" .claude/commands/lkingest.md`
Expected: ≥ 1.

- [ ] **Step 4: Commit** *(reference only — skip this session)*

```bash
git add .claude/commands/lkingest.md
git commit -m "feat: capture anatomy illustrations during /lkingest"
```

---

### Task 5: `/lkimage` command + logging tag

**Files:**
- Create: `.claude/commands/lkimage.md`
- Modify: `.claude/commands/lklogging.md`

- [ ] **Step 1: Write `.claude/commands/lkimage.md`**

```markdown
Base context (path variables, behavioral rules) loaded from CLAUDE.md. Data schemas in lkschemas.md. Python script protocol and data_writer.py reference in lkscripts.md. Log entry format spec in lklogging.md.

## `/lkimage` — Anatomy image bank (Phase 1: review)

Reviews each course's `data\image_bank.json` — labeled anatomy illustrations captured during ingest. Image structure labels are either printed slide labels (`[slide]`, grounded) or AI-identified (`[AI — verify]`, flagged). All writes go through `data_writer.py` `image add` / `image remove` (Rule 15). Multiple active courses + none specified → ask (Rule 2). Never mix courses (Rule 1). Missing `image_bank.json` → treat as empty.

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

### `/lkimage remove {image_id}` — delete a bad capture
Resolve course from the id, confirm, then `data_writer.py image remove`. Log: `[IMAGE] Removed {image_id}`.
```

- [ ] **Step 2: Add `[IMAGE]` tag to `lklogging.md`**

In tag table, add after `[POOL]` row:

```markdown
| `[IMAGE]` | `Captured {N} illustration(s) from {filename} → {unit}` · `Removed {image_id}` |
```

- [ ] **Step 3: Verify**

Run: `grep -c "lkimage\|image bank\|image_bank" .claude/commands/lkimage.md && grep -c "IMAGE" .claude/commands/lklogging.md`
Expected: matches present.

- [ ] **Step 4: Commit** *(reference only — skip this session)*

```bash
git add .claude/commands/lkimage.md .claude/commands/lklogging.md
git commit -m "feat: add /lkimage review command and IMAGE log tag"
```

---

### Task 6: CLAUDE.md + README + requirements

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `scripts/requirements.txt`

- [ ] **Step 1: CLAUDE.md §2 — add image bank + images dir**

After `data\problem_pool.json` line in per-course data list, add:

```
  data\image_bank.json        — labeled anatomy illustrations (image + structure labels) for /lkimage
```

After `materials\{unit_slug}\` line, add:

```
  materials\{unit_slug}\images\ — extracted illustration PNGs (referenced by image_bank.json)
```

- [ ] **Step 2: CLAUDE.md §6 — add `/lkimage`**

After `/lkpool` command block, insert:

```markdown
### `/lkimage` — Anatomy image bank
Full spec in `.claude/commands/lkimage.md`. Variants: `/lkimage {course}` (summary), `/lkimage {course} {scope}` (review), `/lkimage {image_id}`, `/lkimage remove {image_id}`. Labeled illustrations captured during ingest; structure labels are `[slide]` (grounded) or `[AI — verify]` (flagged).

---
```

- [ ] **Step 3: CLAUDE.md §8 — add `img_` naming**

After `Problem ID` bullet, add:

```markdown
- **Image ID**: `img_{course_id}_{NNN}` — e.g. `img_pther_350a_001` (increment from current max in that course's `image_bank.json`)
- **Illustration files**: `materials\{unit_slug}\images\{source_slug}_p{NN}.png` — `{NN}` = source page number
```

- [ ] **Step 4: CLAUDE.md §10 — add Rule 9a**

After Rule 9 (No hallucinated subject-matter knowledge), add:

```markdown
9a. **Image labels exception** — In the anatomy **image bank** only, structure names may be AI-identified **when not printed on the slide**, but MUST be stored `source:"ai"` with `verified:false` and surfaced as `[AI — verify]`. Printed slide labels (text-layer / OCR) stay the grounded default; AI-fill never overrides or invents a printed label.
```

- [ ] **Step 5: README — add `/lkimage` row + Tesseract note**

In Commands table, add after `/lkpool` row:

```markdown
| `/lkimage [course] [scope]` | Review the anatomy image bank (labeled illustrations) |
```

In "Python packages" install line, append `pytesseract` and add note row:

```markdown
| `pytesseract` | (Optional) Detect printed labels + positions on scanned anatomy slides. Needs the Tesseract binary installed separately; without it, image-only slides are captured without label boxes. |
```

- [ ] **Step 6: requirements.txt — add pytesseract**

Append to `scripts/requirements.txt`:

```
pytesseract
```

- [ ] **Step 7: Verify**

Run: `grep -c "image_bank.json\|/lkimage\|Image ID\|9a" CLAUDE.md && grep -c "lkimage" README.md`
Expected: matches.

- [ ] **Step 8: Commit** *(reference only — skip this session)*

```bash
git add CLAUDE.md README.md scripts/requirements.txt
git commit -m "docs: register image bank + /lkimage in CLAUDE.md and README"
```

---

### Task 7: Full-suite verification

**Files:** none (verification only)

- [ ] **Step 1: Run whole test suite**

Run: `python -m unittest discover -s scripts/tests -p "test_*.py" -v`
Expected: PASS — `test_pool` (8) + `test_extract` (5) + `test_image` (6) + `test_image_extract` (3) = 22 tests.

- [ ] **Step 2: End-to-end image_extract on real source**

Run:
```bash
python - <<'PY'
import json, subprocess, sys, tempfile, pathlib
out = tempfile.mkdtemp()
pdf = "savedata/courses/pther_350a/materials/week_06_foot/source_the_arches_of_the_foot.pdf"
r = subprocess.run([sys.executable, "scripts/image_extract.py", "--file", pdf, "--out", out],
                   capture_output=True, text=True)
d = json.loads(r.stdout)
tl = [p for p in d["pages"] if p["source"] == "textlayer"]
print("success", d["success"], "| pages", d["page_count"], "| textlayer pages", len(tl))
if tl: print("sample word:", tl[0]["words"][0])
import shutil; shutil.rmtree(d["pages_dir"], ignore_errors=True)
PY
```
Expected: `success True`, page_count > 0, at least one textlayer page, a sample word with a 4-value normalized bbox.

- [ ] **Step 3: Confirm no stray writes to real savedata**

Run: `git status --porcelain savedata/`
Expected: empty (tests use temp dirs; e2e smoke cleans its render dir).

---

## Self-Review

**Spec coverage:**
- §1 `image_extract.py` (render + textlayer/ocr/none) → Task 2. ✓
- §2 `image add`/`image remove` → Task 1. ✓
- §3 schema → Task 3 (doc) + Task 1 (writer emits exactly these fields). ✓
- §4 `/lkingest` step 7d → Task 4. ✓
- §5 `/lkimage` → Task 5; registered CLAUDE.md Task 6. ✓
- §6 Rule 9a → Task 6 Step 4. ✓
- §7 deps (pytesseract optional) → Task 6 Steps 5–6. ✓
- §8 docs → Tasks 3,4,5,6. ✓
- §9 testing → Tasks 1,2,7. ✓

**Placeholder scan:** No TBD/TODO; all code + insertion text literal. ✓

**Type consistency:** `image add`/`image remove`, flags `--savedata --course --image-id`, `image_id = img_{course}_{NNN}`, dedup key `(source_file, page)`, output keys `added`/`skipped`/`ids`/`removed`, and `image_extract.py` output keys `pages`/`pages_dir`/`source`/`words`/`bbox` are identical across plan, tests, and docs. The dispatch line referencing `cmd_image_remove` is added in Task 1 alongside its definition. ✓

**Note:** `image_extract.py` imports `_safe_name` from `extract_text.py` (no new shared module — YAGNI vs the spec's `_shared.py` suggestion). Importing `extract_text` runs only its defs (its `main()` is `__main__`-guarded), so the import is side-effect-free.
