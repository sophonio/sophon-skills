"""Calendar helpers."""

from datetime import timedelta


def entry_day(entry):
    """The calendar day an entry is booked on: the day its work was finished."""
    finished = entry.start + timedelta(minutes=entry.minutes)
    return finished.date()


def week_start(day):
    """The Monday of the week that holds day."""
    return day - timedelta(days=day.weekday())
