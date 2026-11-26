"""Offline tests for the science-evidence skill, including bundles built from real science-statistics records."""
import copy
import hashlib
import json
import re
import sys

from mockhttp import REPO, run_tool, check

ok = True
SKILL = "science-evidence"
SCOPE = "consistency only; not authentication and not method validation"
CSV = "unit,group,value\na1,A,1\na2,A,2\na3,A,3\na4,A,4\nb1,B,2\nb2,B,4\nb3,B,6\nb4,B,NA\n"


def call(tool, **kw):
    params = {"tool": tool}
    params.update(kw)
    out, ex = run_tool(SKILL, params, [])
    assert not ex, "the evidence skill must make no HTTP request"
    return out


def codes(out):
    return sorted({f["code"] for f in out["result"]["findings"] if f["severity"] == "error"})


# A real analysis record from the statistics skill (cross-skill hash agreement).
stat, _ = run_tool("science-statistics", {
    "tool": "scistat.mean_difference", "csv": CSV, "value_column": "value", "group_column": "group",
    "unit_column": "unit", "units": "µg/L", "missing_policy": "exclude_and_report",
    "group_a": "A", "group_b": "B"}, [])
RECORD = stat["record"]

GOOD = {
    "schema": "sophon.science.evidence/1",
    "bundle_id": "bundle-1",
    "created_at": "2026-11-26T10:00:00Z",
    "question": "Is the group B mean higher than the group A mean in this synthetic assay?",
    "sources": [
        {"id": "s1", "provider": "pubmed", "identifiers": {"pmid": "12345678", "doi": "10.1000/xyz"},
         "title": "A study", "retrieved_at": "2026-11-26T09:00:00Z", "response_sha256": "a" * 64,
         "publication_kind": "journal_article", "retraction_status": "not_flagged", "license": "unknown"},
        {"id": "s2", "provider": "europepmc", "identifiers": {"doi": "10.1101/2026.01.01.000001"},
         "title": "A preprint", "retrieved_at": "2026-11-26T09:00:00Z", "response_sha256": "b" * 64,
         "publication_kind": "preprint", "retraction_status": "unknown", "license": "unknown"},
    ],
    "analyses": [dict(RECORD, id="an1")],
    "claims": [
        {"id": "c1", "text": "The group B mean exceeds the group A mean by 1.5 µg/L in these samples.",
         "kind": "numerical", "status": "supported", "supports": [],
         "numbers": [{"value": 1.5, "analysis_id": "an1", "path": "/difference"},
                     {"value": 4, "analysis_id": "an1", "path": "/n_a"}]},
        {"id": "c2", "text": "Earlier work reports a similar shift.", "kind": "literature",
         "status": "supported", "supports": [{"source_id": "s1", "quote": "a similar shift was observed",
                                              "locator": "abstract"}], "numbers": []},
        {"id": "c3", "text": "The shift may reflect assay drift.", "kind": "interpretation",
         "status": "unverified", "supports": [], "numbers": []},
    ],
    "reviews": [{"id": "r1", "reviewer": "scientific-reviewer", "findings": []}],
    "limitations": ["Synthetic data with four and three units per group."],
}


def variant(mutate):
    b = copy.deepcopy(GOOD)
    mutate(b)
    return b


# ---------------------------------------------------------------- 1. canonical hashing
print("[canonical_hash]")
out = call("scievidence.canonical_hash", value={"b": 1, "a": "é"})
expected = hashlib.sha256('{"a":"é","b":1}'.encode("utf-8")).hexdigest()
ok &= check("canonical hash of a non-ASCII object", out["result"]["sha256"] == expected, str(out))
ok &= check("canonical byte count", out["result"]["bytes"] == len('{"a":"é","b":1}'.encode("utf-8")), str(out))
out = call("scievidence.canonical_hash", value=RECORD["output"])
ok &= check("agrees with science-statistics output_sha256", out["result"]["sha256"] == RECORD["output_sha256"],
            str(out))
out = call("scievidence.canonical_hash", value=float("nan"))
ok &= check("NaN refused", out.get("code") == "INVALID_ARGUMENT", str(out))

