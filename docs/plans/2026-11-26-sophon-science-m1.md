# Plan: Sophon Science M1 — evidence, bounded statistics and the science family
Status: in-progress
Date: 2026-11-26 · Agent: lead-developer · Size: large · Base: main@0103b15c · Branch: sophon/science-m1
Approved: 2026-11-26 via info.request
Consent: Team per task (2026-11-26)
Execution: inline
Spec: docs/plans/2026-11-26-sophon-science-design.md
Discovery: opted out · Voice: plain
Request: "We need to research on how claude science works, and lets create agents and skills to compete with it, lets analyze them deelpy and come with a plan on how to implement these skills and agents to allow science to happen in Sophon as well, using all the Sophon features as well."

## Goal
A user can ask Sophon a biomedical question over public literature and a small synthetic table, and receive a report whose every number and citation is traceable to a recorded tool result, checked by a separate reviewer, with the registered calculation replayed — delivered as three tested skills and a four-agent `science` family that leaves every existing package byte-identical.

## Context
- Claude Science (documentation read 2026-11-26, vendor claims, not tested): skills are written instructions and connectors are read-only data sources (https://claude.com/docs/claude-science/connectors-and-skills); its reviewer checks claims against the execution record and "doesn't re-run analyses" (https://claude.com/docs/claude-science/the-reviewer); the execution log is authoritative over reconstructed code (https://claude.com/docs/claude-science/artifacts); Modal compute has no spend ceiling (https://claude.com/docs/claude-science/compute-providers).
- A skill is `manifest.json` + entrypoint + `README.md` + `LICENSE`; only the entrypoint is copied into the Docker sandbox, `lib/` and `vendor/` work on the process backend only (`CONTRIBUTING.md:22-35`). With `requirements` empty, any `import X`/`from X` line with non-stdlib X is pip-installed (`CONTRIBUTING.md:128`).
- Tool names are unique across the repo and the built-in catalogue, also after `.`→`_`; schema subset: no `oneOf`/`anyOf`/`allOf`/`$ref`/`not`, string enums only, `items` on every array, no parameter named `tool` (`CLAUDE.md`, "Build checks"). A search of `skills/*/manifest.json` for `science_`, `science.` and `sci.` found no tool names.
- Offline HTTP tests use `tests/skills/mockhttp.py` (`run_tool`, `resp`, `err`, `check`; lines 1-21); `tests/skills/run_all.py:10` runs every `test_*.py`. The container smoke is `tests/skills/run_all_container.py` (python:3.13-alpine, entrypoint run with a `params` global, `pip_names` replay at :57-68).
- Reference skill shapes: keyless network skill `skills/package-registry/manifest.json` (network true, 30 s, 256 MB); offline stdlib skill `skills/units-convert/main.py:1-14`; handler table and JSON error output `skills/wikipedia/main.py:161-176`.
- Families: registry `build/agent-src/families.psd1:7-11`; one-agent family template `build/agent-src/families/video/family.psd1:9-58`; optional family and agent keys `build/AgentFamily.psm1:20-53`; SkillPolicy rules `docs/AGENTS.md:521-543`; a family without a `readmes/` folder has hand-written READMEs (`CLAUDE.md`, "Files"). Package files: exactly `manifest.json`, `SOUL.md`, `TOOLS.md`, `README.md`, `LICENSE`.
- Method checks run only when a family has a `Method` key (`build/AgentFamily.psm1:2106-2108`); an excuse table outside a registered rule fails `METHOD-EXCUSES` (`CLAUDE.md`, "Method"). Anchors are read from `tests/agents/fixtures/anchors/<family>.psd1` when present (`build/Test-AgentSources.ps1:887-890`).
- DOC-COUNT reads the documents in `build/agent-src/catalog/doc-counts.psd1:9-19`; the repository states "twenty-two" packages (`tests/README.md:86`). The scenario lint checks ids, roster membership, fixtures and that no 40-character turn text appears under `agents/` or `build/agent-src/` (`tests/agents/evals/README.md:110-121`).
- Regression gate: video-producer and the development packages stay byte-identical (`docs/AGENTS.md:561-567`).
- Literature terms verified 2026-11-26: E-utilities 3 requests/s without a key, 429 above the limit, third-party apps should let users supply their own key (https://support.nlm.nih.gov/kbArticle/?pn=KA-05510); Crossref public pool 5/s DOI lookups, 1/s queries, 429 on excess (https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/); Europe PMC forbids automated bulk download of non-open-access content (https://dev.europepmc.org/developers).
- Assumption: the keyless public pools are enough for M1; per-user NCBI keys and OpenAlex keys wait for a later milestone — the design keeps M1 free of credentials.
- Assumption: the family is MIT, version 1.0.0, `FamilyMajor = 1`, category `ai`, required tag `science`, like the video family; nothing is published in M1.
- Assumption: "one HTTP attempt per call" in the design means no automatic retries; a tool may make the fixed sequence of requests its contract names (search then summary).
- Decision (2026-11-26): agent instruction text is written in `direct` mode with static checks and written scenarios; live behavioural evaluation is a mandatory gate before any publishing (user answer "Stage packages"). The skills stay test-first.

## Approach
Build the three stdlib skills first, test-first, each a single `main.py` that exchanges bounded JSON payloads and returns structured errors; `science-statistics` emits analysis records that `science-evidence` can verify, and both share one canonical-JSON hashing rule. Then add a fourth family, `science`, beside `development` and `video`: four agents composed from its own fragments, using the skills only through `SkillPolicy`, with only `science-lead` delegating. Static anchors and four written acceptance scenarios pin the behaviour we will later run live; documentation counts move from twenty-two to twenty-six packages.
- Rejected: prompt-only specialists — no checkable record (design note).
- Rejected: numpy/scipy requirements — unverified sandbox install behaviour and a new dependency.
- Rejected: copying BioNeMo or Claude skill text — licence conversion and attribution not decided.
- Rejected: OpenAlex in M1 — key and daily budget required at scale.

## Global constraints
- Skills: stdlib only, single `main.py`, no `lib/`, no `vendor/`, no `requirements`, no credentials, `runtime` `sandbox`, `language` `python`, MIT `LICENSE` byte-identical to the root `LICENSE`, version `1.0.0`.
- Every tool returns one JSON object; errors are `{"error": <text>, "code": <UPPER_SNAKE>}`; an unknown tool returns code `UNKNOWN_TOOL`.
- Canonical JSON for every hash: `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")`, hashed with SHA-256, lowercase hex.
- Every analysis and evidence result carries `"provenance": "tool-reported"` and `"verification_scope": "consistency only; not authentication and not method validation"` where it verifies.
- Statistics limits: payload 1,048,576 bytes, 5,000 data rows, 64 columns, 5,000 p-values; NaN and infinity are rejected; units, experimental-unit column and missing-value policy (`exclude_and_report` or `reject`) are required arguments; no p-values, confidence intervals or causal wording are produced.
- Literature: hosts `eutils.ncbi.nlm.nih.gov`, `www.ebi.ac.uk`, `api.crossref.org` only, HTTPS only, no caller URLs, redirects to any other host or scheme refused, 10-second timeout, response cap 5,242,880 bytes, at most 100 records per call, no retries, 429 returns code `RATE_LIMITED` with `retry_after` when the server sends it, User-Agent `sophon-science-literature/1.0 (+https://sophon.buildersoft.io)`.
- Unknown retraction status, licence or database release stay `"unknown"`; "not flagged" is never written as "not retracted".
- Agents: no clinical, dosing or wet-lab instructions; evidence never stored in memory; no notifications; no compute jobs; no claim that a hash authenticates execution.
- Existing packages: no byte of any development or video package changes.

## Out of scope
M2-M5 (biology databases, managed compute, viewers, monitoring), OpenAlex, NCBI or OpenAlex keys, scientific model endpoints, persistent kernels, canvas renderers beyond what exists, live agent evaluation runs, publishing to the Marketplace, `build/Publish-MarketplacePackages.ps1`.

## Verification
- `python tests/skills/run_all.py` → exit 0, last line "<N>/<N> test files passed"
- `pwsh -NoProfile -File build/Build-MarketplacePackages.ps1 -ValidateOnly` → exit 0
- `pwsh -NoProfile -File tests/build/Test-SkillLint.ps1` → exit 0
- `pwsh -NoProfile -File build/Compose-AgentSouls.ps1 -Check` → exit 0
- `pwsh -NoProfile -File build/Test-AgentSources.ps1 -Release` → exit 0
- `pwsh -NoProfile -File tests/agents/Test-AgentPackages.ps1 -SourceOnly` → exit 0 (prints "CLI CHECKS NOT RUN (-SourceOnly)")
- `pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -ValidateOnly -Release` → exit 0
- `pwsh -NoProfile -File build/Build-AgentPackages.ps1 -ValidateOnly` → exit 0 with Sophon CLI 2.2.x on PATH; otherwise reported as not verified
- End to end: `tests/skills/test_science_evidence.py` builds a bundle from a real `scistat.mean_difference` record and recorded literature fixtures, verifies it clean, then fails it on a tampered output, a changed claimed number and a retracted supporting source.
- Regression: `git diff --name-only 0103b15c HEAD -- agents build/agent-src/family.psd1 build/agent-src/souls build/agent-src/fragments build/agent-src/readmes build/agent-src/families/video` lists only files under `agents/science-lead/`, `agents/literature-researcher/`, `agents/scientific-analyst/`, `agents/scientific-reviewer/`.

## Review focus
- Egress: a redirect, an encoded query or a DOI containing `/`, `?`, `#` or `@` must not reach a host outside the three (Task 3).
- Hash agreement: a record produced by `science-statistics` must verify unchanged in `science-evidence` (Task 2).
- Benjamini-Hochberg ties, monotonicity and input order (Task 1).
- Agent text that implies authenticated provenance, validated methods or clinical use (Task 5).
- The Docker path: a science entrypoint that imports anything outside the stdlib, or reads files beside itself (Task 4).

## Orchestration
- Consent: Team per task (2026-11-26) · Estimate: 21 agents, about 11 waves, about 104 cards (9 extra), ≈8× Solo tokens
- Companions: developer=developer, code-reviewer=code-reviewer, agent-engineer=agent-engineer

| Wave | Phase | Agents | Access | Briefs | Gate | Status |
|---|---|---|---|---|---|---|
| 0 | Understand + Design | 3 researchers, 2 architects | read-only | research and compare briefs | design note approved | done |
| 1-8 | Implement, one task per wave | implementer (developer; agent-engineer for Task 5) + code-reviewer | write / read-only | Task N heading, CHANGE working tree | APPROVE with SPEC: MET, then lead verify-and-commit | pending |
| 9 | Final review | 1 code-reviewer, LENS cross-task (interfaces, Global constraints, Review focus including Task 3 egress) | read-only | branch diff file | findings at THRESHOLD 80 | pending |
| 10 | Refute | 3 code-reviewers | read-only | Critical and Important findings | 2 of 3 CONFIRMED | pending |
| 11 | Critic | 1 code-reviewer, MODE completeness | read-only | request, goal, verification, commits | COMPLETE | pending |

## Tasks
### Task 1: Add the science-statistics skill
- [x] Done
Files: `skills/science-statistics/manifest.json` (create), `skills/science-statistics/main.py` (create), `skills/science-statistics/README.md` (create), `skills/science-statistics/LICENSE` (create), `tests/skills/test_science_statistics.py` (create), `docs/plans/2026-11-26-sophon-science-design.md` (add), `docs/plans/2026-11-26-sophon-science-m1.md` (modify)
Depends on: none
Covers: none
Interfaces: produces tools `scistat.describe {csv, value_column, group_column, unit_column, units, missing_policy}`, `scistat.mean_difference {csv, value_column, group_column, unit_column, units, group_a, group_b, missing_policy}`, `scistat.bh_adjust {p_values: number[], labels?: string[], alpha?: number = 0.05}`, `scistat.replay {record}`; each success returns `{"result": …, "record": {"schema": "sophon.science.analysis/1", "tool", "tool_version": "1.0.0", "method", "parameters", "input", "input_sha256", "output", "output_sha256", "python_version", "provenance": "tool-reported"}}`; missing tokens are the empty string, `NA` and `NaN`-as-missing is not accepted (a literal `nan` value is rejected as `INVALID_VALUE`).
- [x] Red: write `tests/skills/test_science_statistics.py` with hand-worked oracles on the CSV `unit,group,value` rows a1/A/1, a2/A/2, a3/A/3, a4/A/4, b1/B/2, b2/B/4, b3/B/6, b4/B/NA: `describe` gives A n=4, missing 0, mean 2.5, sample SD √(5/3), median 2.5; B n=3, missing 1, mean 4, SD 2, median 4; `mean_difference` (B − A) gives difference 1.5, Welch SE √(7/4), Welch df 1323/409, all within 1e-9 relative, and no `p_value` key; `bh_adjust` on [0.01, 0.04, 0.03, 0.005] gives [0.02, 0.04, 0.04, 0.02] in input order with all rejected at 0.05; refusals `INVALID_VALUE` (nan, inf), `MISSING_VALUES` (policy `reject` with NA), `LIMIT_EXCEEDED` (5,001 rows; 65 columns; 1,048,577 bytes), `MISSING_COLUMN`, `INSUFFICIENT_N` (a group with fewer than 2 values), `INVALID_P_VALUE` (−0.1, 1.1); warning `REPEATED_EXPERIMENTAL_UNIT` with `effective_units` when a unit id repeats; `replay` returns `REPLAY_MATCH` on an untouched record and `REPLAY_MISMATCH` after one output value changes; `UNKNOWN_TOOL`; the entrypoint has no non-stdlib import line (the `pip_names` rule of `run_all_container.py:57-68`). Run it alone and confirm it fails because the skill is missing.
- [x] Green: write `manifest.json` (category `data`, tags science/statistics/reproducibility, every tool `riskLevel` `none`, `sandbox` network false, timeoutSeconds 30, maxMemoryMb 256, `requirements` []), `main.py` and `LICENSE`; `README.md` lists the tools, limits, the "no p-values, no causal claims, tool-reported provenance" statement and that results are not validated for clinical use.
Run: `python tests/skills/test_science_statistics.py && pwsh -NoProfile -File build/Build-MarketplacePackages.ps1 -ValidateOnly`
Expected: exit 0; the test prints no `FAIL` line; the validator reports no error for `science-statistics`
Commit: feat(science-statistics): add bounded descriptive and replay tools

### Task 2: Add the science-evidence skill
- [x] Done
Files: `skills/science-evidence/manifest.json` (create), `skills/science-evidence/main.py` (create), `skills/science-evidence/README.md` (create), `skills/science-evidence/LICENSE` (create), `tests/skills/test_science_evidence.py` (create), `docs/plans/2026-11-26-sophon-science-m1.md` (modify)
Depends on: Task 1
Covers: none
Interfaces: uses the Task 1 `record` shape; produces `scievidence.canonical_hash {value}` → `{sha256, bytes}`, `scievidence.validate_bundle {bundle}` → `{valid, findings[]}` (schema only), `scievidence.verify_bundle {bundle}` → `{consistent, findings[], verification_scope}`; bundle schema `sophon.science.evidence/1` = `{schema, bundle_id, created_at, question, sources[{id, provider, identifiers{pmid?, pmcid?, doi?}, title, retrieved_at, response_sha256, publication_kind, retraction_status, license}], analyses[<Task 1 record> + id], claims[{id, text, kind: literature|numerical|interpretation, status: supported|unsupported|contested|unverified, supports[{source_id, quote, locator}], numbers[{value, analysis_id, path}]}], reviews[{id, reviewer, findings[]}], limitations[string]}`; `path` is a JSON Pointer into the analysis `output`; each finding is `{code, severity: error|warning, where, message}`.
- [x] Red: write `tests/skills/test_science_evidence.py`: a bundle built from a real `scistat.mean_difference` record (run through `run_tool`) verifies with zero errors; planted bundles give `DANGLING_REFERENCE`, `DUPLICATE_ID`, `OUTPUT_HASH_MISMATCH` (one output value changed), `NUMBER_MISMATCH` (claimed 1.6 against 1.5), `NUMERICAL_CLAIM_WITHOUT_ANALYSIS`, `MISSING_QUOTE` (a literature claim marked supported with no quote), `RETRACTED_SUPPORT` (a supported claim whose source is `retracted`), `MISSING_LIMITATIONS`, `LIMIT_EXCEEDED` (bundle over 1,048,576 bytes), `SCHEMA_INVALID` (unknown `kind`); `canonical_hash` of `{"b":1,"a":"é"}` equals SHA-256 of the UTF-8 bytes `{"a":"é","b":1}`; `verification_scope` is present on every verify result. Run it alone and confirm it fails because the skill is missing.
- [x] Green: write the skill (category `data`, every tool `riskLevel` `none`, network false, 30 s, 256 MB) and its README, stating that verification checks consistency only.
Run: `python tests/skills/test_science_evidence.py && python tests/skills/test_science_statistics.py && pwsh -NoProfile -File build/Build-MarketplacePackages.ps1 -ValidateOnly`
Expected: exit 0; no `FAIL` line in either test
Commit: feat(science-evidence): add evidence bundle validation and verification

### Task 3: Add the science-literature skill
- [ ] Done
Files: `skills/science-literature/manifest.json` (create), `skills/science-literature/main.py` (create), `skills/science-literature/README.md` (create), `skills/science-literature/LICENSE` (create), `tests/skills/test_science_literature.py` (create), `docs/plans/2026-11-26-sophon-science-m1.md` (modify)
Depends on: Task 2
Covers: none
Interfaces: produces `scilit.pubmed_search {query, limit?=20, min_date?, max_date?}` (E-utilities esearch then esummary, JSON), `scilit.pubmed_abstracts {pmids: string[]}` (efetch, XML), `scilit.europepmc_search {query, limit?=20, cursor?="*"}`, `scilit.crossref_work {doi}`; each record `{provider, pmid, pmcid, doi, title, journal, year, publication_types[], publication_kind: journal_article|preprint|unknown, retraction_status: retracted|not_flagged|unknown, url}`; each result `{records[], next_cursor?, retrieval: {provider, request_url, retrieved_at, response_sha256}}` — the `sources[]` fields of the Task 2 bundle.
- [ ] Before writing code, read the E-utilities reference (https://www.ncbi.nlm.nih.gov/books/NBK25499/) and the Europe PMC REST reference (https://europepmc.org/RestfulWebService) and record the parameter names used (`db`, `term`, `retmax`, `retmode`, `id`, `mindate`, `maxdate`, `datetype`; `query`, `format`, `pageSize`, `cursorMark`, `resultType`) as a Progress line; a name that differs from this list, or a page that cannot be read, stops the task as BLOCKED.
- [ ] Red: write `tests/skills/test_science_literature.py` with mockhttp: exact request URLs and percent-encoding, the User-Agent, one request per documented step and no extra request; record shaping for each provider; a Europe PMC record with source `PPR` gives `preprint`; a publication-type list containing "Retracted Publication" gives `retracted`, an empty one `not_flagged`, a missing one `unknown`; `RATE_LIMITED` with `retry_after` "2" from a 429; `NOT_FOUND` from a Crossref 404; `RESPONSE_TOO_LARGE` above 5,242,880 bytes; `INVALID_ARGUMENT` with no HTTP request for limit 101, a PMID `12a`, a DOI `10.1/../x?y`, 101 PMIDs and an empty query; `UNSAFE_XML` for a body containing `<!ENTITY`; the redirect handler refuses `http://` and a host outside the three (tested on the handler directly, since mockhttp replaces the opener); `retrieval.response_sha256` equals SHA-256 of the raw body. Run it alone and confirm it fails because the skill is missing.
- [ ] Green: write the skill (category `data`, every tool `riskLevel` `low`, `sandbox` network true, timeoutSeconds 30, maxMemoryMb 256, `permissions.network` the three bare hostnames) and its README with the rate limits, the Europe PMC bulk-download restriction and "citation resolution is not claim support".
Run: `python tests/skills/test_science_literature.py && pwsh -NoProfile -File build/Build-MarketplacePackages.ps1 -ValidateOnly && pwsh -NoProfile -File tests/build/Test-SkillLint.ps1`
Expected: exit 0; no `FAIL` line; no validator or lint error
Commit: feat(science-literature): add keyless PubMed, Europe PMC and Crossref lookups

### Task 4: Add the science skills to the container parity smoke
- [ ] Done
Files: `tests/skills/run_all_container.py` (modify), `tests/README.md` (modify), `docs/plans/2026-11-26-sophon-science-m1.md` (modify)
Depends on: Task 3
Covers: none
Interfaces: none
- [ ] Red: add a block that runs each science skill from `/workspace` with an unknown tool (code `UNKNOWN_TOOL`), runs `scistat.describe` on the Task 1 rows and `scievidence.canonical_hash` on one value, and asserts `pip_names(<skill>)` is empty; run the smoke before the skills' Docker path is checked and record the result.
- [ ] Add one row per skill to the `tests/README.md` container paragraph.
Run: `docker image inspect python:3.13-alpine >nul && docker run --rm --memory=256m -v "%CD%:/repo:ro" python:3.13-alpine python /repo/tests/skills/run_all_container.py && python tests/skills/run_all.py`
Expected: exit 0; the container prints "python 3.13" and "<M>/<M> passed"; `run_all.py` ends "<N>/<N> test files passed". Docker or the image missing: Progress line BLOCKED with the output; pulling the image is asked first.
Commit: test(skills): cover the science skills in the container smoke

### Task 5: Add the science agent family
- [ ] Done
Files: `build/agent-src/families.psd1` (modify), `build/agent-src/families/science/family.psd1` (create), `build/agent-src/families/science/souls/science-lead.md` (create), `build/agent-src/families/science/souls/literature-researcher.md` (create), `build/agent-src/families/science/souls/scientific-analyst.md` (create), `build/agent-src/families/science/souls/scientific-reviewer.md` (create), `build/agent-src/families/science/fragments/soul/01-science-ground-rules.md` (create), `…/02-science-evidence.md` (create), `…/03-science-data.md` (create), `…/04-science-delegated.md` (create), `…/05-science-reporting.md` (create), `agents/science-lead/{manifest.json,SOUL.md,TOOLS.md,README.md,LICENSE}` (create), `agents/literature-researcher/{…}` (create), `agents/scientific-analyst/{…}` (create), `agents/scientific-reviewer/{…}` (create), `docs/plans/2026-11-26-sophon-science-m1.md` (modify)
Depends on: Task 3
Covers: none
Interfaces: `SkillPolicy.Skills` = science-evidence, science-literature, science-statistics (MinVersion 1.0.0); per agent `Skills`: lead all three; literature-researcher literature + evidence; scientific-analyst statistics + evidence; scientific-reviewer all three; lead `SubAgents = @{ enabled = $true; maxDepth = 1 }`, the others disabled; each `whenToUse` ends "Family role: <id>."; `SoulCap` lead 24,576, others 16,384; `RoleCap` lead 8,192, others 4,096; `Credits = @{}`; no `Method` key and no excuse table.
- [ ] direct (decision 2026-11-26: agent text is checked statically; live runs gate publishing). Write the family file and the registry entry; the fragments: ground rules (scope, non-clinical boundary, assumptions stated before calculation), evidence (the bundle fields, tool-reported provenance, citation resolution is not claim support, preprint and retraction labels), data (public or synthetic data, no secrets or patient data, no evidence in memory, approval before any network lookup batch), delegated contract (the brief keys and the STATUS block), reporting (claim table, limitations, what was not verified).
- [ ] Role texts: the lead plans the question with the user through info.request, runs at most two literature tracks then one review through agent.delegate, assembles and verifies the bundle; the literature researcher searches, screens and quotes; the analyst refuses to compute until units, experimental unit and missing-value policy are stated; the reviewer reads the bundle, runs `scievidence.verify_bundle` and `scistat.replay`, and reports findings without judging method suitability as settled.
- [ ] Hand-write each `manifest.json` (agent schema 1, version 1.0.0, MIT, category `ai`, tags including `science`, `requires.skills` sorted, `requires.tools` the sorted built-in pins, `sophon.minVersion` 2.2.0), `TOOLS.md` (≤2,048 bytes, skill tools pinned only through SkillPolicy), `README.md` (≤12 KiB, ends "Licensed under the MIT License; see LICENSE.") and `LICENSE` (copy of the root `LICENSE`); compose the SOULs.
Run: `pwsh -NoProfile -File build/Compose-AgentSouls.ps1 && pwsh -NoProfile -File build/Compose-AgentSouls.ps1 -Check && pwsh -NoProfile -File build/Test-AgentSources.ps1 -Family science`
Expected: exit 0; `-Check` reports no drift; `Test-AgentSources.ps1` reports 0 errors for family science
Commit: feat(agents): add the science family with four agents

### Task 6: Add science anchors, fixture and written scenarios
- [ ] Done
Files: `tests/agents/fixtures/anchors/science.psd1` (create), `tests/agents/evals/fixtures/repo-science/fixture.psd1` (create), `tests/agents/evals/fixtures/repo-science/files/data/assay.csv` (create), `tests/agents/evals/fixtures/repo-science/files/evidence/bundle-planted.json` (create), `tests/agents/evals/fixtures/repo-science/files/README.md` (create), `tests/agents/evals/acceptance.psd1` (modify), `docs/plans/2026-11-26-sophon-science-m1.md` (modify)
Depends on: Task 5
Covers: none
Interfaces: none
- [ ] Anchors (each must be in the composed SOULs): "tool-reported", "not authentication", "not for clinical", "STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT" (all four), "experimental unit" (lead, analyst, reviewer).
- [ ] Fixture: a synthetic 12-row assay table with a repeated unit id and one NA; a bundle whose claim says 1.6 where its analysis says 1.5.
- [ ] Four acceptance rows with the next free `ACC-` numbers, no `Pending` key: the lead asks before computing (`Question` or `ChatQuestion`, `NoWrite = '**'` on the first turn); the analyst names the repeated experimental unit before any number (`Says 'experimental unit'`); the literature researcher returns identifiers (`Says 'PMID|DOI'`, no `fs.write`); the reviewer reports the 1.6 against 1.5 mismatch (`Says '1\.6'`, `NoWrite = '**'`).
Run: `pwsh -NoProfile -File build/Test-AgentSources.ps1 -Family science -Release && pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -ValidateOnly -Release`
Expected: exit 0; no `ANCHOR-MISSING`; the lint prints the new acceptance count and 0 errors
Commit: test(agents): add science anchors and acceptance scenarios

### Task 7: Update counts and documentation
- [ ] Done
Files: `README.md` (modify), `CLAUDE.md` (modify), `docs/AGENTS.md` (modify), `docs/PUBLISHING.md` (modify), `tests/README.md` (modify), `CONTRIBUTING.md` (modify only if it states a package count), `tests/agents/Test-AgentPackages.ps1` (modify only if it hard-codes 22), `docs/plans/2026-11-26-sophon-science-m1.md` (modify)
Depends on: Task 6
Covers: none
Interfaces: none
- [ ] Search the DOC-COUNT documents and `tests/agents/Test-AgentPackages.ps1` for `22`, `twenty-two` and `three families`/`two families`; change each stated total to twenty-six packages in three families, add a README "Science agents" section and a "Science" skills table, and a `docs/AGENTS.md` section 14 paragraph: the family, its install order (skills approved before agents), the delegation allow list for `science-lead`, and "not published until the live evaluation passes".
Run: `pwsh -NoProfile -File build/Test-AgentSources.ps1 -Release && pwsh -NoProfile -File tests/agents/Test-AgentPackages.ps1 -SourceOnly`
Expected: exit 0 for both; no `DOC-COUNT` finding
Commit: docs: describe the science family and its skills

### Task 8: Verify the milestone end to end
- [ ] Done
Files: `docs/plans/2026-11-26-sophon-science-m1.md` (modify)
Depends on: Task 7
Covers: none
Interfaces: none
- [ ] Re-read every changed file against the Request, the Global constraints and the Review focus; fix with a failing check first; add `Parked:` lines for minor points.
- [ ] Run the whole Verification list and the regression `git diff --name-only` command.
Run: `python tests/skills/run_all.py && pwsh -NoProfile -File build/Build-MarketplacePackages.ps1 -ValidateOnly && pwsh -NoProfile -File tests/build/Test-SkillLint.ps1 && pwsh -NoProfile -File build/Compose-AgentSouls.ps1 -Check && pwsh -NoProfile -File build/Test-AgentSources.ps1 -Release && pwsh -NoProfile -File tests/agents/Test-AgentPackages.ps1 -SourceOnly && pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -ValidateOnly -Release && git --no-pager diff --name-only 0103b15c HEAD -- agents build/agent-src/family.psd1 build/agent-src/souls build/agent-src/fragments build/agent-src/readmes build/agent-src/families/video`
Expected: exit 0 for every check; the final listing contains only paths under the four science agent folders; `Build-AgentPackages.ps1 -ValidateOnly` run separately when the Sophon CLI is present, otherwise reported as not verified
Commit: chore(science): verify milestone one

## Risks
- `pwsh` (PowerShell 7), Docker or Sophon CLI 2.2.x may be missing on this machine; each missing tool makes its check "not verified" and is reported, never skipped silently.
- Family tooling may require keys the video family did not exercise for a delegating non-development lead (Controller rules, worker fragments); a lint failure there becomes a Ruling or a question, not a weakened check.
- Europe PMC and E-utilities parameter names are taken from documentation read in Task 3; a difference stops that task.
- SOUL budgets: the caps above are first estimates; a cap raise stays within the 65,536-byte platform limit and keeps 5% headroom.
- Statistics written by hand in stdlib can be wrong in edge cases; the oracles are hand-worked, and Welch df and BH ties carry explicit tests.
- Agent behaviour is unverified until the live evaluation gate; the README and the plan say so.

## Progress
- 2026-11-26 Ruling: Task 1 implemented by the lead, reviewed by code-reviewer — the developer child returned no output (it spent its 8,000-token output cap on reasoning) and the paired reviewer found no files; doing the task inline keeps the agent estimate — cost if wrong: none to the code; 2 agents spent without result.
- 2026-11-26 Ruling: `scistat.replay` returns `{"result": …}` without its own record — a replay of a replay has no use — cost if wrong: one extra field to add later.
- 2026-11-26 Task 1: red — `python tests/skills/test_science_statistics.py` → FileNotFoundError for skills/science-statistics/main.py (the skill did not exist).
- 2026-11-26 Review: Task 1 code-reviewer APPROVE, SPEC: MET; 2 Minor findings (test gaps for non-ASCII hashing, exact limits and excluded_rows; the `reject` wording) fixed; a 10**400 p-value was red ("FAIL integer too large for a float") and then fixed.
- 2026-11-26 Task 1: repair 1/3 — the new exact-limit test failed ("field larger than field limit (131072)") → `csv.field_size_limit` set to the 1 MiB payload cap.
- 2026-11-26 Parked: T1-P1 Minor skills/science-statistics/main.py:117 — a row whose cells are all empty is skipped without being counted in excluded_rows.
- 2026-11-26 Parked: T1-P2 Minor skills/science-statistics/main.py:243 — welch_df is null without a warning when both groups have zero variance.
- 2026-11-26 Task 1: complete — `python tests/skills/test_science_statistics.py && pwsh -NoProfile -File build/Build-MarketplacePackages.ps1 -ValidateOnly` → "RESULT: PASS", validator exit 0
- 2026-11-26 Task 2: red — `python tests/skills/test_science_evidence.py` → FileNotFoundError for skills/science-evidence/main.py; green on the first full run.
- 2026-11-26 Ruling: Task 2 implemented by the lead and reviewed by code-reviewer, as in Task 1, to stay within the agent estimate — cost if wrong: none.
- 2026-11-26 Review: Task 2 code-reviewer APPROVE, SPEC: MET; 5 Minor findings (non-RFC 6901 indexes, non-list sections and 10**400 values crashing to INTERNAL_ERROR, test gaps, a README overclaim about hashes) — red first (15 FAIL lines), then fixed.
- 2026-11-26 Parked: T2-P1 Minor skills/science-evidence/manifest.json — `canonical_hash.value` is typed `object` (the schema subset allows one type); a runtime that enforces declared types would refuse arrays and scalars.
- 2026-11-26 Task 2: complete — `python tests/skills/test_science_evidence.py && python tests/skills/test_science_statistics.py && pwsh -NoProfile -File build/Build-MarketplacePackages.ps1 -ValidateOnly` → "RESULT: PASS" twice, validator exit 0
