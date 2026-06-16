Shared protocol file — not a user-invocable command. Referenced by all skill files.

## Tuning config — `scripts\config.json`

Ingestion/render tuning knobs live in `scripts\config.json` (committed). `scripts\lkconfig.py` loads it with baked-in fallback defaults, so a missing/partial/malformed file never breaks ingestion. Edit values there — no code change needed.

| Key | Used by | Meaning |
|-----|---------|---------|
| `scanned_words_per_page_threshold` | extract_text | below this words/page → PDF treated as scanned |
| `max_scanned_pages` | extract_text | scanned-PDF page render cap (CLI `--max-pages` overrides) |
| `image_max_pages` | image_extract | page render cap for image bank (CLI `--max-pages` overrides) |
| `auto_split_pages` | pdf_split | PDFs over this many pages auto-split into ≤N-page parts (CLI `--chunk` overrides; 0 disables) |
| `textlayer_min_words` | image_extract | min text-layer words before OCR fallback |
| `ocr_min_conf` | image_extract | min OCR word confidence (0–100) to keep a label box |
| `render_scale` | extract_text, image_extract | fitz Matrix scale (PDF points → pixels) |
| `passing_score` | data_writer | quiz score-pct at/above which a unit counts as passed |

CLI `--max-pages` (per-file) takes precedence over the config default for that run.

## Python Script Protocol

Use `$pythonExe` (loaded at startup Step 0 from machine.config.json). Use `$scriptsRoot` for script path. Temp output goes to `$scriptsRoot\tmp_extract.json` (gitignored at project root level).

```powershell
$tmpOutput  = Join-Path $scriptsRoot "tmp_extract.json"
$scriptPath = Join-Path $scriptsRoot "extract_text.py"

$extractResult = & $pythonExe $scriptPath `
    --file "C:\full\path\to\source.file" `
    --output $tmpOutput
    # optional: --max-pages N  (scanned-PDF render cap; default 60, 0 = no cap)

$data = Get-Content $tmpOutput | ConvertFrom-Json
if (-not $data.success) {
    Write-Host "Extraction failed: $($data.error)"
    # skip this file
}
```

Clean up after reading:
```powershell
Remove-Item $tmpOutput -ErrorAction SilentlyContinue
```

**Scanned PDF branch** — when `$data.scanned -eq $true`:
```powershell
if ($data.scanned) {
    if ($data.capped) {
        # Surface to user before proceeding
        Write-Host "Note: PDF has $($data.page_count) pages — first 60 ingested. Re-run with --max-pages 0 (or a higher N) to process all."
    }
    # Read each page image via Read tool — Claude handles natively (multimodal)
    # $data.image_paths contains absolute PNG paths, read in order
    # Generate study notes from visual page content; same tagging rules apply (Section 1 of CLAUDE.md)
    # First line of notes: "**Source**: {filename} | ... | **Raw material**: raw/{unit_slug}/source_{slug}.{ext} | **Note**: Scanned PDF — content read from page images"

    # Clean up after notes generated:
    $pagesDir = $data.pages_dir   # sanitized dir reported by extract_text.py (handles trailing-space / illegal-char filenames)
    if ($pagesDir) { Remove-Item $pagesDir -Recurse -ErrorAction SilentlyContinue }
}
```

---

## `pdf_split.py` — auto-split large PDFs (lkingest step 0)

Run **before** extraction for PDFs. Splits a PDF over `auto_split_pages` into sequential ≤N-page part PDFs so each part runs the pipeline on its own (bounded vision cost, one note per part).

```powershell
$split = (& $pythonExe (Join-Path $scriptsRoot "pdf_split.py") `
    --file "C:\full\path\source.pdf" --out (Join-Path $scriptsRoot "tmp_split")) | ConvertFrom-Json
