"""Jira integration skill — communicates with Jira REST API v3 using Basic Auth."""

import base64
import json
import urllib.request
import urllib.parse
import urllib.error

# params is injected by the sandbox runtime via SOPHON_PARAMS
tool_name = params.get("tool", "")
base_url = params.get("baseUrl", "").rstrip("/")
email = params.get("email", "")
api_key = params.get("apiKey", "")

# Build Basic Auth header
credentials = base64.b64encode(f"{email}:{api_key}".encode()).decode()
headers = {
    "Authorization": f"Basic {credentials}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def make_request(method, path, data=None):
    """Make an authenticated request to the Jira REST API."""
    url = f"{base_url}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        raise RuntimeError(f"Jira API error {e.code}: {error_body}") from e


def search_issues():
    jql = params.get("jql", "")
    max_results = params.get("maxResults", 20)
    # Use POST /rest/api/3/search/jql — the old GET /rest/api/3/search was removed Aug 2025
    payload = {
        "jql": jql,
        "maxResults": int(max_results),
        "fields": ["summary", "status", "assignee", "priority", "issuetype"],
    }
    result = make_request("POST", "/rest/api/3/search/jql", payload)
    issues = []
    for issue in result.get("issues", []):
        fields = issue.get("fields", {})
        issues.append({
            "key": issue["key"],
            "summary": fields.get("summary"),
            "status": fields.get("status", {}).get("name"),
            "assignee": (fields.get("assignee") or {}).get("displayName"),
            "priority": (fields.get("priority") or {}).get("name"),
            "issueType": (fields.get("issuetype") or {}).get("name"),
        })
    print(json.dumps({"total": result.get("total", 0), "issues": issues}))


def get_issue():
    issue_key = params.get("issueKey", "")
    result = make_request("GET", f"/rest/api/3/issue/{issue_key}")
    fields = result.get("fields", {})
    print(json.dumps({
        "key": result["key"],
        "summary": fields.get("summary"),
        "description": fields.get("description"),
        "status": (fields.get("status") or {}).get("name"),
        "assignee": (fields.get("assignee") or {}).get("displayName"),
        "reporter": (fields.get("reporter") or {}).get("displayName"),
        "priority": (fields.get("priority") or {}).get("name"),
        "issueType": (fields.get("issuetype") or {}).get("name"),
        "created": fields.get("created"),
        "updated": fields.get("updated"),
    }))


def create_issue():
    project_key = params.get("projectKey", "")
    summary = params.get("summary", "")
    issue_type = params.get("issueType", "Task")
    description = params.get("description")
    priority = params.get("priority")

    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }
    }
    if description:
        payload["fields"]["description"] = {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
        }
    if priority:
        payload["fields"]["priority"] = {"name": priority}

    result = make_request("POST", "/rest/api/3/issue", payload)
    print(json.dumps({
        "key": result.get("key"),
        "id": result.get("id"),
        "self": result.get("self"),
    }))


def list_projects():
    result = make_request("GET", "/rest/api/3/project")
    projects = []
    for proj in result:
        projects.append({
            "key": proj.get("key"),
            "name": proj.get("name"),
            "projectTypeKey": proj.get("projectTypeKey"),
            "style": proj.get("style"),
        })
    print(json.dumps({"projects": projects}))


# Dispatch based on tool name
try:
    if tool_name == "jira.search":
        search_issues()
    elif tool_name == "jira.get_issue":
        get_issue()
    elif tool_name == "jira.create_issue":
        create_issue()
    elif tool_name == "jira.list_projects":
        list_projects()
    else:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
except RuntimeError as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
