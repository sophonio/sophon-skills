"""GitHub code-search skill — searches code, repositories, and commits via the GitHub search API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool's call arguments, and the connection-card credential field (token).

A token is optional: repository and commit search work anonymously (subject to lower rate
limits), but the GitHub code-search endpoint requires authentication.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
token = params.get("token", "")

API_BASE = "https://api.github.com"


def build_headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "sophon-code-search",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def request(path, query=None):
    """GET a GitHub API path and return parsed JSON. Raises RuntimeError on HTTP/URL errors."""
    url = f"{API_BASE}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    req = urllib.request.Request(url, headers=build_headers(), method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            body = e.read().decode("utf-8") if e.fp else ""
            if body:
                parsed = json.loads(body)
                detail = parsed.get("message", body)
        except Exception:  # noqa: BLE001
            detail = ""
        raise RuntimeError(f"GitHub API error {e.code}: {detail or e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"GitHub request failed: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def require_query():
    query = params.get("query")
    if not query or not str(query).strip():
        raise ValueError("query is required")
    return str(query).strip()


# --- Tool handlers ---------------------------------------------------------

def search_code():
    if not token:
        print(json.dumps({"error": "code search requires a GitHub token"}))
        return
    query = require_query()
    per_page = clamp(params.get("limit", 30), 30, 50)
    data = request("/search/code", query={"q": query, "per_page": per_page})
    items = data.get("items") or []
    results = [{
        "repo": (item.get("repository") or {}).get("full_name"),
        "path": item.get("path"),
        "url": item.get("html_url"),
    } for item in items]
    print(json.dumps({"totalCount": data.get("total_count"), "count": len(results), "results": results}))


def search_repositories():
    query = require_query()
    per_page = clamp(params.get("limit", 30), 30, 50)
    sort = params.get("sort")
    if sort and sort not in ("stars", "forks", "updated"):
        raise ValueError("sort must be one of: stars, forks, updated")
    data = request("/search/repositories", query={"q": query, "sort": sort, "per_page": per_page})
    items = data.get("items") or []
    results = [{
        "fullName": item.get("full_name"),
        "description": item.get("description"),
        "stars": item.get("stargazers_count"),
        "language": item.get("language"),
        "url": item.get("html_url"),
    } for item in items]
    print(json.dumps({"totalCount": data.get("total_count"), "count": len(results), "results": results}))


def search_commits():
    query = require_query()
    per_page = clamp(params.get("limit", 30), 30, 50)
    data = request("/search/commits", query={"q": query, "per_page": per_page})
    items = data.get("items") or []
    results = []
    for item in items:
        commit = item.get("commit") or {}
        author = commit.get("author") or {}
        results.append({
            "repo": (item.get("repository") or {}).get("full_name"),
            "sha": item.get("sha"),
            "message": commit.get("message"),
            "author": author.get("name"),
            "url": item.get("html_url"),
        })
    print(json.dumps({"totalCount": data.get("total_count"), "count": len(results), "results": results}))


HANDLERS = {
    "code.search_code": search_code,
    "code.search_repositories": search_repositories,
    "code.search_commits": search_commits,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
