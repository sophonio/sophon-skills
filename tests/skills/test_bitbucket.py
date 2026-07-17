"""Offline mock-HTTP integration tests for the Sophon "bitbucket" skill.

Run: python test_bitbucket.py   (exit 1 on any failure)
"""
import json
import sys

from mockhttp import run_tool, resp, err, check

ok = True

BASE = {"email": "dev@acme.io", "apiToken": "tok-123", "workspace": "acme-ws"}
# base64("dev@acme.io:tok-123") — byte-exact expected Basic credential
EXPECT_AUTH = "Basic ZGV2QGFjbWUuaW86dG9rLTEyMw=="
API = "https://api.bitbucket.org/2.0"


def params(tool, **kw):
    p = dict(BASE)
    p["tool"] = tool
    p.update(kw)
    return p


# ---------------------------------------------------------------- 1. AUTH EXACTNESS + list_repos happy path
print("[list_repos: auth + shaping]")
repo_payload = {
    "values": [
        {"slug": "api-server", "name": "API Server", "uuid": "{123}", "full_name": "acme-ws/api-server",
         "links": {"html": {"href": "https://bitbucket.org/acme-ws/api-server"}},
         "mainbranch": {"name": "main", "type": "branch"}, "updated_on": "2026-07-01T00:00:00Z",
         "is_private": True, "scm": "git"},
        {"slug": "api-docs", "name": "API Docs", "uuid": "{456}",
         "mainbranch": None, "updated_on": "2026-06-01T00:00:00Z", "is_private": False},
    ],
}
out, ex = run_tool("bitbucket", params("bitbucket.list_repos", query='name ~ "api"'),
                   [resp(200, body=repo_payload)])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("Authorization: Basic base64(email:apiToken) byte-exact",
            ex[0].headers.get("authorization") == EXPECT_AUTH, str(ex[0].headers))
ok &= check("Accept: application/json for JSON endpoints",
            ex[0].headers.get("accept") == "application/json", str(ex[0].headers))
ok &= check("User-Agent set", ex[0].headers.get("user-agent") == "sophon-bitbucket-skill",
            str(ex[0].headers))
ok &= check("exact URL (workspace + query encoding)",
            ex[0].url == f"{API}/repositories/acme-ws?q=name+~+%22api%22&sort=-updated_on&pagelen=25",
            ex[0].url)
ok &= check("no request body on GET", ex[0].body is None, str(ex[0].body))
ok &= check("count == 2", out.get("count") == 2, str(out)[:300])
r0 = out["repositories"][0]
ok &= check("trimmed fields present",
            r0.get("slug") == "api-server" and r0.get("mainbranch") == "main"
            and r0.get("is_private") is True and r0.get("updated_on") == "2026-07-01T00:00:00Z",
            str(r0))
ok &= check("raw payload fields absent (uuid/links/full_name/scm)",
            all(k not in r0 for k in ("uuid", "links", "full_name", "scm")), str(r0))
ok &= check("None mainbranch handled", out["repositories"][1]["mainbranch"] is None,
            str(out["repositories"][1]))

# ---------------------------------------------------------------- 2. list_pull_requests happy path
print("[list_pull_requests: shaping]")
pr_payload = {
    "values": [
        {"id": 7, "title": "Fix login", "state": "MERGED", "comment_count": 3,
         "author": {"display_name": "Ann Lee", "uuid": "{u1}"},
         "source": {"branch": {"name": "fix/login"}, "commit": {"hash": "abc"}},
         "destination": {"branch": {"name": "main"}},
         "links": {"html": {"href": "x"}}, "summary": {"raw": "big"}},
    ],
}
out, ex = run_tool("bitbucket", params("bitbucket.list_pull_requests", repo="api-server",
                                       state="MERGED", limit=10),
                   [resp(200, body=pr_payload)])
ok &= check("exact URL with repo path + state + pagelen",
            ex[0].url == f"{API}/repositories/acme-ws/api-server/pullrequests"
                         "?state=MERGED&pagelen=10", ex[0].url)
ok &= check("count == 1", out.get("count") == 1, str(out)[:300])
p0 = out["pull_requests"][0]
ok &= check("pr summary shaped (author/branches/state)",
            p0 == {"id": 7, "title": "Fix login", "author": "Ann Lee",
                   "source_branch": "fix/login", "destination_branch": "main",
                   "state": "MERGED"}, str(p0))

