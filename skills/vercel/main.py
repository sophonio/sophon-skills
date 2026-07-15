"""Vercel integration skill — talks to the Vercel REST API with a bearer access token.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential fields (token, teamId).

When a teamId is configured it is merged into the query string of every request so team-scoped
resources resolve correctly.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
token = params.get("token", "")
team_id = params.get("teamId") or ""
API_BASE = "https://api.vercel.com"

HEADERS = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "sophon-vercel-skill",
    "Accept": "application/json",
}


def request(method, path, data=None, query=None):
    """Make an authenticated request to the Vercel API. Returns parsed JSON (or None for 204)."""
    merged = dict(query or {})
    if team_id:
        merged["teamId"] = team_id
    clean = {k: v for k, v in merged.items() if v not in (None, "")}
    url = f"{API_BASE}{path}"
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
        try:
            parsed = json.loads(detail)
            msg = (parsed.get("error") or {}).get("message") or detail
        except (ValueError, TypeError):
            msg = detail
        raise RuntimeError(f"Vercel API error {e.code}: {msg}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def deployment_summary(d):
    return {
        "uid": d.get("uid") or d.get("id"),
        "name": d.get("name"),
        "url": d.get("url"),
        "state": d.get("state") or d.get("readyState"),
        "target": d.get("target"),
        "createdAt": d.get("created") or d.get("createdAt"),
        "creator": (d.get("creator") or {}).get("username"),
    }


def project_summary(p):
    latest = (p.get("latestDeployments") or [{}])
    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "framework": p.get("framework"),
        "nodeVersion": p.get("nodeVersion"),
        "createdAt": p.get("createdAt"),
        "updatedAt": p.get("updatedAt"),
        "latestDeployment": (latest[0] or {}).get("url") if latest else None,
    }


# --- Tool handlers ---------------------------------------------------------

def list_deployments():
    result = request("GET", "/v6/deployments", query={
        "projectId": params.get("projectId"),
        "state": params.get("state"),
        "limit": clamp(params.get("limit", 20), 20, 100),
    })
    deployments = [deployment_summary(d) for d in (result or {}).get("deployments", [])]
    print(json.dumps({"count": len(deployments), "deployments": deployments}))


def get_deployment():
    deployment_id = params.get("deploymentId")
    if not deployment_id:
        raise ValueError("deploymentId required")
    d = request("GET", f"/v13/deployments/{urllib.parse.quote(str(deployment_id), safe='')}")
    data = deployment_summary(d or {})
    data["projectId"] = (d or {}).get("projectId")
    data["alias"] = (d or {}).get("alias")
    data["readyState"] = (d or {}).get("readyState")
    data["inspectorUrl"] = (d or {}).get("inspectorUrl")
    print(json.dumps(data))


def list_projects():
    result = request("GET", "/v9/projects", query={
        "limit": clamp(params.get("limit", 20), 20, 100),
    })
    projects = [project_summary(p) for p in (result or {}).get("projects", [])]
    print(json.dumps({"count": len(projects), "projects": projects}))


def get_project():
    project_id = params.get("projectId")
    if not project_id:
        raise ValueError("projectId required")
    p = request("GET", f"/v9/projects/{urllib.parse.quote(str(project_id), safe='')}")
    print(json.dumps(project_summary(p or {})))


def list_env():
    project_id = params.get("projectId")
    if not project_id:
        raise ValueError("projectId required")
    result = request("GET", f"/v9/projects/{urllib.parse.quote(str(project_id), safe='')}/env")
    envs = result if isinstance(result, list) else (result or {}).get("envs", [])
    # Never expose decrypted values — return only key + target metadata.
    items = [{
        "id": e.get("id"),
        "key": e.get("key"),
        "target": e.get("target"),
        "type": e.get("type"),
        "gitBranch": e.get("gitBranch"),
    } for e in (envs or [])]
    print(json.dumps({"count": len(items), "env": items}))


HANDLERS = {
    "vercel.list_deployments": list_deployments,
    "vercel.get_deployment": get_deployment,
    "vercel.list_projects": list_projects,
    "vercel.get_project": get_project,
    "vercel.list_env": list_env,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not token:
        print(json.dumps({"error": "Missing Vercel credential: connect the Vercel integration first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
