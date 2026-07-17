"""Offline mock-HTTP integration tests for the onedrive skill."""
import sys
import urllib.parse

from mockhttp import run_tool, resp, err, check

CREDS = {
    "tenantId": "11111111-2222-3333-4444-555555555555",
    "clientId": "app-client-id",
    "clientSecret": "s3cr3t-value-xyz",
    "userId": "drive.owner@contoso.com",
}
TOKEN_URL = ("https://login.microsoftonline.com/11111111-2222-3333-4444-555555555555"
             "/oauth2/v2.0/token")
DRIVE_BASE = "https://graph.microsoft.com/v1.0/users/drive.owner%40contoso.com/drive"
TOKEN_OK = resp(200, body={"access_token": "graph-tok-123", "token_type": "Bearer"})

ok = True


def p(params):
    d = dict(CREDS)
    d.update(params)
    return d


# ---------------------------------------------------------------- 1. AUTH EXACTNESS
print("[1] auth exactness (token POST + Bearer on Graph call)")
out, ex = run_tool("onedrive", p({"tool": "onedrive.list_folder"}),
                   [TOKEN_OK, resp(200, body={"value": []})])
ok &= check("two requests: token then graph", len(ex) == 2, repr(ex))
ok &= check("token POST url exact", ex[0].method == "POST" and ex[0].url == TOKEN_URL,
            repr(ex[0]))
ok &= check("token content-type form-urlencoded",
            ex[0].headers.get("content-type") == "application/x-www-form-urlencoded",
            str(ex[0].headers))
form = urllib.parse.parse_qs(ex[0].body or "")
ok &= check("token body grant_type=client_credentials",
            form.get("grant_type") == ["client_credentials"], str(form))
ok &= check("token body client_id/client_secret exact",
            form.get("client_id") == ["app-client-id"] and
            form.get("client_secret") == ["s3cr3t-value-xyz"], str(form))
ok &= check("token body scope=.default",
            form.get("scope") == ["https://graph.microsoft.com/.default"], str(form))
ok &= check("token request has no authorization header",
            "authorization" not in ex[0].headers, str(ex[0].headers))
ok &= check("graph GET root children exact url",
            ex[1].method == "GET" and
            ex[1].url == f"{DRIVE_BASE}/root/children?%24top=25", ex[1].url)
ok &= check("graph Bearer header exact",
            ex[1].headers.get("authorization") == "Bearer graph-tok-123",
            str(ex[1].headers))
ok &= check("userId percent-encoded in url (@ -> %40)",
            "drive.owner%40contoso.com" in ex[1].url, ex[1].url)

# ---------------------------------------------------------------- 2. HAPPY PATHS
print("[2] happy paths")
# list_folder with a path + limit
out, ex = run_tool(
    "onedrive",
    p({"tool": "onedrive.list_folder", "path": "/Documents/Reports/", "limit": 5}),
    [TOKEN_OK,
     resp(200, body={"value": [
         {"id": "f1", "name": "q3.docx", "size": 1234,
          "lastModifiedDateTime": "2026-07-01T10:00:00Z",
          "file": {"mimeType": "application/vnd.openxmlformats"},
          "webUrl": "https://contoso-my.sharepoint.com/x", "eTag": "raw-etag",
          "cTag": "raw-ctag"},
         {"id": "d1", "name": "Archive", "size": 0,
          "lastModifiedDateTime": "2026-06-01T10:00:00Z",
          "folder": {"childCount": 7}, "parentReference": {"driveId": "raw"}},
     ]})])
ok &= check("list_folder: path url uses root:/...:/children",
            ex[1].url == f"{DRIVE_BASE}/root:/Documents/Reports:/children?%24top=5",
            ex[1].url)
ok &= check("list_folder: count == 2", out.get("count") == 2, str(out)[:300])
items = out.get("items") or [{}, {}]
ok &= check("list_folder: file item shaped",
            items[0].get("type") == "file" and items[0].get("mimeType") ==
            "application/vnd.openxmlformats" and items[0].get("size") == 1234,
            str(items[0]))
ok &= check("list_folder: folder item shaped with childCount",
            items[1].get("type") == "folder" and items[1].get("childCount") == 7,
            str(items[1]))
ok &= check("list_folder: raw payload fields absent (eTag/cTag/webUrl/parentReference)",
            all(k not in items[0] for k in ("eTag", "cTag", "webUrl")) and
            "parentReference" not in items[1], str(items))