# ---------------------------------------------------------------- 3. get_pull_request happy path
print("[get_pull_request: detail shaping]")
pr_detail = {
    "id": 7, "title": "Fix login", "state": "OPEN", "description": "fixes it",
    "created_on": "2026-07-01T00:00:00Z", "updated_on": "2026-07-02T00:00:00Z",
    "comment_count": 2, "task_count": 1, "close_source_branch": True,
    "author": {"display_name": "Ann Lee"},
    "source": {"branch": {"name": "fix/login"}},
    "destination": {"branch": {"name": "main"}},
    "reviewers": [{"display_name": "Bob"}, {"user": {"display_name": "Cara"}}],
    "participants": [
        {"user": {"display_name": "Bob"}, "role": "REVIEWER", "approved": True, "state": "approved"},
        {"user": {"display_name": "Dan"}, "role": "PARTICIPANT", "approved": False, "state": None},
    ],
    "links": {"html": {"href": "https://bitbucket.org/acme-ws/api-server/pull-requests/7"},
              "self": {"href": "https://api.bitbucket.org/..."}},
    "merge_commit": None, "rendered": {"description": {"html": "<p>fixes it</p>"}},
}
out, ex = run_tool("bitbucket", params("bitbucket.get_pull_request", repo="api-server", id=7),
                   [resp(200, body=pr_detail)])
ok &= check("exact URL /pullrequests/7",
            ex[0].url == f"{API}/repositories/acme-ws/api-server/pullrequests/7", ex[0].url)
ok &= check("detail fields present",
            out.get("description") == "fixes it" and out.get("comment_count") == 2
            and out.get("task_count") == 1 and out.get("close_source_branch") is True,
            str(out)[:400])
ok &= check("reviewers flattened to names", out.get("reviewers") == ["Bob", "Cara"],
            str(out.get("reviewers")))
ok &= check("participants shaped", out.get("participants") == [
            {"name": "Bob", "role": "REVIEWER", "approved": True, "state": "approved"},
            {"name": "Dan", "role": "PARTICIPANT", "approved": False, "state": None}],
            str(out.get("participants")))
ok &= check("approval_count == 1", out.get("approval_count") == 1, str(out)[:400])
ok &= check("html url surfaced, raw links absent",
            out.get("url") == "https://bitbucket.org/acme-ws/api-server/pull-requests/7"
            and "links" not in out and "rendered" not in out, str(out)[:400])

# ---------------------------------------------------------------- 4. get_pr_diff raw text handling
print("[get_pr_diff: raw text + truncation]")
diff_text = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n"
out, ex = run_tool("bitbucket", params("bitbucket.get_pr_diff", repo="api-server", id=7),
                   [resp(200, body=diff_text, headers={"Content-Type": "text/plain"})])
ok &= check("diff URL exact",
            ex[0].url == f"{API}/repositories/acme-ws/api-server/pullrequests/7/diff", ex[0].url)
ok &= check("Accept */* for raw endpoint", ex[0].headers.get("accept") == "*/*",
            str(ex[0].headers))
ok &= check("non-JSON body returned verbatim", out.get("diff") == diff_text, str(out)[:200])
ok &= check("truncated False for small diff", out.get("truncated") is False, str(out)[:200])

DIFF_CAP = 100 * 1024
big = "x" * (DIFF_CAP + 5000)
out, ex = run_tool("bitbucket", params("bitbucket.get_pr_diff", repo="api-server", id=7),
                   [resp(200, body=big, headers={"Content-Type": "text/plain"})])
ok &= check("oversized diff truncated flag", out.get("truncated") is True, str(out)[:120])
ok &= check("oversized diff capped at 100 KiB", len(out.get("diff", "")) == DIFF_CAP,
            str(len(out.get("diff", ""))))

# ---------------------------------------------------------------- 5. get_file raw handling
print("[get_file: raw content + truncation]")
content = "import os\nprint('hi')\n"
out, ex = run_tool("bitbucket", params("bitbucket.get_file", repo="api-server", ref="main",
                                       path="src/lib/app.py"),
                   [resp(200, body=content, headers={"Content-Type": "text/plain"})])
ok &= check("src URL keeps path slashes, quotes ref",
            ex[0].url == f"{API}/repositories/acme-ws/api-server/src/main/src/lib/app.py",
            ex[0].url)
ok &= check("file content verbatim", out.get("content") == content, str(out)[:200])
ok &= check("file truncated False", out.get("truncated") is False, str(out)[:120])
ok &= check("path/ref echoed", out.get("path") == "src/lib/app.py" and out.get("ref") == "main",
            str(out)[:200])

FILE_CAP = 256 * 1024
out, ex = run_tool("bitbucket", params("bitbucket.get_file", repo="api-server",
                                       ref="feature/x y", path="a.txt"),
                   [resp(200, body="z" * (FILE_CAP + 1), headers={"Content-Type": "text/plain"})])
ok &= check("ref percent-encoded (slash + space)",
            ex[0].url == f"{API}/repositories/acme-ws/api-server/src/feature%2Fx%20y/a.txt",
            ex[0].url)
