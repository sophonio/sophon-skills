"""Planner integration skill — Microsoft Planner (basic plans) via Microsoft Graph (app-only).

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (tenantId, clientId, clientSecret,
defaultGroupId).

Auth is app-only (OAuth2 client-credentials): we POST to the tenant token endpoint to obtain an
access token, then call Microsoft Graph as https://graph.microsoft.com/v1.0/... with a Bearer
token. Graph has no app-only "list all plans" endpoint, so plans are discovered through a
Microsoft 365 group (defaultGroupId, overridable per call via groupId).

Planner PATCH requests require optimistic concurrency: every PATCH carries an
"If-Match: <@odata.etag>" header with the object's CURRENT ETag. We GET the task first, PATCH
with If-Match, and on a 409/412 conflict re-GET once and retry before surfacing the error.

List tools return the first page of Graph results only (no @odata.nextLink following); Planner
collections are typically single-page.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
tenant_id = params.get("tenantId") or ""
client_id = params.get("clientId") or ""
client_secret = params.get("clientSecret") or ""
default_group_id = params.get("defaultGroupId") or ""

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

ASSIGNMENT = {"@odata.type": "#microsoft.graph.plannerAssignment", "orderHint": " !"}


class ApiError(RuntimeError):
    """Graph API error carrying the HTTP status for retry decisions."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def get_token():
    """Obtain an app-only access token via the client-credentials grant."""
    url = f"https://login.microsoftonline.com/{urllib.parse.quote(tenant_id, safe='')}/oauth2/v2.0/token"
    form = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
    }).encode()
    req = urllib.request.Request(
        url,
        data=form,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "sophon-planner-skill",
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


def request(method, path, token, data=None, query=None, headers=None):
    """Make an authenticated request to Microsoft Graph. Returns parsed JSON (or None for 204)."""
    url = f"{GRAPH_BASE}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    hdrs = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "sophon-planner-skill",
    }
    if body is not None:
        hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
            err = parsed.get("error") or {}
            if isinstance(err, dict):
                code = err.get("code")
                message = err.get("message")
                msg = f"{code}: {message}" if code and message else (message or code or detail)
            else:
                msg = str(err) or detail
        except (ValueError, TypeError):
            msg = detail
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            if retry_after:
                msg = f"{msg} (retry after {retry_after}s)" if msg else f"rate limited (retry after {retry_after}s)"
        raise ApiError(e.code, f"Graph API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Microsoft Graph: {e.reason}") from e


def seg(value, name):
    """Validate and URL-quote a params-derived path segment."""
    s = str(value if value is not None else "")
    if not s:
        raise ValueError(f"{name} required")
    if s in (".", ".."):
        raise ValueError(f"Invalid {name}: {s!r}")
    return urllib.parse.quote(s, safe="")


def need(name):
    v = params.get(name)
    if v in (None, ""):
        raise ValueError(f"{name} required")
    return v


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def task_summary(t):
    t = t or {}
    return {
        "id": t.get("id"),
        "title": t.get("title"),
        "percentComplete": t.get("percentComplete"),
        "dueDateTime": t.get("dueDateTime"),
        "bucketId": t.get("bucketId"),
        "assignments": sorted((t.get("assignments") or {}).keys()),
        "priority": t.get("priority"),
    }


def patch_task(path, payload, token):
    """PATCH a Planner task with the required If-Match ETag; retry once on 409/412 conflict."""
    for attempt in (1, 2):
        task = request("GET", path, token)
        etag = (task or {}).get("@odata.etag")
        if not etag:
            raise RuntimeError("Could not read the task's current ETag (@odata.etag) for update")
        try:
            return request("PATCH", path, token, data=payload,
                           headers={"If-Match": etag, "Prefer": "return=representation"})
        except ApiError as e:
            if attempt == 1 and e.status in (409, 412):
                continue
            raise


# --- Tool handlers ---------------------------------------------------------

def list_plans():
    group_id = params.get("groupId") or default_group_id
    path = f"/groups/{seg(group_id, 'groupId')}/planner/plans"
    token = get_token()
    result = request("GET", path, token)
    plans = [{
        "id": p.get("id"),
        "title": p.get("title"),
        "owner": p.get("owner"),
    } for p in (result or {}).get("value", [])]
    print(json.dumps({"count": len(plans), "plans": plans}))


