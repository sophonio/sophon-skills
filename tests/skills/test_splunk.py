"""Offline mock-HTTP integration tests for the splunk skill."""
import sys
import urllib.parse

from mockhttp import run_tool, resp, err, check

BASE = {"baseUrl": "https://splunk.example.com:8089", "authToken": "jwt-SECRET-token"}
ok = True
all_exchanges = []


def run(tool, extra, steps):
    global all_exchanges
    out, ex = run_tool("splunk", {**BASE, "tool": tool, **extra}, steps)
    all_exchanges += ex
    return out, ex


def body_qs(ex):
    return urllib.parse.parse_qs(ex.body or "")


def url_qs(ex):
    return urllib.parse.parse_qs(urllib.parse.urlsplit(ex.url).query)


# --- 1. oneshot_search: auth exactness + write body ------------------------
out, ex = run("splunk.oneshot_search", {"query": "index=main error", "earliestTime": "-24h@h",
                                        "latestTime": "now", "count": 10},
              [resp(200, body={"fields": [{"name": "host"}],
                               "results": [{"host": "web1", "_raw": "boom"}]})])
ok &= check("oneshot: one request", len(ex) == 1, repr(ex))
ok &= check("oneshot: POST to /services/search/v2/jobs",
            ex[0].method == "POST" and ex[0].url.startswith(
                "https://splunk.example.com:8089/services/search/v2/jobs?"), repr(ex[0]))
ok &= check("oneshot: Bearer auth header exact",
            ex[0].headers.get("authorization") == "Bearer jwt-SECRET-token", str(ex[0].headers))
ok &= check("oneshot: form-encoded content type",
            ex[0].headers.get("content-type") == "application/x-www-form-urlencoded",
            str(ex[0].headers))
qs = body_qs(ex[0])
ok &= check("oneshot: exec_mode=oneshot in body", qs.get("exec_mode") == ["oneshot"], str(qs))
ok &= check("oneshot: 'search ' prefixed", qs.get("search") == ["search index=main error"], str(qs))
ok &= check("oneshot: time bounds in body",
            qs.get("earliest_time") == ["-24h@h"] and qs.get("latest_time") == ["now"], str(qs))
ok &= check("oneshot: count passed through", qs.get("count") == ["10"], str(qs))
ok &= check("oneshot: shaped output count", out.get("count") == 1, str(out)[:200])
ok &= check("oneshot: results passed through", out.get("results") == [{"host": "web1", "_raw": "boom"}],
            str(out)[:200])

# --- generating command: no 'search ' prefix --------------------------------
out, ex = run("splunk.oneshot_search", {"query": "| tstats count where index=main"},
              [resp(200, body={"results": []})])
qs = body_qs(ex[0])
ok &= check("oneshot: leading | not prefixed",
            qs.get("search") == ["| tstats count where index=main"], str(qs))

# --- explicit 'search ' query: not double-prefixed --------------------------
out, ex = run("splunk.oneshot_search", {"query": "search index=web status=500"},
              [resp(200, body={"results": []})])
qs = body_qs(ex[0])
ok &= check("oneshot: existing 'search ' not doubled",
            qs.get("search") == ["search index=web status=500"], str(qs))

# --- 2. create_search_job (write path) --------------------------------------
out, ex = run("splunk.create_search_job", {"query": "index=main"},
              [resp(201, body={"sid": "1720000000.123"})])
qs = body_qs(ex[0])
ok &= check("create_job: POST method", ex[0].method == "POST", repr(ex[0]))
ok &= check("create_job: no exec_mode in body", "exec_mode" not in qs, str(qs))
ok &= check("create_job: search prefixed", qs.get("search") == ["search index=main"], str(qs))
ok &= check("create_job: sid surfaced", out == {"sid": "1720000000.123"}, str(out)[:200])

# --- 3. get_job_status happy path (read) ------------------------------------
out, ex = run("splunk.get_job_status", {"sid": "1720000000.123"},
              [resp(200, body={"entry": [{"name": "1720000000.123", "content": {
                  "dispatchState": "DONE", "doneProgress": 1.0, "isDone": True,
                  "eventCount": 120, "resultCount": 7, "runDuration": 0.42,
                  "eai:acl": {"owner": "admin"}, "custom": {"noise": 1}}}]})])
ok &= check("job_status: GET method", ex[0].method == "GET", repr(ex[0]))
ok &= check("job_status: sid in path",
            "/services/search/v2/jobs/1720000000.123?" in ex[0].url, ex[0].url)
