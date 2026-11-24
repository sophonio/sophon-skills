# reportkit

reportkit turns a CSV file of sales lines into a report: one line per name and region, with the
amount and its share of the total.

```
python -m reportkit report data/sample.csv
python -m reportkit serve --port 8000
```

The reports page lists the same table at `/reports`, and `/api/reports` returns it as JSON.
