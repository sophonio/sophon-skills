"""Sentry integration skill — talks to the Sentry REST API (v0) with an auth token.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential fields (token, organization, host).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
token = params.get("token", "")
org = params.get("organization", "")
base = (params.get("host") or "https://sentry.io").rstrip("/") + "/api/0"

HEADERS = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "User-Agent": "sophon-sentry-skill",
    "Content-Type": "application/json",
}


def request(method, path, data=None, query=None):
    """Make an authenticated request to the Sentry API. Returns parsed JSON (or None for 204)."""
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
        raise RuntimeError(f"Sentry API error {e.code}: {detail}") from e


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


def project_summary(project):
    return {
        "id": project.get("id"),
        "slug": project.get("slug"),
        "name": project.get("name"),
        "platform": project.get("platform"),
        "status": project.get("status"),
    }


def issue_summary(issue):
    return {
        "id": issue.get("id"),
        "shortId": issue.get("shortId"),
        "title": issue.get("title"),
        "culprit": issue.get("culprit"),
        "level": issue.get("level"),
        "status": issue.get("status"),
        "count": issue.get("count"),
        "userCount": issue.get("userCount"),
        "firstSeen": issue.get("firstSeen"),
        "lastSeen": issue.get("lastSeen"),
        "permalink": issue.get("permalink"),
    }


def event_summary(event):
    return {
        "id": event.get("id"),
        "eventID": event.get("eventID"),
        "title": event.get("title") or event.get("message"),
        "message": event.get("message"),
        "platform": event.get("platform"),
        "dateCreated": event.get("dateCreated"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_projects():
    result = request("GET", f"/organizations/{org}/projects/")
    projects = [project_summary(p) for p in (result or [])]
    print(json.dumps({"count": len(projects), "projects": projects}))


def list_issues():
    project = require("project")
    result = request("GET", f"/projects/{org}/{project}/issues/", query={
        "query": params.get("query"),
        "statsPeriod": params.get("statsPeriod") or "14d",
        "limit": clamp(params.get("limit", 25), 25, 100),
    })
    issues = [issue_summary(i) for i in (result or [])]
    print(json.dumps({"count": len(issues), "issues": issues}))


def get_issue():
    issue_id = require("issueId")
    issue = request("GET", f"/issues/{issue_id}/")
    data = issue_summary(issue)
    data["metadata"] = issue.get("metadata")
    data["assignedTo"] = issue.get("assignedTo")
    print(json.dumps(data))


def list_events():
    issue_id = require("issueId")
    result = request("GET", f"/issues/{issue_id}/events/", query={
        "limit": clamp(params.get("limit", 25), 25, 100),
    })
    events = [event_summary(e) for e in (result or [])]
    print(json.dumps({"count": len(events), "events": events}))


def update_issue():
    issue_id = require("issueId")
    payload = {}
    if params.get("status"):
        payload["status"] = params["status"]
    if params.get("assignedTo"):
        payload["assignedTo"] = params["assignedTo"]
    if not payload:
        raise ValueError("Provide at least one of: status, assignedTo")
    issue = request("PUT", f"/issues/{issue_id}/", data=payload)
    data = issue_summary(issue)
    data["assignedTo"] = issue.get("assignedTo")
    print(json.dumps(data))


HANDLERS = {
    "sentry.list_projects": list_projects,
    "sentry.list_issues": list_issues,
    "sentry.get_issue": get_issue,
    "sentry.list_events": list_events,
    "sentry.update_issue": update_issue,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not token:
        print(json.dumps({"error": "Missing Sentry credential: connect the Sentry integration first."}))
    elif not org:
        print(json.dumps({"error": "Missing Sentry organization slug: set it on the Sentry integration."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