# search_files
out, ex = run_tool(
    "onedrive", p({"tool": "onedrive.search_files", "query": "budget"}),
    [TOKEN_OK,
     resp(200, body={"value": [
         {"id": "s1", "name": "budget.xlsx", "size": 999,
          "lastModifiedDateTime": "2026-05-05T00:00:00Z",
          "file": {"mimeType": "application/vnd.ms-excel"},
          "createdBy": {"user": {"displayName": "raw"}}}]})])
ok &= check("search_files: url is /root/search(q='budget')",
            ex[1].url == f"{DRIVE_BASE}/root/search(q='budget')?%24top=25", ex[1].url)
ok &= check("search_files: shaped output", out.get("count") == 1 and
            out["items"][0].get("name") == "budget.xlsx" and
            "createdBy" not in out["items"][0], str(out)[:300])

# get_item by path
out, ex = run_tool(
    "onedrive", p({"tool": "onedrive.get_item", "path": "Documents/q3.docx"}),
    [TOKEN_OK,
     resp(200, body={"id": "i9", "name": "q3.docx", "size": 42,
                     "lastModifiedDateTime": "2026-07-02T00:00:00Z",
                     "createdDateTime": "2026-01-01T00:00:00Z",
                     "webUrl": "https://contoso-my.sharepoint.com/personal/x/q3.docx",
                     "file": {"mimeType": "application/msword", "hashes": {"sha1": "h"}},
                     "parentReference": {"path": "/drive/root:/Documents", "driveId": "z"},
                     "lastModifiedBy": {"user": {"displayName": "Ann Lee",
                                                 "email": "ann@contoso.com"}}})])
ok &= check("get_item: path url", ex[1].url == f"{DRIVE_BASE}/root:/Documents/q3.docx",
            ex[1].url)
ok &= check("get_item: detail fields present",
            out.get("webUrl", "").endswith("q3.docx") and
            out.get("parentPath") == "/drive/root:/Documents" and
            out.get("lastModifiedBy") == "Ann Lee" and
            out.get("createdDateTime") == "2026-01-01T00:00:00Z", str(out)[:400])
ok &= check("get_item: raw fields absent (file.hashes / parentReference)",
            "file" not in out and "parentReference" not in out, str(out)[:400])

# ---------------------------------------------------------------- 3. WRITE PATHS
print("[3] write paths")
# upload_file: PUT raw content with text/plain
out, ex = run_tool(
    "onedrive",
    p({"tool": "onedrive.upload_file", "path": "Documents/notes.txt",
       "content": "hello\nonedrive"}),
    [TOKEN_OK,
     resp(201, body={"id": "n1", "name": "notes.txt", "size": 14,
                     "webUrl": "https://contoso-my.sharepoint.com/notes.txt"})])
ok &= check("upload: PUT to /root:/Documents/notes.txt:/content",
            ex[1].method == "PUT" and
            ex[1].url == f"{DRIVE_BASE}/root:/Documents/notes.txt:/content", repr(ex[1]))
ok &= check("upload: raw body byte-exact", ex[1].body == "hello\nonedrive",
            repr(ex[1].body))
ok &= check("upload: content-type text/plain",
            ex[1].headers.get("content-type") == "text/plain", str(ex[1].headers))
ok &= check("upload: shaped output", out.get("id") == "n1" and out.get("size") == 14,
            str(out))

# upload cap: > 1 MB refused before any Graph call (token already fetched)
out, ex = run_tool(
    "onedrive",
    p({"tool": "onedrive.upload_file", "path": "big.txt",
       "content": "x" * (1024 * 1024 + 1)}),
    [TOKEN_OK])
ok &= check("upload cap: only token request made", len(ex) == 1, repr(ex))
ok &= check("upload cap: friendly error mentions 1 MB",
            "error" in out and "1 MB" in out["error"], str(out)[:200])

# create_folder: POST JSON body with conflictBehavior fail
out, ex = run_tool(
    "onedrive", p({"tool": "onedrive.create_folder", "name": "New Reports",
                   "parentPath": "Documents"}),
    [TOKEN_OK, resp(201, body={"id": "nf1", "name": "New Reports",
                               "webUrl": "https://contoso-my.sharepoint.com/nr"})])
ok &= check("create_folder: POST to parent children",
            ex[1].method == "POST" and
            ex[1].url == f"{DRIVE_BASE}/root:/Documents:/children", repr(ex[1]))
