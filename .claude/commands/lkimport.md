Base context (path variables, behavioral rules) loaded from CLAUDE.md. Python script protocol and data_writer.py reference in lkscripts.md.

## `/lkimport <path>` — Restore savedata from zip

Pre-check: path exists and ends in `.zip` → else: `"File not found or not a .zip: {path}"`

If `savedata/` already has data → warn:
```
⚠ savedata/ already contains data.
Import will merge — existing files will be overwritten by zip contents.
machine.config.json will NOT be touched.
Type YES to continue:
```

Run `import_savedata.py --zip $importPath --savedata $savedataRoot`.

After extract: re-run startup Steps 1–4 (reload JSONs, reprint banner).

Report:
```
Import complete — learnkit_export_slimj_20260511.zip
Restored : N files (3 courses, 14 notes, 8 quiz logs, all deadlines)
Skipped  : machine.config.json (kept local config)
```

Log: `- [IMPORT] savedata restored from {filename}`
