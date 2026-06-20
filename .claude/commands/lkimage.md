Base context (path variables, behavioral rules) from CLAUDE.md. Data schemas in lkschemas.md. Python script protocol + data_writer.py reference in lkscripts.md.

## `/lkimage` — Image bank

Reviews each course's `data\image_bank.json` — labeled diagrams/figures captured during ingest (any subject: anatomy, chemistry, geography, circuits, maps, …). Labels: printed slide labels (`[slide]`, grounded) or AI-identified (`[AI — verify]`, flagged). All writes via `data_writer.py` `image add` / `image remove` (Rule 9). Multiple active courses + none specified → ask (Rule 2). Never mix courses (Rule 1). Missing `image_bank.json` → empty.

### `/lkimage {course}` — summary
Read `course_structure.json` + `image_bank.json`. Print:
- Total illustrations + total structures (slide vs AI tally).
- Breakdown by unit (`display_name` → image count); units with 0 images.

```
PTHER 350A — Image Bank
Total: 12 illustrations · 84 structures (71 slide · 13 AI)
──────────────────────────────────────────────
  Week 6: Foot         12   (Bones 4, Joints 5, Arches 0, Plantar 3)
  Week 1–5             0    (none captured)
```

### `/lkimage {course} {scope}` — review
Each image whose `unit_id` ∈ scope, print: **image file path** (user opens it), `title`, structure list as `name · type · [slide]` or `name · type · [AI — verify]`. Terminal can't inline-render images — give path + labels.

### `/lkimage {image_id}` — one image
Resolve course from id prefix (strip `img_` + trailing `_{NNN}`). Print that image's path, title, full structure list.

### `/lkimage remove {image_id}` — delete bad capture
Resolve course from id, confirm, then `data_writer.py image remove`.