ok &= check("create_folder: exact JSON body",
            ex[1].json == {"name": "New Reports", "folder": {},
                           "@microsoft.graph.conflictBehavior": "fail"}, ex[1].body)
ok &= check("create_folder: content-type json",
            ex[1].headers.get("content-type") == "application/json", str(ex[1].headers))
ok &= check("create_folder: shaped output", out.get("created") is True and
            out.get("id") == "nf1", str(out))

# create_share_link: POST body {view, organization}
out, ex = run_tool(
    "onedrive", p({"tool": "onedrive.create_share_link", "itemId": "i9"}),
    [TOKEN_OK,
     resp(201, body={"id": "perm1", "roles": ["read"],
                     "link": {"type": "view", "scope": "organization",
                              "webUrl": "https://contoso-my.sharepoint.com/:x:/g/link"}})])
ok &= check("share_link: POST to /items/i9/createLink",
            ex[1].method == "POST" and ex[1].url == f"{DRIVE_BASE}/items/i9/createLink",
            repr(ex[1]))
ok &= check("share_link: exact JSON body",
            ex[1].json == {"type": "view", "scope": "organization"}, ex[1].body)
ok &= check("share_link: shaped output (no raw roles/id)",
            out.get("url", "").endswith("/link") and out.get("scope") == "organization"
            and "roles" not in out, str(out))

# ---------------------------------------------------------------- 4. ERROR PATHS
print("[4] error paths")
out, ex = run_tool(
    "onedrive", p({"tool": "onedrive.get_item", "itemId": "i9"}),
    [TOKEN_OK,
     err(401, body={"error": {"code": "InvalidAuthenticationToken",
                              "message": "Access token has expired."}})])
ok &= check("401: error key present", "error" in out and len(out) == 1, str(out)[:300])
ok &= check("401: includes status and Graph message",
            "401" in out["error"] and "Access token has expired." in out["error"],
            str(out)[:300])
ok &= check("401: no traceback leaked",
            "Traceback" not in str(out) and "urllib" not in str(out), str(out)[:300])

# token endpoint failure surfaces friendly error
out, ex = run_tool(
    "onedrive", p({"tool": "onedrive.list_folder"}),
    [err(401, body={"error": "invalid_client",
                    "error_description": "AADSTS7000215: Invalid client secret provided."})])
ok &= check("token 401: friendly error with status",
            "error" in out and "401" in out["error"] and "AADSTS7000215" in out["error"],
            str(out)[:300])

# 429 with Retry-After
out, ex = run_tool(
    "onedrive", p({"tool": "onedrive.search_files", "query": "x"}),
    [TOKEN_OK,
     err(429, body={"error": {"code": "activityLimitReached",
                              "message": "Throttled."}},
         headers={"Retry-After": "17"})])
ok &= check("429: rate-limit message with Retry-After seconds",
            "error" in out and "429" in out["error"] and
            "retry after 17 seconds" in out["error"], str(out)[:300])

# missing credentials -> friendly error, zero requests
out, ex = run_tool("onedrive", {"tool": "onedrive.list_folder", "tenantId": "t",
                                "clientId": "c", "clientSecret": "", "userId": "u"}, [])
ok &= check("missing creds: no HTTP and friendly error",
            len(ex) == 0 and "error" in out and "connect the OneDrive integration"
            in out["error"], str(out)[:300])

# unknown tool
out, ex = run_tool("onedrive", p({"tool": "onedrive.nope"}), [])
ok &= check("unknown tool: error, no HTTP",
            len(ex) == 0 and out.get("error") == "Unknown tool: onedrive.nope", str(out))

# ---------------------------------------------------------------- 5. SECURITY PROBES
print("[5] security probes")
# (a) path-ish itemId must be percent-encoded — no path escape
evil = "abc/../def?x=1"
out, ex = run_tool(
    "onedrive", p({"tool": "onedrive.get_item", "itemId": evil}),
    [TOKEN_OK,
     resp(200, body={"id": "x", "name": "n", "size": 1,
                     "lastModifiedDateTime": "2026-01-01T00:00:00Z", "file": {}})])
quoted = urllib.parse.quote(evil, safe="")
ok &= check("get_item: itemId fully percent-encoded in url",
            ex[1].url == f"{DRIVE_BASE}/items/{quoted}", ex[1].url)
ok &= check("get_item: no raw '../' or '?' from id in url",
            "/../" not in ex[1].url and "?" not in ex[1].url, ex[1].url)