# ---------------------------------------------------------------- 2. a clean bundle
print("[verify_bundle — clean bundle from a real record]")
out = call("scievidence.verify_bundle", bundle=GOOD)
ok &= check("consistent", out["result"]["consistent"] is True, json.dumps(out)[:500])
ok &= check("no error findings", codes(out) == [], str(codes(out)))
ok &= check("scope stated", out["result"]["verification_scope"] == SCOPE, str(out)[:300])
ok &= check("bundle hash reported", re.match(r"^[0-9a-f]{64}$", out["result"]["bundle_sha256"] or "") is not None,
            str(out)[:300])
warn = [f["code"] for f in out["result"]["findings"] if f["severity"] == "warning"]
ok &= check("unused preprint is not a warning by itself", "PREPRINT_SUPPORT" not in warn, str(warn))
out = call("scievidence.validate_bundle", bundle=GOOD)
ok &= check("schema valid", out["result"]["valid"] is True and out["result"]["findings"] == [], str(out)[:300])
out = call("scievidence.verify_bundle", bundle=json.dumps(GOOD))
ok &= check("bundle accepted as a JSON string", out["result"]["consistent"] is True, str(out)[:300])

# ---------------------------------------------------------------- 3. planted defects
print("[verify_bundle — planted defects]")
cases = [
    ("dangling source", lambda b: b["claims"][1]["supports"][0].update(source_id="s9"), "DANGLING_REFERENCE"),
    ("dangling analysis", lambda b: b["claims"][0]["numbers"][0].update(analysis_id="an9"), "DANGLING_REFERENCE"),
    ("unresolvable pointer", lambda b: b["claims"][0]["numbers"][0].update(path="/nope"), "DANGLING_REFERENCE"),
    ("duplicate id", lambda b: b["claims"][2].update(id="c1"), "DUPLICATE_ID"),
    ("tampered output", lambda b: b["analyses"][0]["output"].update(difference=1.6), "OUTPUT_HASH_MISMATCH"),
    ("tampered input", lambda b: b["analyses"][0]["input"].update(csv=CSV + "b5,B,9\n"), "INPUT_HASH_MISMATCH"),
    ("claimed number differs", lambda b: b["claims"][0]["numbers"][0].update(value=1.6), "NUMBER_MISMATCH"),
    ("numerical claim without analysis", lambda b: b["claims"][0].update(numbers=[]),
     "NUMERICAL_CLAIM_WITHOUT_ANALYSIS"),
    ("supported literature claim without quote", lambda b: b["claims"][1]["supports"][0].update(quote=""),
     "MISSING_QUOTE"),
    ("supported literature claim without support", lambda b: b["claims"][1].update(supports=[]), "MISSING_QUOTE"),
    ("retracted support", lambda b: b["sources"][0].update(retraction_status="retracted"), "RETRACTED_SUPPORT"),
    ("no limitations", lambda b: b.update(limitations=[]), "MISSING_LIMITATIONS"),
    ("unknown claim kind", lambda b: b["claims"][0].update(kind="opinion"), "SCHEMA_INVALID"),
    ("unknown retraction status", lambda b: b["sources"][0].update(retraction_status="no"), "SCHEMA_INVALID"),
    ("wrong bundle schema", lambda b: b.update(schema="other/1"), "SCHEMA_INVALID"),
    ("analysis without provenance", lambda b: b["analyses"][0].pop("provenance"), "SCHEMA_INVALID"),
]
for label, mutate, code in cases:
    out = call("scievidence.verify_bundle", bundle=variant(mutate))
    found = codes(out) if "result" in out else [out.get("code")]
    ok &= check(f"{label} -> {code}", code in found and out["result"]["consistent"] is False, str(found))

out = call("scievidence.verify_bundle",
           bundle=variant(lambda b: b["claims"][1]["supports"].append(
               {"source_id": "s2", "quote": "a preprint agrees", "locator": "results"})))
warn = [f["code"] for f in out["result"]["findings"] if f["severity"] == "warning"]
ok &= check("preprint support is a warning, not an error", "PREPRINT_SUPPORT" in warn
            and out["result"]["consistent"] is True, str(out["result"]["findings"]))

