"""Grafana Loki integration skill — queries the Loki HTTP API (/loki/api/v1) with LogQL.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (host, token, username, password, orgId).

Auth is usually not required for a plain Loki server. For proxied/authenticated setups an optional
bearer token is sent as `Authorization: Bearer ...`; if no token is set but a username and password
are provided, HTTP basic auth is used instead. Multi-tenant Loki reads the tenant from the
`X-Scope-OrgID` header, populated from the optional orgId field.

Loki wraps every response as {"status": "success", "data": {...}}. When status is not "success" we
surface the error as {"error": ...}.
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
org_id = params.get("orgId") or ""

API_BASE = f"{host}/loki/api/v1" if host else ""

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "sophon-loki-skill",
}
if token:
    HEADERS["Authorization"] = f"Bearer {token}"
elif username and password:
    raw = f"{username}:{password}".encode()
    HEADERS["Authorization"] = "Basic " + base64.b64encode(raw).decode()
if org_id:
    HEADERS["X-Scope-OrgID"] = org_id


class LokiError(Exception):
    """Raised when the Loki envelope reports status != success."""


def request(path, query=None):
    """GET the Loki API and return the parsed JSON envelope."""
    url = f"{API_BASE}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
        except (ValueError, TypeError):
            raise RuntimeError(f"Loki API error {e.code}: {detail}") from e
        if isinstance(parsed, dict) and parsed.get("status") == "error":
            raise LokiError(parsed.get("error") or parsed.get("message") or f"HTTP {e.code}")
        raise RuntimeError(f"Loki API error {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Loki at {host}: {e.reason}") from e


def unwrap(envelope):
    """Return the `data` from a Loki envelope, or raise LokiError on failure."""
    if not isinstance(envelope, dict):
        raise RuntimeError("Unexpected Loki response")
    if envelope.get("status") != "success":
        raise LokiError(envelope.get("error") or envelope.get("message") or "Loki request failed")
    return envelope.get("data")


def clamp(value, default):
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def trim_result(data):
    """Trim a Loki query result envelope's data into a compact structure.

    A result has {"resultType": "streams"|"matrix"|"vector", "result": [...]}. For streams each
    item is {"stream": {labels}, "values": [[ts, line], ...]}; for metric types each item is
    {"metric": {labels}, "values": [[ts, val], ...]} (or a single "value").
    """
    if not isinstance(data, dict):
        return {"resultType": None, "result": []}
    result_type = data.get("resultType")
    out = []
    for item in data.get("result", []) or []:
        entry = {}
        if "stream" in item:
            entry["labels"] = item.get("stream")
            entry["values"] = item.get("values", [])
        else:
            entry["labels"] = item.get("metric")
            if "values" in item:
                entry["values"] = item.get("values", [])
            if "value" in item:
                entry["value"] = item.get("value")
        out.append(entry)
    return {"resultType": result_type, "count": len(out), "result": out}


# --- Tool handlers ---------------------------------------------------------

def query():
    q = params.get("query")
    if not q:
        raise ValueError("query required")
    data = unwrap(request("/query", query={
        "query": q,
        "limit": clamp(params.get("limit", 100), 100),
        "time": params.get("time"),
    }))
    print(json.dumps(trim_result(data)))


def query_range():
    q = params.get("query")
    if not q:
        raise ValueError("query required")
    for key in ("start", "end"):
        if not params.get(key):
            raise ValueError(f"{key} required")
    data = unwrap(request("/query_range", query={
        "query": q,
        "start": params.get("start"),
        "end": params.get("end"),
        "limit": clamp(params.get("limit", 100), 100),
        "step": params.get("step"),
        "direction": params.get("direction"),
    }))
    print(json.dumps(trim_result(data)))


def list_labels():
    data = unwrap(request("/labels", query={
        "start": params.get("start"),
        "end": params.get("end"),
    }))
    labels = data or []
    print(json.dumps({"count": len(labels), "labels": labels}))


def label_values():
    label = params.get("label")
    if not label:
        raise ValueError("label required")
    path = f"/label/{urllib.parse.quote(str(label), safe='')}/values"
    data = unwrap(request(path, query={
        "start": params.get("start"),
        "end": params.get("end"),
    }))
    values = data or []
    print(json.dumps({"label": label, "count": len(values), "values": values}))


HANDLERS = {
    "loki.query": query,
    "loki.query_range": query_range,
    "loki.list_labels": list_labels,
    "loki.label_values": label_values,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not host:
        print(json.dumps({"error": "host required (configure the Loki connection)"}))
    else:
        handler()
except LokiError as e:
    print(json.dumps({"error": str(e)}))
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
