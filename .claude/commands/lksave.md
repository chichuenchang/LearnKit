Base context (path variables, behavioral rules) loaded from CLAUDE.md. Data schemas in lkschemas.md. Python script protocol and data_writer.py reference in lkscripts.md. Log entry format spec in lklogging.md.

## `/lksave` — Reconcile pending writes

Recovery command. Long session, agent may drift, miss writes. Reviews session actions from context, checks expected file writes happened, writes missing ones.

Read lkschemas.md and lklogging.md before reconciling.

**Per action type — verify, recover if missing:**

| Action | Expected writes |
|--------|----------------|
| `/lkquiz` | `quiz_history` entry in `progress.json` · `[QUIZ]` one-liner in `courses\{slug}\activity_log.md` · `weak_areas` + `status` updated |
| `/lkingest` | `materials_ingested` count in `progress.json` · `[INGEST]` in `courses\{slug}\activity_log.md` · source archived to `raw\{unit}\` · image-rich note → `materials\{unit}\` · (PDF diagrams) captured to `image_bank.json` (+ `images\`) + `[IMAGE]` log · (quiz/exam/practice files) extracted problems in `problem_pool.json` + `[POOL]` log |
| `/lkpool` | `problems[]` entry in `problem_pool.json` · `[POOL]` in `courses\{slug}\activity_log.md` |
| `/lkdeadlines add` | Entry in `data\global_deadlines.json` · `[DEADLINE]` in `courses\{slug}\activity_log.md` |

**Steps:**
1. List all commands run this session (from context)
2. Each: read relevant files, check for expected entries
3. Missing entry → write now via data_writer.py, lklogging.md format — use `run_in_background: true` on log entry writes so they don't block
4. Present → skip silently

**Report:**
```
/lksave — Reconciliation complete
──────────────────────────────────────────
Recovered (3):
  ✓ [QUIZ]  BIOL 201 | {display_name} — score entry written to progress.json
  ✓ [QUIZ]  BIOL 201 | {display_name} — log entry written to activity_log.md
Already committed (5): skipped
──────────────────────────────────────────
```

Nothing to recover → `"All data writes confirmed — nothing missing."`
