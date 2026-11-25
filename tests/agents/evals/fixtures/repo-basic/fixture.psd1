# repo-basic: a small Python command-line project (reportkit) with passing tests and an AGENTS.md that names
# its commands. Planted on purpose: slugify("Hello  World") returns "hello--world"; the greeting says "Helo";
# the report command crashes on data/empty.csv; the version lives in pyproject.toml and reportkit/__init__.py;
# requirements.lock pins the HTTP library that reportkit/client.py uses. The release-1.4.0 patch gives it a remote.
@{
  Description = 'Python CLI and reports page over CSV files; unittest suite; version in two files; a lockfile'
  Test = 'python -B -m unittest discover -s tests'
  Patches = @{
    'last-edit' = @{ Why = 'a small edit after a green run (the Amount column renamed); the header test now fails' }
    'export-requirements' = @{ Why = 'an approved requirements file for the export feature (R1 CSV, R2 PDF, R3 filter)' }
    'release-1.4.0' = @{ Why = 'main pushed to a local bare remote (origin), then one unpushed commit: version 1.4.0 in both files, its changelog entry and the greeting fixed'; Commit = 'Prepare 1.4.0'; Remote = 'origin' }
  }
}
