# Release Engineer

Takes a branch that is ready to merge to a released, deployed and watched version, and takes a release back when it goes wrong. Every step that leaves this machine is asked first, every time.

Part of the Buildersoft development family {{= FamilyVersion}}.

{{# roster}}

## When to use

- A read-only check: is this branch ready to release?
- Shipping: sync, full checks, version and changelog, the release commit and the pull request.
- A deploy checklist walked with you, then a bounded health watch.
- A dependency upgrade, one group at a time.
- A rollback, least destructive option first.

## Not for

- Building or fixing the change: `lead-developer`, `developer`.
- Finding why production broke: `debugger`.
- The verification gate before a merge: `qa-engineer`.
- Accepting work against requirements: `product-owner`.

## How it works

- Finds the project's own release rules first: project instructions, a release or contributing document, CI and release workflow files, package scripts, earlier tags and the changelog's format. The project's convention wins.
- Modes: check, ship, deploy, watch, upgrade and rollback.
- The outward gate: a push, a tag push, opening or merging a pull request, a publish, a deploy, a pipeline trigger, creating a release and commenting on an issue each get their own question that quotes the exact command and its target. No answer means the step does not run.
- ship opens with one "Ship" question that lists the steps and marks the outward ones. A failed check stops the ship with the failing line quoted. You confirm the version number, and it changes every place the version lives. One commit `chore(release): v<version>`, then the family's finish menu. A tag comes only after the merge and only when you ask.
- watch is a fixed number of checks inside one turn (default 5 rounds, 60 seconds apart, at most 15 minutes), reported HEALTHY, DEGRADED or NO_SIGNAL. It ends with "Nothing is watching now."
- upgrade groups security fixes first and each major version alone, reads the migration guide before a major, changes the manifest through the package manager and never loosens a test.
- After a rollback: "To find the cause: tell Debugger 'investigate <symptom>'."

## Tools and cards you'll see

| Tool | Approval card |
|---|---|
| fs.list, fs.find, fs.search, fs.read | none |
| web.scrape | none |
| code.git status, log and diff | none, or one for a range diff |
| fs.edit, fs.write (version, changelog, manifest files) | one each |
| os.execute (sync, checks, the commit, push, the watch loop) | one each |
| http.request (one health request after a deploy) | one |
| info.request | a question, not a card |

A ship costs the files it edits plus about five cards; each further outward step is one more. check raises none; watch raises one.

## After installing

- Effort: the default is fine.
- Start `sophon` in the project folder so the session is bound, then run `/trust` so the project's instructions load. A watch needs a bound session.
- Pick it with `/agent release-engineer`, or `--agent release-engineer` on the command line.
- Pushing and opening a pull request need the setup in `docs/AGENTS.md` section 9.

## Plan mode

The plan card carries the steps of a ship, deploy, watch or rollback; check works read-only.

## Limits

- Nothing runs in the background, so a watch lasts at most 15 minutes inside one turn, and only in a bound session.
- It reads CI results only through commands the project names.
- As a sub-agent it only prepares and reports: nothing leaves the machine and it does not commit.

## What it never does

- Force-pushes, deletes a tag or a release, or merges a pull request unasked.
- Bumps a version you have not confirmed, or edits a lockfile by hand.
- Loosens a test to let an upgrade through.
- Leaves anything running.
- Runs an outward step on an unanswered question.

## Credits and license

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0). Licensed under the MIT License; see LICENSE.
