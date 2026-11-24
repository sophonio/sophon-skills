# Product Owner

Requirements, stories and acceptance: an agreed goal turned into requirements with permanent ids and small stories others can build, and built work judged against them from evidence.

Part of the Buildersoft development family {{= FamilyVersion}}.

{{# roster}}

## When to use

- A requirements file from a brief, a PRD, an issue or a sentence.
- Thin end-to-end stories with one runnable check each.
- A readiness check on a story before it is built.
- An acceptance verdict on built work.
- Replanning what is not built yet, or triage of an incoming report.

## Not for

- Deciding whether to build it: `product-manager`.
- How to build it: `software-architect`.
- Building: `lead-developer`.
- Running the test suite or the verification gate: `qa-engineer`.

## How it works

- Reads `PRODUCT.md`, the product folder, the source you named and the code the goal touches before it writes, so that "Now" in a story is a fact.
- Modes: spec, slice, refine (root only), validate, accept, replan and triage.
- The ticket tree is plain markdown in `docs/product/<slug>/` unless your project instructions name another folder: `requirements.md` (Intent, Requirements `R<n>`, Boundaries, Stories, Notes) and one `NN-<story>.md` per story (Behaviour, Given / When / Then criteria, one Check, Out, Acceptance record). `docs/product/out-of-scope.md` keeps one dated line per declined request.
- spec asks at most five clarifying questions, one per message, and writes each answer down at once.
- slice makes story 01 the thinnest path that runs end to end, and story 02 the one you are least sure about. "Simplified for now" becomes a second story; the first is never shrunk.
- validate is read-only and answers READY or NOT_READY per story.
- accept works backward from the Intent and the requirements: for each R id, what must be true, what exists and what reaches it, with path:line. Ticked boxes and reports are claims. The verdict is ACCEPTED, ACCEPTED_WITH_OPEN_ITEMS or REJECTED.
- Every draft is shown first, then one question ("Spec", "Stories" or "Accept"): Save, Change something or Stop.
- Hands off: "To build: tell Lead Developer 'execute <story path>'." or "To design first: tell Software Architect 'blueprint <requirements path>'."

## Tools and cards you'll see

| Tool | Approval card |
|---|---|
| fs.list, fs.find, fs.search, fs.read | none |
| web.scrape | none |
| code.git status and log | none |
| fs.write or one edit (a file you approved) | one |
| os.execute (a story's Check, accept at root only) | one |
| info.request | a question, not a card |

One card per saved file; in accept at root, one per Check run and one per recorded verdict; none for validate.

## After installing

- Effort: set it to high with `sophon agents models product-owner --effort high`.
- Start `sophon` in the project folder so the session is bound, then run `/trust` so the project's instructions load.
- Pick it with `/agent product-owner`, or `--agent product-owner` on the command line.

## Plan mode

It drafts as usual but cannot save; the draft stays in the chat until you leave plan mode and say "save".

## Limits

- An acceptance verdict needs a runnable Check.
- As a sub-agent it runs nothing and writes nothing: it judges from the command evidence Lead Developer puts in the brief.
- The ticket tree is hand-kept markdown, with no tracker sync.

## What it never does

- Writes code, tests, configuration or plan files.
- Commits: Lead Developer commits the story and requirements files with the first task of the plan that builds them.
- Invents a requirement, an owner or an estimate, or changes an approved Intent unasked.
- Runs anything except a story's Check at root.
- Accepts from ticked boxes or reports.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); blader/humanizer (MIT, © 2025 Siqi Chen); bmad-code-org/BMAD-METHOD (MIT, © 2025 BMad Code, LLC); github/spec-kit (MIT, © GitHub, Inc.); mattpocock/skills (MIT, © 2026 Matt Pocock); and open-gsd/gsd-core (MIT, © 2026 Open GSD).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0). Licensed under the MIT License; see LICENSE.
