# repo-basic: a small Python command-line project (reportkit) with passing tests and an AGENTS.md that names
# its commands. Planted on purpose: slugify("Hello  World") returns "hello--world"; the greeting says "Helo";
# the report command crashes on data/empty.csv; the version lives in pyproject.toml and reportkit/__init__.py;
# requirements.lock pins the HTTP library that reportkit/client.py uses.
@{
  Description = 'Python CLI and reports page over CSV files; unittest suite; version in two files; a lockfile'
  Test = 'python -B -m unittest discover -s tests'
  Patches = @{
    'last-edit' = @{ Why = 'a small edit after a green run (the Amount column renamed); the header test now fails' }
    'export-requirements' = @{ Why = 'an approved requirements file for the export feature (R1 CSV, R2 PDF, R3 filter)' }
  }
}
