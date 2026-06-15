Base context (path variables, behavioral rules) loaded from CLAUDE.md. Data schemas in lkschemas.md. Python script protocol and data_writer.py reference in lkscripts.md. Log entry format spec in lklogging.md.

## `/lkimage` — Image bank (Phase 1: review)

Reviews each course's `data\image_bank.json` — labeled diagrams/figures captured during ingest (any subject: anatomy, chemistry, geography, circuits, maps, …). Image labels are either printed slide labels (`[slide]`, grounded) or AI-identified (`[AI — verify]`, flagged). All writes go through `data_writer.py` `image add` / `image remove` (Rule 15). Multiple active courses + none specified → ask (Rule 2). Never mix courses (Rule 1). Missing `image_bank.json` → treat as empty.

### `/lkimage {course}` — summary
Read `course_structure.json` and `image_bank.json`. Print:
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
For each image whose `unit_id` ∈ scope, print: the **image file path** (user opens it), `title`, and the structure list as `name · type · [slide]` or `name · type · [AI — verify]`. Terminal cannot inline-render images, so give the path + the labels.

### `/lkimage {image_id}` — one image
Resolve the course from the id prefix (strip `img_` and trailing `_{NNN}`). Print that image's path, title, and full structure list.

### `/lkimage remove {image_id}` — delete a bad capture
Resolve course from the id, confirm, then `data_writer.py image remove`. Log: `[IMAGE] Removed {image_id}`.
