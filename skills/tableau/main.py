"""Tableau integration skill — workbooks, views, data sources, view data, and extract
refreshes via the Tableau REST API (version 3.23, Tableau Cloud and Server 2024.2+).

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (baseUrl, siteContentUrl, patName, patSecret).

Auth is a two-step Personal Access Token exchange: POST /api/3.23/auth/signin with the PAT name
and secret returns a short-lived session token (sent as X-Tableau-Auth on every call) plus the
site id that is threaded into every URL path. Sandbox runs are fresh, so the token is minted per
invocation. siteContentUrl is "" for the default site on Tableau Server.
"""

import csv
import io
import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("baseUrl") or "").rstrip("/")
site_content_url = params.get("siteContentUrl") or ""
pat_name = params.get("patName") or ""
pat_secret = params.get("patSecret") or ""

API_VERSION = "3.23"
USER_AGENT = "sophon-tableau-skill"


def seg(value, name):
    """URL-quote a params-derived path segment; reject empty/dot segments outright."""
    s = str(value)
    if not s or s in (".", ".."):
        raise ValueError(f"Invalid {name}: {s!r}")
    return urllib.parse.quote(s, safe="")


def parse_error(e):
    """Extract a friendly message from a Tableau JSON error body {"error": {...}}."""
    detail = e.read().decode() if e.fp else ""
    try:
        parsed = json.loads(detail)
        info = parsed.get("error") or {}
        summary = info.get("summary")
        det = info.get("detail")
        if summary and det:
            msg = f"{summary}: {det}"
        elif summary or det:
            msg = summary or det
        elif info.get("code"):
            msg = f"code {info.get('code')}"
        else:
            msg = detail
    except (ValueError, TypeError):
        msg = detail
    if e.code == 429:
        retry_after = e.headers.get("Retry-After") if e.headers else None
        if retry_after:
            msg = f"{msg} (retry after {retry_after}s)".strip()
    return msg


