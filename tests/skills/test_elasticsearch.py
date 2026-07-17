"""Offline mock-HTTP integration tests for the elasticsearch skill."""
import base64
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = {"baseUrl": "https://es.example.com:9200", "apiKey": "QVBJS0VZaWQ6c2VjcmV0"}
BASIC = {"baseUrl": "https://es.example.com:9200", "username": "elastic", "password": "s3cr3t-pw"}

ok = True


# ---------------------------------------------------------------- auth exactness
# 1) apiKey set -> Authorization: ApiKey {value}
out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.cluster_health"},
    [resp(200, body={"cluster_name": "prod", "status": "green", "number_of_nodes": 3,
                     "number_of_data_nodes": 2, "active_primary_shards": 10,
                     "active_shards": 20, "relocating_shards": 0, "initializing_shards": 0,
                     "unassigned_shards": 0, "active_shards_percent_as_number": 100.0})])
ok &= check("auth: ApiKey header byte-exact",
            ex[0].headers.get("authorization") == "ApiKey QVBJS0VZaWQ6c2VjcmV0",
            str(ex[0].headers))
ok &= check("auth: accept + content negotiation headers",
            ex[0].headers.get("accept") == "application/json"
            and ex[0].headers.get("user-agent") == "sophon-elasticsearch-skill",
            str(ex[0].headers))
ok &= check("cluster_health: URL", ex[0].url == "https://es.example.com:9200/_cluster/health",
            ex[0].url)
ok &= check("cluster_health: shaped output",
            out == {"clusterName": "prod", "status": "green", "numberOfNodes": 3,
                    "numberOfDataNodes": 2, "activePrimaryShards": 10, "activeShards": 20,
                    "relocatingShards": 0, "initializingShards": 0, "unassignedShards": 0,
                    "activeShardsPercent": 100.0},
            str(out)[:300])

# 2) username/password only -> Basic base64(user:pass), byte-exact
expected_basic = "Basic " + base64.b64encode(b"elastic:s3cr3t-pw").decode()
out, ex = run_tool(
    "elasticsearch",
    {**BASIC, "tool": "es.count", "index": "logs-2026"},
    [resp(200, body={"count": 42, "_shards": {"total": 1, "successful": 1}})])
ok &= check("auth: Basic header byte-exact",
            ex[0].headers.get("authorization") == expected_basic, str(ex[0].headers))
ok &= check("count: POST to /{index}/_count",
            ex[0].method == "POST" and ex[0].url == "https://es.example.com:9200/logs-2026/_count",
            repr(ex[0]))
ok &= check("count: no body when no query given", ex[0].body is None, str(ex[0].body))
ok &= check("count: shaped output drops _shards", out == {"count": 42}, str(out))

# 3) apiKey wins over username/password when both present
out, ex = run_tool(
    "elasticsearch",
    {**BASIC, "apiKey": "QVBJS0VZaWQ6c2VjcmV0", "tool": "es.count", "index": "a"},
    [resp(200, body={"count": 0})])
ok &= check("auth: apiKey preferred over basic when both set",
            ex[0].headers.get("authorization") == "ApiKey QVBJS0VZaWQ6c2VjcmV0",
            str(ex[0].headers))


# ---------------------------------------------------------------- es.search happy path
out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.search", "index": "logs-*", "size": 500,
     "query": {"match": {"message": "error"}},
     "sort": [{"@timestamp": "desc"}]},
    [resp(200, body={
        "took": 12, "timed_out": False,
        "_shards": {"total": 5, "successful": 5, "skipped": 0, "failed": 0},
        "hits": {
            "total": {"value": 1337, "relation": "eq"},
            "max_score": 4.2,
            "hits": [
                {"_index": "logs-2026.07", "_id": "d1", "_score": 4.2, "_type": "_doc",
                 "_source": {"message": "error: boom", "level": "error"}},
                {"_index": "logs-2026.07", "_id": "d2", "_score": 3.1, "_type": "_doc",
                 "_source": {"message": "error: bang", "level": "error"}},
            ],
        },
    })])
ok &= check("search: POST to /{index}/_search with wildcard index kept",
            ex[0].method == "POST"
            and ex[0].url == "https://es.example.com:9200/logs-*/_search", repr(ex[0]))
ok &= check("search: body passes query dict and clamps size to 100",
            ex[0].json == {"size": 100, "query": {"match": {"message": "error"}},
                           "sort": [{"@timestamp": "desc"}]},
            str(ex[0].body))
ok &= check("search: Content-Type json on body",
            ex[0].headers.get("content-type") == "application/json", str(ex[0].headers))
ok &= check("search: count + total shaping",
            out.get("count") == 2 and out.get("total") == {"value": 1337, "relation": "eq"},
            str(out)[:300])
ok &= check("search: hits trimmed (raw _type/took/_shards absent)",
            out["hits"][0] == {"_id": "d1", "_index": "logs-2026.07", "_score": 4.2,
                               "_source": {"message": "error: boom", "level": "error"}}
            and "took" not in out and "_shards" not in out and "aggregations" not in out,
            str(out)[:400])

