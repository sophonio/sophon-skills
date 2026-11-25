"""Weekly totals per project."""

from . import buckets


def weekly_totals(entries):
    totals = {}
    for monday, week in sorted(buckets.group_by_week(entries).items()):
        per_project = {}
        for entry in week:
            per_project[entry.project] = per_project.get(entry.project, 0) + entry.minutes
        totals[monday] = per_project
    return totals


def render(totals):
    out = []
    for monday, per_project in totals.items():
        out.append(f"Week of {monday.isoformat()}")
        for project, minutes in sorted(per_project.items()):
            out.append(f"  {project}: {minutes} min")
    return "\n".join(out)
