# Image-Rich Notes Plan

> **Agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Implement task-by-task. Steps use checkbox (`- [ ]`) tracking.
>
> **Git:** user manages git. `Commit` steps reference only — do NOT run this session.

**Goal:** `/lkingest` makes self-contained image-rich `.md` notes — agent-cropped diagrams embedded inline as base64 next to relevant text.

**Architecture:** Agent writes note with lightweight `{{FIG: page | x,y,w,h | caption}}` placeholders; `scripts/notes_embed.py` crops each figure (Pillow) from rendered page, base64-embeds, writes final `.md`. Ingest renders pages before note-gen so agent can crop. No-figure notes pass through unchanged.

**Tech Stack:** Python 3.11 stdlib (`re`, `base64`, `io`) + Pillow (installed); `unittest`+`subprocess` tests; Markdown command files.

**Spec:** `docs/superpowers/specs/2026-06-15-image-rich-notes-design.md`

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `scripts/notes_embed.py` | stdin note + `{{FIG}}` tokens → crop+base64 → self-contained `.md` | Create |
| `scripts/tests/test_notes_embed.py` | unittest: embed / pass-through / missing | Create |
| `.claude/commands/lkingest.md` | reorder steps; note-gen uses `{{FIG}}` + `notes_embed.py` | Modify |
| `.claude/commands/lkscripts.md` | `notes_embed.py` reference + token format | Modify |
| `CLAUDE.md` | note-format line (self-contained, embedded figures) | Modify |
| `README.md` | mention image-rich notes | Modify |

---

### Task 1: `scripts/notes_embed.py`

**Files:**
- Create: `scripts/notes_embed.py`
- Create: `scripts/tests/test_notes_embed.py`

- [ ] **Step 1: Write failing test**

Create `scripts/tests/test_notes_embed.py`:

```python
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = str(pathlib.Path(__file__).resolve().parents[1] / "notes_embed.py")


def make_png(path, size=(400, 300)):
    from PIL import Image
    Image.new("RGB", size, (255, 255, 255)).save(path)


def run_embed(note_text, dest):
    proc = subprocess.run([sys.executable, SCRIPT, "--dest", dest],
                          input=note_text, capture_output=True, text=True)
    return json.loads(proc.stdout)


class NotesEmbedTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self._tmp.name)
        self.png = str(self.d / "page.png")
        make_png(self.png)
        self.dest = str(self.d / "note.md")

    def tearDown(self):
        self._tmp.cleanup()

    def test_embed_figure(self):
        note = f"# Title\n\nIntro.\n\n{{{{FIG: {self.png} | 0,0,0.5,0.5 | Talus diagram}}}}\n\nMore."
        res = run_embed(note, self.dest)
        self.assertTrue(res["success"], res.get("error"))
        self.assertEqual(res["figures_embedded"], 1)
        self.assertEqual(res["missing"], 0)
        txt = pathlib.Path(self.dest).read_text(encoding="utf-8")
        self.assertIn("data:image/png;base64,", txt)
        self.assertIn("Talus diagram", txt)
        self.assertNotIn("{{FIG", txt)

    def test_passthrough_no_tokens(self):
        note = "# Plain note\n\nNo figures here.\n"
        res = run_embed(note, self.dest)
        self.assertTrue(res["success"])
        self.assertEqual(res["figures_embedded"], 0)
        self.assertEqual(pathlib.Path(self.dest).read_text(encoding="utf-8"), note)

    def test_missing_page_graceful(self):
        gone = str(self.d / "nope.png")
        note = f"text {{{{FIG: {gone} | 0,0,0.5,0.5 | Soleus}}}} end"
        res = run_embed(note, self.dest)
        self.assertTrue(res["success"])
        self.assertEqual(res["missing"], 1)
        txt = pathlib.Path(self.dest).read_text(encoding="utf-8")
        self.assertIn("figure unavailable", txt)
        self.assertNotIn("{{FIG", txt)

    def test_empty_dest_dir_created(self):
        nested = str(self.d / "sub" / "deep" / "note.md")
        res = run_embed("# x\n", nested)
        self.assertTrue(res["success"])
        self.assertTrue(pathlib.Path(nested).exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test, verify fails**

Run: `python scripts/tests/test_notes_embed.py -v`
Expected: FAIL — `notes_embed.py` missing (subprocess stdout empty → `json.loads` raises).

- [ ] **Step 3: Create `scripts/notes_embed.py`**

```python
"""Embed agent-cropped figures into a study note as base64 data-URIs.

Usage: python notes_embed.py --dest <md_path>    (reads note text on stdin)
Figure token (inline, single line):
    {{FIG: <page_png_path> | x,y,w,h | caption}}
  - x,y,w,h = crop box normalized 0-1 relative to the page image
  - caption = alt text (no '|' or '}')
No tokens -> the note is written through unchanged.
Output: JSON to stdout (ASCII-safe): {success, dest, figures_embedded, missing, error}
"""
import argparse
import base64
import io
import json
import os
import re
import sys