# search: default size is 10 when omitted; bare-int legacy total normalized
out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.search", "index": "docs"},
    [resp(200, body={"hits": {"total": 7, "hits": []}})])
ok &= check("search: default body is {'size': 10}", ex[0].json == {"size": 10}, str(ex[0].body))
ok &= check("search: legacy int total normalized",
            out == {"total": {"value": 7, "relation": "eq"}, "count": 0, "hits": []},
            str(out))


# ---------------------------------------------------------------- es.list_indices
out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.list_indices"},
    [resp(200, body=[
        {"health": "green", "status": "open", "index": "logs-2026.07", "uuid": "xyz",
         "pri": "1", "rep": "1", "docs.count": "1000", "docs.deleted": "3",
         "store.size": "1.2mb", "pri.store.size": "600kb"},
        {"health": "yellow", "status": "open", "index": "people", "uuid": "abc",
         "pri": "1", "rep": "1", "docs.count": "5", "docs.deleted": "0",
         "store.size": "20kb", "pri.store.size": "10kb"},
    ])])
ok &= check("list_indices: _cat/indices URL has format=json",
            ex[0].url.startswith("https://es.example.com:9200/_cat/indices?")
            and "format=json" in ex[0].url, ex[0].url)
ok &= check("list_indices: sorted-by-index query param", "s=index" in ex[0].url, ex[0].url)
ok &= check("list_indices: shaped output, raw uuid/pri fields absent",
            out == {"count": 2, "indices": [
                {"index": "logs-2026.07", "health": "green", "docsCount": "1000",
                 "storeSize": "1.2mb"},
                {"index": "people", "health": "yellow", "docsCount": "5", "storeSize": "20kb"},
            ]},
            str(out)[:400])


# ---------------------------------------------------------------- es.get_mapping
out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.get_mapping", "index": "people"},
    [resp(200, body={"people": {"mappings": {"properties": {
        "name": {"type": "text"}, "age": {"type": "integer"}}}}})])
ok &= check("get_mapping: GET /{index}/_mapping",
            ex[0].method == "GET" and ex[0].url == "https://es.example.com:9200/people/_mapping",
            repr(ex[0]))
ok &= check("get_mapping: properties extracted",
            out == {"count": 1, "mappings": {"people": {"name": {"type": "text"},
                                                        "age": {"type": "integer"}}}},
            str(out)[:300])


# ---------------------------------------------------------------- es.get_document happy path
out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.get_document", "index": "people", "id": "42"},
    [resp(200, body={"_index": "people", "_id": "42", "_version": 3, "_seq_no": 9,
                     "_primary_term": 1, "found": True, "_source": {"name": "Ann"}})])
ok &= check("get_document: GET /{index}/_doc/{id}",
            ex[0].method == "GET" and ex[0].url == "https://es.example.com:9200/people/_doc/42",
            repr(ex[0]))
ok &= check("get_document: shaped output drops _version/_seq_no",
            out == {"_index": "people", "_id": "42", "found": True, "_source": {"name": "Ann"}},
            str(out)[:300])


# ---------------------------------------------------------------- write path: es.index_document
out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.index_document", "index": "people", "id": "42",
     "document": {"name": "Ann", "age": 30}},
    [resp(201, body={"_index": "people", "_id": "42", "result": "created", "_version": 1,
                     "_shards": {"total": 2, "successful": 1, "failed": 0}})])
ok &= check("index_document: PUT to /{index}/_doc/{id} when id given",
            ex[0].method == "PUT"
            and ex[0].url == "https://es.example.com:9200/people/_doc/42", repr(ex[0]))
ok &= check("index_document: exact JSON body",
            ex[0].json == {"name": "Ann", "age": 30}, str(ex[0].body))
ok &= check("index_document: shaped output drops _shards",
            out == {"_index": "people", "_id": "42", "result": "created", "_version": 1},
            str(out)[:300])

out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.index_document", "index": "people",
     "document": {"name": "Bob"}},
    [resp(201, body={"_index": "people", "_id": "AUTOGEN1", "result": "created",
                     "_version": 1})])
ok &= check("index_document: POST to /{index}/_doc when id omitted",
            ex[0].method == "POST"
            and ex[0].url == "https://es.example.com:9200/people/_doc", repr(ex[0]))
ok &= check("index_document: auto-id output", out.get("_id") == "AUTOGEN1", str(out))

out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.index_document", "index": "people", "document": "not-an-object"},
    [])
ok &= check("index_document: non-object document rejected without HTTP call",
            len(ex) == 0 and "document" in out.get("error", ""), str(out))


# ---------------------------------------------------------------- error paths
# 401 -> friendly error containing the status, no traceback, no secret leak
out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.search", "index": "logs"},
    [err(401, body={"error": {"type": "security_exception",
                              "reason": "unable to authenticate with provided credentials"},
                    "status": 401})])
printed = json.dumps(out)
ok &= check("401: friendly {'error': ...} with status",
            set(out.keys()) == {"error"} and "401" in out["error"]
            and "unable to authenticate" in out["error"], str(out))
ok &= check("401: no Python traceback in output",
            "Traceback" not in printed and "urllib" not in printed, printed[:300])
