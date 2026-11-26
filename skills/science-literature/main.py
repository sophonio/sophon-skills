"""Science literature: keyless, read-only lookups in PubMed (E-utilities), Europe PMC and Crossref.

Standard library only. `params` is injected as a global by the Sophon runtime and carries the tool
name and its arguments. Requests go only to three fixed HTTPS hosts; callers never pass a URL, and a
redirect to any other host or scheme is refused. One attempt per request, no retries: a 429 is
returned to the caller with the server's Retry-After value.

Every result carries retrieval provenance (provider, request URL, UTC time and the SHA-256 of the raw
response) in the shape of an evidence bundle source. A record that resolves is not evidence that it
supports a claim, and "not_flagged" means only that the provider's data shows no retraction notice.
"""

import datetime
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree

tool_name = params.get("tool", "")

USER_AGENT = "sophon-science-literature/1.0 (+https://sophon.buildersoft.io)"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EUROPEPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
CROSSREF = "https://api.crossref.org/works/"
ALLOWED_HOSTS = ("eutils.ncbi.nlm.nih.gov", "www.ebi.ac.uk", "api.crossref.org")
EUTILS_TOOL = "sophon-science-literature"
TIMEOUT_SECONDS = 10
MAX_RESPONSE_BYTES = 5242880
MAX_RECORDS = 100
MAX_QUERY_CHARS = 1000

