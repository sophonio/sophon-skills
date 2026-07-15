"""Stripe read-only reporting skill — talks to the Stripe REST API with a restricted key.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential field (apiKey). Every operation is a
read-only GET; the intended credential is a restricted read key (rk_...).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
api_key = params.get("apiKey", "")
API_BASE = "https://api.stripe.com/v1"

HEADERS = {
    "Authorization": f"Bearer {api_key}",
    "User-Agent": "sophon-stripe-read-skill",
    "Accept": "application/json",
}

# Resources the generic get_object tool is allowed to read.
ALLOWED_RESOURCES = {
    "charges", "customers", "invoices", "subscriptions",
    "payment_intents", "payouts", "products", "prices",
}


def request(path, query=None):
    """Make an authenticated GET request to the Stripe API. Returns parsed JSON."""
    url = f"{API_BASE}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        message = detail
        try:
            parsed = json.loads(detail)
            message = (parsed.get("error") or {}).get("message") or detail
        except (ValueError, AttributeError):
            pass
        raise RuntimeError(f"Stripe API error {e.code}: {message}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


# --- Tool handlers ---------------------------------------------------------

def get_balance():
    result = request("/balance")
    print(json.dumps(result))


def list_charges():
    result = request("/charges", query={
        "limit": clamp(params.get("limit", 10), 10, 100),
        "customer": params.get("customer"),
    })
    print(json.dumps(result))


def list_customers():
    result = request("/customers", query={
        "limit": clamp(params.get("limit", 10), 10, 100),
        "email": params.get("email"),
    })
    print(json.dumps(result))


def list_invoices():
    result = request("/invoices", query={
        "limit": clamp(params.get("limit", 10), 10, 100),
        "customer": params.get("customer"),
        "status": params.get("status"),
    })
    print(json.dumps(result))


def list_subscriptions():
    result = request("/subscriptions", query={
        "limit": clamp(params.get("limit", 10), 10, 100),
        "customer": params.get("customer"),
        "status": params.get("status"),
    })
    print(json.dumps(result))


def get_object():
    resource = (params.get("resource") or "").strip()
    if resource not in ALLOWED_RESOURCES:
        allowed = ", ".join(sorted(ALLOWED_RESOURCES))
        raise ValueError(f"resource must be one of: {allowed}")
    obj_id = (params.get("id") or "").strip()
    if not obj_id:
        raise ValueError("id is required")
    result = request(f"/{resource}/{urllib.parse.quote(obj_id, safe='')}")
    print(json.dumps(result))


HANDLERS = {
    "stripe.get_balance": get_balance,
    "stripe.list_charges": list_charges,
    "stripe.list_customers": list_customers,
    "stripe.list_invoices": list_invoices,
    "stripe.list_subscriptions": list_subscriptions,
    "stripe.get_object": get_object,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not api_key:
        print(json.dumps({"error": "Missing Stripe credential: connect the Stripe integration with a restricted read key first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
