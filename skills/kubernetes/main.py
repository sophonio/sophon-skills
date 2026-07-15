"""Kubernetes integration skill — talks to the Kubernetes REST API with a ServiceAccount token.

Pure standard library (urllib + ssl) so it runs unchanged in the alpine Python sandbox with no pip
dependencies and no kubectl binary. `params` is injected as a global by the Sophon runtime and
carries the tool name, the tool arguments, and the connection-card fields (apiServer, token, caCert,
insecureSkipVerify).

TLS: the API server usually presents a certificate signed by a private cluster CA. When a caCert PEM
is provided we trust it; when insecureSkipVerify is 'true' we disable verification (not recommended).
"""

import json
import ssl
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
api_server = (params.get("apiServer") or "").rstrip("/")
token = params.get("token") or ""
ca_cert = params.get("caCert") or ""
insecure = str(params.get("insecureSkipVerify") or "").strip().lower() == "true"

HEADERS = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "User-Agent": "sophon-kubernetes-skill",
}


def ssl_context():
    """Build an SSL context: trust the cluster CA if given, or skip verification if requested."""
    if ca_cert.strip():
        ctx = ssl.create_default_context(cadata=ca_cert)
    else:
        ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def request(method, path, data=None, query=None, content_type=None, raw=False):
    """Make an authenticated request to the Kubernetes API.

    Returns parsed JSON, or the raw text body when raw=True (used for pod logs).
    """
    url = f"{api_server}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    headers = dict(HEADERS)
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = content_type or "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ssl_context()) as resp:
            text = resp.read().decode()
            if raw:
                return text
            return json.loads(text) if text else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        message = detail
        try:
            parsed = json.loads(detail)
            if isinstance(parsed, dict) and parsed.get("message"):
                message = parsed["message"]
        except (ValueError, TypeError):
            pass
        raise RuntimeError(f"Kubernetes API error {e.code}: {message}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Kubernetes API at {api_server}: {e.reason}") from e


def seg(value):
    """URL-encode a single path segment (namespace / name / pod)."""
    return urllib.parse.quote(str(value), safe="")


# --- summaries -------------------------------------------------------------

def pod_summary(pod):
    meta = pod.get("metadata") or {}
    spec = pod.get("spec") or {}
    status = pod.get("status") or {}
    restarts = sum((cs.get("restartCount") or 0)
                   for cs in (status.get("containerStatuses") or []))
    return {
        "name": meta.get("name"),
        "namespace": meta.get("namespace"),
        "phase": status.get("phase"),
        "node": spec.get("nodeName"),
        "restarts": restarts,
    }


def deployment_summary(dep):
    meta = dep.get("metadata") or {}
    spec = dep.get("spec") or {}
    status = dep.get("status") or {}
    return {
        "name": meta.get("name"),
        "namespace": meta.get("namespace"),
        "replicas": spec.get("replicas"),
        "available": status.get("availableReplicas") or 0,
    }


def service_summary(svc):
    meta = svc.get("metadata") or {}
    spec = svc.get("spec") or {}
    return {
        "name": meta.get("name"),
        "namespace": meta.get("namespace"),
        "type": spec.get("type"),
        "clusterIP": spec.get("clusterIP"),
        "ports": [{
            "name": p.get("name"),
            "port": p.get("port"),
            "targetPort": p.get("targetPort"),
            "protocol": p.get("protocol"),
        } for p in (spec.get("ports") or [])],
    }


def node_summary(node):
    meta = node.get("metadata") or {}
    status = node.get("status") or {}
    node_info = status.get("nodeInfo") or {}
    ready = "Unknown"
    for cond in (status.get("conditions") or []):
        if cond.get("type") == "Ready":
            ready = "Ready" if cond.get("status") == "True" else "NotReady"
            break
    return {
        "name": meta.get("name"),
        "status": ready,
        "version": node_info.get("kubeletVersion"),
    }


# --- tool handlers ---------------------------------------------------------

def list_namespaces():
    result = request("GET", "/api/v1/namespaces")
    names = [{
        "name": (ns.get("metadata") or {}).get("name"),
        "status": (ns.get("status") or {}).get("phase"),
    } for ns in (result or {}).get("items", [])]
    print(json.dumps({"count": len(names), "namespaces": names}))


def list_pods():
    ns = params.get("namespace")
    path = f"/api/v1/namespaces/{seg(ns)}/pods" if ns else "/api/v1/pods"
    result = request("GET", path)
    pods = [pod_summary(p) for p in (result or {}).get("items", [])]
    print(json.dumps({"count": len(pods), "pods": pods}))


def get_pod_logs():
    ns = params.get("namespace")
    pod = params.get("pod")
    if not ns or not pod:
        raise ValueError("namespace and pod are required")
    text = request("GET", f"/api/v1/namespaces/{seg(ns)}/pods/{seg(pod)}/log", query={
        "container": params.get("container"),
        "tailLines": params.get("tailLines"),
    }, raw=True)
    print(json.dumps({"logs": text}))


def list_deployments():
    ns = params.get("namespace")
    path = (f"/apis/apps/v1/namespaces/{seg(ns)}/deployments"
            if ns else "/apis/apps/v1/deployments")
    result = request("GET", path)
    deps = [deployment_summary(d) for d in (result or {}).get("items", [])]
    print(json.dumps({"count": len(deps), "deployments": deps}))


def list_services():
    ns = params.get("namespace")
    path = f"/api/v1/namespaces/{seg(ns)}/services" if ns else "/api/v1/services"
    result = request("GET", path)
    svcs = [service_summary(s) for s in (result or {}).get("items", [])]
    print(json.dumps({"count": len(svcs), "services": svcs}))


def list_nodes():
    result = request("GET", "/api/v1/nodes")
    nodes = [node_summary(n) for n in (result or {}).get("items", [])]
    print(json.dumps({"count": len(nodes), "nodes": nodes}))


def scale_deployment():
    ns = params.get("namespace")
    name = params.get("name")
    if not ns or not name:
        raise ValueError("namespace and name are required")
    if params.get("replicas") is None:
        raise ValueError("replicas is required")
    try:
        replicas = int(params.get("replicas"))
    except (TypeError, ValueError):
        raise ValueError("replicas must be an integer")
    result = request(
        "PATCH",
        f"/apis/apps/v1/namespaces/{seg(ns)}/deployments/{seg(name)}/scale",
        data={"spec": {"replicas": replicas}},
        content_type="application/merge-patch+json",
    )
    spec = (result or {}).get("spec") or {}
    status = (result or {}).get("status") or {}
    print(json.dumps({
        "name": name,
        "namespace": ns,
        "replicas": spec.get("replicas"),
        "currentReplicas": status.get("replicas"),
    }))


HANDLERS = {
    "kubernetes.list_namespaces": list_namespaces,
    "kubernetes.list_pods": list_pods,
    "kubernetes.get_pod_logs": get_pod_logs,
    "kubernetes.list_deployments": list_deployments,
    "kubernetes.list_services": list_services,
    "kubernetes.list_nodes": list_nodes,
    "kubernetes.scale_deployment": scale_deployment,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not api_server or not token:
        print(json.dumps({"error": "apiServer and token are required (configure the Kubernetes connection)"}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
