"""Power BI integration skill — workspaces, datasets, reports, refreshes via the Power BI REST API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (tenantId, clientId, clientSecret).

Auth is app-only (OAuth2 client-credentials) with a Microsoft Entra service principal: we POST to
the tenant token endpoint with scope https://analysis.windows.net/powerbi/api/.default, then call
https://api.powerbi.com/v1.0/myorg with a Bearer token. The service principal must be allowed to
call Fabric public APIs (tenant setting) and be a Member/Admin of each target workspace; it cannot
access My Workspace or RLS/SSO-enabled datasets.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
tenant_id = params.get("tenantId") or ""
client_id = params.get("clientId") or ""
client_secret = params.get("clientSecret") or ""

API_BASE = "https://api.powerbi.com/v1.0/myorg"


def get_token():
    """Obtain an app-only access token via the client-credentials grant."""
    url = f"https://login.microsoftonline.com/{urllib.parse.quote(tenant_id, safe='')}/oauth2/v2.0/token"
    form = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://analysis.windows.net/powerbi/api/.default",
    }).encode()
    req = urllib.request.Request(
        url,
        data=form,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "sophon-powerbi-skill",
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
        raise RuntimeError(f"Could not reach Microsoft login endpoint: {e.reason}") from e
    token = data.get("access_token")
    if not token:
        raise RuntimeError("No access_token in token response")
    return token


def parse_error_body(detail):
    """Extract a friendly message from a Power BI error body (including error.pbi.error.details)."""
    try:
        parsed = json.loads(detail)
    except (ValueError, TypeError):
        return detail
    err = parsed.get("error")
    if not isinstance(err, dict):
        return detail
    msg = err.get("message") or err.get("code") or detail
    pbi = err.get("pbi.error")
    if isinstance(pbi, dict):
        parts = []
        for d in pbi.get("details") or []:
            value = ((d or {}).get("detail") or {}).get("value")
            if value:
                parts.append(str(value))
        if parts:
            msg = f"{msg}: {'; '.join(parts)}"
    return msg


def request(method, path, token, data=None, query=None):
    """Make an authenticated request to the Power BI REST API. Returns parsed JSON (or None for 202/204/empty)."""
    url = f"{API_BASE}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "sophon-powerbi-skill",
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
        msg = parse_error_body(detail)
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            if retry_after:
                msg = f"{msg} (rate limited; retry after {retry_after} seconds)".strip()
            else:
                msg = f"{msg} (rate limited)".strip()
        raise RuntimeError(f"Power BI API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach the Power BI API: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def require(key):
    value = params.get(key)
    if not value:
        raise ValueError(f"{key} required")
    return str(value)


def workspace_summary(ws):
    return {
        "id": ws.get("id"),
        "name": ws.get("name"),
        "isOnDedicatedCapacity": ws.get("isOnDedicatedCapacity"),
    }


def dataset_summary(ds):
    return {
        "id": ds.get("id"),
        "name": ds.get("name"),
        "configuredBy": ds.get("configuredBy"),
        "isRefreshable": ds.get("isRefreshable"),
    }


def report_summary(rp):
    return {
        "id": rp.get("id"),
        "name": rp.get("name"),
        "webUrl": rp.get("webUrl"),
        "datasetId": rp.get("datasetId"),
    }


def dashboard_summary(db):
    return {
        "id": db.get("id"),
        "displayName": db.get("displayName"),
    }


def tile_summary(tile):
    return {
        "id": tile.get("id"),
        "title": tile.get("title"),
        "reportId": tile.get("reportId"),
        "datasetId": tile.get("datasetId"),
    }


def refresh_summary(rf):
    exception = rf.get("serviceExceptionJson")
    if isinstance(exception, str) and len(exception) > 500:
        exception = exception[:500] + "... (truncated)"
    return {
        "status": rf.get("status"),
        "startTime": rf.get("startTime"),
        "endTime": rf.get("endTime"),
        "serviceExceptionJson": exception,
    }


# --- Tool handlers ---------------------------------------------------------

def list_workspaces():
    token = get_token()
    result = request("GET", "/groups", token)
    workspaces = [workspace_summary(w) for w in (result or {}).get("value", [])]
    print(json.dumps({"count": len(workspaces), "workspaces": workspaces}))


def list_datasets():
    token = get_token()
    workspace_id = require("workspaceId")
    result = request("GET", f"/groups/{urllib.parse.quote(workspace_id, safe='')}/datasets", token)
    datasets = [dataset_summary(d) for d in (result or {}).get("value", [])]
    print(json.dumps({"count": len(datasets), "datasets": datasets}))


def list_reports():
    token = get_token()
    workspace_id = require("workspaceId")
    result = request("GET", f"/groups/{urllib.parse.quote(workspace_id, safe='')}/reports", token)
    reports = [report_summary(r) for r in (result or {}).get("value", [])]
    print(json.dumps({"count": len(reports), "reports": reports}))


def list_dashboards():
    token = get_token()
    workspace_id = require("workspaceId")
    ws = urllib.parse.quote(workspace_id, safe='')
    dashboard_id = params.get("dashboardId")
    if dashboard_id:
        result = request(
            "GET",
            f"/groups/{ws}/dashboards/{urllib.parse.quote(str(dashboard_id), safe='')}/tiles",
            token,
        )
        tiles = [tile_summary(t) for t in (result or {}).get("value", [])]
        print(json.dumps({"dashboardId": dashboard_id, "count": len(tiles), "tiles": tiles}))
    else:
        result = request("GET", f"/groups/{ws}/dashboards", token)
        dashboards = [dashboard_summary(d) for d in (result or {}).get("value", [])]
        print(json.dumps({"count": len(dashboards), "dashboards": dashboards}))


def execute_dax():
    token = get_token()
    workspace_id = require("workspaceId")
    dataset_id = require("datasetId")
    dax = require("query")
    max_rows = clamp(params.get("maxRows", 100), 100, 1000)
    payload = {
        "queries": [{"query": dax}],
        "serializerSettings": {"includeNulls": True},
    }
    result = request(
        "POST",
        f"/groups/{urllib.parse.quote(workspace_id, safe='')}/datasets/{urllib.parse.quote(dataset_id, safe='')}/executeQueries",
        token,
        data=payload,
    )
    tables = ((result or {}).get("results") or [{}])[0].get("tables") or [{}]
    rows = tables[0].get("rows") or []
    truncated = len(rows) > max_rows
    print(json.dumps({
        "rowCount": len(rows),
        "truncated": truncated,
        "rows": rows[:max_rows],
    }))


def get_refresh_history():
    token = get_token()
    workspace_id = require("workspaceId")
    dataset_id = require("datasetId")
    top = clamp(params.get("limit", 10), 10, 100)
    result = request(
        "GET",
        f"/groups/{urllib.parse.quote(workspace_id, safe='')}/datasets/{urllib.parse.quote(dataset_id, safe='')}/refreshes",
        token,
        query={"$top": top},
    )
    refreshes = [refresh_summary(r) for r in (result or {}).get("value", [])]
    print(json.dumps({"count": len(refreshes), "refreshes": refreshes}))


def refresh_dataset():
    token = get_token()
    workspace_id = require("workspaceId")
    dataset_id = require("datasetId")
    request(
        "POST",
        f"/groups/{urllib.parse.quote(workspace_id, safe='')}/datasets/{urllib.parse.quote(dataset_id, safe='')}/refreshes",
        token,
        data={},
    )
    print(json.dumps({
        "workspaceId": workspace_id,
        "datasetId": dataset_id,
        "refreshRequested": True,
    }))


HANDLERS = {
    "powerbi.list_workspaces": list_workspaces,
    "powerbi.list_datasets": list_datasets,
    "powerbi.list_reports": list_reports,
    "powerbi.list_dashboards": list_dashboards,
    "powerbi.execute_dax": execute_dax,
    "powerbi.get_refresh_history": get_refresh_history,
    "powerbi.refresh_dataset": refresh_dataset,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (tenant_id and client_id and client_secret):
        print(json.dumps({"error": "Missing Power BI credentials: connect the Power BI integration first (tenantId, clientId, clientSecret)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
