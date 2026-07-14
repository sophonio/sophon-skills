# Google Personal Skill

Personal Gmail and Google Calendar integration for Sophon, built for `@gmail.com` accounts using an App Password — no OAuth or Google Cloud Console project required. Email is sent and read via IMAP/SMTP; calendar events are managed via Google's CalDAV endpoint.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `google.mail_list` | None | List recent inbox emails |
| `google.mail_read` | None | Read a specific email by ID |
| `google.mail_search` | None | Search emails by query |
| `google.mail_send` | High | Send a new email |
| `google.mail_reply` | High | Reply to an email |
| `google.calendar_list` | None | List upcoming calendar events |
| `google.calendar_create` | Medium | Create a calendar event |
| `google.calendar_update` | Medium | Update a calendar event |
| `google.calendar_delete` | High | Delete a calendar event |
| `google.calendar_search` | None | Search calendar events |

## Setup

1. Go to **Settings > Connections** in the Sophon Dashboard
2. Click **Connect** on the **Google Personal** card
3. Enter your Gmail address (must be `@gmail.com`)
4. Enter an App Password — requires 2-Step Verification to be enabled on the account

Generate an App Password at: https://myaccount.google.com/apppasswords

## Usage Examples

**List recent mail:**
> "Show me my last 10 emails"

**Reply to a message:**
> "Reply to that email from Sarah and say I'll join the call"

**Check the calendar:**
> "What's on my calendar for the next 7 days?"

**Create an event:**
> "Schedule a team sync tomorrow at 2pm for 30 minutes"

## Requirements

- A personal `@gmail.com` Google account with 2-Step Verification enabled (required to generate an App Password)
- Network access from the sandbox to Gmail's IMAP/SMTP servers and Google's CalDAV endpoint

## Third-Party Software

- `caldav` — dual-licensed **GPL-3.0-or-later** / **Apache-2.0** (see its PyPI distribution for full license terms)

## Trademarks

Google, Gmail, and Google Calendar are trademarks of Google LLC. This skill is an independent integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or sponsored by Google.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
