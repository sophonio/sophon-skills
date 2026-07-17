"""MongoDB Atlas integration skill — control-plane operations via the Atlas Administration API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (clientId, clientSecret, projectId).

Auth is OAuth2 client-credentials via Atlas Service Accounts: we POST to
https://cloud.mongodb.com/api/oauth/token with HTTP Basic (clientId:clientSecret) to mint a
short-lived access token (~1 hour, no refresh token; minted fresh per invocation), then call
https://cloud.mongodb.com/api/atlas/v2 with a Bearer token and a pinned versioned Accept header.

Scope: control-plane/ops only (projects, clusters, alerts, metrics, events, database users).
The Atlas Data API (document CRUD) reached end-of-life in September 2025, so this skill
deliberately exposes no collection-data tools.
"""

import base64
import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
client_id = params.get("clientId") or ""
client_secret = params.get("clientSecret") or ""

TOKEN_URL = "https://cloud.mongodb.com/api/oauth/token"
API_BASE = "https://cloud.mongodb.com/api/atlas/v2"
ACCEPT = "application/vnd.atlas.2025-03-12+json"

DEFAULT_METRICS = [
    "PROCESS_CPU_USER",
    "CONNECTIONS",
    "OPCOUNTER_QUERY",
    "OPCOUNTER_INSERT",
    "OPCOUNTER_UPDATE",
    "OPCOUNTER_DELETE",
]


