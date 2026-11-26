"""Science statistics: bounded descriptive statistics with replayable analysis records.

Runs fully local in the Sophon Python sandbox: no network, no credentials, standard library only.
`params` is injected as a global by the Sophon runtime and carries the tool name and its arguments.

Every successful call returns {"result": ..., "record": ...}. The record holds the exact input, the
parameters, the output and canonical SHA-256 hashes of input and output, so scistat.replay can
recompute the registered method later. Records are tool-reported: they show consistency, they do
not authenticate execution and they do not validate the choice of method. No p-values, confidence
intervals or causal statements are produced.
"""

import csv
import hashlib
import io
import json
import math
import platform
import re

tool_name = params.get("tool", "")

TOOL_VERSION = "1.0.0"
RECORD_SCHEMA = "sophon.science.analysis/1"
SCOPE = "consistency only; not authentication and not method validation"
MAX_PAYLOAD_BYTES = 1048576
MAX_ROWS = 5000
MAX_COLUMNS = 64
MAX_P_VALUES = 5000
MISSING_TOKENS = ("", "NA")
POLICIES = ("exclude_and_report", "reject")
NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")

# The whole payload is capped at MAX_PAYLOAD_BYTES, so one field may use all of it.
csv.field_size_limit(MAX_PAYLOAD_BYTES)


class ToolError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


# --- Canonical hashing ---------------------------------------------------------

