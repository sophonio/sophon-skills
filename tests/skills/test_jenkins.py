"""Offline mock-HTTP integration tests for the Sophon "jenkins" skill."""
import base64
import json
import sys
import urllib.error
import urllib.request

import mockhttp
from mockhttp import run_tool, resp, err, check


def netfail(reason="Connection refused"):
    """Scripted step: the transport raises urllib.error.URLError (network unreachable)."""
    return {"kind": "netfail", "reason": reason}


class _NetFailTransport(mockhttp.MockTransport):
    """Extends the harness transport (without modifying it) with a netfail() step kind."""

    def __call__(self, req, *args, **kwargs):
        if self.steps and self.steps[0].get("kind") == "netfail":
            if isinstance(req, str):
                req = urllib.request.Request(req)
            self.exchanges.append(mockhttp.Exchange(req))
            step = self.steps.pop(0)
            raise urllib.error.URLError(step["reason"])
        return super().__call__(req, *args, **kwargs)


mockhttp.MockTransport = _NetFailTransport  # run_tool resolves this at call time

BASE = "https://jenkins.example.com"
CREDS = {"baseUrl": BASE, "username": "alice", "apiToken": "s3cr3t-tok"}
EXPECTED_AUTH = "Basic " + base64.b64encode(b"alice:s3cr3t-tok").decode()

ok = True


def p(tool, **kw):
    d = dict(CREDS)
    d["tool"] = tool
    d.update(kw)
    return d