ok &= check("job_status: trimmed fields present",
            out.get("dispatchState") == "DONE" and out.get("isDone") is True
            and out.get("resultCount") == 7, str(out)[:200])
ok &= check("job_status: raw payload fields absent",
            "eai:acl" not in out and "custom" not in out and "entry" not in out, str(out)[:200])

# --- get_job_status on 204/empty body: friendly not-ready object ------------
out, ex = run("splunk.get_job_status", {"sid": "1720000000.999"}, [resp(204, body=b"")])
ok &= check("job_status 204: not an error", "error" not in out, str(out)[:200])
ok &= check("job_status 204: QUEUED + isDone False",
            out.get("dispatchState") == "QUEUED" and out.get("isDone") is False, str(out)[:200])
ok &= check("job_status 204: friendly message", "poll again" in (out.get("message") or ""),
            str(out)[:200])

# --- 4. get_job_results happy path (read) -----------------------------------
out, ex = run("splunk.get_job_results", {"sid": "1720000000.123", "count": 2, "offset": 5},
              [resp(200, body={"fields": [{"name": "host"}],
                               "results": [{"host": "a"}, {"host": "b"}],
                               "preview": False, "init_offset": 5})])
ok &= check("job_results: GET to /results",
            ex[0].method == "GET" and "/services/search/v2/jobs/1720000000.123/results?" in ex[0].url,
            ex[0].url)
uq = url_qs(ex[0])
ok &= check("job_results: count/offset in url",
            uq.get("count") == ["2"] and uq.get("offset") == ["5"], str(uq))
ok &= check("job_results: shaped count", out.get("count") == 2, str(out)[:200])
ok &= check("job_results: raw fields absent", "preview" not in out and "init_offset" not in out,
            str(out)[:200])

# --- get_job_results on 204/empty body: friendly not-finished object --------
out, ex = run("splunk.get_job_results", {"sid": "1720000000.123"}, [resp(204, body=b"")])
ok &= check("job_results 204: not an error", "error" not in out, str(out)[:200])
ok &= check("job_results 204: empty results + message",
            out.get("count") == 0 and out.get("results") == []
            and "still be running" in (out.get("message") or ""), str(out)[:250])

# --- 5. list_saved_searches happy path (read) -------------------------------
out, ex = run("splunk.list_saved_searches", {},
              [resp(200, body={"entry": [
                  {"name": "Errors last hour",
                   "content": {"search": "index=main error", "cron_schedule": "0 * * * *",
                               "is_scheduled": True, "disabled": False,
                               "qualifiedSearch": "search index=main error",
                               "alert_type": "always"}},
                  {"name": "Daily volume",
                   "content": {"search": "| tstats count", "cron_schedule": None,
                               "is_scheduled": False, "disabled": False}}]})])
ok &= check("saved_searches: GET /services/saved/searches",
            ex[0].method == "GET" and "/services/saved/searches?" in ex[0].url, ex[0].url)
ok &= check("saved_searches: default count=30 in url", url_qs(ex[0]).get("count") == ["30"],
            ex[0].url)
ok &= check("saved_searches: count 2", out.get("count") == 2, str(out)[:200])
s0 = (out.get("savedSearches") or [{}])[0]
ok &= check("saved_searches: trimmed fields",
            s0.get("name") == "Errors last hour" and s0.get("cronSchedule") == "0 * * * *"
            and s0.get("isScheduled") is True, str(s0))
ok &= check("saved_searches: raw fields absent",
            "qualifiedSearch" not in s0 and "alert_type" not in s0 and "content" not in s0, str(s0))

# --- 6. run_saved_search: name with a space is URL-quoted (write path) ------
out, ex = run("splunk.run_saved_search", {"name": "Errors last hour"},
              [resp(201, body={"sid": "1720000001.7"})])
ok &= check("run_saved: POST method", ex[0].method == "POST", repr(ex[0]))
ok &= check("run_saved: name quoted in dispatch path",
            "/services/saved/searches/Errors%20last%20hour/dispatch?" in ex[0].url, ex[0].url)
ok &= check("run_saved: sid + name surfaced",
            out == {"name": "Errors last hour", "sid": "1720000001.7"}, str(out)[:200])

# --- 7. list_indexes happy path (read) --------------------------------------
out, ex = run("splunk.list_indexes", {"count": 5},
              [resp(200, body={"entry": [
                  {"name": "main", "content": {"totalEventCount": "123456",
                                               "currentDBSizeMB": "512",
                                               "maxTotalDataSizeMB": "500000",
                                               "disabled": False,
                                               "homePath": "$SPLUNK_DB/main/db"}}]})])
