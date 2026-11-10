"""Todoist integration skill — talks to the Todoist API v1 with an API token.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential field (apiToken).

Uses the unified API at /api/v1. The former REST API v2 (/rest/v2) now answers HTTP 410
"This endpoint is deprecated". Three things differ from v2 and shape the code below:
  * list endpoints return {"results": [...], "next_cursor": ...} instead of a bare array;
  * filter queries moved to their own endpoint, GET /tasks/filter?query=..., and are no longer a
    parameter of GET /tasks;
  * task and project objects no longer carry a `url` field, so it is derived from the id.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
api_token = params.get("apiToken", "")

API_BASE = "https://api.todoist.com/api/v1"
TASK_URL = "https://app.todoist.com/app/task"
PROJECT_URL = "https://app.todoist.com/app/project"
INBOX_URL = "https://app.todoist.com/app/inbox"
MAX_LIMIT = 200

HEADERS = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "sophon-todoist-skill",
}


def request(method, path, data=None, query=None):
    """Make an authenticated request to the Todoist API. Returns parsed JSON (or None for 204)."""
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
        raise RuntimeError(f"Todoist API error {e.code}: {detail}") from e


def results_of(payload):
    """Unwrap a v1 paginated list response, tolerating a bare array."""
    if isinstance(payload, dict):
        return payload.get("results") or []
    return payload or []


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def task_summary(task):
    task_id = task.get("id")
    return {
        "id": task_id,
        "content": task.get("content"),
        "due": (task.get("due") or {}).get("string") if task.get("due") else None,
        "priority": task.get("priority"),
        "projectId": task.get("project_id"),
        # v1 no longer returns a url; the id-only form is what the official client builds when
        # it has no title slug to append.
        "url": f"{TASK_URL}/{task_id}" if task_id else None,
    }


def project_summary(project):
    project_id = project.get("id")
    # v1 sends `inbox_project`; `is_inbox_project` is the v2 spelling, still accepted here.
    is_inbox = project.get("inbox_project", project.get("is_inbox_project"))
    return {
        "id": project_id,
        "name": project.get("name"),
        "color": project.get("color"),
        "isFavorite": project.get("is_favorite"),
        "isInboxProject": is_inbox,
        "url": INBOX_URL if is_inbox else (f"{PROJECT_URL}/{project_id}" if project_id else None),
    }


# --- Tool handlers ---------------------------------------------------------

def list_tasks():
    limit = clamp(params.get("limit", 30), 30, MAX_LIMIT)
    query = params.get("filter")
    project_id = params.get("projectId")

    if query:
        # Filtering has its own endpoint in v1 and takes `query`, not `filter`. It accepts no
        # project_id, so when both are supplied the project is applied to the returned tasks.
        result = request("GET", "/tasks/filter", query={"query": query, "limit": limit})
        tasks = results_of(result)
        if project_id:
            tasks = [t for t in tasks if str(t.get("project_id")) == str(project_id)]
    else:
        result = request("GET", "/tasks", query={"project_id": project_id, "limit": limit})
        tasks = results_of(result)

    tasks = [task_summary(t) for t in tasks][:limit]
    print(json.dumps({"count": len(tasks), "tasks": tasks}))


def list_projects():
    result = request("GET", "/projects", query={"limit": MAX_LIMIT})
    projects = [project_summary(p) for p in results_of(result)]
    print(json.dumps({"count": len(projects), "projects": projects}))


def add_task():
    content = params.get("content")
    if not content:
        raise ValueError("content is required")
    payload = {"content": content}
    if params.get("projectId"):
        payload["project_id"] = str(params["projectId"])
    if params.get("dueString"):
        payload["due_string"] = params["dueString"]
    if params.get("priority"):
        payload["priority"] = int(params["priority"])
    if params.get("description"):
        payload["description"] = params["description"]
    task = request("POST", "/tasks", data=payload)
    result = task_summary(task or {})
    print(json.dumps(result))


def complete_task():
    task_id = params.get("taskId")
    if not task_id:
        raise ValueError("taskId is required")
    request("POST", f"/tasks/{urllib.parse.quote(str(task_id), safe='')}/close")
    print(json.dumps({"id": str(task_id), "closed": True}))


def update_task():
    task_id = params.get("taskId")
    if not task_id:
        raise ValueError("taskId is required")
    payload = {}
    if params.get("content"):
        payload["content"] = params["content"]
    if params.get("dueString"):
        payload["due_string"] = params["dueString"]
    if params.get("priority"):
        payload["priority"] = int(params["priority"])
    if params.get("description"):
        payload["description"] = params["description"]
    if not payload:
        raise ValueError("Provide at least one field to update (content, dueString, priority, description)")
    task = request("POST", f"/tasks/{urllib.parse.quote(str(task_id), safe='')}", data=payload)
    # Todoist returns the updated task JSON; older responses may be empty.
    if task:
        print(json.dumps(task_summary(task)))
    else:
        print(json.dumps({"id": str(task_id), "updated": True}))


HANDLERS = {
    "todoist.list_tasks": list_tasks,
    "todoist.list_projects": list_projects,
    "todoist.add_task": add_task,
    "todoist.complete_task": complete_task,
    "todoist.update_task": update_task,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not api_token:
        print(json.dumps({"error": "Missing Todoist credential: connect the Todoist integration first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
