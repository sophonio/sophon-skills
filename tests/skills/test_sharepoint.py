"""Offline mock-HTTP integration tests for the sharepoint skill (Microsoft Graph, app-only)."""
import json
import sys

from mockhttp import run_tool, resp, err, check

CREDS = {"tenantId": "tid-123", "clientId": "cid-456", "clientSecret": "s3cr3t-XYZ"}
TOKEN = resp(200, body={"access_token": "gtok", "token_type": "Bearer", "expires_in": 3599})

ok = True


def p(tool, **kw):
    d = {"tool": tool, **CREDS}
    d.update(kw)
    return d


# ---------------------------------------------------------------- 1. AUTH EXACTNESS
print("[auth exactness — token POST + Bearer on Graph call]")
out, ex = run_tool("sharepoint", p("sp.search_sites", query="marketing"),
                   [TOKEN, resp(200, body={"value": []})])
ok &= check("token: POST method", ex[0].method == "POST", repr(ex[0]))
ok &= check("token: exact URL (tenant in path)",
            ex[0].url == "https://login.microsoftonline.com/tid-123/oauth2/v2.0/token", ex[0].url)
ok &= check("token: form-encoded content-type",
            ex[0].headers.get("content-type") == "application/x-www-form-urlencoded",
            str(ex[0].headers))
ok &= check("token: exact form body (grant/client/secret/scope)",
            ex[0].body == ("grant_type=client_credentials&client_id=cid-456"
                           "&client_secret=s3cr3t-XYZ"
                           "&scope=https%3A%2F%2Fgraph.microsoft.com%2F.default"),
            str(ex[0].body))
ok &= check("graph: Bearer token header",
            ex[1].headers.get("authorization") == "Bearer gtok", str(ex[1].headers))
ok &= check("graph: no auth header on token request",
            "authorization" not in ex[0].headers, str(ex[0].headers))

# ---------------------------------------------------------------- 2. HAPPY PATHS
print("[happy path — sp.search_sites]")
out, ex = run_tool("sharepoint", p("sp.search_sites", query="marketing"),
                   [TOKEN,
                    resp(200, body={"value": [
                        {"id": "contoso.sharepoint.com,g1,g2", "displayName": "Marketing",
                         "name": "marketing", "webUrl": "https://contoso.sharepoint.com/sites/Marketing",
                         "description": "Mkt site", "createdDateTime": "2020-01-01T00:00:00Z",
                         "root": {}, "siteCollection": {"hostname": "contoso.sharepoint.com"}}]})])
ok &= check("search_sites: GET /sites?search=marketing",
            ex[1].method == "GET"
            and ex[1].url == "https://graph.microsoft.com/v1.0/sites?search=marketing", ex[1].url)
ok &= check("search_sites: count == 1", out.get("count") == 1, str(out)[:200])
ok &= check("search_sites: trimmed fields present",
            out["sites"][0]["displayName"] == "Marketing"
            and out["sites"][0]["webUrl"] == "https://contoso.sharepoint.com/sites/Marketing",
            str(out)[:300])
ok &= check("search_sites: raw payload fields absent",
            "siteCollection" not in out["sites"][0] and "root" not in out["sites"][0]
            and "createdDateTime" not in out["sites"][0], str(out["sites"][0]))

print("[happy path — sp.get_site addresses /sites/{hostname}:/{path}]")
out, ex = run_tool("sharepoint",
                   p("sp.get_site", hostname="contoso.sharepoint.com", path="/sites/Team Alpha/"),
                   [TOKEN,
                    resp(200, body={"id": "contoso.sharepoint.com,a,b", "displayName": "Team Alpha",
                                    "name": "TeamAlpha", "webUrl": "https://x", "description": None,
                                    "root": {}})])
ok &= check("get_site: hostname:/path addressing (space quoted, slashes kept)",
            ex[1].url == "https://graph.microsoft.com/v1.0/sites/contoso.sharepoint.com:/sites/Team%20Alpha",
            ex[1].url)
ok &= check("get_site: shaped single-site output",
            out.get("id") == "contoso.sharepoint.com,a,b" and out.get("displayName") == "Team Alpha"
            and "root" not in out, str(out)[:200])

