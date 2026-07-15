"""Todoist integration skill — talks to the Todoist REST API v2 with an API token.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential field (apiToken).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
api_token = params.get("apiToken", "")
API_BASE = "https://api.todoist.com/rest/v2"

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


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def task_summary(task):
    return {
        "id": task.get("id"),
        "content": task.get("content"),
        "due": (task.get("due") or {}).get("string") if task.get("due") else None,
        "priority": task.get("priority"),
        "projectId": task.get("project_id"),
        "url": task.get("url"),
    }


def project_summary(project):
    return {
        "id": project.get("id"),
        "name": project.get("name"),
        "color": project.get("color"),
        "isFavorite": project.get("is_favorite"),
        "isInboxProject": project.get("is_inbox_project"),
        "url": project.get("url"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_tasks():
    result = request("GET", "/tasks", query={
        "project_id": params.get("projectId"),
        "filter": params.get("filter"),
    })
    tasks = [task_summary(t) for t in (result or [])]
    limit = clamp(params.get("limit", 30), 30, 200)
    tasks = tasks[:limit]
    print(json.dumps({"count": len(tasks), "tasks": tasks}))


def list_projects():
    result = request("GET", "/projects")
    projects = [project_summary(p) for p in (result or [])]
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
    request("POST", f"/tasks/{task_id}/close")
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
    task = request("POST", f"/tasks/{task_id}", data=payload)
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
