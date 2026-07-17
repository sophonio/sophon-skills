# Sophon Skills

Open-source **Skills** (and, later, **Plugins**) that [Buildersoft](https://buildersoft.io)
publishes to the [Sophon Marketplace](https://marketplace.sophon.buildersoft.io).

A **Skill** is a self-contained folder — a `manifest.json` describing the skill and its tools, an
entrypoint (e.g. `main.py`), a `README.md`, and a `LICENSE` — that Sophon can install and run in a
sandbox. This repo holds the source for first-party skills, a PowerShell pipeline that packages them
into `.sophon-skill` artifacts, and the docs for publishing them.

> These are **Sophon** skills (`manifest.json` format), not Claude Code / Anthropic `SKILL.md`
> plugins — a different ecosystem with a different manifest.

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
| [`airtable`](skills/airtable) | data | Read/write Airtable base records |
| [`stripe-read`](skills/stripe-read) | data | Read-only Stripe reporting (balance, charges, customers, invoices) |

**Files & media**

| Skill | Category | Description |
|-------|----------|-------------|
| [`pdf-toolkit`](skills/pdf-toolkit) | data | Merge, split, rotate, encrypt, and extract text/tables from PDFs |
| [`image-processing`](skills/image-processing) | utility | Resize, convert, crop, compress, and watermark images |
| [`json-yaml-tools`](skills/json-yaml-tools) | data | Convert, query (JMESPath), validate, and merge JSON/YAML/TOML |
| [`youtube-watcher`](skills/youtube-watcher) | data | Fetch YouTube transcripts to summarize or answer questions about a video |

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

All skills are pure-Python and run in the sandbox with no system binaries — most use only the
standard library (`urllib`, `hashlib`); a few pin small, pure-Python or musllinux-wheel dependencies.

## Repository layout

```
skills/<name>/        A skill: manifest.json + entrypoint + README.md + LICENSE
plugins/              Sophon plugins (.sophon-plugin, .NET gRPC) — scaffolded, none yet
templates/            Contributor scaffolds (skill-python, skill-csharp, plugin-*)
build/                Build-MarketplacePackages.ps1, Publish-MarketplacePackages.ps1
docs/PUBLISHING.md    How to build, validate, and publish to the Marketplace
dist/                 Built .sophon-skill artifacts (git-ignored)
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
3. `pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly` until it passes.
4. Open a PR. CI runs the same validation.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full contract and PR checklist, and
[`docs/PUBLISHING.md`](docs/PUBLISHING.md) for the publishing runbook.

## License

Licensed under the MIT License. © 2026 Buildersoft LLC. Each skill also carries its own LICENSE.