ok &= check("oversized file truncated flag + 256 KiB cap",
            out.get("truncated") is True and len(out.get("content", "")) == FILE_CAP,
            str(out)[:120])

# ---------------------------------------------------------------- 6. list_pipeline_runs happy path
print("[list_pipeline_runs: shaping]")
pipe_payload = {
    "values": [
        {"build_number": 42, "uuid": "{p1}", "created_on": "2026-07-10T00:00:00Z",
         "state": {"name": "COMPLETED", "result": {"name": "SUCCESSFUL"}},
         "target": {"ref_name": "main", "commit": {"hash": "deadbeef"}},
         "trigger": {"name": "PUSH"}},
        {"build_number": 41, "state": {"name": "IN_PROGRESS"},
         "target": {"ref_name": "dev"}, "created_on": "2026-07-09T00:00:00Z"},
    ],
}
out, ex = run_tool("bitbucket", params("bitbucket.list_pipeline_runs", repo="api-server"),
                   [resp(200, body=pipe_payload)])
ok &= check("pipelines URL exact",
            ex[0].url == f"{API}/repositories/acme-ws/api-server/pipelines/"
                         "?sort=-created_on&pagelen=25", ex[0].url)
ok &= check("count == 2", out.get("count") == 2, str(out)[:300])
ok &= check("pipeline summary shaped", out["pipelines"][0] == {
            "build_number": 42, "state": "COMPLETED", "result": "SUCCESSFUL",
            "branch": "main", "created_on": "2026-07-10T00:00:00Z"}, str(out["pipelines"][0]))
ok &= check("missing result handled as None", out["pipelines"][1]["result"] is None,
            str(out["pipelines"][1]))

# ---------------------------------------------------------------- 7. Pagination: follow "next" across 2 pages
print("[pagination: next links]")
page2_url = f"{API}/repositories/acme-ws?sort=-updated_on&pagelen=30&page=2"
out, ex = run_tool(
    "bitbucket", params("bitbucket.list_repos", limit=30),
    [resp(200, body={"values": [{"slug": f"r{i}"} for i in range(20)], "next": page2_url}),
     resp(200, body={"values": [{"slug": f"r{20 + i}"} for i in range(5)]})])
ok &= check("two requests for two pages", len(ex) == 2, repr(ex))
ok &= check("second request hits the next URL verbatim (no re-appended query)",
            ex[1].url == page2_url, ex[1].url)
ok &= check("next-page auth header still exact", ex[1].headers.get("authorization") == EXPECT_AUTH,
            str(ex[1].headers))
ok &= check("results merged across pages", out.get("count") == 25
            and out["repositories"][0]["slug"] == "r0"
            and out["repositories"][24]["slug"] == "r24", str(out.get("count")))

# limit cap: stop paging once limit reached even though "next" exists
out, ex = run_tool(
    "bitbucket", params("bitbucket.list_repos", limit=5),
    [resp(200, body={"values": [{"slug": f"r{i}"} for i in range(8)],
                     "next": f"{API}/repositories/acme-ws?page=2"})])
ok &= check("stops at limit, trims values, ignores next",
            len(ex) == 1 and out.get("count") == 5, f"{len(ex)} reqs, count={out.get('count')}")

# PAGE_CAP: at most 5 pages even when every page has a next link
steps = [resp(200, body={"values": [{"slug": f"p{i}"}],
                         "next": f"{API}/repositories/acme-ws?page={i + 2}"}) for i in range(5)]
out, ex = run_tool("bitbucket", params("bitbucket.list_repos", limit=50), steps)
ok &= check("page cap stops after 5 pages", len(ex) == 5 and out.get("count") == 5,
            f"{len(ex)} reqs, count={out.get('count')}")

# ---------------------------------------------------------------- 8. WRITE PATH: add_pr_comment
print("[add_pr_comment: write body]")
out, ex = run_tool(
    "bitbucket", params("bitbucket.add_pr_comment", repo="api-server", id=7,
                        text="Looks good, one nit."),
    [resp(200, body={"id": 900, "created_on": "2026-07-17T10:00:00Z",
                     "content": {"raw": "Looks good, one nit."},
                     "links": {"html": {"href": "https://bitbucket.org/acme-ws/api-server/pull-requests/7#comment-900"}}})])
ok &= check("POST method", ex[0].method == "POST", ex[0].method)
ok &= check("comments URL exact",
            ex[0].url == f"{API}/repositories/acme-ws/api-server/pullrequests/7/comments",
            ex[0].url)
ok &= check("exact JSON body", ex[0].json == {"content": {"raw": "Looks good, one nit."}},
            str(ex[0].body))
ok &= check("Content-Type application/json",
            ex[0].headers.get("content-type") == "application/json", str(ex[0].headers))