print("[happy path — sp.list_lists]")
out, ex = run_tool("sharepoint", p("sp.list_lists", siteId="contoso.sharepoint.com,a,b"),
                   [TOKEN,
                    resp(200, body={"value": [
                        {"id": "l1", "displayName": "Tasks", "description": "",
                         "webUrl": "https://x/Lists/Tasks", "list": {"template": "genericList"},
                         "createdBy": {"user": {"id": "u"}}, "eTag": "\"1\""}]})])
ok &= check("list_lists: url quotes siteId commas",
            ex[1].url == "https://graph.microsoft.com/v1.0/sites/contoso.sharepoint.com%2Ca%2Cb/lists",
            ex[1].url)
ok &= check("list_lists: count + template flattened",
            out.get("count") == 1 and out["lists"][0]["template"] == "genericList", str(out)[:200])
ok &= check("list_lists: raw fields absent",
            "createdBy" not in out["lists"][0] and "eTag" not in out["lists"][0],
            str(out["lists"][0]))

print("[happy path — sp.query_list_items: expand=fields, 2 pages via @odata.nextLink]")
NEXT = "https://graph.microsoft.com/v1.0/sites/s1/lists/l1/items?%24skiptoken=Paged%3DTRUE"
out, ex = run_tool("sharepoint", p("sp.query_list_items", siteId="s1", listId="l1"),
                   [TOKEN,
                    resp(200, body={"@odata.nextLink": NEXT, "value": [
                        {"id": "1", "webUrl": "https://x/1", "createdDateTime": "2026-01-01T00:00:00Z",
                         "lastModifiedDateTime": "2026-01-02T00:00:00Z", "eTag": "\"1\"",
                         "fields": {"Title": "First", "Status": "Active"}}]}),
                    resp(200, body={"value": [
                        {"id": "2", "webUrl": "https://x/2", "createdDateTime": "2026-02-01T00:00:00Z",
                         "lastModifiedDateTime": "2026-02-02T00:00:00Z", "eTag": "\"2\"",
                         "fields": {"Title": "Second", "Status": "Done"}}]})])
ok &= check("query_list_items: page-1 URL has expand=fields and top",
            ex[1].url == "https://graph.microsoft.com/v1.0/sites/s1/lists/l1/items"
                         "?%24expand=fields&%24top=25", ex[1].url)
ok &= check("query_list_items: page 2 fetched via exact nextLink", ex[2].url == NEXT, ex[2].url)
ok &= check("query_list_items: 3 requests total (token + 2 pages)", len(ex) == 3, repr(ex))
ok &= check("query_list_items: items merged across pages, not truncated",
            out.get("count") == 2 and out.get("truncated") is False
            and out["items"][1]["fields"]["Title"] == "Second", str(out)[:300])
ok &= check("query_list_items: raw eTag absent from items",
            all("eTag" not in i for i in out["items"]), str(out["items"])[:200])

print("[query_list_items: filter forwarded, top clamped to 50]")
out, ex = run_tool("sharepoint",
                   p("sp.query_list_items", siteId="s1", listId="l1",
                     filter="fields/Status eq 'Active'", top=999),
                   [TOKEN, resp(200, body={"value": []})])
ok &= check("query_list_items: $filter encoded + top clamped",
            ex[1].url == "https://graph.microsoft.com/v1.0/sites/s1/lists/l1/items"
                         "?%24expand=fields&%24filter=fields%2FStatus+eq+%27Active%27&%24top=50",
            ex[1].url)

print("[query_list_items: page cap stops at MAX_PAGES and reports truncated]")
page = lambda n: resp(200, body={"@odata.nextLink": f"https://graph.microsoft.com/v1.0/next{n}",
                                 "value": [{"id": str(n), "fields": {"Title": f"t{n}"}}]})
out, ex = run_tool("sharepoint", p("sp.query_list_items", siteId="s1", listId="l1"),
                   [TOKEN, page(1), page(2), page(3), page(4), page(5)])
ok &= check("query_list_items: stops after 5 pages (6 requests incl. token)",
            len(ex) == 6, repr(ex))
ok &= check("query_list_items: truncated=True with 5 items",
            out.get("truncated") is True and out.get("count") == 5, str(out)[:200])

