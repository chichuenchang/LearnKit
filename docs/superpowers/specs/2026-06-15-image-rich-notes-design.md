# Image-Rich Notes — Design Spec

**Date**: 2026-06-15
**Status**: Approved, pending implementation plan
**Project**: LearnKit (PTStudy)

---

## Goal

Make `/lkingest` produce **image-rich study notes by default**: a single self-contained `.md` where agent-chosen, agent-cropped diagrams are embedded inline (base64) next to the text they illustrate. Text and figures live together — no separate `images/` dependency for the note, no relative-path rendering failures.

---

## Decisions (from brainstorm)

| Decision | Choice |
|----------|--------|
| Note format | **Self-contained `.md`** — figures embedded as base64 data-URIs inline (one file, always renders in VS Code/Obsidian) |
| Figure cropping | **Agent-cropped** — the agent picks a crop box per figure (clean single diagrams), not whole 2-up pages |
| Mechanism | Agent writes lightweight `{{FIG:…}}` placeholders → `notes_embed.py` crops + base64-embeds them |

---

## Mechanism: placeholder → embed

The agent cannot paste 100 KB base64 blobs into a note heredoc, so it writes **placeholders** and a script expands them.

**Placeholder token (single line, inline in the note body):**
```
{{FIG: <page_png_path> | x,y,w,h | caption}}
```
- `<page_png_path>` — a rendered page PNG (from the ingest render pass).
- `x,y,w,h` — crop box, **normalized 0–1** relative to that page image.
- `caption` — alt/caption text (no `|` or `}}`).

**`scripts/notes_embed.py`:**
- `python notes_embed.py --dest <md_path>` ; reads the note text (with tokens) from **stdin**.
- For each `{{FIG:…}}`: open the page PNG, crop the normalized box (Pillow), PNG→base64, replace the token with `![caption](data:image/png;base64,…)`.
- Missing page / unreadable / malformed token → replace with `*(figure unavailable: caption)*` (never crash).
- No tokens at all → write the note through unchanged (so it cleanly replaces `notes write` for ALL notes).
- Write the final self-contained `.md` to `--dest` (utf-8). Print `{"success": true, "figures_embedded": N, "missing": M}` (ASCII-safe stdout).

Agent does judgment (which figure, where, crop region, caption); the script does crop + base64 + write. **Dep: Pillow (installed).**

---

## Ingest flow change (PDFs)

Reorder so the agent can see + crop pages *before* writing the note:

1. (steps 1–5) extract text · identify course/type/unit — unchanged.
2. (6) archive source → `raw/{unit}/` — unchanged.
3. **Render pages** — run `image_extract.py` → page PNGs (temp `pages_dir`) + label boxes. (This is the render the image bank already needs; now it also feeds note figures.)
4. **Image-bank capture** (existing 7c) — agent selects labeled-illustration pages → save whole page PNGs to `materials/{unit}/images/` + `image_bank.json` (UNCHANGED — `/lkimage` quiz still consumes these PNG files + their `label_bbox`).
5. **Generate image-rich note** — agent writes the grade-focused, Section-1-tagged note, inserting `{{FIG: <temp_page_png> | crop | caption}}` placeholders inline where each diagram belongs. Pipe to `notes_embed.py --dest materials/{unit}/{type}_{slug}.md` → self-contained `.md` with cropped base64 figures.
6. (7b) pool extraction — unchanged.
7. (8) clean temp `pages_dir`, fire data writes + logs — unchanged.

**Scanned PDFs:** the agent already reads page images for note content; it now also emits `{{FIG}}` placeholders for the figures it wants.

**Non-PDF files** (docx/txt/pptx) and any note with no figures: the agent emits no `{{FIG}}` tokens → `notes_embed.py` writes through (identical to today's `notes write`).

---

## What stays the same

- **`image_bank.json` + `materials/{unit}/images/*.png`** — still produced by the capture step; `/lkimage` and the Phase-2 quiz read the PNG files + `label_bbox`. The note's base64 figures are *additional* (different purpose: portable inline reading). Yes, the figure bytes exist both as bank PNGs and as note base64 — accepted (out of scope to dedup).
- **`raw/` = sources, `materials/` = notes + `images/`** (your policy).
- **Rule 9 / 9a, Rule 15** — note content from materials only; AI image labels flagged; structured writes via `data_writer.py` (notes are file artifacts via `notes_embed.py`, same class as `notes write`).

---

## Components

| File | Responsibility | Action |
|------|----------------|--------|
| `scripts/notes_embed.py` | stdin note + `{{FIG}}` → crop (Pillow) + base64 → self-contained `.md` | Create |
| `scripts/tests/test_notes_embed.py` | unittest for embed + pass-through + missing-figure | Create |
| `.claude/commands/lkingest.md` | reorder steps; note-gen uses `{{FIG}}` + `notes_embed.py` | Modify |
| `.claude/commands/lkscripts.md` | `notes_embed.py` reference + token format | Modify |
| `CLAUDE.md` | note format note (self-contained, embedded figures) | Modify |
| `README.md` | mention image-rich notes | Modify |

---

## Testing

- `test_notes_embed.py` (subprocess):
  - **embed**: note with one `{{FIG: tmp.png | 0,0,0.5,0.5 | Talus}}` + a generated PNG → output `.md` contains `data:image/png;base64,`, the caption `Talus`, and no `{{FIG`.
  - **pass-through**: note with no tokens → output `.md` == input text; `figures_embedded == 0`.
  - **missing page**: token references a non-existent PNG → output has `*(figure unavailable` and `missing == 1`, `success == true`.
  - **stdout ASCII-safe**: result JSON parses (no Windows cp1252 crash).

---

## Out of scope

- Retrofitting the existing text-only notes (this applies to future ingests; a one-off re-embed pass could be added later).
- HTML companion (user chose `.md`-only).
- Deduping figure bytes between `images/` PNGs and note base64.
- Auto-deciding figures without the agent (the agent's vision + judgment chooses crops).
