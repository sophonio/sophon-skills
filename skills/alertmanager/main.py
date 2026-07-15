"""Prometheus Alertmanager integration skill — talks to the Alertmanager v2 REST API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (host, token, username, password).

Auth is usually not required for a plain Alertmanager server. For proxied/authenticated setups an
optional bearer token is sent as `Authorization: Bearer ...`; if no token is set but a username and
password are provided, HTTP basic auth is used instead.
"""

import base64
import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
host = (params.get("host") or "").rstrip("/")
token = params.get("token") or ""
username = params.get("username") or ""
password = params.get("password") or ""

API_BASE = f"{host}/api/v2" if host else ""

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "sophon-alertmanager-skill",
}
if token:
    HEADERS["Authorization"] = f"Bearer {token}"
elif username and password:
    raw = f"{username}:{password}".encode()
    HEADERS["Authorization"] = "Basic " + base64.b64encode(raw).decode()


def request(method, path, data=None, query=None):
    """Make a request to the Alertmanager API. Returns parsed JSON (or None for empty bodies)."""
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
        raise RuntimeError(f"Alertmanager API error {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Alertmanager at {host}: {e.reason}") from e


def as_bool(value, default):
    """Coerce a param that may arrive as a real bool or a string into a bool."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def alert_summary(a):
    status = a.get("status") or {}
    return {
        "labels": a.get("labels"),
        "annotations": a.get("annotations"),
        "state": status.get("state"),
        "silencedBy": status.get("silencedBy"),
        "inhibitedBy": status.get("inhibitedBy"),
        "activeAt": a.get("startsAt"),
        "endsAt": a.get("endsAt"),
        "generatorURL": a.get("generatorURL"),
        "fingerprint": a.get("fingerprint"),
    }


def silence_summary(s):
    status = s.get("status") or {}
    return {
        "id": s.get("id"),
        "state": status.get("state"),
        "matchers": s.get("matchers"),
        "startsAt": s.get("startsAt"),
        "endsAt": s.get("endsAt"),
        "createdBy": s.get("createdBy"),
        "comment": s.get("comment"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_alerts():
    data = request("GET", "/alerts", query={
        "active": str(as_bool(params.get("active"), True)).lower(),
        "silenced": str(as_bool(params.get("silenced"), False)).lower(),
        "inhibited": str(as_bool(params.get("inhibited"), False)).lower(),
    })
    alerts = [alert_summary(a) for a in (data or [])]
    print(json.dumps({"count": len(alerts), "alerts": alerts}))


def list_silences():
    data = request("GET", "/silences")
    silences = [silence_summary(s) for s in (data or [])]
    print(json.dumps({"count": len(silences), "silences": silences}))


def get_status():
    data = request("GET", "/status")
    print(json.dumps(data if data is not None else {}))


def create_silence():
    matchers = params.get("matchers")
    if not isinstance(matchers, list) or not matchers:
        raise ValueError("matchers required (a non-empty array of {name, value, isRegex})")
    payload_matchers = []
    for m in matchers:
        if not isinstance(m, dict) or not m.get("name") or "value" not in m:
            raise ValueError("each matcher needs a name and value")
        payload_matchers.append({
            "name": m.get("name"),
            "value": m.get("value"),
            "isRegex": as_bool(m.get("isRegex"), False),
        })
    for key in ("startsAt", "endsAt", "createdBy", "comment"):
        if not params.get(key):
            raise ValueError(f"{key} required")
    payload = {
        "matchers": payload_matchers,
        "startsAt": params.get("startsAt"),
        "endsAt": params.get("endsAt"),
        "createdBy": params.get("createdBy"),
        "comment": params.get("comment"),
    }
    result = request("POST", "/silences", data=payload)
    print(json.dumps({"silenceId": (result or {}).get("silenceID"), "status": "created"}))


def expire_silence():
    silence_id = params.get("silenceId")
    if not silence_id:
        raise ValueError("silenceId required")
    request("DELETE", f"/silence/{urllib.parse.quote(str(silence_id), safe='')}")
    print(json.dumps({"silenceId": silence_id, "status": "expired"}))


HANDLERS = {
    "alertmanager.list_alerts": list_alerts,
    "alertmanager.list_silences": list_silences,
    "alertmanager.get_status": get_status,
    "alertmanager.create_silence": create_silence,
    "alertmanager.expire_silence": expire_silence,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not host:
        print(json.dumps({"error": "host required (configure the Alertmanager connection)"}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
