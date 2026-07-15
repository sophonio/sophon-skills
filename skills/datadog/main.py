"""Datadog integration skill — talks to the Datadog REST API (v1) with an API key + Application key.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential fields (apiKey, appKey, site).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
api_key = params.get("apiKey", "")
app_key = params.get("appKey", "")
site = (params.get("site") or "datadoghq.com").strip().rstrip("/")
base = f"https://api.{site}"

HEADERS = {
    "DD-API-KEY": api_key,
    "DD-APPLICATION-KEY": app_key,
    "Accept": "application/json",
    "User-Agent": "sophon-datadog-skill",
    "Content-Type": "application/json",
}


def request(method, path, data=None, query=None):
    """Make an authenticated request to the Datadog API. Returns parsed JSON (or None for 204)."""
    url = f"{base}{path}"
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
        raise RuntimeError(f"Datadog API error {e.code}: {detail}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def monitor_summary(mon):
    return {
        "id": mon.get("id"),
        "name": mon.get("name"),
        "overall_state": mon.get("overall_state"),
        "type": mon.get("type"),
    }


# --- Tool handlers ---------------------------------------------------------

def query_metrics():
    query = params.get("query")
    if not query:
        raise ValueError("query is required")
    result = request("GET", "/api/v1/query", query={
        "query": query,
        "from": params.get("from"),
        "to": params.get("to"),
    })
    print(json.dumps(result))


def list_monitors():
    query = {"page_size": clamp(params.get("limit", 50), 50, 1000)}
    if params.get("name"):
        query["name"] = params["name"]
    if params.get("tags"):
        query["monitor_tags"] = params["tags"]
    result = request("GET", "/api/v1/monitor", query=query)
    monitors = [monitor_summary(m) for m in (result or [])]
    print(json.dumps({"count": len(monitors), "monitors": monitors}))


def get_monitor():
    monitor_id = int(params.get("monitorId"))
    mon = request("GET", f"/api/v1/monitor/{monitor_id}")
    data = monitor_summary(mon)
    data["message"] = mon.get("message")
    data["query"] = mon.get("query")
    data["tags"] = mon.get("tags")
    print(json.dumps(data))


def mute_monitor():
    monitor_id = int(params.get("monitorId"))
    payload = {}
    if params.get("end") is not None:
        payload["end"] = int(params["end"])
    mon = request("POST", f"/api/v1/monitor/{monitor_id}/mute", data=payload)
    print(json.dumps(monitor_summary(mon)))


def unmute_monitor():
    monitor_id = int(params.get("monitorId"))
    mon = request("POST", f"/api/v1/monitor/{monitor_id}/unmute")
    print(json.dumps(monitor_summary(mon)))


HANDLERS = {
    "datadog.query_metrics": query_metrics,
    "datadog.list_monitors": list_monitors,
    "datadog.get_monitor": get_monitor,
    "datadog.mute_monitor": mute_monitor,
    "datadog.unmute_monitor": unmute_monitor,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not api_key or not app_key:
        print(json.dumps({"error": "Missing Datadog credentials: connect the Datadog integration first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
