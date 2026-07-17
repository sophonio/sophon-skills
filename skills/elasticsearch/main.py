"""Elasticsearch integration skill — search, query, and index documents over the REST API.

Pure standard library (urllib + ssl) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (baseUrl, apiKey, username, password, caCert,
insecureTls).

Auth: if apiKey is set we send "Authorization: ApiKey <apiKey>" (the base64 id:key string Kibana
hands out when you create an API key); otherwise HTTP basic auth with username + password. This
works against Elastic Cloud, Elastic serverless, self-managed Elasticsearch 8/9, and OpenSearch
(basic auth). AWS OpenSearch domains in IAM/SigV4-only mode are not supported.

TLS: self-signed certificates are common on self-managed clusters. When a caCert PEM is provided
we trust it; when insecureTls is 'true' we disable verification (not recommended).
"""

import base64
import json
import ssl
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("baseUrl") or "").rstrip("/")
api_key = params.get("apiKey") or ""
username = params.get("username") or ""
password = params.get("password") or ""
ca_cert = params.get("caCert") or ""
insecure = str(params.get("insecureTls") or "").strip().lower() == "true"


def auth_header():
    """Build the Authorization header: ApiKey when set, else HTTP basic auth."""
    if api_key:
        return f"ApiKey {api_key}"
    creds = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {creds}"


