import base64
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import extract_text  # noqa: E402

SCRIPT = str(pathlib.Path(__file__).resolve().parents[1] / "extract_text.py")


def _png_bytes(color=(255, 0, 0)):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color).save(buf, format="PNG")
    return buf.getvalue()


class SafeNameTests(unittest.TestCase):
    def test_trailing_space_stripped(self):
        # The bug: "The Bones of the Foot " → dir ending in space → Windows fails
        self.assertEqual(extract_text._safe_name("The Bones of the Foot "), "The Bones of the Foot")

    def test_trailing_dot_stripped(self):
        self.assertEqual(extract_text._safe_name("report."), "report")

    def test_illegal_chars_replaced(self):
        self.assertEqual(extract_text._safe_name('a:b/c?'), "a_b_c_")

    def test_normal_unchanged(self):
        self.assertEqual(extract_text._safe_name("The Arches of the Foot"), "The Arches of the Foot")

    def test_empty_falls_back(self):
        self.assertEqual(extract_text._safe_name("   "), "doc")


class HtmlExtractTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self._tmp.name)
        self._cleanup_dirs = []

    def tearDown(self):
        self._tmp.cleanup()
        for dd in self._cleanup_dirs:
            shutil.rmtree(dd, ignore_errors=True)

    def _write_quiz_html(self, name):
        png = _png_bytes()
        b64 = base64.b64encode(png).decode()
        (self.d / "fig.png").write_bytes(png)
        html = (
            "<html><head><style>.x{color:red}</style><title>T</title></head><body>"
            "<script>var hidden=\"SECRETTOKEN\";</script>"
            "<h1>Quiz Title</h1><p>Question one text.</p>"
            f'<img src="data:image/png;base64,{b64}" alt="Diagram A">'
            '<img src="fig.png" alt="Local fig">'
            '<img src="https://example.com/x.png" alt="remote">'
            f'<img src="data:image/svg+xml;base64,{b64}" alt="svg">'
            "</body></html>"
        )
        f = self.d / name
        f.write_text(html, encoding="utf-8")
        return f

    def test_text_and_image_extraction(self):
        f = self._write_quiz_html("quiz_unit1.html")
        text, images, skipped, pages_dir = extract_text.extract_html(str(f))
        if pages_dir:
            self._cleanup_dirs.append(pages_dir)
        self.assertIn("Quiz Title", text)
        self.assertIn("Question one text.", text)
        self.assertNotIn("SECRETTOKEN", text)          # <script> dropped
        self.assertNotIn("color:red", text)            # <style> dropped
        self.assertEqual(len(images), 2)               # data-uri PNG + local file
        self.assertEqual(skipped, 2)                   # remote URL + svg
        self.assertEqual(images[0]["alt"], "Diagram A")
        for im in images:
            self.assertTrue(pathlib.Path(im["path"]).is_file())

    def test_main_dispatch_json(self):
        f = self._write_quiz_html("quiz_unit2.html")
        out = self.d / "out.json"
        subprocess.run([sys.executable, SCRIPT, "--file", str(f), "--output", str(out)],
                       capture_output=True, text=True)
        data = json.loads(out.read_text(encoding="utf-8"))
        if data.get("pages_dir"):
            self._cleanup_dirs.append(data["pages_dir"])
        self.assertTrue(data["success"], data.get("error"))
        self.assertEqual(data["file_type"], "html")
        self.assertEqual(len(data["images"]), 2)
        self.assertEqual(data["images_skipped"], 2)
        self.assertGreater(data["word_count"], 0)
        self.assertFalse(data["scanned"])

    def test_no_images_no_pages_dir(self):
        f = self.d / "plain.html"
        f.write_text("<html><body><p>Just text, no images.</p></body></html>", encoding="utf-8")
        text, images, skipped, pages_dir = extract_text.extract_html(str(f))
        self.assertIn("Just text", text)
        self.assertEqual(images, [])
        self.assertEqual(skipped, 0)
        self.assertIsNone(pages_dir)                    # nothing saved → nothing to clean


if __name__ == "__main__":
    unittest.main()
