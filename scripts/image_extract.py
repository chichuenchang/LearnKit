"""Render PDF pages to PNG and detect label text + boxes for the image bank.

Usage: python image_extract.py --file <pdf> --out <dir>
Output: JSON to stdout. Tesseract OCR is OPTIONAL (graceful degrade to source:"none").
"""
import argparse
import json
import os
import pathlib
import shutil

from extract_text import _safe_name  # reuse the path-component sanitizer

TEXTLAYER_MIN_WORDS = 5
MAX_PAGES = 60
OCR_MIN_CONF = 40


def _tesseract_cmd():
    """Locate a working Tesseract binary. Prefers an explicit override and the
    self-contained UB-Mannheim install over a bare PATH lookup (a conda-forge
    tesseract on PATH can be DLL-broken under subprocess on Windows)."""
    env = os.environ.get("LK_TESSERACT_CMD")
    if env and os.path.exists(env):
        return env
    for c in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
              r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
              os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")):
        if os.path.exists(c):
            return c
    return shutil.which("tesseract")  # last resort (may be on PATH)


def _norm_bbox(x0, y0, x1, y1, w, h):
    if w <= 0 or h <= 0:
        return None
    return [round(x0 / w, 4), round(y0 / h, 4),
            round((x1 - x0) / w, 4), round((y1 - y0) / h, 4)]


def _ocr_words(png_path):
    """Return [{text,bbox,conf}] via Tesseract, or None if OCR unavailable."""
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return None
    cmd = _tesseract_cmd()
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
    try:
        img = Image.open(png_path)
        data = pytesseract.image_to_data(
            img, config="--psm 12", output_type=pytesseract.Output.DICT)
    except Exception:
        return None
    words = []
    W, H = img.size
    for i in range(len(data["text"])):
        txt = (data["text"][i] or "").strip()
        try:
            conf = float(data["conf"][i])
        except ValueError:
            conf = -1.0
        if not txt or conf < OCR_MIN_CONF:
            continue
        x, y, w, h = (data["left"][i], data["top"][i],
                      data["width"][i], data["height"][i])
        words.append({"text": txt, "bbox": _norm_bbox(x, y, x + w, y + h, W, H),
                      "conf": round(conf / 100, 2)})
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    result = {"success": False, "filename": os.path.basename(args.file),
              "pages_dir": None, "page_count": 0, "capped": False,
              "pages": [], "error": None}
    try:
        import fitz
        if not os.path.exists(args.file):
            raise FileNotFoundError(f"File not found: {args.file}")

        stem = _safe_name(pathlib.Path(args.file).stem)
        out_dir = pathlib.Path(args.out) / stem
        out_dir.mkdir(parents=True, exist_ok=True)
        result["pages_dir"] = str(out_dir)

        doc = fitz.open(args.file)
        total = len(doc)
        result["page_count"] = total
        result["capped"] = total > MAX_PAGES
        mat = fitz.Matrix(2, 2)  # 2x render; PDF points -> pixels = *2

        for i in range(min(total, MAX_PAGES)):
            page = doc[i]
            pix = page.get_pixmap(matrix=mat)
            img_path = out_dir / f"page_{i + 1:03d}.png"
            pix.save(str(img_path))
            W, H = pix.width, pix.height

            tw = page.get_text("words")  # (x0,y0,x1,y1,word,block,line,wordno)
            words = []
            source = "none"
            if len(tw) >= TEXTLAYER_MIN_WORDS:
                source = "textlayer"
                for x0, y0, x1, y1, word, *_ in tw:
                    txt = (word or "").strip()
                    if not txt:
                        continue
                    words.append({"text": txt,
                                  "bbox": _norm_bbox(x0 * 2, y0 * 2, x1 * 2, y1 * 2, W, H),
                                  "conf": 1.0})
            else:
                ocr = _ocr_words(str(img_path))
                if ocr is not None:
                    source, words = "ocr", ocr

            result["pages"].append({"page": i + 1, "image_path": str(img_path),
                                    "image_w": W, "image_h": H,
                                    "source": source, "words": words})
        doc.close()
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)

    # ensure_ascii=True (default): keep stdout pure-ASCII so non-cp1252 glyphs
    # in slide text (e.g. bullets) never crash a Windows console codepage.
    print(json.dumps(result))


if __name__ == "__main__":
    main()