ok &= check("write auth header exact", ex[0].headers.get("authorization") == EXPECT_AUTH,
            str(ex[0].headers))
ok &= check("comment result shaped", out == {
            "id": 900, "created_on": "2026-07-17T10:00:00Z",
            "url": "https://bitbucket.org/acme-ws/api-server/pull-requests/7#comment-900"},
            str(out))

# ---------------------------------------------------------------- 9. ERROR PATHS
print("[errors: 401 / 429 / validation]")
out, ex = run_tool("bitbucket", params("bitbucket.list_repos"),
                   [err(401, body={"type": "error", "error": {"message": "Token is invalid or expired"}})])
raw_out = json.dumps(out)
ok &= check("401 -> friendly error object", set(out.keys()) == {"error"}, raw_out[:200])
ok &= check("401 status + API message included",
            "401" in out["error"] and "Token is invalid or expired" in out["error"], raw_out[:300])
ok &= check("no traceback leaked", "Traceback" not in raw_out and "urllib" not in raw_out,
            raw_out[:300])
ok &= check("secret token not leaked in error output",
            "tok-123" not in raw_out and EXPECT_AUTH.split()[1] not in raw_out, raw_out[:300])

out, ex = run_tool("bitbucket", params("bitbucket.get_pull_request", repo="api-server", id=7),
                   [err(429, body="slow down",
                        headers={"Retry-After": "37", "X-RateLimit-Limit": "1000"})])
ok &= check("429 -> error mentions rate limit + status",
            "error" in out and "429" in out["error"] and "Rate limit" in out["error"],
            str(out)[:300])
ok &= check("429 surfaces Retry-After seconds", "Retry after 37 seconds" in out["error"],
            str(out)[:300])

# non-JSON error body must not crash the error handler
out, ex = run_tool("bitbucket", params("bitbucket.list_repos"),
                   [err(503, body="<html>Service Unavailable</html>")])
ok &= check("non-JSON 503 body handled",
            "error" in out and "503" in out["error"], str(out)[:300])

# validation errors (no HTTP call at all)
out, ex = run_tool("bitbucket", params("bitbucket.get_pull_request", repo="api-server"), [])
ok &= check("missing id -> error, no HTTP", "error" in out and len(ex) == 0, str(out)[:200])
out, ex = run_tool("bitbucket", params("bitbucket.list_pull_requests"), [])
ok &= check("missing repo -> error, no HTTP", "error" in out and len(ex) == 0, str(out)[:200])

out, ex = run_tool("bitbucket", {"tool": "bitbucket.list_repos", "email": "dev@acme.io",
                                 "workspace": "acme-ws"}, [])
ok &= check("missing apiToken -> credentials error, no HTTP",
            "error" in out and "credentials" in out["error"].lower() and len(ex) == 0,
            str(out)[:200])
out, ex = run_tool("bitbucket", params("bitbucket.nuke_repo"), [])
ok &= check("unknown tool -> error", out.get("error") == "Unknown tool: bitbucket.nuke_repo",
            str(out)[:200])

# ---------------------------------------------------------------- 10. SECURITY PROBES
print("[security: path traversal encoding]")
out, ex = run_tool("bitbucket", params("bitbucket.get_pull_request", repo="api-server",
                                       id="abc/../def?x=1"),
                   [resp(200, body={"id": 1, "title": "t", "state": "OPEN"})])
ok &= check("path-ish PR id percent-encoded (no path escape)",
            ex[0].url == f"{API}/repositories/acme-ws/api-server/pullrequests/abc%2F..%2Fdef%3Fx%3D1",
            ex[0].url)

out, ex = run_tool("bitbucket", params("bitbucket.list_pull_requests", repo="evil/../other?x=1"),
                   [resp(200, body={"values": []})])
ok &= check("path-ish repo slug percent-encoded",
            ex[0].url.startswith(f"{API}/repositories/acme-ws/evil%2F..%2Fother%3Fx%3D1/pullrequests"),
            ex[0].url)

out, ex = run_tool("bitbucket", params("bitbucket.get_pr_diff", repo="api-server",
                                       id="1/../2"),
                   [resp(200, body="d", headers={"Content-Type": "text/plain"})])
ok &= check("diff id percent-encoded",
            ex[0].url == f"{API}/repositories/acme-ws/api-server/pullrequests/1%2F..%2F2/diff",
            ex[0].url)

out, ex = run_tool("bitbucket", params("bitbucket.get_file", repo="api-server", ref="main",
                                       path="../../pullrequests/1/diff"), [])
ok &= check("get_file '..' path segments rejected, no HTTP",
            "error" in out and ".." in out["error"] and len(ex) == 0, str(out)[:200])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
