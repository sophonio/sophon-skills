"""Confluence integration skill — communicates with Confluence REST API v2 using Basic Auth."""

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
    """Make an authenticated request to the Confluence REST API."""
    url = f"{base_url}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        raise RuntimeError(f"Confluence API error {e.code}: {error_body}") from e


def search():
    cql = params.get("cql", "")
    limit = params.get("limit", 20)
    encoded_cql = urllib.parse.quote(cql)
    result = make_request("GET", f"/wiki/api/v2/search?cql={encoded_cql}&limit={int(limit)}")
    results = []
    for item in result.get("results", []):
        content = item.get("content", {})
        results.append({
            "id": content.get("id"),
            "title": item.get("title"),
            "type": content.get("type"),
            "spaceId": content.get("spaceId"),
            "url": item.get("url"),
            "excerpt": item.get("excerpt"),
            "lastModified": item.get("lastModified"),
        })
    print(json.dumps({"total": result.get("totalSize", 0), "results": results}))


def get_page():
    page_id = params.get("pageId", "")
    result = make_request("GET", f"/wiki/api/v2/pages/{page_id}?body-format=storage")
    body = result.get("body", {}).get("storage", {})
    print(json.dumps({
        "id": result.get("id"),
        "title": result.get("title"),
        "spaceId": result.get("spaceId"),
        "status": result.get("status"),
        "version": result.get("version", {}).get("number"),
        "body": body.get("value", ""),
        "createdAt": result.get("createdAt"),
        "authorId": result.get("authorId"),
    }))


def create_page():
    space_id = params.get("spaceId", "")
    title = params.get("title", "")
    body = params.get("body", "")
    parent_id = params.get("parentId")

    payload = {
        "spaceId": space_id,
        "status": "current",
        "title": title,
        "body": {
            "representation": "storage",
            "value": body,
        },
    }
    if parent_id:
        payload["parentId"] = parent_id

    result = make_request("POST", "/wiki/api/v2/pages", payload)
    print(json.dumps({
        "id": result.get("id"),
        "title": result.get("title"),
        "spaceId": result.get("spaceId"),
        "version": result.get("version", {}).get("number"),
    }))


def update_page():
    page_id = params.get("pageId", "")
    title = params.get("title", "")
    body = params.get("body", "")

    # Fetch current version number first
    current = make_request("GET", f"/wiki/api/v2/pages/{page_id}")
    current_version = current.get("version", {}).get("number", 1)

    payload = {
        "id": page_id,
        "status": "current",
        "title": title,
        "body": {
            "representation": "storage",
            "value": body,
        },
        "version": {
            "number": current_version + 1,
        },
    }

    result = make_request("PUT", f"/wiki/api/v2/pages/{page_id}", payload)
    print(json.dumps({
        "id": result.get("id"),
        "title": result.get("title"),
        "version": result.get("version", {}).get("number"),
    }))


def list_spaces():
    limit = params.get("limit", 25)
    result = make_request("GET", f"/wiki/api/v2/spaces?limit={int(limit)}")
    spaces = []
    for space in result.get("results", []):
        spaces.append({
            "id": space.get("id"),
            "key": space.get("key"),
            "name": space.get("name"),
            "type": space.get("type"),
            "status": space.get("status"),
            "homepageId": space.get("homepageId"),
        })
    print(json.dumps({"spaces": spaces}))


def add_comment():
    page_id = params.get("pageId", "")
    body = params.get("body", "")

    payload = {
        "pageId": page_id,
        "body": {
            "representation": "storage",
            "value": body,
        },
    }

    result = make_request("POST", f"/wiki/api/v2/pages/{page_id}/footer-comments", payload)
    print(json.dumps({
        "id": result.get("id"),
        "pageId": page_id,
    }))


# Dispatch based on tool name
try:
    if tool_name == "confluence.search":
        search()
    elif tool_name == "confluence.get_page":
        get_page()
    elif tool_name == "confluence.create_page":
        create_page()
    elif tool_name == "confluence.update_page":
        update_page()
    elif tool_name == "confluence.list_spaces":
        list_spaces()
    elif tool_name == "confluence.add_comment":
        add_comment()
    else:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
except RuntimeError as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
