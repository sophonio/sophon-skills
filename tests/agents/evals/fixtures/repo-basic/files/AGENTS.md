# reportkit

Small reporting tool: a `report` command and a reports page over CSV files.

## Commands

- Test: `python -m unittest discover -s tests`
- Report: `python -m reportkit report data/sample.csv`
- Reports page: `python -m reportkit serve --port 8000`, then open http://localhost:8000/reports

## Rules

- Python 3.10 or later. The standard library only, except `reportkit/client.py`, which uses httpx.
- The version lives in `pyproject.toml` and in `reportkit/__init__.py`; keep them equal.
- `CHANGELOG.md` gets one entry per release, newest first.
