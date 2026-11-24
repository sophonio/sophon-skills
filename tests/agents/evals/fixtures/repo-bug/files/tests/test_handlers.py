import unittest
from datetime import datetime

from timesheet import handlers, routes
from timesheet.storage import Entry


def store():
    return handlers.Store([
        Entry("e1", datetime(2026, 11, 10, 9), 60, "billing", "ada"),
        Entry("e2", datetime(2026, 11, 10, 11), 30, "support", "grace"),
    ])


class HandlerTest(unittest.TestCase):
    def test_list_shows_only_the_callers_entries(self):
        status, body = handlers.list_entries(store(), handlers.Request(user="ada"))
        self.assertEqual((status, [item["id"] for item in body]), (200, ["e1"]))

    def test_archive_hides_an_entry_from_the_list(self):
        data = store()
        handlers.archive_entry(data, handlers.Request(user="ada", params={"id": "e1"}))
        self.assertEqual(handlers.list_entries(data, handlers.Request(user="ada"))[1], [])

    def test_routes_resolve_with_params(self):
        handler, params = routes.resolve("DELETE", "/entries/e2")
        self.assertEqual((handler, params), (handlers.delete_entry, {"id": "e2"}))


if __name__ == "__main__":
    unittest.main()
