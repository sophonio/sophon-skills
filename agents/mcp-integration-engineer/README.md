# MCP Integration Engineer

Designs, builds and evaluates Model Context Protocol servers that let a model use a service well.

Part of the Buildersoft development family 3.0.0.

| Agent | Role | Delegates | Changes files | Commits |
|---|---|---|---|---|
| lead-developer | orchestrator: sizes, plans, builds, verifies, commits | yes (depth 1) | yes | yes |
| developer | implementer: tdd / direct / debug | no | yes | yes |
| researcher | codebase and web facts, every claim cited | no | no | no |
| software-architect | blueprint / ADR / greenfield / compare / critique | no | its plan or ADR file only | no |
| code-reviewer | review / refute / re-review / completeness | no | no | no |
| qa-engineer | verification gate, regression checks, tests | no | tests, when asked | yes |
| debugger | root cause first, then a fix when asked | no | fix + regression test, when asked | yes |
| security-reviewer | exploitable vulnerabilities only | no | no | no |
| ui-ux-designer | direction / build / critique / copy / judge | no | UI presentation files | yes |
| frontend-developer | UI implementer: component / direct / artifact / perf | no | yes | yes |
| design-system-engineer | audit / tokens / theme / playground / brand-check | no | tokens, themes, components | yes |
| visual-designer | concept / art / generative / image / motion | no | asset files | yes |
| e2e-test-engineer | browser end-to-end tests: write / visual / flake | no | e2e tests | yes |
| accessibility-reviewer | WCAG 2.2 AA: audit / review | no | no | no |
| **mcp-integration-engineer** (this one) | MCP servers: design / build / evals | no | yes | yes |
| technical-writer | documentation: draft / edit / reader-test | no | documentation files | yes |
| product-manager | discover / analyst / brief / PRD / prioritise / pre-mortem | no | its product documents only | no |
| product-owner | spec / slice / refine / validate / accept / replan / triage | no | its requirements and story files only | no |
| release-engineer | check / ship / deploy / watch / upgrade / rollback | no | version, changelog and dependency files | yes |
| agent-engineer | agent instructions: design / rule / test / review / diagnose | no | agent and skill instruction files | yes |

## When to use

- A new MCP server that wraps a service or an HTTP API.
- New tools for an existing MCP server, in its own SDK version and style.
- An MCP server whose tools are hard for a model to use: vague names, one tool per endpoint, unbounded lists, errors that say nothing about recovery.
- An evaluation set of realistic, read-only questions with verifiable answers for a server.

## Not for

- Application features outside the server: `developer`. Test suites beyond the server's self-check: `qa-engineer`.
- Security audits: `security-reviewer`. User documentation: `technical-writer`.
- Agent instructions and packages: `agent-engineer`.

## How it works

- It starts by looking for an existing server in the repository and noting its language, SDK major version, transport and how settings and credentials arrive. An existing server is extended, not rewritten.
- **Design:** it reads the target API's documentation, lists the jobs people actually ask for, and chooses focused tools that compose into those jobs, adding a workflow tool only where a job always chains the same calls. Each tool gets a service-prefixed snake_case name, a description that says what it returns and when to use a sibling tool, an input schema with bounds and defaults, pagination for lists, a Markdown or JSON response format, error messages that name the next step, and honest read-only, destructive, idempotent and open-world annotations. You see the design as a table and approve it before anything is built.
- **Limits live in the server**, never in a description, because the calling model may have read hostile text: the smallest scope per tool, ownership and bounds checked on every call, reads and writes in separate tools, a destructive tool that takes one exact id, and a URL-fetching tool limited to listed schemes and hosts. A server reachable beyond localhost checks its allowed hosts and verifies bearer tokens issued for it.
- **Build:** it uses the official MCP SDK for TypeScript or Python. Before it writes a call it reads the SDK version in use and opens a source for that version (the installed package, then the official documentation), and cites it. One API client, shared pagination and formatting helpers and one registered tool per design row. Work bigger than a small change gets a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task, then the finish menu: Push + open PR, Merge into `<base>` locally, or Keep local. Discard runs only when you ask, after a second confirmation.
- **Verification:** the build, then a self-check client script that starts the built server over stdio, lists its tools, calls read-only tools and checks that a zero, an empty, a missing and an oversized input each come back as a readable error. On the TypeScript SDK v2 the client is a separate package, so it asks before adding it as a dev dependency or speaks JSON-RPC to the server directly. The SDK inspector's command-line mode is used only after you agree to download it. Nothing is left running.
- **Evals:** ten independent, read-only, multi-step questions about stable data, each with one answer checked by exact string comparison, written to one XML file. It verifies every answer through the server's tools and runs no evaluation harness.
- Replies are plain sentences; say "terse" or "caveman" for short ones and "normal" to switch back.

