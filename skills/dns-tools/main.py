"""DNS + WHOIS diagnostics skill — DNS-over-HTTPS (Google) and RDAP over urllib.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies and no authentication. `params` is injected as a global by the Sophon runtime and
carries the tool name plus the tool's call arguments.

Network hosts: dns.google (DoH JSON API) and rdap.org (RDAP redirector).
"""

import json
import ipaddress
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")

USER_AGENT = "sophon-dns-tools-skill/1.0 (+https://buildersoft.io)"
DOH_URL = "https://dns.google/resolve"
RDAP_URL = "https://rdap.org/domain/"

# DNS RCODEs of interest.
RCODE = {0: "NOERROR", 1: "FORMERR", 2: "SERVFAIL", 3: "NXDOMAIN", 5: "REFUSED"}
# Numeric record type -> name, for decoding Answer entries.
TYPE_NAMES = {
    1: "A", 2: "NS", 5: "CNAME", 6: "SOA", 12: "PTR",
    15: "MX", 16: "TXT", 28: "AAAA", 257: "CAA",
}


def get_json(url):
    """GET a URL and return parsed JSON. Raises RuntimeError on HTTP/URL errors."""
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP error {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Request failed: {e.reason}") from e


def doh(name, rtype):
    """Query Google's DNS-over-HTTPS JSON API. Returns the parsed response dict."""
    qs = urllib.parse.urlencode({"name": name, "type": rtype})
    return get_json(f"{DOH_URL}?{qs}")


def parse_answers(resp):
    """Extract Answer records as a list of {data, ttl, type} dicts."""
    answers = []
    for ans in resp.get("Answer") or []:
        answers.append({
            "data": (ans.get("data") or "").strip('"') if ans.get("type") == 16
            else ans.get("data"),
            "ttl": ans.get("TTL"),
            "type": TYPE_NAMES.get(ans.get("type"), ans.get("type")),
        })
    return answers


def status_name(resp):
    code = resp.get("Status")
    return RCODE.get(code, str(code))


def txt_records(name):
    """Return the list of TXT record strings for a name (empty if none/NXDOMAIN)."""
    resp = doh(name, "TXT")
    records = []
    for ans in resp.get("Answer") or []:
        if ans.get("type") == 16:
            records.append((ans.get("data") or "").strip('"'))
    return records


# --- Tool handlers ---------------------------------------------------------

def lookup():
    name = params.get("name")
    if not name or not str(name).strip():
        raise ValueError("name is required")
    rtype = (params.get("type") or "A").strip().upper()
    resp = doh(str(name).strip(), rtype)
    answers = [{"data": a["data"], "ttl": a["ttl"]} for a in parse_answers(resp)]
    print(json.dumps({
        "name": str(name).strip(),
        "type": rtype,
        "answers": answers,
        "status": status_name(resp),
    }))


def reverse():
    ip = params.get("ip")
    if not ip or not str(ip).strip():
        raise ValueError("ip is required")
    try:
        addr = ipaddress.ip_address(str(ip).strip())
    except ValueError:
        raise ValueError(f"invalid IP address: {ip}")
    # reverse_pointer gives the .in-addr.arpa / .ip6.arpa name.
    arpa = addr.reverse_pointer
    resp = doh(arpa, "PTR")
    hostnames = [ (a.get("data") or "").rstrip(".")
                  for a in (resp.get("Answer") or []) if a.get("type") == 12 ]
    print(json.dumps({
        "ip": str(addr),
        "arpa": arpa,
        "hostnames": hostnames,
        "status": status_name(resp),
    }))


def mail_records():
    domain = params.get("domain")
    if not domain or not str(domain).strip():
        raise ValueError("domain is required")
    domain = str(domain).strip().rstrip(".")

    # MX, sorted by preference (the "data" is "<pref> <host>").
    mx_resp = doh(domain, "MX")
    mx = []
    for ans in mx_resp.get("Answer") or []:
        if ans.get("type") != 15:
            continue
        raw = (ans.get("data") or "").strip()
        parts = raw.split()
        if len(parts) == 2 and parts[0].isdigit():
            mx.append({"preference": int(parts[0]),
                       "exchange": parts[1].rstrip("."),
                       "ttl": ans.get("TTL")})
        else:
            mx.append({"preference": None, "exchange": raw.rstrip("."),
                       "ttl": ans.get("TTL")})
    mx.sort(key=lambda r: (r["preference"] is None, r["preference"] if r["preference"] is not None else 0))

    # SPF: a TXT record at the apex starting with v=spf1.
    spf = None
    for rec in txt_records(domain):
        if rec.lower().startswith("v=spf1"):
            spf = rec
            break

    # DMARC: TXT at _dmarc.<domain> starting with v=DMARC1.
    dmarc = None
    for rec in txt_records(f"_dmarc.{domain}"):
        if rec.lower().startswith("v=dmarc1"):
            dmarc = rec
            break

    print(json.dumps({
        "domain": domain,
        "mx": mx,
        "spf": spf,
        "dmarc": dmarc,
    }))


def whois():
    domain = params.get("domain")
    if not domain or not str(domain).strip():
        raise ValueError("domain is required")
    domain = str(domain).strip().rstrip(".").lower()
    url = RDAP_URL + urllib.parse.quote(domain)
    try:
        data = get_json(url)
    except RuntimeError as e:
        if "404" in str(e):
            print(json.dumps({"error": f"domain not found: {domain}"}))
            return
        raise

    # Registrar: entity whose roles include "registrar"; prefer its vcard fn.
    registrar = None
    for ent in data.get("entities") or []:
        roles = ent.get("roles") or []
        if "registrar" in roles:
            vcard = (ent.get("vcardArray") or [None, []])
            props = vcard[1] if len(vcard) > 1 else []
            for prop in props:
                if isinstance(prop, list) and len(prop) >= 4 and prop[0] == "fn":
                    registrar = prop[3]
                    break
            if not registrar:
                registrar = ent.get("handle")
            if registrar:
                break

    # Nameservers.
    nameservers = []
    for ns in data.get("nameservers") or []:
        name = ns.get("ldhName") or ns.get("unicodeName")
        if name:
            nameservers.append(name.lower().rstrip("."))

    # Events: registration / expiration / last changed.
    events = {}
    for ev in data.get("events") or []:
        action = ev.get("eventAction")
        date = ev.get("eventDate")
        if action and date:
            events[action] = date

    print(json.dumps({
        "domain": (data.get("ldhName") or domain).lower(),
        "registrar": registrar,
        "status": data.get("status") or [],
        "nameservers": nameservers,
        "events": events,
    }))


HANDLERS = {
    "dns.lookup": lookup,
    "dns.reverse": reverse,
    "dns.mail_records": mail_records,
    "dns.whois": whois,
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
