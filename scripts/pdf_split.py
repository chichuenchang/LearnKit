"""Split a PDF into <=N-page parts for chunked ingestion.

When a PDF has more pages than the chunk size, ingesting it whole either
truncates at the render cap or blows up vision-token cost. This tool splits it
into sequential <=N-page part PDFs so each part can run through the normal
ingest pipeline on its own (its own note, image-bank entries, etc.).

Usage: python pdf_split.py --file <pdf> --out <dir> [--chunk N]
  --chunk defaults to config auto_split_pages. <=0 disables splitting.

Output: JSON to stdout —
  { success, split (bool), page_count, chunk, out_dir,
    parts: [ { path, index, part_count, from_page, to_page, pages } ],
    error }

page_count <= chunk (or chunk <= 0) → split=false and parts=[the original file]
(one entry spanning the whole document), so callers can loop uniformly.
"""
import argparse
import json
import math
import os
import pathlib
import sys

from lkconfig import get as cfg
from extract_text import _safe_name  # shared path-component sanitizer


def split_pdf(path, out_dir, chunk):
    import fitz
    doc = fitz.open(path)
    total = len(doc)
    stem = _safe_name(pathlib.Path(path).stem)
    ext = pathlib.Path(path).suffix or ".pdf"

    # No split: whole document as a single logical part (points at the original).
    if chunk <= 0 or total <= chunk:
        doc.close()
        return {
            "split": False, "page_count": total, "chunk": chunk,
            "out_dir": None,
            "parts": [{"path": str(path), "index": 1, "part_count": 1,
                       "from_page": 1, "to_page": total, "pages": total}],
        }

    dest = pathlib.Path(out_dir) / stem
    dest.mkdir(parents=True, exist_ok=True)
    part_count = math.ceil(total / chunk)
    parts = []
    for i in range(part_count):
        a = i * chunk                      # 0-based inclusive
        b = min(a + chunk, total) - 1      # 0-based inclusive
        part = fitz.open()
        part.insert_pdf(doc, from_page=a, to_page=b)
        ppath = dest / f"{stem}_part{i + 1:02d}{ext}"
        part.save(str(ppath))
        part.close()
        parts.append({"path": str(ppath), "index": i + 1, "part_count": part_count,
                      "from_page": a + 1, "to_page": b + 1, "pages": b - a + 1})
    doc.close()
    return {"split": True, "page_count": total, "chunk": chunk,
            "out_dir": str(dest), "parts": parts}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--chunk", type=int, default=cfg("auto_split_pages"),
                    help="max pages per part; <=0 disables splitting")
    args = ap.parse_args()

    result = {"success": False, "split": False, "page_count": 0,
              "chunk": args.chunk, "out_dir": None, "parts": [], "error": None}
    try:
        if not os.path.exists(args.file):
            raise FileNotFoundError(f"File not found: {args.file}")
        if pathlib.Path(args.file).suffix.lower() != ".pdf":
            raise ValueError("pdf_split only handles .pdf files")
        result.update(split_pdf(args.file, args.out, args.chunk))
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
