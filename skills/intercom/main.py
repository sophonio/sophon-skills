"""Intercom integration skill — search conversations and contacts, read Help Center articles,
add internal notes, reply to customers, and close/snooze/assign conversations.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (baseUrl, accessToken).

Auth is a static internal-app Access Token sent as "Authorization: Bearer {accessToken}" with an
"Intercom-Version: 2.15" header on every call. The base URL is regional (api.intercom.io,
api.eu.intercom.io, or api.au.intercom.io). Message bodies are HTML; summaries strip tags with a
small regex helper.
"""

import html
import json
import re
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("baseUrl") or "https://api.intercom.io").rstrip("/")
access_token = params.get("accessToken") or ""

INTERCOM_VERSION = "2.15"

_admin_cache = {}


def request(method, path, data=None, query=None):
    """Make an authenticated request to Intercom. Returns parsed JSON (or None for 204/empty)."""
    url = f"{base_url}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Intercom-Version": INTERCOM_VERSION,
        "User-Agent": "sophon-intercom-skill",
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
            errors = parsed.get("errors")
            if isinstance(errors, list) and errors:
                msg = "; ".join(
                    str(err.get("message") or err.get("code") or "") for err in errors if err
                ).strip("; ") or detail
            else:
                msg = detail
        except (ValueError, TypeError, AttributeError):
            msg = detail
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            if retry_after:
                msg = f"{msg} (rate limited; retry after {retry_after}s)"
        raise RuntimeError(f"Intercom API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Intercom: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text):
    """Naively strip HTML tags and collapse whitespace for plain-text summaries."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", text))).strip()


def get_admin_id():
    """Resolve the token's admin id via GET /me (cached in-process)."""
    if "id" not in _admin_cache:
        me = request("GET", "/me") or {}
        admin_id = me.get("id")
        if not admin_id:
            raise RuntimeError("Could not resolve the admin id for this access token from /me")
        _admin_cache["id"] = admin_id
    return _admin_cache["id"]


def conversation_summary(c):
    source = c.get("source") or {}
    return {
        "id": c.get("id"),
        "state": c.get("state"),
        "priority": c.get("priority"),
        "read": c.get("read"),
        "subject": strip_html(source.get("subject")),
        "snippet": strip_html(source.get("body"))[:200],
        "adminAssigneeId": c.get("admin_assignee_id"),
        "teamAssigneeId": c.get("team_assignee_id"),
        "createdAt": c.get("created_at"),
        "updatedAt": c.get("updated_at"),
    }


def contact_summary(c):
    return {
        "id": c.get("id"),
        "role": c.get("role"),
        "name": c.get("name"),
        "email": c.get("email"),
        "phone": c.get("phone"),
        "externalId": c.get("external_id"),
        "createdAt": c.get("created_at"),
        "lastSeenAt": c.get("last_seen_at"),
    }


def next_cursor(result):
    return (((result or {}).get("pages") or {}).get("next") or {}).get("starting_after")


# --- Tool handlers ---------------------------------------------------------

def search_conversations():
    terms = []
    state = params.get("state")
    if state:
        if state not in ("open", "closed", "snoozed"):
            raise ValueError("state must be one of: open, closed, snoozed")
        terms.append({"field": "state", "operator": "=", "value": state})
    assignee_id = params.get("assigneeId")
    if assignee_id not in (None, ""):
        try:
            assignee_id = int(assignee_id)
        except (TypeError, ValueError):
            pass
        terms.append({"field": "admin_assignee_id", "operator": "=", "value": assignee_id})
    updated_since = params.get("updatedSince")
    if updated_since not in (None, ""):
        try:
            updated_since = int(updated_since)
        except (TypeError, ValueError):
            raise ValueError("updatedSince must be a Unix epoch timestamp (seconds)")
        terms.append({"field": "updated_at", "operator": ">", "value": updated_since})
    if not terms:
        # No filters given: fall back to a match-all query so a bare listing still works.
        terms.append({"field": "updated_at", "operator": ">", "value": 0})
    query = terms[0] if len(terms) == 1 else {"operator": "AND", "value": terms}
    pagination = {"per_page": clamp(params.get("limit", 20), 20, 50)}
    if params.get("cursor"):
        pagination["starting_after"] = params["cursor"]
    result = request("POST", "/conversations/search", data={"query": query, "pagination": pagination})
    conversations = [conversation_summary(c) for c in (result or {}).get("conversations", [])]
    out = {"count": len(conversations), "conversations": conversations}
    cursor = next_cursor(result)
    if cursor:
        out["nextCursor"] = cursor
    print(json.dumps(out))


def get_conversation():
    conversation_id = params.get("conversationId")
    if not conversation_id:
        raise ValueError("conversationId required")
    c = request("GET", f"/conversations/{urllib.parse.quote(str(conversation_id), safe='')}") or {}
    source = c.get("source") or {}
    parts = ((c.get("conversation_parts") or {}).get("conversation_parts")) or []
    trimmed_parts = [{
        "partType": p.get("part_type"),
        "authorType": ((p.get("author") or {}).get("type")),
        "authorName": ((p.get("author") or {}).get("name")),
        "body": strip_html(p.get("body")),
        "createdAt": p.get("created_at"),
    } for p in parts[-20:]]
    print(json.dumps({
        "id": c.get("id"),
        "state": c.get("state"),
        "priority": c.get("priority"),
        "subject": strip_html(source.get("subject")),
        "snippet": strip_html(source.get("body"))[:500],
        "contactIds": [x.get("id") for x in ((c.get("contacts") or {}).get("contacts")) or []],
        "adminAssigneeId": c.get("admin_assignee_id"),
        "teamAssigneeId": c.get("team_assignee_id"),
        "createdAt": c.get("created_at"),
        "updatedAt": c.get("updated_at"),
        "totalParts": len(parts),
        "conversationParts": trimmed_parts,
    }))


def search_contacts():
    email = params.get("email")
    field = params.get("field")
    value = params.get("value")
    if email:
        query = {"field": "email", "operator": "=", "value": email}
    elif field and value not in (None, ""):
        operator = params.get("operator") or "="
        if operator in ("IN", "NIN"):
            # Intercom requires an array value for IN/NIN; accept a comma-separated string.
            if isinstance(value, str):
                value = [v.strip() for v in value.split(",") if v.strip()]
            elif not isinstance(value, list):
                value = [value]
            if not value:
                raise ValueError("value must contain at least one item for IN/NIN")
        query = {"field": field, "operator": operator, "value": value}
    else:
        raise ValueError("Provide email, or field and value, to search contacts")
    pagination = {"per_page": clamp(params.get("limit", 20), 20, 50)}
    if params.get("cursor"):
        pagination["starting_after"] = params["cursor"]
    result = request("POST", "/contacts/search", data={"query": query, "pagination": pagination})
    contacts = [contact_summary(c) for c in (result or {}).get("data", [])]
    out = {"count": len(contacts), "contacts": contacts}
    cursor = next_cursor(result)
    if cursor:
        out["nextCursor"] = cursor
    print(json.dumps(out))


def get_contact():
    contact_id = params.get("contactId")
    if not contact_id:
        raise ValueError("contactId required")
    c = request("GET", f"/contacts/{urllib.parse.quote(str(contact_id), safe='')}") or {}
    location = c.get("location") or {}
    profile = contact_summary(c)
    profile.update({
        "updatedAt": c.get("updated_at"),
        "signedUpAt": c.get("signed_up_at"),
        "location": {
            "city": location.get("city"),
            "region": location.get("region"),
            "country": location.get("country"),
        },
        "companies": [x.get("id") for x in ((c.get("companies") or {}).get("data")) or []],
        "customAttributes": c.get("custom_attributes") or {},
    })
    print(json.dumps(profile))


def list_articles():
    page = params.get("page")
    if page not in (None, ""):
        try:
            page = int(page)
        except (TypeError, ValueError):
            raise ValueError("page must be a positive integer")
        if page < 1:
            raise ValueError("page must be a positive integer")
    else:
        page = None
    result = request("GET", "/articles", query={
        "per_page": clamp(params.get("limit", 25), 25, 50),
        "page": page,
    })
    articles = [{
        "id": a.get("id"),
        "title": a.get("title"),
        "state": a.get("state"),
        "url": a.get("url"),
    } for a in (result or {}).get("data", [])]
    print(json.dumps({
        "count": len(articles),
        "totalCount": (result or {}).get("total_count"),
        "articles": articles,
    }))


def add_note():
    conversation_id = params.get("conversationId")
    body = params.get("body")
    if not conversation_id:
        raise ValueError("conversationId required")
    if not body:
        raise ValueError("body required")
    c = request(
        "POST",
        f"/conversations/{urllib.parse.quote(str(conversation_id), safe='')}/reply",
        data={"message_type": "note", "type": "admin", "admin_id": get_admin_id(), "body": body},
    ) or {}
    print(json.dumps({"id": c.get("id"), "state": c.get("state"), "noteAdded": True}))


def reply_customer():
    conversation_id = params.get("conversationId")
    body = params.get("body")
    if not conversation_id:
        raise ValueError("conversationId required")
    if not body:
        raise ValueError("body required")
    c = request(
        "POST",
        f"/conversations/{urllib.parse.quote(str(conversation_id), safe='')}/reply",
        data={"message_type": "comment", "type": "admin", "admin_id": get_admin_id(), "body": body},
    ) or {}
    print(json.dumps({"id": c.get("id"), "state": c.get("state"), "replied": True}))


def update_conversation():
    conversation_id = params.get("conversationId")
    action = params.get("action")
    if not conversation_id:
        raise ValueError("conversationId required")
    if action not in ("close", "snooze", "assign"):
        raise ValueError("action must be one of: close, snooze, assign")
    admin_id = get_admin_id()
    if action == "close":
        payload = {"message_type": "close", "type": "admin", "admin_id": admin_id}
    elif action == "snooze":
        snoozed_until = params.get("snoozedUntil")
        try:
            snoozed_until = int(snoozed_until)
        except (TypeError, ValueError):
            raise ValueError("snoozedUntil (Unix epoch seconds) is required to snooze")
        payload = {"message_type": "snoozed", "admin_id": admin_id, "snoozed_until": snoozed_until}
    else:  # assign
        assignee_id = params.get("assigneeId")
        if assignee_id in (None, ""):
            raise ValueError("assigneeId is required to assign")
        assignee_type = params.get("assigneeType") or "admin"
        if assignee_type not in ("admin", "team"):
            raise ValueError("assigneeType must be admin or team")
        try:
            assignee_id = int(assignee_id)
        except (TypeError, ValueError):
            pass
        payload = {
            "message_type": "assignment",
            "type": assignee_type,
            "admin_id": admin_id,
            "assignee_id": assignee_id,
        }
    c = request(
        "POST",
        f"/conversations/{urllib.parse.quote(str(conversation_id), safe='')}/parts",
        data=payload,
    ) or {}
    print(json.dumps({
        "id": c.get("id"),
        "state": c.get("state"),
        "action": action,
        "adminAssigneeId": c.get("admin_assignee_id"),
        "teamAssigneeId": c.get("team_assignee_id"),
        "snoozedUntil": c.get("snoozed_until"),
    }))


HANDLERS = {
    "intercom.search_conversations": search_conversations,
    "intercom.get_conversation": get_conversation,
    "intercom.search_contacts": search_contacts,
    "intercom.get_contact": get_contact,
    "intercom.list_articles": list_articles,
    "intercom.add_note": add_note,
    "intercom.reply_customer": reply_customer,
    "intercom.update_conversation": update_conversation,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not access_token:
        print(json.dumps({"error": "Missing Intercom credentials: connect the Intercom integration first (baseUrl, accessToken)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
