"""Time entries from a CSV file with the columns id, start, minutes, project and owner."""

import csv
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Entry:
    id: str
    start: datetime
    minutes: int
    project: str
    owner: str
    archived: bool = False


def load_entries(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return [
            Entry(
                id=row["id"],
                start=datetime.fromisoformat(row["start"]),
                minutes=int(row["minutes"]),
                project=row["project"],
                owner=row["owner"],
            )
            for row in csv.DictReader(handle)
        ]
