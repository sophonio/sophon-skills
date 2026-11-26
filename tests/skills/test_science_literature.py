"""Offline mock-HTTP tests for the science-literature skill (PubMed E-utilities, Europe PMC, Crossref)."""
import contextlib
import hashlib
import io
import json
import re
import sys
import urllib.request

from mockhttp import REPO, run_tool, resp, err, check

ok = True
SKILL = "science-literature"
UA = "sophon-science-literature/1.0 (+https://sophon.buildersoft.io)"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOLQ = "tool=sophon-science-literature"


def call(tool, steps, **kw):
    params = {"tool": tool}
    params.update(kw)
    return run_tool(SKILL, params, steps)


def sha(body):
    raw = body if isinstance(body, bytes) else json.dumps(body).encode()
    return hashlib.sha256(raw).hexdigest()


ESEARCH = {"header": {"type": "esearch"},
           "esearchresult": {"count": "2", "retmax": "2", "idlist": ["42753714", "11111111"]}}
ESUMMARY = {"result": {
    "uids": ["42753714", "11111111"],
    "42753714": {"uid": "42753714", "title": "Status of Malaria Vaccine Introduction-Africa, 2019-2024.",
                 "fulljournalname": "The American journal of tropical medicine and hygiene",
                 "source": "Am J Trop Med Hyg", "pubdate": "2026 Nov", "pubtype": ["Journal Article"],
                 "articleids": [{"idtype": "pubmed", "value": "42753714"},
                                {"idtype": "doi", "value": "10.4269/ajtmh.26-0338"},
                                {"idtype": "pmc", "value": "PMC13590960"}]},
    "11111111": {"uid": "11111111", "title": "A withdrawn study", "fulljournalname": "J Example",
                 "pubdate": "2019 Mar 2", "pubtype": ["Journal Article", "Retracted Publication"],
                 "articleids": []},
}}

# ---------------------------------------------------------------- 1. pubmed_search
print("[pubmed_search — esearch then esummary]")
out, ex = call("scilit.pubmed_search", [resp(200, body=ESEARCH), resp(200, body=ESUMMARY)],
               query="malaria vaccine", limit=2)
ok &= check("two requests", len(ex) == 2, repr(ex))
ok &= check("esearch URL exact",
            ex[0].url == f"{EUTILS}/esearch.fcgi?db=pubmed&term=malaria+vaccine&retmax=2&retmode=json&{TOOLQ}",
            ex[0].url)
ok &= check("esummary URL exact",
            ex[1].url == f"{EUTILS}/esummary.fcgi?db=pubmed&id=42753714%2C11111111&retmode=json&{TOOLQ}", ex[1].url)
ok &= check("GET with the skill User-Agent", all(e.method == "GET" and e.headers.get("user-agent") == UA for e in ex),
            str(ex[0].headers))
recs = out["records"]
ok &= check("two records", len(recs) == 2, str(out)[:300])
r0 = recs[0]
ok &= check("record shaped", r0["provider"] == "pubmed" and r0["pmid"] == "42753714"
            and r0["doi"] == "10.4269/ajtmh.26-0338" and r0["pmcid"] == "PMC13590960"
            and r0["journal"] == "The American journal of tropical medicine and hygiene" and r0["year"] == 2026,
            str(r0))
ok &= check("journal article, not flagged", r0["publication_kind"] == "journal_article"
            and r0["retraction_status"] == "not_flagged", str(r0))
ok &= check("url points at PubMed", r0["url"] == "https://pubmed.ncbi.nlm.nih.gov/42753714/", r0["url"])
ok &= check("retracted publication flagged", recs[1]["retraction_status"] == "retracted"
            and recs[1]["year"] == 2019 and recs[1]["doi"] is None, str(recs[1]))
