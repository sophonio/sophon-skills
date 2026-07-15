# CalDAV Calendar

Manage calendars and events on any CalDAV server from Sophon: list calendars, list events in a time
range, and create, update, or delete events. Works with iCloud, Fastmail, Nextcloud, Google
(app-password), and other standards-compliant CalDAV providers.

Implemented with the pure-python [`caldav`](https://pypi.org/project/caldav/) client and
[`icalendar`](https://pypi.org/project/icalendar/) for parsing and building events, so it runs in the
sandbox unchanged.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `caldav.list_calendars` | none | List the calendars on the connected account |
| `caldav.list_events` | none | List events in a calendar within a time range |
| `caldav.create_event` | medium | Create a new event |
| `caldav.update_event` | medium | Update an existing event by UID |
| `caldav.delete_event` | high | Delete an event by UID (not reversible) |

Times are given as ISO 8601 dates (`2026-07-01`, all-day) or datetimes
(`2026-07-01T09:00:00` / `2026-07-01T09:00:00Z`). A calendar is addressed by its **name** or **URL**
(from `caldav.list_calendars`); omit it to use the first calendar on the account.

## Connection

Connect the **CalDAV Calendar** integration with:

- **CalDAV URL** — your provider's CalDAV endpoint:
  - iCloud: `https://caldav.icloud.com/`
  - Fastmail: `https://caldav.fastmail.com/`
  - Nextcloud: `https://<your-host>/remote.php/dav`
  - Google: `https://apidata.googleusercontent.com/caldav/v2/`
- **Username** — your account username / email for the provider.
- **App Password** — an **app-specific password**, not your main account password. Most providers
  require you to generate one (and to enable two-factor authentication first):
  - iCloud: Apple ID > Sign-In and Security > App-Specific Passwords
  - Fastmail: Settings > Privacy & Security > App Passwords
  - Google: Google Account > Security > App Passwords

Credentials are stored in Sophon's credential vault and supplied to the skill at call time; they are
never written into the skill.

## Notes

- `caldav.delete_event` is irreversible and marked high-risk so Sophon can gate it behind approval.
- Events are located for update/delete by their **UID**. Use `caldav.list_events` to discover UIDs.

## Trademarks

iCloud is a trademark of Apple Inc.; Fastmail is a trademark of Fastmail Pty Ltd; Nextcloud is a
trademark of Nextcloud GmbH; Google is a trademark of Google LLC. This is an unofficial, independently
built CalDAV integration and is not affiliated with or endorsed by any of these providers.
