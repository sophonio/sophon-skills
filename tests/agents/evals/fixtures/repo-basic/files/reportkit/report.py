"""Builds report lines from stored rows and renders them as a text table."""

from dataclasses import dataclass

COLUMNS = ("Name", "Region", "Amount", "Share")


@dataclass
class ReportLine:
    name: str
    region: str
    amount: float
    share: float


def build_lines(rows):
    totals = {}
    for row in rows:
        key = (row["name"], row["region"])
        totals[key] = totals.get(key, 0.0) + row["amount"]
    grand = sum(totals.values()) or 1.0
    lines = [ReportLine(name, region, amount, amount * 100 / grand) for (name, region), amount in totals.items()]
    lines.sort(key=lambda line: (-line.amount, line.name))
    return lines


def as_cells(line):
    return (line.name, line.region, f"{line.amount:.2f}", f"{line.share:.1f}%")


def render_table(lines):
    cells = [COLUMNS] + [as_cells(line) for line in lines]
    widths = [max(len(row[i]) for row in cells) for i in range(len(COLUMNS))]
    out = []
    for number, row in enumerate(cells):
        out.append("  ".join(value.ljust(widths[i]) for i, value in enumerate(row)).rstrip())
        if number == 0:
            out.append("  ".join("-" * width for width in widths))
    return "\n".join(out)
