"""Currency conversion skill — ECB reference rates via the keyless Frankfurter API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies and no authentication. `params` is injected as a global by the Sophon runtime and
carries the tool name plus the tool's call arguments.

The Frankfurter API (https://api.frankfurter.app) is keyless and publishes European Central Bank
reference rates (~30 currencies, updated on TARGET business days around 16:00 CET). Unknown currency
codes cause the API to return an error message, which we surface as {"error": ...}.
"""

import json
import re
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")

API_BASE = "https://api.frankfurter.app"
USER_AGENT = "sophon-currency-convert-skill/1.0 (+https://buildersoft.io)"
CODE_RE = re.compile(r"^[A-Za-z]{3}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def get_json(path, query=None):
    """GET API_BASE + path (with optional query dict) and return parsed JSON.

    Raises RuntimeError on HTTP/transport errors. Frankfurter returns a JSON body with a
    "message" field for bad requests (e.g. unknown currency), which we convert to RuntimeError.
    """
    url = API_BASE + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            body = e.read().decode("utf-8")
            if body:
                parsed = json.loads(body)
                detail = parsed.get("message") or parsed.get("error") or body
        except Exception:  # noqa: BLE001
            detail = ""
        if detail:
            raise RuntimeError(str(detail)) from e
        raise RuntimeError(f"Frankfurter API error {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Frankfurter request failed: {e.reason}") from e


def require_code(value, field):
    """Validate and uppercase a 3-letter currency code."""
    if value is None or not str(value).strip():
        raise ValueError(f"{field} is required")
    code = str(value).strip().upper()
    if not CODE_RE.match(code):
        raise ValueError(f"{field} must be a 3-letter currency code, e.g. USD (got {value!r})")
    return code


def require_amount(value, field="amount", default=None):
    if value is None or (isinstance(value, str) and not value.strip()):
        if default is not None:
            return float(default)
        raise ValueError(f"{field} is required")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number (got {value!r})")


def normalize_symbols(value):
    """Accept a comma-separated string or a list, return a list of uppercased codes."""
    if value is None:
        return []
    if isinstance(value, str):
        parts = value.split(",")
    elif isinstance(value, (list, tuple)):
        parts = value
    else:
        raise ValueError("symbols must be a comma-separated string or an array of codes")
    codes = []
    for part in parts:
        code = str(part).strip().upper()
        if not code:
            continue
        if not CODE_RE.match(code):
            raise ValueError(f"invalid currency code in symbols: {part!r}")
        codes.append(code)
    return codes


# --- Tool handlers ---------------------------------------------------------

def convert():
    amount = require_amount(params.get("amount"))
    src = require_code(params.get("from"), "from")
    dst = require_code(params.get("to"), "to")
    if src == dst:
        print(json.dumps({
            "amount": amount, "from": src, "to": dst,
            "rate": 1.0, "result": amount, "date": None,
        }))
        return
    data = get_json("/latest", {"amount": amount, "from": src, "to": dst})
    rates = data.get("rates") or {}
    if dst not in rates:
        print(json.dumps({"error": f"no rate available for {src}->{dst}"}))
        return
    result = rates[dst]
    rate = result / amount if amount else None
    print(json.dumps({
        "amount": amount,
        "from": src,
        "to": dst,
        "rate": rate,
        "result": result,
        "date": data.get("date"),
    }))


def rates():
    base = require_code(params.get("base") or "EUR", "base")
    symbols = normalize_symbols(params.get("symbols"))
    query = {"from": base}
    if symbols:
        query["to"] = ",".join(symbols)
    data = get_json("/latest", query)
    print(json.dumps({
        "base": data.get("base", base),
        "date": data.get("date"),
        "rates": data.get("rates") or {},
    }))


def historical():
    date = params.get("date")
    if not date or not str(date).strip():
        raise ValueError("date is required")
    date = str(date).strip()
    if not DATE_RE.match(date):
        raise ValueError(f"date must be in YYYY-MM-DD format (got {date!r})")
    src = require_code(params.get("from"), "from")
    dst = require_code(params.get("to"), "to")
    amount = require_amount(params.get("amount"), "amount", default=1)
    if src == dst:
        print(json.dumps({
            "amount": amount, "from": src, "to": dst,
            "rate": 1.0, "result": amount, "date": date,
        }))
        return
    data = get_json(f"/{date}", {"amount": amount, "from": src, "to": dst})
    rates_map = data.get("rates") or {}
    if dst not in rates_map:
        print(json.dumps({"error": f"no rate available for {src}->{dst} on {date}"}))
        return
    result = rates_map[dst]
    rate = result / amount if amount else None
    print(json.dumps({
        "amount": amount,
        "from": src,
        "to": dst,
        "rate": rate,
        "result": result,
        "date": data.get("date", date),
    }))


def list_currencies():
    data = get_json("/currencies")
    print(json.dumps({"currencies": data}))


HANDLERS = {
    "currency.convert": convert,
    "currency.rates": rates,
    "currency.historical": historical,
    "currency.list_currencies": list_currencies,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
