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
| [`jira`](skills/jira) | integration | Jira — search issues, manage projects |
| [`linear`](skills/linear) | integration | Linear issues, projects, cycles, and comments (GraphQL) |
| [`dependency-audit`](skills/dependency-audit) | development | Scan lockfiles for known CVEs via the OSV.dev API |

**Productivity, docs & calendar**

| Skill | Category | Description |
|-------|----------|-------------|
| [`notion`](skills/notion) | integration | Read/search/create/update Notion pages and databases |
| [`todoist`](skills/todoist) | productivity | Manage Todoist tasks and projects |
| [`caldav-calendar`](skills/caldav-calendar) | integration | Event CRUD on any CalDAV server (iCloud, Fastmail, Nextcloud) |
| [`confluence`](skills/confluence) | integration | Confluence — search pages, manage content and spaces |
| [`google-gmail`](skills/google-gmail) | integration | Google personal email & calendar (Gmail IMAP/SMTP, Calendar CalDAV) |

**Data & files**

| Skill | Category | Description |
|-------|----------|-------------|
| [`sql-query`](skills/sql-query) | data | Query PostgreSQL / MySQL / SQLite with schema introspection |
| [`pdf-toolkit`](skills/pdf-toolkit) | data | Merge, split, rotate, encrypt, and extract text/tables from PDFs |
| [`image-processing`](skills/image-processing) | utility | Resize, convert, crop, compress, and watermark images |
| [`json-yaml-tools`](skills/json-yaml-tools) | data | Convert, query (JMESPath), validate, and merge JSON/YAML/TOML |
| [`youtube-watcher`](skills/youtube-watcher) | data | Fetch YouTube transcripts to summarize or answer questions about a video |

All skills are pure-Python and run in the sandbox with no system binaries — API skills use the
standard library (`urllib`); others pin small, pure-Python or musllinux-wheel dependencies.

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

MIT © 2026 Buildersoft LLC. Each skill also carries its own `LICENSE`.
