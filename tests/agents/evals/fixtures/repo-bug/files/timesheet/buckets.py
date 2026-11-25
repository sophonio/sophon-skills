"""Groups entries into weeks."""

from . import timeutil


def group_by_week(entries):
    weeks = {}
    for entry in entries:
        if entry.archived:
            continue
        monday = timeutil.week_start(timeutil.entry_day(entry))
        weeks.setdefault(monday, []).append(entry)
    return weeks