# read_file itemId also encoded
out, ex = run_tool(
    "onedrive", p({"tool": "onedrive.read_file", "itemId": evil}),
    [TOKEN_OK,
     err(302, headers={"Location": "https://contoso-my.sharepoint.com/dl/abc"}),
     resp(200, body=b"text")])
ok &= check("read_file: itemId percent-encoded in /content url",
            ex[1].url == f"{DRIVE_BASE}/items/{quoted}/content", ex[1].url)

# (b) secret never appears in printed output on an error path
out, ex = run_tool(
    "onedrive", p({"tool": "onedrive.list_folder"}),
    [err(500, body="internal error")])
ok &= check("secret absent from error output", "s3cr3t-value-xyz" not in str(out),
            str(out)[:300])
ok &= check("500: status surfaced", "500" in out.get("error", ""), str(out)[:300])

# ---------------------------------------------------------------- 6. MUST-VERIFY: read_file
print("[6] read_file redirect / binary / search escaping / upload cap")
file_text = "line one\nline two é\n"
out, ex = run_tool(
    "onedrive", p({"tool": "onedrive.read_file", "itemId": "f42"}),
    [TOKEN_OK,
     err(302, headers={"Location":
                       "https://contoso-my.sharepoint.com/personal/_layouts/download?g=1"}),
     resp(200, body=file_text.encode("utf-8"))])
ok &= check("read_file: three requests (token, graph, download)", len(ex) == 3, repr(ex))
ok &= check("read_file: graph /content call has Bearer",
            ex[1].headers.get("authorization") == "Bearer graph-tok-123" and
            ex[1].url == f"{DRIVE_BASE}/items/f42/content", repr(ex[1]))
ok &= check("read_file: download follows Location exactly",
            ex[2].url ==
            "https://contoso-my.sharepoint.com/personal/_layouts/download?g=1", ex[2].url)
ok &= check("CRITICAL read_file: NO authorization header on sharepoint request",
            "authorization" not in ex[2].headers, str(ex[2].headers))
ok &= check("read_file: content decoded and returned",
            out.get("content") == file_text and out.get("truncated") is False, str(out)[:200])

# binary content refused with helpful error
png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 32
out, ex = run_tool(
    "onedrive", p({"tool": "onedrive.read_file", "itemId": "img1"}),
    [TOKEN_OK,
     err(302, headers={"Location": "https://contoso-my.sharepoint.com/dl/img1"}),
     resp(200, body=png)])
ok &= check("read_file: binary refused with helpful error",
            "error" in out and "binary" in out["error"] and "webUrl" in out["error"],
            str(out)[:300])
ok &= check("read_file: binary error is not a traceback",
            "Traceback" not in str(out), str(out)[:200])

# direct 200 (no redirect) tolerated
out, ex = run_tool(
    "onedrive", p({"tool": "onedrive.read_file", "itemId": "f43"}),
    [TOKEN_OK, resp(200, body=b"direct body")])
ok &= check("read_file: direct 200 body tolerated",
            out.get("content") == "direct body" and len(ex) == 2, str(out)[:200])

# redirect with no Location -> friendly error
out, ex = run_tool(
    "onedrive", p({"tool": "onedrive.read_file", "itemId": "f44"}),
    [TOKEN_OK, err(302)])
ok &= check("read_file: 302 without Location is a friendly error",
            "error" in out and "no Location header" in out["error"], str(out)[:200])

# truncation over the 512 KB cap
big = b"a" * (512 * 1024 + 100)
out, ex = run_tool(
    "onedrive", p({"tool": "onedrive.read_file", "itemId": "f45"}),
    [TOKEN_OK,
     err(302, headers={"Location": "https://contoso-my.sharepoint.com/dl/f45"}),
     resp(200, body=big)])
ok &= check("read_file: truncated at 512 KB cap",
            out.get("truncated") is True and len(out.get("content", "")) == 512 * 1024,
            f"truncated={out.get('truncated')} len={len(out.get('content', ''))}")

# search escapes single quotes (Graph OData: ' -> '' then percent-encoded)
out, ex = run_tool(
    "onedrive", p({"tool": "onedrive.search_files", "query": "ann's plan"}),
    [TOKEN_OK, resp(200, body={"value": []})])
ok &= check("search: single quote doubled and percent-encoded",
            ex[1].url ==
            f"{DRIVE_BASE}/root/search(q='ann%27%27s%20plan')?%24top=25", ex[1].url)
ok &= check("search: no raw single quote from query in url",
            "ann'" not in ex[1].url, ex[1].url)

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
