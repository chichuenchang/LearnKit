Shared protocol file — not a user-invocable command. Referenced by all skill files.

## Python Script Protocol

Use `$pythonExe` (resolved at startup Step 0.5). Use `$scriptsRoot` for script path. Temp output goes to `$scriptsRoot\tmp_extract.json` (gitignored at project root level).

```powershell
$tmpOutput  = Join-Path $scriptsRoot "tmp_extract.json"
$scriptPath = Join-Path $scriptsRoot "extract_text.py"

$extractResult = & $pythonExe $scriptPath `
    --file "C:\full\path\to\source.file" `
    --output $tmpOutput

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
        Write-Host "Note: PDF has $($data.page_count) pages — first 20 ingested."
    }
    # Read each page image via Read tool — Claude handles natively (multimodal)
    # $data.image_paths contains absolute PNG paths, read in order
    # Generate study notes from visual page content; same tagging rules apply (Section 1 of CLAUDE.md)
    # First line of notes: "**Source**: {filename} | ... | **Note**: Scanned PDF — content read from page images"

    # Clean up after notes generated:
    $basename = [System.IO.Path]::GetFileNameWithoutExtension($data.filename)
    $pagesDir = Join-Path $scriptsRoot "tmp_pages" $basename
    Remove-Item $pagesDir -Recurse -ErrorAction SilentlyContinue
}
```

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
| `progress study` | `--savedata --course --unit` | — |
| `progress ingest` | `--savedata --course --unit` | — |
| `deadline add` | `--savedata --course-id --course-code --type --title --date` | `--time --location --details` |
| `deadline complete` | `--savedata --deadline-id` | — |
| `index update` | `--savedata --course` | — |
| `log entry` | `--savedata --entry` | `--course` (omit for global log only; include for both global + per-course) |
| `manifest add` | `--savedata --course-id --course-code --filename --method --file-type --unit --confidence --filed-path --summary-path` | `--original-path --page-count --word-count` |

**Flag notes:**
- `--course` = course slug (e.g. `pther_350a`) — used by `progress`, `index update`, `log entry`
- `--course-id` = course slug — used by `deadline add`, `manifest add`
- `--course-code` = display code (e.g. `PTHER 350A`) — used by `deadline add`, `manifest add`
- `deadline add` requires BOTH `--course-id` and `--course-code` (separate flags, not interchangeable)
- `log entry --course slug` writes to BOTH global and per-course logs in one call
- `log entry` without `--course` writes to global log only

**Log entry format** — always prefix with type tag:
```powershell
--entry "[DEADLINE] PTHER 350A | Added: Term Quiz 1 on 2026-05-13"   # global
--entry "[DEADLINE] Added: Term Quiz 1 on 2026-05-13" --course "pther_350a"  # both logs
```
