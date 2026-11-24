# craft-reference: the Sophon entrypoint. Reference topics for the Buildersoft development agents.
#
# Sophon copies only this file, as script.py, into an empty workspace folder and puts two lines in
# front of it that define `params`. The topics are therefore embedded below, between the GENERATED
# DOCS markers, by build/craft-reference/generate.py; edit build/craft-reference/topics/ instead.
#
# Rules for this file (checked by tests/skills/test_craft_reference.py and the build lint):
# - standard library only (json and sys), no __future__ import (the preamble comes first);
# - comments only, never a docstring or any multi-line string;
# - every embedded document line starts with a quote, so no line can look like an import;
# - exactly one write to stdout: plain ASCII markdown for a topic, else one compact JSON object;
#   the exit code is always 0.
import json
import sys

# --- GENERATED DOCS BEGIN ---
# Written by build/craft-reference/generate.py from build/craft-reference/; never edit by hand.
# Every document line is one physical line that starts with a quote (the import scan reads every line).
SKILL_NAME = "craft-reference"
SKILL_VERSION = "1.0.0"
CORPUS_SHA256 = "4494fbb7a9bd683813143fe2b6703d33e25b3283d0182b3fe9ac6e6f771f3292"
INDEX = [
{"id": "design-sophon-default", "family": "design", "title": "Sophon default: full token tables", "bytes": 694, "summary": "Stub. Planned: dark and light role tables, status colours, type, space, radius, elevation, motion and the Banned list.", "sections": ["dark-roles", "light-roles", "status-colours", "type", "space-and-radius", "elevation", "motion-tokens", "other-themes", "fonts", "banned-list"], "origin": "original", "reviewed": "2026-11", "sources": "Sources: original text by Buildersoft LLC."},
{"id": "design-sophon-components", "family": "design", "title": "Sophon default: archetypes, layout and components", "bytes": 780, "summary": "Stub. Planned: page archetypes, density, layout measures, page states and component patterns.", "sections": ["page-archetypes", "density", "layout-measures", "shell-text-ladder", "page-states", "navigation", "tables", "forms", "empty-states", "command-surface", "product-wording"], "origin": "original", "reviewed": "2026-11", "sources": "Sources: original text by Buildersoft LLC."},
{"id": "design-schools", "family": "design", "title": "Design schools: six recipes in one anatomy", "bytes": 521, "summary": "Stub. Planned: an index and six direction recipes in one anatomy.", "sections": ["index", "swiss", "editorial", "modern-tool", "brutalist", "warm-humanist", "experimental"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: webDesignEngineer."},
{"id": "design-open-systems", "family": "design", "title": "Open design systems: five recipes", "bytes": 389, "summary": "Stub. Planned: five public design systems described as facts in one anatomy.", "sections": ["material-3", "carbon", "primer", "fluent-2", "radix"], "origin": "original", "reviewed": "2026-11", "sources": "Sources: original text by Buildersoft LLC."},
{"id": "design-directions-round", "family": "design", "title": "Direction round: option anatomy and examples", "bytes": 375, "summary": "Stub. Planned: the option anatomy as a template, a filled example, safer and bolder examples, a picker layout.", "sections": ["option-anatomy", "filled-example", "safer-and-bolder", "picker-layout"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: impeccable; interfaceDesign; emilSkills."},
{"id": "design-generated-defaults", "family": "design", "title": "Generated-looking defaults: the dated catalogue", "bytes": 505, "summary": "Stub. Planned: the dated catalogue of defaults that read as generated, with the repair for each.", "sections": ["type", "colour", "layout", "components", "imagery", "motion", "copy"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: anthropicSkills; impeccable; tasteSkill; webDesignEngineer; baselineUi; webInterfaceGuidelines."},
{"id": "design-critique-rubric", "family": "design", "title": "Critique rubric: heuristics, personas, severities", "bytes": 370, "summary": "Stub. Planned: ten heuristics with scoring anchors, persona sketches, severity anchors and a scoring sheet.", "sections": ["heuristics", "personas", "severity-anchors", "scoring-sheet"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: impeccable; nielsen."},
{"id": "design-refinement-verbs", "family": "design", "title": "Refinement verbs: bolder, quieter, distill, polish", "bytes": 409, "summary": "Stub. Planned: what each refinement verb changes and keeps, typical moves and the report table.", "sections": ["bolder", "quieter", "distill", "polish", "report-table"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: impeccable."},
{"id": "design-motion", "family": "design", "title": "Motion: purpose, durations, easing, reduced motion", "bytes": 378, "summary": "Stub. Planned: what motion is for, duration and easing by kind of change, enter and exit, reduced motion.", "sections": ["purpose", "duration-and-easing", "enter-and-exit", "reduced-motion"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: emilSkills; webInterfaceGuidelines."},
{"id": "design-md-template", "family": "design", "title": "DESIGN.md: skeleton, token block and dated rules", "bytes": 361, "summary": "Stub. Planned: the DESIGN.md skeleton, the token block, the dated-rule line and who owns each part.", "sections": ["skeleton", "token-block", "dated-rules", "ownership"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: designMd; interfaceDesign."},
{"id": "design-frontend-floors", "family": "design", "title": "Frontend floors: use what exists, the interaction floor", "bytes": 271, "summary": "Stub. Planned: the use-what-exists ladder with examples and the interaction floor as a checklist.", "sections": ["use-what-exists", "the-interaction-floor"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: webInterfaceGuidelines; baselineUi; anthropicSkills."},
{"id": "design-states-matrix", "family": "design", "title": "States: nine control states, five page states, break data", "bytes": 319, "summary": "Stub. Planned: nine control states by component kind, five page states and the break data set.", "sections": ["control-states", "page-states", "break-data"], "origin": "original", "reviewed": "2026-11", "sources": "Sources: original text by Buildersoft LLC."},
{"id": "design-variants", "family": "design", "title": "Variants: axes, comparison table, switcher", "bytes": 297, "summary": "Stub. Planned: variant axes with examples, the comparison table and a one-at-a-time switcher.", "sections": ["axes", "comparison-table", "switcher"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: emilSkills."},
{"id": "design-a11y-preferences", "family": "design", "title": "Preference checks: reduced motion, contrast, forced colours", "bytes": 333, "summary": "Stub. Planned: checks in code for reduced motion, contrast preference and forced colours.", "sections": ["reduced-motion", "contrast-preference", "forced-colours"], "origin": "original", "reviewed": "2026-11", "sources": "Sources: original text by Buildersoft LLC."},
{"id": "design-token-guards", "family": "design", "title": "Token guards: literal, parity and contrast tests", "bytes": 371, "summary": "Stub. Planned: literal, parity and contrast guard tests in outline, and the allow-list format.", "sections": ["literal-guard", "parity-guard", "contrast-guard", "allow-list"], "origin": "original", "reviewed": "2026-11", "sources": "Sources: original text by Buildersoft LLC."},
{"id": "design-evaluate", "family": "design", "title": "Measuring a page without sight: evaluate recipes", "bytes": 544, "summary": "Stub. Planned: evaluate snippets for overflow, targets, names, headings, focus, contrast and a style census.", "sections": ["overflow", "target-sizes", "unnamed-controls", "heading-order", "focus-styles", "contrast-pairs", "census"], "origin": "original", "reviewed": "2026-11", "sources": "Sources: original text by Buildersoft LLC."},
{"id": "product-brief", "family": "product", "title": "Product brief and PRODUCT.md skeletons", "bytes": 312, "summary": "Stub. Planned: the one-page brief skeleton, the PRODUCT.md skeleton and one filled example.", "sections": ["brief-skeleton", "product-md-skeleton", "filled-example"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: pmSkills."},
{"id": "product-prd", "family": "product", "title": "Lean PRD: sections, id forms, examples", "bytes": 352, "summary": "Stub. Planned: pRD sections, id forms, counter-measure examples and the form of an unknown.", "sections": ["sections", "id-forms", "counter-measures", "unknowns"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: bmadMethod; specKit."},
{"id": "product-discovery", "family": "product", "title": "Discovery question bank and premise forms", "bytes": 309, "summary": "Stub. Planned: a question bank by kind of product, premise forms and evidence labels.", "sections": ["question-bank", "premise-forms", "evidence-labels"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: gstack; specKit."},
{"id": "product-prioritisation", "family": "product", "title": "Prioritisation lenses and the pre-mortem sheet", "bytes": 355, "summary": "Stub. Planned: risk-first, RICE and opportunity lenses with worked rows, and the pre-mortem sheet.", "sections": ["risk-first", "rice", "opportunity", "pre-mortem"], "origin": "original", "reviewed": "2026-11", "sources": "Sources: original text by Buildersoft LLC."},
{"id": "product-tickets", "family": "product", "title": "Tickets: requirements and story files, status words, id chain", "bytes": 441, "summary": "Stub. Planned: requirements and story file fields, status words, the id chain and the out-of-scope file.", "sections": ["requirements-file", "story-file", "status-words", "id-chain", "out-of-scope"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: specKit; gsdCore; mattpocock."},
{"id": "product-slicing", "family": "product", "title": "Slicing patterns: thin paths and story splits", "bytes": 307, "summary": "Stub. Planned: thin end-to-end paths by kind of system, split patterns, signs of two stories.", "sections": ["thin-paths", "split-patterns", "two-stories"], "origin": "original", "reviewed": "2026-11", "sources": "Sources: original text by Buildersoft LLC."},
{"id": "product-acceptance", "family": "product", "title": "Acceptance: criteria patterns and the evidence table", "bytes": 263, "summary": "Stub. Planned: acceptance criteria patterns and a filled evidence table.", "sections": ["criteria-patterns", "evidence-table"], "origin": "original", "reviewed": "2026-11", "sources": "Sources: original text by Buildersoft LLC."},
{"id": "eng-review-checks", "family": "engineering", "title": "Review checks by defect class", "bytes": 177, "summary": "Stub. Planned: review checks by defect class, each a question with the sign to look for.", "sections": ["checks-by-class"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: anthropic."},
{"id": "eng-silent-failures", "family": "engineering", "title": "Silent failures: catches, defaults and fallbacks", "bytes": 198, "summary": "Stub. Planned: patterns that hide errors, by language idiom, with the visible alternative.", "sections": ["patterns-by-idiom"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: anthropic."},
{"id": "eng-test-quality", "family": "engineering", "title": "Test quality: tautology, vacuity, boundaries, examples", "bytes": 329, "summary": "Stub. Planned: tautology and vacuity examples, what to mock, boundary value tables.", "sections": ["tautology-and-vacuity", "what-to-mock", "boundary-values"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: mattpocock; superpowers."},
{"id": "eng-debugging-tactics", "family": "engineering", "title": "Debugging: reproduction loops and tactics by symptom", "bytes": 321, "summary": "Stub. Planned: rungs for building a reproduction, tactics by symptom, bisect recipes.", "sections": ["reproduction-rungs", "tactics-by-symptom", "bisect"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: superpowers; mattpocock."},
{"id": "eng-security-checklist", "family": "engineering", "title": "Security checklist by class, with the high-miss patterns", "bytes": 263, "summary": "Stub. Planned: the checklist by class with source, sink and defence, and the high-miss patterns.", "sections": ["checklist-by-class", "high-miss"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: anthropicSecurityReview; anthropicSecurityGuidance."},
{"id": "eng-privacy-sweep", "family": "engineering", "title": "Privacy sweep: personal data fields and flows", "bytes": 247, "summary": "Stub. Planned: purpose, flow, retention, deletion and access per personal-data field; leak points.", "sections": ["field-sheet", "leak-points"], "origin": "original", "reviewed": "2026-11", "sources": "Sources: original text by Buildersoft LLC."},
{"id": "eng-adr", "family": "engineering", "title": "Decision records: the gate, the short form, worked examples", "bytes": 325, "summary": "Stub. Planned: the three-part gate with examples, the short record form and two worked records.", "sections": ["three-part-gate", "short-form", "worked-records"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: mattpocock; anthropic."},
{"id": "eng-api-contract", "family": "engineering", "title": "API contract checklist", "bytes": 454, "summary": "Stub. Planned: operations, shapes, errors, paging, idempotent writes, auth, versioning, compatibility.", "sections": ["operations-and-shapes", "errors", "paging", "idempotent-writes", "auth", "versioning"], "origin": "original", "reviewed": "2026-11", "sources": "Sources: original text by Buildersoft LLC."},
{"id": "eng-e2e", "family": "engineering", "title": "Browser end-to-end tests: locators, waits, healing", "bytes": 360, "summary": "Stub. Planned: locator order, waits that hold, test data, failure causes and their repairs.", "sections": ["locators", "waits", "test-data", "failure-causes"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: playwright; anthropicSkills."},
{"id": "eng-mcp-contract", "family": "engineering", "title": "MCP tool contracts and the evaluation set", "bytes": 313, "summary": "Stub. Planned: the tool contract checklist, schema and error conventions, the evaluation set format.", "sections": ["tool-contract", "schemas-and-errors", "evaluation-set"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: anthropicSkills."},
{"id": "eng-perf-measure", "family": "engineering", "title": "Measuring performance: baselines, noise, reporting", "bytes": 356, "summary": "Stub. Planned: terms, the baseline method, the noise test and the reporting table.", "sections": ["terms", "baseline", "noise-test", "reporting"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: addyosmani."},
{"id": "eng-sources-versions", "family": "engineering", "title": "Sources and versions: where the version lives, by ecosystem", "bytes": 324, "summary": "Stub. Planned: where the version in use lives per ecosystem, source ranking, where changelogs are kept.", "sections": ["version-in-use", "source-ranking", "changelogs"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: addyosmani."},
{"id": "eng-docs-accuracy", "family": "engineering", "title": "Documentation accuracy: drift checks, glossary, change notes", "bytes": 382, "summary": "Stub. Planned: what to verify per quoted item, glossary rules, change-description forms, skeletons.", "sections": ["quoted-items", "glossary", "change-descriptions", "skeletons"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: mattpocock; humanizer."},
{"id": "release-ship", "family": "release", "title": "Shipping: version places, changelog forms, pre-ship checks", "bytes": 388, "summary": "Stub. Planned: where a version number lives, changelog forms, a SemVer decision table, pre-ship checks.", "sections": ["version-places", "changelog-forms", "semver-table", "pre-ship-checks"], "origin": "original", "reviewed": "2026-11", "sources": "Sources: original text by Buildersoft LLC."},
{"id": "release-deploy-rollback", "family": "release", "title": "Deploy and rollback: checklists and health signals", "bytes": 418, "summary": "Stub. Planned: before, during and after checklists, health signals, rollback options and their costs.", "sections": ["before", "during", "after", "health-signals", "rollback-options"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: gstack; compoundEngineering."},
{"id": "agent-pressure-tests", "family": "agent", "title": "Pressure tests: scenario format, pressures, run tables", "bytes": 382, "summary": "Stub. Planned: the scenario file format, pressure kinds with example wording, run tables, reading results.", "sections": ["scenario-format", "pressure-kinds", "run-tables", "reading-results"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: superpowers."},
{"id": "agent-instruction-style", "family": "agent", "title": "Instruction forms: which form fits which failure", "bytes": 327, "summary": "Stub. Planned: instruction forms mapped to observed failures, the excuse-table format, recipe examples.", "sections": ["instruction-forms", "excuse-table-format", "positive-recipes"], "origin": "adapted", "reviewed": "2026-11", "sources": "Sources: superpowers."},
{"id": "agent-package-facts", "family": "agent", "title": "Sophon package facts: files, limits, scanner families", "bytes": 378, "summary": "Stub. Planned: the seven package files, byte and manifest limits, the TOOLS.md grammar, scanner families.", "sections": ["package-files", "limits", "tools-md-grammar", "scanner-families"], "origin": "original", "reviewed": "2026-11", "sources": "Sources: original text by Buildersoft LLC."},
]
DOCS = {
"design-sophon-default": [
("", (
"# Sophon default: full token tables\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("dark-roles", (
"## Dark roles\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("light-roles", (
"## Light roles\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("status-colours", (
"## Status colours\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("type", (
"## Type\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("space-and-radius", (
"## Space and radius\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("elevation", (
"## Elevation\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("motion-tokens", (
"## Motion tokens\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("other-themes", (
"## Other themes\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("fonts", (
"## Fonts\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("banned-list", (
"## Banned list\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"design-sophon-components": [
("", (
"# Sophon default: archetypes, layout and components\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("page-archetypes", (
"## Page archetypes\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("density", (
"## Density\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("layout-measures", (
"## Layout measures\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("shell-text-ladder", (
"## Shell text ladder\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("page-states", (
"## Page states\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("navigation", (
"## Navigation\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("tables", (
"## Tables\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("forms", (
"## Forms\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("empty-states", (
"## Empty states\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("command-surface", (
"## Command surface\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("product-wording", (
"## Product wording\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"design-schools": [
("", (
"# Design schools: six recipes in one anatomy\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("index", (
"## Index\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("swiss", (
"## Swiss\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("editorial", (
"## Editorial\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("modern-tool", (
"## Modern tool\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("brutalist", (
"## Brutalist\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("warm-humanist", (
"## Warm humanist\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("experimental", (
"## Experimental\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"design-open-systems": [
("", (
"# Open design systems: five recipes\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("material-3", (
"## Material 3\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("carbon", (
"## Carbon\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("primer", (
"## Primer\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("fluent-2", (
"## Fluent 2\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("radix", (
"## Radix\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"design-directions-round": [
("", (
"# Direction round: option anatomy and examples\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("option-anatomy", (
"## Option anatomy\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("filled-example", (
"## Filled example\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("safer-and-bolder", (
"## Safer and bolder\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("picker-layout", (
"## Picker layout\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"design-generated-defaults": [
("", (
"# Generated-looking defaults: the dated catalogue\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("type", (
"## Type\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("colour", (
"## Colour\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("layout", (
"## Layout\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("components", (
"## Components\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("imagery", (
"## Imagery\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("motion", (
"## Motion\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("copy", (
"## Copy\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"design-critique-rubric": [
("", (
"# Critique rubric: heuristics, personas, severities\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("heuristics", (
"## Heuristics\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("personas", (
"## Personas\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("severity-anchors", (
"## Severity anchors\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("scoring-sheet", (
"## Scoring sheet\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"design-refinement-verbs": [
("", (
"# Refinement verbs: bolder, quieter, distill, polish\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("bolder", (
"## Bolder\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("quieter", (
"## Quieter\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("distill", (
"## Distill\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("polish", (
"## Polish\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("report-table", (
"## Report table\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"design-motion": [
("", (
"# Motion: purpose, durations, easing, reduced motion\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("purpose", (
"## Purpose\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("duration-and-easing", (
"## Duration and easing\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("enter-and-exit", (
"## Enter and exit\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("reduced-motion", (
"## Reduced motion\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"design-md-template": [
("", (
"# DESIGN.md: skeleton, token block and dated rules\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("skeleton", (
"## Skeleton\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("token-block", (
"## Token block\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("dated-rules", (
"## Dated rules\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("ownership", (
"## Ownership\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"design-frontend-floors": [
("", (
"# Frontend floors: use what exists, the interaction floor\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("use-what-exists", (
"## Use what exists\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("the-interaction-floor", (
"## The interaction floor\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"design-states-matrix": [
("", (
"# States: nine control states, five page states, break data\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("control-states", (
"## Control states\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("page-states", (
"## Page states\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("break-data", (
"## Break data\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"design-variants": [
("", (
"# Variants: axes, comparison table, switcher\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("axes", (
"## Axes\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("comparison-table", (
"## Comparison table\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("switcher", (
"## Switcher\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"design-a11y-preferences": [
("", (
"# Preference checks: reduced motion, contrast, forced colours\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("reduced-motion", (
"## Reduced motion\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("contrast-preference", (
"## Contrast preference\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("forced-colours", (
"## Forced colours\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"design-token-guards": [
("", (
"# Token guards: literal, parity and contrast tests\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("literal-guard", (
"## Literal guard\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("parity-guard", (
"## Parity guard\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("contrast-guard", (
"## Contrast guard\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("allow-list", (
"## Allow-list\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"design-evaluate": [
("", (
"# Measuring a page without sight: evaluate recipes\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("overflow", (
"## Overflow\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("target-sizes", (
"## Target sizes\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("unnamed-controls", (
"## Unnamed controls\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("heading-order", (
"## Heading order\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("focus-styles", (
"## Focus styles\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("contrast-pairs", (
"## Contrast pairs\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("census", (
"## Census\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"product-brief": [
("", (
"# Product brief and PRODUCT.md skeletons\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("brief-skeleton", (
"## Brief skeleton\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("product-md-skeleton", (
"## PRODUCT.md skeleton\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("filled-example", (
"## Filled example\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"product-prd": [
("", (
"# Lean PRD: sections, id forms, examples\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("sections", (
"## Sections\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("id-forms", (
"## Id forms\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("counter-measures", (
"## Counter-measures\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("unknowns", (
"## Unknowns\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"product-discovery": [
("", (
"# Discovery question bank and premise forms\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("question-bank", (
"## Question bank\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("premise-forms", (
"## Premise forms\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("evidence-labels", (
"## Evidence labels\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"product-prioritisation": [
("", (
"# Prioritisation lenses and the pre-mortem sheet\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("risk-first", (
"## Risk first\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("rice", (
"## RICE\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("opportunity", (
"## Opportunity\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("pre-mortem", (
"## Pre-mortem\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"product-tickets": [
("", (
"# Tickets: requirements and story files, status words, id chain\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("requirements-file", (
"## Requirements file\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("story-file", (
"## Story file\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("status-words", (
"## Status words\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("id-chain", (
"## Id chain\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("out-of-scope", (
"## Out of scope\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"product-slicing": [
("", (
"# Slicing patterns: thin paths and story splits\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("thin-paths", (
"## Thin paths\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("split-patterns", (
"## Split patterns\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("two-stories", (
"## Two stories\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"product-acceptance": [
("", (
"# Acceptance: criteria patterns and the evidence table\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("criteria-patterns", (
"## Criteria patterns\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("evidence-table", (
"## Evidence table\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"eng-review-checks": [
("", (
"# Review checks by defect class\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("checks-by-class", (
"## Checks by class\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"eng-silent-failures": [
("", (
"# Silent failures: catches, defaults and fallbacks\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("patterns-by-idiom", (
"## Patterns by idiom\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"eng-test-quality": [
("", (
"# Test quality: tautology, vacuity, boundaries, examples\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("tautology-and-vacuity", (
"## Tautology and vacuity\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("what-to-mock", (
"## What to mock\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("boundary-values", (
"## Boundary values\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"eng-debugging-tactics": [
("", (
"# Debugging: reproduction loops and tactics by symptom\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("reproduction-rungs", (
"## Reproduction rungs\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("tactics-by-symptom", (
"## Tactics by symptom\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("bisect", (
"## Bisect\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"eng-security-checklist": [
("", (
"# Security checklist by class, with the high-miss patterns\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("checklist-by-class", (
"## Checklist by class\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("high-miss", (
"## High miss\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"eng-privacy-sweep": [
("", (
"# Privacy sweep: personal data fields and flows\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("field-sheet", (
"## Field sheet\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("leak-points", (
"## Leak points\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"eng-adr": [
("", (
"# Decision records: the gate, the short form, worked examples\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("three-part-gate", (
"## Three-part gate\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("short-form", (
"## Short form\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("worked-records", (
"## Worked records\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"eng-api-contract": [
("", (
"# API contract checklist\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("operations-and-shapes", (
"## Operations and shapes\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("errors", (
"## Errors\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("paging", (
"## Paging\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("idempotent-writes", (
"## Idempotent writes\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("auth", (
"## Auth\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("versioning", (
"## Versioning\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"eng-e2e": [
("", (
"# Browser end-to-end tests: locators, waits, healing\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("locators", (
"## Locators\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("waits", (
"## Waits\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("test-data", (
"## Test data\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("failure-causes", (
"## Failure causes\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"eng-mcp-contract": [
("", (
"# MCP tool contracts and the evaluation set\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("tool-contract", (
"## Tool contract\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("schemas-and-errors", (
"## Schemas and errors\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("evaluation-set", (
"## Evaluation set\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"eng-perf-measure": [
("", (
"# Measuring performance: baselines, noise, reporting\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("terms", (
"## Terms\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("baseline", (
"## Baseline\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("noise-test", (
"## Noise test\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("reporting", (
"## Reporting\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"eng-sources-versions": [
("", (
"# Sources and versions: where the version lives, by ecosystem\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("version-in-use", (
"## Version in use\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("source-ranking", (
"## Source ranking\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("changelogs", (
"## Changelogs\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"eng-docs-accuracy": [
("", (
"# Documentation accuracy: drift checks, glossary, change notes\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("quoted-items", (
"## Quoted items\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("glossary", (
"## Glossary\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("change-descriptions", (
"## Change descriptions\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("skeletons", (
"## Skeletons\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"release-ship": [
("", (
"# Shipping: version places, changelog forms, pre-ship checks\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("version-places", (
"## Version places\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("changelog-forms", (
"## Changelog forms\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("semver-table", (
"## SemVer table\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("pre-ship-checks", (
"## Pre-ship checks\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"release-deploy-rollback": [
("", (
"# Deploy and rollback: checklists and health signals\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("before", (
"## Before\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("during", (
"## During\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("after", (
"## After\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("health-signals", (
"## Health signals\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("rollback-options", (
"## Rollback options\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"agent-pressure-tests": [
("", (
"# Pressure tests: scenario format, pressures, run tables\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("scenario-format", (
"## Scenario format\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("pressure-kinds", (
"## Pressure kinds\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("run-tables", (
"## Run tables\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("reading-results", (
"## Reading results\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"agent-instruction-style": [
("", (
"# Instruction forms: which form fits which failure\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("instruction-forms", (
"## Instruction forms\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("excuse-table-format", (
"## Excuse-table format\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("positive-recipes", (
"## Positive recipes\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
"agent-package-facts": [
("", (
"# Sophon package facts: files, limits, scanner families\n"
"\n"
"Stub: the full text of this topic arrives in milestone M7 of the agents 3.0 plan.\n"
"\n"
)),
("package-files", (
"## Package files\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("limits", (
"## Limits\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("tools-md-grammar", (
"## TOOLS.md grammar\n"
"\n"
"Planned section; its text arrives in M7.\n"
"\n"
)),
("scanner-families", (
"## Scanner families\n"
"\n"
"Planned section; its text arrives in M7.\n"
)),
],
}
# --- GENERATED DOCS END ---

FAMILIES = ["design", "product", "engineering", "release", "agent"]
TOOLS = ["craft.topics", "craft.read"]
LOWER = "abcdefghijklmnopqrstuvwxyz"
ID_CHARS = LOWER + "0123456789-"
TOOL_CHARS = LOWER + "0123456789._-"


def is_id(value, shortest, longest):
    # ^[a-z][a-z0-9-]{n,m}$ without the re module.
    if not isinstance(value, str) or not shortest + 1 <= len(value) <= longest + 1:
        return False
    if value[0] not in LOWER:
        return False
    return all(ch in ID_CHARS for ch in value)


def compact(doc):
    return json.dumps(doc, ensure_ascii=True, separators=(",", ":"))


def failure(code, sentence, **extra):
    doc = {"error": sentence, "code": code}
    doc.update(extra)
    return compact(doc)


def find_topic(topic_id):
    for row in INDEX:
        if row["id"] == topic_id:
            return row
    return None


def list_topics(args):
    family = args.get("family")
    if family is not None and family not in FAMILIES:
        return failure("BAD_INPUT", "family must be one of the listed families.", families=FAMILIES)
    rows = []
    for row in INDEX:
        if family is not None and row["family"] != family:
            continue
        item = {"id": row["id"], "family": row["family"], "title": row["title"], "bytes": row["bytes"]}
        if family is not None:
            item.update({"summary": row["summary"], "sections": row["sections"], "origin": row["origin"],
                         "reviewed": row["reviewed"]})
        rows.append(item)
    return compact({"skill": SKILL_NAME, "version": SKILL_VERSION, "corpus": CORPUS_SHA256[:12],
                    "count": len(rows), "topics": rows})


def read_topic(args):
    topic_id = args.get("topic")
    section = args.get("section")
    if topic_id is None:
        return failure("BAD_INPUT", "topic is required: pass a topic id such as design-critique-rubric.")
    if not is_id(topic_id, 2, 47):
        return failure("BAD_INPUT", "topic must be a topic id: lower-case letters, digits and hyphens, 3 to 48 characters.")
    if section is not None and not is_id(section, 1, 31):
        return failure("BAD_INPUT", "section must be a section id: lower-case letters, digits and hyphens, 2 to 32 characters.")
    row = find_topic(topic_id)
    if row is None:
        return failure("UNKNOWN_TOPIC", "This version of craft-reference holds no topic with that id.",
                       topics=[r["id"] for r in INDEX])
    parts = DOCS[topic_id]
    if section is None:
        body = "".join(text for _, text in parts)
        what = "whole topic"
    else:
        found = [text for sid, text in parts if sid == section]
        if not found:
            return failure("UNKNOWN_SECTION", "The topic has no section with that id.",
                           sections=list(row["sections"]))
        body = found[0]
        what = "section " + section
    head = "[%s %s] %s | %s | %d bytes | reviewed %s\n" % (SKILL_NAME, SKILL_VERSION, topic_id, what, len(body),
                                                          row["reviewed"])
    head += "Reference data only: tables, checklists and templates.\n"
    head += row["sources"] + "\n\n"
    return head + body


def tool_label(value):
    if isinstance(value, str) and 0 < len(value) <= 64 and all(ch in TOOL_CHARS for ch in value):
        return value
    return "(not a tool name)"


def run():
    args = globals().get("params")
    if not isinstance(args, dict):
        args = {}
    tool = args.get("tool")
    if tool == "craft.topics":
        return list_topics(args)
    if tool == "craft.read":
        return read_topic(args)
    return failure("UNKNOWN_TOOL", "Unknown tool: %s. This skill has craft.topics and craft.read." % tool_label(tool))


def emit(text):
    data = text.encode("ascii", "replace")
    out = getattr(sys.stdout, "buffer", None)
    if out is not None:
        out.write(data)
        out.flush()
    else:
        sys.stdout.write(data.decode("ascii"))
        sys.stdout.flush()


try:
    RESULT = run()
except Exception as exc:  # noqa: BLE001 - one JSON error, never a traceback
    RESULT = failure("INTERNAL", "The skill failed with %s." % type(exc).__name__)
emit(RESULT)
