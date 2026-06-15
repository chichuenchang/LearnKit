import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = str(REPO / "scripts" / "image_extract.py")
TEXT_PDF = REPO / "savedata/courses/pther_350a/materials/week_06_foot/source_the_arches_of_the_foot.pdf"
SCANNED_PDF = REPO / "savedata/courses/pther_350a/materials/week_06_foot/source_the_bones_of_the_foot.pdf"


def run_extract(pdf, out_dir):
    # LK_OCR_DISABLE keeps the test fast/deterministic (no PaddleOCR/GPU init);
    # exercises the text-layer + graceful-no-OCR paths.
    env = {**os.environ, "LK_OCR_DISABLE": "1"}
    proc = subprocess.run([sys.executable, SCRIPT, "--file", str(pdf), "--out", out_dir],
                          capture_output=True, text=True, env=env)
    return json.loads(proc.stdout)


class ImageExtractTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    @unittest.skipUnless(TEXT_PDF.exists(), "text-layer fixture missing")
    def test_textlayer_pdf(self):
        res = run_extract(TEXT_PDF, self.out)
        self.assertTrue(res["success"], res.get("error"))
        self.assertGreater(res["page_count"], 0)
        tl = [p for p in res["pages"] if p["source"] == "textlayer" and p["words"]]
        self.assertTrue(tl, "expected at least one text-layer page with words")
        bbox = tl[0]["words"][0]["bbox"]
        self.assertEqual(len(bbox), 4)
        self.assertTrue(all(0.0 <= v <= 1.5 for v in bbox), bbox)  # normalized

    @unittest.skipUnless(SCANNED_PDF.exists(), "scanned fixture missing")
    def test_scanned_pdf_graceful(self):
        res = run_extract(SCANNED_PDF, self.out)
        self.assertTrue(res["success"], res.get("error"))
        self.assertGreater(len(res["pages"]), 0)
        for p in res["pages"]:
            self.assertIn(p["source"], {"textlayer", "ocr", "none"})

    def test_missing_file(self):
        res = run_extract(REPO / "nope_does_not_exist.pdf", self.out)
        self.assertFalse(res["success"])


if __name__ == "__main__":
    unittest.main()
