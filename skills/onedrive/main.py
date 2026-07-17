"""OneDrive integration skill — OneDrive for Business files via Microsoft Graph (app-only).

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (tenantId, clientId, clientSecret, userId).

Auth is app-only (OAuth2 client-credentials): we POST to the tenant token endpoint to obtain an
access token, then call Microsoft Graph as
https://graph.microsoft.com/v1.0/users/{userId}/drive/... with a Bearer token. App-only requires
an explicit target user (UPN) and works only for OneDrive for Business (Microsoft 365 work/school
accounts, not consumer OneDrive personal).

File downloads: GET /items/{id}/content answers 302 with a pre-authenticated *.sharepoint.com
URL. We must NOT let urllib auto-follow that redirect, because it would forward the Graph
Authorization header cross-host; instead we capture the Location header and fetch it with no
auth header at all.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
tenant_id = params.get("tenantId") or ""
client_id = params.get("clientId") or ""
client_secret = params.get("clientSecret") or ""
user_id = params.get("userId") or ""

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
USER_AGENT = "sophon-onedrive-skill"
MAX_READ_BYTES = 512 * 1024      # cap for onedrive.read_file
MAX_UPLOAD_BYTES = 1024 * 1024   # cap for onedrive.upload_file (sandbox limit, not the API's)


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
            "User-Agent": USER_AGENT,
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


def drive_url(path):
    """Absolute Graph URL for a path relative to the target user's drive."""
    return f"{GRAPH_BASE}/users/{urllib.parse.quote(user_id, safe='')}/drive{path}"


def http_error_message(e):
    """Turn an HTTPError from Graph into a friendly message (incl. 429 Retry-After)."""
    detail = e.read().decode() if e.fp else ""
    try:
        parsed = json.loads(detail)
        msg = ((parsed.get("error") or {}).get("message")) or detail
    except (ValueError, TypeError):
        msg = detail
    if e.code == 429:
        retry_after = e.headers.get("Retry-After")
        suffix = f" (retry after {retry_after} seconds)" if retry_after else ""
        return f"OneDrive API error 429: rate limited{suffix}: {msg}"
    return f"OneDrive API error {e.code}: {msg}"


def request(method, path, token, data=None, query=None, raw=None, content_type=None):
    """Make an authenticated request to the drive. Returns parsed JSON (or None for 204)."""
    url = drive_url(path)
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    if raw is not None:
        body = raw
    elif data is not None:
        body = json.dumps(data).encode()
    else:
        body = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if body is not None:
        headers["Content-Type"] = content_type or "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            text = resp.read().decode()
            return json.loads(text) if text else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(http_error_message(e)) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Microsoft Graph: {e.reason}") from e


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Redirect handler that refuses to follow, so 3xx surfaces as HTTPError."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ARG002
        return None


def download_content(token, path):
    """Fetch a /content endpoint safely.

    Graph replies 302 with a pre-authenticated *.sharepoint.com Location; the Authorization
    header must not be forwarded to that host, so we capture the redirect ourselves and fetch
    the download URL with no auth header. Returns at most MAX_READ_BYTES + 1 bytes.
    """
    req = urllib.request.Request(
        drive_url(path),
        headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
        method="GET",
    )
    opener = urllib.request.build_opener(_NoRedirect())
    location = None
    try:
        with opener.open(req) as resp:
            # Graph normally 302s, but tolerate a direct 200 body.
            return resp.read(MAX_READ_BYTES + 1)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            location = e.headers.get("Location")
        else:
            raise RuntimeError(http_error_message(e)) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Microsoft Graph: {e.reason}") from e
    if not location:
        raise RuntimeError("Download redirect from Microsoft Graph had no Location header")
    dl = urllib.request.Request(location, headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        with urllib.request.urlopen(dl) as resp:
            return resp.read(MAX_READ_BYTES + 1)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"OneDrive download failed ({e.code})") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach the OneDrive download host: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def encode_path(path):
    """Percent-encode a drive-relative path, keeping segment separators."""
    return urllib.parse.quote(path.strip("/"), safe="/")


def item_summary(it):
    kind = "folder" if "folder" in it else "file"
    out = {
        "id": it.get("id"),
        "name": it.get("name"),
        "type": kind,
        "size": it.get("size"),
        "lastModifiedDateTime": it.get("lastModifiedDateTime"),
    }
    if kind == "folder":
        out["childCount"] = (it.get("folder") or {}).get("childCount")
    else:
        out["mimeType"] = (it.get("file") or {}).get("mimeType")
    return out


