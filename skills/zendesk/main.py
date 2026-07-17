"""Zendesk Support integration skill — tickets, users, search, and Help Center via the Zendesk API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (subdomain, clientId, clientSecret).

Auth is OAuth2 client-credentials: we POST to https://{subdomain}.zendesk.com/oauth/tokens to
obtain an access token, then call https://{subdomain}.zendesk.com/api/v2/... with a Bearer token.
Tokens live at most 48 hours and are not refreshable; a fresh one is minted on every invocation,
which is fine because each sandbox run is fresh. API-token basic auth is deliberately not
implemented (Zendesk is sunsetting API tokens starting 2026-07-28).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
subdomain = params.get("subdomain") or ""
client_id = params.get("clientId") or ""
client_secret = params.get("clientSecret") or ""

BASE = f"https://{subdomain}.zendesk.com"


def get_token():
    """Obtain an access token via the OAuth2 client-credentials grant."""
    url = f"{BASE}/oauth/tokens"
    body = json.dumps({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "read write",
    }).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "sophon-zendesk-skill",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            hint = f" Retry after {retry_after} seconds." if retry_after else ""
            raise RuntimeError(f"Token request failed (429): rate limit exceeded (limits are plan-dependent).{hint}") from e
        try:
            parsed = json.loads(detail)
            msg = parsed.get("error_description") or parsed.get("description") or parsed.get("error") or detail
            if isinstance(msg, dict):
                msg = msg.get("message") or msg.get("title") or detail
        except (ValueError, TypeError):
            msg = detail
        raise RuntimeError(f"Token request failed ({e.code}): {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Zendesk: {e.reason}") from e
    token = data.get("access_token")
    if not token:
        raise RuntimeError("No access_token in token response")
    return token


def request(method, path, token, data=None, query=None):
    """Make an authenticated request to the Zendesk API. Returns parsed JSON (or None for 204)."""
    url = f"{BASE}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "sophon-zendesk-skill",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            hint = f" Retry after {retry_after} seconds." if retry_after else ""
            raise RuntimeError(f"Zendesk API error 429: rate limit exceeded (limits are plan-dependent).{hint}") from e
        try:
            parsed = json.loads(detail)
            msg = parsed.get("description") or parsed.get("error") or detail
            if isinstance(msg, dict):
                msg = msg.get("message") or msg.get("title") or detail
        except (ValueError, TypeError):
            msg = detail
        raise RuntimeError(f"Zendesk API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Zendesk: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def ticket_summary(t):
    return {
        "id": t.get("id"),
        "subject": t.get("subject"),
        "status": t.get("status"),
        "priority": t.get("priority"),
        "type": t.get("type"),
        "requester_id": t.get("requester_id"),
        "assignee_id": t.get("assignee_id"),
        "tags": t.get("tags"),
        "created_at": t.get("created_at"),
        "updated_at": t.get("updated_at"),
    }


def user_summary(u):
    return {
        "id": u.get("id"),
        "name": u.get("name"),
        "email": u.get("email"),
        "role": u.get("role"),
        "active": u.get("active"),
        "suspended": u.get("suspended"),
        "organization_id": u.get("organization_id"),
        "time_zone": u.get("time_zone"),
        "created_at": u.get("created_at"),
    }


def article_summary(a):
    return {
        "id": a.get("id"),
        "title": a.get("title"),
        "snippet": a.get("snippet"),
        "html_url": a.get("html_url"),
        "section_id": a.get("section_id"),
        "locale": a.get("locale"),
        "updated_at": a.get("updated_at"),
    }


def search_result_summary(r):
    """Shape one universal-search result by its result_type."""
    result_type = r.get("result_type")
    if result_type == "ticket":
        item = ticket_summary(r)
    elif result_type == "user":
        item = user_summary(r)
    elif result_type == "organization":
        item = {"id": r.get("id"), "name": r.get("name"), "created_at": r.get("created_at")}
    elif result_type == "group":
        item = {"id": r.get("id"), "name": r.get("name"), "created_at": r.get("created_at")}
    else:
        item = {"id": r.get("id"), "name": r.get("name") or r.get("subject") or r.get("title"),
                "url": r.get("html_url") or r.get("url")}
    item["result_type"] = result_type
    return item


def comment_summary(c):
    return {
        "id": c.get("id"),
        "author_id": c.get("author_id"),
        "public": c.get("public"),
        "body": c.get("body"),
        "created_at": c.get("created_at"),
    }


# --- Tool handlers ---------------------------------------------------------

def search():
    token = get_token()
    query = params.get("query")
    if not query:
        raise ValueError("query required")
    limit = clamp(params.get("limit", 25), 25, 100)
    result = request("GET", "/api/v2/search.json", token, query={
        "query": query,
        "per_page": limit,
    })
    results = [search_result_summary(r) for r in (result or {}).get("results", [])]
    print(json.dumps({"count": len(results), "results": results}))


def list_tickets():
    token = get_token()
    limit = clamp(params.get("limit", 25), 25, 100)
    status = params.get("status")
    sort_by = params.get("sortBy") or "created_at"
    sort_order = params.get("sortOrder") or "desc"
    if status:
        # The tickets endpoint has no status filter; use the search API for status filtering.
        # The search API only sorts by updated_at/created_at/priority/status/ticket_type,
        # so map unsupported values (e.g. "id") to created_at and note the fallback.
        search_sort_fallback = sort_by not in ("updated_at", "created_at", "priority", "status", "ticket_type")
        search_sort_by = "created_at" if search_sort_fallback else sort_by
        result = request("GET", "/api/v2/search.json", token, query={
            "query": f"type:ticket status:{status}",
            "sort_by": search_sort_by,
            "sort_order": sort_order,
            "per_page": limit,
        })
        tickets = [ticket_summary(t) for t in (result or {}).get("results", [])]
        if search_sort_fallback:
            print(json.dumps({"count": len(tickets), "tickets": tickets,
                              "note": f"Status filtering uses the search API, which cannot sort by {sort_by}; sorted by created_at instead."}))
            return
    else:
        result = request("GET", "/api/v2/tickets.json", token, query={
            "sort_by": sort_by,
            "sort_order": sort_order,
            "per_page": limit,
        })
        tickets = [ticket_summary(t) for t in (result or {}).get("tickets", [])]
    print(json.dumps({"count": len(tickets), "tickets": tickets}))


def get_ticket():
    token = get_token()
    ticket_id = params.get("ticketId")
    if not ticket_id:
        raise ValueError("ticketId required")
    tid = urllib.parse.quote(str(ticket_id), safe="")
    max_comments = clamp(params.get("maxComments", 20), 20, 100)
    result = request("GET", f"/api/v2/tickets/{tid}.json", token)
    ticket = (result or {}).get("ticket") or {}
    detail = ticket_summary(ticket)
    detail["description"] = ticket.get("description")
    detail["organization_id"] = ticket.get("organization_id")
    detail["group_id"] = ticket.get("group_id")
    detail["via"] = (ticket.get("via") or {}).get("channel")
    comments_result = request("GET", f"/api/v2/tickets/{tid}/comments.json", token, query={
        "per_page": max_comments,
    })
    comments = [comment_summary(c) for c in (comments_result or {}).get("comments", [])[:max_comments]]
    detail["comments"] = comments
    detail["comment_count"] = len(comments)
    print(json.dumps(detail))


def search_help_center():
    token = get_token()
    query = params.get("query")
    if not query:
        raise ValueError("query required")
    limit = clamp(params.get("limit", 25), 25, 100)
    try:
        result = request("GET", "/api/v2/help_center/articles/search.json", token, query={
            "query": query,
            "per_page": limit,
        })
    except RuntimeError as e:
        if str(e).startswith("Zendesk API error 404"):
            raise RuntimeError("Help Center (Zendesk Guide) is not enabled on this account") from e
        raise
    articles = [article_summary(a) for a in (result or {}).get("results", [])]
    print(json.dumps({"count": len(articles), "articles": articles}))


def get_user():
    token = get_token()
    user_id = params.get("userId")
    email = params.get("email")
    if user_id:
        uid = urllib.parse.quote(str(user_id), safe="")
        result = request("GET", f"/api/v2/users/{uid}.json", token)
        print(json.dumps(user_summary((result or {}).get("user") or {})))
    elif email:
        result = request("GET", "/api/v2/users/search.json", token, query={"query": email})
        users = [user_summary(u) for u in (result or {}).get("users", [])]
        print(json.dumps({"count": len(users), "users": users}))
    else:
        raise ValueError("userId or email required")


def create_ticket():
    token = get_token()
    subject = params.get("subject")
    body = params.get("body")
    if not subject:
        raise ValueError("subject required")
    if not body:
        raise ValueError("body required")
    ticket = {"subject": subject, "comment": {"body": body}}
    if params.get("requesterId"):
        ticket["requester_id"] = params["requesterId"]
    elif params.get("requesterEmail"):
        requester = {"email": params["requesterEmail"]}
        if params.get("requesterName"):
            requester["name"] = params["requesterName"]
        ticket["requester"] = requester
    if params.get("priority"):
        ticket["priority"] = params["priority"]
    if params.get("tags"):
        ticket["tags"] = params["tags"]
    result = request("POST", "/api/v2/tickets.json", token, data={"ticket": ticket})
    created = (result or {}).get("ticket") or {}
    print(json.dumps({"id": created.get("id"), "subject": created.get("subject"),
                      "status": created.get("status"), "url": created.get("url"),
                      "created": True}))


def update_ticket():
    token = get_token()
    ticket_id = params.get("ticketId")
    if not ticket_id:
        raise ValueError("ticketId required")
    ticket = {}
    if params.get("status"):
        ticket["status"] = params["status"]
    if params.get("priority"):
        ticket["priority"] = params["priority"]
    if params.get("assigneeId") is not None:
        ticket["assignee_id"] = params["assigneeId"]
    if params.get("tags") is not None:
        ticket["tags"] = params["tags"]
    if not ticket:
        raise ValueError("nothing to update: provide status, priority, assigneeId, and/or tags")
    tid = urllib.parse.quote(str(ticket_id), safe="")
    result = request("PUT", f"/api/v2/tickets/{tid}.json", token, data={"ticket": ticket})
    updated = (result or {}).get("ticket") or {}
    print(json.dumps({"id": updated.get("id"), "status": updated.get("status"),
                      "priority": updated.get("priority"), "assignee_id": updated.get("assignee_id"),
                      "tags": updated.get("tags"), "updated": True}))


def add_comment():
    token = get_token()
    ticket_id = params.get("ticketId")
    if not ticket_id:
        raise ValueError("ticketId required")
    body = params.get("body")
    if not body:
        raise ValueError("body required")
    public = params.get("public")
    if public is None:
        public = True
    tid = urllib.parse.quote(str(ticket_id), safe="")
    result = request("PUT", f"/api/v2/tickets/{tid}.json", token, data={
        "ticket": {"comment": {"body": body, "public": bool(public)}},
    })
    updated = (result or {}).get("ticket") or {}
    print(json.dumps({"id": updated.get("id"), "status": updated.get("status"),
                      "public": bool(public), "commented": True}))


HANDLERS = {
    "zendesk.search": search,
    "zendesk.list_tickets": list_tickets,
    "zendesk.get_ticket": get_ticket,
    "zendesk.search_help_center": search_help_center,
    "zendesk.get_user": get_user,
    "zendesk.create_ticket": create_ticket,
    "zendesk.update_ticket": update_ticket,
    "zendesk.add_comment": add_comment,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (subdomain and client_id and client_secret):
        print(json.dumps({"error": "Missing Zendesk credentials: connect the Zendesk integration first (subdomain, clientId, clientSecret)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
