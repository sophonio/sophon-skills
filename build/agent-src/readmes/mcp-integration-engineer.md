# MCP Integration Engineer

Designs, builds and evaluates Model Context Protocol servers that let a model use a service well.

Part of the Buildersoft development family {{= FamilyVersion}}.

{{# roster}}

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

{{> readme/80-upgrade-3}}

{{> readme/70-reference-skill}}

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); addyosmani/agent-skills (MIT, © 2025 Addy Osmani); and Anthropic's security-guidance plugin, anthropics/claude-plugins-official (Apache-2.0).

Portions adapted from Anthropic's agent skills, anthropics/skills (Apache-2.0, © 2026 Anthropic, PBC), changed by Buildersoft LLC: rewritten for Sophon tools, with scripts and branding removed (mcp-builder).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0).

Licensed under the Apache-2.0 License; see LICENSE.