ok &= check("indexes: GET /services/data/indexes",
            ex[0].method == "GET" and "/services/data/indexes?" in ex[0].url, ex[0].url)
ok &= check("indexes: count clamped/passed", url_qs(ex[0]).get("count") == ["5"], ex[0].url)
i0 = (out.get("indexes") or [{}])[0]
ok &= check("indexes: trimmed fields",
            out.get("count") == 1 and i0.get("name") == "main"
            and i0.get("totalEventCount") == "123456", str(out)[:250])
ok &= check("indexes: raw fields absent", "homePath" not in i0, str(i0))

# --- 8. error paths ---------------------------------------------------------
out, ex = run("splunk.list_indexes", {},
              [err(401, body={"messages": [{"type": "ERROR", "text": "Unauthorized"}]})])
raw_out = str(out)
ok &= check("401: friendly error object", isinstance(out.get("error"), str), str(out)[:200])
ok &= check("401: status code included", "401" in out.get("error", ""), str(out)[:200])
ok &= check("401: message text included", "Unauthorized" in out.get("error", ""), str(out)[:200])
ok &= check("401: no traceback", "Traceback" not in raw_out and "urllib" not in raw_out, raw_out[:300])
ok &= check("401: token not leaked", "jwt-SECRET-token" not in raw_out, raw_out[:300])

out, ex = run("splunk.oneshot_search", {"query": "index=main"},
              [err(429, body={"messages": [{"type": "WARN", "text": "Too many searches"}]},
                   headers={"Retry-After": "42"})])
ok &= check("429: error surfaces", "error" in out and "429" in out["error"], str(out)[:200])
ok &= check("429: Retry-After included", "Retry-After: 42" in out["error"], str(out)[:200])
ok &= check("429: token not leaked", "jwt-SECRET-token" not in str(out), str(out)[:300])

# --- non-JSON error body still surfaces cleanly -----------------------------
out, ex = run("splunk.get_job_status", {"sid": "x"},
              [err(500, body="<html>Internal Server Error</html>")])
ok &= check("500: friendly error with status", "500" in out.get("error", ""), str(out)[:200])
ok &= check("500: no traceback", "Traceback" not in str(out), str(out)[:300])

# --- 9. security probes ------------------------------------------------------
evil = "abc/../def?x=1"
out, ex = run("splunk.get_job_status", {"sid": evil}, [resp(204, body=b"")])
enc = urllib.parse.quote(evil, safe="")  # abc%2F..%2Fdef%3Fx%3D1
ok &= check("security: path-ish sid percent-encoded",
            f"/services/search/v2/jobs/{enc}?" in ex[0].url, ex[0].url)
ok &= check("security: no path escape", "/jobs/abc/../def" not in ex[0].url and "?x=1" not in ex[0].url,
            ex[0].url)

out, ex = run("splunk.run_saved_search", {"name": "../../etc/passwd"},
              [resp(201, body={"sid": "s1"})])
ok &= check("security: saved-search name percent-encoded",
            "/services/saved/searches/..%2F..%2Fetc%2Fpasswd/dispatch?" in ex[0].url, ex[0].url)

# --- missing credentials guard ----------------------------------------------
out, ex = run_tool("splunk", {"tool": "splunk.list_indexes", "baseUrl": "", "authToken": ""}, [])
ok &= check("missing creds: no HTTP call, friendly error",
            len(ex) == 0 and "Missing Splunk credentials" in out.get("error", ""), str(out)[:200])

# --- unknown tool ------------------------------------------------------------
out, ex = run_tool("splunk", {**BASE, "tool": "splunk.nope"}, [])
ok &= check("unknown tool: friendly error", "Unknown tool" in out.get("error", ""), str(out)[:200])

# --- global invariants: every request Bearer-authed and output_mode=json ----
ok &= check("ALL exchanges: output_mode=json in url",
            all(url_qs(e).get("output_mode") == ["json"] for e in all_exchanges),
            "; ".join(e.url for e in all_exchanges if url_qs(e).get("output_mode") != ["json"]))
ok &= check("ALL exchanges: Bearer auth header",
            all(e.headers.get("authorization") == "Bearer jwt-SECRET-token" for e in all_exchanges),
            "; ".join(repr(e) for e in all_exchanges
                      if e.headers.get("authorization") != "Bearer jwt-SECRET-token"))
ok &= check("ALL exchanges: Accept application/json",
            all(e.headers.get("accept") == "application/json" for e in all_exchanges))

print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
