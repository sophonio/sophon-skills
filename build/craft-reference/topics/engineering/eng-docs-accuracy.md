---
id: eng-docs-accuracy
summary: What to check per kind of quoted item, glossary rules, change-description forms with examples, skeletons by doc type.
reviewed: 2026-11
---
# Documentation accuracy: drift checks, glossary, change notes

## Quoted items

| Item in the doc | Check against | Usual drift |
|---|---|---|
| command | the package script, build target, CI step or CLI definition | a renamed script; a flag that moved to a subcommand |
| flag or option | the argument parser in the source | removed, renamed or with a new default |
| environment variable | where the code reads it | a new prefix; now required; a new default |
| file or folder path | the tree at the current commit | moved in a restructure |
| route or endpoint | the router or OpenAPI file | a new version prefix; a changed method |
| function, class or symbol | its definition and signature | renamed; a new parameter; a changed return |
| default or limit | the constant or config schema | the number changed in code, not in the doc |
| version number | the manifest or lockfile | the doc names an old major |
| sample output | a real run today | new columns, wording or order |
| behaviour claim ("retries three times") | the code path that does it | the code changed and the sentence did not |

## Glossary

- One term per concept; the glossary names it and lists aliases to avoid ("workspace, not project").
- A definition says what the thing is in this product, in one or two sentences, without implementation detail.
- Each term is used with the meaning the glossary gives; a second meaning gets a second term.
- New terms are added when first used in a doc, not later.

## Change descriptions

| Form | Shape | Weak | Better |
|---|---|---|---|
| commit subject | imperative, standalone, about 50 characters | "Fix bug" | "Reject expired coupons at checkout" |
| commit or PR body | what changed and why; what a reviewer checks | "Moving code from A to B" | "Move rate limits into the gateway so every route shares one counter" |
| changelog entry | what changed for the user, newest first, grouped as Added, Changed, Fixed, Removed | "Refactored the auth module" | "Sign-in links now expire after 15 minutes" |
| release note | the entries that matter to most users, then breaking changes with the migration step | "Various improvements" | "Breaking: `--out` is now `--output`; the old flag fails with a hint" |

Vague in change notes: "various", "improve", "enhance", "robust", "Phase 1"; the work done in place of the result.

## Skeletons

| Doc type | Sections in order |
|---|---|
| README | what it is (one sentence); install; first run with expected output; configuration; where to go next; licence |
| how-to | goal; prerequisites; numbered steps, one action each with the expected result; check that it worked; troubleshooting |
| reference | one entry per item (command, option, endpoint): syntax, parameters with types and defaults, example, errors |
| tutorial | what the reader builds; setup; steps that each end in a visible result; the finished state; next steps |
| troubleshooting | symptom as the reader sees it; cause; fix; how to confirm |
| decision record prose | title; status; context, decision and reason in 1-3 sentences |
