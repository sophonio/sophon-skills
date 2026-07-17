"""Outlook Mail integration skill — Microsoft 365 mailbox via Microsoft Graph (app-only).

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (tenantId, clientId, clientSecret, userId).

Auth is app-only (OAuth2 client-credentials): we POST to the tenant token endpoint to obtain an
access token, then call Microsoft Graph as https://graph.microsoft.com/v1.0/users/{userId}/...
with a Bearer token. App-only requires an explicit user mailbox and works only for Microsoft 365
work/school accounts (not consumer outlook.com). All message reads send
Prefer: outlook.body-content-type="text" so bodies come back as plain text.
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
PREFER_TEXT = {"Prefer": 'outlook.body-content-type="text"'}
LIST_SELECT = "id,subject,from,receivedDateTime,isRead,hasAttachments"


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
            "User-Agent": "sophon-outlook-mail-skill",
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


def request(method, path, token, data=None, query=None, headers=None):
    """Make an authenticated request to Microsoft Graph. Returns parsed JSON (or None for 204)."""
    url = f"{GRAPH_BASE}/users/{urllib.parse.quote(user_id, safe='')}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    all_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "sophon-outlook-mail-skill",
    }
    if headers:
        all_headers.update(headers)
    if body is not None:
        all_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=all_headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
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


def address_of(recipient):
    return ((recipient or {}).get("emailAddress") or {}).get("address")


def to_recipients(addresses):
    return [{"emailAddress": {"address": addr}} for addr in (addresses or [])]


def message_summary(msg):
    return {
        "id": msg.get("id"),
        "subject": msg.get("subject"),
        "from": address_of(msg.get("from")),
        "receivedDateTime": msg.get("receivedDateTime"),
        "isRead": msg.get("isRead"),
        "hasAttachments": msg.get("hasAttachments"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_messages():
    token = get_token()
    folder = params.get("folder") or "inbox"
    limit = clamp(params.get("limit", 25), 25, 50)
    result = request(
        "GET",
        f"/mailFolders/{urllib.parse.quote(str(folder), safe='')}/messages",
        token,
        query={
            "$top": limit,
            "$select": LIST_SELECT,
            "$orderby": "receivedDateTime desc",
        },
        headers=PREFER_TEXT,
    )
    messages = [message_summary(m) for m in (result or {}).get("value", [])]
    print(json.dumps({"count": len(messages), "messages": messages}))


def search_messages():
    token = get_token()
    search = params.get("search")
    filter_expr = params.get("filter")
    if search and filter_expr:
        raise ValueError("Provide either search or filter, not both")
    if not search and not filter_expr:
        raise ValueError("Provide a search phrase or an OData filter expression")
    limit = clamp(params.get("limit", 25), 25, 50)
    query = {"$top": limit, "$select": LIST_SELECT}
    if search:
        # Graph requires the $search value in double quotes; escape embedded quotes.
        # $search cannot be combined with $orderby.
        escaped = str(search).replace('\\', '\\\\').replace('"', '\\"')
        query["$search"] = f'"{escaped}"'
    else:
        query["$filter"] = filter_expr
    result = request("GET", "/messages", token, query=query, headers=PREFER_TEXT)
    messages = [message_summary(m) for m in (result or {}).get("value", [])]
    print(json.dumps({"count": len(messages), "messages": messages}))


def get_message():
    token = get_token()
    message_id = params.get("messageId")
    if not message_id:
        raise ValueError("messageId required")
    msg_path = f"/messages/{urllib.parse.quote(str(message_id), safe='')}"
    msg = request(
        "GET",
        msg_path,
        token,
        query={"$select": f"{LIST_SELECT},toRecipients,ccRecipients,body"},
        headers=PREFER_TEXT,
    ) or {}
    attachments = []
    if msg.get("hasAttachments"):
        att = request("GET", f"{msg_path}/attachments", token,
                      query={"$select": "name,size,contentType"}) or {}
        attachments = [{
            "name": a.get("name"),
            "size": a.get("size"),
            "contentType": a.get("contentType"),
        } for a in att.get("value", [])]
    print(json.dumps({
        "id": msg.get("id"),
        "subject": msg.get("subject"),
        "from": address_of(msg.get("from")),
        "to": [address_of(r) for r in msg.get("toRecipients") or []],
        "cc": [address_of(r) for r in msg.get("ccRecipients") or []],
        "receivedDateTime": msg.get("receivedDateTime"),
        "isRead": msg.get("isRead"),
        "hasAttachments": msg.get("hasAttachments"),
        "body": (msg.get("body") or {}).get("content"),
        "attachments": attachments,
    }))


def list_folders():
    token = get_token()
    result = request("GET", "/mailFolders", token, query={"$top": 50})
    folders = [{
        "id": f.get("id"),
        "displayName": f.get("displayName"),
        "totalItemCount": f.get("totalItemCount"),
        "unreadItemCount": f.get("unreadItemCount"),
    } for f in (result or {}).get("value", [])]
    print(json.dumps({"count": len(folders), "folders": folders}))


def move_message():
    token = get_token()
    message_id = params.get("messageId")
    destination = params.get("destinationId")
    if not message_id:
        raise ValueError("messageId required")
    if not destination:
        raise ValueError("destinationId required (a folder id or a well-known name like inbox, archive, deleteditems)")
    moved = request(
        "POST",
        f"/messages/{urllib.parse.quote(str(message_id), safe='')}/move",
        token,
        data={"destinationId": destination},
    ) or {}
    print(json.dumps({"id": moved.get("id"), "subject": moved.get("subject"),
                      "parentFolderId": moved.get("parentFolderId"), "moved": True}))


def create_draft():
    token = get_token()
    reply_to = params.get("replyToMessageId")
    subject = params.get("subject")
    to = params.get("to")
    body_text = params.get("body")
    if reply_to:
        # Create a reply draft in the same thread, then patch in the body text.
        draft = request(
            "POST",
            f"/messages/{urllib.parse.quote(str(reply_to), safe='')}/createReply",
            token,
            data={},
        ) or {}
        draft_id = draft.get("id")
        if not draft_id:
            raise RuntimeError("Reply draft was not created")
        patch = {}
        if body_text:
            patch["body"] = {"contentType": "text", "content": body_text}
        if subject:
            patch["subject"] = subject
        if to:
            patch["toRecipients"] = to_recipients(to)
        if patch:
            draft = request(
                "PATCH",
                f"/messages/{urllib.parse.quote(str(draft_id), safe='')}",
                token,
                data=patch,
            ) or draft
    else:
        if not subject:
            raise ValueError("subject required when not replying to a message")
        if not to:
            raise ValueError("to required when not replying to a message")
        payload = {
            "subject": subject,
            "toRecipients": to_recipients(to),
            "body": {"contentType": "text", "content": body_text or ""},
        }
        draft = request("POST", "/messages", token, data=payload) or {}
    print(json.dumps({"id": draft.get("id"), "subject": draft.get("subject"),
                      "isDraft": True, "note": "Draft created; nothing was sent."}))


def send_mail():
    token = get_token()
    to = params.get("to")
    subject = params.get("subject")
    body_text = params.get("body")
    if not to:
        raise ValueError("to required (list of recipient email addresses)")
    if not subject:
        raise ValueError("subject required")
    if body_text is None:
        raise ValueError("body required")
    message = {
        "subject": subject,
        "body": {"contentType": "text", "content": body_text},
        "toRecipients": to_recipients(to),
    }
    cc = params.get("cc")
    if cc:
        message["ccRecipients"] = to_recipients(cc)
    request("POST", "/sendMail", token, data={"message": message, "saveToSentItems": True})
    print(json.dumps({"sent": True, "note": "accepted for delivery"}))


HANDLERS = {
    "mail.list_messages": list_messages,
    "mail.search_messages": search_messages,
    "mail.get_message": get_message,
    "mail.list_folders": list_folders,
    "mail.move_message": move_message,
    "mail.create_draft": create_draft,
    "mail.send_mail": send_mail,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (tenant_id and client_id and client_secret and user_id):
        print(json.dumps({"error": "Missing Microsoft Graph credentials: connect the Outlook Mail integration first (tenantId, clientId, clientSecret, userId)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