FIG_RE = re.compile(
    r"\{\{FIG:\s*(?P<path>[^|]+?)\s*\|\s*"
    r"(?P<x>[\d.]+)\s*,\s*(?P<y>[\d.]+)\s*,\s*(?P<w>[\d.]+)\s*,\s*(?P<h>[\d.]+)\s*\|\s*"
    r"(?P<cap>[^}]*)\}\}"
)


def _embed_one(m, stats):
    path = m.group("path").strip()
    cap = m.group("cap").strip()
    try:
        from PIL import Image
        x, y, w, h = (float(m.group(k)) for k in ("x", "y", "w", "h"))
        img = Image.open(path).convert("RGB")
        W, H = img.size
        box = (int(x * W), int(y * H), int((x + w) * W), int((y + h) * H))
        crop = img.crop(box)
        buf = io.BytesIO()
        crop.save(buf, format="PNG")
        uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
        stats["embedded"] += 1
        cap_safe = cap.replace("[", "").replace("]", "")
        return f"![{cap_safe}]({uri})"
    except Exception:
        stats["missing"] += 1
        return f"*(figure unavailable: {cap})*"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True)
    args = ap.parse_args()

    result = {"success": False, "dest": args.dest,
              "figures_embedded": 0, "missing": 0, "error": None}
    try:
        text = sys.stdin.buffer.read().decode("utf-8-sig")
        stats = {"embedded": 0, "missing": 0}
        out = FIG_RE.sub(lambda m: _embed_one(m, stats), text)
        os.makedirs(os.path.dirname(os.path.abspath(args.dest)), exist_ok=True)
        with open(args.dest, "w", encoding="utf-8") as f:
            f.write(out)
        result["figures_embedded"] = stats["embedded"]
        result["missing"] = stats["missing"]
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)

    print(json.dumps(result))  # ASCII-safe stdout


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test, verify passes**

Run: `python scripts/tests/test_notes_embed.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit** *(reference only — skip)*

```bash
git add scripts/notes_embed.py scripts/tests/test_notes_embed.py
git commit -m "feat: add notes_embed.py figure embedder"
```

---

### Task 2: `/lkingest` — reorder + figure embed

**Files:**
- Modify: `.claude/commands/lkingest.md`

Current order: 7 (notes via `notes write`) → 7b (pool) → 7c (image bank). Reorder so pages render BEFORE note-gen, and note embeds figures.

- [ ] **Step 1: Replace step 7 with render step (7a)**

Find step 7 (`7. **Generate grade-focused study notes** ...` through its powershell `notes write` block ending in ```` ``` ````) and replace WHOLE step 7 block with:

````markdown
7a. **Render pages** (PDFs): Run `image_extract.py --file {source} --out {scriptsRoot}\tmp_pages` (see lkscripts.md) → page PNGs in `pages_dir` + per-page label boxes (PaddleOCR / text-layer). These pages feed BOTH the image bank (7b) and the note figures (7c). Keep `pages_dir` until step 8 cleanup. Non-PDF → skip (no figures).
````

- [ ] **Step 2: Replace step 7b (pool), make it image-bank step (7b)**

Find step `7b. **Extract problems to the pool**` (whole block through its `pool add` surface line) and replace with image-bank capture step (moved from old 7c):

````markdown
7b. **Capture labeled diagrams/figures to the image bank** (PDFs only): from the 7a pages, for each page that is a **labeled diagram or figure** (any subject; skip title/text/summary pages):
   - Save the page PNG → `materials\{unit_slug}\images\{source_slug}_p{NN}.png`.
   - Keep detected `words` that label a part/region/term: record `name`, `bbox`, `confidence`, a free-form `type` (e.g. `bone`, `country`, `component`; or null), `source:"slide"`. Notable unlabeled structures → `source:"ai"`, `verified:false`, `label_bbox:null` (Rule 9a, `[AI — verify]`). Never invent coordinates.
   - Set `title` + `label_source`. Build one JSON array → single `image add` call (lkscripts.md). Surface: `"Captured {N} illustration(s) — {S} slide labels, {A} AI-flagged."`
