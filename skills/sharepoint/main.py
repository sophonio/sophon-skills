"""SharePoint integration skill — SharePoint Online sites, lists, and files via Microsoft Graph (app-only).

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (tenantId, clientId, clientSecret).

Auth is app-only (OAuth2 client-credentials): we POST to the tenant token endpoint to obtain an
access token, then call Microsoft Graph site-scoped endpoints (https://graph.microsoft.com/v1.0/sites/...)
with a Bearer token. Requires Sites.Read.All application permission (Sites.ReadWrite.All for the
write tools) granted with admin consent.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
tenant_id = params.get("tenantId") or ""
client_id = params.get("clientId") or ""
client_secret = params.get("clientSecret") or ""

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
MAX_PAGES = 5


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
            "User-Agent": "sophon-sharepoint-skill",
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


def request(method, path, token, data=None, query=None):
    """Make an authenticated request to Microsoft Graph. Returns parsed JSON (or None for 204).

    `path` is appended to the Graph v1.0 base URL, unless it is already an absolute URL
    (used to follow @odata.nextLink pages).
    """
    url = path if path.startswith("http") else f"{GRAPH_BASE}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "sophon-sharepoint-skill",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            hint = f"retry after {retry_after}s" if retry_after else "retry in a few seconds"
            raise RuntimeError(f"Graph is throttling this app (429); {hint}") from e
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
            msg = ((parsed.get("error") or {}).get("message")) or detail
        except (ValueError, TypeError):
            msg = detail
        raise RuntimeError(f"Graph API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Microsoft Graph: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def site_summary(site):
    return {
        "id": site.get("id"),
        "displayName": site.get("displayName"),
        "name": site.get("name"),
        "webUrl": site.get("webUrl"),
        "description": site.get("description"),
    }


def list_summary(lst):
    return {
        "id": lst.get("id"),
        "displayName": lst.get("displayName"),
        "description": lst.get("description"),
        "template": (lst.get("list") or {}).get("template"),
        "webUrl": lst.get("webUrl"),
    }


def file_summary(item):
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "webUrl": item.get("webUrl"),
        "size": item.get("size"),
        "lastModifiedDateTime": item.get("lastModifiedDateTime"),
        "isFolder": "folder" in item,
    }


def item_summary(item):
    return {
        "id": item.get("id"),
        "webUrl": item.get("webUrl"),
        "createdDateTime": item.get("createdDateTime"),
        "lastModifiedDateTime": item.get("lastModifiedDateTime"),
        "fields": item.get("fields") or {},
    }


def require(key):
    value = params.get(key)
    if not value:
        raise ValueError(f"{key} required")
    return str(value)


# --- Tool handlers ---------------------------------------------------------

def search_sites():
    token = get_token()
    query = require("query")
    result = request("GET", "/sites", token, query={"search": query})
    sites = [site_summary(s) for s in (result or {}).get("value", [])]
    print(json.dumps({"count": len(sites), "sites": sites}))


def get_site():
    token = get_token()
    hostname = require("hostname")
    path = require("path").strip("/")
    encoded_path = urllib.parse.quote(path, safe="/")
    site = request("GET", f"/sites/{urllib.parse.quote(hostname, safe='')}:/{encoded_path}", token)
    print(json.dumps(site_summary(site or {})))


def list_lists():
    token = get_token()
    site_id = require("siteId")
    result = request("GET", f"/sites/{urllib.parse.quote(site_id, safe='')}/lists", token)
    lists = [list_summary(l) for l in (result or {}).get("value", [])]
    print(json.dumps({"count": len(lists), "lists": lists}))


def query_list_items():
    token = get_token()
    site_id = require("siteId")
    list_id = require("listId")
    top = clamp(params.get("top", 25), 25, 50)
    path = (f"/sites/{urllib.parse.quote(site_id, safe='')}"
            f"/lists/{urllib.parse.quote(list_id, safe='')}/items")
    result = request("GET", path, token, query={
        "$expand": "fields",
        "$filter": params.get("filter"),
        "$top": top,
    })
    items = [item_summary(i) for i in (result or {}).get("value", [])]
    pages = 1
    next_link = (result or {}).get("@odata.nextLink")
    while next_link and pages < MAX_PAGES:
        result = request("GET", next_link, token)
        items.extend(item_summary(i) for i in (result or {}).get("value", []))
        next_link = (result or {}).get("@odata.nextLink")
        pages += 1
    print(json.dumps({"count": len(items), "items": items, "truncated": bool(next_link)}))


def get_list_item():
    token = get_token()
    site_id = require("siteId")
    list_id = require("listId")
    item_id = require("itemId")
    path = (f"/sites/{urllib.parse.quote(site_id, safe='')}"
            f"/lists/{urllib.parse.quote(list_id, safe='')}"
            f"/items/{urllib.parse.quote(item_id, safe='')}")
    item = request("GET", path, token, query={"$expand": "fields"})
    print(json.dumps(item_summary(item or {})))


def search_files():
    token = get_token()
    site_id = require("siteId")
    query = require("query").replace("'", "''")
    path = (f"/sites/{urllib.parse.quote(site_id, safe='')}"
            f"/drive/root/search(q='{urllib.parse.quote(query, safe='')}')")
    result = request("GET", path, token)
    files = [file_summary(f) for f in (result or {}).get("value", [])]
    print(json.dumps({"count": len(files), "files": files}))


def create_list_item():
    token = get_token()
    site_id = require("siteId")
    list_id = require("listId")
    fields = params.get("fields")
    if not isinstance(fields, dict) or not fields:
        raise ValueError("fields required: an object of column name -> value")
    path = (f"/sites/{urllib.parse.quote(site_id, safe='')}"
            f"/lists/{urllib.parse.quote(list_id, safe='')}/items")
    item = request("POST", path, token, data={"fields": fields})
    print(json.dumps({"id": (item or {}).get("id"), "webUrl": (item or {}).get("webUrl"),
                      "fields": (item or {}).get("fields") or {}, "created": True}))


def update_list_item():
    token = get_token()
    site_id = require("siteId")
    list_id = require("listId")
    item_id = require("itemId")
    fields = params.get("fields")
    if not isinstance(fields, dict) or not fields:
        raise ValueError("fields required: an object of column name -> value")
    path = (f"/sites/{urllib.parse.quote(site_id, safe='')}"
            f"/lists/{urllib.parse.quote(list_id, safe='')}"
            f"/items/{urllib.parse.quote(item_id, safe='')}/fields")
    updated = request("PATCH", path, token, data=fields)
    print(json.dumps({"id": item_id, "fields": updated or {}, "updated": True}))


HANDLERS = {
    "sp.search_sites": search_sites,
    "sp.get_site": get_site,
    "sp.list_lists": list_lists,
    "sp.query_list_items": query_list_items,
    "sp.get_list_item": get_list_item,
    "sp.search_files": search_files,
    "sp.create_list_item": create_list_item,
    "sp.update_list_item": update_list_item,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (tenant_id and client_id and client_secret):
        print(json.dumps({"error": "Missing Microsoft Graph credentials: connect the SharePoint integration first (tenantId, clientId, clientSecret)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
