import unittest
from datetime import date

from timesheet.timeutil import week_start


class WeekStartTest(unittest.TestCase):
    def test_monday_is_its_own_week_start(self):
        self.assertEqual(week_start(date(2026, 11, 16)), date(2026, 11, 16))

    def test_sunday_belongs_to_the_week_before(self):
        self.assertEqual(week_start(date(2026, 11, 15)), date(2026, 11, 9))


if __name__ == "__main__":
    unittest.main()
