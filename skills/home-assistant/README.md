# Home Assistant

Read and control your Home Assistant instance from Sophon: list entity states and history, list
service domains, and call services to control devices — all through the Home Assistant REST API.

Implemented over the Python standard library (`urllib`, no dependencies), so it runs in the sandbox
unchanged. The `/api` path is appended to your configured base URL automatically.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `ha.list_states` | none | List all entities with current state and friendly name |
| `ha.get_state` | none | Get the full state object for a single entity |
| `ha.list_services` | none | List available service domains and their services |
| `ha.call_service` | high | Call a service to control a device or entity |
| `ha.get_history` | none | Get recent state history for an entity over the past N hours |

`ha.call_service` is rated **high** because it can perform real-world actions (unlocking doors,
opening garages, switching devices) that are not always reversible.

## Connection

Connect the **Home Assistant** integration with:

- **Base URL** *(required)* — base URL of your Home Assistant instance, e.g.
  `http://homeassistant.local:8123`.
- **Long-Lived Access Token** *(required)* — create one in Home Assistant under
  **Profile > Security > Long-Lived Access Tokens**. Sent as `Authorization: Bearer …`.

Credentials are stored in Sophon's credential vault and supplied to the skill at call time; they are
never written into the skill.

## Notes

- All tools except `ha.call_service` are read-only.
- `ha.call_service` sends `{"entity_id": entityId, ...data}` to
  `POST /api/services/{domain}/{service}` and returns the entities Home Assistant reports as changed.
- On an API error the tool returns `{"error": "..."}`.

## Trademarks

Home Assistant is a trademark of the Open Home Foundation. This is an unofficial, independently built
integration and is not affiliated with or endorsed by Home Assistant or the Open Home Foundation.
