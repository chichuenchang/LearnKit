Base context (path vars, behavioral rules) from CLAUDE.md. Python script protocol + data_writer.py ref in lkscripts.md. Data schemas in lkschemas.md (default empty JSON values).

## `/lksetup` — Onboarding + machine config

Run when `savedata/` absent, or on explicit invoke. Re-run safe.

**Step 1 — Detect project root (auto)**
Run `git rev-parse --show-toplevel` (fallback: cwd). Derive:
- `$projectRoot` = git output or cwd
- `$savedataRoot` = `Join-Path $projectRoot "savedata"`
- `$scriptsRoot`  = `Join-Path $projectRoot "scripts"`

Print paths banner.

**Step 2 — Locate Python**

Test `python` in PATH with `import pdfplumber, pptx, docx, fitz, PIL`. Pass → use `python`, print `"Python: found in PATH — packages OK"`. Sets `packages_ok: true` in machine.config.json (Step 5). (OCR pkgs paddleocr / pytesseract optional — not in gate.)

Fail → probe common locations (`%USERPROFILE%\miniconda3`, `\anaconda3`, `\AppData\Local\Programs\Python\Python311`, `\Python312`), show:
```
Python not found in PATH or packages missing.

Suggested interpreters (tested):
  [1] C:\Users\{user}\miniconda3\python.exe  ← packages OK
  [2] C:\Users\{user}\AppData\...\Python311\python.exe  ← packages MISSING
  [3] Enter path manually

Select [1-3]:
```
Packages missing but Python found → offer `pip install pdfplumber python-pptx python-docx PyMuPDF Pillow [Y/n]`. Success → `packages_ok: true`. Skip/fail → `packages_ok: false`, warn: `"Ingestion will not work until Python is configured. Run /lksetup again to fix."`

**Step 3 — Create savedata/ structure**

Create subdirs under `$savedataRoot`: `data\`, `courses\`, `archive\`, `raw\`
Create default data JSON only if absent (re-run safe):
- `data\courses_index.json` → default empty

**Step 4 — User name**
```
Your name (for display in banners — e.g., "Alex", "slimj"):
> _
```
Blank → default `"Student"`.

**Step 5 — Write config files**
Write `user.config.json` + `machine.config.json` per Section 2 schemas.
`machine.config.json` must include: `machine_id`, `python_exe`, `project_root`, `savedata_root`, `scripts_root` (absolute paths from Step 1), `packages_ok` (bool — true only if Step 2 passed).

**Step 6 — Summary**
```
──────────────────────────────────────────────────────
Setup complete!

User      : {$userName}
Python    : {$pythonExe}  [OK / ⚠ packages missing]
savedata/ : {$savedataRoot}
──────────────────────────────────────────────────────
Next steps:
  1. Drop a syllabus into savedata\raw\ or paste its path.
  2. Run /lkingest to load the syllabus and create your first course.
  3. Run /lkquiz to start studying.
  4. Run /lkexport to back up your data anytime.
──────────────────────────────────────────────────────
```

**Re-run on existing savedata** → show menu:
```
savedata/ already exists. What would you like to do?
  [1] Reconfigure Python path only
  [2] Full re-setup (safe — will not overwrite existing data)
  [3] Cancel
```
