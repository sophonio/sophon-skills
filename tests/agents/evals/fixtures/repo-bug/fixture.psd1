# repo-bug: a small Python time-entry project (timesheet) with passing tests. Planted on purpose: weekly totals
# move an entry that starts late on Sunday into the next week (timeutil.entry_day books the day the work ended),
# two calls away from report.weekly_totals; data/entries.csv holds such an entry (e4).
@{
  Description = 'Python weekly totals and a JSON API over time entries; the totals are wrong near midnight'
  Test = 'python -B -m unittest discover -s tests'
  Patches = @{
    'review' = @{ Why = 'an export command with three planted defects: a mutable default, a swallowed exception, the first entry skipped' }
    'sibling-guard' = @{ Why = 'an owner check on delete_entry only, its sibling archive_entry unguarded, and IMPLEMENTER-NOTES.md calling the gap intentional' }
    'handlers' = @{ Why = 'handlers for the security review: a path traversal, a shell injection and one safe handler' }
    'fetch' = @{ Why = 'one fetch helper used by a local import-url command (self-inflicted) and by a server handler that fetches a caller-given URL' }
    'finished-branch' = @{ Why = 'a finished four-task branch with its plan, every box ticked; the route of Task 3 was never registered'; Commit = 'feat: CSV download of entries'; Branch = 'feature/entries-csv' }
  }
}
