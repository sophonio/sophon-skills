"""Reads sales lines from a CSV file with the columns name, region and amount."""

import csv


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        index = {name: position for position, name in enumerate(header)}
        rows = []
        for record in reader:
            if not record:
                continue
            rows.append({
                "name": record[index["name"]],
                "region": record[index["region"]],
                "amount": float(record[index["amount"]]),
            })
        return rows
