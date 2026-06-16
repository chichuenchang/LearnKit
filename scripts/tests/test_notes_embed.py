import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = str(pathlib.Path(__file__).resolve().parents[1] / "notes_embed.py")


def make_png(path, size=(400, 300)):
    from PIL import Image
    Image.new("RGB", size, (255, 255, 255)).save(path)


def run_embed(note_text, dest):
    proc = subprocess.run([sys.executable, SCRIPT, "--dest", dest],
                          input=note_text, capture_output=True, text=True)
    return json.loads(proc.stdout)


class NotesEmbedTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self._tmp.name)
        self.png = str(self.d / "page.png")
        make_png(self.png)
        self.dest = str(self.d / "note.md")

    def tearDown(self):
        self._tmp.cleanup()

    def test_embed_figure(self):
        note = f"# Title\n\nIntro.\n\n{{{{FIG: {self.png} | 0,0,0.5,0.5 | Talus diagram}}}}\n\nMore."
        res = run_embed(note, self.dest)
        self.assertTrue(res["success"], res.get("error"))
        self.assertEqual(res["figures_embedded"], 1)
        self.assertEqual(res["missing"], 0)
        txt = pathlib.Path(self.dest).read_text(encoding="utf-8")
        self.assertIn("data:image/png;base64,", txt)
        self.assertIn("Talus diagram", txt)
        self.assertNotIn("{{FIG", txt)

    def test_passthrough_no_tokens(self):
        note = "# Plain note\n\nNo figures here.\n"
        res = run_embed(note, self.dest)
        self.assertTrue(res["success"])
        self.assertEqual(res["figures_embedded"], 0)
        self.assertEqual(pathlib.Path(self.dest).read_text(encoding="utf-8"), note)

    def test_missing_page_graceful(self):
        gone = str(self.d / "nope.png")
        note = f"text {{{{FIG: {gone} | 0,0,0.5,0.5 | Soleus}}}} end"
        res = run_embed(note, self.dest)
        self.assertTrue(res["success"])
        self.assertEqual(res["missing"], 1)
        txt = pathlib.Path(self.dest).read_text(encoding="utf-8")
        self.assertIn("figure unavailable", txt)
        self.assertNotIn("{{FIG", txt)

    def test_empty_dest_dir_created(self):
        nested = str(self.d / "sub" / "deep" / "note.md")
        res = run_embed("# x\n", nested)
        self.assertTrue(res["success"])
        self.assertTrue(pathlib.Path(nested).exists())


if __name__ == "__main__":
    unittest.main()
