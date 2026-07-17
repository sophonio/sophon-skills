"""Offline mock-HTTP integration tests for the outlook-mail Sophon skill."""
import sys
import urllib.parse

from mockhttp import run_tool, resp, err, check

ok = True

CREDS = {
    "tenantId": "11111111-2222-3333-4444-555555555555",
    "clientId": "app-client-id",
    "clientSecret": "s3cr3t-value-XYZ",
    "userId": "mailbox@contoso.com",
}
TOKEN_URL = ("https://login.microsoftonline.com/"
             "11111111-2222-3333-4444-555555555555/oauth2/v2.0/token")
TOKEN_BODY = urllib.parse.urlencode({
    "grant_type": "client_credentials",
    "client_id": CREDS["clientId"],
    "client_secret": CREDS["clientSecret"],
    "scope": "https://graph.microsoft.com/.default",
})
TOKEN_OK = resp(200, body={"access_token": "graph-tok-123", "token_type": "Bearer"})
USER_BASE = "https://graph.microsoft.com/v1.0/users/mailbox%40contoso.com"


def p(tool, **kw):
    d = dict(CREDS)
    d["tool"] = tool
    d.update(kw)
    return d


GRAPH_MSG = {
    "@odata.etag": "W/\"etag\"",
    "id": "AAMkAGI1",
    "subject": "Quarterly report",
    "from": {"emailAddress": {"name": "Ann Lee", "address": "ann@contoso.com"}},
    "receivedDateTime": "2026-07-15T09:30:00Z",
    "isRead": False,
    "hasAttachments": True,
    "internetMessageId": "<raw@contoso.com>",
    "changeKey": "CQAAABYA",
}

# ---------------------------------------------------------------- 1. AUTH EXACTNESS
print("[auth exactness — token flow + Bearer + Prefer]")
out, ex = run_tool("outlook-mail", p("mail.list_messages"),
                   [TOKEN_OK, resp(200, body={"value": [GRAPH_MSG]})])
ok &= check("token: exactly two requests (token + graph)", len(ex) == 2, repr(ex))
ok &= check("token: POST method", ex[0].method == "POST", ex[0].method)
ok &= check("token: exact tenant token URL", ex[0].url == TOKEN_URL, ex[0].url)
ok &= check("token: byte-exact form body", ex[0].body == TOKEN_BODY, str(ex[0].body))
ok &= check("token: form-urlencoded content type",
            ex[0].headers.get("content-type") == "application/x-www-form-urlencoded",
            str(ex[0].headers))
ok &= check("graph: Bearer token header",
            ex[1].headers.get("authorization") == "Bearer graph-tok-123", str(ex[1].headers))
ok &= check("graph: Prefer text body header on message read",
            ex[1].headers.get("prefer") == 'outlook.body-content-type="text"',
            str(ex[1].headers))
ok &= check("graph: Accept json", ex[1].headers.get("accept") == "application/json",
            str(ex[1].headers))

# ---------------------------------------------------------------- 2. HAPPY PATHS
print("[happy path — mail.list_messages]")
qs = urllib.parse.parse_qs(urllib.parse.urlsplit(ex[1].url).query)
ok &= check("list: url targets inbox messages",
            ex[1].url.startswith(f"{USER_BASE}/mailFolders/inbox/messages?"), ex[1].url)
ok &= check("list: default $top=25", qs.get("$top") == ["25"], str(qs))
ok &= check("list: $select trimmed fields",
            qs.get("$select") == ["id,subject,from,receivedDateTime,isRead,hasAttachments"],
            str(qs))
ok &= check("list: $orderby newest first",
            qs.get("$orderby") == ["receivedDateTime desc"], str(qs))
ok &= check("list: count shaping", out.get("count") == 1, str(out)[:200])
m = (out.get("messages") or [{}])[0]
ok &= check("list: from flattened to address", m.get("from") == "ann@contoso.com", str(m))
ok &= check("list: trimmed fields present",
            m.get("id") == "AAMkAGI1" and m.get("subject") == "Quarterly report"
            and m.get("receivedDateTime") == "2026-07-15T09:30:00Z"
            and m.get("isRead") is False and m.get("hasAttachments") is True, str(m))
ok &= check("list: raw payload fields absent",
            "@odata.etag" not in m and "internetMessageId" not in m and "changeKey" not in m,
            str(m))