````

- [ ] **Step 3: Replace step 7c (old image bank) with image-rich note step (7c)**

Find step `7c. **Capture anatomy illustrations...` / `7c. **Capture labeled diagrams/figures to the image bank**` (OLD image-bank block, now duplicated by Step 2 above) and replace with note-generation step:

````markdown
7c. **Generate the image-rich study note** and write via `notes_embed.py` (no Write tool): write a grade-focused, Section-1-tagged note. Inline, where a diagram illustrates the text, drop a figure placeholder:
   ```
   {{FIG: {pages_dir}\page_{NN}.png | x,y,w,h | caption}}
   ```
   - `x,y,w,h` = crop box **normalized 0–1** on that page image (crop to the single figure — on 2-up handout pages, top slide ≈ `0,0,1,0.5`, bottom slide ≈ `0,0.5,1,0.5`; tighten as needed).
   - First line of the note: `**Source**: {filename} | **Course**: {course_code} | **Unit**: {unit display name} | **Ingested**: {date} | **Raw material**: raw/{unit_slug}/source_{slug}.{ext}`, then `---`, then the body with `{{FIG}}` placeholders.
   - Pipe to `notes_embed.py` → self-contained `.md` (figures become inline base64):
   ```powershell
   $notesContent = @'
   {full note content with {{FIG: ...}} placeholders}
   '@
   $notesContent | & $pythonExe (Join-Path $scriptsRoot "notes_embed.py") `
       --dest "{$savedataRoot}\courses\{course_id}\materials\{unit_slug}\{type}_{slug}.md" | Out-Null
   ```
   - Non-PDF / no relevant figures → write the note with no `{{FIG}}` tokens (notes_embed passes it through). `notes_embed.py` replaces `notes write` for ALL notes.

7d. **Extract problems to the pool** (only when file type ∈ `{practice_quiz, exam_review, past_exam}`): scan the extracted text for discrete Q+A pairs (none → skip). Map each to a unit, assign `topic`, set `question_type`/`options`/`answer`/`tags` (from the file only, Rule 9), `source_type` = classification, `verbatim:true`, `source_file`. Build one JSON array → single `pool add` call (lkscripts.md). Surface: `"Extracted {added} problem(s) to {course_code} pool ({skipped} duplicate(s) skipped)."`
````

- [ ] **Step 4: Update step 8 cleanup to use 7a pages_dir**

In step 8, ensure render dir cleaned. After `[INGEST]`/`[POOL]`/`[IMAGE]` log lines, confirm/append:

```markdown
   After all writes, clean up the 7a render dir (`pages_dir` from `image_extract.py`).
```

- [ ] **Step 5: Verify**

Run: `grep -c "notes_embed\|{{FIG\|7a\|Render pages" .claude/commands/lkingest.md`
Expected: ≥ 3 matches.

- [ ] **Step 6: Commit** *(reference only — skip)*

```bash
git add .claude/commands/lkingest.md
git commit -m "feat: image-rich notes in /lkingest (render-first + figure embed)"
```

---

### Task 3: `lkscripts.md` + `CLAUDE.md` + `README.md`

**Files:**
- Modify: `.claude/commands/lkscripts.md`
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: `lkscripts.md` — document `notes_embed.py`**

Replace the `notes write` row in the subcommand reference table:

```markdown
| `notes write` | `--dest` | — (reads content from stdin; raw write, no figure embedding) |
```

(keep it) and add this block right after the `pool add` batch block (before the "Log entry format" heading):

````markdown
**`notes_embed.py` — write a study note, embedding `{{FIG}}` figures as base64 (reads stdin):**
```powershell
$note = @'
# ...
Intro text.
{{FIG: C:\...\tmp_pages\...\page_06.png | 0,0.5,1,0.5 | Deep compartment muscles}}
More text.
'@
$r = ($note | & $pythonExe (Join-Path $scriptsRoot "notes_embed.py") --dest $mdPath) | ConvertFrom-Json
# success → { figures_embedded, missing }
```
Token = `{{FIG: <page_png> | x,y,w,h | caption}}` (crop normalized 0-1). Each is cropped (Pillow) → base64 → `![caption](data:image/png;base64,...)`. No tokens → writes through unchanged (replaces `notes write` for the note step). Missing/bad page → `*(figure unavailable)*`, never crashes.
````

- [ ] **Step 2: `CLAUDE.md` §2 — note materials notes self-contained image-rich**

Replace the `materials\{unit_slug}\` line:

```markdown
  materials\{unit_slug}\      — generated study notes (.md, self-contained: figures embedded inline as base64) — NO source files (sources live in raw\)