out = call("scievidence.validate_bundle", bundle=variant(lambda b: b["claims"][0].update(kind="opinion")))
ok &= check("validate_bundle reports the schema error", out["result"]["valid"] is False
            and any(f["code"] == "SCHEMA_INVALID" for f in out["result"]["findings"]), str(out)[:300])

# ---------------------------------------------------------------- 3b. pointers, malformed sections, numbers
print("[pointers, malformed sections, number edges]")
bh, _ = run_tool("science-statistics", {"tool": "scistat.bh_adjust", "p_values": [0.01, 0.04]}, [])


def with_bh(path, value):
    def mutate(b):
        b["analyses"].append(dict(bh["record"], id="an2"))
        b["claims"][0]["numbers"] = [{"value": value, "analysis_id": "an2", "path": path}]
    return variant(mutate)


out = call("scievidence.verify_bundle", bundle=with_bh("/tests/0/adjusted", bh["result"]["tests"][0]["adjusted"]))
ok &= check("list index pointer resolves", out["result"]["consistent"] is True, str(out["result"]["findings"]))
for path in ("/tests/01/adjusted", "/tests/\u00b2/adjusted", "/tests/-/adjusted"):
    out = call("scievidence.verify_bundle", bundle=with_bh(path, 0.02))
    ok &= check(f"non-RFC 6901 index {path!r} is a dangling reference",
                "result" in out and "DANGLING_REFERENCE" in codes(out), str(out)[:200])
out = call("scievidence.verify_bundle", bundle=with_bh("/tests/0/adjusted", 10 ** 400))
ok &= check("huge integer claim value is a mismatch", "result" in out and "NUMBER_MISMATCH" in codes(out),
            str(out)[:200])
out = call("scievidence.verify_bundle",
           bundle=variant(lambda b: b["claims"][0]["numbers"][0].update(value=1.5000001)))
ok &= check("near-equal outside tolerance is a mismatch", "NUMBER_MISMATCH" in codes(out), str(codes(out)))
ok &= check("scope stated on a failing result",
            out["result"]["verification_scope"] == SCOPE and out["result"]["consistent"] is False, "")


def tilde(b):
    b["analyses"][0] = dict(b["analyses"][0])
    b["analyses"][0]["output"] = dict(b["analyses"][0]["output"], **{"a/b~c": 7})
    b["analyses"][0]["output_sha256"] = hashlib.sha256(json.dumps(
        b["analyses"][0]["output"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    b["claims"][0]["numbers"] = [{"value": 7, "analysis_id": "an1", "path": "/a~1b~0c"}]


out = call("scievidence.verify_bundle", bundle=variant(tilde))
ok &= check("~0 and ~1 escapes resolve", out["result"]["consistent"] is True, str(out["result"]["findings"]))
for section in ("sources", "claims", "limitations"):
    for bad in (5, True):
        for tool in ("scievidence.validate_bundle", "scievidence.verify_bundle"):
            out = call(tool, bundle=variant(lambda b: b.update({section: bad})))
            ok &= check(f"{tool.split('.')[1]}: {section}={bad!r} is SCHEMA_INVALID",
                        "result" in out and any(f["code"] == "SCHEMA_INVALID" for f in out["result"]["findings"]),
                        str(out)[:200])

# ---------------------------------------------------------------- 4. limits and refusals
print("[limits and refusals]")
big = variant(lambda b: b["limitations"].append("x" * 1048576))
out = call("scievidence.verify_bundle", bundle=big)
ok &= check("bundle over 1,048,576 bytes", out.get("code") == "LIMIT_EXCEEDED", str(out)[:200])
out = call("scievidence.verify_bundle", bundle=json.dumps(big))
ok &= check("JSON-string bundle over 1,048,576 bytes", out.get("code") == "LIMIT_EXCEEDED", str(out)[:200])
out = call("scievidence.verify_bundle", bundle="{not json")
ok &= check("malformed JSON string", out.get("code") == "INVALID_ARGUMENT", str(out)[:200])
out = call("scievidence.nope")
ok &= check("unknown tool", out.get("code") == "UNKNOWN_TOOL", str(out))

# ---------------------------------------------------------------- 5. sandbox import hygiene
print("[entrypoint imports only the stdlib]")
src = open(f"{REPO}/skills/{SKILL}/main.py", encoding="utf-8").read()
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
