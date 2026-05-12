# LearnKit

A Claude Code study agent for university courses. Drop in your course materials — syllabuses, lecture slides, PDFs — and LearnKit builds study guides, runs adaptive quizzes, tracks your progress, and keeps you focused on what actually gets graded.

Works with any university course. Each student keeps their own private data.

---

## Requirements

- [Claude Code](https://claude.ai/code)
- Python 3.10+
- PowerShell (Windows) or WSL

### Python packages

```bash
pip install pdfplumber python-pptx python-docx pymupdf
```

| Package | Purpose |
|---------|---------|
| `pdfplumber` | Extract text from PDF lecture notes and syllabuses |
| `python-pptx` | Extract text from PowerPoint slides |
| `python-docx` | Extract text from Word documents |
| `pymupdf` | Render scanned PDF pages as images for visual extraction |

> `/setup` will detect your Python interpreter and offer to install missing packages automatically.

---

## Getting Started

```bash
git clone https://github.com/yourname/learnkit.git
cd learnkit
claude
```

On first launch LearnKit detects no study data and prompts you to run `/setup`.

**`/setup` will:**
1. Locate your Python interpreter and verify packages
2. Create your personal `savedata/` folder
3. Ask for your name
4. Optionally link a private git repo for cross-machine sync

After setup, drop a syllabus into `savedata/raw/` and run `/ingest`.

---

## How It Works

```
learnkit/              ← public repo (clone this)
├── CLAUDE.md          ← agent instructions
├── scripts/           ← Python extraction helpers
└── .gitignore         ← ignores savedata/

savedata/              ← your private data (gitignored)
├── user.config.json   ← your name
├── machine.config.json← Python path (never exported)
├── data/              ← global index, deadlines, manifest
├── courses/           ← per-course notes, progress, quiz history
├── archive/           ← completed courses
└── raw/               ← drop zone for new files
```

---

## Commands

| Command | What it does |
|---------|-------------|
| `/setup` | First-time onboarding, Python config, savedata init |
| `/ingest` | Process files from `savedata/raw/` or pasted paths |
| `/study [course] [unit]` | Generate a grade-focused study session |
| `/quiz [course] [scope]` | Adaptive interactive quiz |
| `/deadlines` | View all upcoming deadlines |
| `/progress` | Study dashboard across all courses |
| `/course add` | Register a new course |
| `/course complete` | Archive a finished course |
| `/save` | Reconcile any missed data writes from current session |
| `/export [path]` | Pack savedata into a portable zip |
| `/import <path>` | Restore savedata from a zip |
| `/log` | View activity log |

---

## Moving to a New Machine

Export your data on the old machine, copy the zip anywhere (USB, cloud drive, email), then import on the new machine.

**Old machine:**
```
/export
```
Produces `learnkit_export_{name}_{date}.zip` in the project folder.

**New machine:**
```bash
git clone https://github.com/yourname/learnkit.git
cd learnkit && claude
/setup
/import C:\path\to\learnkit_export_name_date.zip
```

All courses, notes, quiz history, and progress restore automatically. Machine-specific config (Python path) is set fresh by `/setup` — it is never included in the export.

---

## Supported File Types

| Type | Extensions |
|------|-----------|
| Lecture slides | `.pptx` |
| Documents | `.pdf`, `.docx` |
| Syllabuses | `.pdf`, `.docx` |
| Practice quizzes | `.pdf`, `.docx` |

---

## License

MIT
