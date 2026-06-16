import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

SCRIPT = str(pathlib.Path(__file__).resolve().parents[1] / "image_bank_build.py")


def run(spec):
    proc = subprocess.run([sys.executable, SCRIPT], input=json.dumps(spec),
                          capture_output=True, text=True)
    return json.loads(proc.stdout)


def read_bank(sd, course):
    p = pathlib.Path(sd) / "courses" / course / "data" / "image_bank.json"
    return json.loads(p.read_text(encoding="utf-8"))


class ImageBankBuildTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        self.sd = str(self.root / "savedata")
        self.course = "test_101"
        self.pages_dir = self.root / "pages"
        self.images_dir = self.root / "images"
        self.pages_dir.mkdir(parents=True)
        # 200x300 page; "Talus" sits in the top half (y=0.2 < 0.5)
        Image.new("RGB", (200, 300), "white").save(self.pages_dir / "page_005.png")
        self.img_json = self.root / "img.json"
        self.img_json.write_text(json.dumps({"pages": [
            {"page": 5, "words": [{"text": "Talus", "bbox": [0.6, 0.2, 0.1, 0.03]}]}
        ]}), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _spec(self, **over):
        spec = {
            "savedata": self.sd, "course": self.course,
            "img_json": str(self.img_json), "pages_dir": str(self.pages_dir),
            "images_dir": str(self.images_dir),
            "image_path_prefix": "materials/week_06_foot/images",
            "slug": "source_foot", "unit_id": "week_06",
            "unit_slug": "week_06_foot", "source_file": "source_foot.pdf",
            "captures": [{"page": 5, "half": "top", "title": "The Talus",
                          "structures": [["Talus", "bone"], ["Missing", "bone"]]}],
        }
        spec.update(over)
        return spec

    def test_build_writes_records_and_crop(self):
        res = run(self._spec())
        self.assertTrue(res["success"], res)
        self.assertEqual(res["added"], 1)
        self.assertEqual(res["report"], ["p5t:1/2"])  # 1 of 2 labels found
        # cropped PNG written to images_dir
        self.assertTrue((self.images_dir / "source_foot_p05t.png").exists())
        img = read_bank(self.sd, self.course)["images"][0]
        self.assertEqual(img["image_w"], 200)
        self.assertEqual(img["image_h"], 150)        # top half of 300
        self.assertEqual(img["label_source"], "textlayer")
        self.assertEqual(len(img["structures"]), 1)  # only the matched phrase boxed
        st = img["structures"][0]
        self.assertEqual(st["name"], "Talus")
        # y=0.2 in full page -> 0.4 in top-half crop space
        self.assertAlmostEqual(st["label_bbox"][1], 0.4, places=3)

    def test_missing_spec_field_fails_gracefully(self):
        spec = self._spec()
        del spec["captures"]
        res = run(spec)
        self.assertFalse(res["success"])
        self.assertIn("captures", res["error"])

    def test_invalid_stdin_fails_gracefully(self):
        proc = subprocess.run([sys.executable, SCRIPT], input="not json",
                              capture_output=True, text=True)
        res = json.loads(proc.stdout)
        self.assertFalse(res["success"])


if __name__ == "__main__":
    unittest.main()
