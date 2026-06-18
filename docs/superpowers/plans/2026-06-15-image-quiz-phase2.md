# Image MCQ Quiz — Phase 2 Implementation Plan

> **Agentic workers:** REQUIRED SUB-SKILL. Use superpowers:subagent-driven-development (preferred) or superpowers:executing-plans. Implement task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Git note:** user manages git for this feature. `Commit` steps = reference points; do NOT run them this session — leave working tree for user.

**Goal:** `/lkimage quiz {course} {scope}` builds self-contained HTML page of MCQ questions ("name the highlighted structure", 4 options A–D) from image bank, opens in browser.

**Architecture:** Agent selects targets + builds 4 options (correct + 3 distractors), emits quiz-spec JSON; `scripts/image_quiz.py` masks+highlights each target (Pillow), embeds images as base64 data-URIs, renders ONE self-contained `.html` (inline CSS/JS, vanilla, no deps). Agent opens it (`Start-Process`), logs.

**Tech Stack:** Python 3.11 stdlib + Pillow (installed); `unittest`+`subprocess` for tests; self-contained HTML5/CSS/JS.

**Spec:** `docs/superpowers/specs/2026-06-15-image-quiz-phase2-design.md`

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `scripts/image_quiz.py` | quiz-spec JSON (stdin) → masked images + self-contained HTML | Create |
| `scripts/tests/test_image_quiz.py` | unittest for HTML builder | Create |
| `.claude/commands/lkimage.md` | `/lkimage quiz` variant (agent flow) | Modify |
| `.claude/commands/lkscripts.md` | `image_quiz.py` reference | Modify |
| `.claude/commands/lklogging.md` | `[IMAGE]` "Quiz generated" phrasing | Modify |
| `CLAUDE.md` | §6 `/lkimage` variants (+quiz) | Modify |
| `README.md` | `/lkimage` row (+quiz) | Modify |

---

### Task 1: `scripts/image_quiz.py`

**Files:**
- Create: `scripts/image_quiz.py`
- Create: `scripts/tests/test_image_quiz.py`

- [ ] **Step 1: Write failing test**

Create `scripts/tests/test_image_quiz.py`:

```python
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = str(pathlib.Path(__file__).resolve().parents[1] / "image_quiz.py")


def make_png(path):
    from PIL import Image
    Image.new("RGB", (400, 300), (255, 255, 255)).save(path)


def run_quiz(spec, out_html):
    proc = subprocess.run([sys.executable, SCRIPT, "--out", out_html],
                          input=json.dumps(spec), capture_output=True, text=True)
    return json.loads(proc.stdout)


class ImageQuizTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self._tmp.name)
        self.png = str(self.d / "p.png")
        make_png(self.png)
        self.html = str(self.d / "quiz.html")

    def tearDown(self):
        self._tmp.cleanup()

    def _spec(self, n=2):
        return {"title": "Test Quiz", "questions": [
            {"image_path": self.png, "image_w": 400, "image_h": 300,
             "target_bbox": [0.3, 0.3, 0.2, 0.05],
             "stem": "What is the name of the highlighted structure?",
             "options": ["Talus", "Calcaneus", "Navicular", "Cuboid"],
             "answer_index": (i % 4)} for i in range(n)]}

    def test_builds_html(self):
        res = run_quiz(self._spec(2), self.html)
        self.assertTrue(res["success"], res.get("error"))
        self.assertEqual(res["question_count"], 2)
        txt = pathlib.Path(self.html).read_text(encoding="utf-8")
        self.assertEqual(txt.count('class="card"'), 2)
        self.assertEqual(txt.count('class="opt"'), 8)          # 4 per card
        self.assertEqual(txt.count('data-correct="1"'), 2)     # 1 per card
        self.assertIn("data:image/png;base64,", txt)

    def test_self_contained_offline(self):
        run_quiz(self._spec(1), self.html)
        txt = pathlib.Path(self.html).read_text(encoding="utf-8")
        self.assertNotIn("http://", txt)
        self.assertNotIn("https://", txt)

    def test_missing_image_skipped(self):
        spec = self._spec(1)
        spec["questions"][0]["image_path"] = str(self.d / "nope.png")
        res = run_quiz(spec, self.html)
        self.assertTrue(res["success"], res.get("error"))
        self.assertEqual(res["question_count"], 0)

    def test_empty_stdin_fails(self):
        proc = subprocess.run([sys.executable, SCRIPT, "--out", self.html],
                              input="", capture_output=True, text=True)
        self.assertFalse(json.loads(proc.stdout)["success"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test, verify it fails**

Run: `python scripts/tests/test_image_quiz.py -v`
Expected: FAIL — `image_quiz.py` absent (subprocess stdout empty → `json.loads` raises).

- [ ] **Step 3: Create `scripts/image_quiz.py`**

```python
"""Render an image MCQ quiz to a self-contained HTML page.

Usage: python image_quiz.py --out <html_path>   (reads a quiz-spec JSON on stdin)
Output: JSON to stdout (ASCII-safe). The HTML embeds images as base64 data-URIs
and uses inline CSS/JS only (fully offline, single file).
"""
import argparse
import base64
import html as htmllib
import io
import json
import os
import sys