print("[happy path — sp.get_list_item]")
out, ex = run_tool("sharepoint", p("sp.get_list_item", siteId="s1", listId="l1", itemId="7"),
                   [TOKEN,
                    resp(200, body={"id": "7", "webUrl": "https://x/7",
                                    "createdDateTime": "2026-01-01T00:00:00Z",
                                    "lastModifiedDateTime": "2026-01-02T00:00:00Z",
                                    "contentType": {"id": "ct"}, "fields": {"Title": "Seven"}})])
ok &= check("get_list_item: URL + expand=fields",
            ex[1].url == "https://graph.microsoft.com/v1.0/sites/s1/lists/l1/items/7"
                         "?%24expand=fields", ex[1].url)
ok &= check("get_list_item: shaped item (contentType dropped)",
            out.get("id") == "7" and out["fields"]["Title"] == "Seven"
            and "contentType" not in out, str(out)[:200])

print("[sp.search_files: quote escaping ('' doubling) + shaping]")
out, ex = run_tool("sharepoint", p("sp.search_files", siteId="s1", query="O'Brien's plan"),
                   [TOKEN,
                    resp(200, body={"value": [
                        {"id": "f1", "name": "plan.docx", "webUrl": "https://x/plan.docx",
                         "size": 1234, "lastModifiedDateTime": "2026-06-01T00:00:00Z",
                         "file": {"mimeType": "application/msword"},
                         "parentReference": {"driveId": "d"}},
                        {"id": "f2", "name": "Plans", "webUrl": "https://x/Plans", "size": 0,
                         "lastModifiedDateTime": "2026-06-02T00:00:00Z", "folder": {"childCount": 3}}]})])
ok &= check("search_files: single quotes doubled then percent-encoded",
            ex[1].url == "https://graph.microsoft.com/v1.0/sites/s1/drive/root/"
                         "search(q='O%27%27Brien%27%27s%20plan')", ex[1].url)
ok &= check("search_files: count + isFolder flags",
            out.get("count") == 2 and out["files"][0]["isFolder"] is False
            and out["files"][1]["isFolder"] is True, str(out)[:300])
ok &= check("search_files: raw fields absent",
            "parentReference" not in out["files"][0] and "file" not in out["files"][0],
            str(out["files"][0]))

# ---------------------------------------------------------------- 3. WRITE PATHS
print("[write — sp.create_list_item exact POST body]")
out, ex = run_tool("sharepoint",
                   p("sp.create_list_item", siteId="s1", listId="l1",
                     fields={"Title": "New task", "Status": "Active"}),
                   [TOKEN,
                    resp(201, body={"id": "42", "webUrl": "https://x/42",
                                    "fields": {"Title": "New task", "Status": "Active"}})])
ok &= check("create_list_item: POST to /items",
            ex[1].method == "POST"
            and ex[1].url == "https://graph.microsoft.com/v1.0/sites/s1/lists/l1/items", repr(ex[1]))
ok &= check("create_list_item: exact JSON body {'fields': ...}",
            ex[1].json == {"fields": {"Title": "New task", "Status": "Active"}}, str(ex[1].body))
ok &= check("create_list_item: json content-type",
            ex[1].headers.get("content-type") == "application/json", str(ex[1].headers))
ok &= check("create_list_item: shaped output with created flag",
            out == {"id": "42", "webUrl": "https://x/42",
                    "fields": {"Title": "New task", "Status": "Active"}, "created": True},
            str(out)[:200])

print("[write — sp.update_list_item exact PATCH body]")
out, ex = run_tool("sharepoint",
                   p("sp.update_list_item", siteId="s1", listId="l1", itemId="42",
                     fields={"Status": "Done"}),
                   [TOKEN, resp(200, body={"Status": "Done", "Title": "New task"})])
ok &= check("update_list_item: PATCH to /items/42/fields",
            ex[1].method == "PATCH"
            and ex[1].url == "https://graph.microsoft.com/v1.0/sites/s1/lists/l1/items/42/fields",
            repr(ex[1]))
ok &= check("update_list_item: body is the bare fields map",
            ex[1].json == {"Status": "Done"}, str(ex[1].body))
ok &= check("update_list_item: shaped output with updated flag",
            out.get("updated") is True and out.get("id") == "42"
            and out["fields"]["Status"] == "Done", str(out)[:200])

