"""Batch image-bank builder for LearnKit.

Crops single slides (or slide halves) from already-rendered PDF pages, locates
printed label phrases in each page's text-layer to derive label boxes, and writes
the resulting image records to image_bank.json via data_writer.py `image add`.

Use for batch re-ingest when image_extract.py has already rendered pages and you
have a list of (page, half, structures) captures. For one-off ingest the agent
builds the image-record array inline (lkingest.md step 7b); this tool automates
the phrase -> label-box matching across many pages.

Usage: python image_bank_build.py        (reads a capture spec JSON on stdin)
Output: JSON to stdout — {success, added, skipped, ids, report, error}
  report[] = per-capture coverage strings like "p5t:3/4" (3 of 4 labels boxed).

Spec (stdin), all fields required unless noted:
{
  "savedata": "<savedata root>",
  "course":   "<course slug>",
  "img_json": "<path to image_extract.py output JSON (pages[].words)>",
  "pages_dir": "<dir holding page_NNN.png from image_extract.py>",
  "images_dir": "<dest dir for cropped PNGs, e.g. .../materials/{unit}/images>",
  "image_path_prefix": "<path stored in the record, e.g. materials/{unit}/images>",
  "slug": "<source slug used in output filenames>",
  "unit_id": "...", "unit_slug": "...", "source_file": "source_x.pdf",
  "captures": [
    { "page": 5, "half": "top|bottom|full", "title": "Slide heading",
      "structures": [ ["Talus", "bone"], ["Calcaneus", "bone"] ] }
  ]
}
"""
import json
import pathlib
import re
import subprocess
import sys

from PIL import Image

DATA_WRITER = pathlib.Path(__file__).parent / "data_writer.py"


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).split()


def find_phrase(words, phrase):
    """Locate a contiguous label phrase in the page's text-layer words.

    Returns its bounding box as normalized [x, y, w, h] (full-page space), or
    None when the phrase is not found."""
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
    """Remap a full-page-normalized box into the chosen half's crop space.

    A half spans 0.5 of the page, so half-relative coords = *2 (clamped 0-1)."""
    x, y, w, h = box
    if half == "full":
        return [round(x, 4), round(min(max(y, 0), 1), 4), round(w, 4), round(min(h, 1), 4)]
    yy = y * 2 if half == "top" else (y - 0.5) * 2
    return [round(x, 4), round(min(max(yy, 0), 1), 4), round(w, 4), round(min(h * 2, 1), 4)]


def build(spec):
    """Crop pages per the spec and return (image_records, coverage_report)."""
    img = json.load(open(spec["img_json"], encoding="utf-8"))
    pages = {p["page"]: p for p in img["pages"]}
    pdir = pathlib.Path(spec["pages_dir"])
    dst = pathlib.Path(spec["images_dir"])
    dst.mkdir(parents=True, exist_ok=True)

    records, report = [], []
    for cap in spec["captures"]:
        pg, half = cap["page"], cap["half"]
        page = pages[pg]; words = page["words"]
        im = Image.open(pdir / f"page_{pg:03d}.png").convert("RGB"); W, H = im.size
        if half == "full":
            box = (0, 0, W, H)
        elif half == "top":
            box = (0, 0, W, H // 2)
        else:
            box = (0, H // 2, W, H)
        crop = im.crop(box); cw, ch = crop.size
        name = f"{spec['slug']}_p{pg:02d}{ {'top': 't', 'bottom': 'b', 'full': 'f'}[half] }.png"
        crop.save(dst / name)
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
    return records, report


def main():
    try:
        spec = json.load(sys.stdin)
    except Exception as e:
        print(json.dumps({"success": False, "error": f"invalid spec JSON on stdin: {e}"}))
        return
    try:
        records, report = build(spec)
    except KeyError as e:
        print(json.dumps({"success": False, "error": f"spec missing field: {e}"}))
        return
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return

    r = subprocess.run([sys.executable, str(DATA_WRITER), "image", "add",
                        "--savedata", spec["savedata"], "--course", spec["course"]],
                       input=json.dumps(records), capture_output=True, text=True)
    try:
        result = json.loads(r.stdout)
    except Exception:
        print(json.dumps({"success": False, "error": "data_writer image add failed",
                          "report": report, "writer_stdout": r.stdout,
                          "writer_stderr": r.stderr}))
        return
    result["report"] = report
    print(json.dumps(result))


if __name__ == "__main__":
    main()
