"""Uptime / availability checks over the Python standard library.

Runs in the alpine Python sandbox with no pip dependencies and no credentials. `params` is injected
as a global by the Sophon runtime and carries the tool name and the tool's call arguments.

Everything here uses only the standard library: urllib for HTTP(S), socket for raw TCP reachability,
and ssl for TLS certificate inspection. Latency is measured with time.monotonic(); certificate
expiry is computed with datetime. All errors are returned as JSON — nothing is raised to the runtime.
"""

import json
import socket
import ssl
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

tool_name = params.get("tool", "")

# Format certificates use for notBefore/notAfter, e.g. "Jun  1 12:00:00 2026 GMT".
CERT_TIME_FORMAT = "%b %d %H:%M:%S %Y %Z"


def to_timeout(value, default=10.0):
    """Coerce a user-supplied timeout into a positive float, falling back to the default."""
    try:
        t = float(value)
    except (TypeError, ValueError):
        return default
    return t if t > 0 else default


def to_port(value):
    port = int(value)
    if port < 1 or port > 65535:
        raise ValueError("port must be between 1 and 65535")
    return port


def flatten_name(name_tuples):
    """Turn certificate subject/issuer ((('CN', 'x'),), ...) into a flat dict."""
    out = {}
    for rdn in (name_tuples or ()):
        for key, value in rdn:
            out[key] = value
    return out


# --- Tool handlers ---------------------------------------------------------

def http_check():
    url = params.get("url")
    if not isinstance(url, str) or not url.strip():
        raise ValueError("missing 'url'")
    url = url.strip()
    scheme = url.split("://", 1)[0].lower() if "://" in url else ""
    if scheme not in ("http", "https"):
        raise ValueError("url must start with http:// or https://")

    method = (params.get("method") or "GET").upper()
    if method not in ("GET", "HEAD"):
        raise ValueError("method must be GET or HEAD")
    timeout = to_timeout(params.get("timeoutSeconds"))
    expect_status = params.get("expectStatus")
    if expect_status is not None:
        try:
            expect_status = int(expect_status)
        except (TypeError, ValueError):
            raise ValueError("expectStatus must be an integer")

    headers = {"User-Agent": "sophon-uptime-check"}
    extra = params.get("header")
    if isinstance(extra, dict):
        for k, v in extra.items():
            headers[str(k)] = str(v)

    req = urllib.request.Request(url, headers=headers, method=method)
    start = time.monotonic()
    result = {"url": url, "status": None, "ok": False, "latencyMs": None, "finalUrl": None}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result["latencyMs"] = round((time.monotonic() - start) * 1000, 2)
            result["status"] = resp.status
            result["finalUrl"] = resp.geturl()
    except urllib.error.HTTPError as e:
        # An HTTP error is still a live response — capture its status.
        result["latencyMs"] = round((time.monotonic() - start) * 1000, 2)
        result["status"] = e.code
        result["finalUrl"] = getattr(e, "url", url)
    except (urllib.error.URLError, socket.timeout, ssl.SSLError, OSError) as e:
        result["latencyMs"] = round((time.monotonic() - start) * 1000, 2)
        reason = getattr(e, "reason", None)
        result["error"] = str(reason) if reason is not None else str(e)
        print(json.dumps(result))
        return

    if expect_status is not None:
        result["ok"] = result["status"] == expect_status
    else:
        result["ok"] = 200 <= (result["status"] or 0) < 300
    print(json.dumps(result))


def tcp_check():
    host = params.get("host")
    if not isinstance(host, str) or not host.strip():
        raise ValueError("missing 'host'")
    host = host.strip()
    port = to_port(params.get("port"))
    timeout = to_timeout(params.get("timeoutSeconds"))

    result = {"host": host, "port": port, "open": False, "latencyMs": None}
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            result["latencyMs"] = round((time.monotonic() - start) * 1000, 2)
            result["open"] = True
    except (socket.timeout, OSError) as e:
        result["latencyMs"] = round((time.monotonic() - start) * 1000, 2)
        result["error"] = str(e)
    print(json.dumps(result))


def tls_cert_check():
    host = params.get("host")
    if not isinstance(host, str) or not host.strip():
        raise ValueError("missing 'host'")
    host = host.strip()
    port = to_port(params.get("port")) if params.get("port") is not None else 443
    timeout = to_timeout(params.get("timeoutSeconds"))

    result = {"host": host, "port": port}
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
    except (socket.timeout, ssl.SSLError, OSError) as e:
        result["error"] = str(e)
        print(json.dumps(result))
        return

    if not cert:
        result["error"] = "no certificate returned by peer"
        print(json.dumps(result))
        return

    not_before = cert.get("notBefore")
    not_after = cert.get("notAfter")
    result["subject"] = flatten_name(cert.get("subject"))
    result["issuer"] = flatten_name(cert.get("issuer"))
    result["notBefore"] = not_before
    result["notAfter"] = not_after
    result["daysUntilExpiry"] = None
    if not_after:
        try:
            expiry = datetime.strptime(not_after, CERT_TIME_FORMAT).replace(tzinfo=timezone.utc)
            delta = expiry - datetime.now(timezone.utc)
            result["daysUntilExpiry"] = delta.days
        except (ValueError, TypeError) as e:
            result["error"] = f"could not parse notAfter: {e}"
    print(json.dumps(result))


HANDLERS = {
    "uptime.http": http_check,
    "uptime.tcp": tcp_check,
    "uptime.tls_cert": tls_cert_check,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    else:
        handler()
except ValueError as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
