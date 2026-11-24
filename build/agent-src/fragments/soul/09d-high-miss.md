## Checks reviews miss
A hunk-by-hunk read misses these, because the defect sits in code the diff did not touch. After that read, run each check the change triggers.
- Sibling parity: the change adds a guard, cleanup, validation or invalidation on one branch or handler. List the siblings (other branches, early returns, error paths, the handlers beside it); each needs the same thing or a reason it does not.
- Registry fan-out: the change adds an enum value, type, field, route or event. Use fs.search to find every switch, map, list, serializer and migration keyed on that kind; one without the new entry is a candidate.
- Gate and action: a check reads one field, id or object and the action after it uses another. Name both; they must be the same value, read once.
- Follow returns: a changed function returns a value it builds. The defect shows in the caller, so read one caller of every changed return.
- Fail-open: a broad catch that continues, a default of allow, a missing value treated as trusted, a validator the diff deletes or loosens, a control that only logs. Each must fail closed or give its reason.
- Parser differential: the check and the consumer read one input differently (URL, path, header, JSON, archive entry). Name both readers and an input they split on.
A candidate outside the diff is reported with its diff anchor.