print("[happy path — mail.get_message with attachments]")
full_msg = dict(GRAPH_MSG)
full_msg.update({
    "toRecipients": [{"emailAddress": {"address": "me@contoso.com"}}],
    "ccRecipients": [{"emailAddress": {"address": "cc@contoso.com"}}],
    "body": {"contentType": "text", "content": "Hello there"},
})
out, ex = run_tool("outlook-mail", p("mail.get_message", messageId="AAMkAGI1"),
                   [TOKEN_OK,
                    resp(200, body=full_msg),
                    resp(200, body={"value": [{"name": "a.pdf", "size": 1234,
                                               "contentType": "application/pdf",
                                               "contentBytes": "AAAA"}]})])
ok &= check("get: three requests (token + msg + attachments)", len(ex) == 3, repr(ex))
ok &= check("get: message url",
            ex[1].url.startswith(f"{USER_BASE}/messages/AAMkAGI1?"), ex[1].url)
ok &= check("get: Prefer text header", ex[1].headers.get("prefer")
            == 'outlook.body-content-type="text"', str(ex[1].headers))
ok &= check("get: attachments url",
            ex[2].url.startswith(f"{USER_BASE}/messages/AAMkAGI1/attachments?"), ex[2].url)
ok &= check("get: body flattened to text", out.get("body") == "Hello there", str(out)[:300])
ok &= check("get: to/cc flattened",
            out.get("to") == ["me@contoso.com"] and out.get("cc") == ["cc@contoso.com"],
            str(out)[:300])
ok &= check("get: attachment metadata only (no contentBytes)",
            out.get("attachments") == [{"name": "a.pdf", "size": 1234,
                                        "contentType": "application/pdf"}], str(out)[:300])
ok &= check("get: raw fields absent", "@odata.etag" not in out and "changeKey" not in out,
            str(out)[:300])

print("[happy path — mail.list_folders]")
out, ex = run_tool("outlook-mail", p("mail.list_folders"),
                   [TOKEN_OK,
                    resp(200, body={"value": [
                        {"id": "f1", "displayName": "Inbox", "totalItemCount": 10,
                         "unreadItemCount": 2, "parentFolderId": "root", "childFolderCount": 0},
                        {"id": "f2", "displayName": "Archive", "totalItemCount": 5,
                         "unreadItemCount": 0, "parentFolderId": "root", "childFolderCount": 0},
                    ]})])
ok &= check("folders: url", ex[1].url.startswith(f"{USER_BASE}/mailFolders?"), ex[1].url)
ok &= check("folders: count", out.get("count") == 2, str(out)[:200])
f0 = (out.get("folders") or [{}])[0]
ok &= check("folders: trimmed shape",
            f0 == {"id": "f1", "displayName": "Inbox", "totalItemCount": 10,
                   "unreadItemCount": 2}, str(f0))

print("[happy path — mail.search_messages ($search quoting, no $orderby)]")
out, ex = run_tool("outlook-mail", p("mail.search_messages", search='project "alpha"'),
                   [TOKEN_OK, resp(200, body={"value": [GRAPH_MSG]})])
qs = urllib.parse.parse_qs(urllib.parse.urlsplit(ex[1].url).query)
ok &= check("search: url targets /messages",
            ex[1].url.startswith(f"{USER_BASE}/messages?"), ex[1].url)
ok &= check("search: $search wrapped in quotes with escaping",
            qs.get("$search") == ['"project \\"alpha\\""'], str(qs))
ok &= check("search: no $orderby with $search", "$orderby" not in qs, str(qs))
ok &= check("search: Prefer text header", ex[1].headers.get("prefer")
            == 'outlook.body-content-type="text"', str(ex[1].headers))
ok &= check("search: count shaping", out.get("count") == 1, str(out)[:200])

print("[happy path — mail.search_messages with filter]")
out, ex = run_tool("outlook-mail", p("mail.search_messages", filter="isRead eq false"),
                   [TOKEN_OK, resp(200, body={"value": []})])
qs = urllib.parse.parse_qs(urllib.parse.urlsplit(ex[1].url).query)
ok &= check("filter: $filter passed through", qs.get("$filter") == ["isRead eq false"], str(qs))
ok &= check("filter: empty result count 0", out.get("count") == 0 and out.get("messages") == [],
            str(out)[:200])

# ---------------------------------------------------------------- 3. WRITE PATHS
print("[write path — mail.move_message]")
out, ex = run_tool("outlook-mail",
                   p("mail.move_message", messageId="AAMkAGI1", destinationId="archive"),
                   [TOKEN_OK,
                    resp(201, body={"id": "AAMkNEW", "subject": "Quarterly report",
                                    "parentFolderId": "arch-folder-id"})])
