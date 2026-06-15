import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = str(pathlib.Path(__file__).resolve().parents[1] / "data_writer.py")


def _run(args, stdin=None):
    proc = subprocess.run(
        [sys.executable, SCRIPT, *args],
        input=stdin, capture_output=True, text=True,
    )
    return json.loads(proc.stdout)


def add(savedata, course, problems):
    return _run(
        ["pool", "add", "--savedata", savedata, "--course", course],
        stdin=json.dumps(problems),
    )


def remove(savedata, course, pid):
    return _run(
        ["pool", "remove", "--savedata", savedata, "--course", course,
         "--problem-id", pid],
    )


def read_pool(savedata, course):
    p = (pathlib.Path(savedata) / "courses" / course / "data"
         / "problem_pool.json")
    return json.loads(p.read_text(encoding="utf-8"))


MCQ = {
    "question": "Which nerve innervates gluteus medius?",
    "answer": "Superior gluteal nerve",
    "question_type": "mcq",
    "options": ["Superior gluteal nerve", "Sciatic nerve"],
    "unit_id": "week_03",
    "topic": "Nerves of gluteal region",
    "source": "Midterm 1 2025",
    "source_file": "source_midterm1.pdf",
    "source_type": "past_exam",
    "verbatim": True,
}


class PoolAddTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sd = self._tmp.name
        self.course = "test_101"

    def tearDown(self):
        self._tmp.cleanup()

    def test_add_single(self):
        res = add(self.sd, self.course, [MCQ])
        self.assertTrue(res["success"])
        self.assertEqual(res["added"], 1)
        self.assertEqual(res["skipped"], 0)
        pool = read_pool(self.sd, self.course)
        self.assertEqual(len(pool["problems"]), 1)
        prob = pool["problems"][0]
        self.assertEqual(prob["problem_id"], "prob_test_101_001")
        self.assertEqual(prob["options"], MCQ["options"])
        self.assertEqual(prob["verbatim"], True)

    def test_id_increment_across_calls(self):
        add(self.sd, self.course, [MCQ])
        q2 = dict(MCQ, question="Second question?")
        q3 = dict(MCQ, question="Third question?")
        res = add(self.sd, self.course, [q2, q3])
        self.assertEqual(res["added"], 2)
        self.assertEqual(res["ids"], ["prob_test_101_002", "prob_test_101_003"])

    def test_dedup_same_question(self):
        add(self.sd, self.course, [MCQ])
        res = add(self.sd, self.course, [dict(MCQ)])
        self.assertEqual(res["added"], 0)
        self.assertEqual(res["skipped"], 1)
        self.assertEqual(len(read_pool(self.sd, self.course)["problems"]), 1)

    def test_invalid_question_type(self):
        bad = dict(MCQ, question_type="fill_blank")
        res = add(self.sd, self.course, [bad])
        self.assertFalse(res["success"])
        self.assertIn("question_type", res["error"])

    def test_defaults_for_minimal_short_answer(self):
        minimal = {
            "question": "Name the hip flexors.",
            "answer": "Iliopsoas, rectus femoris",
            "question_type": "short_answer",
        }
        add(self.sd, self.course, [minimal])
        prob = read_pool(self.sd, self.course)["problems"][0]
        self.assertEqual(prob["options"], [])
        self.assertEqual(prob["source_file"], "manual")
        self.assertEqual(prob["source_type"], "manual")
        self.assertEqual(prob["verbatim"], False)
        self.assertEqual(prob["tags"], [])

    def test_empty_stdin_fails(self):
        res = _run(["pool", "add", "--savedata", self.sd,
                    "--course", self.course], stdin="")
        self.assertFalse(res["success"])


class PoolRemoveTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sd = self._tmp.name
        self.course = "test_101"
        add(self.sd, self.course, [MCQ, dict(MCQ, question="Second?")])

    def tearDown(self):
        self._tmp.cleanup()

    def test_remove_existing(self):
        res = remove(self.sd, self.course, "prob_test_101_001")
        self.assertTrue(res["success"])
        self.assertEqual(res["removed"], "prob_test_101_001")
        ids = [p["problem_id"] for p in read_pool(self.sd, self.course)["problems"]]
        self.assertEqual(ids, ["prob_test_101_002"])

    def test_remove_missing(self):
        res = remove(self.sd, self.course, "prob_test_101_999")
        self.assertFalse(res["success"])
        self.assertIn("not found", res["error"])


if __name__ == "__main__":
    unittest.main()
