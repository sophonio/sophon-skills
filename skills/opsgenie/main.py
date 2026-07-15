"""Opsgenie integration skill — talks to the Opsgenie Alert API v2 with an API key.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential fields (apiKey, region).

The base host depends on the account region: EU accounts use https://api.eu.opsgenie.com, all
others use https://api.opsgenie.com. Requests authenticate with the "GenieKey <apiKey>" header.
Opsgenie wraps every response as {"data": ..., "requestId": ..., ...}.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
api_key = params.get("apiKey", "")
region = (params.get("region") or "us").strip().lower()

API_BASE = "https://api.eu.opsgenie.com" if region == "eu" else "https://api.opsgenie.com"

HEADERS = {
    "Authorization": f"GenieKey {api_key}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "sophon-opsgenie-skill",
}


def request(method, path, data=None, query=None):
    """Make an authenticated request to the Opsgenie API. Returns parsed JSON (or {} for empty)."""
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
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
        except (ValueError, TypeError):
            raise RuntimeError(f"Opsgenie API error {e.code}: {detail}") from e
        if isinstance(parsed, dict) and parsed.get("message"):
            raise RuntimeError(f"Opsgenie API error {e.code}: {parsed.get('message')}")
        raise RuntimeError(f"Opsgenie API error {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Opsgenie: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def alert_summary(alert):
    return {
        "id": alert.get("id"),
        "tinyId": alert.get("tinyId"),
        "message": alert.get("message"),
        "status": alert.get("status"),
        "acknowledged": alert.get("acknowledged"),
        "priority": alert.get("priority"),
        "owner": alert.get("owner"),
        "tags": alert.get("tags"),
        "count": alert.get("count"),
        "createdAt": alert.get("createdAt"),
        "updatedAt": alert.get("updatedAt"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_alerts():
    result = request("GET", "/v2/alerts", query={
        "query": params.get("query"),
        "limit": clamp(params.get("limit", 20), 20, 100),
    })
    alerts = [alert_summary(a) for a in (result.get("data") or [])]
    print(json.dumps({"count": len(alerts), "alerts": alerts}))


def get_alert():
    alert_id = params.get("alertId")
    if not alert_id:
        raise ValueError("alertId required")
    result = request("GET", f"/v2/alerts/{urllib.parse.quote(str(alert_id), safe='')}")
    data = result.get("data") or {}
    summary = alert_summary(data)
    summary["description"] = data.get("description")
    summary["responders"] = data.get("responders")
    summary["source"] = data.get("source")
    print(json.dumps(summary))


def acknowledge_alert():
    alert_id = params.get("alertId")
    if not alert_id:
        raise ValueError("alertId required")
    payload = {}
    if params.get("note"):
        payload["note"] = params["note"]
    result = request("POST", f"/v2/alerts/{urllib.parse.quote(str(alert_id), safe='')}/acknowledge",
                     data=payload)
    print(json.dumps({"status": "requested", "result": result.get("result"),
                      "requestId": result.get("requestId")}))


def close_alert():
    alert_id = params.get("alertId")
    if not alert_id:
        raise ValueError("alertId required")
    payload = {}
    if params.get("note"):
        payload["note"] = params["note"]
    result = request("POST", f"/v2/alerts/{urllib.parse.quote(str(alert_id), safe='')}/close",
                     data=payload)
    print(json.dumps({"status": "requested", "result": result.get("result"),
                      "requestId": result.get("requestId")}))


def create_alert():
    message = params.get("message")
    if not message:
        raise ValueError("message required")
    payload = {"message": message}
    if params.get("description"):
        payload["description"] = params["description"]
    if params.get("priority"):
        payload["priority"] = params["priority"]
    if params.get("tags"):
        payload["tags"] = params["tags"]
    result = request("POST", "/v2/alerts", data=payload)
    print(json.dumps({"status": "requested", "result": result.get("result"),
                      "requestId": result.get("requestId")}))


def who_is_on_call():
    schedule_id = params.get("scheduleId")
    if not schedule_id:
        raise ValueError("scheduleId required")
    result = request("GET",
                     f"/v2/schedules/{urllib.parse.quote(str(schedule_id), safe='')}/on-calls")
    data = result.get("data") or {}
    participants = data.get("onCallParticipants") or []
    print(json.dumps({
        "scheduleId": data.get("_parent", {}).get("id") if isinstance(data.get("_parent"), dict) else schedule_id,
        "scheduleName": data.get("_parent", {}).get("name") if isinstance(data.get("_parent"), dict) else None,
        "count": len(participants),
        "onCall": participants,
    }))


HANDLERS = {
    "opsgenie.list_alerts": list_alerts,
    "opsgenie.get_alert": get_alert,
    "opsgenie.acknowledge_alert": acknowledge_alert,
    "opsgenie.close_alert": close_alert,
    "opsgenie.create_alert": create_alert,
    "opsgenie.who_is_on_call": who_is_on_call,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not api_key:
        print(json.dumps({"error": "Missing Opsgenie credential: connect the Opsgenie integration first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
