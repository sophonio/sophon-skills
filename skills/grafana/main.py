"""Grafana integration skill — talks to the Grafana HTTP API with a service-account token.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential fields (host, token).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
token = params.get("token", "")
base = (params.get("host") or "").rstrip("/")

HEADERS = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "User-Agent": "sophon-grafana-skill",
    "Content-Type": "application/json",
}


def request(method, path, data=None, query=None):
    """Make an authenticated request to the Grafana API. Returns parsed JSON (or None for 204)."""
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
        raise RuntimeError(f"Grafana API error {e.code}: {detail}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def require(key):
    value = params.get(key)
    if value in (None, ""):
        raise ValueError(f"Missing required parameter: {key}")
    return value


def dashboard_hit(hit):
    return {
        "uid": hit.get("uid"),
        "title": hit.get("title"),
        "type": hit.get("type"),
        "url": hit.get("url"),
        "folderTitle": hit.get("folderTitle"),
        "tags": hit.get("tags"),
    }


def datasource_summary(ds):
    return {
        "id": ds.get("id"),
        "uid": ds.get("uid"),
        "name": ds.get("name"),
        "type": ds.get("type"),
    }


def alert_rule_summary(rule):
    return {
        "uid": rule.get("uid"),
        "title": rule.get("title"),
        "folderUID": rule.get("folderUID"),
        "ruleGroup": rule.get("ruleGroup"),
        "condition": rule.get("condition"),
        "noDataState": rule.get("noDataState"),
        "execErrState": rule.get("execErrState"),
        "for": rule.get("for"),
    }


# --- Tool handlers ---------------------------------------------------------

def search_dashboards():
    result = request("GET", "/api/search", query={
        "query": params.get("query"),
        "type": "dash-db",
        "limit": clamp(params.get("limit", 30), 30, 100),
    })
    hits = [dashboard_hit(h) for h in (result or [])]
    print(json.dumps({"count": len(hits), "dashboards": hits}))


def get_dashboard():
    uid = require("uid")
    result = request("GET", f"/api/dashboards/uid/{urllib.parse.quote(str(uid))}")
    dashboard = (result or {}).get("dashboard") or {}
    meta = (result or {}).get("meta") or {}
    print(json.dumps({
        "uid": dashboard.get("uid"),
        "title": dashboard.get("title"),
        "tags": dashboard.get("tags"),
        "version": dashboard.get("version"),
        "folderTitle": meta.get("folderTitle"),
        "url": meta.get("url"),
        "panelCount": len(dashboard.get("panels", []) or []),
        "dashboard": dashboard,
    }))


def list_datasources():
    result = request("GET", "/api/datasources")
    sources = [datasource_summary(d) for d in (result or [])]
    print(json.dumps({"count": len(sources), "datasources": sources}))


def list_alert_rules():
    result = request("GET", "/api/v1/provisioning/alert-rules")
    rules = [alert_rule_summary(r) for r in (result or [])]
    print(json.dumps({"count": len(rules), "alertRules": rules}))


def create_annotation():
    text = require("text")
    payload = {"text": text}
    if params.get("dashboardUid"):
        payload["dashboardUID"] = params["dashboardUid"]
    if params.get("panelId") is not None:
        try:
            payload["panelId"] = int(params["panelId"])
        except (TypeError, ValueError):
            raise ValueError("panelId must be an integer")
    if params.get("tags"):
        payload["tags"] = params["tags"]
    if params.get("time") is not None:
        try:
            payload["time"] = int(params["time"])
        except (TypeError, ValueError):
            raise ValueError("time must be an epoch time in milliseconds")
    result = request("POST", "/api/annotations", data=payload)
    print(json.dumps({
        "id": (result or {}).get("id"),
        "message": (result or {}).get("message"),
    }))


HANDLERS = {
    "grafana.search_dashboards": search_dashboards,
    "grafana.get_dashboard": get_dashboard,
    "grafana.list_datasources": list_datasources,
    "grafana.list_alert_rules": list_alert_rules,
    "grafana.create_annotation": create_annotation,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not base:
        print(json.dumps({"error": "Missing Grafana URL: set the host on the Grafana integration."}))
    elif not token:
        print(json.dumps({"error": "Missing Grafana credential: connect the Grafana integration first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
