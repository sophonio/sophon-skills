# timesheet

Time entries in a CSV file, weekly totals per project, and a small JSON API over the entries.

## Commands

- Test: `python -m unittest discover -s tests`
- Weekly totals: `python -m timesheet weekly data/entries.csv`
- API: `python -m timesheet serve --port 8100`

## Rules

- Python 3.10 or later, standard library only.
- Weeks start on Monday. Times in the CSV are local times without an offset.
- Every API route is listed in `timesheet/routes.py`.
