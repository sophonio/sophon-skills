"""Freshdesk integration skill — helpdesk tickets, contacts, and notes via the Freshdesk REST API v2.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (baseUrl, apiKey).

Auth is a personal API key sent as HTTP Basic auth: base64(apiKey + ":X") — Freshdesk ignores
the password, so "X" is used as a dummy. All requests go to {baseUrl}/api/v2. Rate limits are
plan-dependent per-minute quotas; a 429 response includes a Retry-After header which we surface.
"""

import base64
import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("baseUrl") or "").rstrip("/")
api_key = params.get("apiKey") or ""

STATUS_NAMES = {2: "Open", 3: "Pending", 4: "Resolved", 5: "Closed"}
PRIORITY_NAMES = {1: "Low", 2: "Medium", 3: "High", 4: "Urgent"}


def request(method, path, data=None, query=None):
    """Make an authenticated request to the Freshdesk API. Returns parsed JSON (or None for 204)."""
    url = f"{base_url}/api/v2{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    auth = base64.b64encode(f"{api_key}:X".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Accept": "application/json",
        "User-Agent": "sophon-freshdesk-skill",
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
        try:
            parsed = json.loads(detail)
            parts = []
            if parsed.get("description"):
                parts.append(parsed["description"])
            if parsed.get("message"):
                parts.append(parsed["message"])
            for err in parsed.get("errors") or []:
                field = err.get("field")
                message = err.get("message") or err.get("code") or ""
                parts.append(f"{field}: {message}" if field else message)
            msg = "; ".join(p for p in parts if p) or detail
        except (ValueError, TypeError, AttributeError):
            msg = detail
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            hint = f" Retry after {retry_after} seconds." if retry_after else ""
            raise RuntimeError(
                f"Freshdesk API error 429: rate limit exceeded (limits are per-minute and "
                f"plan-dependent; invalid requests count too).{hint}"
            ) from e
        raise RuntimeError(f"Freshdesk API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Freshdesk: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def ticket_summary(t):
    return {
        "id": t.get("id"),
        "subject": t.get("subject"),
        "status": STATUS_NAMES.get(t.get("status"), t.get("status")),
        "priority": PRIORITY_NAMES.get(t.get("priority"), t.get("priority")),
        "requester_id": t.get("requester_id"),
        "responder_id": t.get("responder_id"),
        "created_at": t.get("created_at"),
        "updated_at": t.get("updated_at"),
        "due_by": t.get("due_by"),
        "tags": t.get("tags") or [],
    }


def contact_summary(c):
    return {
        "id": c.get("id"),
        "name": c.get("name"),
        "email": c.get("email"),
        "phone": c.get("phone"),
        "mobile": c.get("mobile"),
        "company_id": c.get("company_id"),
        "active": c.get("active"),
        "created_at": c.get("created_at"),
    }


def conversation_summary(c):
    return {
        "id": c.get("id"),
        "body_text": c.get("body_text"),
        "private": c.get("private"),
        "incoming": c.get("incoming"),
        "user_id": c.get("user_id"),
        "created_at": c.get("created_at"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_tickets():
    per_page = clamp(params.get("limit", 30), 30, 100)
    result = request("GET", "/tickets", query={
        "filter": params.get("filter"),
        "updated_since": params.get("updatedSince"),
        "order_by": params.get("orderBy"),
        "order_type": params.get("orderType"),
        "per_page": per_page,
    })
    tickets = [ticket_summary(t) for t in (result or [])]
    print(json.dumps({"count": len(tickets), "tickets": tickets}))


def get_ticket():
    ticket_id = params.get("ticketId")
    if not ticket_id:
        raise ValueError("ticketId required")
    ticket_id = urllib.parse.quote(str(ticket_id), safe="")
    ticket = request("GET", f"/tickets/{ticket_id}") or {}
    # The ?include=conversations shortcut returns only the first 10 conversations,
    # so fetch them from the dedicated endpoint instead.
    per_page = clamp(params.get("conversationLimit", 30), 30, 100)
    conversations = request("GET", f"/tickets/{ticket_id}/conversations",
                            query={"per_page": per_page}) or []
    print(json.dumps({
        "id": ticket.get("id"),
        "subject": ticket.get("subject"),
        "description_text": ticket.get("description_text"),
        "status": STATUS_NAMES.get(ticket.get("status"), ticket.get("status")),
        "priority": PRIORITY_NAMES.get(ticket.get("priority"), ticket.get("priority")),
        "requester_id": ticket.get("requester_id"),
        "responder_id": ticket.get("responder_id"),
        "type": ticket.get("type"),
        "tags": ticket.get("tags") or [],
        "created_at": ticket.get("created_at"),
        "updated_at": ticket.get("updated_at"),
        "due_by": ticket.get("due_by"),
        "conversations": [conversation_summary(c) for c in conversations],
    }))


def search_tickets():
    query = params.get("query") or ""
    if not query:
        raise ValueError("query required")
    # Freshdesk's 512-character limit applies to the quoted query string, and we add the
    # surrounding double quotes below, so the user-supplied query may be at most 510 chars.
    if len(query) > 510:
        raise ValueError("query must be 510 characters or fewer (Freshdesk's 512-character limit includes the surrounding quotes)")
    # Freshdesk requires the query string to be wrapped in double quotes inside the URL param.
    result = request("GET", "/search/tickets", query={"query": f'"{query}"'}) or {}
    tickets = [ticket_summary(t) for t in result.get("results") or []]
    print(json.dumps({"count": len(tickets), "total": result.get("total"), "tickets": tickets}))


def search_contacts():
    email = params.get("email")
    query = params.get("query")
    if email:
        # Exact email lookup via the contacts list endpoint.
        result = request("GET", "/contacts", query={"email": email}) or []
        contacts = [contact_summary(c) for c in result]
    elif query:
        if len(query) > 510:
            raise ValueError("query must be 510 characters or fewer (Freshdesk's 512-character limit includes the surrounding quotes)")
        result = request("GET", "/search/contacts", query={"query": f'"{query}"'}) or {}
        contacts = [contact_summary(c) for c in result.get("results") or []]
    else:
        raise ValueError("provide either query (search expression) or email (exact match)")
    print(json.dumps({"count": len(contacts), "contacts": contacts}))


def create_ticket():
    subject = params.get("subject")
    description = params.get("description")
    email = params.get("email")
    if not subject or not description or not email:
        raise ValueError("subject, description, and email are required")
    payload = {
        "subject": subject,
        "description": description,
        "email": email,
        "priority": int(params.get("priority") or 1),
        "status": int(params.get("status") or 2),
    }
    if params.get("tags"):
        payload["tags"] = params["tags"]
    ticket = request("POST", "/tickets", data=payload) or {}
    print(json.dumps({
        "id": ticket.get("id"),
        "subject": ticket.get("subject"),
        "status": STATUS_NAMES.get(ticket.get("status"), ticket.get("status")),
        "priority": PRIORITY_NAMES.get(ticket.get("priority"), ticket.get("priority")),
        "created_at": ticket.get("created_at"),
    }))


def update_ticket():
    ticket_id = params.get("ticketId")
    if not ticket_id:
        raise ValueError("ticketId required")
    payload = {}
    if params.get("status") is not None:
        payload["status"] = int(params["status"])
    if params.get("priority") is not None:
        payload["priority"] = int(params["priority"])
    if params.get("responderId") is not None:
        payload["responder_id"] = int(params["responderId"])
    if params.get("tags") is not None:
        payload["tags"] = params["tags"]
    if not payload:
        raise ValueError("nothing to update: provide status, priority, responderId, and/or tags")
    ticket = request("PUT", f"/tickets/{urllib.parse.quote(str(ticket_id), safe='')}",
                     data=payload) or {}
    print(json.dumps({
        "id": ticket.get("id"),
        "subject": ticket.get("subject"),
        "status": STATUS_NAMES.get(ticket.get("status"), ticket.get("status")),
        "priority": PRIORITY_NAMES.get(ticket.get("priority"), ticket.get("priority")),
        "responder_id": ticket.get("responder_id"),
        "tags": ticket.get("tags") or [],
        "updated": True,
    }))


def add_note():
    ticket_id = params.get("ticketId")
    body = params.get("body")
    if not ticket_id:
        raise ValueError("ticketId required")
    if not body:
        raise ValueError("body required")
    private = params.get("private")
    if private is None:
        private = True
    payload = {"body": body, "private": bool(private)}
    note = request("POST", f"/tickets/{urllib.parse.quote(str(ticket_id), safe='')}/notes",
                   data=payload) or {}
    print(json.dumps({
        "id": note.get("id"),
        "ticket_id": ticket_id,
        "private": note.get("private"),
        "created_at": note.get("created_at"),
    }))


HANDLERS = {
    "freshdesk.list_tickets": list_tickets,
    "freshdesk.get_ticket": get_ticket,
    "freshdesk.search_tickets": search_tickets,
    "freshdesk.search_contacts": search_contacts,
    "freshdesk.create_ticket": create_ticket,
    "freshdesk.update_ticket": update_ticket,
    "freshdesk.add_note": add_note,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and api_key):
        print(json.dumps({"error": "Missing Freshdesk credentials: connect the Freshdesk integration first (baseUrl, apiKey)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