CARD_TMPL = """  <section class="card" data-i="{i}">
    <div class="meta">Q {n} / {total}</div>
    <img alt="question image" src="{uri}">
    <p class="stem">{stem}</p>
    <div class="opts">
{buttons}
    </div>
    <div class="fb"></div>
  </section>"""

BTN_TMPL = '      <button class="opt"{correct}>{letter}. {text}</button>'

PAGE_TMPL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
 body{{font-family:system-ui,Arial,sans-serif;max-width:820px;margin:24px auto;padding:0 14px;color:#1b1b1b}}
 h1{{font-size:18px}}
 .bar{{position:sticky;top:0;background:#fff;padding:8px 0;border-bottom:1px solid #ddd;font-weight:600}}
 .card{{display:none;margin:18px 0}}
 .card.active{{display:block}}
 .card img{{max-width:100%;border:1px solid #ccc;border-radius:6px}}
 .meta{{color:#777;font-size:13px;margin:6px 0}}
 .stem{{font-weight:600;margin:10px 0}}
 .opts{{display:flex;flex-direction:column;gap:8px}}
 .opt{{text-align:left;padding:10px 12px;border:1px solid #bbb;border-radius:6px;background:#fafafa;cursor:pointer;font-size:15px}}
 .opt:hover{{background:#f0f0f0}}
 .opt.correct{{background:#d8f5d8;border-color:#2e9e2e}}
 .opt.wrong{{background:#f7d6d6;border-color:#c23b3b}}
 .opt:disabled{{cursor:default}}
 .fb{{margin-top:10px;font-weight:600;min-height:22px}}
 .next{{margin-top:12px;padding:8px 16px;font-size:15px;cursor:pointer}}
 #summary{{display:none;font-size:18px;font-weight:700;margin-top:20px}}
</style></head><body>
<h1>{title}</h1>
<div class="bar">Score: <span id="score">0</span> / <span id="answered">0</span></div>
{cards}
<button class="next" id="next">Next &#9654;</button>
<div id="summary"></div>
<script>
 const cards=[...document.querySelectorAll('.card')];let cur=0,score=0,answered=0;
 const scoreEl=document.getElementById('score'),ansEl=document.getElementById('answered');
 const nextBtn=document.getElementById('next'),summary=document.getElementById('summary');
 function show(i){{cards.forEach((c,k)=>c.classList.toggle('active',k===i));}}
 cards.forEach(card=>{{
   card.querySelectorAll('.opt').forEach(opt=>{{
     opt.addEventListener('click',()=>{{
       if(card.dataset.done)return;card.dataset.done='1';
       const correct=card.querySelector('.opt[data-correct]');
       card.querySelectorAll('.opt').forEach(o=>{{o.disabled=true;if(o.dataset.correct)o.classList.add('correct');}});
       const ok=opt.dataset.correct==='1';if(!ok)opt.classList.add('wrong');
       answered++;if(ok)score++;scoreEl.textContent=score;ansEl.textContent=answered;
       card.querySelector('.fb').textContent=ok?'\\u2713 Correct':('\\u2717 Correct: '+correct.textContent.replace(/^[A-D]\\. /,''));
     }});
   }});
 }});
 nextBtn.addEventListener('click',()=>{{
   if(cur<cards.length-1){{cur++;show(cur);}}
   else{{cards.forEach(c=>c.classList.remove('active'));nextBtn.style.display='none';
     summary.style.display='block';
     summary.textContent='Done \\u2014 '+score+' / '+cards.length+'  ('+Math.round(100*score/Math.max(cards.length,1))+'%)';}}
 }});
 document.addEventListener('keydown',e=>{{const m={{a:0,b:1,c:2,d:3}};if(e.key in m){{const c=cards[cur];if(c){{const b=c.querySelectorAll('.opt')[m[e.key]];if(b)b.click();}}}}}});
 if(cards.length)show(0);
</script></body></html>"""


def _mask_highlight(img, bbox):
    from PIL import ImageDraw
    W, H = img.size
    x, y = int(bbox[0] * W), int(bbox[1] * H)
    w, h = int(bbox[2] * W), int(bbox[3] * H)
    pad = max(3, int(0.005 * W))
    box = [x - pad, y - pad, x + w + pad, y + h + pad]
    d = ImageDraw.Draw(img)
    d.rectangle(box, fill=(238, 238, 238))                       # blank the label text
    d.rectangle(box, outline=(214, 40, 40), width=max(2, int(0.004 * W)))  # highlight
    d.text(((box[0] + box[2]) // 2 - 4, (box[1] + box[3]) // 2 - 8), "?", fill=(214, 40, 40))
    return img


def _data_uri(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    result = {"success": False, "html_path": args.out, "question_count": 0, "error": None}
    try:
        from PIL import Image
        raw = sys.stdin.buffer.read().decode("utf-8-sig").strip()
        if not raw:
            raise ValueError("no quiz-spec on stdin")
        spec = json.loads(raw)
        title = spec.get("title") or "LearnKit image quiz"
        questions = spec.get("questions") or []

        # validate (image exists + opens) so the rendered total is accurate
        valid = []
        for q in questions:
            ip = q.get("image_path")
            if not ip or not os.path.exists(ip):
                continue
            try:
                img = Image.open(ip).convert("RGB")
            except Exception:
                continue
            valid.append((q, img))

        total = len(valid)
        cards = []
        for idx, (q, img) in enumerate(valid):
            _mask_highlight(img, q["target_bbox"])
            uri = _data_uri(img)
            opts = q.get("options") or []
            ai = int(q.get("answer_index", 0))
            btns = []
            for k, opt in enumerate(opts):
                correct = ' data-correct="1"' if k == ai else ''
                letter = "ABCD"[k] if k < 4 else str(k + 1)
                btns.append(BTN_TMPL.format(correct=correct, letter=letter,
                                            text=htmllib.escape(str(opt))))
            stem = htmllib.escape(q.get("stem") or "What is the name of the highlighted structure?")
            cards.append(CARD_TMPL.format(i=idx, n=idx + 1, total=total, uri=uri,
                                          stem=stem, buttons="\n".join(btns)))

        page = PAGE_TMPL.format(title=htmllib.escape(title), cards="\n".join(cards))
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(page)
        result["question_count"] = total
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)

    print(json.dumps(result))  # ASCII-safe stdout


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test, verify it passes**

Run: `python scripts/tests/test_image_quiz.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit** *(reference only — skip this session)*

```bash
git add scripts/image_quiz.py scripts/tests/test_image_quiz.py
git commit -m "feat: add image_quiz.py MCQ HTML builder"
```

---

### Task 2: `/lkimage quiz` flow + scripts doc

**Files:**
- Modify: `.claude/commands/lkimage.md`
- Modify: `.claude/commands/lkscripts.md`

- [ ] **Step 1: Add `/lkimage quiz` section to `lkimage.md`**

After `### \`/lkimage {image_id}\` — one image` block (before `### \`/lkimage remove\``), insert:

```markdown
### `/lkimage quiz {course} {scope}` — image MCQ quiz (Phase 2)
Generate a self-contained HTML page of "name the highlighted structure" MCQs (4 options A–D), open it in the browser. `{scope}` = same tokens as `/lkquiz` (`week_01`, ranges, lists, `exam_1`).

1. Read `image_bank.json`. **Eligible targets** = structures with `label_bbox != null` whose `unit_id` ∈ scope.
2. Pick up to ~15 targets, spread across images/units (cap at eligible count). Skip if 0 eligible (see Edge cases).
3. Per target build 4 **options**: the correct `name` + **3 distractors** — other structure names in scope, **prefer same `type`**; fall back to any scope names, then course-wide. Need ≥ 4 distinct names or skip that target. Shuffle; record `answer_index`.
4. Assemble a quiz-spec JSON and pipe it to `image_quiz.py` (see lkscripts.md):
   ```powershell
   $out = "{savedataRoot}\courses\{slug}\quiz\lkimage_quiz_{scope}_{YYYYMMDD}.html"
   $r = ($specJson | & $pythonExe (Join-Path $scriptsRoot "image_quiz.py") --out $out) | ConvertFrom-Json
   if ($r.success) { Start-Process $r.html_path }    # open in browser
   ```
5. Log per course: `- [IMAGE] Quiz generated — {N} Qs ({scope})`. No `progress.json` write (the page scores client-side).

**Edge cases**: 0 eligible targets → `"No image-bank questions for {scope}. Run /lkimage to check coverage."` · all `label_bbox` null (Tesseract absent at capture) → `"No structures have label positions (boxes). Re-ingest with Tesseract installed to enable image quizzes."` · < 4 distinct names course-wide → `"Need at least 4 labeled structures to build options."`
```

- [ ] **Step 2: Add `image_quiz.py` to `lkscripts.md`**

After `image_extract.py` block (before `image add` line), insert:

````markdown
**`image_quiz.py` — build a self-contained image-MCQ HTML page (reads quiz-spec on stdin):**
```powershell
$specJson = @'
{ "title": "PTHER 350A — Week 6 (image quiz)", "questions": [
  { "image_path": "C:\\...\\images\\source_..._p05.png", "image_w": 1100, "image_h": 1500,
    "target_bbox": [0.62,0.40,0.10,0.03], "stem": "What is the name of the highlighted structure?",
    "options": ["Talus","Calcaneus","Navicular","Cuboid"], "answer_index": 0 } ] }
'@
$r = ($specJson | & $pythonExe (Join-Path $scriptsRoot "image_quiz.py") --out $htmlPath) | ConvertFrom-Json
# success → { html_path, question_count }.  Then: Start-Process $r.html_path
```
Masks each `target_bbox` (Pillow), embeds images as base64 (single offline file). The agent builds `options` + `answer_index` (correct + 3 distractors); the script only renders.
````

- [ ] **Step 3: Verify**

Run: `grep -c "lkimage quiz\|image_quiz" .claude/commands/lkimage.md .claude/commands/lkscripts.md`
Expected: matches in both.

- [ ] **Step 4: Commit** *(reference only — skip)*

```bash
git add .claude/commands/lkimage.md .claude/commands/lkscripts.md
git commit -m "feat: add /lkimage quiz flow + image_quiz.py doc"
```

---

### Task 3: Logging + CLAUDE + README

**Files:**
- Modify: `.claude/commands/lklogging.md`
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: `lklogging.md` — extend `[IMAGE]` row**

Replace `[IMAGE]` row:

```markdown
| `[IMAGE]` | `Captured {N} illustration(s) from {filename} → {unit}` · `Quiz generated — {N} Qs ({scope})` · `Removed {image_id}` |
```

- [ ] **Step 2: `CLAUDE.md` §6 — add quiz to `/lkimage` variants**

Replace `/lkimage` Full-spec line:

```markdown
Full spec in `.claude/commands/lkimage.md`. Variants: `/lkimage {course}` (summary), `/lkimage {course} {scope}` (review), `/lkimage {image_id}`, `/lkimage quiz {course} {scope}` (image MCQ quiz → HTML), `/lkimage remove {image_id}`. Labeled illustrations captured during ingest; structure labels are `[slide]` (grounded) or `[AI — verify]` (flagged).
```

- [ ] **Step 3: `README.md` — extend `/lkimage` row**

Replace `/lkimage` row:

```markdown
| `/lkimage [course] [scope]` | Review the image bank, or `/lkimage quiz` for an image MCQ quiz (HTML) |
```

- [ ] **Step 4: Verify**

Run: `grep -c "Quiz generated" .claude/commands/lklogging.md && grep -c "lkimage quiz\|image MCQ" CLAUDE.md README.md`
Expected: matches.

- [ ] **Step 5: Commit** *(reference only — skip)*

```bash
git add .claude/commands/lklogging.md CLAUDE.md README.md
git commit -m "docs: register /lkimage quiz in logging, CLAUDE, README"
```

---

### Task 4: Full-suite verification + real end-to-end

**Files:** none (verification only)

- [ ] **Step 1: Run whole test suite**

Run: `python -m unittest discover -s scripts/tests -p "test_*.py" -v`
Expected: PASS — `test_pool` (8) + `test_extract` (5) + `test_image` (6) + `test_image_extract` (3) + `test_image_quiz` (4) = 26 tests.

- [ ] **Step 2: End-to-end on a real captured page**

Run:
```bash
python - <<'PY'
import json, subprocess, sys, tempfile, pathlib, shutil
out = tempfile.mkdtemp()
pdf = "savedata/courses/pther_350a/materials/week_06_foot/source_the_bones_of_the_foot.pdf"
# render page images
r = subprocess.run([sys.executable,"scripts/image_extract.py","--file",pdf,"--out",out],capture_output=True,text=True)
d = json.loads(r.stdout)
pg = d["pages"][4]  # an interior page
spec = {"title":"E2E image quiz","questions":[
  {"image_path":pg["image_path"],"image_w":pg["image_w"],"image_h":pg["image_h"],
   "target_bbox":[0.5,0.4,0.12,0.04],"stem":"What is the name of the highlighted structure?",
   "options":["Talus","Calcaneus","Navicular","Cuboid"],"answer_index":1}]}
html = str(pathlib.Path(out)/"quiz.html")
q = subprocess.run([sys.executable,"scripts/image_quiz.py","--out",html],input=json.dumps(spec),capture_output=True,text=True)
res = json.loads(q.stdout)
txt = pathlib.Path(html).read_text(encoding="utf-8")
print("quiz:",res["success"],"| qs:",res["question_count"],"| has_img:", "data:image/png;base64," in txt, "| offline:", ("http://" not in txt and "https://" not in txt))
shutil.rmtree(d["pages_dir"],ignore_errors=True); shutil.rmtree(out,ignore_errors=True)
PY
```
Expected: `quiz: True | qs: 1 | has_img: True | offline: True`.

- [ ] **Step 3: Confirm no stray real writes**

Run: `ls scripts/tmp_pages/ 2>/dev/null | grep -i foot && echo "LEFTOVER" || echo "clean"`
Expected: `clean`.

---

## Self-Review

**Spec coverage:**
- §1 command `/lkimage quiz {scope}` → Task 2 (lkimage.md flow). ✓
- §2 `image_quiz.py` (mask+highlight, base64, HTML) → Task 1. ✓
- §3 HTML/JS self-contained MCQ → Task 1 (PAGE_TMPL). ✓
- §4 agent selection + distractors → Task 2 (lkimage.md). ✓
- §5 storage/open/logging → Task 2 (Start-Process) + Task 3 (log row). ✓
- §6 edge cases → Task 2 (Edge cases block) + Task 1 (missing-image skip). ✓
- §7 testing → Task 1 tests + Task 4. ✓
- §8 out of scope — respected (no progress write-back). ✓

**Placeholder scan:** No TBD/TODO; full code + literal insertion text. ✓

**Type consistency:** quiz-spec keys (`image_path`, `target_bbox`, `options`, `answer_index`, `stem`, `title`) identical across `image_quiz.py`, tests, `lkimage.md`, `lkscripts.md`. Output keys `success`/`html_path`/`question_count`/`error` consistent. HTML markers `class="card"`, `class="opt"`, `data-correct="1"` match between `image_quiz.py` and test assertions. ✓

**Note:** JS in `PAGE_TMPL` uses `{{`/`}}` to escape literal braces inside `str.format` template; only real substitutions are `{title}` and `{cards}`. The ✓/✗/▶/— glyphs written as `\u…` JS escapes / HTML entities so file stays clean and stdout JSON stays ASCII.
```
