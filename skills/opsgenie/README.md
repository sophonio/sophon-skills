# Opsgenie

Interact with Opsgenie from Sophon: list and inspect alerts, acknowledge and close them, create new
alerts that page on-call responders, and see who is currently on call for a schedule.

Implemented with the Opsgenie Alert API v2 over the Python standard library (no dependencies), so it
runs in the sandbox unchanged.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `opsgenie.list_alerts` | none | List alerts, optionally filtered with a search query |
| `opsgenie.get_alert` | none | Get one alert by id |
| `opsgenie.acknowledge_alert` | medium | Acknowledge an alert |
| `opsgenie.close_alert` | medium | Close an alert |
| `opsgenie.create_alert` | high | Create a new alert (can page on-call responders) |
| `opsgenie.who_is_on_call` | none | Get current on-call participants for a schedule |

## Connection

Connect the **Opsgenie** integration with:

- **API Key** — an Opsgenie API integration key. Authenticates as `GenieKey <apiKey>`.
- **Region** *(optional)* — `us` (default) or `eu`. EU accounts use `https://api.eu.opsgenie.com`;
  all others use `https://api.opsgenie.com`.

The API key is stored in Sophon's credential vault and supplied to the skill at call time; it is
never written into the skill.

## Notes

- `opsgenie.create_alert` is marked high-risk because creating an alert can page on-call responders.
  Sophon can gate it behind approval.
- Acknowledge/close operations return a `requestId`; Opsgenie processes them asynchronously.

## Trademarks

Opsgenie is a trademark of Atlassian. This is an unofficial, independently built integration and is
not affiliated with or endorsed by Atlassian.
