"""
Text extraction helper for PT Study Agent.
Usage: python extract_text.py --file <path> --output <path>
Outputs JSON: { success, filename, file_type, page_count, word_count, text, error }
"""
import argparse
import json
import os
import sys


def extract_pdf(path):
    import pdfplumber
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    full_text = "\n\n".join(pages)
    return full_text, len(pages)


def extract_pptx(path):
    from pptx import Presentation
    prs = Presentation(path)
    slides = []
    for i, slide in enumerate(prs.slides, 1):
        parts = []
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                parts.append(shape.text.strip())
        if parts:
            slides.append(f"[Slide {i}]\n" + "\n".join(parts))
    return "\n\n".join(slides), len(prs.slides)


def extract_docx(path):
    from docx import Document
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs), len(paragraphs)


def extract_text_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    return text, text.count("\n") + 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = {
        "success": False,
        "filename": os.path.basename(args.file),
        "file_type": None,
        "page_count": 0,
        "word_count": 0,
        "text": "",
        "error": None,
    }

    ext = os.path.splitext(args.file)[1].lower()

    try:
        if not os.path.exists(args.file):
            raise FileNotFoundError(f"File not found: {args.file}")

        if ext == ".pdf":
            result["file_type"] = "pdf"
            result["text"], result["page_count"] = extract_pdf(args.file)
        elif ext == ".pptx":
            result["file_type"] = "pptx"
            result["text"], result["page_count"] = extract_pptx(args.file)
        elif ext == ".docx":
            result["file_type"] = "docx"
            result["text"], result["page_count"] = extract_docx(args.file)
        elif ext in (".txt", ".md"):
            result["file_type"] = ext.lstrip(".")
            result["text"], result["page_count"] = extract_text_file(args.file)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        result["word_count"] = len(result["text"].split())
        result["success"] = True

    except Exception as e:
        result["error"] = str(e)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