def sign_in():
    """Exchange the PAT for a session token and site id (POST /auth/signin)."""
    url = f"{base_url}/api/{API_VERSION}/auth/signin"
    payload = {
        "credentials": {
            "personalAccessTokenName": pat_name,
            "personalAccessTokenSecret": pat_secret,
            "site": {"contentUrl": site_content_url},
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Tableau API error {e.code}: {parse_error(e)}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Tableau: {e.reason}") from e
    creds = data.get("credentials") or {}
    token = creds.get("token")
    site_id = (creds.get("site") or {}).get("id")
    if not token or not site_id:
        raise RuntimeError("Tableau sign-in response did not include a session token and site id")
    return token, site_id


def request(method, path, token, site_id, data=None, query=None, accept="application/json"):
    """Authenticated site-scoped request. Returns parsed JSON, raw text for CSV, None if empty."""
    url = (f"{base_url}/api/{API_VERSION}/sites/"
           f"{urllib.parse.quote(str(site_id), safe='')}{path}")
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "X-Tableau-Auth": token,
        "Accept": accept,
        "User-Agent": USER_AGENT,
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Tableau API error {e.code}: {parse_error(e)}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Tableau: {e.reason}") from e
    if accept == "text/csv":
        return raw
    return json.loads(raw) if raw else None


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def workbook_summary(wb):
    return {
        "id": wb.get("id"),
        "name": wb.get("name"),
        "project": (wb.get("project") or {}).get("name"),
        "owner": (wb.get("owner") or {}).get("name"),
        "updatedAt": wb.get("updatedAt"),
        "webpageUrl": wb.get("webpageUrl"),
    }


def view_summary(v):
    return {
        "id": v.get("id"),
        "name": v.get("name"),
        "contentUrl": v.get("contentUrl"),
        "workbookId": (v.get("workbook") or {}).get("id"),
    }


def datasource_summary(d):
    return {
        "id": d.get("id"),
        "name": d.get("name"),
        "type": d.get("type"),
        "project": (d.get("project") or {}).get("name"),
        "updatedAt": d.get("updatedAt"),
    }


def job_summary(j):
    return {
        "id": j.get("id"),
        "type": j.get("type") or j.get("jobType"),
        "status": j.get("status"),
        "createdAt": j.get("createdAt"),
    }


def _items(result, plural, singular):
    container = (result or {}).get(plural) or {}
    items = container.get(singular) or []
    return items if isinstance(items, list) else [items]


# --- Tool handlers ---------------------------------------------------------

def list_workbooks():
    limit = clamp(params.get("limit", 25), 25, 100)
    token, site_id = sign_in()
    result = request("GET", "/workbooks", token, site_id, query={"pageSize": limit})
    workbooks = [workbook_summary(w) for w in _items(result, "workbooks", "workbook")]
    print(json.dumps({"count": len(workbooks), "workbooks": workbooks}))


def list_views():
    limit = clamp(params.get("limit", 25), 25, 100)
    workbook_id = params.get("workbookId")
    if workbook_id:
        path = f"/workbooks/{seg(workbook_id, 'workbookId')}/views"
    else:
        path = "/views"
    token, site_id = sign_in()
    result = request("GET", path, token, site_id, query={"pageSize": limit})
    views = [view_summary(v) for v in _items(result, "views", "view")]
    print(json.dumps({"count": len(views), "views": views}))


def list_datasources():
    limit = clamp(params.get("limit", 25), 25, 100)
    token, site_id = sign_in()
    result = request("GET", "/datasources", token, site_id, query={"pageSize": limit})
    datasources = [datasource_summary(d) for d in _items(result, "datasources", "datasource")]
    print(json.dumps({"count": len(datasources), "datasources": datasources}))


def get_view_data():
    view_id = params.get("viewId")
    if not view_id:
        raise ValueError("viewId required")
    path = f"/views/{seg(view_id, 'viewId')}/data"
    max_rows = clamp(params.get("maxRows", 200), 200, 1000)
    token, site_id = sign_in()
    text = request("GET", path, token, site_id, accept="text/csv")
    reader = csv.reader(io.StringIO(text or ""))
    columns = next(reader, None) or []
    rows = []
    truncated = False
    for record in reader:
        if not record:
            continue
        if len(rows) >= max_rows:
            truncated = True
            break
        rows.append({(columns[i] if i < len(columns) else f"col{i}"): record[i]
                     for i in range(len(record))})
    print(json.dumps({"columns": columns, "count": len(rows), "rows": rows,
                      "truncated": truncated}))


def search_content():
    query_text = params.get("query")
    if not query_text:
        raise ValueError("query required")
    limit = clamp(params.get("limit", 25), 25, 100)
    needle = str(query_text).lower()
    # The name field on Query Workbooks/Views/Data Sources only supports eq/in — the has
    # (substring) operator is reserved for Query Jobs — so substring matching is done
    # client-side over the first page (up to 100 items) of each content type.
    page = {"pageSize": 100}

    def matching(items):
        hits = [i for i in items if needle in str(i.get("name") or "").lower()]
        return hits[:limit]

    token, site_id = sign_in()
    wb_result = request("GET", "/workbooks", token, site_id, query=page)
    view_result = request("GET", "/views", token, site_id, query=page)
    ds_result = request("GET", "/datasources", token, site_id, query=page)
    print(json.dumps({
        "workbooks": [workbook_summary(w)
                      for w in matching(_items(wb_result, "workbooks", "workbook"))],
        "views": [view_summary(v) for v in matching(_items(view_result, "views", "view"))],
        "datasources": [datasource_summary(d)
                        for d in matching(_items(ds_result, "datasources", "datasource"))],
    }))


def list_jobs():
    limit = clamp(params.get("limit", 25), 25, 100)
    token, site_id = sign_in()
    result = request("GET", "/jobs", token, site_id, query={"pageSize": limit})
    items = _items(result, "backgroundJobs", "backgroundJob") or _items(result, "jobs", "job")
    jobs = [job_summary(j) for j in items]
    print(json.dumps({"count": len(jobs), "jobs": jobs}))


def refresh_datasource():
    datasource_id = params.get("datasourceId")
    if not datasource_id:
        raise ValueError("datasourceId required")
    path = f"/datasources/{seg(datasource_id, 'datasourceId')}/refresh"
    token, site_id = sign_in()
    result = request("POST", path, token, site_id, data={})
    job = (result or {}).get("job") or {}
    print(json.dumps({
        "refreshRequested": True,
        "refreshType": "full",
        "datasourceId": datasource_id,
        "jobId": job.get("id"),
        "jobType": job.get("type") or job.get("jobType"),
    }))


HANDLERS = {
    "tableau.list_workbooks": list_workbooks,
    "tableau.list_views": list_views,
    "tableau.list_datasources": list_datasources,
    "tableau.get_view_data": get_view_data,
    "tableau.search_content": search_content,
    "tableau.list_jobs": list_jobs,
    "tableau.refresh_datasource": refresh_datasource,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and pat_name and pat_secret):
        print(json.dumps({"error": "Missing Tableau credentials: connect the Tableau integration first (baseUrl, patName, patSecret; siteContentUrl is optional and empty for the default site on Tableau Server)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
