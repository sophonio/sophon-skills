# Pipedrive Skill

Pipedrive CRM integration for Sophon — search deals, people, organizations, and leads; work your pipeline; and log notes and activities. Authenticates with your personal Pipedrive API token (sent as the `x-api-token` header) against `https://<companyDomain>.pipedrive.com`.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `pipedrive.search` | None | Search deals, people, organizations, and leads by term |
| `pipedrive.list_deals` | None | List deals filtered by pipeline, stage, status, or owner (cursor pagination) |
| `pipedrive.get_deal` | None | Get a deal's title, value, stage, status, owner, links, and expected close date |
| `pipedrive.get_person` | None | Get a person's name, emails, phones, and organization |
| `pipedrive.update_deal` | Medium | Move a deal to another stage, change its status, value, or owner |
| `pipedrive.add_note` | Low | Add a note to a deal, person, or organization |
| `pipedrive.create_activity` | Low | Create a call, meeting, task, deadline, email, or lunch activity |

## Setup

1. Find your **company domain**: it is the subdomain of the URL you use to open Pipedrive — for `https://yourcompany.pipedrive.com` it is `yourcompany`. Enter only the subdomain.
2. Get your **personal API token**: in Pipedrive, click your profile avatar and go to **Settings > Personal preferences > API**, then copy *Your personal API token*.
3. Note: company admins can **disable API access per user**. If the API tab is missing or requests fail with a permissions error, ask your Pipedrive admin to enable API access for your user.
4. The token acts as *you* — every tool call sees and changes only what your Pipedrive user can see and change.
5. Go to **Settings > Connections** in the Sophon Dashboard, click **Connect** on the Pipedrive card, enter the company domain and API token, and test the connection.

## Usage Examples

**Search the CRM:**
> "Search Pipedrive for anything matching 'Acme'"

**Work the pipeline:**
> "List my open deals in the Sales pipeline"

**Inspect a deal:**
> "Show me deal 42 — value, stage, and expected close date"

**Move a deal:**
> "Mark deal 42 as won"

**Log follow-ups:**
> "Add a note to deal 42 that the contract was sent, and create a call activity for tomorrow"

## Requirements

- A Pipedrive account on any plan with API access enabled for your user (admins can disable it per user).
- Pipedrive rate limiting is a **daily API token budget** (sized by plan and seats). Once the budget is spent, all requests return HTTP 429 until it resets at midnight — the skill surfaces this clearly when it happens.
- The skill prefers narrow field returns: list and get tools return trimmed summaries, not raw API payloads.

## Trademarks

Pipedrive is a trademark of Pipedrive Inc. This skill is an independent integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or sponsored by Pipedrive.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
