# Freshdesk Skill

Freshdesk helpdesk integration for Sophon — list, search, create, and update support tickets, read ticket conversations, add notes, and look up contacts via the Freshdesk REST API v2.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `freshdesk.list_tickets` | None | List tickets with optional view filter, updated-since, and sort order |
| `freshdesk.get_ticket` | None | Get a ticket's details plus its conversation thread |
| `freshdesk.search_tickets` | None | Search tickets with a Freshdesk query expression |
| `freshdesk.search_contacts` | None | Find contacts by query expression or exact email |
| `freshdesk.create_ticket` | Medium | Create a new support ticket |
| `freshdesk.update_ticket` | Medium | Update a ticket's status, priority, assignee, or tags |
| `freshdesk.add_note` | Low | Add a private or public note to a ticket |

## Setup

1. Log in to your Freshdesk portal (e.g. `https://yourcompany.freshdesk.com`)
2. Click your profile picture (top right) and open **Profile Settings**
3. Click **View API key** (you may need to complete a captcha) and copy the key — no admin
   involvement is needed; every agent can view their own API key, and API calls act as that agent
4. In Sophon, open **Settings > Connections**, click **Connect** on the Freshdesk card
5. Enter your Freshdesk URL (e.g. `https://yourcompany.freshdesk.com`) and paste the API key
6. Test the connection

Finding your API key: https://support.freshdesk.com/support/solutions/articles/215517-how-to-find-your-api-key

## Usage Examples

**List tickets:**
> "Show my open Freshdesk tickets sorted by priority"

**Read a ticket:**
> "Summarize Freshdesk ticket 4521 including the conversation history"

**Search:**
> "Search Freshdesk for urgent open tickets tagged billing"

**Create a ticket:**
> "Create a Freshdesk ticket for jane@acme.com titled 'Cannot log in' with high priority"

**Add a note:**
> "Add a private note to ticket 4521 saying the fix ships Friday"

## Requirements

- A Freshdesk account (any plan — the REST API is available on all plans, including the free tier)
- An agent login; the API key inherits that agent's permissions, so the agent must be allowed to
  view/edit the tickets and contacts you want to work with
- API rate limits are plan-dependent per-minute quotas, and invalid requests count against them;
  when the limit is hit Freshdesk returns HTTP 429 and this skill surfaces the `Retry-After` value

## Trademarks

Freshdesk is a trademark of Freshworks Inc. This project is not affiliated with or endorsed by Freshworks Inc.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