def get_token():
    """Mint a service-account access token via the OAuth2 client-credentials grant."""
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req = urllib.request.Request(
        TOKEN_URL,
        data=b"grant_type=client_credentials",
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "sophon-mongodb-atlas-skill",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
            msg = parsed.get("error_description") or parsed.get("error") or detail
        except (ValueError, TypeError):
            msg = detail
        raise RuntimeError(f"Token request failed ({e.code}): {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach MongoDB Atlas token endpoint: {e.reason}") from e
    token = data.get("access_token")
    if not token:
        raise RuntimeError("No access_token in token response")
    return token


def request(method, path, token, data=None, query=None):
    """Make an authenticated request to the Atlas Administration API v2.

    Returns parsed JSON (or None for 204/empty bodies).
    """
    url = f"{API_BASE}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean, doseq=True)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": ACCEPT,
        "User-Agent": "sophon-mongodb-atlas-skill",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        msg = detail
        error_code = ""
        try:
            parsed = json.loads(detail)
            error_code = parsed.get("errorCode") or ""
            msg = parsed.get("detail") or parsed.get("reason") or detail
            if error_code:
                msg = f"{error_code}: {msg}"
        except (ValueError, TypeError):
            pass
        if e.code == 403 and "ACCESS_LIST" in error_code.upper():
            msg += (" Hint: your organization requires an IP access list for the Atlas"
                    " Administration API. Add Sophon's egress IPs to this service account's"
                    " API access list, or relax the org setting 'Require IP Access List for"
                    " the Atlas Administration API'.")
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            if retry_after:
                msg += f" (Retry-After: {retry_after})"
        raise RuntimeError(f"Atlas API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach MongoDB Atlas: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def get_project_id():
    """Tool argument `projectId` falls back to the connection-card field (same flat key)."""
    project_id = params.get("projectId") or ""
    if not project_id:
        raise ValueError("projectId required: pass it as a tool argument or set a default "
                         "project ID on the MongoDB Atlas connection.")
    return urllib.parse.quote(str(project_id), safe="")


def project_summary(p):
    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "clusterCount": p.get("clusterCount"),
        "created": p.get("created"),
    }


def instance_size(cluster):
    """Best-effort instance size from replicationSpecs (dedicated/flex topologies)."""
    for spec in cluster.get("replicationSpecs") or []:
        for rc in spec.get("regionConfigs") or []:
            size = (rc.get("electableSpecs") or {}).get("instanceSize")
            if size:
                return size
    return (cluster.get("providerSettings") or {}).get("instanceSizeName")


def disk_size(cluster):
    """Best-effort disk size (GB): moved under replicationSpecs in API version 2024-08-05."""
    for spec in cluster.get("replicationSpecs") or []:
        for rc in spec.get("regionConfigs") or []:
            size = (rc.get("electableSpecs") or {}).get("diskSizeGB")
            if size is not None:
                return size
    return cluster.get("diskSizeGB")


def cluster_summary(c):
    return {
        "name": c.get("name"),
        "stateName": c.get("stateName"),
        "mongoDBVersion": c.get("mongoDBVersion"),
        "instanceSize": instance_size(c),
        "paused": c.get("paused"),
    }


def alert_summary(a):
    return {
        "id": a.get("id"),
        "eventTypeName": a.get("eventTypeName"),
        "status": a.get("status"),
        "created": a.get("created"),
        "metricName": a.get("metricName"),
    }


def event_summary(ev):
    return {
        "id": ev.get("id"),
        "eventTypeName": ev.get("eventTypeName"),
        "created": ev.get("created"),
        "actor": ev.get("username") or ev.get("publicKey"),
    }


def database_user_summary(u):
    # Never expose any password/credential material — only identity and grants.
    return {
        "username": u.get("username"),
        "authDatabase": u.get("databaseName"),
        "roles": [
            {"roleName": r.get("roleName"), "databaseName": r.get("databaseName")}
            for r in (u.get("roles") or [])
        ],
    }


def measurement_summary(m):
    points = [
        {"timestamp": p.get("timestamp"), "value": p.get("value")}
        for p in (m.get("dataPoints") or [])
        if p.get("value") is not None
    ][-60:]
    return {"name": m.get("name"), "units": m.get("units"), "points": points}


# --- Tool handlers ---------------------------------------------------------

def list_projects():
    token = get_token()
    limit = clamp(params.get("limit", 25), 25, 100)
    result = request("GET", "/groups", token, query={"itemsPerPage": limit})
    projects = [project_summary(p) for p in (result or {}).get("results", [])]
    print(json.dumps({"count": len(projects), "totalCount": (result or {}).get("totalCount"),
                      "projects": projects}))


def list_clusters():
    project_id = get_project_id()
    limit = clamp(params.get("limit", 25), 25, 100)
    token = get_token()
    result = request("GET", f"/groups/{project_id}/clusters", token,
                     query={"itemsPerPage": limit})
    clusters = [cluster_summary(c) for c in (result or {}).get("results", [])]
    print(json.dumps({"count": len(clusters), "totalCount": (result or {}).get("totalCount"),
                      "clusters": clusters}))


def get_cluster():
    project_id = get_project_id()
    name = params.get("clusterName")
    if not name:
        raise ValueError("clusterName required")
    token = get_token()
    c = request("GET", f"/groups/{project_id}/clusters/{urllib.parse.quote(str(name), safe='')}",
                token) or {}
    print(json.dumps({
        "id": c.get("id"),
        "name": c.get("name"),
        "stateName": c.get("stateName"),
        "clusterType": c.get("clusterType"),
        "mongoDBVersion": c.get("mongoDBVersion"),
        "mongoDBMajorVersion": c.get("mongoDBMajorVersion"),
        "instanceSize": instance_size(c),
        "paused": c.get("paused"),
        "backupEnabled": c.get("backupEnabled"),
        "diskSizeGB": disk_size(c),
        "createDate": c.get("createDate"),
        "connectionStringSrv": (c.get("connectionStrings") or {}).get("standardSrv"),
    }))


def list_alerts():
    project_id = get_project_id()
    limit = clamp(params.get("limit", 25), 25, 100)
    token = get_token()
    result = request("GET", f"/groups/{project_id}/alerts", token,
                     query={"status": "OPEN", "itemsPerPage": limit})
    alerts = [alert_summary(a) for a in (result or {}).get("results", [])]
    print(json.dumps({"count": len(alerts), "totalCount": (result or {}).get("totalCount"),
                      "alerts": alerts}))


def acknowledge_alert():
    project_id = get_project_id()
    alert_id = params.get("alertId")
    if not alert_id:
        raise ValueError("alertId required")
    until = params.get("acknowledgedUntil")
    if not until:
        raise ValueError("acknowledgedUntil required (ISO 8601 date-time, "
                         "e.g. 2026-07-18T00:00:00Z)")
    token = get_token()
    payload = {"acknowledgedUntil": until}
    if params.get("comment"):
        payload["acknowledgementComment"] = params["comment"]
    a = request("PATCH",
                f"/groups/{project_id}/alerts/{urllib.parse.quote(str(alert_id), safe='')}",
                token, data=payload) or {}
    print(json.dumps({
        "id": a.get("id"),
        "status": a.get("status"),
        "acknowledgedUntil": a.get("acknowledgedUntil"),
        "acknowledgementComment": a.get("acknowledgementComment"),
    }))


def get_process_metrics():
    project_id = get_project_id()
    process_id = params.get("processId")
    if not process_id:
        raise ValueError("processId required (host:port, e.g. "
                         "cluster0-shard-00-00.ab1cd.mongodb.net:27017 — see cluster processes)")
    metrics = params.get("metrics") or DEFAULT_METRICS
    granularity = params.get("granularity") or "PT1M"
    period = params.get("period") or "PT1H"
    token = get_token()
    result = request(
        "GET",
        f"/groups/{project_id}/processes/{urllib.parse.quote(str(process_id), safe='')}/measurements",
        token,
        query={"granularity": granularity, "period": period, "m": metrics},
    ) or {}
    measurements = [measurement_summary(m) for m in result.get("measurements") or []]
    print(json.dumps({
        "processId": result.get("processId") or process_id,
        "granularity": result.get("granularity") or granularity,
        "period": period,
        "count": len(measurements),
        "measurements": measurements,
    }))


def list_events():
    project_id = get_project_id()
    limit = clamp(params.get("limit", 25), 25, 100)
    token = get_token()
    result = request("GET", f"/groups/{project_id}/events", token,
                     query={"itemsPerPage": limit})
    events = [event_summary(ev) for ev in (result or {}).get("results", [])]
    print(json.dumps({"count": len(events), "totalCount": (result or {}).get("totalCount"),
                      "events": events}))


def list_database_users():
    project_id = get_project_id()
    limit = clamp(params.get("limit", 25), 25, 100)
    token = get_token()
    result = request("GET", f"/groups/{project_id}/databaseUsers", token,
                     query={"itemsPerPage": limit})
    users = [database_user_summary(u) for u in (result or {}).get("results", [])]
    print(json.dumps({"count": len(users), "totalCount": (result or {}).get("totalCount"),
                      "databaseUsers": users}))


HANDLERS = {
    "atlas.list_projects": list_projects,
    "atlas.list_clusters": list_clusters,
    "atlas.get_cluster": get_cluster,
    "atlas.list_alerts": list_alerts,
    "atlas.acknowledge_alert": acknowledge_alert,
    "atlas.get_process_metrics": get_process_metrics,
    "atlas.list_events": list_events,
    "atlas.list_database_users": list_database_users,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (client_id and client_secret):
        print(json.dumps({"error": "Missing MongoDB Atlas credentials: connect the MongoDB Atlas integration first (clientId, clientSecret)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