# ---------------------------------------------------------------- 4. ERROR PATHS
print("[error — Graph 401 is a friendly error with status, no traceback]")
out, ex = run_tool("sharepoint", p("sp.list_lists", siteId="s1"),
                   [TOKEN,
                    err(401, body={"error": {"code": "InvalidAuthenticationToken",
                                             "message": "Access token has expired."}})])
ok &= check("401: output is {'error': ...}", set(out.keys()) == {"error"}, str(out)[:200])
ok &= check("401: message includes status and Graph message",
            "401" in out["error"] and "Access token has expired." in out["error"], out.get("error"))
ok &= check("401: no traceback leaked",
            "Traceback" not in out["error"] and "urllib" not in out["error"], out.get("error"))

print("[error — token endpoint 401]")
out, ex = run_tool("sharepoint", p("sp.search_sites", query="x"),
                   [err(401, body={"error": "invalid_client",
                                   "error_description": "AADSTS7000215: Invalid client secret provided."})])
ok &= check("token 401: friendly error with status + AAD description",
            "401" in out.get("error", "") and "AADSTS7000215" in out["error"], str(out)[:300])

print("[error — 429 with Retry-After surfaces the seconds value]")
out, ex = run_tool("sharepoint", p("sp.query_list_items", siteId="s1", listId="l1"),
                   [TOKEN, err(429, body={"error": {"code": "activityLimitReached",
                                                    "message": "throttled"}},
                               headers={"Retry-After": "17"})])
ok &= check("429: error mentions 429 and 'retry after 17s'",
            "429" in out.get("error", "") and "retry after 17s" in out["error"], str(out)[:300])

print("[error — 429 without Retry-After still friendly]")
out, ex = run_tool("sharepoint", p("sp.get_list_item", siteId="s1", listId="l1", itemId="1"),
                   [TOKEN, err(429, body="")])
ok &= check("429 no header: generic retry hint",
            "429" in out.get("error", "") and "retry" in out["error"].lower(), str(out)[:300])

print("[error — missing required param never hits the network]")
out, ex = run_tool("sharepoint", p("sp.get_site", hostname="contoso.sharepoint.com"),
                   [TOKEN])
ok &= check("missing path: 'path required' error after token only",
            out.get("error") == "path required" and len(ex) == 1, f"{out} / {ex!r}")

# ---------------------------------------------------------------- 5. SECURITY PROBES
print("[security — path-ish itemId is percent-encoded, no path escape]")
out, ex = run_tool("sharepoint",
                   p("sp.get_list_item", siteId="s1", listId="l1", itemId="abc/../def?x=1"),
                   [TOKEN, resp(200, body={"id": "abc", "fields": {}})])
ok &= check("itemId fully quoted (safe='')",
            ex[1].url == "https://graph.microsoft.com/v1.0/sites/s1/lists/l1/items/"
                         "abc%2F..%2Fdef%3Fx%3D1?%24expand=fields", ex[1].url)
ok &= check("no raw traversal in URL", "abc/../def" not in ex[1].url and "?x=1" not in ex[1].url,
            ex[1].url)

print("[security — path-ish siteId/listId also quoted]")
out, ex = run_tool("sharepoint",
                   p("sp.list_lists", siteId="s1/../admin"),
                   [TOKEN, resp(200, body={"value": []})])
ok &= check("siteId fully quoted",
            ex[1].url == "https://graph.microsoft.com/v1.0/sites/s1%2F..%2Fadmin/lists", ex[1].url)

print("[security — client secret never appears in printed output]")
out, _ = run_tool("sharepoint", p("sp.search_sites", query="x"),
                  [err(401, body={"error": "invalid_client",
                                  "error_description": "bad secret"})])
ok &= check("secret absent from error output", "s3cr3t-XYZ" not in json.dumps(out),
            json.dumps(out)[:300])
out, _ = run_tool("sharepoint", p("sp.list_lists", siteId="s1"),
                  [TOKEN, resp(200, body={"value": []})])
ok &= check("secret and token absent from happy output",
            "s3cr3t-XYZ" not in json.dumps(out) and "gtok" not in json.dumps(out),
            json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
