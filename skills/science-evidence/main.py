"""Science evidence: canonical hashing, schema validation and consistency checks for evidence bundles.

Runs fully local in the Sophon Python sandbox: no network, no credentials, standard library only.
`params` is injected as a global by the Sophon runtime and carries the tool name and its arguments.

A bundle (schema sophon.science.evidence/1) links a research question to its sources, the analysis
records produced by science-statistics, the claims made from them, reviews and limitations. The
checks here are consistency checks only: matching hashes and resolving references do not
authenticate that anything ran, do not show that a source supports a claim beyond the quoted text,
and do not validate the method.
"""

import copy
import hashlib
import json
import math
import re

tool_name = params.get("tool", "")

BUNDLE_SCHEMA = "sophon.science.evidence/1"
RECORD_SCHEMA = "sophon.science.analysis/1"
SCOPE = "consistency only; not authentication and not method validation"
MAX_BUNDLE_BYTES = 1048576
NUMBER_TOLERANCE = 1e-9
ARRAY_INDEX_RE = re.compile(r"^(?:0|[1-9][0-9]*)$")

PUBLICATION_KINDS = ("journal_article", "preprint", "unknown")
RETRACTION_STATUSES = ("retracted", "not_flagged", "unknown")
CLAIM_KINDS = ("literature", "numerical", "interpretation")
CLAIM_STATUSES = ("supported", "unsupported", "contested", "unverified")