ok &= check("move: POST method", ex[1].method == "POST", ex[1].method)
ok &= check("move: exact url", ex[1].url == f"{USER_BASE}/messages/AAMkAGI1/move", ex[1].url)
ok &= check("move: exact JSON body {destinationId}",
            ex[1].json == {"destinationId": "archive"}, str(ex[1].body))
ok &= check("move: json content type",
            (ex[1].headers.get("content-type") or "").startswith("application/json"),
            str(ex[1].headers))
ok &= check("move: shaped output",
            out.get("moved") is True and out.get("id") == "AAMkNEW"
            and out.get("parentFolderId") == "arch-folder-id", str(out))

print("[write path — mail.send_mail on 202]")
out, ex = run_tool("outlook-mail",
                   p("mail.send_mail", to=["a@x.co", "b@x.co"], cc=["c@x.co"],
                     subject="Hi", body="Body text"),
                   [TOKEN_OK, resp(202, body=b"")])
ok &= check("send: POST to /sendMail", ex[1].method == "POST"
            and ex[1].url == f"{USER_BASE}/sendMail", repr(ex[1]))
ok &= check("send: exact JSON body",
            ex[1].json == {"message": {"subject": "Hi",
                                       "body": {"contentType": "text", "content": "Body text"},
                                       "toRecipients": [{"emailAddress": {"address": "a@x.co"}},
                                                        {"emailAddress": {"address": "b@x.co"}}],
                                       "ccRecipients": [{"emailAddress": {"address": "c@x.co"}}]},
                           "saveToSentItems": True}, str(ex[1].body))
ok &= check("send: {'sent': true, ...} on 202", out.get("sent") is True, str(out))

print("[write path — mail.create_draft new draft]")
out, ex = run_tool("outlook-mail",
                   p("mail.create_draft", subject="Draft subj", to=["d@x.co"], body="draft body"),
                   [TOKEN_OK,
                    resp(201, body={"id": "DRAFT1", "subject": "Draft subj", "isDraft": True})])
ok &= check("draft: POST /messages", ex[1].method == "POST"
            and ex[1].url == f"{USER_BASE}/messages", repr(ex[1]))
ok &= check("draft: exact JSON body",
            ex[1].json == {"subject": "Draft subj",
                           "toRecipients": [{"emailAddress": {"address": "d@x.co"}}],
                           "body": {"contentType": "text", "content": "draft body"}},
            str(ex[1].body))
ok &= check("draft: shaped output", out.get("id") == "DRAFT1" and out.get("isDraft") is True,
            str(out))

# ---------------------------------------------------------------- 4. ERROR PATHS
print("[error path — Graph 401]")
out, ex = run_tool("outlook-mail", p("mail.list_messages"),
                   [TOKEN_OK,
                    err(401, body={"error": {"code": "InvalidAuthenticationToken",
                                             "message": "Access token has expired."}})])
ok &= check("401: friendly error object", isinstance(out.get("error"), str), str(out))
ok &= check("401: includes HTTP status", "401" in out.get("error", ""), str(out))
ok &= check("401: includes Graph message", "Access token has expired." in out.get("error", ""),
            str(out))
ok &= check("401: no Python traceback", "Traceback" not in str(out), str(out))

print("[error path — token endpoint 401]")
out, ex = run_tool("outlook-mail", p("mail.list_folders"),
                   [err(401, body={"error": "invalid_client",
                                   "error_description": "AADSTS7000215: Invalid client secret."})])
ok &= check("token 401: friendly error with status",
            "401" in out.get("error", "") and "AADSTS7000215" in out.get("error", ""), str(out))
ok &= check("token 401: no traceback", "Traceback" not in str(out), str(out))

print("[error path — Graph 429]")
out, ex = run_tool("outlook-mail", p("mail.list_messages"),
                   [TOKEN_OK,
                    err(429, body={"error": {"code": "TooManyRequests",
                                             "message": "Too many requests"}},
                        headers={"Retry-After": "30"})])
ok &= check("429: surfaces as error with status", "429" in out.get("error", ""), str(out))
ok &= check("429: no traceback", "Traceback" not in str(out), str(out))

print("[error path — mutually exclusive search+filter]")
out, ex = run_tool("outlook-mail",
                   p("mail.search_messages", search="x", filter="isRead eq false"),
                   [TOKEN_OK])