def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256_of(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


# --- Argument helpers ----------------------------------------------------------

def required_text(args, name):
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ToolError("INVALID_ARGUMENT", f"{name} is required and must be a non-empty string")
    return value


def finite(x):
    if isinstance(x, float) and not math.isfinite(x):
        raise ToolError("NUMERIC_OVERFLOW", "a result is not a finite number")
    return x


def check_finite_tree(value):
    if isinstance(value, dict):
        for v in value.values():
            check_finite_tree(v)
    elif isinstance(value, list):
        for v in value:
            check_finite_tree(v)
    else:
        finite(value)


# --- Table parsing -------------------------------------------------------------

def table_input(args):
    text = args.get("csv")
    if not isinstance(text, str) or not text.strip():
        raise ToolError("INVALID_ARGUMENT", "csv is required and must be non-empty text")
    if len(text.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ToolError("LIMIT_EXCEEDED", f"csv exceeds {MAX_PAYLOAD_BYTES} bytes")
    return {
        "csv": text,
        "value_column": required_text(args, "value_column"),
        "group_column": required_text(args, "group_column"),
        "unit_column": required_text(args, "unit_column"),
    }


def table_parameters(args):
    policy = args.get("missing_policy")
    if policy not in POLICIES:
        raise ToolError("INVALID_ARGUMENT", "missing_policy must be one of: " + ", ".join(POLICIES))
    return {"units": required_text(args, "units"), "missing_policy": policy}


def parse_value(token):
    if not NUMBER_RE.match(token):
        raise ToolError("INVALID_VALUE", f"value {token!r} is not a finite decimal number")
    value = float(token)
    if not math.isfinite(value):
        raise ToolError("INVALID_VALUE", f"value {token!r} is not a finite number")
    return value


def read_rows(inp, params_):
    text = inp["csv"]
    if text.startswith("\ufeff"):
        text = text[1:]
    try:
        reader = csv.reader(io.StringIO(text, newline=""))
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]
    except csv.Error as e:
        raise ToolError("MALFORMED_CSV", f"csv could not be parsed: {e}")
    if not rows:
        raise ToolError("MALFORMED_CSV", "csv has no header row")
    header = [h.strip() for h in rows[0]]
    if len(header) > MAX_COLUMNS:
        raise ToolError("LIMIT_EXCEEDED", f"csv has {len(header)} columns; the limit is {MAX_COLUMNS}")
    data = rows[1:]
    if len(data) > MAX_ROWS:
        raise ToolError("LIMIT_EXCEEDED", f"csv has {len(data)} data rows; the limit is {MAX_ROWS}")
    index = {}
    for key in ("value_column", "group_column", "unit_column"):
        name = inp[key]
        if name not in header:
            raise ToolError("MISSING_COLUMN", f"column {name!r} ({key}) is not in the header")
        index[key] = header.index(name)
    reject = params_["missing_policy"] == "reject"
    parsed = []
    excluded = 0
    for line_no, row in enumerate(data, start=2):
        if len(row) != len(header):
            raise ToolError("MALFORMED_CSV", f"row {line_no} has {len(row)} fields; the header has {len(header)}")
        group = row[index["group_column"]].strip()
        unit = row[index["unit_column"]].strip()
        raw = row[index["value_column"]].strip()
        if group in MISSING_TOKENS or unit in MISSING_TOKENS:
            if reject:
                raise ToolError("MISSING_VALUES", f"row {line_no} has a missing group or experimental unit")
            excluded += 1
            continue
        if raw in MISSING_TOKENS:
            if reject:
                raise ToolError("MISSING_VALUES", f"row {line_no} has a missing value")
            value = None
        else:
            value = parse_value(raw)
        parsed.append({"group": group, "unit": unit, "value": value})
    return parsed, excluded


def unit_warnings(rows):
    units = [r["unit"] for r in rows]
    distinct = len(set(units))
    if distinct < len(units):
        return [{
            "code": "REPEATED_EXPERIMENTAL_UNIT",
            "rows": len(units),
            "effective_units": distinct,
            "message": ("Some experimental units appear in more than one row. These statistics treat "
                        "rows as independent; they are not valid for repeated measures without "
                        "aggregating to one value per unit."),
        }]
    return []


# --- Statistics ----------------------------------------------------------------

def mean(values):
    return math.fsum(values) / len(values)


def sample_variance(values):
    m = mean(values)
    return math.fsum((v - m) ** 2 for v in values) / (len(values) - 1)


def median(values):
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def summarize(name, values, missing):
    n = len(values)
    return {
        "group": name,
        "n": n,
        "missing": missing,
        "mean": mean(values) if n else None,
        "sd": math.sqrt(sample_variance(values)) if n >= 2 else None,
        "median": median(values) if n else None,
        "min": min(values) if n else None,
        "max": max(values) if n else None,
    }


def split_groups(rows):
    groups = {}
    for r in rows:
        g = groups.setdefault(r["group"], {"values": [], "missing": 0})
        if r["value"] is None:
            g["missing"] += 1
        else:
            g["values"].append(r["value"])
    return groups


def compute_describe(inp, params_):
    rows, excluded = read_rows(inp, params_)
    if not rows:
        raise ToolError("INSUFFICIENT_N", "no rows remain after excluding missing groups or units")
    groups = split_groups(rows)
    return {
        "units": params_["units"],
        "value_column": inp["value_column"],
        "groups": [summarize(name, groups[name]["values"], groups[name]["missing"]) for name in sorted(groups)],
        "excluded_rows": excluded,
        "warnings": unit_warnings(rows),
    }


def compute_mean_difference(inp, params_):
    group_a, group_b = params_["group_a"], params_["group_b"]
    rows, excluded = read_rows(inp, params_)
    used = [r for r in rows if r["group"] in (group_a, group_b)]
    groups = split_groups(used)
    for name in (group_a, group_b):
        if name not in groups or len(groups[name]["values"]) < 2:
            raise ToolError("INSUFFICIENT_N", f"group {name!r} needs at least 2 values")
    va, vb = groups[group_a]["values"], groups[group_b]["values"]
    na, nb = len(va), len(vb)
    sa, sb = sample_variance(va) / na, sample_variance(vb) / nb
    se = math.sqrt(sa + sb)
    denom = sa ** 2 / (na - 1) + sb ** 2 / (nb - 1)
    df = (sa + sb) ** 2 / denom if denom > 0 else None
    return {
        "units": params_["units"],
        "value_column": inp["value_column"],
        "group_a": group_a,
        "group_b": group_b,
        "n_a": na,
        "n_b": nb,
        "missing_a": groups[group_a]["missing"],
        "missing_b": groups[group_b]["missing"],
        "mean_a": mean(va),
        "mean_b": mean(vb),
        "difference": mean(vb) - mean(va),
        "difference_definition": "mean(group_b) - mean(group_a)",
        "welch_se": se,
        "welch_df": df,
        "excluded_rows": excluded,
        "other_rows": len(rows) - len(used),
        "warnings": unit_warnings(used),
        "note": ("No p-value or confidence interval is computed. The difference describes these "
                 "samples only and is not evidence of a cause."),
    }


def bh_input(args):
    p_values = args.get("p_values")
    if not isinstance(p_values, list) or not p_values:
        raise ToolError("INVALID_ARGUMENT", "p_values must be a non-empty list of numbers")
    if len(p_values) > MAX_P_VALUES:
        raise ToolError("LIMIT_EXCEEDED", f"{len(p_values)} p-values; the limit is {MAX_P_VALUES}")
    for i, p in enumerate(p_values):
        if isinstance(p, bool) or not isinstance(p, (int, float)):
            raise ToolError("INVALID_P_VALUE", f"p_values[{i}] is not a number")
        try:
            in_range = math.isfinite(p) and 0 <= p <= 1
        except OverflowError:
            in_range = False
        if not in_range:
            raise ToolError("INVALID_P_VALUE", f"p_values[{i}] = {p!r} is outside [0, 1]")
    labels = args.get("labels")
    if labels is not None:
        if (not isinstance(labels, list) or len(labels) != len(p_values)
                or not all(isinstance(x, str) for x in labels)):
            raise ToolError("INVALID_ARGUMENT", "labels must be a list of strings, one per p-value")
    return {"p_values": [float(p) for p in p_values], "labels": labels}


def bh_parameters(args):
    alpha = args.get("alpha", 0.05)
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not 0 < alpha < 1:
        raise ToolError("INVALID_ARGUMENT", "alpha must be a number between 0 and 1 (exclusive)")
    return {"alpha": float(alpha)}


def compute_bh(inp, params_):
    p = inp["p_values"]
    labels = inp["labels"]
    m = len(p)
    order = sorted(range(m), key=lambda i: (p[i], i))
    adjusted = [0.0] * m
    running = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, p[i] * m / rank)
        adjusted[i] = running
    return {
        "m": m,
        "alpha": params_["alpha"],
        "method": "Benjamini-Hochberg step-up false discovery rate adjustment of supplied p-values",
        "tests": [{
            "index": i,
            "label": labels[i] if labels else None,
            "raw_p": p[i],
            "adjusted": adjusted[i],
            "rejected": adjusted[i] <= params_["alpha"],
        } for i in range(m)],
    }