class ToolError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256_of(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def finding(code, where, message, severity="error"):
    return {"code": code, "severity": severity, "where": where, "message": message}


def is_number(x):
    return not isinstance(x, bool) and isinstance(x, (int, float))


def listed(container, key):
    """The list under key, or an empty list when it is missing or not a list (reported by the schema)."""
    value = container.get(key) if isinstance(container, dict) else None
    return value if isinstance(value, list) else []


# --- Input -----------------------------------------------------------------------

def bundle_argument():
    bundle = params.get("bundle")
    if isinstance(bundle, str):
        if len(bundle.encode("utf-8")) > MAX_BUNDLE_BYTES:
            raise ToolError("LIMIT_EXCEEDED", f"bundle exceeds {MAX_BUNDLE_BYTES} bytes")
        try:
            bundle = json.loads(bundle)
        except ValueError:
            raise ToolError("INVALID_ARGUMENT", "bundle is not valid JSON")
    if not isinstance(bundle, dict):
        raise ToolError("INVALID_ARGUMENT", "bundle must be a JSON object")
    try:
        size = len(canonical_bytes(bundle))
    except ValueError:
        raise ToolError("INVALID_ARGUMENT", "bundle holds a value that cannot be hashed (NaN or infinity)")
    if size > MAX_BUNDLE_BYTES:
        raise ToolError("LIMIT_EXCEEDED", f"bundle exceeds {MAX_BUNDLE_BYTES} bytes")
    return bundle


# --- Schema ----------------------------------------------------------------------

def schema_findings(bundle):
    out = []

    def need(obj, key, kind, where, allowed=None):
        value = obj.get(key) if isinstance(obj, dict) else None
        good = isinstance(value, kind) and not (kind is str and not value.strip() and allowed is None)
        if kind is list:
            good = isinstance(value, list)
        if good and allowed is not None and value not in allowed:
            good = False
        if not good:
            expect = f"one of {', '.join(allowed)}" if allowed else ("a non-empty string" if kind is str
                                                                    else kind.__name__)
            out.append(finding("SCHEMA_INVALID", f"{where}.{key}", f"must be {expect}"))
            return None
        return value

    if bundle.get("schema") != BUNDLE_SCHEMA:
        out.append(finding("SCHEMA_INVALID", "schema", f"must be {BUNDLE_SCHEMA}"))
    for key in ("bundle_id", "created_at", "question"):
        need(bundle, key, str, "bundle")
    for key in ("sources", "analyses", "claims", "reviews", "limitations"):
        need(bundle, key, list, "bundle")

    for i, s in enumerate(listed(bundle, "sources")):
        where = f"sources[{i}]"
        if not isinstance(s, dict):
            out.append(finding("SCHEMA_INVALID", where, "must be an object"))
            continue
        for key in ("id", "provider", "title", "retrieved_at", "response_sha256", "license"):
            need(s, key, str, where)
        need(s, "identifiers", dict, where)
        need(s, "publication_kind", str, where, PUBLICATION_KINDS)
        need(s, "retraction_status", str, where, RETRACTION_STATUSES)

    for i, a in enumerate(listed(bundle, "analyses")):
        where = f"analyses[{i}]"
        if not isinstance(a, dict):
            out.append(finding("SCHEMA_INVALID", where, "must be an object"))
            continue
        need(a, "id", str, where)
        need(a, "schema", str, where, (RECORD_SCHEMA,))
        for key in ("tool", "method", "input_sha256", "output_sha256"):
            need(a, key, str, where)
        need(a, "provenance", str, where, ("tool-reported",))
        for key in ("input", "parameters", "output"):
            need(a, key, dict, where)

    for i, c in enumerate(listed(bundle, "claims")):
        where = f"claims[{i}]"
        if not isinstance(c, dict):
            out.append(finding("SCHEMA_INVALID", where, "must be an object"))
            continue
        need(c, "id", str, where)
        need(c, "text", str, where)
        need(c, "kind", str, where, CLAIM_KINDS)
        need(c, "status", str, where, CLAIM_STATUSES)
        for j, sup in enumerate(need(c, "supports", list, where) or []):
            w = f"{where}.supports[{j}]"
            if not isinstance(sup, dict):
                out.append(finding("SCHEMA_INVALID", w, "must be an object"))
                continue
            need(sup, "source_id", str, w)
            if not isinstance(sup.get("quote"), str):
                out.append(finding("SCHEMA_INVALID", f"{w}.quote", "must be a string"))
            if not isinstance(sup.get("locator"), str):
                out.append(finding("SCHEMA_INVALID", f"{w}.locator", "must be a string"))
        for j, num in enumerate(need(c, "numbers", list, where) or []):
            w = f"{where}.numbers[{j}]"
            if not isinstance(num, dict) or not is_number(num.get("value")):
                out.append(finding("SCHEMA_INVALID", f"{w}.value", "must be a number"))
                continue
            need(num, "analysis_id", str, w)
            if not isinstance(num.get("path"), str) or not num["path"].startswith("/"):
                out.append(finding("SCHEMA_INVALID", f"{w}.path", "must be a JSON Pointer starting with /"))

    for i, r in enumerate(listed(bundle, "reviews")):
        where = f"reviews[{i}]"
        if not isinstance(r, dict):
            out.append(finding("SCHEMA_INVALID", where, "must be an object"))
            continue
        need(r, "id", str, where)
        need(r, "reviewer", str, where)
        need(r, "findings", list, where)

    for i, item in enumerate(listed(bundle, "limitations")):
        if not isinstance(item, str) or not item.strip():
            out.append(finding("SCHEMA_INVALID", f"limitations[{i}]", "must be a non-empty string"))
    return out


# --- Consistency -----------------------------------------------------------------

def resolve_pointer(document, pointer):
    """Resolve an RFC 6901 JSON Pointer; returns (found, value)."""
    if pointer == "":
        return True, document
    current = document
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and ARRAY_INDEX_RE.match(token) and int(token) < len(current):
            current = current[int(token)]
        else:
            return False, None
    return True, current


def consistency_findings(bundle):
    out = []
    seen = {}
    for section in ("sources", "analyses", "claims", "reviews"):
        for i, item in enumerate(bundle[section]):
            ident = item["id"]
            if ident in seen:
                out.append(finding("DUPLICATE_ID", f"{section}[{i}].id",
                                   f"id {ident!r} is also used at {seen[ident]}"))
            else:
                seen[ident] = f"{section}[{i}]"

    sources = {s["id"]: s for s in bundle["sources"]}
    analyses = {a["id"]: a for a in bundle["analyses"]}

    for i, a in enumerate(bundle["analyses"]):
        where = f"analyses[{i}]"
        if sha256_of(a["input"]) != a["input_sha256"]:
            out.append(finding("INPUT_HASH_MISMATCH", where, "the input does not match input_sha256"))
        if sha256_of(a["output"]) != a["output_sha256"]:
            out.append(finding("OUTPUT_HASH_MISMATCH", where, "the output does not match output_sha256"))

    for i, c in enumerate(bundle["claims"]):
        where = f"claims[{i}]"
        supported = c["status"] == "supported"
        for j, sup in enumerate(c["supports"]):
            w = f"{where}.supports[{j}]"
            source = sources.get(sup["source_id"])
            if source is None:
                out.append(finding("DANGLING_REFERENCE", w, f"source {sup['source_id']!r} is not in sources"))
                continue
            if supported and source["retraction_status"] == "retracted":
                out.append(finding("RETRACTED_SUPPORT", w,
                                   f"a supported claim relies on retracted source {source['id']!r}"))
            if supported and source["publication_kind"] == "preprint":
                out.append(finding("PREPRINT_SUPPORT", w,
                                   f"source {source['id']!r} is a preprint (not peer reviewed); label it",
                                   severity="warning"))
        for j, num in enumerate(c["numbers"]):
            w = f"{where}.numbers[{j}]"
            analysis = analyses.get(num["analysis_id"])
            if analysis is None:
                out.append(finding("DANGLING_REFERENCE", w, f"analysis {num['analysis_id']!r} is not in analyses"))
                continue
            found, value = resolve_pointer(analysis["output"], num["path"])
            if not found:
                out.append(finding("DANGLING_REFERENCE", w,
                                   f"path {num['path']!r} does not exist in the output of {analysis['id']!r}"))
                continue
            try:
                equal = is_number(value) and math.isclose(num["value"], value, rel_tol=NUMBER_TOLERANCE,
                                                          abs_tol=1e-12)
            except OverflowError:
                equal = False
            if not equal:
                out.append(finding("NUMBER_MISMATCH", w,
                                   f"the claim states {num['value']!r} but {analysis['id']}{num['path']} is {value!r}"))
        if supported and c["kind"] == "numerical" and not c["numbers"]:
            out.append(finding("NUMERICAL_CLAIM_WITHOUT_ANALYSIS", where,
                               "a supported numerical claim cites no analysis value"))
        if supported and c["kind"] == "literature":
            if not c["supports"] or any(not sup["quote"].strip() for sup in c["supports"]):
                out.append(finding("MISSING_QUOTE", where,
                                   "a supported literature claim needs at least one support, and every support "
                                   "needs a quoted passage"))

    if not bundle["limitations"]:
        out.append(finding("MISSING_LIMITATIONS", "limitations", "state at least one limitation"))
    return out


# --- Tools -------------------------------------------------------------------------

def canonical_hash():
    if "value" not in params:
        raise ToolError("INVALID_ARGUMENT", "value is required")
    try:
        raw = canonical_bytes(params["value"])
    except (ValueError, TypeError):
        raise ToolError("INVALID_ARGUMENT", "value cannot be hashed (NaN, infinity or a non-JSON type)")
    if len(raw) > MAX_BUNDLE_BYTES:
        raise ToolError("LIMIT_EXCEEDED", f"value exceeds {MAX_BUNDLE_BYTES} bytes")
    return {"result": {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}}


def validate_bundle():
    bundle = bundle_argument()
    found = schema_findings(bundle)
    return {"result": {"valid": not found, "findings": found}}


def verify_bundle():
    bundle = bundle_argument()
    found = schema_findings(bundle)
    if not found:
        found = consistency_findings(copy.deepcopy(bundle))
    errors = sum(1 for f in found if f["severity"] == "error")
    return {"result": {
        "consistent": errors == 0,
        "findings": found,
        "counts": {"errors": errors, "warnings": len(found) - errors},
        "bundle_sha256": sha256_of(bundle),
        "verification_scope": SCOPE,
    }}


HANDLERS = {
    "scievidence.canonical_hash": canonical_hash,
    "scievidence.validate_bundle": validate_bundle,
    "scievidence.verify_bundle": verify_bundle,
}


def main():
    handler = HANDLERS.get(tool_name)
    if handler is None:
        return {"error": f"Unknown tool: {tool_name}", "code": "UNKNOWN_TOOL"}
    return handler()


try:
    print(json.dumps(main()))
except ToolError as e:
    print(json.dumps({"error": e.message, "code": e.code}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}", "code": "INTERNAL_ERROR"}))