def list_buckets():
    plan_id = need("planId")
    path = f"/planner/plans/{seg(plan_id, 'planId')}/buckets"
    token = get_token()
    result = request("GET", path, token)
    buckets = [{
        "id": b.get("id"),
        "name": b.get("name"),
        "orderHint": b.get("orderHint"),
    } for b in (result or {}).get("value", [])]
    print(json.dumps({"count": len(buckets), "buckets": buckets}))


def list_tasks():
    bucket_id = params.get("bucketId")
    plan_id = params.get("planId")
    if bucket_id:
        path = f"/planner/buckets/{seg(bucket_id, 'bucketId')}/tasks"
    elif plan_id:
        path = f"/planner/plans/{seg(plan_id, 'planId')}/tasks"
    else:
        raise ValueError("planId or bucketId required")
    limit = clamp(params.get("limit", 50), 50, 200)
    token = get_token()
    result = request("GET", path, token)
    tasks = [task_summary(t) for t in (result or {}).get("value", [])[:limit]]
    print(json.dumps({"count": len(tasks), "tasks": tasks}))


def get_task():
    task_id = need("taskId")
    path = f"/planner/tasks/{seg(task_id, 'taskId')}"
    token = get_token()
    task = request("GET", path, token) or {}
    details = request("GET", f"{path}/details", token) or {}
    out = task_summary(task)
    out["planId"] = task.get("planId")
    out["createdDateTime"] = task.get("createdDateTime")
    out["description"] = details.get("description")
    out["checklist"] = [{
        "title": item.get("title"),
        "isChecked": item.get("isChecked"),
    } for item in (details.get("checklist") or {}).values()]
    print(json.dumps(out))


def create_task():
    plan_id = need("planId")
    title = need("title")
    payload = {"planId": str(plan_id), "title": str(title)}
    if params.get("bucketId"):
        payload["bucketId"] = str(params["bucketId"])
    if params.get("dueDateTime"):
        payload["dueDateTime"] = str(params["dueDateTime"])
    assignee_ids = params.get("assigneeIds")
    if assignee_ids:
        if isinstance(assignee_ids, str):
            assignee_ids = [assignee_ids]
        elif not isinstance(assignee_ids, list):
            raise ValueError("assigneeIds must be a list of user ids")
        payload["assignments"] = {str(uid): dict(ASSIGNMENT) for uid in assignee_ids}
    token = get_token()
    task = request("POST", "/planner/tasks", token, data=payload) or {}
    print(json.dumps({
        "id": task.get("id"),
        "title": task.get("title"),
        "planId": task.get("planId"),
        "bucketId": task.get("bucketId"),
    }))


def update_task():
    task_id = need("taskId")
    path = f"/planner/tasks/{seg(task_id, 'taskId')}"
    payload = {}
    if params.get("title") is not None:
        payload["title"] = str(params["title"])
    if params.get("percentComplete") is not None:
        payload["percentComplete"] = int(params["percentComplete"])
    if params.get("dueDateTime") is not None:
        payload["dueDateTime"] = params["dueDateTime"] or None
    if params.get("bucketId") is not None:
        payload["bucketId"] = str(params["bucketId"])
    if not payload:
        raise ValueError("nothing to update: provide title, percentComplete, dueDateTime, and/or bucketId")
    token = get_token()
    updated = patch_task(path, payload, token)
    if updated:
        out = task_summary(updated)
        out["updated"] = True
    else:
        out = {"id": task_id, "updated": True}
    print(json.dumps(out))


def assign_task():
    task_id = need("taskId")
    user_id = need("userId")
    path = f"/planner/tasks/{seg(task_id, 'taskId')}"
    action = (params.get("action") or "add").lower()
    if action not in ("add", "remove"):
        raise ValueError("action must be 'add' or 'remove'")
    value = dict(ASSIGNMENT) if action == "add" else None
    token = get_token()
    updated = patch_task(path, {"assignments": {str(user_id): value}}, token)
    out = {
        "id": (updated or {}).get("id") or task_id,
        "userId": user_id,
        "action": action,
    }
    if updated:
        out["assignments"] = sorted((updated.get("assignments") or {}).keys())
    print(json.dumps(out))


HANDLERS = {
    "planner.list_plans": list_plans,
    "planner.list_buckets": list_buckets,
    "planner.list_tasks": list_tasks,
    "planner.get_task": get_task,
    "planner.create_task": create_task,
    "planner.update_task": update_task,
    "planner.assign_task": assign_task,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (tenant_id and client_id and client_secret and default_group_id):
        print(json.dumps({"error": "Missing Microsoft Graph credentials: connect the Planner integration first (tenantId, clientId, clientSecret, defaultGroupId)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
