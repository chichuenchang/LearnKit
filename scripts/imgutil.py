"""Shared image helpers for LearnKit scripts.

Small primitives reused across the image pipeline (notes_embed, image_quiz,
extract_text, image_extract) so cropping / base64 embedding / PDF page raster
live in exactly one place.
"""
import base64
import io


def data_uri(img):
    """PIL image -> 'data:image/png;base64,...' string (for self-contained HTML/MD)."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def crop_norm(img, bbox):
    """Crop a PIL image to a normalized [x,y,w,h] region (clamped to bounds).

    A degenerate / out-of-range box collapses to nothing -> return the image
    unchanged rather than raising."""
    W, H = img.size
    x, y, w, h = bbox
    left, top = max(0, int(x * W)), max(0, int(y * H))
    right, bottom = min(W, int((x + w) * W)), min(H, int((y + h) * H))
    if right <= left or bottom <= top:
        return img
    return img.crop((left, top, right, bottom))


def render_page_png(page, scale, out_path):
    """Render a fitz PDF page to PNG at the given scale. Returns (width, height) px."""
    import fitz
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
    pix.save(str(out_path))
    return pix.width, pix.height