# optional: --chunk N  (max pages/part; default = config auto_split_pages; 0 disables)
# $split.split  → bool;  $split.parts[] = { path, index, part_count, from_page, to_page, pages }
foreach ($p in $split.parts) { <# ingest $p.path as its own file: steps 1–7 #> }
Remove-Item (Join-Path $scriptsRoot "tmp_split") -Recurse -ErrorAction SilentlyContinue
```
`split:false` (page_count ≤ chunk, or chunk ≤ 0) → `parts` holds one entry pointing at the **original** file, so the loop is uniform. When `split:true`, archive the original to raw once; the part PDFs are derived (regenerable) and live under `tmp_split` — clean them up after ingest. Non-PDF input → `success:false` (skip; only PDFs split).

---

## `data_writer.py` — validated structured writes (no temp file)

```powershell
$writerPath = Join-Path $scriptsRoot "data_writer.py"
$result = (& $pythonExe $writerPath progress quiz `
    --savedata $savedataRoot `
    --course "biol_201" `
    --unit "unit_01_cell_structure" `
    --score-pct 78.0 --correct 14 --total 18 --incorrect 3 --skipped 1 `
    --weak-topics "cell cycle phases,membrane transport") | ConvertFrom-Json
if (-not $result.success) {
    Write-Host "Write failed: $($result.error)"
}
```

Output lands directly on stdout — no temp file, no cleanup needed. Same error-check pattern for all subcommands.

### Complete subcommand reference

Use these exact flags. Do not guess — wrong flags cause silent failure or ambiguous-option errors.

| Subcommand | Required flags | Optional flags |
|------------|---------------|----------------|
| `progress quiz` | `--savedata --course --unit --score-pct --correct --total --incorrect` | `--skipped --partial --adaptive --weak-topics "a,b" --mcq "11/13" --sa "2/5"` |
| `progress ingest` | `--savedata --course --unit` | — |
| `pool add` | `--savedata --course` | — (reads JSON array of problems from stdin) |
| `pool remove` | `--savedata --course --problem-id` | — |
| `image add` | `--savedata --course` | — (reads JSON array of image records from stdin) |
| `image remove` | `--savedata --course --image-id` | — |
| `deadline add` | `--savedata --course-id --course-code --type --title --date` | `--time --location --details` |
| `deadline complete` | `--savedata --deadline-id` | — |
| `notes write` | `--dest` | — (reads content from stdin; raw write, no figure embedding — prefer `notes_embed.py` for notes) |
| `log entry` | `--savedata --course --entry` | — |

**Flag notes:**
- `--course` = course slug (e.g. `pther_350a`) — used by `progress`, `pool`, `log entry`
- `--course-id` = course slug — used by `deadline add`
- `--course-code` = display code (e.g. `PTHER 350A`) — used by `deadline add`
- `deadline add` requires BOTH `--course-id` and `--course-code` (separate flags, not interchangeable)
- `log entry --course slug` writes to that course's `activity_log.md`

**`pool add` — batch problem write (reads stdin, like `notes write`):**
```powershell
$problemsJson = @'
[ { "question": "Which nerve innervates gluteus medius?", "answer": "Superior gluteal nerve", "question_type": "mcq", "options": ["Superior gluteal nerve","Sciatic nerve"], "unit_id": "week_03", "unit_slug": "week_03_hip_joint_gluteal_region", "topic": "Nerves of gluteal region", "source": "Midterm 1 2025", "source_file": "source_midterm1.pdf", "source_type": "past_exam", "verbatim": true } ]
'@
$result = ($problemsJson | & $pythonExe $writerPath pool add `
    --savedata $savedataRoot --course "pther_350a") | ConvertFrom-Json
if (-not $result.success) { Write-Host "Pool write failed: $($result.error)" }
# success → { added, skipped, ids[] }
```
`--course` is the course slug. Each problem is one object in the array; one call writes many. `question_type` validated against the allowed set; duplicate question text (normalized) is skipped.

**Image-based problems** — add a `figure` object to any problem whose figure is part of the question: `"figure": { "image_path": "<abs path to a persistent PNG under materials\\{unit}\\images>", "bbox": [x,y,w,h]|null, "caption": "..." }`. `bbox` (normalized 0–1) crops the display to the figure region; `null` = whole image. Stored only when `image_path` is present (bad/missing → `figure:null`, no error). Served via `image_quiz.py` (see below), not the terminal loop.

**`image_extract.py` — render pages + detect label boxes (for the image bank):**
```powershell
$r = (& $pythonExe (Join-Path $scriptsRoot "image_extract.py") `
    --file "C:\full\path\source.pdf" --out (Join-Path $scriptsRoot "tmp_pages")) | ConvertFrom-Json
# optional: --max-pages N  (page cap; default 60, 0 = no cap). $r.capped = true when pages dropped.
# $r.pages[] = { page, image_path, image_w, image_h, source(textlayer|ocr|none), words[] }
# words[] = { text, bbox [x,y,w,h normalized 0-1], conf }
# Clean up $r.pages_dir after building image records.
```
Label boxes come from the PDF text layer (`source:"textlayer"`, exact) or OCR (`source:"ocr"` — PaddleOCR primary on GPU, Tesseract fallback). No OCR engine available → image-only pages return `source:"none"` with no boxes (graceful). The agent classifies which words label parts/regions of the figure and does the flagged AI-fill; it does NOT invent coordinates.

**`image add` — batch image-record write (reads stdin, like `pool add`):** one JSON array of image records → `image_bank.json`; assigns `img_{course}_{NNN}`, dedups by `(source_file, page, image_path)`.

**`image_bank_build.py` — batch image-bank builder (reads a capture spec on stdin):** for re-ingest of a deck where `image_extract.py` already rendered pages. Crops each slide/half, matches printed label phrases against the page text-layer to derive label boxes, then writes records via `image add`. For one-off ingest the agent builds the record array inline (lkingest.md step 7b) — use this only for batch passes.
```powershell
$spec = @'
{ "savedata": "<savedataRoot>", "course": "pther_350a",
  "img_json": "C:\\...\\tmp_pages\\img.json", "pages_dir": "C:\\...\\tmp_pages\\source_foot",
  "images_dir": "<savedataRoot>\\courses\\pther_350a\\materials\\week_06_foot\\images",
  "image_path_prefix": "materials/week_06_foot/images",
  "slug": "source_foot", "unit_id": "week_06", "unit_slug": "week_06_foot",
  "source_file": "source_foot.pdf",
  "captures": [ { "page": 5, "half": "top", "title": "The Talus",
                  "structures": [ ["Talus","bone"], ["Calcaneus","bone"] ] } ] }
'@
$r = ($spec | & $pythonExe (Join-Path $scriptsRoot "image_bank_build.py")) | ConvertFrom-Json
# success → { success, added, skipped, ids[], report[] }.  report[] e.g. "p5t:1/2" = labels boxed/total.
```
`half` ∈ `top|bottom|full` (2-up handout → `top`/`bottom`; single-slide page → `full`). Only phrases found in the text-layer get a `label_bbox`; unmatched structures are dropped (coverage shown in `report`). Records carry `label_source:"textlayer"`.

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
Per question: `image_path`, `stem`, `options`, `answer_index` (required); `target_bbox` and `crop_bbox` optional (normalized `[x,y,w,h]`).
- **Image-bank quiz** (`/lkimage quiz`): set `target_bbox` → the region is blanked + highlighted with a "?" so the student names it.
- **Figure-bearing pool problems** (`/lkquiz --html`): set `crop_bbox` = the problem's `figure.bbox` (or omit for whole image) and **no** `target_bbox` → the figure shows unmasked with the verbatim `stem`/`options`. Missing image → that question is skipped.

The agent builds `options` + `answer_index`; the script only crops/masks (Pillow) + embeds images as base64 (single offline file).

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
Token = `{{FIG: <page_png> | x,y,w,h | caption}}` (crop normalized 0-1). Each is cropped (Pillow) → base64 → `![caption](data:image/png;base64,...)` inline. No tokens → writes through unchanged (replaces `notes write` for the note step). Missing/bad page → `*(figure unavailable)*`, never crashes.

**Log entry format** — always prefix with type tag:
```powershell
--entry "[DEADLINE] Added: Term Quiz 1 on 2026-05-13" --course "pther_350a"
```
```powershell
# Global log only
Start-Job -ScriptBlock { param($e,$w,$s,$entry)
    & $e $w log entry --savedata $s --entry $entry
} -ArgumentList $pythonExe,$writerPath,$savedataRoot,$logEntry | Out-Null

# Both global + per-course
Start-Job -ScriptBlock { param($e,$w,$s,$entry,$c)
    & $e $w log entry --savedata $s --entry $entry --course $c
} -ArgumentList $pythonExe,$writerPath,$savedataRoot,$logEntry,$courseSlug | Out-Null
```
All other `data_writer.py` subcommands remain synchronous — their success/failure matters.