ok &= check("total count reported", out["total"] == 2, str(out)[:200])
ret = out["retrieval"]
ok &= check("retrieval provenance", ret["provider"] == "pubmed" and ret["request_url"] == ex[1].url
            and ret["response_sha256"] == sha(ESUMMARY)
            and re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$", ret["retrieved_at"]) is not None, str(ret))
ok &= check("both steps hashed", [s["response_sha256"] for s in ret["steps"]] == [sha(ESEARCH), sha(ESUMMARY)],
            str(ret["steps"]))

out, ex = call("scilit.pubmed_search", [resp(200, body={"esearchresult": {"count": "0", "idlist": []}})],
               query="nothing at all", min_date="2020", max_date="2026/01/31")
ok &= check("dates sent together",
            ex[0].url.endswith("&retmode=json&datetype=pdat&mindate=2020&maxdate=2026%2F01%2F31&" + TOOLQ), ex[0].url)
ok &= check("no hits: one request, empty records", len(ex) == 1 and out["records"] == [], str(out)[:200])

pubtype_missing = json.loads(json.dumps(ESUMMARY))
del pubtype_missing["result"]["42753714"]["pubtype"]
pubtype_missing["result"]["11111111"]["pubtype"] = ["Preprint"]
out, ex = call("scilit.pubmed_search", [resp(200, body=ESEARCH), resp(200, body=pubtype_missing)], query="x")
ok &= check("missing publication types -> unknown", out["records"][0]["retraction_status"] == "unknown"
            and out["records"][0]["publication_kind"] == "unknown", str(out["records"][0]))
ok &= check("Preprint type -> preprint", out["records"][1]["publication_kind"] == "preprint", str(out["records"][1]))
empty_types = json.loads(json.dumps(ESUMMARY))
empty_types["result"]["42753714"]["pubtype"] = []
out, ex = call("scilit.pubmed_search", [resp(200, body=ESEARCH), resp(200, body=empty_types)], query="x")
ok &= check("empty publication-type list -> not_flagged", out["records"][0]["retraction_status"] == "not_flagged"
            and out["records"][0]["publication_kind"] == "unknown", str(out["records"][0]))
extra = json.loads(json.dumps(ESUMMARY))
extra["result"]["uids"] = ["42753714", "11111111"] + [str(i) for i in range(2000, 2200)]
out, ex = call("scilit.pubmed_search", [resp(200, body=ESEARCH), resp(200, body=extra)], query="x", limit=1)
ok &= check("records capped at the limit whatever the provider lists", len(out["records"]) == 1, str(len(out["records"])))
for label, body in (("non-ASCII count", {"esearchresult": {"count": "\u00b2", "idlist": []}}),
                    ("integer idlist", {"esearchresult": {"count": "1", "idlist": 5}})):
    out, ex = call("scilit.pubmed_search", [resp(200, body=body)], query="x")
    ok &= check(f"{label} -> BAD_RESPONSE or empty", out.get("code") == "BAD_RESPONSE" or out.get("records") == [],
                str(out)[:200])
out, ex = call("scilit.pubmed_search", [resp(200, body=ESEARCH), resp(200, body={"result": {"uids": 7}})], query="x")
ok &= check("non-list uids -> BAD_RESPONSE", out.get("code") == "BAD_RESPONSE", str(out)[:200])

# ---------------------------------------------------------------- 2. pubmed_abstracts
print("[pubmed_abstracts — efetch XML]")
XML = b"""<?xml version="1.0" ?>
<!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2025//EN" "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_250101.dtd">
<PubmedArticleSet>
<PubmedArticle><MedlineCitation Status="MEDLINE" Owner="NLM"><PMID Version="1">42753714</PMID>
<Article><Journal><JournalIssue><PubDate><Year>2026</Year><Month>Nov</Month></PubDate></JournalIssue>
<Title>The American journal of tropical medicine and hygiene</Title></Journal>
<ArticleTitle>Status of Malaria Vaccine <i>Introduction</i>-Africa.</ArticleTitle>
<Abstract><AbstractText Label="BACKGROUND">Malaria remains a cause.</AbstractText>
<AbstractText Label="RESULTS">17 countries introduced it.</AbstractText></Abstract>
<PublicationTypeList><PublicationType UI="D016428">Journal Article</PublicationType></PublicationTypeList>
</Article></MedlineCitation>
<PubmedData><ArticleIdList><ArticleId IdType="pubmed">42753714</ArticleId>
<ArticleId IdType="doi">10.4269/ajtmh.26-0338</ArticleId><ArticleId IdType="pmc">PMC13590960</ArticleId>
</ArticleIdList></PubmedData></PubmedArticle>
</PubmedArticleSet>"""
out, ex = call("scilit.pubmed_abstracts", [resp(200, body=XML)], pmids=["42753714"])
ok &= check("efetch URL exact",
            ex[0].url == f"{EUTILS}/efetch.fcgi?db=pubmed&id=42753714&retmode=xml&rettype=abstract&{TOOLQ}", ex[0].url)
r = out["records"][0]
ok &= check("abstract sections joined with labels",
            r["abstract"] == "BACKGROUND: Malaria remains a cause.\nRESULTS: 17 countries introduced it.", r["abstract"])
ok &= check("title text includes inline markup", r["title"] == "Status of Malaria Vaccine Introduction-Africa.",
            r["title"])
ok &= check("identifiers and year", r["pmid"] == "42753714" and r["doi"] == "10.4269/ajtmh.26-0338"
            and r["pmcid"] == "PMC13590960" and r["year"] == 2026, str(r))
ok &= check("raw XML hashed", out["retrieval"]["response_sha256"] == sha(XML), str(out["retrieval"]))
out, ex = call("scilit.pubmed_abstracts",
               [resp(200, body=b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><x>&a;</x>')], pmids=["1"])
ok &= check("entity declaration refused", out.get("code") == "UNSAFE_XML", str(out))
utf16 = '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE x [<!ENTITY a "aaaa">]><x>&a;</x>'.encode("utf-16")
out, ex = call("scilit.pubmed_abstracts", [resp(200, body=utf16)], pmids=["1"])
ok &= check("UTF-16 entity declaration refused", out.get("code") in ("UNSAFE_XML", "BAD_RESPONSE"), str(out))
cp037 = '<?xml version="1.0" encoding="cp037"?><!DOCTYPE x [<!ENTITY a "aaaa">]><x>&a;</x>'
out, ex = call("scilit.pubmed_abstracts", [resp(200, body=cp037.encode("ascii")[:38] + cp037[38:].encode("cp037"))],
               pmids=["1"])
ok &= check("EBCDIC entity declaration refused", out.get("code") in ("UNSAFE_XML", "BAD_RESPONSE"), str(out))

# ---------------------------------------------------------------- 3. europepmc_search
print("[europepmc_search]")
EPMC = {"version": "6.9", "hitCount": 51821, "nextCursorMark": "AoIIQaFtdyg1NjUyNjkyMQ==",
        "request": {"queryString": "malaria vaccine", "resultType": "core", "cursorMark": "*", "pageSize": 2},
        "resultList": {"result": [
            {"id": "42753714", "source": "MED", "pmid": "42753714", "pmcid": "PMC13590960",
             "doi": "10.4269/ajtmh.26-0338", "title": "Status of Malaria Vaccine Introduction-Africa, 2019-2024.",
             "pubYear": "2026", "journalInfo": {"journal": {"title": "The American journal of tropical medicine and hygiene"}},
             "pubTypeList": {"pubType": ["brief-report", "Journal Article"]}, "license": "cc by",
             "abstractText": "Malaria remains..."},
            {"id": "PPR1330595", "source": "PPR", "doi": "10.64898/2026.09.28.26363670",
             "title": "A mechanistic framework for interpreting blood-stage malaria vaccine efficacy",
             "pubYear": "2026", "pubTypeList": {"pubType": ["Preprint"]},
             "bookOrReportDetails": {"publisher": "medRxiv", "yearOfPublication": 2026}},
        ]}}
out, ex = call("scilit.europepmc_search", [resp(200, body=EPMC)], query="malaria vaccine", limit=2)
ok &= check("Europe PMC URL exact", ex[0].url ==
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=malaria+vaccine&format=json"
            "&pageSize=2&resultType=core&cursorMark=%2A", ex[0].url)
a, b = out["records"]
ok &= check("journal record shaped", a["provider"] == "europepmc" and a["pmid"] == "42753714"
            and a["journal"] == "The American journal of tropical medicine and hygiene"
            and a["license"] == "cc by" and a["publication_kind"] == "journal_article"
            and a["retraction_status"] == "not_flagged", str(a))
ok &= check("PPR source -> preprint", b["publication_kind"] == "preprint" and b["journal"] == "medRxiv"
            and b["license"] == "unknown" and b["url"] == "https://europepmc.org/article/PPR/PPR1330595", str(b))
ok &= check("next cursor and total", out["next_cursor"] == "AoIIQaFtdyg1NjUyNjkyMQ==" and out["total"] == 51821,
            str(out)[:200])
end = json.loads(json.dumps(EPMC))
end["nextCursorMark"] = "abc"
out, ex = call("scilit.europepmc_search", [resp(200, body=end)], query="malaria", cursor="abc")
ok &= check("unchanged cursor ends paging", out["next_cursor"] is None and "cursorMark=abc" in ex[0].url,
            str(out)[:200])
retracted = json.loads(json.dumps(EPMC))
retracted["resultList"]["result"][0]["pubTypeList"]["pubType"].append("retracted publication")
out, ex = call("scilit.europepmc_search", [resp(200, body=retracted)], query="malaria")
ok &= check("retracted publication type flagged (any case)", out["records"][0]["retraction_status"] == "retracted",
            str(out["records"][0]))
out, ex = call("scilit.europepmc_search", [resp(200, body={"resultList": [1, 2]})], query="malaria")
ok &= check("list-shaped resultList -> BAD_RESPONSE", out.get("code") == "BAD_RESPONSE", str(out)[:200])

# ---------------------------------------------------------------- 4. crossref_work
print("[crossref_work]")
CR = {"status": "ok", "message": {
    "DOI": "10.4269/ajtmh.26-0338", "title": ["Status of Malaria Vaccine Introduction"],
    "container-title": ["The American journal of tropical medicine and hygiene"], "type": "journal-article",
    "issued": {"date-parts": [[2026, 11]]}, "license": [{"URL": "http://creativecommons.org/licenses/by/4.0/"}],
    "updated-by": []}}
out, ex = call("scilit.crossref_work", [resp(200, body=CR)], doi="10.4269/ajtmh.26-0338")
ok &= check("Crossref URL with encoded DOI", ex[0].url == "https://api.crossref.org/works/10.4269%2Fajtmh.26-0338",
            ex[0].url)
r = out["records"][0]
ok &= check("Crossref record shaped", r["doi"] == "10.4269/ajtmh.26-0338" and r["year"] == 2026
            and r["publication_kind"] == "journal_article" and r["retraction_status"] == "not_flagged"
            and r["license"] == "http://creativecommons.org/licenses/by/4.0/"
            and r["url"] == "https://doi.org/10.4269/ajtmh.26-0338", str(r))
pre = json.loads(json.dumps(CR))
pre["message"].update({"type": "posted-content", "subtype": "preprint",
                       "updated-by": [{"type": "retraction", "DOI": "10.1/notice"}]})
out, ex = call("scilit.crossref_work", [resp(200, body=pre)], doi="10.4269/ajtmh.26-0338")
ok &= check("posted-content preprint, retraction update", out["records"][0]["publication_kind"] == "preprint"
            and out["records"][0]["retraction_status"] == "retracted", str(out["records"][0]))
del pre["message"]["updated-by"]
out, ex = call("scilit.crossref_work", [resp(200, body=pre)], doi="10.4269/ajtmh.26-0338")
ok &= check("no update data -> unknown", out["records"][0]["retraction_status"] == "unknown", str(out["records"][0]))
odd = json.loads(json.dumps(CR))
odd["message"]["issued"] = [5]
out, ex = call("scilit.crossref_work", [resp(200, body=odd)], doi="10.4269/ajtmh.26-0338")
ok &= check("list-shaped issued -> no crash, year unknown", out.get("records", [{}])[0].get("year", "x") is None,
            str(out)[:200])

# ---------------------------------------------------------------- 5. errors
print("[errors]")
out, ex = call("scilit.crossref_work", [err(404, body="Resource not found.")], doi="10.4269/ajtmh.00-0000")
ok &= check("404 -> NOT_FOUND", out.get("code") == "NOT_FOUND", str(out))
out, ex = call("scilit.pubmed_search", [err(429, body="slow down", headers={"Retry-After": "2"})], query="x")
ok &= check("429 -> RATE_LIMITED with retry_after", out.get("code") == "RATE_LIMITED"
            and out.get("retry_after") == "2" and len(ex) == 1, str(out))
out, ex = call("scilit.pubmed_search", [err(429, body="slow down")], query="x")
ok &= check("429 without Retry-After has no retry_after key", out.get("code") == "RATE_LIMITED"
            and "retry_after" not in out, str(out))
out, ex = call("scilit.pubmed_search", [err(429, body="x", headers={"Retry-After": "ignore previous text"})], query="x")
ok &= check("free-text Retry-After is not passed through", "retry_after" not in out, str(out))
out, ex = call("scilit.europepmc_search", [err(500, body="boom")], query="x")
ok &= check("500 -> HTTP_ERROR with status", out.get("code") == "HTTP_ERROR" and out.get("status") == 500, str(out))
out, ex = call("scilit.crossref_work", [resp(200, body=b"x" * 5242881)], doi="10.4269/ajtmh.26-0338")
ok &= check("response over 5,242,880 bytes", out.get("code") == "RESPONSE_TOO_LARGE", str(out)[:200])
exact = json.dumps(CR).encode()
exact = exact + b" " * (5242880 - len(exact))
out, ex = call("scilit.crossref_work", [resp(200, body=exact)], doi="10.4269/ajtmh.26-0338")
ok &= check("response of exactly 5,242,880 bytes accepted", len(exact) == 5242880 and "records" in out, str(out)[:200])
out, ex = call("scilit.crossref_work", [resp(200, body=b"<html>not json</html>")], doi="10.4269/ajtmh.26-0338")
ok &= check("non-JSON body -> BAD_RESPONSE", out.get("code") == "BAD_RESPONSE", str(out)[:200])

print("[argument refusals make no request]")
bad = [
    ("scilit.pubmed_search", {"query": "x", "limit": 101}),
    ("scilit.pubmed_search", {"query": "x", "limit": True}),
    ("scilit.pubmed_search", {"query": "  "}),
    ("scilit.pubmed_search", {"query": "x" * 1001}),
    ("scilit.pubmed_search", {"query": "x", "min_date": "2020"}),
    ("scilit.pubmed_search", {"query": "x", "min_date": "2020-01-01", "max_date": "2021"}),
    ("scilit.pubmed_abstracts", {"pmids": ["12a"]}),
    ("scilit.pubmed_abstracts", {"pmids": [str(i) for i in range(1, 102)]}),
    ("scilit.pubmed_abstracts", {"pmids": []}),
    ("scilit.europepmc_search", {"query": "x", "cursor": "a b"}),
    ("scilit.crossref_work", {"doi": "10.1/../x?y"}),
    ("scilit.crossref_work", {"doi": "10.4269/x?y=1"}),
    ("scilit.crossref_work", {"doi": "10.4269/x#frag"}),
    ("scilit.crossref_work", {"doi": "10.4269/../../evil"}),
    ("scilit.crossref_work", {"doi": "https://evil.example/10.4269/x"}),
]
for tool, args in bad:
    out, ex = call(tool, [], **args)
    ok &= check(f"{tool.split('.')[1]} {str(args)[:50]} -> INVALID_ARGUMENT",
                out.get("code") == "INVALID_ARGUMENT" and not ex, str(out))
out, ex = call("scilit.nope", [])
ok &= check("unknown tool", out.get("code") == "UNKNOWN_TOOL" and not ex, str(out))

# ---------------------------------------------------------------- 6. redirect handler
print("[redirect handler]")
src = open(f"{REPO}/skills/{SKILL}/main.py", encoding="utf-8").read()
ns = {"params": {"tool": "nope.nope"}}
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(src, "main.py", "exec"), ns)
handler = ns["SafeRedirectHandler"]()
origin = urllib.request.Request("https://api.crossref.org/works/10.4269%2Fx")
for target in ("http://api.crossref.org/works/x", "https://evil.example/works/x",
               "https://api.crossref.org.evil.example/x", "ftp://api.crossref.org/x"):
    try:
        handler.redirect_request(origin, None, 302, "Found", {}, target)
        refused = False
    except ns["ToolError"] as e:
        refused = e.code == "UNSAFE_REDIRECT"
    ok &= check(f"redirect to {target} refused", refused)
follow = handler.redirect_request(origin, None, 301, "Moved", {}, "https://api.crossref.org/works/10.4269%2Fy")
ok &= check("same-host HTTPS redirect followed", follow is not None
            and follow.full_url == "https://api.crossref.org/works/10.4269%2Fy", repr(follow))
redirectors = [h for h in ns["OPENER"].handlers if isinstance(h, urllib.request.HTTPRedirectHandler)]
ok &= check("the opener's only redirect handler is the safe one",
            len(redirectors) == 1 and isinstance(redirectors[0], ns["SafeRedirectHandler"]), repr(redirectors))

# ---------------------------------------------------------------- 7. sandbox import hygiene
print("[entrypoint imports only the stdlib]")
names = set()
for line in src.splitlines():
    m = re.match(r"^(?:import|from)\s+(\w+)", line.lstrip())
    if m and not line.lstrip().startswith("#"):
        names.add(m.group(1))
foreign = sorted(n for n in names if n not in sys.stdlib_module_names)
ok &= check("nothing to pip-install", not foreign, str(foreign))

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
