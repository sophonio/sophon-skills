import unittest

from reportkit.greeting import greet


class GreetingTest(unittest.TestCase):
    def test_names_the_person(self):
        self.assertIn("Ada", greet("Ada"))


if __name__ == "__main__":
    unittest.main()
