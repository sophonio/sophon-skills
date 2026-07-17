"""Offline mock-HTTP integration tests for the sonarqube skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "https://sonar.example.com"
TOK = "squ_1234abcd-SECRET-VALUE"

DEFAULT_METRICS_ENC = ("coverage%2Cduplicated_lines_density%2Cncloc%2Ccomplexity%2C"
                       "reliability_rating%2Csecurity_rating%2Csqale_rating")


def creds(**extra):
    p = {"baseUrl": BASE, "token": TOK}
    p.update(extra)
    return p


ok = True

# ---------------------------------------------------------------------------
# 1. sonar.search_projects — happy path + auth exactness
# ---------------------------------------------------------------------------
print("scenario: search_projects happy path / auth exactness")
out, ex = run_tool("sonarqube", creds(tool="sonar.search_projects"), [
    # Faithful to the vendor's search_projects-example.json: key/name/qualifier/isFavorite/
    # tags/visibility, plus "analysisDate" (NOT "lastAnalysisDate") when f=analysisDate is
    # requested.
    resp(200, body={"paging": {"pageIndex": 1, "pageSize": 25, "total": 2},
                    "components": [
                        {"key": "proj-a", "name": "Project A", "qualifier": "TRK",
                         "visibility": "public", "isFavorite": False,
                         "analysisDate": "2026-07-01T10:00:00+0000",
                         "tags": ["internal"]},
                        {"key": "proj-b", "name": "Project B", "qualifier": "TRK"},
                    ]}),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact (requests f=analysisDate)",
            ex[0].url == f"{BASE}/api/components/search_projects?ps=25&f=analysisDate",
            ex[0].url)
ok &= check("Authorization is exactly 'Bearer <token>'",
            ex[0].headers.get("authorization") == f"Bearer {TOK}", str(ex[0].headers))
ok &= check("Accept header", ex[0].headers.get("accept") == "application/json",
            str(ex[0].headers))
ok &= check("User-Agent header", ex[0].headers.get("user-agent") == "sophon-sonarqube-skill",
            str(ex[0].headers))
ok &= check("no request body on GET", ex[0].body is None, str(ex[0].body))
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("project shaped to key/name/lastAnalysisDate (analysisDate mapped)",
            out["projects"][0] == {"key": "proj-a", "name": "Project A",
                                   "lastAnalysisDate": "2026-07-01T10:00:00+0000"},
            str(out["projects"][0]))
ok &= check("raw fields absent (qualifier/visibility/tags)",
            "qualifier" not in out["projects"][0] and "visibility" not in out["projects"][0]
            and "tags" not in out["projects"][0], str(out["projects"][0]))
ok &= check("token not echoed in output", TOK not in json.dumps(out))

# organization (Cloud) appended as query param
print("scenario: organization appended as organization= query param")
out, ex = run_tool("sonarqube", creds(tool="sonar.search_projects",
                                      organization="acme-org"), [
    resp(200, body={"components": []}),
])
ok &= check("organization appended to URL",
            ex[0].url == f"{BASE}/api/components/search_projects"
                         "?ps=25&f=analysisDate&organization=acme-org",
            ex[0].url)
ok &= check("empty result count 0", out.get("count") == 0, str(out))

# ps clamp <= 100
print("scenario: ps clamped to 100")
out, ex = run_tool("sonarqube", creds(tool="sonar.search_projects", limit=500), [
    resp(200, body={"components": []}),
])
ok &= check("ps clamped to 100",
            ex[0].url == f"{BASE}/api/components/search_projects?ps=100&f=analysisDate",
            ex[0].url)

# filter + pagination params encoded byte-exactly
print("scenario: search_projects filter and page params")
out, ex = run_tool("sonarqube", creds(tool="sonar.search_projects",
                                      filter="ncloc > 1000", page=2), [
    resp(200, body={"components": []}),
])
ok &= check("filter and p encoded byte-exact",
            ex[0].url == f"{BASE}/api/components/search_projects"
                         "?filter=ncloc+%3E+1000&ps=25&p=2&f=analysisDate",
            ex[0].url)

# ---------------------------------------------------------------------------
# 2. sonar.get_quality_gate_status — happy path, failing conditions only
# ---------------------------------------------------------------------------
print("scenario: get_quality_gate_status happy path")
out, ex = run_tool("sonarqube", creds(tool="sonar.get_quality_gate_status",
                                      projectKey="proj-a", branch="main"), [
    resp(200, body={"projectStatus": {
        "status": "ERROR",
        "ignoredConditions": False,
        "conditions": [
            {"status": "ERROR", "metricKey": "coverage", "comparator": "LT",
             "errorThreshold": "80", "actualValue": "62.5"},
            {"status": "OK", "metricKey": "new_bugs", "comparator": "GT",
             "errorThreshold": "0", "actualValue": "0"},
            {"status": "NO_VALUE", "metricKey": "new_coverage", "comparator": "LT",
             "errorThreshold": "80"},
        ]}}),
])
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}/api/qualitygates/project_status?projectKey=proj-a&branch=main",
            ex[0].url)
ok &= check("Bearer auth", ex[0].headers.get("authorization") == f"Bearer {TOK}")
ok &= check("gate status ERROR", out.get("status") == "ERROR", str(out)[:200])
ok &= check("only failing conditions returned (OK and NO_VALUE excluded)",
            len(out.get("failingConditions", [])) == 1, str(out)[:300])
ok &= check("failing condition has metric/actual/threshold",
            out["failingConditions"][0]["metric"] == "coverage"
            and out["failingConditions"][0]["actual"] == "62.5"
            and out["failingConditions"][0]["threshold"] == "80"
            and out["failingConditions"][0]["comparator"] == "LT",
            str(out["failingConditions"][0]))
ok &= check("branch echoed", out.get("branch") == "main", str(out)[:200])

# ---------------------------------------------------------------------------
# 3. sonar.search_issues — happy path with filters
# ---------------------------------------------------------------------------
print("scenario: search_issues happy path with filters")
out, ex = run_tool("sonarqube", creds(tool="sonar.search_issues", projectKey="proj-a",
                                      severities="CRITICAL,BLOCKER", types="BUG",
                                      limit=10), [
    resp(200, body={"total": 1, "paging": {"pageIndex": 1, "pageSize": 10, "total": 1},
                    "issues": [
                        {"key": "AXi4-abc123", "rule": "java:S2095", "severity": "CRITICAL",
                         "component": "proj-a:src/Main.java", "project": "proj-a",
                         "line": 42, "hash": "deadbeef",
                         "textRange": {"startLine": 42, "endLine": 42},
                         "flows": [], "status": "OPEN", "message": "Close this resource.",
                         "effort": "5min", "debt": "5min", "tags": ["cwe"],
                         "type": "BUG"}],
                    "components": [{"key": "proj-a:src/Main.java"}]}),
])
ok &= check("URL byte-exact (componentKeys + encoded severities + ps)",
            ex[0].url == f"{BASE}/api/issues/search?componentKeys=proj-a"
                         "&severities=CRITICAL%2CBLOCKER&types=BUG&ps=10",
            ex[0].url)
ok &= check("count/total", out.get("count") == 1 and out.get("total") == 1, str(out)[:200])
iss = out["issues"][0]
ok &= check("issue shaped",
            iss == {"key": "AXi4-abc123", "rule": "java:S2095", "severity": "CRITICAL",
                    "type": "BUG", "component": "proj-a:src/Main.java", "line": 42,
                    "message": "Close this resource.", "status": "OPEN"},
            str(iss))
ok &= check("raw fields absent (flows/textRange/hash)",
            "flows" not in iss and "textRange" not in iss and "hash" not in iss, str(iss))

# list-valued filter joined with commas
print("scenario: search_issues accepts list-valued severities")
out, ex = run_tool("sonarqube", creds(tool="sonar.search_issues",
                                      severities=["MAJOR", "MINOR"]), [
    resp(200, body={"paging": {"total": 0}, "issues": []}),
])
ok &= check("list joined and encoded",
            ex[0].url == f"{BASE}/api/issues/search?severities=MAJOR%2CMINOR&ps=25",
            ex[0].url)

# ---------------------------------------------------------------------------
# 4. sonar.search_hotspots — happy path
# ---------------------------------------------------------------------------
print("scenario: search_hotspots happy path")
out, ex = run_tool("sonarqube", creds(tool="sonar.search_hotspots", projectKey="proj-a",
                                      status="TO_REVIEW"), [
    resp(200, body={"paging": {"total": 1}, "hotspots": [
        {"key": "hs-1", "component": "proj-a:src/db.py", "project": "proj-a",
         "securityCategory": "sql-injection", "vulnerabilityProbability": "HIGH",
         "status": "TO_REVIEW", "line": 7, "message": "Make sure this SQL is safe.",
         "author": "dev@x.co", "creationDate": "2026-06-01T00:00:00+0000",
         "ruleKey": "python:S2077"}]}),
])
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}/api/hotspots/search?projectKey=proj-a&status=TO_REVIEW&ps=25",
            ex[0].url)
hs = out["hotspots"][0]
ok &= check("hotspot shaped",
            hs == {"key": "hs-1", "securityCategory": "sql-injection",
                   "vulnerabilityProbability": "HIGH", "component": "proj-a:src/db.py",
                   "line": 7, "message": "Make sure this SQL is safe."},
            str(hs))
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])
ok &= check("raw fields absent (author/ruleKey)",
            "author" not in hs and "ruleKey" not in hs, str(hs))

# ---------------------------------------------------------------------------
# 5. sonar.get_measures — default metric set + metric/value pairs
# ---------------------------------------------------------------------------
print("scenario: get_measures default metric set")
out, ex = run_tool("sonarqube", creds(tool="sonar.get_measures", component="proj-a"), [
    resp(200, body={"component": {"key": "proj-a", "name": "Project A",
                    "qualifier": "TRK", "measures": [
                        {"metric": "coverage", "value": "85.0", "bestValue": False},
                        {"metric": "ncloc", "value": "1200"},
                        {"metric": "new_coverage", "period": {"index": 1, "value": "70.0"}},
                    ]}}),
])
ok &= check("URL byte-exact with default metricKeys",
            ex[0].url == f"{BASE}/api/measures/component?component=proj-a"
                         f"&metricKeys={DEFAULT_METRICS_ENC}",
            ex[0].url)
ok &= check("metric/value pairs",
            out == {"component": "proj-a",
                    "measures": {"coverage": "85.0", "ncloc": "1200",
                                 "new_coverage": "70.0"}},
            str(out))

print("scenario: get_measures metricKeys override")
out, ex = run_tool("sonarqube", creds(tool="sonar.get_measures", component="proj-a",
                                      metricKeys="coverage"), [
    resp(200, body={"component": {"key": "proj-a", "measures": [
        {"metric": "coverage", "value": "85.0"}]}}),
])
ok &= check("override respected",
            ex[0].url == f"{BASE}/api/measures/component?component=proj-a&metricKeys=coverage",
            ex[0].url)

print("scenario: get_measures handles Cloud-style periods array for new_* metrics")
out, ex = run_tool("sonarqube", creds(tool="sonar.get_measures", component="proj-a",
                                      metricKeys="new_coverage"), [
    resp(200, body={"component": {"key": "proj-a", "measures": [
        {"metric": "new_coverage", "periods": [{"index": 1, "value": "70.0"}]}]}}),
])
ok &= check("periods-array value extracted",
            out == {"component": "proj-a", "measures": {"new_coverage": "70.0"}}, str(out))

# ---------------------------------------------------------------------------
# 6. sonar.get_analysis_history — date/value series
# ---------------------------------------------------------------------------
print("scenario: get_analysis_history happy path")
out, ex = run_tool("sonarqube", creds(tool="sonar.get_analysis_history",
                                      component="proj-a", metrics="coverage"), [
    resp(200, body={"paging": {"total": 2}, "measures": [
        {"metric": "coverage", "history": [
            {"date": "2026-06-01T00:00:00+0000", "value": "80.0"},
            {"date": "2026-07-01T00:00:00+0000", "value": "85.0"}]}]}),
])
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}/api/measures/search_history?component=proj-a"
                         "&metrics=coverage&ps=25",
            ex[0].url)
ok &= check("date/value series shaped",
            out == {"component": "proj-a", "metrics": [
                {"metric": "coverage", "history": [
                    {"date": "2026-06-01T00:00:00+0000", "value": "80.0"},
                    {"date": "2026-07-01T00:00:00+0000", "value": "85.0"}]}]},
            str(out))

# ---------------------------------------------------------------------------
# 7. WRITE PATH — sonar.assign_issue POSTs a form-encoded body
# ---------------------------------------------------------------------------
print("scenario: assign_issue write path (form-encoded POST)")
out, ex = run_tool("sonarqube", creds(tool="sonar.assign_issue", issue="AXi4-abc123",
                                      assignee="jane.doe"), [
    resp(200, body={"issue": {"key": "AXi4-abc123", "assignee": "jane.doe"}}),
])
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL byte-exact (no query)", ex[0].url == f"{BASE}/api/issues/assign", ex[0].url)
ok &= check("body form-encoded byte-exact", ex[0].body == "issue=AXi4-abc123&assignee=jane.doe",
            str(ex[0].body))
ok &= check("Content-Type is x-www-form-urlencoded (not JSON)",
            ex[0].headers.get("content-type") == "application/x-www-form-urlencoded",
            str(ex[0].headers))
ok &= check("Bearer auth on write", ex[0].headers.get("authorization") == f"Bearer {TOK}")
ok &= check("success output",
            out == {"issue": "AXi4-abc123", "assignee": "jane.doe", "updated": True},
            str(out))

print("scenario: assign_issue without assignee unassigns (no assignee field in body)")
out, ex = run_tool("sonarqube", creds(tool="sonar.assign_issue", issue="AXi4-abc123"), [
    resp(200, body={"issue": {"key": "AXi4-abc123"}}),
])
ok &= check("body has only issue=", ex[0].body == "issue=AXi4-abc123", str(ex[0].body))
ok &= check("unassign output", out == {"issue": "AXi4-abc123", "assignee": None,
                                       "updated": True}, str(out))

print("scenario: assign_issue with organization appends organization= to the POST URL")
out, ex = run_tool("sonarqube", creds(tool="sonar.assign_issue", issue="AXi4-abc123",
                                      assignee="jane.doe", organization="acme-org"), [
    resp(200, body={"issue": {"key": "AXi4-abc123", "assignee": "jane.doe"}}),
])
ok &= check("organization on write-path URL",
            ex[0].url == f"{BASE}/api/issues/assign?organization=acme-org", ex[0].url)
ok &= check("form body unchanged", ex[0].body == "issue=AXi4-abc123&assignee=jane.doe",
            str(ex[0].body))

# ---------------------------------------------------------------------------
# 8. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 surfaces friendly error")
out, ex = run_tool("sonarqube", creds(tool="sonar.search_projects"), [
    err(401, body={"errors": [{"msg": "Authentication required"}]}),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("includes API error msg", "Authentication required" in out["error"],
            out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw,
            raw[:300])
ok &= check("token not leaked in error output", TOK not in raw, raw[:300])

print("scenario: 429 (Cloud rate limit) includes Retry-After backoff hint")
out, ex = run_tool("sonarqube", creds(tool="sonar.search_issues"), [
    err(429, body={"errors": [{"msg": "Too many requests"}]},
        headers={"Retry-After": "42"}),
])
ok &= check("429 error surfaced", "error" in out and "429" in out["error"], str(out)[:300])
ok &= check("Retry-After value included", "42" in out["error"], out.get("error", ""))
ok &= check("backoff hint present", "retry" in out["error"].lower(), out.get("error", ""))

print("scenario: 429 without Retry-After still hints backoff")
out, ex = run_tool("sonarqube", creds(tool="sonar.search_issues"), [
    err(429, body=""),
])
ok &= check("generic backoff hint", "back off" in out.get("error", "").lower(),
            out.get("error", ""))

print("scenario: non-JSON error body tolerated")
out, ex = run_tool("sonarqube", creds(tool="sonar.search_projects"), [
    err(502, body="<html>bad gateway</html>"),
])
ok &= check("502 non-JSON body still friendly",
            "error" in out and "502" in out["error"] and "Traceback" not in json.dumps(out),
            str(out)[:300])

print("scenario: missing required params -> friendly error, no HTTP call")
out, ex = run_tool("sonarqube", creds(tool="sonar.get_quality_gate_status"), [])
ok &= check("projectKey required error", out.get("error") == "projectKey required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))
out, ex = run_tool("sonarqube", creds(tool="sonar.search_hotspots"), [])
ok &= check("hotspots projectKey required", out.get("error") == "projectKey required",
            str(out))
out, ex = run_tool("sonarqube", creds(tool="sonar.get_measures"), [])
ok &= check("component required", out.get("error") == "component required", str(out))
out, ex = run_tool("sonarqube", creds(tool="sonar.assign_issue"), [])
ok &= check("issue required", out.get("error") == "issue required", str(out))

print("scenario: missing credentials -> friendly connect-first error, no HTTP call")
out, ex = run_tool("sonarqube", {"tool": "sonar.search_projects", "baseUrl": "",
                                 "token": ""}, [])
ok &= check("connect-first message names the integration and fields",
            out.get("error") == "Missing SonarQube credentials: connect the SonarQube "
                                "integration first (baseUrl, token).", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("sonarqube", creds(tool="sonar.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: sonar.nope", str(out))

# ---------------------------------------------------------------------------
# 9. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-injection projectKey is percent-encoded into the query string")
evil = "abc/../def?x=1"
out, ex = run_tool("sonarqube", creds(tool="sonar.search_issues", projectKey=evil), [
    resp(200, body={"paging": {"total": 0}, "issues": []}),
])
ok &= check("evil key fully quoted in query",
            ex[0].url == f"{BASE}/api/issues/search?componentKeys=abc%2F..%2Fdef%3Fx%3D1&ps=25",
            ex[0].url)
ok &= check("no raw '../' and single '?' in URL",
            "../" not in ex[0].url and ex[0].url.count("?") == 1, ex[0].url)

print("scenario: path-injection component on get_measures percent-encoded")
out, ex = run_tool("sonarqube", creds(tool="sonar.get_measures", component=evil,
                                      metricKeys="ncloc"), [
    resp(200, body={"component": {"key": "x", "measures": []}}),
])
ok &= check("component quoted",
            ex[0].url == f"{BASE}/api/measures/component?component=abc%2F..%2Fdef%3Fx%3D1"
                         "&metricKeys=ncloc",
            ex[0].url)

print("scenario: path-injection issue key on write path percent-encoded in form body")
out, ex = run_tool("sonarqube", creds(tool="sonar.assign_issue", issue="a&b=c",
                                      assignee="x y"), [
    resp(200, body={}),
])
ok &= check("form body encodes reserved chars", ex[0].body == "issue=a%26b%3Dc&assignee=x+y",
            str(ex[0].body))

print("scenario: secret never appears in any output (error path)")
out, ex = run_tool("sonarqube", creds(tool="sonar.search_hotspots", projectKey="proj-a"), [
    err(403, body={"errors": [{"msg": "Insufficient privileges"}]}),
])
ok &= check("token absent from error output", TOK not in json.dumps(out),
            json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
