import unittest

from reportkit.slug import slugify


class SlugifyTest(unittest.TestCase):
    def test_lowercases_and_joins_words(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_drops_punctuation(self):
        self.assertEqual(slugify("Q3 report, final"), "q3-report-final")


if __name__ == "__main__":
    unittest.main()
