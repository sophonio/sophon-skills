"""Home Assistant integration skill — talks to the Home Assistant REST API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (host, token).

Auth is a Long-Lived Access Token sent as `Authorization: Bearer ...`. The base URL is the
configured host with `/api` appended.
"""

import json
import datetime
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
host = (params.get("host") or "").rstrip("/")
token = params.get("token") or ""

API_BASE = f"{host}/api" if host else ""

HEADERS = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "sophon-home-assistant-skill",
}


def request(method, path, data=None, query=None):
    """Make an authenticated request to the Home Assistant API. Returns parsed JSON (or None)."""
    url = f"{API_BASE}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        raise RuntimeError(f"Home Assistant API error {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Home Assistant at {host}: {e.reason}") from e


def state_summary(entity):
    attrs = entity.get("attributes") or {}
    return {
        "entity_id": entity.get("entity_id"),
        "state": entity.get("state"),
        "friendly_name": attrs.get("friendly_name"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_states():
    result = request("GET", "/states")
    states = [state_summary(e) for e in (result or [])]
    print(json.dumps({"count": len(states), "states": states}))


def get_state():
    entity_id = params.get("entityId")
    if not entity_id:
        raise ValueError("entityId required")
    result = request("GET", f"/states/{urllib.parse.quote(str(entity_id), safe='')}")
    print(json.dumps(result if result is not None else {}))


def list_services():
    result = request("GET", "/services")
    domains = [{
        "domain": d.get("domain"),
        "services": sorted((d.get("services") or {}).keys()),
    } for d in (result or [])]
    print(json.dumps({"count": len(domains), "domains": domains}))


def call_service():
    domain = params.get("domain")
    service = params.get("service")
    if not domain or not service:
        raise ValueError("domain and service required")
    payload = {}
    entity_id = params.get("entityId")
    if entity_id:
        payload["entity_id"] = entity_id
    extra = params.get("data")
    if isinstance(extra, dict):
        payload.update(extra)
    result = request(
        "POST",
        f"/services/{urllib.parse.quote(str(domain), safe='')}/{urllib.parse.quote(str(service), safe='')}",
        data=payload,
    )
    changed = [state_summary(e) for e in (result or []) if isinstance(e, dict)]
    print(json.dumps({
        "domain": domain,
        "service": service,
        "changedCount": len(changed),
        "changed": changed,
    }))


def get_history():
    entity_id = params.get("entityId")
    if not entity_id:
        raise ValueError("entityId required")
    try:
        hours = max(1, int(params.get("hours", 24)))
    except (TypeError, ValueError):
        hours = 24
    start = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    start_iso = start.replace(microsecond=0).isoformat()
    result = request(
        "GET",
        f"/history/period/{urllib.parse.quote(start_iso, safe='')}",
        query={
            "filter_entity_id": entity_id,
            "minimal_response": "true",
        },
    )
    # HA returns a list of lists (one inner list per entity).
    series = []
    for group in (result or []):
        for point in group:
            series.append({
                "state": point.get("state"),
                "last_changed": point.get("last_changed"),
                "last_updated": point.get("last_updated"),
            })
    print(json.dumps({
        "entity_id": entity_id,
        "hours": hours,
        "count": len(series),
        "history": series,
    }))


HANDLERS = {
    "ha.list_states": list_states,
    "ha.get_state": get_state,
    "ha.list_services": list_services,
    "ha.call_service": call_service,
    "ha.get_history": get_history,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not host:
        print(json.dumps({"error": "host required (configure the Home Assistant connection)"}))
    elif not token:
        print(json.dumps({"error": "Missing Home Assistant credential: connect the Home Assistant integration first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