# ---------------------------------------------------------------- 1. AUTH EXACTNESS + list_jobs
print("[list_jobs: auth + shaping]")
out, ex = run_tool("jenkins", p("jenkins.list_jobs"), [
    resp(200, body={"_class": "hudson.model.Hudson", "jobs": [
        {"_class": "hudson.model.FreeStyleProject", "name": "build-app",
         "url": f"{BASE}/job/build-app/", "color": "blue"},
        {"_class": "org.jenkinsci.plugins.workflow.job.WorkflowJob", "name": "deploy",
         "url": f"{BASE}/job/deploy/", "color": "red_anime"},
        {"_class": "com.cloudbees.hudson.plugins.folder.Folder", "name": "team-a",
         "url": f"{BASE}/job/team-a/", "color": None},
    ]}),
])
ok &= check("one request", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("Basic auth header byte-exact",
            ex[0].headers.get("authorization") == EXPECTED_AUTH, str(ex[0].headers))
ok &= check("Accept: application/json", ex[0].headers.get("accept") == "application/json",
            str(ex[0].headers))
ok &= check("top-level URL is /api/json", ex[0].url.startswith(f"{BASE}/api/json?"), ex[0].url)
ok &= check("URL contains tree=", "tree=" in ex[0].url, ex[0].url)
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("count == 3", out.get("count") == 3, str(out)[:300])
ok &= check("status mapped from color", out["jobs"][0]["status"] == "success", str(out["jobs"][0]))
ok &= check("_anime -> building=True + base status",
            out["jobs"][1]["building"] is True and out["jobs"][1]["status"] == "failed",
            str(out["jobs"][1]))
ok &= check("folder flagged isFolder", out["jobs"][2]["isFolder"] is True, str(out["jobs"][2]))
ok &= check("raw fields (color/_class) absent",
            "color" not in out["jobs"][0] and "_class" not in out["jobs"][0], str(out["jobs"][0]))

print("[list_jobs: folder param nests path]")
out, ex = run_tool("jenkins", p("jenkins.list_jobs", folder="team-a/sub b"), [
    resp(200, body={"jobs": []}),
])
ok &= check("folder path /job/team-a/job/sub%20b",
            ex[0].url.startswith(f"{BASE}/job/team-a/job/sub%20b/api/json?"), ex[0].url)
ok &= check("tree= present", "tree=" in ex[0].url, ex[0].url)
ok &= check("empty folder -> count 0", out.get("count") == 0, str(out))

# ---------------------------------------------------------------- 2. get_job (nested + space)
print("[get_job: nested job path with space, shaping]")
out, ex = run_tool("jenkins", p("jenkins.get_job", job="team-a/svc x"), [
    resp(200, body={"_class": "org.jenkinsci.plugins.workflow.job.WorkflowJob",
                    "name": "svc x", "description": "Builds svc", "buildable": True,
                    "inQueue": False,
                    "healthReport": [{"description": "Build stability", "score": 80,
                                      "iconClassName": "icon-health-60to79"}],
                    "lastBuild": {"number": 42, "result": "SUCCESS",
                                  "timestamp": 1789000000000, "duration": 61000},
                    "lastSuccessfulBuild": {"number": 42},
                    "lastFailedBuild": {"number": 40}}),
])
ok &= check("nested path segments quoted",
            ex[0].url.startswith(f"{BASE}/job/team-a/job/svc%20x/api/json?"), ex[0].url)
ok &= check("tree= present", "tree=" in ex[0].url, ex[0].url)
ok &= check("name/buildable shaped", out.get("name") == "svc x" and out.get("buildable") is True,
            str(out)[:300])
ok &= check("healthReport trimmed to description+score",
            out["healthReport"] == [{"description": "Build stability", "score": 80}],
            str(out.get("healthReport")))
ok &= check("lastBuild passed through", out["lastBuild"]["number"] == 42, str(out.get("lastBuild")))

# ---------------------------------------------------------------- 3. get_build
print("[get_build: parameters, causes, changeSet+changeSets merge]")
out, ex = run_tool("jenkins", p("jenkins.get_build", job="team-a/svc-x", number=7), [
    resp(200, body={
        "number": 7, "result": "FAILURE", "building": False,
        "timestamp": 1789000000000, "duration": 33000,
        "actions": [
            {"parameters": [{"name": "ENV", "value": "prod", "_class": "x"}]},
            {"causes": [{"shortDescription": "Started by user alice"}]},
            {},
        ],
        "changeSet": {"items": [{"msg": "fix: a", "author": {"fullName": "Ann"}}]},
        "changeSets": [{"items": [{"msg": "feat: b", "author": {"fullName": "Bob"}}]}],
    }),
])
ok &= check("build URL /job/team-a/job/svc-x/7/api/json",
            ex[0].url.startswith(f"{BASE}/job/team-a/job/svc-x/7/api/json?"), ex[0].url)
ok &= check("tree= present", "tree=" in ex[0].url, ex[0].url)
ok &= check("result shaped", out.get("result") == "FAILURE" and out.get("number") == 7,
            str(out)[:300])
ok &= check("parameters flattened", out["parameters"] == [{"name": "ENV", "value": "prod"}],
            str(out.get("parameters")))
ok &= check("causes flattened", out["causes"] == ["Started by user alice"], str(out.get("causes")))
ok &= check("changes merged from changeSet + changeSets",
            out["changes"] == [{"msg": "fix: a", "author": "Ann"},
                               {"msg": "feat: b", "author": "Bob"}], str(out.get("changes")))
ok &= check("raw actions field absent", "actions" not in out, str(out)[:300])

print("[get_build: bad number -> friendly error, no HTTP]")
out, ex = run_tool("jenkins", p("jenkins.get_build", job="a", number="seven"), [])
ok &= check("non-integer number errors", "error" in out and "integer" in out["error"], str(out))
ok &= check("no request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------- 4. get_queue
print("[get_queue: shaping]")
out, ex = run_tool("jenkins", p("jenkins.get_queue"), [
    resp(200, body={"_class": "hudson.model.Queue", "items": [
        {"_class": "hudson.model.Queue$WaitingItem", "id": 118,
         "why": "In the quiet period. Expires in 3.2 sec", "inQueueSince": 1789000123456,
         "blocked": False, "buildable": False,
         "task": {"_class": "hudson.model.FreeStyleProject", "name": "deploy",
                  "url": f"{BASE}/job/deploy/", "color": "blue"}},
    ]}),
])
ok &= check("queue URL", ex[0].url.startswith(f"{BASE}/queue/api/json?"), ex[0].url)
ok &= check("tree= present", "tree=" in ex[0].url, ex[0].url)
ok &= check("count == 1", out.get("count") == 1, str(out))
item = out["items"][0]
ok &= check("item trimmed", item["id"] == 118 and item["task"] == {"name": "deploy",
            "url": f"{BASE}/job/deploy/"}, str(item))
ok &= check("raw item fields absent", "blocked" not in item and "_class" not in item, str(item))

# ---------------------------------------------------------------- 5. get_console_log
print("[get_console_log: start offset + progressive headers]")
out, ex = run_tool("jenkins", p("jenkins.get_console_log", job="deploy", number=12, start=120), [
    resp(200, body="Started by user alice\n[Pipeline] stage\n",
         headers={"X-Text-Size": "1234", "X-More-Data": "true"}),
])
ok &= check("progressiveText URL with start",
            ex[0].url == f"{BASE}/job/deploy/12/logText/progressiveText?start=120", ex[0].url)
ok &= check("text passthrough", out.get("text") == "Started by user alice\n[Pipeline] stage\n",
            str(out)[:200])
ok &= check("textSize parsed to int", out.get("textSize") == 1234, str(out.get("textSize")))
ok &= check("hasMore true", out.get("hasMore") is True, str(out))
ok &= check("not truncated", out.get("truncated") is False, str(out))

print("[get_console_log: tailKb clamps and truncates]")
big = "x" * 5000
out, ex = run_tool("jenkins", p("jenkins.get_console_log", job="deploy", number=12, tailKb=1), [
    resp(200, body=big, headers={"X-Text-Size": "5000", "X-More-Data": "false"}),
])
ok &= check("tailKb forces start=0",
            ex[0].url == f"{BASE}/job/deploy/12/logText/progressiveText?start=0", ex[0].url)
ok &= check("kept last 1 KiB", out.get("text") == big[-1024:] and len(out["text"]) == 1024,
            f"len={len(out.get('text') or '')}")
ok &= check("truncated flag set", out.get("truncated") is True, str(out.get("truncated")))
ok &= check("hasMore false", out.get("hasMore") is False, str(out.get("hasMore")))

# ---------------------------------------------------------------- 6. WRITE PATH: trigger_build
print("[trigger_build: no parameters -> POST /build, 201+Location]")
out, ex = run_tool("jenkins", p("jenkins.trigger_build", job="deploy"), [
    resp(201, body="", headers={"Location": f"{BASE}/queue/item/118/"}),
])
ok &= check("POST method", ex[0].method == "POST", ex[0].method)
ok &= check("URL is /job/deploy/build", ex[0].url == f"{BASE}/job/deploy/build", ex[0].url)
ok &= check("no body on plain build", ex[0].body is None, str(ex[0].body))
ok &= check("Basic auth on write", ex[0].headers.get("authorization") == EXPECTED_AUTH,
            str(ex[0].headers))
ok &= check("queued info returned",
            out == {"queued": True, "queueUrl": f"{BASE}/queue/item/118/"}, str(out))

print("[trigger_build: parameters -> exact form body to buildWithParameters]")
out, ex = run_tool("jenkins",
                   p("jenkins.trigger_build", job="team-a/svc-x",
                     parameters={"ENV": "prod", "VERSION": "1.2.3", "DRY_RUN": None}), [
    resp(201, body="", headers={"Location": f"{BASE}/queue/item/119/"}),
])
ok &= check("POST to nested buildWithParameters",
            ex[0].method == "POST"
            and ex[0].url == f"{BASE}/job/team-a/job/svc-x/buildWithParameters", ex[0].url)
ok &= check("exact urlencoded body", ex[0].body == "ENV=prod&VERSION=1.2.3&DRY_RUN=",
            str(ex[0].body))
ok &= check("form content-type",
            ex[0].headers.get("content-type") == "application/x-www-form-urlencoded",
            str(ex[0].headers))
ok &= check("queueUrl from Location", out.get("queueUrl") == f"{BASE}/queue/item/119/", str(out))

# ---------------------------------------------------------------- 7. ERROR PATHS
print("[errors: 401 friendly, no traceback, no secret leak]")
out, ex = run_tool("jenkins", p("jenkins.get_job", job="deploy"), [err(401, body="")])
printed = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), str(out))
ok &= check("mentions HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("friendly auth hint", "authentication failed" in out["error"], out.get("error", ""))
ok &= check("no python traceback", "Traceback" not in printed, printed[:300])
ok &= check("apiToken not leaked in output", "s3cr3t-tok" not in printed, printed[:300])
ok &= check("username not leaked in output", "alice" not in printed, printed[:300])

print("[errors: 404 friendly]")
out, ex = run_tool("jenkins", p("jenkins.get_build", job="deploy", number=999), [
    err(404, body=""),
])
ok &= check("404 hint mentions job path/build number",
            "404" in out.get("error", "") and "check the job path" in out.get("error", ""),
            str(out))

print("[errors: 429 includes Retry-After]")
out, ex = run_tool("jenkins", p("jenkins.list_jobs"), [
    err(429, body="", headers={"Retry-After": "30"}),
])
ok &= check("429 in error", "429" in out.get("error", ""), str(out))
ok &= check("retry-after surfaced", "retry after 30s" in out.get("error", ""), str(out))
ok &= check("rate limited wording", "rate limited" in out.get("error", ""), str(out))

print("[errors: 200 HTML body -> baseUrl hint]")
out, ex = run_tool("jenkins", p("jenkins.list_jobs"), [
    resp(200, body="<!DOCTYPE html><html><head><title>Sign in</title></head></html>"),
])
ok &= check("HTML-on-200 gives baseUrl hint",
            "check baseUrl points at Jenkins" in out.get("error", ""), str(out))
ok &= check("no traceback for HTML", "Traceback" not in json.dumps(out), str(out)[:300])

print("[errors: network unreachable -> URLError branch]")
out, ex = run_tool("jenkins", p("jenkins.list_jobs"), [netfail("Connection refused")])
ok &= check("URLError gives could-not-reach message",
            "Could not reach your Jenkins instance" in out.get("error", ""), str(out))
ok &= check("reason surfaced", "Connection refused" in out.get("error", ""), str(out))
ok &= check("no traceback on URLError", "Traceback" not in json.dumps(out), str(out)[:300])
ok &= check("request was attempted", len(ex) == 1, repr(ex))

print("[errors: unknown tool + missing credentials guards]")
out, ex = run_tool("jenkins", {"tool": "jenkins.nope", **CREDS}, [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: jenkins.nope", str(out))

out, ex = run_tool("jenkins", {"tool": "jenkins.list_jobs", "baseUrl": BASE, "username": "alice"},
                   [])
ok &= check("missing credentials guarded, no HTTP",
            "Missing Jenkins credentials" in out.get("error", "") and len(ex) == 0, str(out))

# ---------------------------------------------------------------- 8. SECURITY PROBES
print("[security: path-ish job id — dot-segment traversal rejected before HTTP]")
out, ex = run_tool("jenkins", p("jenkins.get_job", job="abc/../def?x=1"), [])
ok &= check("'..' segment rejected with friendly error",
            "error" in out and "'.' or '..'" in out["error"], str(out))
ok &= check("no HTTP request made for traversal path", len(ex) == 0, repr(ex))
ok &= check("no traceback on rejection", "Traceback" not in json.dumps(out), str(out)[:300])

print("[security: reserved chars in a segment are percent-encoded, no query injection]")
out, ex = run_tool("jenkins", p("jenkins.get_job", job="def?x=1"), [
    resp(200, body={"name": "def?x=1"}),
])
url = ex[0].url
path_part, sep, query_part = url.partition("?tree")
ok &= check("reserved chars percent-encoded in segment",
            "/job/def%3Fx%3D1/api/json" in url, url)
ok &= check("raw '?x=1' not present in URL", "def?x=1" not in url, url)
ok &= check("only query string is the tree= selector",
            sep == "?tree" and "?" not in path_part.replace("%3F", ""), url)

print("[security: job name with space quoted (must-verify)]")
out, ex = run_tool("jenkins", p("jenkins.get_job", job="team a/svc x"), [
    resp(200, body={"name": "svc x"}),
])
ok &= check("space -> %20 per segment",
            ex[0].url.startswith(f"{BASE}/job/team%20a/job/svc%20x/api/json?"), ex[0].url)

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
