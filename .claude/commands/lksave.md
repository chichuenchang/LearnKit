Base context (path variables, behavioral rules) loaded from CLAUDE.md. Data schemas in lkschemas.md. Python script protocol and data_writer.py reference in lkscripts.md. Log entry format spec in lklogging.md.

## `/lksave` — Reconcile pending data writes

Recovery command for long sessions where agent may have drifted and missed writing data. Reviews actions taken this session from conversation context, checks that all expected file writes occurred, and writes any that are missing.

Read lkschemas.md and lklogging.md before starting reconciliation.

**For each action type, verify and recover if missing:**

| Action | Expected writes |
|--------|----------------|
| `/lkquiz` | `quiz_history` entry in `progress.json` · `[QUIZ]` one-liner in `courses\{slug}\activity_log.md` · `weak_areas` + `status` updated |
| `/lkingest` | `materials_ingested` count in `progress.json` · `[INGEST]` in `courses\{slug}\activity_log.md` |
| `/lkdeadlines add` | Entry in `data\global_deadlines.json` · `[DEADLINE]` in `courses\{slug}\activity_log.md` |

**Steps:**
1. List all commands run this session (from context)
2. For each, read the relevant files and check for the expected entries
3. Missing entry → write it now using lklogging.md format via data_writer.py — use `run_in_background: true` on the tool call for log entry writes so they don't block
4. Already present → skip silently

**Report:**
```
/lksave — Reconciliation complete
──────────────────────────────────────────
Recovered (3):
  ✓ [QUIZ]  BIOL 201 | Unit 1 — score entry written to progress.json
  ✓ [QUIZ]  BIOL 201 | Unit 1 — log entry written to activity_log.md
Already committed (5): skipped
──────────────────────────────────────────
```

Nothing to recover → `"All data writes confirmed — nothing missing."`
