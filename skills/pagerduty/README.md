# PagerDuty

Interact with PagerDuty from Sophon: list and inspect incidents, acknowledge and resolve them,
create (trigger) new incidents, and see who is currently on call.

Implemented with the PagerDuty REST API v2 over the Python standard library (no dependencies), so it
runs in the sandbox unchanged.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `pagerduty.list_incidents` | none | List incidents (filter by status/urgency) |
| `pagerduty.get_incident` | none | Get one incident by id |
| `pagerduty.acknowledge_incident` | medium | Acknowledge a triggered incident |
| `pagerduty.resolve_incident` | medium | Resolve an incident |
| `pagerduty.create_incident` | high | Trigger a new incident (pages on-call responders) |
| `pagerduty.list_oncalls` | none | List current on-call assignments |

## Connection

Connect the **PagerDuty** integration with:

- **API Token** *(required)* — a [PagerDuty REST API token](https://support.pagerduty.com/docs/api-access-keys).
- **From Email** *(optional)* — the email of a valid PagerDuty user. This is **required** to
  acknowledge, resolve, or create incidents (PagerDuty attributes write actions to this user).

The token is stored in Sophon's credential vault and supplied to the skill at call time; it is never
written into the skill.

## Notes

- `pagerduty.create_incident` pages real on-call responders, so it is marked high-risk and can be
  gated behind approval.
- Write actions (acknowledge, resolve, create) fail with a clear error if no From email is set.

## Trademarks

PagerDuty is a trademark of PagerDuty, Inc. This is an unofficial, independently built integration
and is not affiliated with or endorsed by PagerDuty.
