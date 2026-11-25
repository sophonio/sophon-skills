import os
import tempfile
import unittest

from reportkit.storage import load_rows


class StorageTest(unittest.TestCase):
    def test_reads_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "rows.csv")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("name,region,amount\nAda,North,1.5\n")
            self.assertEqual(load_rows(path), [{"name": "Ada", "region": "North", "amount": 1.5}])


if __name__ == "__main__":
    unittest.main()
