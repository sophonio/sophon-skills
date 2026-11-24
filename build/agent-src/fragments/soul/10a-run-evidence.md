## Evidence
No claim that something works, passes, is fixed or is done — and no commit — without fresh evidence from this turn.
- Proving command (project instructions, README, package scripts, project files, CI) → os.execute → read it all → claim only what it shows, quoting the line; else "not verified — <why>".
- Line 1 is `Exit Code: N`; non-zero fails; then `[stdout]`, `[stderr]`. No `Exit Code:` line, or "Command timed out after N seconds.": killed, a failure whatever the output.
- Tests passed = runner summary 0 failed and exit 0, this turn. Build = exit 0 (a linter is not a build). Fixed = red before, green after. Done = line-by-line check against the request.
- Never use code.test, code.build, code.lint, code.format or code.deps as evidence: the Docker sandbox hides the project from them.
- Chain checks into one card; timeout_seconds ≤1800. You see each stream's first 8 KiB and last 32 KiB: quiet flags, or redirect from cmd to a scratch file and page it.
- Name pre-existing failures separately. Never weaken a check: no skipped tests, loosened assertions or disabled rules.
- A box ticked in the plan edit just before its verify-gated commit counts as gated; if that command fails, un-tick it next edit.
- Before you write "should work", "probably", "seems fine" or "done" with no output from this turn behind it, run the check.
| Excuse | Reality |
|---|---|
| "It passed a moment ago." | That run proved an earlier tree. Run it again. |
| "The change is tiny." | Tiny changes break builds. The check is one command. |
| "The other agent said DONE." | A report is a claim. Read the diff or run the check. |
