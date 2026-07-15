"""Prometheus integration skill — queries the Prometheus HTTP API (/api/v1).

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (host, token, username, password).

Auth is usually not required for a plain Prometheus server. For proxied/authenticated setups an
optional bearer token is sent as `Authorization: Bearer ...`; if no token is set but a username and
password are provided, HTTP basic auth is used instead.

Prometheus wraps every response as {"status": "success"|"error", "data": ...}. When status is not
"success" we surface the error as {"error": ...}.
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

API_BASE = f"{host}/api/v1" if host else ""

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "sophon-prometheus-skill",
}
if token:
    HEADERS["Authorization"] = f"Bearer {token}"
elif username and password:
    raw = f"{username}:{password}".encode()
    HEADERS["Authorization"] = "Basic " + base64.b64encode(raw).decode()


class PromError(Exception):
    """Raised when the Prometheus envelope reports status != success."""


def request(path, query=None):
    """GET the Prometheus API and return the parsed JSON envelope."""
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
            raise RuntimeError(f"Prometheus API error {e.code}: {detail}") from e
        # Prometheus returns a JSON error envelope even on 4xx.
        if isinstance(parsed, dict) and parsed.get("status") == "error":
            raise PromError(parsed.get("error") or f"HTTP {e.code}")
        raise RuntimeError(f"Prometheus API error {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Prometheus at {host}: {e.reason}") from e


def unwrap(envelope):
    """Return the `data` from a Prometheus envelope, or raise PromError on failure."""
    if not isinstance(envelope, dict):
        raise RuntimeError("Unexpected Prometheus response")
    if envelope.get("status") != "success":
        raise PromError(envelope.get("error") or "Prometheus request failed")
    return envelope.get("data")


# --- Tool handlers ---------------------------------------------------------

def query():
    q = params.get("query")
    if not q:
        raise ValueError("query required")
    data = unwrap(request("/query", query={"query": q, "time": params.get("time")}))
    print(json.dumps(data if data is not None else {}))


def query_range():
    q = params.get("query")
    if not q:
        raise ValueError("query required")
    for key in ("start", "end", "step"):
        if not params.get(key):
            raise ValueError(f"{key} required")
    data = unwrap(request("/query_range", query={
        "query": q,
        "start": params.get("start"),
        "end": params.get("end"),
        "step": params.get("step"),
    }))
    print(json.dumps(data if data is not None else {}))


def list_alerts():
    data = unwrap(request("/alerts")) or {}
    alerts = [{
        "state": a.get("state"),
        "labels": a.get("labels"),
        "annotations": a.get("annotations"),
        "activeAt": a.get("activeAt"),
        "value": a.get("value"),
    } for a in data.get("alerts", [])]
    print(json.dumps({"count": len(alerts), "alerts": alerts}))


def list_targets():
    data = unwrap(request("/targets")) or {}
    targets = [{
        "job": (t.get("labels") or {}).get("job"),
        "instance": (t.get("labels") or {}).get("instance"),
        "health": t.get("health"),
        "scrapeUrl": t.get("scrapeUrl"),
        "lastScrape": t.get("lastScrape"),
        "lastError": t.get("lastError"),
    } for t in data.get("activeTargets", [])]
    print(json.dumps({"count": len(targets), "targets": targets}))


def label_values():
    label = params.get("label")
    if not label:
        raise ValueError("label required")
    data = unwrap(request(f"/label/{urllib.parse.quote(str(label), safe='')}/values"))
    values = data or []
    print(json.dumps({"label": label, "count": len(values), "values": values}))


HANDLERS = {
    "prometheus.query": query,
    "prometheus.query_range": query_range,
    "prometheus.list_alerts": list_alerts,
    "prometheus.list_targets": list_targets,
    "prometheus.label_values": label_values,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not host:
        print(json.dumps({"error": "host required (configure the Prometheus connection)"}))
    else:
        handler()
except PromError as e:
    print(json.dumps({"error": str(e)}))
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