def item_detail(it):
    out = item_summary(it or {})
    it = it or {}
    out["webUrl"] = it.get("webUrl")
    out["createdDateTime"] = it.get("createdDateTime")
    out["parentPath"] = (it.get("parentReference") or {}).get("path")
    modified_by = ((it.get("lastModifiedBy") or {}).get("user") or {})
    out["lastModifiedBy"] = modified_by.get("displayName") or modified_by.get("email")
    return out


# --- Tool handlers ---------------------------------------------------------

def list_folder():
    token = get_token()
    limit = clamp(params.get("limit", 25), 25, 100)
    path = (params.get("path") or "").strip("/")
    api_path = f"/root:/{encode_path(path)}:/children" if path else "/root/children"
    result = request("GET", api_path, token, query={"$top": limit})
    items = [item_summary(i) for i in (result or {}).get("value", [])]
    print(json.dumps({"count": len(items), "items": items}))


def search_files():
    token = get_token()
    query = params.get("query") or ""
    if not query:
        raise ValueError("query required")
    limit = clamp(params.get("limit", 25), 25, 100)
    escaped = urllib.parse.quote(query.replace("'", "''"), safe="")
    result = request("GET", f"/root/search(q='{escaped}')", token, query={"$top": limit})
    items = [item_summary(i) for i in (result or {}).get("value", [])]
    print(json.dumps({"count": len(items), "items": items}))


def get_item():
    token = get_token()
    item_id = params.get("itemId")
    path = (params.get("path") or "").strip("/")
    if item_id:
        api_path = f"/items/{urllib.parse.quote(str(item_id), safe='')}"
    elif path:
        api_path = f"/root:/{encode_path(path)}"
    else:
        raise ValueError("provide itemId or path")
    it = request("GET", api_path, token)
    print(json.dumps(item_detail(it)))


def read_file():
    token = get_token()
    item_id = params.get("itemId")
    if not item_id:
        raise ValueError("itemId required (use onedrive.get_item or onedrive.list_folder to find it)")
    data = download_content(token, f"/items/{urllib.parse.quote(str(item_id), safe='')}/content")
    truncated = len(data) > MAX_READ_BYTES
    data = data[:MAX_READ_BYTES]
    if b"\x00" in data:
        raise RuntimeError(
            "File appears to be binary and cannot be shown as text. "
            "Use onedrive.get_item and open the file via its webUrl instead."
        )
    print(json.dumps({
        "itemId": item_id,
        "content": data.decode("utf-8", errors="replace"),
        "truncated": truncated,
    }))


def create_folder():
    token = get_token()
    name = params.get("name")
    if not name:
        raise ValueError("name required")
    parent = (params.get("parentPath") or "").strip("/")
    api_path = f"/root:/{encode_path(parent)}:/children" if parent else "/root/children"
    payload = {"name": name, "folder": {}, "@microsoft.graph.conflictBehavior": "fail"}
    it = request("POST", api_path, token, data=payload) or {}
    print(json.dumps({"id": it.get("id"), "name": it.get("name"),
                      "webUrl": it.get("webUrl"), "created": True}))


def upload_file():
    token = get_token()
    path = (params.get("path") or "").strip("/")
    content = params.get("content")
    if not path:
        raise ValueError("path required (drive-relative, e.g. Documents/notes.txt)")
    if content is None:
        raise ValueError("content required")
    body = str(content).encode("utf-8")
    if len(body) > MAX_UPLOAD_BYTES:
        raise ValueError("content too large: this tool uploads at most 1 MB of text")
    it = request("PUT", f"/root:/{encode_path(path)}:/content", token,
                 raw=body, content_type="text/plain") or {}
    print(json.dumps({"id": it.get("id"), "name": it.get("name"), "size": it.get("size"),
                      "webUrl": it.get("webUrl")}))


def create_share_link():
    token = get_token()
    item_id = params.get("itemId")
    if not item_id:
        raise ValueError("itemId required")
    result = request(
        "POST",
        f"/items/{urllib.parse.quote(str(item_id), safe='')}/createLink",
        token,
        data={"type": "view", "scope": "organization"},
    ) or {}
    link = result.get("link") or {}
    print(json.dumps({
        "itemId": item_id,
        "url": link.get("webUrl"),
        "type": link.get("type"),
        "scope": link.get("scope"),
    }))


HANDLERS = {
    "onedrive.list_folder": list_folder,
    "onedrive.search_files": search_files,
    "onedrive.get_item": get_item,
    "onedrive.read_file": read_file,
    "onedrive.create_folder": create_folder,
    "onedrive.upload_file": upload_file,
    "onedrive.create_share_link": create_share_link,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (tenant_id and client_id and client_secret and user_id):
        print(json.dumps({"error": "Missing Microsoft Graph credentials: connect the OneDrive integration first (tenantId, clientId, clientSecret, userId)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
