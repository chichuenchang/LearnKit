Base context (path vars, behavioral rules) from CLAUDE.md. Python script protocol + data_writer.py ref in lkscripts.md.

## `/lkexport [path]` — Pack savedata into zip

**Included:**
```
savedata\data\
savedata\courses\**\*.md           (study notes only — no source binaries)
savedata\courses\**\data\*.json    (course_structure, problem_pool)
savedata\archive\
savedata\user.config.json
```

**Excluded:**
```
machine.config.json            (machine-specific — set fresh on each machine via /lksetup)
raw\                           (drop zone — transient)
**/source_*.*                  (original source files — re-ingestable from course portal)
```

Output filename: `learnkit_export_{user_name}_{YYYYMMDD}.zip`
Default location: `$projectRoot`. Override via optional `[path]` arg.

Run `export_savedata.py --savedata $savedataRoot --output $exportPath`. Parse JSON result. Report:
```
Export complete — learnkit_export_slimj_20260511.zip
Location : C:\Users\{user}\Projects\learnkit\
Contents : N files (3 courses, 14 notes, 8 quizzes)
Size     : 142 KB
```