def ssl_context():
    """Build an SSL context: trust the custom CA if given, or skip verification if requested."""
    if ca_cert.strip():
        ctx = ssl.create_default_context(cadata=ca_cert)
    else:
        ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def request(method, path, data=None, query=None):
    """Make an authenticated request to the cluster. Returns parsed JSON (or None for 204/empty)."""
    url = f"{base_url}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    headers = {
        "Authorization": auth_header(),
        "Accept": "application/json",
        "User-Agent": "sophon-elasticsearch-skill",
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ssl_context()) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        message = detail
        try:
            parsed = json.loads(detail)
            err = parsed.get("error")
            if isinstance(err, dict):
                message = err.get("reason") or err.get("type") or detail
            elif isinstance(err, str) and err:
                message = err
        except (ValueError, TypeError):
            pass
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            if retry_after:
                message = f"{message} (Retry-After: {retry_after})"
        raise RuntimeError(f"Elasticsearch API error {e.code}: {message}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Elasticsearch at {base_url}: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def index_path(index):
    """URL-encode an index name into a path segment (keeps * and , for wildcards/multi-index)."""
    if not index:
        raise ValueError("index is required")
    return urllib.parse.quote(str(index), safe="*,")


def hit_summary(hit):
    return {
        "_id": hit.get("_id"),
        "_index": hit.get("_index"),
        "_score": hit.get("_score"),
        "_source": hit.get("_source"),
    }


def total_summary(total):
    """hits.total is {'value': n, 'relation': 'eq'} on ES7+/OpenSearch, a bare int on older."""
    if isinstance(total, dict):
        return {"value": total.get("value"), "relation": total.get("relation")}
    return {"value": total, "relation": "eq"}


# --- tool handlers ---------------------------------------------------------

def search():
    index = index_path(params.get("index"))
    body = {"size": clamp(params.get("size", 10), 10, 100)}
    if params.get("query"):
        body["query"] = params["query"]
    if params.get("sort"):
        body["sort"] = params["sort"]
    if params.get("aggs"):
        body["aggs"] = params["aggs"]
    result = request("POST", f"/{index}/_search", data=body) or {}
    hits_block = result.get("hits") or {}
    hits = [hit_summary(h) for h in (hits_block.get("hits") or [])]
    out = {
        "total": total_summary(hits_block.get("total")),
        "count": len(hits),
        "hits": hits,
    }
    if result.get("aggregations"):
        out["aggregations"] = result["aggregations"]
    print(json.dumps(out))


def esql_query():
    query = params.get("query")
    if not query:
        raise ValueError("query is required")
    try:
        result = request("POST", "/_query", data={"query": query}) or {}
    except RuntimeError as e:
        # Only translate the missing-endpoint response (404, or OpenSearch's 400
        # "no handler found for uri [/_query]"). Real ES|QL parsing/verification
        # errors also come back as 400 and must reach the user unchanged.
        code = getattr(getattr(e, "__cause__", None), "code", None)
        if code == 404 or (code == 400 and "no handler found" in str(e)):
            raise RuntimeError(
                "ES|QL is not supported by this cluster (requires Elasticsearch 8.11+)"
            ) from e
        raise
    columns = [c.get("name") for c in (result.get("columns") or [])]
    values = result.get("values") or []
    print(json.dumps({"columns": columns, "count": len(values), "values": values}))


def count():
    index = index_path(params.get("index"))
    body = {"query": params["query"]} if params.get("query") else None
    result = request("POST", f"/{index}/_count", data=body) or {}
    print(json.dumps({"count": result.get("count")}))


def get_document():
    index = index_path(params.get("index"))
    doc_id = params.get("id")
    if not doc_id:
        raise ValueError("id is required")
    result = request("GET", f"/{index}/_doc/{urllib.parse.quote(str(doc_id), safe='')}") or {}
    print(json.dumps({
        "_index": result.get("_index"),
        "_id": result.get("_id"),
        "found": result.get("found"),
        "_source": result.get("_source"),
    }))


def list_indices():
    result = request("GET", "/_cat/indices", query={"format": "json", "s": "index"}) or []
    indices = [{
        "index": idx.get("index"),
        "health": idx.get("health"),
        "docsCount": idx.get("docs.count"),
        "storeSize": idx.get("store.size"),
    } for idx in result]
    print(json.dumps({"count": len(indices), "indices": indices}))


def get_mapping():
    index = index_path(params.get("index"))
    result = request("GET", f"/{index}/_mapping") or {}
    mappings = {
        name: ((entry.get("mappings") or {}).get("properties") or {})
        for name, entry in result.items()
    }
    print(json.dumps({"count": len(mappings), "mappings": mappings}))


def cluster_health():
    result = request("GET", "/_cluster/health") or {}
    print(json.dumps({
        "clusterName": result.get("cluster_name"),
        "status": result.get("status"),
        "numberOfNodes": result.get("number_of_nodes"),
        "numberOfDataNodes": result.get("number_of_data_nodes"),
        "activePrimaryShards": result.get("active_primary_shards"),
        "activeShards": result.get("active_shards"),
        "relocatingShards": result.get("relocating_shards"),
        "initializingShards": result.get("initializing_shards"),
        "unassignedShards": result.get("unassigned_shards"),
        "activeShardsPercent": result.get("active_shards_percent_as_number"),
    }))


def index_document():
    index = index_path(params.get("index"))
    document = params.get("document")
    if not isinstance(document, dict):
        raise ValueError("document is required and must be a JSON object")
    doc_id = params.get("id")
    if doc_id:
        result = request(
            "PUT", f"/{index}/_doc/{urllib.parse.quote(str(doc_id), safe='')}", data=document
        ) or {}
    else:
        result = request("POST", f"/{index}/_doc", data=document) or {}
    print(json.dumps({
        "_index": result.get("_index"),
        "_id": result.get("_id"),
        "result": result.get("result"),
        "_version": result.get("_version"),
    }))


HANDLERS = {
    "es.search": search,
    "es.esql_query": esql_query,
    "es.count": count,
    "es.get_document": get_document,
    "es.list_indices": list_indices,
    "es.get_mapping": get_mapping,
    "es.cluster_health": cluster_health,
    "es.index_document": index_document,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and (api_key or (username and password))):
        print(json.dumps({"error": "Missing Elasticsearch credentials: connect the Elasticsearch integration first (baseUrl plus either apiKey, or username and password)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
