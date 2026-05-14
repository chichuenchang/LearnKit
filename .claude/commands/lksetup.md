Base context (path variables, behavioral rules) loaded from CLAUDE.md. Python script protocol and data_writer.py reference in lkscripts.md. Data schemas in lkschemas.md (for default empty JSON values).

## `/lksetup` — New-user onboarding and machine configuration

Run when `savedata/` does not exist, or explicitly invoked at any time. Safe to re-run.

**Step 1 — Detect project root (automatic)**
Path detection: same as startup Step 0. Print detected `$projectRoot` and `$savedataRoot` in a banner.

**Step 2 — Locate Python interpreter**

Test `python` in PATH with `import pdfplumber, pptx, docx`. Passes → use `python`, print `"Python: found in PATH — packages OK"`.

Fails → probe common locations (`%USERPROFILE%\miniconda3`, `\anaconda3`, `\AppData\Local\Programs\Python\Python311`, `\Python312`) and show results:
```
Python not found in PATH or packages missing.

Suggested interpreters (tested):
  [1] C:\Users\{user}\miniconda3\python.exe  ← packages OK
  [2] C:\Users\{user}\AppData\...\Python311\python.exe  ← packages MISSING
  [3] Enter path manually

Select [1-3]:
```
If packages missing but Python found → offer `pip install pdfplumber python-pptx python-docx [Y/n]`.
Allow skip with warning: `"Ingestion will not work until Python is configured. Run /lksetup again to fix."`

**Step 3 — Create savedata/ directory structure**

Create subdirs under `$savedataRoot`: `data\`, `courses\`, `archive\`, `raw\`
Create default data JSON files only if not already present (re-run safe):
- `data\courses_index.json` → default empty
- `data\global_deadlines.json` → default empty
- `data\materials_manifest.json` → default empty
- `data\activity_log.md` → header only if missing

**Step 4 — User name**
```
Your name (for display in banners — e.g., "Alex", "slimj"):
> _
```
Blank → use `"Student"` as default.

**Step 5 — Write config files**
Write `user.config.json` and `machine.config.json` per Section 2 schemas.

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
  4. Run /lkexport to back up your progress anytime.
──────────────────────────────────────────────────────
```

**Re-running on existing savedata** → show menu:
```
savedata/ already exists. What would you like to do?
  [1] Reconfigure Python path only
  [2] Full re-setup (safe — will not overwrite existing data)
  [3] Cancel
```
