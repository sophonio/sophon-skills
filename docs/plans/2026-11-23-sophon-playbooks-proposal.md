# Sophon proposal: playbooks, renders the model can see, worktrees for children

**Status:** drafted, not built · 2026-11-23 · addressed to the Sophon team · from the development agent family 3.0.0

This proposal asks Sophon for three platform features and five smaller ones. Nothing in the 3.0 agent
family depends on any of them: every 3.0.0 package works on Sophon 2.2.x as it is. The proposal comes
from the 3.0 design ([`2026-11-23-agents-v3-design.md`](2026-11-23-agents-v3-design.md), section
"Platform proposal (draft, not built)"), and owner decision 1 of that design keeps it a draft.

## Why

Three limits shaped the 3.0 design more than any other.

- **No instructions on demand.** Sophon cannot load instructions when a task needs them, so the whole
  method lives in every `SOUL.md`, and the size caps had to rise (the lead's cap went from 43,008 B to
  62,464 B, against a platform limit of 65,536 B). Every child pays for its whole SOUL, uncached.
- **The model never sees its own renders.** `browser.screenshot`, the screenshots of `browser.act` and
  `canvas.render` show the user an image, while the agent receives only a text stand-in. Design agents
  therefore measure the DOM and ask the user to be their eyes.
- **Children share the parent's workspace.** Two writers can run at once only on disjoint files, and a
  reviewer never reads a frozen snapshot of the change it reviews.

## 1. Playbooks in the agent package

- **Format.** An optional `playbooks/` folder in the package, format v1.1 and additive: up to 32
  markdown files of at most 32,768 B each, with the package total raised to 1,048,576 B. A package that
  carries playbooks states the Sophon version that introduced them in `sophon.minVersion`, because older
  versions refuse unknown entries.
- **Manifest.** `"playbooks": [{ "id", "title", "whenToUse", "audience" }]`. `whenToUse` is one line of
  at most 160 characters.
- **Audience.** `audience` is `root`, `child` or `both` (the default). A root session lists and can read
  only `root` and `both`; a delegated or graph-node session only `child` and `both`. Controller text can
  then never reach a worker, by construction instead of by a lint.
- **Index.** Sophon appends a name-only index (id and `whenToUse`) after the SOUL, inside the cached
  prefix, filtered by audience.
- **Tool.** A built-in `playbook.read {id, section}` with a read-only effect. It works in plan mode, in
  sub-agents and without a sandbox, and it raises no card.
- **Trust.** Playbooks are scanned at install and by the Marketplace exactly as `SOUL.md` is. The text
  is returned as agent instructions with the trust of the SOUL it shipped with. It is not wrapped as
  external content and does not taint the turn.
- **Cost.** Text is paid for only when it is read, and then stays in the conversation like any tool
  result.
- **Updates.** A playbook change is a content change like a SOUL change: it applies on a minor or patch
  update and pauses when the user edited that file.

## 2. Renders that reach the model

- **Today** only `desktop.activity` and `remote.control` return images to the model. `browser.screenshot`,
  the screenshots of `browser.act` and `canvas.render` return them to the user only.
- **Proposal.** A `forModel: true` argument on those three tools returns the image to a model that has
  vision. The image is scaled down (long edge 1,568 px), counted against a per-turn image budget, and
  marked as tainted like any page content. On a route without vision the model receives today's text
  stand-in.
- For the canvas, the returned image is a rendering of the frame the user sees.
- **Effect on the family.** Design agents could critique their own render. The rule in
  `22-design-checks` that the agent never describes a render would then apply only when no image came
  back. The user's eyes stay the final judge.

## 3. Worktree isolation for children

- **Today** a child works in the parent's workspace, and `code.git` has no worktree operation. The lead
  therefore runs writers side by side only on disjoint files, and a per-task reviewer reads a working
  tree that can still move.
- **Proposal.** An `isolation: "worktree"` option on an `agent.delegate` entry. Sophon creates a git
  worktree at the parent's HEAD under its data folder, optionally carrying the parent's uncommitted
  changes as a patch, and binds the child to it.
- The child's result carries the path of its diff and the name of its branch. The parent applies the
  change with one card, or drops it. Sophon removes the worktree when the parent's turn ends.
- An unbound session, or a workspace that is not a git repository, falls back to the shared workspace
  and says so in the result.
- **Effect on the family.** Parallel implementers on overlapping files, a reviewer that reads an
  immutable snapshot, and a discard that costs nothing. The 3.0 plan leaves worktrees out for exactly
  this missing support.

## 4. How the reference skill's topics would migrate

Today long reference material ships as the Marketplace skill `craft-reference` (tools `craft.topics`
and `craft.read`), which every development agent except Artifact Creator requires. With playbooks it
would move into the packages:

1. Topic files already pass the SOUL text lint and carry stable ids, so the composer copies each
   agent's topics (the registry's `usedBy` list) into `agents/<id>/playbooks/<topic-id>.md`. Ids and
   pointers in role text do not change.
2. Fragment `18-reference-topics` is rewritten once to name the playbook tool. The fallback sentence
   goes, because a playbook is always present.
3. `requires.skills` and the pin are removed in the same major version, since a `requires` change stops
   auto-update anyway. The development family then has no `SkillPolicy`.
4. Because playbooks are trusted, text that must stay inline today can leave the SOULs: the full excuse
   tables, per-mode procedures, and the lead's controller loop as `audience: root` playbooks. The caps
   can then come back down.
5. `craft-reference` stays published through that major, because other publishers' agents may use it.
   In its next major every topic id still answers, with one line saying that the topic moved into the
   agent packages; the skill is withdrawn one major later.

## 5. Smaller asks

- A manifest flag that lets a skill tool with no network and risk `none` classify as read-only, so
  that it works in plan mode and does not taint. Today skill tools are refused in plan mode.
- `recommends.skills`: a soft dependency that neither blocks Marketplace approval nor stops
  auto-update.
- Plan mode requested by the model and confirmed by the user.
- A question relay from a child to the root's question card. Today a sub-agent cannot ask the user.
- Session-start and pre-commit hooks, as a place for a verification gate.

## What the family does until then

- The method stays inline in each `SOUL.md`, sliced by role, under the tiered caps with at least 5%
  headroom.
- Design agents measure the DOM and ask the user what looks off; they never describe a render they
  cannot see.
- Only Lead Developer delegates. Its parallel implementers take disjoint files, and a reviewer reads a
  diff file or one working-tree diff.
- Every agent that names a reference topic also works when `craft-reference` is missing or refused.
