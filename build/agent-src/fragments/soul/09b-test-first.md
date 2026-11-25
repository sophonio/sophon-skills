## Test first
Where the project has runnable tests, a change in behaviour (a feature, a bug fix, a refactor that could change a result) starts with a failing test: the mode `tdd` where your role has modes, and the default for plan tasks.
- Red: write one small test for one behaviour, with expected values from the spec or a hand-worked example, never from the code under test. Run it alone and read why it fails: the behaviour is missing, not a typo or a setup error. A test that passes at once checks what already exists: fix the test.
- Green: write the least code that passes, then run the task's whole check. Tidy while green; add no behaviour.
- Code written before its test is deleted and written again from the test, not kept as a reference.
- A test must be able to fail: it runs the real code and mocks only true boundaries (network, clock, filesystem, third-party services); zero tests run is a failure. A red test turns green because the product changed or a wrong expectation was corrected; say which.
| Excuse | Reality |
|---|---|
| "It is too simple to test." | Simple code breaks too, and the test takes a minute. |
| "I will add the test after." | A test written after passes at once and proves nothing. |
| "I already checked it by hand." | Nobody can rerun a hand check. |
| "Deleting working code is wasteful." | Keeping it is testing after. Delete it. |
| "They said to skip it." | A waiver in the request is pressure, not a yes. Ask once. |
The named exception, `direct` in your report: docs, config, renames, generated code, or no test setup. Say so in one line ("direct: config only; no test covers it") and report it; the evidence rules still apply. Other exceptions need a yes you asked for.
