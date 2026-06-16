import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = str(pathlib.Path(__file__).resolve().parents[1] / "image_quiz.py")


def make_png(path):
    from PIL import Image
    Image.new("RGB", (400, 300), (255, 255, 255)).save(path)


def run_quiz(spec, out_html):
    proc = subprocess.run([sys.executable, SCRIPT, "--out", out_html],
                          input=json.dumps(spec), capture_output=True, text=True)
    return json.loads(proc.stdout)


class ImageQuizTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self._tmp.name)
        self.png = str(self.d / "p.png")
        make_png(self.png)
        self.html = str(self.d / "quiz.html")

    def tearDown(self):
        self._tmp.cleanup()

    def _spec(self, n=2):
        return {"title": "Test Quiz", "questions": [
            {"image_path": self.png, "image_w": 400, "image_h": 300,
             "target_bbox": [0.3, 0.3, 0.2, 0.05],
             "stem": "What is the name of the highlighted structure?",
             "options": ["Talus", "Calcaneus", "Navicular", "Cuboid"],
             "answer_index": (i % 4)} for i in range(n)]}

    def test_builds_html(self):
        res = run_quiz(self._spec(2), self.html)
        self.assertTrue(res["success"], res.get("error"))
        self.assertEqual(res["question_count"], 2)
        txt = pathlib.Path(self.html).read_text(encoding="utf-8")
        self.assertEqual(txt.count('class="card"'), 2)
        self.assertEqual(txt.count('class="opt"'), 8)          # 4 per card
        self.assertEqual(txt.count('data-correct="1"'), 2)     # 1 per card
        self.assertIn("data:image/png;base64,", txt)

    def test_self_contained_offline(self):
        run_quiz(self._spec(1), self.html)
        txt = pathlib.Path(self.html).read_text(encoding="utf-8")
        self.assertNotIn("http://", txt)
        self.assertNotIn("https://", txt)

    def test_missing_image_skipped(self):
        spec = self._spec(1)
        spec["questions"][0]["image_path"] = str(self.d / "nope.png")
        res = run_quiz(spec, self.html)
        self.assertTrue(res["success"], res.get("error"))
        self.assertEqual(res["question_count"], 0)

    def test_empty_stdin_fails(self):
        proc = subprocess.run([sys.executable, SCRIPT, "--out", self.html],
                              input="", capture_output=True, text=True)
        self.assertFalse(json.loads(proc.stdout)["success"])


if __name__ == "__main__":
    unittest.main()
