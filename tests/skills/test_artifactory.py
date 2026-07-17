"""Offline mock-HTTP integration tests for the artifactory skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "https://mycompany.jfrog.io"
API = f"{BASE}/artifactory/api"
TOK = "artifTOK-SECRET-VALUE"


def creds(**extra):
    p = {"baseUrl": BASE, "accessToken": TOK}
    p.update(extra)
    return p


ok = True

# ---------------------------------------------------------------------------
# 1. artifactory.list_repositories — happy path + auth exactness
# ---------------------------------------------------------------------------
print("scenario: list_repositories happy path / auth exactness")
out, ex = run_tool("artifactory", creds(tool="artifactory.list_repositories"), [
    resp(200, body=[
        {"key": "libs-release", "type": "LOCAL", "description": "internal releases",
         "url": f"{BASE}/artifactory/libs-release", "packageType": "Maven"},
        {"key": "npm-remote", "type": "REMOTE", "url": f"{BASE}/artifactory/npm-remote",
         "packageType": "Npm"},
    ]),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact (base + /artifactory/api appended)",
            ex[0].url == f"{API}/repositories", ex[0].url)
ok &= check("Authorization is exactly 'Bearer <token>'",
            ex[0].headers.get("authorization") == f"Bearer {TOK}", str(ex[0].headers))
ok &= check("Accept header", ex[0].headers.get("accept") == "application/json",
            str(ex[0].headers))
ok &= check("User-Agent", ex[0].headers.get("user-agent") == "sophon-artifactory-skill",
            str(ex[0].headers))
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("repo shaped to key/type/packageType/url",
            out["repositories"][0] == {"key": "libs-release", "type": "LOCAL",
                                       "packageType": "Maven",
                                       "url": f"{BASE}/artifactory/libs-release"},
            str(out["repositories"][0]))
ok &= check("raw description absent", "description" not in out["repositories"][0],
            str(out["repositories"][0]))
ok &= check("token not echoed in output", TOK not in json.dumps(out))

print("scenario: list_repositories type filter")
out, ex = run_tool("artifactory", creds(tool="artifactory.list_repositories", type="local"), [
    resp(200, body=[]),
])
ok &= check("type filter in URL", ex[0].url == f"{API}/repositories?type=local", ex[0].url)
ok &= check("empty result count 0", out.get("count") == 0, str(out))

print("scenario: list_repositories invalid type rejected without HTTP")
out, ex = run_tool("artifactory", creds(tool="artifactory.list_repositories", type="LOCAL"), [])
ok &= check("invalid type -> friendly error",
            out.get("error") == "type must be one of: local, remote, virtual, federated",
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 2. artifactory.search_artifacts — quick mode
# ---------------------------------------------------------------------------
print("scenario: search_artifacts quick mode")
out, ex = run_tool("artifactory", creds(tool="artifactory.search_artifacts",
                                        name="guava", repos="libs-release"), [
    resp(200, body={"results": [
        {"uri": f"{API}/storage/libs-release/org/guava/guava-1.0.jar"},
    ]}),
])
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact",
            ex[0].url == f"{API}/search/artifact?name=guava&repos=libs-release", ex[0].url)
ok &= check("no body on quick search", ex[0].body is None, str(ex[0].body))
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])
ok &= check("repo/path/name derived from storage uri",
            out["results"][0] == {"uri": f"{API}/storage/libs-release/org/guava/guava-1.0.jar",
                                  "repo": "libs-release", "path": "org/guava/guava-1.0.jar",
                                  "name": "guava-1.0.jar"},
            str(out["results"][0]))

print("scenario: search_artifacts quick mode omits empty repos param")
out, ex = run_tool("artifactory", creds(tool="artifactory.search_artifacts", name="x"), [
    resp(200, body={"results": []}),
])
ok &= check("repos dropped when empty", ex[0].url == f"{API}/search/artifact?name=x", ex[0].url)

print("scenario: search_artifacts quick mode falls back to repo when repos absent")
out, ex = run_tool("artifactory", creds(tool="artifactory.search_artifacts",
                                        name="x", repo="libs-release"), [
    resp(200, body={"results": []}),
])
ok &= check("repo used as repos fallback",
            ex[0].url == f"{API}/search/artifact?name=x&repos=libs-release", ex[0].url)

# ---------------------------------------------------------------------------
# 3. artifactory.search_artifacts — AQL mode (safe construction, text/plain, cap)
# ---------------------------------------------------------------------------
print("scenario: search_artifacts AQL mode body byte-exact")
out, ex = run_tool("artifactory", creds(tool="artifactory.search_artifacts",
                                        repo="libs-release", namePattern="*.jar"), [
    resp(200, body={"results": [
        {"repo": "libs-release", "path": "org/acme", "name": "app-1.0.jar",
         "size": 1024, "created": "2026-05-01T00:00:00.000Z", "type": "file",
         "modified_by": "raw-should-not-leak"},
    ], "range": {"start_pos": 0, "end_pos": 1, "total": 1}}),
])
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{API}/search/aql", ex[0].url)
ok &= check("Content-Type is text/plain",
            ex[0].headers.get("content-type") == "text/plain", str(ex[0].headers))
ok &= check("AQL body byte-exact (includes repo/path/name for non-admin filtering)",
            ex[0].body == 'items.find({"repo":"libs-release","name":{"$match":"*.jar"}})'
                          '.include("repo","path","name","size","created").limit(50)',
            str(ex[0].body))
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])
ok &= check("AQL result shaped",
            out["results"][0] == {"repo": "libs-release", "path": "org/acme",
                                  "name": "app-1.0.jar", "size": 1024,
                                  "created": "2026-05-01T00:00:00.000Z"},
            str(out["results"][0]))
ok &= check("raw type/modified_by absent",
            "type" not in out["results"][0] and "modified_by" not in out["results"][0],
            str(out["results"][0]))

print("scenario: search_artifacts AQL limit capped at 100")
out, ex = run_tool("artifactory", creds(tool="artifactory.search_artifacts",
                                        repo="r1", pathPattern="org/*",
                                        createdAfter="2026-01-01", limit=500), [
    resp(200, body={"results": []}),
])
ok &= check("AQL body with path/created and .limit(100) cap",
            ex[0].body == 'items.find({"repo":"r1","path":{"$match":"org/*"},'
                          '"created":{"$gt":"2026-01-01"}})'
                          '.include("repo","path","name","size","created").limit(100)',
            str(ex[0].body))

print("scenario: search_artifacts AQL injection attempt stays JSON-escaped")
out, ex = run_tool("artifactory", creds(tool="artifactory.search_artifacts",
                                        repo='r"1',
                                        namePattern='*"}).limit(10000)//'), [
    resp(200, body={"results": []}),
])
ok &= check("hostile params cannot terminate the criteria object (byte-exact)",
            ex[0].body == 'items.find({"repo":"r\\"1","name":'
                          '{"$match":"*\\"}).limit(10000)//"}})'
                          '.include("repo","path","name","size","created").limit(50)',
            str(ex[0].body))
ok &= check("body still ends with the skill-appended .limit(50)",
            ex[0].body.endswith(").limit(50)"), str(ex[0].body))

print("scenario: search_artifacts with no criteria rejected without HTTP")
out, ex = run_tool("artifactory", creds(tool="artifactory.search_artifacts"), [])
ok &= check("no-criteria friendly error",
            "error" in out and "quick search" in out["error"] and "AQL" in out["error"],
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 4. artifactory.get_artifact_info — happy path (+stats second request)
# ---------------------------------------------------------------------------
print("scenario: get_artifact_info happy path")
FILE_INFO = {"repo": "libs-release", "path": "/org/acme/app-1.0.jar",
             "created": "2026-05-01T00:00:00.000Z", "createdBy": "ci",
             "lastModified": "2026-05-02T00:00:00.000Z", "modifiedBy": "ci",
             "lastUpdated": "2026-05-02T00:00:00.000Z",
             "downloadUri": f"{BASE}/artifactory/libs-release/org/acme/app-1.0.jar",
             "mimeType": "application/java-archive", "size": "1024",
             "checksums": {"sha1": "sha1val", "md5": "md5val", "sha256": "sha256val"},
             "originalChecksums": {"sha256": "sha256val"},
             "uri": f"{API}/storage/libs-release/org/acme/app-1.0.jar"}
out, ex = run_tool("artifactory", creds(tool="artifactory.get_artifact_info",
                                        repo="libs-release", path="org/acme/app-1.0.jar"), [
    resp(200, body=FILE_INFO),
])
ok &= check("one request (no stats)", len(ex) == 1, repr(ex))
ok &= check("URL byte-exact",
            ex[0].url == f"{API}/storage/libs-release/org/acme/app-1.0.jar", ex[0].url)
ok &= check("size coerced to int", out.get("size") == 1024, str(out)[:200])
ok &= check("sha256 surfaced", out.get("checksums", {}).get("sha256") == "sha256val",
            str(out)[:300])
ok &= check("created/lastModified present",
            out.get("created") == "2026-05-01T00:00:00.000Z"
            and out.get("lastModified") == "2026-05-02T00:00:00.000Z", str(out)[:300])
ok &= check("raw originalChecksums/createdBy/uri absent",
            "originalChecksums" not in out and "createdBy" not in out and "uri" not in out,
            str(out)[:300])
ok &= check("no downloadCount without stats", "downloadCount" not in out, str(out)[:300])

print("scenario: get_artifact_info stats=true makes second ?stats request")
out, ex = run_tool("artifactory", creds(tool="artifactory.get_artifact_info",
                                        repo="libs-release", path="org/acme/app-1.0.jar",
                                        stats=True), [
    resp(200, body=FILE_INFO),
    resp(200, body={"uri": "x", "downloadCount": 7, "lastDownloaded": 1789000000000,
                    "lastDownloadedBy": "raw"}),
])
ok &= check("two requests made", len(ex) == 2, repr(ex))
ok &= check("second URL is ?stats byte-exact",
            ex[1].url == f"{API}/storage/libs-release/org/acme/app-1.0.jar?stats", ex[1].url)
ok &= check("both requests authed",
            all(e.headers.get("authorization") == f"Bearer {TOK}" for e in ex))
ok &= check("downloadCount merged", out.get("downloadCount") == 7, str(out)[:300])
ok &= check("lastDownloaded merged", out.get("lastDownloaded") == 1789000000000,
            str(out)[:300])

print("scenario: get_artifact_info missing path -> friendly error, no HTTP")
out, ex = run_tool("artifactory", creds(tool="artifactory.get_artifact_info",
                                        repo="libs-release"), [])
ok &= check("repo and path required", out.get("error") == "repo and path required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 5. artifactory.get_item_properties — happy path + 404 friendly
# ---------------------------------------------------------------------------
print("scenario: get_item_properties happy path")
out, ex = run_tool("artifactory", creds(tool="artifactory.get_item_properties",
                                        repo="libs-release", path="org/app.jar"), [
    resp(200, body={"properties": {"env": ["prod"], "team": ["core"]},
                    "uri": f"{API}/storage/libs-release/org/app.jar"}),
])
ok &= check("URL byte-exact (?properties)",
            ex[0].url == f"{API}/storage/libs-release/org/app.jar?properties", ex[0].url)
ok &= check("properties map returned",
            out == {"repo": "libs-release", "path": "org/app.jar",
                    "properties": {"env": ["prod"], "team": ["core"]}}, str(out))

print("scenario: get_item_properties 404 -> friendly 'no properties set'")
out, ex = run_tool("artifactory", creds(tool="artifactory.get_item_properties",
                                        repo="libs-release", path="org/app.jar"), [
    err(404, body={"errors": [{"status": 404, "message": "No properties could be found."}]}),
])
ok &= check("friendly empty-properties result",
            out == {"repo": "libs-release", "path": "org/app.jar", "properties": {},
                    "note": "no properties set"}, str(out))
ok &= check("no error key / no traceback",
            "error" not in out and "Traceback" not in json.dumps(out), str(out))

print("scenario: get_item_properties 404 for a missing item stays an error")
out, ex = run_tool("artifactory", creds(tool="artifactory.get_item_properties",
                                        repo="libs-release", path="org/nope.jar"), [
    err(404, body={"errors": [{"status": 404,
                               "message": "Unable to find item"}]}),
])
ok &= check("missing item surfaced as 404 error, not empty properties",
            out.get("error") == "Artifactory API error 404: Unable to find item", str(out))

# ---------------------------------------------------------------------------
# 6. artifactory.list_builds — all builds + per-build numbers + 404 empty
# ---------------------------------------------------------------------------
print("scenario: list_builds all builds")
out, ex = run_tool("artifactory", creds(tool="artifactory.list_builds"), [
    resp(200, body={"builds": [
        {"uri": "/my-app", "lastBuildTime": "2026-07-01T10:00:00.000+0000"},
        {"uri": "/other%20app", "lastBuildTime": "2026-06-01T10:00:00.000+0000"},
    ], "uri": f"{API}/build"}),
])
ok &= check("URL byte-exact", ex[0].url == f"{API}/build", ex[0].url)
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("build name stripped/decoded",
            out["builds"][0] == {"name": "my-app",
                                 "lastBuildTime": "2026-07-01T10:00:00.000+0000"}
            and out["builds"][1]["name"] == "other app", str(out)[:300])

print("scenario: list_builds with buildName lists numbers")
out, ex = run_tool("artifactory", creds(tool="artifactory.list_builds", buildName="my-app"), [
    resp(200, body={"buildsNumbers": [
        {"uri": "/42", "started": "2026-07-01T10:00:00.000+0000"},
        {"uri": "/41", "started": "2026-06-30T10:00:00.000+0000"},
    ], "uri": f"{API}/build/my-app"}),
])
ok &= check("URL byte-exact", ex[0].url == f"{API}/build/my-app", ex[0].url)
ok &= check("numbers shaped",
            out == {"buildName": "my-app", "count": 2, "builds": [
                {"number": "42", "started": "2026-07-01T10:00:00.000+0000"},
                {"number": "41", "started": "2026-06-30T10:00:00.000+0000"}]}, str(out))

print("scenario: list_builds 404 (no builds) -> empty result, not an error")
out, ex = run_tool("artifactory", creds(tool="artifactory.list_builds"), [
    err(404, body={"errors": [{"status": 404, "message": "No builds were found"}]}),
])
ok &= check("empty builds result", out == {"count": 0, "builds": []}, str(out))

# ---------------------------------------------------------------------------
# 7. artifactory.get_storage_summary — happy path + 403 scoped-token message
# ---------------------------------------------------------------------------
print("scenario: get_storage_summary happy path")
out, ex = run_tool("artifactory", creds(tool="artifactory.get_storage_summary"), [
    resp(200, body={
        "binariesSummary": {"binariesCount": "1,000"},
        "fileStoreSummary": {"storageType": "s3"},
        "repositoriesSummaryList": [
            {"repoKey": "libs-release", "repoType": "LOCAL", "foldersCount": 10,
             "filesCount": 100, "usedSpace": "1.50 GB", "itemsCount": 110,
             "packageType": "Maven", "percentage": "10%"},
            {"repoKey": "TOTAL", "repoType": "NA", "foldersCount": 99, "filesCount": 999,
             "usedSpace": "15.0 GB", "itemsCount": 1098, "packageType": "NA",
             "percentage": "100%"},
        ]}),
])
ok &= check("URL byte-exact", ex[0].url == f"{API}/storageinfo", ex[0].url)
ok &= check("repositories trimmed to repoKey/usedSpace/itemsCount/packageType",
            out["repositories"][0] == {"repoKey": "libs-release", "usedSpace": "1.50 GB",
                                       "itemsCount": 110, "packageType": "Maven"},
            str(out["repositories"][0]))
ok &= check("raw foldersCount/percentage absent",
            "foldersCount" not in out["repositories"][0]
            and "percentage" not in out["repositories"][0], str(out["repositories"][0]))
ok &= check("raw binariesSummary absent from output", "binariesSummary" not in out,
            str(out)[:300])

print("scenario: get_storage_summary 403 -> scoped-token guidance")
out, ex = run_tool("artifactory", creds(tool="artifactory.get_storage_summary"), [
    err(403, body={"errors": [{"status": 403, "message": "Forbidden"}]}),
])
ok &= check("exact scoped-token message",
            out.get("error") == "storage summary requires an admin or system:info-scoped token",
            str(out))
ok &= check("token not leaked", TOK not in json.dumps(out))

# ---------------------------------------------------------------------------
# 8. artifactory.set_item_properties — write path + encoding
# ---------------------------------------------------------------------------
print("scenario: set_item_properties write path")
out, ex = run_tool("artifactory", creds(tool="artifactory.set_item_properties",
                                        repo="libs-release", path="org/app.jar",
                                        properties={"env": "prod", "team": "core devs"}), [
    resp(204),
])
ok &= check("method PUT", ex[0].method == "PUT", ex[0].method)
ok &= check("URL byte-exact with k=v;k2=v2 query, encoded space, non-recursive default",
            ex[0].url == f"{API}/storage/libs-release/org/app.jar"
                         "?properties=env=prod;team=core%20devs&recursive=0", ex[0].url)
ok &= check("no body on properties PUT", ex[0].body is None, str(ex[0].body))
ok &= check("Bearer auth on write", ex[0].headers.get("authorization") == f"Bearer {TOK}")
ok &= check("success output",
            out == {"set": True, "repo": "libs-release", "path": "org/app.jar",
                    "properties": {"env": "prod", "team": "core devs"}}, str(out))

print("scenario: set_item_properties backslash-escapes '=' and encodes ';' inside values")
out, ex = run_tool("artifactory", creds(tool="artifactory.set_item_properties",
                                        repo="libs-release", path="org/app.jar",
                                        properties={"qa": "a=b;c"}), [
    resp(204),
])
# JFrog requires an encoded backslash (%5C) before special chars , \ | = in keys/values.
ok &= check("'=' gets %5C escape, ';' percent-encoded",
            ex[0].url == f"{API}/storage/libs-release/org/app.jar"
                         "?properties=qa=a%5C%3Db%3Bc&recursive=0",
            ex[0].url)

print("scenario: set_item_properties backslash-escapes ',', '|', and '\\' too")
out, ex = run_tool("artifactory", creds(tool="artifactory.set_item_properties",
                                        repo="libs-release", path="org/app.jar",
                                        properties={"k=1": "a,b|c\\d"}), [
    resp(204),
])
ok &= check("comma/pipe/backslash escaped in value, '=' escaped in key",
            ex[0].url == f"{API}/storage/libs-release/org/app.jar"
                         "?properties=k%5C%3D1=a%5C%2Cb%5C%7Cc%5C%5Cd&recursive=0",
            ex[0].url)

print("scenario: set_item_properties recursive=true opts into recursive stamping")
out, ex = run_tool("artifactory", creds(tool="artifactory.set_item_properties",
                                        repo="libs-release", path="org/folder",
                                        properties={"env": "prod"}, recursive=True), [
    resp(204),
])
ok &= check("recursive=1 when requested",
            ex[0].url == f"{API}/storage/libs-release/org/folder"
                         "?properties=env=prod&recursive=1", ex[0].url)

print("scenario: set_item_properties missing properties -> friendly error, no HTTP")
out, ex = run_tool("artifactory", creds(tool="artifactory.set_item_properties",
                                        repo="libs-release", path="org/app.jar"), [])
ok &= check("properties required error",
            out.get("error") == "properties required (object of key/value pairs)", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 9. ERROR PATHS — 401 friendly, 429 Retry-After, non-JSON body
# ---------------------------------------------------------------------------
print("scenario: 401 surfaces friendly error from Artifactory errors[] body")
out, ex = run_tool("artifactory", creds(tool="artifactory.list_repositories"), [
    err(401, body={"errors": [{"status": 401, "message": "Bad credentials"}]}),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("includes API message", "Bad credentials" in out["error"], out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw,
            raw[:300])
ok &= check("token not leaked in error output", TOK not in raw, raw[:300])

print("scenario: 429 includes Retry-After when present")
out, ex = run_tool("artifactory", creds(tool="artifactory.list_repositories"), [
    err(429, body={"errors": [{"status": 429, "message": "Too many requests"}]},
        headers={"Retry-After": "30"}),
])
ok &= check("429 error surfaced", "error" in out and "429" in out["error"], str(out)[:300])
ok &= check("Retry-After included", "retry after 30s" in out["error"], out.get("error", ""))
ok &= check("message included", "Too many requests" in out["error"], out.get("error", ""))

print("scenario: 429 HTTP-date Retry-After gets no 's' unit")
out, ex = run_tool("artifactory", creds(tool="artifactory.list_repositories"), [
    err(429, body={"errors": [{"status": 429, "message": "Too many requests"}]},
        headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}),
])
ok &= check("HTTP-date surfaced verbatim without trailing 's'",
            "retry after Wed, 21 Oct 2026 07:28:00 GMT)" in out.get("error", ""),
            out.get("error", ""))

print("scenario: non-JSON error body tolerated")
out, ex = run_tool("artifactory", creds(tool="artifactory.list_repositories"), [
    err(502, body="<html>bad gateway</html>"),
])
ok &= check("502 non-JSON body still friendly",
            "error" in out and "502" in out["error"]
            and "Traceback" not in json.dumps(out), str(out)[:300])

print("scenario: missing credentials -> friendly error, no HTTP call")
out, ex = run_tool("artifactory", {"tool": "artifactory.list_repositories",
                                   "baseUrl": "", "accessToken": ""}, [])
ok &= check("missing-credentials message names fields",
            "error" in out and "connect the Artifactory integration" in out["error"]
            and "baseUrl" in out["error"] and "accessToken" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("artifactory", creds(tool="artifactory.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: artifactory.nope",
            str(out))

# ---------------------------------------------------------------------------
# 10. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-traversal repo/path rejected, no HTTP")
out, ex = run_tool("artifactory", creds(tool="artifactory.get_artifact_info",
                                        repo="abc/../def?x=1", path="a.jar"), [])
ok &= check("traversal repo rejected",
            out.get("error") == "repo must not contain '.' or '..' path segments", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))
out, ex = run_tool("artifactory", creds(tool="artifactory.get_artifact_info",
                                        repo="libs-release", path="abc/../def?x=1"), [])
ok &= check("traversal path rejected",
            out.get("error") == "path must not contain '.' or '..' path segments", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))
out, ex = run_tool("artifactory", creds(tool="artifactory.set_item_properties",
                                        repo="libs-release", path="a/../b",
                                        properties={"k": "v"}), [])
ok &= check("traversal path rejected on write tool",
            out.get("error") == "path must not contain '.' or '..' path segments", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: path segments percent-encoded (spaces, '?', '#')")
out, ex = run_tool("artifactory", creds(tool="artifactory.get_artifact_info",
                                        repo="libs", path="my dir/sub/file name.jar"), [
    resp(200, body=FILE_INFO),
])
ok &= check("segments quoted, '/' separators kept",
            ex[0].url == f"{API}/storage/libs/my%20dir/sub/file%20name.jar", ex[0].url)
out, ex = run_tool("artifactory", creds(tool="artifactory.get_item_properties",
                                        repo="libs", path="a?x=1/b#c"), [
    resp(200, body={"properties": {}}),
])
ok &= check("'?' and '#' in segments quoted",
            ex[0].url == f"{API}/storage/libs/a%3Fx%3D1/b%23c?properties", ex[0].url)

print("scenario: buildName quoted / traversal rejected")
out, ex = run_tool("artifactory", creds(tool="artifactory.list_builds",
                                        buildName="release/2.0"), [
    resp(200, body={"buildsNumbers": []}),
])
ok &= check("buildName fully quoted (no path escape)",
            ex[0].url == f"{API}/build/release%2F2.0", ex[0].url)
out, ex = run_tool("artifactory", creds(tool="artifactory.list_builds", buildName="b/../x"), [])
ok &= check("traversal buildName rejected",
            out.get("error") == "buildName must not contain '.' or '..' path segments",
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: secret never appears in any output (error path)")
out, ex = run_tool("artifactory", creds(tool="artifactory.list_builds"), [
    err(403, body={"errors": [{"status": 403, "message": "forbidden"}]}),
])
ok &= check("accessToken absent from error output", TOK not in json.dumps(out),
            json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