# --- Records and tools ---------------------------------------------------------

def mean_difference_parameters(args):
    out = table_parameters(args)
    out["group_a"] = required_text(args, "group_a")
    out["group_b"] = required_text(args, "group_b")
    if out["group_a"] == out["group_b"]:
        raise ToolError("INVALID_ARGUMENT", "group_a and group_b must differ")
    return out


METHODS = {
    "scistat.describe": ("describe/1", table_input, table_parameters, compute_describe),
    "scistat.mean_difference": ("mean_difference_welch/1", table_input, mean_difference_parameters,
                                compute_mean_difference),
    "scistat.bh_adjust": ("benjamini_hochberg/1", bh_input, bh_parameters, compute_bh),
}


def run_method(name, inp, params_):
    compute = METHODS[name][3]
    try:
        output = compute(inp, params_)
    except OverflowError:
        raise ToolError("NUMERIC_OVERFLOW", "a calculation overflowed the floating-point range")
    check_finite_tree(output)
    return output


def analysis_tool(name):
    method, get_input, get_params, _ = METHODS[name]
    inp = get_input(params)
    params_ = get_params(params)
    output = run_method(name, inp, params_)
    record = {
        "schema": RECORD_SCHEMA,
        "tool": name,
        "tool_version": TOOL_VERSION,
        "method": method,
        "parameters": params_,
        "input": inp,
        "input_sha256": sha256_of(inp),
        "output": output,
        "output_sha256": sha256_of(output),
        "python_version": platform.python_version(),
        "provenance": "tool-reported",
    }
    return {"result": output, "record": record}


def replay():
    record = params.get("record")
    if isinstance(record, str):
        try:
            record = json.loads(record)
        except ValueError:
            raise ToolError("INVALID_RECORD", "record is not valid JSON")
    if not isinstance(record, dict) or record.get("schema") != RECORD_SCHEMA:
        raise ToolError("INVALID_RECORD", f"record must be an object with schema {RECORD_SCHEMA}")
    name = record.get("tool")
    if name not in METHODS or record.get("method") != METHODS[name][0]:
        raise ToolError("INVALID_RECORD", "record names a tool or method this skill does not register")
    for key in ("input", "parameters", "output"):
        if not isinstance(record.get(key), dict):
            raise ToolError("INVALID_RECORD", f"record.{key} must be an object")
    mismatches = []
    try:
        if sha256_of(record["input"]) != record.get("input_sha256"):
            mismatches.append({"field": "input_sha256", "message": "the input does not match its recorded hash"})
        if sha256_of(record["output"]) != record.get("output_sha256"):
            mismatches.append({"field": "output_sha256", "message": "the output does not match its recorded hash"})
    except ValueError:
        raise ToolError("INVALID_RECORD", "record holds a value that cannot be hashed (NaN or infinity)")
    recomputed_sha = None
    try:
        recomputed = run_method(name, record["input"], record["parameters"])
        recomputed_sha = sha256_of(recomputed)
        if recomputed_sha != record.get("output_sha256"):
            mismatches.append({"field": "output", "message": "recomputing the method gives a different output"})
    except ToolError as e:
        mismatches.append({"field": "recompute", "message": f"{e.code}: {e.message}"})
    except (KeyError, TypeError) as e:
        mismatches.append({"field": "recompute", "message": f"the recorded input or parameters are incomplete: {e}"})
    match = not mismatches
    return {"result": {
        "code": "REPLAY_MATCH" if match else "REPLAY_MISMATCH",
        "match": match,
        "mismatches": mismatches,
        "tool": name,
        "method": record.get("method"),
        "recorded_output_sha256": record.get("output_sha256"),
        "recomputed_output_sha256": recomputed_sha,
        "recorded_python_version": record.get("python_version"),
        "replay_python_version": platform.python_version(),
        "verification_scope": SCOPE,
    }}


def main():
    if tool_name in METHODS:
        return analysis_tool(tool_name)
    if tool_name == "scistat.replay":
        return replay()
    return {"error": f"Unknown tool: {tool_name}", "code": "UNKNOWN_TOOL"}


try:
    print(json.dumps(main()))
except ToolError as e:
    print(json.dumps({"error": e.message, "code": e.code}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}", "code": "INTERNAL_ERROR"}))
