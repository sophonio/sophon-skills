"""Wikipedia skill — search and read Wikipedia articles via the public MediaWiki API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies and no authentication. `params` is injected as a global by the Sophon runtime and
carries the tool name plus the tool's call arguments.

Wikimedia's API etiquette policy requires a descriptive User-Agent on every request.
Language is chosen per call: the request host is "{language}.wikipedia.org" (default "en").
"""

import json
import re
import html
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")

USER_AGENT = "sophon-wikipedia-skill/1.0 (+https://buildersoft.io)"
LANG_RE = re.compile(r"^[a-z-]{2,10}$")
TAG_RE = re.compile(r"<[^>]+>")
MAX_ARTICLE_CHARS = 40000


def resolve_language():
    """Validate and return the requested language code, defaulting to 'en'."""
    lang = (params.get("language") or "en").strip().lower()
    if not LANG_RE.match(lang):
        raise ValueError(f"invalid language code: {lang!r} (expected [a-z-]{{2,10}}, e.g. en, de, fr)")
    return lang


def get_json(url):
    """GET a URL and return parsed JSON. Raises RuntimeError on HTTP errors."""
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Wikipedia API error {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Wikipedia request failed: {e.reason}") from e


def strip_html(text):
    """Remove HTML tags and unescape entities from a snippet string."""
    if not text:
        return ""
    return html.unescape(TAG_RE.sub("", text)).strip()


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def article_url(lang, title):
    return f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"


# --- Tool handlers ---------------------------------------------------------

def search():
    query = params.get("query")
    if not query or not str(query).strip():
        raise ValueError("query is required")
    lang = resolve_language()
    limit = clamp(params.get("limit", 10), 10, 50)
    qs = urllib.parse.urlencode({
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "format": "json",
    })
    url = f"https://{lang}.wikipedia.org/w/api.php?{qs}"
    data = get_json(url)
    hits = (data.get("query") or {}).get("search") or []
    results = [{
        "title": h.get("title"),
        "snippet": strip_html(h.get("snippet")),
        "pageid": h.get("pageid"),
    } for h in hits]
    print(json.dumps({"language": lang, "count": len(results), "results": results}))


def get_summary():
    title = params.get("title")
    if not title or not str(title).strip():
        raise ValueError("title is required")
    lang = resolve_language()
    encoded = urllib.parse.quote(str(title).strip().replace(" ", "_"), safe="")
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    try:
        data = get_json(url)
    except RuntimeError as e:
        if "404" in str(e):
            print(json.dumps({"error": f"page not found: {title}"}))
            return
        raise
    if data.get("type", "").endswith("not_found") or data.get("title") == "Not found.":
        print(json.dumps({"error": f"page not found: {title}"}))
        return
    page_url = ((data.get("content_urls") or {}).get("desktop") or {}).get("page") \
        or article_url(lang, data.get("title") or str(title))
    print(json.dumps({
        "title": data.get("title"),
        "description": data.get("description"),
        "extract": data.get("extract"),
        "url": page_url,
    }))


def get_article():
    title = params.get("title")
    if not title or not str(title).strip():
        raise ValueError("title is required")
    lang = resolve_language()
    qs = urllib.parse.urlencode({
        "action": "query",
        "prop": "extracts",
        "explaintext": 1,
        "redirects": 1,
        "titles": str(title).strip(),
        "format": "json",
    })
    url = f"https://{lang}.wikipedia.org/w/api.php?{qs}"
    data = get_json(url)
    pages = (data.get("query") or {}).get("pages") or {}
    if not pages:
        print(json.dumps({"error": f"page not found: {title}"}))
        return
    page = next(iter(pages.values()))
    if "missing" in page or page.get("pageid") is None:
        print(json.dumps({"error": f"page not found: {title}"}))
        return
    extract = page.get("extract") or ""
    truncated = False
    if len(extract) > MAX_ARTICLE_CHARS:
        extract = extract[:MAX_ARTICLE_CHARS]
        truncated = True
    resolved_title = page.get("title") or str(title)
    out = {
        "title": resolved_title,
        "extract": extract,
        "url": article_url(lang, resolved_title),
    }
    if truncated:
        out["truncated"] = True
        out["note"] = f"Extract truncated to {MAX_ARTICLE_CHARS} characters."
    print(json.dumps(out))


HANDLERS = {
    "wikipedia.search": search,
    "wikipedia.get_summary": get_summary,
    "wikipedia.get_article": get_article,
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