## Tools and cards you'll see

| Action | Card |
|---|---|
| Reading and searching files, `code.git` status and log, `web.scrape` for API and SDK docs, the todo list | none |
| Each file it creates or edits | one per file |
| Builds, self-checks and installs (`os.execute`), chained into one command where possible | one each |
| `code.git` diff | may raise one; none in a trusted workspace on the Gateway we tested |
| Approving the tool design or a plan | a question, or the plan card in plan mode |

## After installing

- **Install:** `sophon agents install mcp-integration-engineer`, with `--allow-delegation-from lead-developer` if Lead Developer should brief it. The default effort is fine.
- **Allowed Medium-risk calls for the session** never cover this agent's edits, commits or shell commands, nor any call it makes as a sub-agent.
- **Bind and trust the folder.** Run `sophon` in the repository so the session is bound, then `/trust` the folder so its AGENTS.md conventions load.
- **Credentials** for the service come from environment variables or your secret store. Set them in the environment the shell inherits if you want checks against the live API; without them the self-check runs against a local mock of the API with a placeholder key, and the report says so.

## Works best with

- `lead-developer`: hands it the MCP server work in a larger plan.
- `security-reviewer`: reviews the server's auth and input handling.
- `technical-writer`: documents the server for its users.

## Limits

- It never starts a long-running server, an inspector UI or a watcher, so Streamable HTTP servers are tested in-process, and live end-to-end runs are left to you.
- Checks against the live API need credentials in the environment.
- It writes evaluation files but does not run them against a model.

## What it never does

- Guess an SDK API, a protocol field or an endpoint.
- Hard-code, log or print credentials, or put them in fixtures, eval files or commands.
- Write a destructive tool without saying so in its description and annotations, or use one in an evaluation.
- Add a dependency or download a tool without asking, or push without your choice in the Git menu.

## What's new in 3.0.0

- The self-check sends a zero, an empty, a missing and an oversized input; limits are enforced in the server, which treats its calling model as a possible attacker.
- SDK facts come from the version in use, with the source cited.
- The finish menu adds Merge into `<base>` locally; Discard only on request.
- A terse voice on request.

## Upgrading from 2.x

- 3.0.0 is a major version, so Sophon never applies it unattended. Take it yourself, one agent at a time: `sophon agents update <id>`.
- Update every family agent you have installed in one sitting. In between, Lead Developer 3.0.0 gives a companion below 3.0.0 the brief that 2.x understands and tells you once which agents to update, and a 3.0.0 companion still accepts a 2.x brief. An agent you created locally from these files reports no version and counts as current.
- Four agents are new: `product-owner`, `product-manager`, `release-engineer` and `agent-engineer`. Install the ones you want with `--allow-delegation-from lead-developer`. Updating never changes delegation settings, so an existing allow list needs them added.
- The instructions are longer. Each new session of this agent, and each sub-agent run of it, reads about 2,200 more tokens than in 2.x.
- 3.0.0 lists the optional `craft-reference` skill, which returns long reference material on request. Sophon offers to install it; if you decline, the agent works from what it carries.
- Your own edits to an installed agent pause its updates. Add `--discard-local-changes` to replace them.

## Reference skill

This agent can read longer tables, checklists and templates from the optional `craft-reference` skill, which Sophon offers when you install the agent. The skill does not run in plan mode or on a Gateway without the Docker sandbox, and the agent then works from the summary it carries. The skill's own notices credit the sources of its topics.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); addyosmani/agent-skills (MIT, © 2025 Addy Osmani); and Anthropic's security-guidance plugin, anthropics/claude-plugins-official (Apache-2.0).

Portions adapted from Anthropic's agent skills, anthropics/skills (Apache-2.0, © 2026 Anthropic, PBC), changed by Buildersoft LLC: rewritten for Sophon tools, with scripts and branding removed (mcp-builder).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, frontend-design; Apache-2.0).

Licensed under the Apache-2.0 License; see LICENSE.
