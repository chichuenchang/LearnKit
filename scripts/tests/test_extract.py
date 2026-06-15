import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import extract_text  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
