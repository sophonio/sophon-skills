## Findings block
```
FINDINGS
F1 | Critical | confidence 90 | src/a.cs:42 | correctness
  Claim: <one line>
  Fails when: <input or state> → <wrong result or crash>
  Fix: <one line>
  Evidence: <quoted line with path:line, or command output>
POSSIBLE: <below-threshold items, one line each> | none
NOT_CHECKED: <scope not covered, and why> | none
```
- Critical = wrong behaviour, data loss, security exposure or a broken build on a normal path. Important = must fix before merge: missed requirement, fragile error handling, a test asserting nothing, likely regression. Minor = polish, or for security an older flaw. A plan or author's choice never lowers severity.
- Votes (refute, verify): `F1: CONFIRMED | REFUTED — <path:line evidence>`; unsure = `REFUTED (unsure)`; security adds ` · predates: yes|no`. Re-review: `F1: ADDRESSED | NOT_ADDRESSED — <path:line>`.
- VERDICT: review `APPROVE | REQUEST_CHANGES` (REQUEST_CHANGES iff any Critical or Important) + `SPEC: MET | GAPS | CANNOT_VERIFY`; refute n/a; re-review `ALL_ADDRESSED | OPEN`; completeness `COMPLETE | GAPS`; security `CLEAN | ISSUES`; QA `PASS | PASS_WITH_WARNINGS | FAIL`; debugger investigate/fix `ROOT_CAUSE_FOUND | NOT_REPRODUCED | INCONCLUSIVE`, hypothesis `CONFIRMED | FALSIFIED | INCONCLUSIVE`; architect `READY | NEEDS_DECISION`; researcher, developer, UX n/a (a UX judge starts SUMMARY with `WINNER <n>`).
