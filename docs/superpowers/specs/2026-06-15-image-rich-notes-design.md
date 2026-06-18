# Image-Rich Notes — Design Spec

**Date**: 2026-06-15
**Status**: Approved, pending implementation plan
**Project**: LearnKit (PTStudy)

---

## Goal

`/lkingest` make **image-rich study notes by default**: one self-contained `.md`. Agent picks + crops diagrams, embeds inline (base64) next to text they illustrate. Text + figures together — no separate `images/` dependency for note, no relative-path render failures.

---

## Decisions (from brainstorm)

| Decision | Choice |
|----------|--------|
| Note format | **Self-contained `.md`** — figures embedded as base64 data-URIs inline (one file, always renders in VS Code/Obsidian) |
| Figure cropping | **Agent-cropped** — agent picks crop box per figure (clean single diagrams), not whole 2-up pages |
| Mechanism | Agent writes lightweight `{{FIG:…}}` placeholders → `notes_embed.py` crops + base64-embeds |

---

## Mechanism: placeholder → embed

Agent can't paste 100 KB base64 blobs into note heredoc. Writes **placeholders**; script expands.

**Placeholder token (single line, inline in note body):**
```
{{FIG: <page_png_path> | x,y,w,h | caption}}
```
- `<page_png_path>` — rendered page PNG (from ingest render pass).
- `x,y,w,h` — crop box, **normalized 0–1** relative to that page image.
- `caption` — alt/caption text (no `|` or `}}`).

**`scripts/notes_embed.py`:**
- `python notes_embed.py --dest <md_path>` ; reads note text (with tokens) from **stdin**.
- Per `{{FIG:…}}`: open page PNG, crop normalized box (Pillow), PNG→base64, replace token with `![caption](data:image/png;base64,…)`.
- Missing page / unreadable / malformed token → replace with `*(figure unavailable: caption)*` (never crash).
- No tokens → write note through unchanged (cleanly replaces `notes write` for ALL notes).
- Write final self-contained `.md` to `--dest` (utf-8). Print `{"success": true, "figures_embedded": N, "missing": M}` (ASCII-safe stdout).

Agent judges (which figure, where, crop region, caption); script crops + base64 + writes. **Dep: Pillow (installed).**

---

## Ingest flow change (PDFs)

Reorder so agent sees + crops pages *before* writing note:

1. (steps 1–5) extract text · identify course/type/unit — unchanged.
2. (6) archive source → `raw/{unit}/` — unchanged.
3. **Render pages** — run `image_extract.py` → page PNGs (temp `pages_dir`) + label boxes. (Render image bank already needs; now also feeds note figures.)
4. **Image-bank capture** (existing 7c) — agent selects labeled-illustration pages → save whole page PNGs to `materials/{unit}/images/` + `image_bank.json` (UNCHANGED — `/lkimage` quiz still consumes these PNG files + their `label_bbox`).
5. **Generate image-rich note** — agent writes grade-focused, Section-1-tagged note, inserting `{{FIG: <temp_page_png> | crop | caption}}` placeholders inline where each diagram belongs. Pipe to `notes_embed.py --dest materials/{unit}/{type}_{slug}.md` → self-contained `.md` with cropped base64 figures.
6. (7b) pool extraction — unchanged.
7. (8) clean temp `pages_dir`, fire data writes + logs — unchanged.

**Scanned PDFs:** agent already reads page images for note content; now also emits `{{FIG}}` placeholders for figures it wants.

**Non-PDF files** (docx/txt/pptx) and any note with no figures: agent emits no `{{FIG}}` tokens → `notes_embed.py` writes through (identical to today's `notes write`).

---

## What stays same

- **`image_bank.json` + `materials/{unit}/images/*.png`** — still produced by capture step; `/lkimage` and Phase-2 quiz read PNG files + `label_bbox`. Note's base64 figures are *additional* (different purpose: portable inline reading). Figure bytes exist both as bank PNGs and note base64 — accepted (out of scope to dedup).
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
  - **embed**: note with one `{{FIG: tmp.png | 0,0,0.5,0.5 | Talus}}` + generated PNG → output `.md` contains `data:image/png;base64,`, caption `Talus`, no `{{FIG`.
  - **pass-through**: note with no tokens → output `.md` == input text; `figures_embedded == 0`.
  - **missing page**: token references non-existent PNG → output has `*(figure unavailable` and `missing == 1`, `success == true`.
  - **stdout ASCII-safe**: result JSON parses (no Windows cp1252 crash).

---

## Out of scope

- Retrofit existing text-only notes (applies to future ingests; one-off re-embed pass could be added later).
- HTML companion (user chose `.md`-only).
- Dedup figure bytes between `images/` PNGs and note base64.
- Auto-decide figures without agent (agent's vision + judgment chooses crops).
