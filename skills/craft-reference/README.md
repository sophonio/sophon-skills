# Craft Reference

A read-only reference library for the Buildersoft development agents on the Sophon Marketplace:
long tables, checklists and templates for interface design, product documents, engineering
reviews, releases and agent instructions. An agent's instructions name a topic at the step that
uses it; the agent reads that one topic with `craft.read` and gets plain markdown back.

No network, no credentials, no files: the topics are embedded in the skill. Both tools have risk
level `none`, so they raise no approval card.

> **Status: 1.0.0 in preparation.** This version carries one stub per topic: its title and its
> planned section headings. The full topic text arrives before the first publish.

## Optional by design

Every agent that names a topic also works without this skill. Gates, approvals, scope and output
formats live in each agent's own instructions; a topic only adds depth. When the skill is not
installed, when plan mode is on, or when the Gateway has no Docker sandbox, the call is refused and
the agent works from the summary it carries.

## Tools

| Tool | Parameters | Returns |
|---|---|---|
| `craft.topics` | `family` (optional): `design`, `product`, `engineering`, `release` or `agent` | One JSON object: skill, version, corpus hash (12 hex digits), count and one row per topic (id, family, title, bytes). With `family`, each row also has its summary, section ids, origin and review month. |
| `craft.read` | `topic` (required), `section` (optional) | The topic, or one `## ` section of it, as ASCII markdown behind a three-line header: version, id, part, byte count and review month; a fixed line that says the text is reference data; the sources of an adapted topic. |

