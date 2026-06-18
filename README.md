# LearnKit

Claude Code study agent for university courses. Drop course materials — syllabuses, lecture slides, PDFs. LearnKit builds study guides, runs adaptive quizzes, tracks progress, keeps focus on what gets graded.

Works with any course. Each student keeps own private data.

---

## Requirements

- [Claude Code](https://claude.ai/code)
- Python 3.10+
- PowerShell (Windows) or WSL

### Python packages

```bash
pip install pdfplumber python-pptx python-docx pymupdf pytesseract
```

| Package | Purpose |
|---------|---------|
| `pdfplumber` | Extract text from PDF lecture notes, syllabuses |
| `python-pptx` | Extract text from PowerPoint slides |
| `python-docx` | Extract text from Word docs |
| `pymupdf` | Render scanned PDF pages as images for visual extraction |
| `paddleocr` + `paddlepaddle-gpu` | (Optional, **primary** OCR) GPU label detection for image bank. Install paddle from Paddle CUDA index: `pip install paddlepaddle-gpu -i https://www.paddlepaddle.org.cn/packages/stable/cu126/` then `pip install paddleocr`. |
| `pytesseract` | (Optional, **fallback** OCR) Detect labels + positions via Tesseract binary (UB-Mannheim build on Windows) when PaddleOCR absent. No OCR → image-only slides captured without label boxes. |

> `/lksetup` detects Python interpreter, offers to install missing packages automatically.

---

## Getting Started

```bash
git clone https://github.com/yourname/learnkit.git
cd learnkit
claude
```

First launch: LearnKit detects no study data, prompts `/lksetup`.

**`/lksetup` will:**
1. Locate Python interpreter, verify packages
2. Create personal `savedata/` folder
3. Ask for name
4. Optionally link private git repo for cross-machine sync

After setup, drop syllabus into `savedata/raw/`, run `/lkingest`.

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
├── data/              ← global index, deadlines
├── courses/           ← per-course notes, progress, quiz history
├── archive/           ← completed courses
└── raw/               ← drop zone for new files
```

---

## Commands

| Command | What it does |
|---------|-------------|
| `/lksetup` | First-time onboarding, Python config, savedata init |
| `/lkingest` | Process files from `savedata/raw/` or pasted paths → self-contained image-rich notes |
| `/lkquiz [course] [scope]` | Adaptive interactive quiz |
| `/lkdeadlines` | View all upcoming deadlines |
| `/lkprogress` | Study dashboard across all courses |
| `/lkpool [course]` | Manage pool of past quiz/exam problems |
| `/lkimage [course] [scope]` | Review image bank, or `/lkimage quiz` for image MCQ quiz (HTML) |
| `/lkcourse add` | Register new course |
| `/lkcourse complete` | Archive finished course |
| `/lksave` | Reconcile missed data writes from current session |
| `/lkexport [path]` | Pack savedata into portable zip |
| `/lkimport <path>` | Restore savedata from zip |
| `/lklog` | View activity log |

---

## Moving to a New Machine

Export data on old machine, copy zip anywhere (USB, cloud drive, email), import on new machine.

**Old machine:**
```
/lkexport
```
Produces `learnkit_export_{name}_{date}.zip` in project folder.

**New machine:**
```bash
git clone https://github.com/yourname/learnkit.git
cd learnkit && claude
/lksetup
/lkimport C:\path\to\learnkit_export_name_date.zip
```

All courses, notes, quiz history, progress restore automatically. Machine-specific config (Python path) set fresh by `/lksetup` — never included in export.

---

## Supported File Types

| Type | Extensions |
|------|-----------|
| Lecture slides | `.pptx` |
| Documents | `.pdf`, `.docx` |
| Syllabuses | `.pdf`, `.docx` |
| Practice quizzes | `.pdf`, `.docx` |
| Past exams | `.pdf`, `.docx` |

---

## License

MIT
