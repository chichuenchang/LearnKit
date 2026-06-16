import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

import fitz

SCRIPT = str(pathlib.Path(__file__).resolve().parents[1] / "pdf_split.py")


def make_pdf(path, pages):
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    doc.save(str(path))
    doc.close()


def run(pdf, out, chunk=None):
    args = [sys.executable, SCRIPT, "--file", str(pdf), "--out", str(out)]
    if chunk is not None:
        args += ["--chunk", str(chunk)]
    proc = subprocess.run(args, capture_output=True, text=True)
    return json.loads(proc.stdout)


def page_count(path):
    doc = fitz.open(str(path))
    n = len(doc)
    doc.close()
    return n


class PdfSplitTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        self.out = self.root / "out"
        self.pdf = self.root / "big.pdf"

    def tearDown(self):
        self._tmp.cleanup()

    def test_splits_into_parts(self):
        make_pdf(self.pdf, 7)
        res = run(self.pdf, self.out, chunk=3)
        self.assertTrue(res["success"], res)
        self.assertTrue(res["split"])
        self.assertEqual(res["page_count"], 7)
        self.assertEqual(len(res["parts"]), 3)            # 3 + 3 + 1
        self.assertEqual([p["pages"] for p in res["parts"]], [3, 3, 1])
        self.assertEqual(res["parts"][0]["from_page"], 1)
        self.assertEqual(res["parts"][-1]["to_page"], 7)
        # every part exists on disk with the reported page count
        for p in res["parts"]:
            self.assertTrue(pathlib.Path(p["path"]).exists())
            self.assertEqual(page_count(p["path"]), p["pages"])
        # parts cover all pages with no gap/overlap
        self.assertEqual(sum(p["pages"] for p in res["parts"]), 7)

    def test_no_split_when_under_chunk(self):
        make_pdf(self.pdf, 5)
        res = run(self.pdf, self.out, chunk=10)
        self.assertTrue(res["success"])
        self.assertFalse(res["split"])
        self.assertEqual(len(res["parts"]), 1)
        self.assertEqual(res["parts"][0]["path"], str(self.pdf))  # points at original
        self.assertEqual(res["parts"][0]["pages"], 5)

    def test_exact_multiple(self):
        make_pdf(self.pdf, 6)
        res = run(self.pdf, self.out, chunk=3)
        self.assertEqual([p["pages"] for p in res["parts"]], [3, 3])

    def test_chunk_zero_disables(self):
        make_pdf(self.pdf, 9)
        res = run(self.pdf, self.out, chunk=0)
        self.assertFalse(res["split"])
        self.assertEqual(len(res["parts"]), 1)

    def test_missing_file_fails(self):
        res = run(self.root / "nope.pdf", self.out, chunk=3)
        self.assertFalse(res["success"])
        self.assertIn("not found", res["error"].lower())

    def test_non_pdf_fails(self):
        bad = self.root / "x.txt"
        bad.write_text("hi", encoding="utf-8")
        res = run(bad, self.out, chunk=3)
        self.assertFalse(res["success"])


if __name__ == "__main__":
    unittest.main()
