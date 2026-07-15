"""Notion integration skill — talks to the Notion REST API with an internal integration token.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential field (token).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
token = params.get("token", "")

API_BASE = "https://api.notion.com"
NOTION_VERSION = "2022-06-28"

HEADERS = {
    "Authorization": f"Bearer {token}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
    "User-Agent": "sophon-notion-skill",
}


def request(method, path, data=None, query=None):
    """Make an authenticated request to the Notion API. Returns parsed JSON (or None for 204)."""
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
        raise RuntimeError(f"Notion API error {e.code}: {detail}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def plain_text(rich):
    """Join a Notion rich_text / title array into a single plain string."""
    if not isinstance(rich, list):
        return ""
    return "".join(seg.get("plain_text", "") for seg in rich if isinstance(seg, dict))


def title_of(obj):
    """Best-effort title extraction from a page or database object."""
    # Database objects carry a top-level "title" rich_text array.
    if obj.get("object") == "database":
        return plain_text(obj.get("title", []))
    # Page objects carry the title inside whichever property has type "title".
    props = obj.get("properties", {})
    if isinstance(props, dict):
        for prop in props.values():
            if isinstance(prop, dict) and prop.get("type") == "title":
                return plain_text(prop.get("title", []))
    return None


def object_summary(obj):
    return {
        "id": obj.get("id"),
        "object": obj.get("object"),
        "title": title_of(obj),
        "url": obj.get("url"),
    }


def block_summary(block):
    btype = block.get("type")
    content = block.get(btype) if isinstance(block.get(btype), dict) else {}
    text = plain_text(content.get("rich_text", [])) if isinstance(content, dict) else ""
    return {
        "id": block.get("id"),
        "type": btype,
        "text": text,
        "hasChildren": block.get("has_children"),
    }


# --- Tool handlers ---------------------------------------------------------

def search():
    payload = {"page_size": clamp(params.get("limit", 20), 20, 100)}
    query = params.get("query")
    if query:
        payload["query"] = query
    filter_type = params.get("filterType")
    if filter_type in ("page", "database"):
        payload["filter"] = {"property": "object", "value": filter_type}
    result = request("POST", "/v1/search", data=payload)
    results = [object_summary(o) for o in (result or {}).get("results", [])]
    print(json.dumps({"count": len(results), "results": results}))


def get_page():
    page_id = params.get("pageId", "")
    page = request("GET", f"/v1/pages/{page_id}")
    data = object_summary(page)
    data["createdTime"] = page.get("created_time")
    data["lastEditedTime"] = page.get("last_edited_time")
    data["archived"] = page.get("archived")
    data["properties"] = page.get("properties")
    print(json.dumps(data))


def get_block_children():
    block_id = params.get("blockId", "")
    result = request("GET", f"/v1/blocks/{block_id}/children", query={
        "page_size": clamp(params.get("limit", 50), 50, 100),
    })
    blocks = [block_summary(b) for b in (result or {}).get("results", [])]
    print(json.dumps({"count": len(blocks), "blocks": blocks,
                      "hasMore": (result or {}).get("has_more", False)}))


def query_database():
    database_id = params.get("databaseId", "")
    payload = {"page_size": clamp(params.get("limit", 20), 20, 100)}
    if params.get("filter"):
        payload["filter"] = params["filter"]
    if params.get("sorts"):
        payload["sorts"] = params["sorts"]
    result = request("POST", f"/v1/databases/{database_id}/query", data=payload)
    rows = [object_summary(o) for o in (result or {}).get("results", [])]
    print(json.dumps({"count": len(rows), "results": rows,
                      "hasMore": (result or {}).get("has_more", False)}))


def create_page():
    parent_database_id = params.get("parentDatabaseId")
    parent_page_id = params.get("parentPageId")
    if parent_database_id:
        parent = {"database_id": parent_database_id}
    elif parent_page_id:
        parent = {"page_id": parent_page_id}
    else:
        raise ValueError("create_page requires either parentDatabaseId or parentPageId")

    payload = {"parent": parent}

    properties = params.get("properties")
    title = params.get("title")
    if properties:
        payload["properties"] = properties
    elif title is not None:
        if parent_database_id:
            # Minimal title property; assumes the DB's title column is named "Name".
            payload["properties"] = {
                "Name": {"title": [{"text": {"content": title}}]}
            }
        else:
            # Page-under-page: parent has an implicit "title" property.
            payload["properties"] = {
                "title": {"title": [{"text": {"content": title}}]}
            }
    else:
        payload["properties"] = {}

    if params.get("children"):
        payload["children"] = params["children"]

    page = request("POST", "/v1/pages", data=payload)
    print(json.dumps({"id": page.get("id"), "url": page.get("url")}))


def update_page():
    page_id = params.get("pageId", "")
    payload = {}
    if params.get("properties"):
        payload["properties"] = params["properties"]
    if "archived" in params and params.get("archived") is not None:
        payload["archived"] = bool(params["archived"])
    if not payload:
        raise ValueError("update_page requires 'properties' and/or 'archived'")
    page = request("PATCH", f"/v1/pages/{page_id}", data=payload)
    print(json.dumps({"id": page.get("id"), "url": page.get("url"),
                      "archived": page.get("archived")}))


def append_blocks():
    block_id = params.get("blockId", "")
    children = params.get("children")
    if not isinstance(children, list) or not children:
        raise ValueError("append_blocks requires a non-empty 'children' array")
    result = request("PATCH", f"/v1/blocks/{block_id}/children",
                     data={"children": children})
    appended = (result or {}).get("results", [])
    print(json.dumps({"id": block_id, "appended": len(appended)}))


HANDLERS = {
    "notion.search": search,
    "notion.get_page": get_page,
    "notion.get_block_children": get_block_children,
    "notion.query_database": query_database,
    "notion.create_page": create_page,
    "notion.update_page": update_page,
    "notion.append_blocks": append_blocks,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not token:
        print(json.dumps({"error": "Missing Notion credential: connect the Notion integration first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
