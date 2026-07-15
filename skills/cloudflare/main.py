"""Cloudflare integration skill — talks to the Cloudflare API v4 with a scoped API token.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential fields (apiToken, zoneId, accountId).

Cloudflare wraps every response as {"success": bool, "result": ..., "errors": [...]}. On
success=false we surface the errors as {"error": errors}.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
api_token = params.get("apiToken", "")
API_BASE = "https://api.cloudflare.com/client/v4"

HEADERS = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json",
    "User-Agent": "sophon-cloudflare-skill",
    "Accept": "application/json",
}


def request(method, path, data=None, query=None):
    """Make an authenticated request to the Cloudflare API. Returns the parsed JSON envelope."""
    url = f"{API_BASE}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            return json.loads(detail)
        except (ValueError, TypeError):
            raise RuntimeError(f"Cloudflare API error {e.code}: {detail}") from e


def unwrap(envelope):
    """Return the `result` from a Cloudflare envelope, or raise CloudflareError on failure."""
    if not isinstance(envelope, dict):
        raise RuntimeError("Unexpected Cloudflare response")
    if not envelope.get("success", False):
        raise CloudflareError(envelope.get("errors") or "Cloudflare request failed")
    return envelope.get("result")


class CloudflareError(Exception):
    """Raised when the Cloudflare envelope reports success:false; carries the errors payload."""

    def __init__(self, errors):
        self.errors = errors
        super().__init__(str(errors))


def resolve_zone():
    zone = params.get("zoneId") or ""
    if not zone:
        raise ValueError("zoneId required (pass it or configure it on the connection)")
    return zone


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def dns_summary(record):
    return {
        "id": record.get("id"),
        "type": record.get("type"),
        "name": record.get("name"),
        "content": record.get("content"),
        "ttl": record.get("ttl"),
        "proxied": record.get("proxied"),
        "proxiable": record.get("proxiable"),
    }


def zone_summary(zone):
    return {
        "id": zone.get("id"),
        "name": zone.get("name"),
        "status": zone.get("status"),
        "paused": zone.get("paused"),
        "type": zone.get("type"),
        "nameServers": zone.get("name_servers"),
    }


# --- Tool handlers ---------------------------------------------------------

def list_zones():
    envelope = request("GET", "/zones", query={
        "per_page": clamp(params.get("limit", 50), 50, 50),
    })
    zones = [zone_summary(z) for z in (unwrap(envelope) or [])]
    print(json.dumps({"count": len(zones), "zones": zones}))


def list_dns_records():
    zone = resolve_zone()
    envelope = request("GET", f"/zones/{zone}/dns_records", query={
        "type": params.get("type"),
        "name": params.get("name"),
        "per_page": clamp(params.get("limit", 100), 100, 100),
    })
    records = [dns_summary(r) for r in (unwrap(envelope) or [])]
    print(json.dumps({"count": len(records), "records": records}))


def create_dns_record():
    zone = resolve_zone()
    payload = {
        "type": params.get("type", ""),
        "name": params.get("name", ""),
        "content": params.get("content", ""),
    }
    if params.get("ttl") is not None:
        payload["ttl"] = int(params["ttl"])
    if params.get("proxied") is not None:
        payload["proxied"] = bool(params["proxied"])
    record = unwrap(request("POST", f"/zones/{zone}/dns_records", data=payload))
    print(json.dumps(dns_summary(record or {})))


def update_dns_record():
    zone = resolve_zone()
    record_id = params.get("recordId")
    if not record_id:
        raise ValueError("recordId required")
    payload = {}
    for key in ("type", "name", "content"):
        if params.get(key) is not None:
            payload[key] = params[key]
    if params.get("ttl") is not None:
        payload["ttl"] = int(params["ttl"])
    if params.get("proxied") is not None:
        payload["proxied"] = bool(params["proxied"])
    record = unwrap(request("PATCH", f"/zones/{zone}/dns_records/{record_id}", data=payload))
    print(json.dumps(dns_summary(record or {})))


def delete_dns_record():
    zone = resolve_zone()
    record_id = params.get("recordId")
    if not record_id:
        raise ValueError("recordId required")
    result = unwrap(request("DELETE", f"/zones/{zone}/dns_records/{record_id}"))
    print(json.dumps({"deleted": True, "id": (result or {}).get("id", record_id)}))


def purge_cache():
    zone = resolve_zone()
    files = params.get("files")
    if params.get("everything"):
        payload = {"purge_everything": True}
    elif files:
        payload = {"files": files}
    else:
        raise ValueError("Provide everything:true or a non-empty files list")
    result = unwrap(request("POST", f"/zones/{zone}/purge_cache", data=payload))
    print(json.dumps({"purged": True, "id": (result or {}).get("id", zone)}))


HANDLERS = {
    "cloudflare.list_zones": list_zones,
    "cloudflare.list_dns_records": list_dns_records,
    "cloudflare.create_dns_record": create_dns_record,
    "cloudflare.update_dns_record": update_dns_record,
    "cloudflare.delete_dns_record": delete_dns_record,
    "cloudflare.purge_cache": purge_cache,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not api_token:
        print(json.dumps({"error": "Missing Cloudflare credential: connect the Cloudflare integration first."}))
    else:
        handler()
except CloudflareError as e:
    print(json.dumps({"error": e.errors}))
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
