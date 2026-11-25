import unittest
from datetime import date, datetime

from timesheet import report
from timesheet.storage import Entry


def entry(identifier, start, minutes, project="billing"):
    return Entry(identifier, datetime.fromisoformat(start), minutes, project, "ada")


class WeeklyTotalsTest(unittest.TestCase):
    def test_sums_minutes_per_project_and_week(self):
        totals = report.weekly_totals([
            entry("a", "2026-11-10T09:00:00", 60),
            entry("b", "2026-11-12T09:00:00", 30),
            entry("c", "2026-11-17T09:00:00", 15, "support"),
        ])
        self.assertEqual(totals, {date(2026, 11, 9): {"billing": 90}, date(2026, 11, 16): {"support": 15}})

    def test_archived_entries_do_not_count(self):
        archived = entry("a", "2026-11-10T09:00:00", 60)
        archived.archived = True
        self.assertEqual(report.weekly_totals([archived]), {})


if __name__ == "__main__":
    unittest.main()
