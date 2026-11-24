# timesheet

Reads time entries (start, minutes, project, owner) from a CSV file and prints the minutes per
project for each week. A small JSON API lists, deletes and archives entries.

```
python -m timesheet weekly data/entries.csv
python -m timesheet serve --port 8100
```
