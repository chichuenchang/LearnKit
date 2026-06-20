Base context (path vars, behavioral rules) from CLAUDE.md. Python script protocol + data_writer.py ref in lkscripts.md.

## `/lkimport <path>` — Restore savedata from zip

Pre-check: path exists, ends `.zip` → else: `"File not found or not a .zip: {path}"`

`savedata/` already has data → warn:
```
⚠ savedata/ already contains data.
Import will merge — existing files will be overwritten by zip contents.
machine.config.json will NOT be touched.
Type YES to continue:
```

Run `import_savedata.py --zip $importPath --savedata $savedataRoot`.

After extract: re-run startup Steps 1–3 (reload JSONs, reprint banner).

Report:
```
Import complete — learnkit_export_slimj_20260511.zip
Restored : N files (3 courses, 14 notes, 8 quizzes)
Skipped  : machine.config.json (kept local config)
```
