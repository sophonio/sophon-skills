# Sophon Skills

Open-source **Skills and Agents** (and, later, **Plugins**) that [Buildersoft](https://buildersoft.io)
publishes to the [Sophon Marketplace](https://marketplace.sophon.buildersoft.io).

A **Skill** is a self-contained folder — a `manifest.json` describing the skill and its tools, an
entrypoint (e.g. `main.py`), a `README.md`, and a `LICENSE` — that Sophon can install and run in a
sandbox. This repo holds the source for first-party skills, a PowerShell pipeline that packages them
into `.sophon-skill` artifacts, and the docs for publishing them.

> These are **Sophon** skills (`manifest.json` format), not Claude Code / Anthropic `SKILL.md`
> plugins — a different ecosystem with a different manifest.

## Agents

The **Buildersoft development family 2.1.0**: sixteen `.sophon-agent` packages that work on a
repository the way Claude Code does. They plan in a markdown file you approve, execute it task by
task with a live todo list, verify with real commands, commit each verified task on a feature
branch and offer a pull request. The nine original agents are licensed **MIT**; the seven
frontend, design, testing, MCP and docs agents added in 2.1 are licensed **Apache-2.0**. Only Lead
Developer starts sub-agents, and only with your consent.

The seventeenth package, [Artifact Creator](agents/artifact-creator), is a standalone **Apache-2.0**
productivity agent for grounded reports, explainers, guides, diagrams and presentations across
subjects. It does not delegate or build interactive applications. File creation depends on the
available tools and permissions; live creation has not been verified for this package.
All seventeen are authored by **Buildersoft LLC** and require **Sophon 2.2.0+**.

| Agent | Role | Delegates | Read-only |
|-------|------|-----------|-----------|
| [Lead Developer](agents/lead-developer) | Sizes, plans, builds (alone or with consented sub-agents), verifies, commits, offers a PR | yes | no |
| [Developer](agents/developer) | One scoped change, test first, verified | no | no |
| [Researcher](agents/researcher) | Codebase and web facts, every claim cited | no | yes |
| [Software Architect](agents/software-architect) | One decisive blueprint, ADRs, plans the lead can run | no | yes (saves only its plan or ADR) |
| [Code Reviewer](agents/code-reviewer) | Defects it can show: line, failing case, fix | no | yes |
| [QA Engineer](agents/qa-engineer) | PASS / FAIL gates with fresh evidence, red/green proofs, tests | no | no |
| [Debugger](agents/debugger) | Reproduce, one hypothesis at a time, proven root cause | no | no |
| [Security Reviewer](agents/security-reviewer) | Exploitable vulnerabilities a change introduces | no | yes |
| [UI/UX Designer](agents/ui-ux-designer) | Design direction, presentation-layer build, critique, interface copy | no | no |
| [Frontend Developer](agents/frontend-developer) | UI implementation: components, direct edits, artifacts, performance | no | no |
| [Design System Engineer](agents/design-system-engineer) | Design-system audits, tokens, themes, playgrounds, brand checks | no | no |
| [Visual Designer](agents/visual-designer) | Concepts, art, generative pieces, images (image generation only if you opt in), motion | no | no |
| [E2E Test Engineer](agents/e2e-test-engineer) | Browser end-to-end and visual tests, red then green, flaky tests made deterministic | no | no |
| [Accessibility Reviewer](agents/accessibility-reviewer) | WCAG 2.2 AA audits and reviews, verdict CONFORMS or GAPS | no | yes |
| [MCP Integration Engineer](agents/mcp-integration-engineer) | MCP servers: design, build, evals | no | no |
| [Technical Writer](agents/technical-writer) | Documentation drafted with you, edited or reader-tested; every command checked | no | no |

Each `agents/<id>/SOUL.md` is generated from `build/agent-src/`; never edit it by hand. Compose,
check and build with Sophon CLI 2.2.x on PATH:

Each package's `LICENSE` matches its canonical source byte for byte: the root `LICENSE` for MIT,
or `build/licenses/Apache-2.0.txt` for Apache-2.0.

```powershell
pwsh -NoProfile -File build/Compose-AgentSouls.ps1                # regenerate agents/*/SOUL.md
pwsh -NoProfile -File build/Test-AgentSources.ps1                 # lint, preflight, budgets, manifests (no CLI)
pwsh -NoProfile -File build/Build-AgentPackages.ps1 -ValidateOnly # adds sophon dev validate: 0 errors, 0 warnings
pwsh -NoProfile -File build/Build-AgentPackages.ps1               # dist/agents/<id>-<version>.sophon-agent + SHA256SUMS
pwsh -NoProfile -File tests/agents/Test-AgentPackages.ps1         # sections A-L
```

Upload artifacts are in **`dist/agents/`**, with a `SHA256SUMS` index. Nothing is uploaded by
these commands: agents are published manually, one file at a time, in the Marketplace wizard. See
[docs/AGENTS.md](docs/AGENTS.md) for install order, the settings a package cannot carry, the
approval cards to expect and the maintainer runbook. The skill build/publish scripts remain
skill-only.

## Video agent

**[Video Producer](agents/video-producer)** 1.0.0, the only agent of the separate **video**
family. It turns a brief, a script or your own footage into a finished short video: script and
storyboard for your approval, voice-over, images, clips and music from Sophon's media tools, then
a local edit, captions, mix, platform checks and render with the
[`ffmpeg-video`](skills/ffmpeg-video) skill. It needs FFmpeg 6.1+ and Python 3.10+ on the computer
that runs Sophon, and Sophon's process sandbox (the Docker sandbox has no FFmpeg). Install the
skill first; the agent's README covers requirements, the isolation trade-off and limits.

Both families are built by the same commands above; `-Family <id>` limits a command to one of
them. See [docs/AGENTS.md](docs/AGENTS.md) section 14.

## Skills in this repo

**Developer & source control**

| Skill | Category | Description |
|-------|----------|-------------|
| [`github`](skills/github) | development | Issues, pull requests, and Actions runs, plus a raw REST API passthrough |
| [`gitlab`](skills/gitlab) | development | Issues, merge requests, and CI/CD pipelines (SaaS + self-managed) |
| [`jira`](skills/jira) | integration | Jira — search issues, manage projects |
| [`linear`](skills/linear) | integration | Linear issues, projects, cycles, and comments (GraphQL) |
| [`sentry`](skills/sentry) | development | Triage Sentry issues — search, inspect events, resolve/assign |
| [`dependency-audit`](skills/dependency-audit) | development | Scan lockfiles for known CVEs via the OSV.dev API |
| [`package-registry`](skills/package-registry) | development | Look up npm & PyPI package metadata and versions (keyless) |
| [`code-search`](skills/code-search) | development | Search GitHub code, repositories, and commits |
| [`github-projects`](skills/github-projects) | development | Manage GitHub Projects v2 boards and items (GraphQL) |

**Observability & incident**

| Skill | Category | Description |
|-------|----------|-------------|
| [`prometheus-query`](skills/prometheus-query) | data | Run PromQL instant/range queries; inspect alerts and targets |
| [`grafana`](skills/grafana) | integration | Search dashboards, list datasources/alert rules, create annotations |
| [`datadog`](skills/datadog) | integration | Query metrics and list/mute monitors |
| [`pagerduty`](skills/pagerduty) | integration | List/ack/resolve/create incidents and look up on-call |
| [`opsgenie`](skills/opsgenie) | integration | List/ack/close/create Opsgenie alerts and on-call lookup |
| [`alertmanager`](skills/alertmanager) | data | Inspect Prometheus Alertmanager alerts and manage silences |
| [`loki-logs`](skills/loki-logs) | data | Query and tail logs from Grafana Loki with LogQL |

**Productivity, docs & calendar**

| Skill | Category | Description |
|-------|----------|-------------|
| [`notion`](skills/notion) | integration | Read/search/create/update Notion pages and databases |
| [`todoist`](skills/todoist) | productivity | Manage Todoist tasks and projects |
| [`caldav-calendar`](skills/caldav-calendar) | integration | Event CRUD on any CalDAV server (iCloud, Fastmail, Nextcloud) |
| [`confluence`](skills/confluence) | integration | Confluence — search pages, manage content and spaces |
| [`google-gmail`](skills/google-gmail) | integration | Google personal email & calendar (Gmail IMAP/SMTP, Calendar CalDAV) |
| [`outlook-calendar`](skills/outlook-calendar) | integration | Microsoft 365 calendar events via Graph (app-only) |

**Cloud, infra & business**

| Skill | Category | Description |
|-------|----------|-------------|
| [`cloudflare`](skills/cloudflare) | integration | Manage DNS records, purge cache, and list zones |
| [`vercel`](skills/vercel) | integration | Inspect deployments, projects, and environment variables |
| [`kubernetes`](skills/kubernetes) | development | Inspect and operate clusters — pods, deployments, logs, scale |
| [`fly-io`](skills/fly-io) | integration | Manage Fly.io Machines (list, start/stop/restart/destroy) |
| [`home-assistant`](skills/home-assistant) | integration | Read entity states and call services on Home Assistant |
| [`sql-query`](skills/sql-query) | data | Query PostgreSQL / MySQL / SQLite with schema introspection |
| [`postgres`](skills/postgres) | data | Named PostgreSQL connections, schema discovery, and read/write SQL tools |
| [`mssql`](skills/mssql) | data | Named SQL Server connections, schema discovery, and read/write SQL tools |
| [`oracle`](skills/oracle) | data | Named Oracle connections, schema discovery, and read/write SQL tools |
| [`mysql`](skills/mysql) | data | Named MySQL/MariaDB connections, schema discovery, and read/write SQL tools |
| [`sqlite`](skills/sqlite) | data | Managed SQLite files, schema discovery, and read/write SQL tools |
| [`airtable`](skills/airtable) | data | Read/write Airtable base records |
| [`stripe-read`](skills/stripe-read) | data | Read-only Stripe reporting (balance, charges, customers, invoices) |

**Files & media**

| Skill | Category | Description |
|-------|----------|-------------|
| [`pdf-toolkit`](skills/pdf-toolkit) | data | Merge, split, rotate, encrypt, and extract text/tables from PDFs |
| [`image-processing`](skills/image-processing) | utility | Resize, convert, crop, compress, and watermark images |
| [`json-yaml-tools`](skills/json-yaml-tools) | data | Convert, query (JMESPath), validate, and merge JSON/YAML/TOML |
| [`youtube-watcher`](skills/youtube-watcher) | data | Fetch YouTube transcripts to summarize or answer questions about a video |
| [`ffmpeg-video`](skills/ffmpeg-video) | utility | Edit, caption, mix, check and render video locally with FFmpeg (44 tools; process sandbox only) |

**Enterprise systems**

| Skill | Category | Description |
|-------|----------|-------------|
| [`salesforce`](skills/salesforce) | integration | Query and update Salesforce CRM records with SOQL/SOSL (client-credentials) |
| [`servicenow`](skills/servicenow) | integration | Work ServiceNow incidents, changes, and knowledge (OAuth or basic auth) |
| [`sharepoint`](skills/sharepoint) | integration | Search SharePoint sites, query lists, and find files via Graph (app-only) |
| [`snowflake`](skills/snowflake) | data | Run SQL and browse databases/schemas on Snowflake (programmatic access token) |
| [`zendesk`](skills/zendesk) | integration | Triage and respond to Zendesk Support tickets (client-credentials) |
| [`outlook-mail`](skills/outlook-mail) | integration | Microsoft 365 mailbox triage — read, search, draft, send via Graph (app-only) |
| [`entra-id`](skills/entra-id) | integration | Look up Entra ID users, groups, roles, sign-ins, and app registrations |
| [`databricks`](skills/databricks) | data | Execute SQL on warehouses, browse Unity Catalog, and trigger jobs |
| [`okta`](skills/okta) | integration | Search Okta users/groups/apps and query the system log |
| [`azure-devops`](skills/azure-devops) | development | Azure DevOps work items (WIQL), builds, PRs, and pipeline runs |
| [`splunk`](skills/splunk) | data | Run SPL searches and browse indexes and saved searches (auth token) |
| [`elasticsearch`](skills/elasticsearch) | data | Query Elasticsearch/OpenSearch — Query DSL, ES\|QL, mappings, cluster health |
| [`powerbi`](skills/powerbi) | data | List Power BI workspaces and reports, run DAX queries, trigger refreshes |
| [`onedrive`](skills/onedrive) | integration | Browse, search, read, and upload OneDrive for Business files (Graph app-only) |
| [`bitbucket`](skills/bitbucket) | development | Bitbucket Cloud repos, pull requests, diffs, and Pipelines runs |
| [`mongodb-atlas`](skills/mongodb-atlas) | data | MongoDB Atlas operations — clusters, alerts, metrics, events (service account) |
| [`jenkins`](skills/jenkins) | development | Inspect Jenkins jobs, builds, and queue; read console logs; trigger builds |
| [`intercom`](skills/intercom) | integration | Search Intercom conversations and contacts, add notes, reply, and triage |
| [`freshdesk`](skills/freshdesk) | integration | Freshdesk ticket triage — list, search, create, update, and annotate |
| [`freshservice`](skills/freshservice) | integration | Freshservice ITSM — tickets, change requests, and asset lookups |
| [`hubspot`](skills/hubspot) | integration | HubSpot CRM — search, create, and update contacts, companies, deals, tickets |
| [`pipedrive`](skills/pipedrive) | integration | Pipedrive sales pipeline — deals, contacts, notes, and activities |
| [`clickhouse`](skills/clickhouse) | data | Read-only SQL on ClickHouse plus schema and storage introspection |
| [`sonarqube`](skills/sonarqube) | development | Quality gates, issues, hotspots, and metrics from SonarQube/SonarCloud |
| [`jira-service-management`](skills/jira-service-management) | integration | JSM service desks — queues, requests, SLAs, comments, approvals |
| [`planner`](skills/planner) | productivity | Microsoft Planner plans, buckets, and tasks via Graph (app-only) |
| [`tableau`](skills/tableau) | data | Tableau workbooks, view data, jobs, and extract refreshes (PAT) |
| [`hashicorp-vault`](skills/hashicorp-vault) | integration | Vault health, mounts, secret metadata, and policies (token or AppRole) |
| [`dynamics-365`](skills/dynamics-365) | integration | Dynamics 365 Dataverse records — OData queries and record CRUD |
| [`artifactory`](skills/artifactory) | development | JFrog Artifactory repositories, artifact search (AQL), builds, properties |

**Entertainment & media**

| Skill | Category | Description |
|-------|----------|-------------|
| [`tmdb`](skills/tmdb) | data | Search movies/TV, discovery, trending, and streaming providers (TMDB) |
| [`plex`](skills/plex) | integration | Search a Plex server, sessions, on-deck, recently added, library scans |
| [`jellyfin`](skills/jellyfin) | integration | Jellyfin library search, items, sessions, next-up, metadata refresh |
| [`radarr`](skills/radarr) | integration | Radarr movie library, calendar, queue, and add/monitor movies |
| [`sonarr`](skills/sonarr) | integration | Sonarr series library, calendar, missing episodes, queue, add series |
| [`seerr`](skills/seerr) | integration | Overseerr/Jellyseerr media requests — search, request, approve, decline |
| [`steam`](skills/steam) | integration | Steam profiles, owned/recent games, achievements, player counts, news |
| [`twitch`](skills/twitch) | integration | Twitch streams, top games, clips, VODs, and channel info (app token) |
| [`ticketmaster`](skills/ticketmaster) | integration | Search live events, attractions, and venues via Ticketmaster Discovery |
| [`lastfm`](skills/lastfm) | integration | Last.fm artist info, similar artists, charts, and public listening history |

**Research & utilities**

| Skill | Category | Description |
|-------|----------|-------------|
| [`wikipedia`](skills/wikipedia) | data | Search Wikipedia and read article summaries/full text (keyless) |
| [`translate-text`](skills/translate-text) | integration | Machine translation via the DeepL API |
| [`currency-convert`](skills/currency-convert) | data | Convert currencies and fetch ECB reference rates (keyless) |
| [`dns-tools`](skills/dns-tools) | utility | DNS lookups (DoH), mail records (SPF/DMARC), and RDAP whois (keyless) |
| [`uptime-check`](skills/uptime-check) | utility | Probe HTTP/TCP endpoints and check TLS certificate expiry |
| [`units-convert`](skills/units-convert) | utility | Offline unit conversion across length, mass, temperature, and more |
| [`crypto-utils`](skills/crypto-utils) | utility | Offline hashing, HMAC, JWT decode/verify, token & password generation |

All skills but one are pure-Python and run in the sandbox with no system binaries — most use only
the standard library (`urllib`, `hashlib`); a few pin small, pure-Python or musllinux-wheel
dependencies. The exception is `ffmpeg-video`: it drives the FFmpeg installed on the host, so it
runs only on Sophon's process sandbox backend, and it ships the MIT-licensed
[ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) unchanged under `vendor/` (see
[docs/VENDORING.md](docs/VENDORING.md)).

## Repository layout

```
skills/<name>/        A skill: manifest.json + entrypoint + README.md + LICENSE (+ optional lib/, locked vendor/)
agents/<id>/          An agent: manifest.json + SOUL.md (generated) + TOOLS.md + README.md + LICENSE
plugins/              Sophon plugins (.sophon-plugin, .NET gRPC) — scaffolded, none yet
templates/            Contributor scaffolds (skill-python, skill-csharp, plugin-*)
build/                Build-MarketplacePackages.ps1, Publish-MarketplacePackages.ps1, SkillLint.psm1 (skills);
                      Compose-AgentSouls.ps1, Test-AgentSources.ps1, Build-AgentPackages.ps1 (agents)
build/catalog/        Data for the skill checks: sandbox stdlib list, marketplace rules
build/ffmpeg-video/   Vendoring and generation for ffmpeg-video: Sync-FfmpegSkill.ps1, generate.py, policy.json
build/agent-src/      Agent sources: families.psd1 (registry), family.psd1 (development), souls/, fragments/,
                      families/video/, tool catalogue
tests/skills/         Offline skill tests (run_all.py), the Sophon sandbox simulator, ffmpeg-video tests
tests/build/          Skill build-check tests (Test-SkillLint.ps1) and fixture skills
tests/agents/         Agent package tests (Test-AgentPackages.ps1), fixtures, manual eval scenarios
docs/PUBLISHING.md    How to build, validate, and publish to the Marketplace
docs/AGENTS.md        The agents: install, settings, cards, families, maintainer runbook
docs/VENDORING.md     Policy for third-party code vendored into a skill
dist/                 Built .sophon-skill artifacts; dist/agents/ holds .sophon-agent (git-ignored)
```

## Quick start

Requires [PowerShell 7+](https://learn.microsoft.com/powershell/) (`pwsh`).

```bash
# Validate every skill's manifest against the marketplace contract (no output written)
pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly

# Build .sophon-skill artifacts into dist/ (prints a SHA256 per artifact)
pwsh -File build/Build-MarketplacePackages.ps1

# Publish dist/ artifacts to the Marketplace (needs an smk_ publisher key)
$env:SOPHON_MARKETPLACE_API_KEY = 'smk_...'
pwsh -File build/Publish-MarketplacePackages.ps1
```

## Adding a skill

1. Copy `templates/skill-python/` (or `templates/skill-csharp/`) to `skills/<your-skill>/` and
   rename the `.template` files.
2. Fill in `manifest.json` — see the field contract in [`CONTRIBUTING.md`](CONTRIBUTING.md). The
   folder name **must** equal the manifest `name`.
3. `pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly` until it passes, and add a
   `tests/skills/test_<your-skill>.py` that `python tests/skills/run_all.py` runs.
4. Open a PR. CI runs the same validation.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full contract and PR checklist, and
[`docs/PUBLISHING.md`](docs/PUBLISHING.md) for the publishing runbook.

## License

Licensed under the MIT License. © 2026 Buildersoft LLC. Each skill also carries its own LICENSE.

The development agents each carry their own LICENSE too: the nine original agents are MIT, and the
seven added in 2.1 and Artifact Creator are licensed under the Apache License, Version 2.0.

The development agents' workflow patterns are adapted, not copied, from obra/superpowers (MIT,
© 2025 Jesse Vincent) and Anthropic's Claude Code plugins (Apache-2.0). Portions of the agents
added in 2.1 are adapted from Anthropic's agent skills, anthropics/skills (Apache-2.0, © 2026
Anthropic, PBC), and changed by Buildersoft LLC.

`skills/ffmpeg-video/vendor/ffmpeg-skill/` is ffmpeg-skill by kajisho5 (MIT, © 2026 kajisho5),
shipped unchanged; see `skills/ffmpeg-video/THIRD_PARTY_NOTICES.md`. FFmpeg is a trademark of
Fabrice Bellard; this project is not affiliated with or endorsed by the FFmpeg project.
