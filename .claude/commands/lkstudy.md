Base context (path variables, schemas, behavioral rules, Section 1 tagging, Section 11 logging) loaded from CLAUDE.md.

## `/lkstudy {course_code} {unit_id}` — Generate a study session

Multiple active + no course → ask. Single active → assume.

`{unit_id}`: `unit_01`, `unit_1`, `u1`, `"unit 1"`, or display name (fuzzy match).

**Workflow:**

1. Read `courses\{slug}\misc.md`. Has entries → show under `## Course Notes` before study content.
2. Read all `.md` in `courses\{slug}\materials\{unit_slug}\` + relevant `multi_unit\` files.
3. Check `progress.json` for unit's weak areas — address first.
4. Check `global_deadlines.json` filtered by `course_id` for next exam covering this unit — set urgency tone from date.

**Output structure:**
```
# Study Session — [Course Code] Unit N: [Unit Name]
[EXAM IN N DAYS — urgency if applicable]

## Learning Objectives
[From syllabus — each objective heads what follows]

## [Topic from Learning Objective 1]
[EXAM-CRITICAL] Fact stated exam-style...
[LIKELY TESTED]  Fact...
[LOW EXAM VALUE] One-line background only.

## Key Terms
| Term | Definition | Exam Probability |
...

## Weak Areas from Past Quizzes
[If any — extra detail on these topics]

## Likely Exam Questions on This Unit
[5-10 probable questions — no answers, prompt recall only]
```

**After delivering study content**, write data using `data_writer.py`:

```powershell
# Increment study_sessions
$result = (& $pythonExe $writerPath progress study `
    --savedata $savedataRoot --course {course_id} --unit {unit_slug}) | ConvertFrom-Json

# Log entry (writes to global log + per-course log)
$result = (& $pythonExe $writerPath log entry `
    --savedata $savedataRoot --course {course_id} `
    --entry "- [STUDY] {course_code} | Unit N: {unit_name} — {topic summary, ≤8 words}") | ConvertFrom-Json
```

See Section 11 of CLAUDE.md for log entry format.

**Web research**: Only if user explicitly asks.
- Tier 1 (free): `.edu` and `.ac.uk` domains, PubMed/PMC, official textbook publisher sites (Elsevier, Springer, Wiley open-access), Wikipedia (definitions only — never for exam facts)
- Tier 2 (with label): Any accredited academic source not in Tier 1 — label `[WEB — {domain}]`
- Tier 3 (never): Reddit, Quizlet, Chegg, CourseHero, student blogs, Rate My Professor, any crowd-sourced content
- Web differs from course materials → note: `"[Note: course materials say X; this source says Y — follow course materials for exams]"`

Append at end of every study session: `"To supplement with web research (Tier 1 sources only), ask me to search for [topic]."`
