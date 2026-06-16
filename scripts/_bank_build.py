"""Temp batch helper: crop single slides + box structures from text-layer + image add.
Reads a captures spec JSON on stdin. Delete after the re-ingest batch."""
import json
import pathlib
import re
import subprocess
import sys

from PIL import Image

spec = json.load(sys.stdin)
IMG = json.load(open(spec["img_json"], encoding="utf-8"))
pages = {p["page"]: p for p in IMG["pages"]}
PDIR = pathlib.Path(spec["pages_dir"])
DST = pathlib.Path(spec["images_dir"])
DST.mkdir(parents=True, exist_ok=True)


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).split()


def find_phrase(words, phrase):
    toks = norm(phrase)
    if not toks:
        return None
    flat = []
    for w in words:
        for t in norm(w["text"]):
            flat.append((w, t))
    n = len(flat)
    for i in range(n):
        if flat[i][1] == toks[0]:
            j, k, span = i, 0, []
            while j < n and k < len(toks):
                if flat[j][1] == toks[k]:
                    span.append(flat[j][0]); k += 1; j += 1
                else:
                    break
            if k == len(toks):
                xs0 = [b["bbox"][0] for b in span]; ys0 = [b["bbox"][1] for b in span]
                xs1 = [b["bbox"][0] + b["bbox"][2] for b in span]
                ys1 = [b["bbox"][1] + b["bbox"][3] for b in span]
                return [min(xs0), min(ys0), max(xs1) - min(xs0), max(ys1) - min(ys0)]
    return None


def to_crop(box, half):
    x, y, w, h = box
    if half == "full":
        return [round(x, 4), round(min(max(y, 0), 1), 4), round(w, 4), round(min(h, 1), 4)]
    yy = y * 2 if half == "top" else (y - 0.5) * 2
    return [round(x, 4), round(min(max(yy, 0), 1), 4), round(w, 4), round(min(h * 2, 1), 4)]


records, report = [], []
for cap in spec["captures"]:
    pg, half = cap["page"], cap["half"]
    page = pages[pg]; words = page["words"]
    im = Image.open(PDIR / f"page_{pg:03d}.png").convert("RGB"); W, H = im.size
    if half == "full":
        box = (0, 0, W, H)
    elif half == "top":
        box = (0, 0, W, H // 2)
    else:
        box = (0, H // 2, W, H)
    crop = im.crop(box); cw, ch = crop.size
    name = f"{spec['slug']}_p{pg:02d}{ {'top': 't', 'bottom': 'b', 'full': 'f'}[half] }.png"
    crop.save(DST / name)
    srecs = []
    for sname, stype in cap["structures"]:
        b = find_phrase(words, sname)
        if b:
            srecs.append({"name": sname, "type": stype, "source": "slide",
                          "label_bbox": to_crop(b, half), "confidence": 1.0})
    records.append({"unit_id": spec["unit_id"], "unit_slug": spec["unit_slug"],
                    "source_file": spec["source_file"], "page": pg,
                    "image_path": f"{spec['image_path_prefix']}/{name}",
                    "image_w": cw, "image_h": ch, "title": cap["title"],
                    "label_source": "textlayer", "structures": srecs})
    report.append(f"p{pg}{half[0]}:{len(srecs)}/{len(cap['structures'])}")

r = subprocess.run([sys.executable, "scripts/data_writer.py", "image", "add",
                    "--savedata", spec["savedata"], "--course", spec["course"]],
                   input=json.dumps(records), capture_output=True, text=True)
print(" ".join(report), "||", r.stdout.strip())
