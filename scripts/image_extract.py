"""Render PDF pages to PNG and detect label text + boxes for the image bank.

Usage: python image_extract.py --file <pdf> --out <dir>
Output: JSON to stdout. OCR is OPTIONAL — PaddleOCR (GPU) primary, Tesseract
fallback; neither present → graceful degrade to source:"none".
"""
import argparse
import json
import os
import pathlib
import shutil

from extract_text import _safe_name  # reuse the path-component sanitizer

from imgutil import render_page_png
from lkconfig import get as cfg

TEXTLAYER_MIN_WORDS = cfg("textlayer_min_words")
MAX_PAGES = cfg("image_max_pages")  # default page cap; override with --max-pages (0 = no cap)
OCR_MIN_CONF = cfg("ocr_min_conf")


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


_PADDLE = None
_PADDLE_TRIED = False


def _get_paddle():
    """Lazily init ONE PaddleOCR (GPU) instance per process, or None if unavailable."""
    global _PADDLE, _PADDLE_TRIED
    if _PADDLE_TRIED:
        return _PADDLE
    _PADDLE_TRIED = True
    try:
        import ssl
        # Windows: a malformed cert in the ROOT store crashes aiohttp's import-time
        # SSL context (PaddleOCR imports aiohttp). Skip the windows-store cert load.
        try:
            ssl.SSLContext._load_windows_store_certs = lambda self, storename, purpose: None
        except Exception:
            pass
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        from paddleocr import PaddleOCR
        _PADDLE = PaddleOCR(lang="en")
    except Exception:
        _PADDLE = None
    return _PADDLE


def _paddle_words(png_path):
    """Return [{text,bbox,conf}] via PaddleOCR (GPU), or None if unavailable."""
    ocr = _get_paddle()
    if ocr is None:
        return None
    try:
        from PIL import Image
        res = ocr.predict(png_path)
    except Exception:
        return None
    if not res:
        return []
    r0 = res[0]
    texts = r0.get("rec_texts") or []
    scores = r0.get("rec_scores") or []
    boxes = r0.get("rec_boxes")
    polys = r0.get("rec_polys")
    W, H = Image.open(png_path).size
    words = []
    for i, txt in enumerate(texts):
        t = (txt or "").strip()
        if not t:
            continue
        conf = float(scores[i]) if i < len(scores) else 1.0
        if conf < OCR_MIN_CONF / 100.0:
            continue
        if boxes is not None and i < len(boxes):
            b = boxes[i]
            x0, y0, x1, y1 = float(b[0]), float(b[1]), float(b[2]), float(b[3])
        elif polys is not None and i < len(polys):
            xs = [float(pt[0]) for pt in polys[i]]
            ys = [float(pt[1]) for pt in polys[i]]
            x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        else:
            continue
        words.append({"text": t, "bbox": _norm_bbox(x0, y0, x1, y1, W, H),
                      "conf": round(conf, 2)})
    return words


def _ocr_words(png_path):
    """OCR a page → [{text,bbox,conf}] or None. PaddleOCR (GPU) primary, Tesseract
    fallback. LK_OCR_DISABLE=1 skips OCR entirely (used by tests for speed)."""
    if os.environ.get("LK_OCR_DISABLE"):
        return None
    w = _paddle_words(png_path)
    if w is not None:
        return w
    return _tesseract_words(png_path)


def _tesseract_words(png_path):
    """Return [{text,bbox,conf}] via Tesseract, or None if unavailable."""
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
    ap.add_argument("--max-pages", type=int, default=MAX_PAGES,
                    help="page render cap; 0 = no cap")
    args = ap.parse_args()
    max_pages = args.max_pages

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
        render_count = total if max_pages <= 0 else min(total, max_pages)
        result["capped"] = total > render_count
        scale = cfg("render_scale")  # PDF points -> pixels = *scale

        for i in range(render_count):
            page = doc[i]
            img_path = out_dir / f"page_{i + 1:03d}.png"
            W, H = render_page_png(page, scale, img_path)

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
                                  "bbox": _norm_bbox(x0 * scale, y0 * scale, x1 * scale, y1 * scale, W, H),
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
