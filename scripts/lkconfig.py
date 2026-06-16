"""Shared tuning config for LearnKit scripts.

Reads config.json sitting next to this file. Every key falls back to
DEFAULTS, so a missing, partial, or malformed config never breaks
ingestion — the baked-in defaults match the committed config.json.

Usage:
    from lkconfig import get as cfg
    MAX_SCANNED_PAGES = cfg("max_scanned_pages")
"""
import json
import pathlib

_CONFIG_PATH = pathlib.Path(__file__).parent / "config.json"

DEFAULTS = {
    "scanned_words_per_page_threshold": 50,  # below this words/page → treat PDF as scanned
    "max_scanned_pages": 60,                 # scanned-PDF page render cap (extract_text)
    "image_max_pages": 60,                   # page render cap for image bank (image_extract)
    "auto_split_pages": 60,                  # PDFs over this many pages auto-split into <=N-page parts
    "textlayer_min_words": 5,                # min text-layer words before falling back to OCR
    "ocr_min_conf": 40,                      # min OCR word confidence (0-100) to keep a box
    "render_scale": 2,                       # fitz Matrix scale: PDF points → pixels multiplier
    "passing_score": 70.0,                   # quiz score-pct at/above which a unit counts as passed
}


def _load():
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        return {}


_CONFIG = _load()


def get(key):
    """Return config value for key, falling back to the baked-in default."""
    return _CONFIG.get(key, DEFAULTS[key])