ok &= check("401: apiKey secret not leaked in output",
            "QVBJS0VZaWQ6c2VjcmV0" not in printed, printed[:300])

# basic-auth error path must not leak the password either
out, ex = run_tool(
    "elasticsearch",
    {**BASIC, "tool": "es.cluster_health"},
    [err(401, body={"error": "Unauthorized"})])
printed = json.dumps(out)
ok &= check("401 basic: password not leaked in output",
            "s3cr3t-pw" not in printed and base64.b64encode(b"elastic:s3cr3t-pw").decode()
            not in printed, printed[:300])
ok &= check("401 basic: string-form error body surfaced",
            "401" in out.get("error", "") and "Unauthorized" in out.get("error", ""), str(out))

# 429 -> Retry-After header appended to the message
out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.count", "index": "logs"},
    [err(429, body={"error": {"type": "circuit_breaking_exception",
                              "reason": "too many requests"}},
         headers={"Retry-After": "17"})])
ok &= check("429: status + reason + Retry-After surfaced",
            "429" in out.get("error", "") and "too many requests" in out.get("error", "")
            and "Retry-After: 17" in out.get("error", ""), str(out))

# unreachable host -> URLError path (no HTTP exchange scripted, transport not hit here)
out, ex = run_tool(
    "elasticsearch",
    {"tool": "es.search", "index": "logs", "baseUrl": ""},
    [])
ok &= check("missing creds: friendly connect-integration error, no HTTP call",
            len(ex) == 0 and "credentials" in out.get("error", "").lower(), str(out))

out, ex = run_tool("elasticsearch", {**BASE, "tool": "es.nope"}, [])
ok &= check("unknown tool: friendly error", out == {"error": "Unknown tool: es.nope"}, str(out))


# ---------------------------------------------------------------- es.esql_query must-verify
# happy path
out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.esql_query", "query": "FROM logs-* | LIMIT 2"},
    [resp(200, body={"columns": [{"name": "level", "type": "keyword"},
                                 {"name": "message", "type": "text"}],
                     "values": [["error", "boom"], ["warn", "meh"]]})])
ok &= check("esql: POST /_query with query string body",
            ex[0].method == "POST" and ex[0].url == "https://es.example.com:9200/_query"
            and ex[0].json == {"query": "FROM logs-* | LIMIT 2"}, repr(ex[0]))
ok &= check("esql: columns flattened to names + count",
            out == {"columns": ["level", "message"], "count": 2,
                    "values": [["error", "boom"], ["warn", "meh"]]}, str(out)[:300])

# 404 -> not-supported message
out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.esql_query", "query": "FROM x"},
    [err(404, body={"error": {"type": "not_found", "reason": "not found"}})])
ok &= check("esql: 404 -> ES|QL-not-supported message",
            out.get("error") == "ES|QL is not supported by this cluster (requires Elasticsearch 8.11+)",
            str(out))

# OpenSearch-style 400 "no handler found" -> not-supported message
out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.esql_query", "query": "FROM x"},
    [err(400, body={"error": "no handler found for uri [/_query] and method [POST]",
                    "status": 400})])
ok &= check("esql: 400 no-handler -> ES|QL-not-supported message",
            out.get("error") == "ES|QL is not supported by this cluster (requires Elasticsearch 8.11+)",
            str(out))

# real 400 parsing_exception -> surfaces the actual error text, NOT the not-supported message
out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.esql_query", "query": "FRUM logs"},
    [err(400, body={"error": {"type": "parsing_exception",
                              "reason": "line 1:1: mismatched input 'FRUM'"},
                    "status": 400})])
ok &= check("esql: 400 parsing_exception surfaces real error text",
            "mismatched input 'FRUM'" in out.get("error", "")
            and "not supported" not in out.get("error", ""), str(out))


# ---------------------------------------------------------------- security probes
# path-ish document id must be percent-encoded (no path escape, no query injection)
out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.get_document", "index": "people", "id": "abc/../def?x=1"},
    [resp(200, body={"_index": "people", "_id": "abc/../def?x=1", "found": True,
                     "_source": {}})])
ok &= check("security: path-ish id percent-encoded in URL",
            ex[0].url == "https://es.example.com:9200/people/_doc/abc%2F..%2Fdef%3Fx%3D1",
            ex[0].url)

# path-ish index name must not escape the path either (index keeps * and , only)
out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.count", "index": "../_security/user?x=1"},
    [resp(200, body={"count": 0})])
ok &= check("security: path-ish index percent-encoded in URL",
            ex[0].url == "https://es.example.com:9200/..%2F_security%2Fuser%3Fx%3D1/_count",
            ex[0].url)

# write path with path-ish id
out, ex = run_tool(
    "elasticsearch",
    {**BASE, "tool": "es.index_document", "index": "people", "id": "../evil",
     "document": {"a": 1}},
    [resp(201, body={"_index": "people", "_id": "../evil", "result": "created",
                     "_version": 1})])
ok &= check("security: index_document id percent-encoded in URL",
            ex[0].url == "https://es.example.com:9200/people/_doc/..%2Fevil", ex[0].url)


print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
