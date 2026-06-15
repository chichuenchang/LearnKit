import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = str(pathlib.Path(__file__).resolve().parents[1] / "data_writer.py")


def _run(args, stdin=None):
    proc = subprocess.run([sys.executable, SCRIPT, *args],
                          input=stdin, capture_output=True, text=True)
    return json.loads(proc.stdout)


def add(sd, course, images):
    return _run(["image", "add", "--savedata", sd, "--course", course],
                stdin=json.dumps(images))


def remove(sd, course, iid):
    return _run(["image", "remove", "--savedata", sd, "--course", course,
                 "--image-id", iid])


def read_bank(sd, course):
    p = (pathlib.Path(sd) / "courses" / course / "data" / "image_bank.json")
    return json.loads(p.read_text(encoding="utf-8"))


REC = {
    "unit_id": "week_06", "unit_slug": "week_06_foot",
    "source_file": "source_the_bones_of_the_foot.pdf", "page": 5,
    "image_path": "materials/week_06_foot/images/source_the_bones_of_the_foot_p05.png",
    "image_w": 1100, "image_h": 1500, "title": "The Talus", "label_source": "ocr",
    "structures": [
        {"name": "Talus", "type": "bone", "source": "slide",
         "label_bbox": [0.62, 0.40, 0.10, 0.03], "confidence": 0.91},
        {"name": "Dorsalis pedis a.", "type": "artery", "source": "ai",
         "label_bbox": None, "confidence": None, "verified": False},
    ],
}


class ImageAddTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sd = self._tmp.name
        self.course = "test_101"

    def tearDown(self):
        self._tmp.cleanup()

    def test_add_single(self):
        res = add(self.sd, self.course, [REC])
        self.assertTrue(res["success"])
        self.assertEqual(res["added"], 1)
        bank = read_bank(self.sd, self.course)
        img = bank["images"][0]
        self.assertEqual(img["image_id"], "img_test_101_001")
        self.assertEqual(img["page"], 5)
        self.assertEqual(img["structures"][0]["verified"], True)   # slide default
        self.assertEqual(img["structures"][1]["verified"], False)  # ai

    def test_dedup_by_source_and_page(self):
        add(self.sd, self.course, [REC])
        same = dict(REC)            # same source_file + page 5
        other = dict(REC, page=6)   # same source, different page
        res = add(self.sd, self.course, [same, other])
        self.assertEqual(res["added"], 1)
        self.assertEqual(res["skipped"], 1)
        self.assertEqual(res["ids"], ["img_test_101_002"])

    def test_freeform_type_accepted(self):
        # type is course-agnostic / free-form — any subject term is accepted
        rec = dict(REC, structures=[{"name": "France", "type": "country", "source": "slide"}])
        res = add(self.sd, self.course, [rec])
        self.assertTrue(res["success"])
        st = read_bank(self.sd, self.course)["images"][0]["structures"][0]
        self.assertEqual(st["type"], "country")

    def test_empty_stdin_fails(self):
        res = _run(["image", "add", "--savedata", self.sd,
                    "--course", self.course], stdin="")
        self.assertFalse(res["success"])


class ImageRemoveTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sd = self._tmp.name
        self.course = "test_101"
        add(self.sd, self.course, [REC, dict(REC, page=6)])

    def tearDown(self):
        self._tmp.cleanup()

    def test_remove_existing(self):
        res = remove(self.sd, self.course, "img_test_101_001")
        self.assertTrue(res["success"])
        ids = [i["image_id"] for i in read_bank(self.sd, self.course)["images"]]
        self.assertEqual(ids, ["img_test_101_002"])

    def test_remove_missing(self):
        res = remove(self.sd, self.course, "img_test_101_999")
        self.assertFalse(res["success"])
        self.assertIn("not found", res["error"])


if __name__ == "__main__":
    unittest.main()