Errors are one JSON object with an `error` sentence and a stable `code`: `UNKNOWN_TOOL`,
`BAD_INPUT` (with `families` when the family was wrong), `UNKNOWN_TOPIC` (with every id),
`UNKNOWN_SECTION` (with the topic's section ids) and `INTERNAL`. A topic is at most 12,288 bytes,
so one call returns it whole; the corpus is at most 204,800 bytes.

Each call starts a sandbox container (about one to two seconds). A topic id is permanent from
1.0.0: a retired topic keeps a stub that names its successor.

## Topics

Generated from `build/craft-reference/topics.index.json` by `build/craft-reference/generate.py`.

<!-- topics:begin -->

| Id | Family | Title | Sections | Bytes | Origin |
|---|---|---|---|---|---|
| `design-sophon-default` | design | Sophon default: full token tables | 10 | 10061 of 10240 | original |
| `design-sophon-components` | design | Sophon default: archetypes, layout and components | 11 | 7302 of 8192 | original |
| `design-schools` | design | Design schools: six recipes in one anatomy | 7 | 7442 of 11264 | adapted |
| `design-open-systems` | design | Open design systems: five recipes | 5 | 8082 of 9216 | original |
| `design-directions-round` | design | Direction round: option anatomy and examples | 4 | 3502 of 4096 | adapted |
| `design-generated-defaults` | design | Generated-looking defaults: the dated catalogue | 7 | 8111 of 11264 | adapted |
| `design-critique-rubric` | design | Critique rubric: heuristics, personas, severities | 4 | 5982 of 7168 | adapted |
| `design-refinement-verbs` | design | Refinement verbs: bolder, quieter, distill, polish | 5 | 3836 of 5120 | adapted |
| `design-motion` | design | Motion: purpose, durations, easing, reduced motion | 4 | 4220 of 5120 | adapted |
| `design-md-template` | design | DESIGN.md: skeleton, token block and dated rules | 4 | 5102 of 5120 | adapted |
| `design-frontend-floors` | design | Frontend floors: use what exists, the interaction floor | 2 | 4628 of 5120 | adapted |
| `design-states-matrix` | design | States: nine control states, five page states, break data | 3 | 4619 of 5120 | original |
| `design-variants` | design | Variants: axes, comparison table, switcher | 3 | 1456 of 2048 | adapted |
| `design-a11y-preferences` | design | Preference checks: reduced motion, contrast, forced colours | 3 | 3624 of 4096 | original |
| `design-token-guards` | design | Token guards: literal, parity and contrast tests | 4 | 4013 of 4096 | original |
| `design-evaluate` | design | Measuring a page without sight: evaluate recipes | 7 | 5107 of 5120 | original |
| `product-brief` | product | Product brief and PRODUCT.md skeletons | 3 | 3029 of 4096 | adapted |
| `product-prd` | product | Lean PRD: sections, id forms, examples | 4 | 4094 of 5120 | adapted |
| `product-discovery` | product | Discovery question bank and premise forms | 3 | 2979 of 3072 | adapted |
| `product-prioritisation` | product | Prioritisation lenses and the pre-mortem sheet | 4 | 2637 of 3072 | original |
| `product-tickets` | product | Tickets: requirements and story files, status words, id chain | 5 | 4370 of 5120 | adapted |
| `product-slicing` | product | Slicing patterns: thin paths and story splits | 3 | 3518 of 4096 | original |
| `product-acceptance` | product | Acceptance: criteria patterns and the evidence table | 2 | 3831 of 4096 | original |
| `eng-review-checks` | engineering | Review checks by defect class | 5 | 4588 of 5120 | adapted |
| `eng-silent-failures` | engineering | Silent failures: catches, defaults and fallbacks | 3 | 3038 of 3072 | adapted |
| `eng-test-quality` | engineering | Test quality: tautology, vacuity, boundaries, examples | 4 | 4540 of 5120 | adapted |
| `eng-debugging-tactics` | engineering | Debugging: reproduction loops and tactics by symptom | 4 | 4618 of 5120 | adapted |
| `eng-security-checklist` | engineering | Security checklist by class, with the high-miss patterns | 2 | 5784 of 6144 | adapted |
| `eng-privacy-sweep` | engineering | Privacy sweep: personal data fields and flows | 3 | 3031 of 3072 | original |
| `eng-adr` | engineering | Decision records: the gate, the short form, worked examples | 3 | 2539 of 3072 | adapted |
| `eng-api-contract` | engineering | API contract checklist | 6 | 2760 of 3072 | original |
| `eng-e2e` | engineering | Browser end-to-end tests: locators, waits, healing | 4 | 3435 of 4096 | adapted |
| `eng-mcp-contract` | engineering | MCP tool contracts and the evaluation set | 3 | 3603 of 4096 | adapted |
| `eng-perf-measure` | engineering | Measuring performance: baselines, noise, reporting | 5 | 2554 of 3072 | adapted |
| `eng-sources-versions` | engineering | Sources and versions: where the version lives, by ecosystem | 3 | 1955 of 2048 | adapted |
| `eng-docs-accuracy` | engineering | Documentation accuracy: drift checks, glossary, change notes | 4 | 3063 of 3072 | adapted |
| `release-ship` | release | Shipping: version places, changelog forms, pre-ship checks | 4 | 3515 of 4096 | original |
| `release-deploy-rollback` | release | Deploy and rollback: checklists and health signals | 7 | 3994 of 5120 | adapted |
| `agent-pressure-tests` | agent | Pressure tests: scenario format, pressures, run tables | 4 | 4127 of 5120 | adapted |
| `agent-instruction-style` | agent | Instruction forms: which form fits which failure | 4 | 3498 of 4096 | adapted |
| `agent-package-facts` | agent | Sophon package facts: files, limits, scanner families | 4 | 2980 of 3072 | original |

<!-- topics:end -->

## How this skill is built

The topic sources live in `build/craft-reference/topics/<family>/<id>.md`. The generator checks
them (ASCII only, size limits, heading rules, no phrase that Sophon's content scanner flags, no
agent protocol words) and writes the embedded block of `main.py`, the table above,
`THIRD_PARTY_NOTICES.md` and `build/craft-reference/topics.lock.json`:

```
python -B build/craft-reference/generate.py            # regenerate
python -B build/craft-reference/generate.py --check    # fail on drift (CI)
python -B build/craft-reference/generate.py --summary  # sizes per topic and family
python tests/skills/test_craft_reference.py            # offline tests
```

## Licence and notices

Licensed under the Apache License, Version 2.0; see `LICENSE`. Every topic is written in
Buildersoft LLC's own words; `THIRD_PARTY_NOTICES.md` credits the upstream projects whose ideas or
structure an adapted topic follows.

The names of the public design systems and of the upstream projects belong to their owners and
are used only to identify them.
