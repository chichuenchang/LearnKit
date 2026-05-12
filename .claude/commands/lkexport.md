Base context (path variables, behavioral rules) loaded from CLAUDE.md. Python script protocol and data_writer.py reference in lkscripts.md.

## `/lkexport [path]` — Pack savedata into a zip file

**What's included:**
```
savedata\data\
savedata\courses\**\*.md       (study notes only — no source binaries)
savedata\archive\
savedata\user.config.json
```

**What's excluded:**
```
machine.config.json            (machine-specific — set fresh on each machine via /lksetup)
raw\                           (drop zone — transient)
**/source_*.*                  (original source files — re-ingestable from course portal)
```

Output filename: `learnkit_export_{user_name}_{YYYYMMDD}.zip`
Default output location: `$projectRoot`. Override with optional `[path]` argument.

Run `export_savedata.py --savedata $savedataRoot --output $exportPath`. Parse JSON result. Report:
```
Export complete — learnkit_export_slimj_20260511.zip
Location : C:\Users\{user}\Projects\learnkit\
Contents : N files (3 courses, 14 notes, 8 quiz logs, deadlines)
Size     : 142 KB
```

Log: `- [EXPORT] savedata packed → {filename} ({size_kb} KB)`