PMID_RE = re.compile(r"^[1-9][0-9]{0,8}$")
DATE_RE = re.compile(r"^\d{4}(?:/\d{2}(?:/\d{2})?)?$")
CURSOR_RE = re.compile(r"^[A-Za-z0-9+/=*_-]{1,200}$")
DOI_RE = re.compile(r"^10\.\d{4,9}/[^\s?#]+$")
YEAR_RE = re.compile(r"(\d{4})")
DIGITS_RE = re.compile(r"^[0-9]+$")
RETRY_AFTER_RE = re.compile(r"^(?:[0-9]{1,6}|[A-Z][a-z]{2}, [0-9]{2} [A-Z][a-z]{2} [0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2} GMT)$")
XML_ENCODING_RE = re.compile(r"""^\s*<\?xml[^>]*encoding\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


class ToolError(Exception):
    def __init__(self, code, message, **extra):
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only to HTTPS on one of the fixed hosts."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlsplit(newurl)
        if target.scheme != "https" or (target.hostname or "").lower() not in ALLOWED_HOSTS:
            raise ToolError("UNSAFE_REDIRECT", f"refused a redirect to {target.scheme}://{target.hostname}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(SafeRedirectHandler)


# --- HTTP ------------------------------------------------------------------------

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(url, accept):
    host = urllib.parse.urlsplit(url).hostname
    if not url.startswith("https://") or host not in ALLOWED_HOSTS:
        raise ToolError("INVALID_ARGUMENT", "internal error: request outside the fixed hosts")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept}, method="GET")
    try:
        with OPENER.open(req, timeout=TIMEOUT_SECONDS) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            retry = e.headers.get("Retry-After") if e.headers is not None else None
            extra = {"retry_after": retry.strip()} if isinstance(retry, str) and RETRY_AFTER_RE.match(retry.strip()) else {}
            raise ToolError("RATE_LIMITED", "the provider asked to slow down (HTTP 429)", **extra)
        if e.code == 404:
            raise ToolError("NOT_FOUND", "the provider has no such record (HTTP 404)")
        raise ToolError("HTTP_ERROR", f"the provider returned HTTP {e.code}", status=e.code)
    except urllib.error.URLError as e:
        raise ToolError("NETWORK_ERROR", f"the request failed: {e.reason}")
    except TimeoutError:
        raise ToolError("TIMEOUT", f"no answer within {TIMEOUT_SECONDS} seconds")
    if len(body) > MAX_RESPONSE_BYTES:
        raise ToolError("RESPONSE_TOO_LARGE", f"the response exceeds {MAX_RESPONSE_BYTES} bytes")
    return body, {"request_url": url, "retrieved_at": utc_now(), "response_sha256": hashlib.sha256(body).hexdigest()}


def fetch_json(url):
    body, step = fetch(url, "application/json")
    try:
        return json.loads(body.decode("utf-8")), step
    except (UnicodeDecodeError, ValueError):
        raise ToolError("BAD_RESPONSE", "the provider did not return JSON")


def retrieval(provider, steps):
    last = steps[-1]
    return {"provider": provider, "request_url": last["request_url"], "retrieved_at": last["retrieved_at"],
            "response_sha256": last["response_sha256"], "steps": steps}


def shape(value, kind, what):
    """Provider data of the expected JSON type, or BAD_RESPONSE."""
    if not isinstance(value, kind):
        raise ToolError("BAD_RESPONSE", f"the provider returned an unexpected {what}")
    return value


# --- Arguments -------------------------------------------------------------------

def query_arg():
    q = params.get("query")
    if not isinstance(q, str) or not q.strip():
        raise ToolError("INVALID_ARGUMENT", "query is required")
    if len(q) > MAX_QUERY_CHARS:
        raise ToolError("INVALID_ARGUMENT", f"query exceeds {MAX_QUERY_CHARS} characters")
    return q.strip()


def limit_arg():
    limit = params.get("limit", 20)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RECORDS:
        raise ToolError("INVALID_ARGUMENT", f"limit must be an integer from 1 to {MAX_RECORDS}")
    return limit


# --- Shaping helpers -------------------------------------------------------------

def classify(types, preprint=False):
    """Publication kind and retraction status from a provider's publication-type list (None = unknown)."""
    if types is None:
        return ("preprint" if preprint else "unknown"), "unknown"
    lowered = [str(t).strip().lower() for t in types]
    retracted = "retracted publication" in lowered
    if preprint or "preprint" in lowered:
        kind = "preprint"
    elif lowered:
        kind = "journal_article"
    else:
        kind = "unknown"
    return kind, ("retracted" if retracted else "not_flagged")


def year_of(text):
    m = YEAR_RE.search(str(text or ""))
    return int(m.group(1)) if m else None


def record(provider, pmid=None, pmcid=None, doi=None, title=None, journal=None, year=None, types=None,
           kind="unknown", retraction="unknown", license_=None, url=None):
    return {"provider": provider, "pmid": pmid, "pmcid": pmcid, "doi": doi, "title": title, "journal": journal,
            "year": year, "publication_types": list(types or []), "publication_kind": kind,
            "retraction_status": retraction, "license": license_ or "unknown", "url": url}


# --- PubMed ----------------------------------------------------------------------

def eutils_url(name, pairs):
    return f"{EUTILS}/{name}.fcgi?" + urllib.parse.urlencode(pairs + [("tool", EUTILS_TOOL)])


def pubmed_search():
    query, limit = query_arg(), limit_arg()
    min_date, max_date = params.get("min_date"), params.get("max_date")
    pairs = [("db", "pubmed"), ("term", query), ("retmax", str(limit)), ("retmode", "json")]
    if min_date is not None or max_date is not None:
        if not (isinstance(min_date, str) and isinstance(max_date, str)
                and DATE_RE.match(min_date) and DATE_RE.match(max_date)):
            raise ToolError("INVALID_ARGUMENT", "min_date and max_date go together, as YYYY, YYYY/MM or YYYY/MM/DD")
        pairs += [("datetype", "pdat"), ("mindate", min_date), ("maxdate", max_date)]
    found, step1 = fetch_json(eutils_url("esearch", pairs))
    result = shape(shape(found, dict, "esearch response").get("esearchresult"), dict, "esearchresult")
    idlist = shape(result.get("idlist", []), list, "esearch idlist")
    ids = [i for i in idlist if isinstance(i, str) and PMID_RE.match(i)][:limit]
    count = result.get("count")
    total = int(count) if isinstance(count, str) and DIGITS_RE.match(count) else None
    if not ids:
        return {"records": [], "total": total, "retrieval": retrieval("pubmed", [step1])}
    summary, step2 = fetch_json(eutils_url("esummary", [("db", "pubmed"), ("id", ",".join(ids)), ("retmode", "json")]))
    docs = shape(shape(summary, dict, "esummary response").get("result"), dict, "esummary result")
    uids = shape(docs.get("uids", ids), list, "esummary uids")
    records = []
    for uid in uids:
        if len(records) >= limit:
            break
        doc = docs.get(uid) if isinstance(uid, str) else None
        if not isinstance(doc, dict):
            continue
        idmap = {a.get("idtype"): a.get("value") for a in doc.get("articleids") or [] if isinstance(a, dict)}
        types = doc.get("pubtype") if isinstance(doc.get("pubtype"), list) else None
        kind, retraction = classify(types)
        records.append(record("pubmed", pmid=str(uid), pmcid=idmap.get("pmc") or idmap.get("pmcid"),
                              doi=idmap.get("doi"), title=doc.get("title"),
                              journal=doc.get("fulljournalname") or doc.get("source"),
                              year=year_of(doc.get("pubdate")), types=types, kind=kind, retraction=retraction,
                              url=f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"))
    return {"records": records, "total": total, "retrieval": retrieval("pubmed", [step1, step2])}


def element_text(node):
    return " ".join("".join(node.itertext()).split()) if node is not None else None


def pubmed_abstracts():
    pmids = params.get("pmids")
    if (not isinstance(pmids, list) or not pmids or len(pmids) > MAX_RECORDS
            or not all(isinstance(p, str) and PMID_RE.match(p) for p in pmids)):
        raise ToolError("INVALID_ARGUMENT", f"pmids must be 1 to {MAX_RECORDS} numeric PubMed ids as strings")
    url = eutils_url("efetch", [("db", "pubmed"), ("id", ",".join(pmids)), ("retmode", "xml"), ("rettype", "abstract")])
    body, step = fetch(url, "application/xml")
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        raise ToolError("BAD_RESPONSE", "the response is not UTF-8 XML")
    declared = XML_ENCODING_RE.match(text)
    if declared and declared.group(1).strip().lower() not in ("utf-8", "utf8"):
        raise ToolError("UNSAFE_XML", f"the response declares encoding {declared.group(1)!r}; only UTF-8 is accepted")
    if "<!ENTITY" in text.upper():
        raise ToolError("UNSAFE_XML", "the response declares XML entities; refused")
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as e:
        raise ToolError("BAD_RESPONSE", f"the response is not well-formed XML: {e}")
    records = []
    for article in root.iter("PubmedArticle"):
        citation = article.find("MedlineCitation")
        art = citation.find("Article") if citation is not None else None
        if art is None:
            continue
        pmid = element_text(citation.find("PMID"))
        sections = []
        for part in art.findall("Abstract/AbstractText"):
            text = element_text(part)
            label = part.get("Label")
            if text:
                sections.append(f"{label}: {text}" if label else text)
        ids = {a.get("IdType"): element_text(a) for a in article.findall("PubmedData/ArticleIdList/ArticleId")}
        type_nodes = art.findall("PublicationTypeList/PublicationType")
        types = [element_text(t) for t in type_nodes] if art.find("PublicationTypeList") is not None else None
        kind, retraction = classify(types)
        rec = record("pubmed", pmid=pmid, pmcid=ids.get("pmc"), doi=ids.get("doi"),
                     title=element_text(art.find("ArticleTitle")), journal=element_text(art.find("Journal/Title")),
                     year=year_of(element_text(art.find("Journal/JournalIssue/PubDate/Year"))
                                  or element_text(art.find("Journal/JournalIssue/PubDate/MedlineDate"))),
                     types=types, kind=kind, retraction=retraction,
                     url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None)
        rec["abstract"] = "\n".join(sections) or None
        records.append(rec)
    return {"records": records, "retrieval": retrieval("pubmed", [step])}


# --- Europe PMC ------------------------------------------------------------------

def europepmc_search():
    query, limit = query_arg(), limit_arg()
    cursor = params.get("cursor", "*")
    if not isinstance(cursor, str) or not CURSOR_RE.match(cursor):
        raise ToolError("INVALID_ARGUMENT", "cursor must be a value returned as next_cursor, or *")
    url = EUROPEPMC + "?" + urllib.parse.urlencode([("query", query), ("format", "json"), ("pageSize", str(limit)),
                                                     ("resultType", "core"), ("cursorMark", cursor)])
    data, step = fetch_json(url)
    data = shape(data, dict, "Europe PMC response")
    results = shape(shape(data.get("resultList"), dict, "Europe PMC resultList").get("result"), list,
                    "Europe PMC result list")
    records = []
    for item in results[:limit]:
        if not isinstance(item, dict):
            continue
        type_list = item.get("pubTypeList")
        types = type_list.get("pubType") if isinstance(type_list, dict) else None
        if isinstance(types, str):
            types = [types]
        kind, retraction = classify(types if isinstance(types, list) else None, preprint=item.get("source") == "PPR")
        info = item.get("journalInfo") if isinstance(item.get("journalInfo"), dict) else {}
        journal_obj = info.get("journal") if isinstance(info.get("journal"), dict) else {}
        book = item.get("bookOrReportDetails") if isinstance(item.get("bookOrReportDetails"), dict) else {}
        journal = journal_obj.get("title") or book.get("publisher")
        source, ident = item.get("source"), item.get("id")
        records.append(record("europepmc", pmid=item.get("pmid"), pmcid=item.get("pmcid"), doi=item.get("doi"),
                              title=item.get("title"), journal=journal, year=year_of(item.get("pubYear")),
                              types=types if isinstance(types, list) else None, kind=kind, retraction=retraction,
                              license_=item.get("license"),
                              url=f"https://europepmc.org/article/{source}/{ident}" if source and ident else None))
    next_cursor = data.get("nextCursorMark")
    if not isinstance(next_cursor, str) or next_cursor == cursor or not records:
        next_cursor = None
    total = data.get("hitCount") if isinstance(data.get("hitCount"), int) else None
    return {"records": records, "total": total, "next_cursor": next_cursor, "retrieval": retrieval("europepmc", [step])}


# --- Crossref --------------------------------------------------------------------

def crossref_work():
    doi = params.get("doi")
    if (not isinstance(doi, str) or len(doi) > 200 or not DOI_RE.match(doi)
            or any(seg in (".", "..") for seg in doi.split("/"))):
        raise ToolError("INVALID_ARGUMENT", "doi must look like 10.<registrant>/<suffix>, without ? or # or dot segments")
    data, step = fetch_json(CROSSREF + urllib.parse.quote(doi, safe=""))
    msg = data.get("message") if isinstance(data, dict) else None
    if not isinstance(msg, dict):
        raise ToolError("BAD_RESPONSE", "Crossref returned no message")
    work_type, subtype = msg.get("type"), msg.get("subtype")
    if work_type == "posted-content" and subtype == "preprint":
        kind = "preprint"
    elif work_type == "journal-article":
        kind = "journal_article"
    else:
        kind = "unknown"
    updates = msg.get("updated-by")
    if not isinstance(updates, list):
        retraction = "unknown"
    elif any(isinstance(u, dict) and str(u.get("type", "")).lower() == "retraction" for u in updates):
        retraction = "retracted"
    else:
        retraction = "not_flagged"
    issued = msg.get("issued") if isinstance(msg.get("issued"), dict) else {}
    date_parts = issued.get("date-parts")
    first = date_parts[0] if isinstance(date_parts, list) and date_parts else None
    parts = first if isinstance(first, list) and first else [None]
    licenses = msg.get("license") if isinstance(msg.get("license"), list) else []
    found_doi = msg.get("DOI") or doi
    titles = msg.get("title") if isinstance(msg.get("title"), list) else []
    containers = msg.get("container-title") if isinstance(msg.get("container-title"), list) else []
    rec = record("crossref", doi=found_doi, title=titles[0] if titles else None,
                 journal=containers[0] if containers else None,
                 year=parts[0] if isinstance(parts[0], int) else None,
                 types=[work_type] if work_type else None, kind=kind, retraction=retraction,
                 license_=licenses[0].get("URL") if licenses and isinstance(licenses[0], dict) else None,
                 url=f"https://doi.org/{found_doi}")
    return {"records": [rec], "retrieval": retrieval("crossref", [step])}


HANDLERS = {
    "scilit.pubmed_search": pubmed_search,
    "scilit.pubmed_abstracts": pubmed_abstracts,
    "scilit.europepmc_search": europepmc_search,
    "scilit.crossref_work": crossref_work,
}


def main():
    handler = HANDLERS.get(tool_name)
    if handler is None:
        return {"error": f"Unknown tool: {tool_name}", "code": "UNKNOWN_TOOL"}
    return handler()


try:
    print(json.dumps(main()))
except ToolError as e:
    out = {"error": e.message, "code": e.code}
    out.update(e.extra)
    print(json.dumps(out))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}", "code": "INTERNAL_ERROR"}))
