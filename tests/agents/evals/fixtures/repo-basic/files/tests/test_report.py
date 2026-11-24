import unittest

from reportkit import report


ROWS = [
    {"name": "Ada", "region": "North", "amount": 60.0},
    {"name": "Grace", "region": "South", "amount": 40.0},
]


class ReportTest(unittest.TestCase):
    def test_lines_carry_share_of_total(self):
        lines = report.build_lines(ROWS)
        self.assertEqual([(line.name, round(line.share)) for line in lines], [("Ada", 60), ("Grace", 40)])

    def test_table_has_header_and_one_row_per_line(self):
        table = report.render_table(report.build_lines(ROWS)).splitlines()
        self.assertEqual(table[0].split(), ["Name", "Region", "Amount", "Share"])
        self.assertEqual(len(table), 4)


if __name__ == "__main__":
    unittest.main()