```

- [ ] **Step 3: `README.md` — mention image-rich notes**

In `/lkingest` row of Commands table, replace:

```markdown
| `/lkingest` | Process files from `savedata/raw/` or pasted paths → self-contained image-rich notes |
```

- [ ] **Step 4: Verify**

Run: `grep -c "notes_embed" .claude/commands/lkscripts.md && grep -c "self-contained\|image-rich" CLAUDE.md README.md`
Expected: matches.

- [ ] **Step 5: Commit** *(reference only — skip)*

```bash
git add .claude/commands/lkscripts.md CLAUDE.md README.md
git commit -m "docs: document notes_embed + image-rich notes"
```

---

### Task 4: Full-suite verify + real end-to-end

**Files:** none (verify only)

- [ ] **Step 1: Run whole test suite**

Run: `python -m unittest discover -s scripts/tests -p "test_*.py" -v`
Expected: PASS — pool(8) + extract(5) + image(6) + image_extract(3) + image_quiz(4) + notes_embed(4) = 30 tests.

- [ ] **Step 2: Real end-to-end — render page, embed cropped figure**

Run:
```bash
python - <<'PY'
import json, subprocess, sys, tempfile, pathlib, shutil
out = tempfile.mkdtemp()
pdf = "savedata/courses/pther_350a/raw/week_05_leg_and_ankle/source_posterior_compartment_leg.pdf"
r = subprocess.run([sys.executable,"scripts/image_extract.py","--file",pdf,"--out",out],capture_output=True,text=True)
d = json.loads(r.stdout)
page = d["pages"][2]["image_path"]   # page 3: deep muscles on the bottom slide
note = f"# Posterior Compartment\n\nDeep muscles:\n\n{{{{FIG: {page} | 0,0.5,1,0.5 | Deep subcompartment muscles}}}}\n\nAll tibial nerve."
dest = str(pathlib.Path(out)/"note.md")
e = subprocess.run([sys.executable,"scripts/notes_embed.py","--dest",dest],input=note,capture_output=True,text=True)
res = json.loads(e.stdout)
txt = pathlib.Path(dest).read_text(encoding="utf-8")
print("embed:",res["success"],"| figs:",res["figures_embedded"],"| has_base64:", "data:image/png;base64," in txt, "| token_gone:", "{{FIG" not in txt)
shutil.rmtree(d["pages_dir"],ignore_errors=True); shutil.rmtree(out,ignore_errors=True)
PY
```
Expected: `embed: True | figs: 1 | has_base64: True | token_gone: True`.

- [ ] **Step 3: Confirm no leftover temp**

Run: `ls scripts/tmp_pages/ 2>/dev/null | grep -i posterior && echo LEFTOVER || echo clean`
Expected: `clean`.

---

## Self-Review

**Spec coverage:**
- "Self-contained `.md`, base64" → Task 1 (`_embed_one` → data-URI). ✓
- "Agent-cropped figures via `{{FIG}}`" → Task 1 (FIG_RE + crop) + Task 2 step 3 (agent emits tokens). ✓
- "notes_embed pass-through when no tokens" → Task 1 (`test_passthrough`). ✓
- "Render pages before note-gen" → Task 2 steps 1–3 (7a render, 7c note). ✓
- "image bank unchanged" → Task 2 step 2 (7b capture retained). ✓
- "non-PDF pass-through" → Task 2 step 3 + Task 1. ✓
- docs → Task 3. ✓
- testing → Task 1 + Task 4. ✓

**Placeholder scan:** none — full code + literal insertion text. ✓

**Type consistency:** token grammar `{{FIG: path | x,y,w,h | caption}}`, output keys `success`/`figures_embedded`/`missing`/`dest`, and `data:image/png;base64,` marker match across `notes_embed.py`, the tests, `lkingest.md`, and `lkscripts.md`. ✓

**Note:** Task 2 reuses much of old step 7c image-bank text in new 7b — engineer must delete now-duplicated old block (Task 2 step 3 explicitly replaces it with note step). After edits there must be exactly one image-bank step (7b) and one note step (7c).