ok &= check("search+filter: ValueError surfaced as {'error': ...}",
            out.get("error") == "Provide either search or filter, not both", str(out))
ok &= check("search+filter: no Graph call made", len(ex) == 1, repr(ex))

print("[error path — neither search nor filter]")
out, ex = run_tool("outlook-mail", p("mail.search_messages"), [TOKEN_OK])
ok &= check("no-criteria: ValueError surfaced",
            out.get("error") == "Provide a search phrase or an OData filter expression", str(out))

# ---------------------------------------------------------------- 5. SECURITY PROBES
print("[security — path-ish messageId is percent-encoded]")
evil = "abc/../def?x=1"
safe_msg = dict(GRAPH_MSG)
safe_msg["hasAttachments"] = False
out, ex = run_tool("outlook-mail", p("mail.get_message", messageId=evil),
                   [TOKEN_OK, resp(200, body=safe_msg)])
path = urllib.parse.urlsplit(ex[1].url).path
ok &= check("id probe: fully percent-encoded in path",
            "abc%2F..%2Fdef%3Fx%3D1" in ex[1].url, ex[1].url)
ok &= check("id probe: no path escape or query injection",
            "/../" not in path and "def?x=1" not in ex[1].url.split("$")[0]
            and path == "/v1.0/users/mailbox%40contoso.com/messages/abc%2F..%2Fdef%3Fx%3D1",
            ex[1].url)

print("[security — path-ish folder name in list_messages]")
out, ex = run_tool("outlook-mail", p("mail.list_messages", folder="inbox/../drafts?x=1"),
                   [TOKEN_OK, resp(200, body={"value": []})])
ok &= check("folder probe: percent-encoded",
            "inbox%2F..%2Fdrafts%3Fx%3D1" in ex[1].url and "/../" not in
            urllib.parse.urlsplit(ex[1].url).path, ex[1].url)

print("[security — secret never leaks to stdout on error]")
import io, json as _json, contextlib as _ctx
from mockhttp import MockTransport, patched, REPO
src = open(f"{REPO}/skills/outlook-mail/main.py", encoding="utf-8").read()
buf = io.StringIO()
transport = MockTransport([err(401, body={"error": "invalid_client",
                                          "error_description": "bad secret"})])
with patched(transport), _ctx.redirect_stdout(buf):
    exec(compile(src, "outlook-mail/main.py", "exec"), {"params": p("mail.list_messages")})
printed = buf.getvalue()
ok &= check("secret probe: clientSecret absent from stdout",
            CREDS["clientSecret"] not in printed, printed[:300])
ok &= check("secret probe: output still valid error JSON",
            "error" in _json.loads(printed.strip()), printed[:300])

# ---------------------------------------------------------------- 6. SKILL-SPECIFIC
print("[must-verify — $top clamped to 50]")
out, ex = run_tool("outlook-mail", p("mail.list_messages", limit=500),
                   [TOKEN_OK, resp(200, body={"value": []})])
qs = urllib.parse.parse_qs(urllib.parse.urlsplit(ex[1].url).query)
ok &= check("clamp: limit=500 sends $top=50", qs.get("$top") == ["50"], str(qs))

out, ex = run_tool("outlook-mail", p("mail.search_messages", search="x", limit=500),
                   [TOKEN_OK, resp(200, body={"value": []})])
qs = urllib.parse.parse_qs(urllib.parse.urlsplit(ex[1].url).query)
ok &= check("clamp: search limit=500 sends $top=50", qs.get("$top") == ["50"], str(qs))

out, ex = run_tool("outlook-mail", p("mail.list_messages", limit="not-a-number"),
                   [TOKEN_OK, resp(200, body={"value": []})])
qs = urllib.parse.parse_qs(urllib.parse.urlsplit(ex[1].url).query)
ok &= check("clamp: garbage limit falls back to default 25", qs.get("$top") == ["25"], str(qs))

print("[must-verify — missing credentials / unknown tool]")
out, ex = run_tool("outlook-mail", {"tool": "mail.list_messages", "tenantId": "t",
                                    "clientId": "c", "clientSecret": "", "userId": "u"}, [])
ok &= check("missing creds: no HTTP, friendly error",
            len(ex) == 0 and "Missing Microsoft Graph credentials" in out.get("error", ""),
            str(out))
out, ex = run_tool("outlook-mail", p("mail.nope"), [])
ok &= check("unknown tool: error, no HTTP",
            len(ex) == 0 and out.get("error") == "Unknown tool: mail.nope", str(out))

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
