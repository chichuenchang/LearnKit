"""Embed agent-cropped figures into a study note as base64 data-URIs.

Usage: python notes_embed.py --dest <md_path>    (reads note text on stdin)
Figure token (inline, single line):
    {{FIG: <page_png_path> | x,y,w,h | caption}}
  - x,y,w,h = crop box normalized 0-1 relative to the page image
  - caption = alt text (no '|' or '}')
No tokens -> the note is written through unchanged.
Output: JSON to stdout (ASCII-safe): {success, dest, figures_embedded, missing, error}
"""
import argparse
import json
import os
import re
import sys

from imgutil import crop_norm, data_uri

FIG_RE = re.compile(
    r"\{\{FIG:\s*(?P<path>[^|]+?)\s*\|\s*"
    r"(?P<x>[\d.]+)\s*,\s*(?P<y>[\d.]+)\s*,\s*(?P<w>[\d.]+)\s*,\s*(?P<h>[\d.]+)\s*\|\s*"
    r"(?P<cap>[^}]*)\}\}"
)


def _embed_one(m, stats):
    path = m.group("path").strip()
    cap = m.group("cap").strip()
    try:
        from PIL import Image
        x, y, w, h = (float(m.group(k)) for k in ("x", "y", "w", "h"))
        img = Image.open(path).convert("RGB")
        uri = data_uri(crop_norm(img, (x, y, w, h)))
        stats["embedded"] += 1
        cap_safe = cap.replace("[", "").replace("]", "")
        return f"![{cap_safe}]({uri})"
    except Exception:
        stats["missing"] += 1
        return f"*(figure unavailable: {cap})*"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True)
    args = ap.parse_args()

    result = {"success": False, "dest": args.dest,
              "figures_embedded": 0, "missing": 0, "error": None}
    try:
        text = sys.stdin.buffer.read().decode("utf-8-sig")
        stats = {"embedded": 0, "missing": 0}
        out = FIG_RE.sub(lambda m: _embed_one(m, stats), text)
        os.makedirs(os.path.dirname(os.path.abspath(args.dest)), exist_ok=True)
        # newline="" prevents Windows newline re-translation (\r\n -> \r\r\n)
        with open(args.dest, "w", encoding="utf-8", newline="") as f:
            f.write(out)
        result["figures_embedded"] = stats["embedded"]
        result["missing"] = stats["missing"]
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)

    print(json.dumps(result))  # ASCII-safe stdout


if __name__ == "__main__":
    main()
