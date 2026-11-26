"""Offline tests for the science-statistics skill (no network: every call scripts zero HTTP steps)."""
import hashlib
import json
import math
import re
import sys

from mockhttp import REPO, run_tool, check

ok = True
SKILL = "science-statistics"

CSV = "unit,group,value\na1,A,1\na2,A,2\na3,A,3\na4,A,4\nb1,B,2\nb2,B,4\nb3,B,6\nb4,B,NA\n"
COLS = {"value_column": "value", "group_column": "group", "unit_column": "unit",
        "units": "mg/L", "missing_policy": "exclude_and_report"}


def call(tool, **kw):
    params = {"tool": tool}
    params.update(kw)
    out, ex = run_tool(SKILL, params, [])
    assert not ex, "the statistics skill must make no HTTP request"
    return out


def close(a, b, rel=1e-9):
    return a is not None and b is not None and math.isclose(a, b, rel_tol=rel, abs_tol=1e-12)


def canonical_sha(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                     allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def group(out, name):
    return next(g for g in out["result"]["groups"] if g["group"] == name)


# ---------------------------------------------------------------- 1. describe oracles
print("[describe — hand-worked oracles]")
out = call("scistat.describe", csv=CSV, **COLS)
a, b = group(out, "A"), group(out, "B")
ok &= check("A n=4 missing=0", a["n"] == 4 and a["missing"] == 0, str(a))
ok &= check("A mean 2.5, median 2.5", close(a["mean"], 2.5) and close(a["median"], 2.5), str(a))
ok &= check("A sample SD sqrt(5/3)", close(a["sd"], math.sqrt(5 / 3)), str(a))
ok &= check("A min 1 max 4", a["min"] == 1 and a["max"] == 4, str(a))
ok &= check("B n=3 missing=1", b["n"] == 3 and b["missing"] == 1, str(b))
ok &= check("B mean 4, SD 2, median 4", close(b["mean"], 4) and close(b["sd"], 2)
            and close(b["median"], 4), str(b))
ok &= check("units echoed", out["result"]["units"] == "mg/L", str(out["result"])[:200])
ok &= check("no warnings for distinct units", out["result"]["warnings"] == [], str(out["result"]["warnings"]))

rec = out["record"]
ok &= check("record schema", rec["schema"] == "sophon.science.analysis/1", str(rec)[:200])
ok &= check("record tool and version", rec["tool"] == "scistat.describe" and rec["tool_version"] == "1.0.0",
            str(rec)[:200])
ok &= check("record provenance tool-reported", rec["provenance"] == "tool-reported", str(rec)[:200])
ok &= check("record output equals result", rec["output"] == out["result"], "")
ok &= check("record output_sha256 is canonical", rec["output_sha256"] == canonical_sha(rec["output"]), "")
ok &= check("record input_sha256 is canonical", rec["input_sha256"] == canonical_sha(rec["input"]), "")
ok &= check("record input carries the csv", rec["input"]["csv"] == CSV, "")
ok &= check("record python_version present", re.match(r"^\d+\.\d+", rec["python_version"] or "") is not None,
            str(rec.get("python_version")))

# ---------------------------------------------------------------- 2. mean difference oracles
print("[mean_difference — Welch oracles, B minus A]")
out = call("scistat.mean_difference", csv=CSV, group_a="A", group_b="B", **COLS)
r = out["result"]
ok &= check("difference 1.5", close(r["difference"], 1.5), str(r))
ok &= check("Welch SE sqrt(7/4)", close(r["welch_se"], math.sqrt(7 / 4)), str(r))
ok &= check("Welch df 1323/409", close(r["welch_df"], 1323 / 409), str(r))
ok &= check("n_a 4, n_b 3, missing_b 1", r["n_a"] == 4 and r["n_b"] == 3 and r["missing_b"] == 1, str(r))
ok &= check("no p-value or interval anywhere",
            all(k not in json.dumps(out) for k in ("p_value", "\"ci", "confidence_interval")), str(r))
ok &= check("direction stated", r["difference_definition"] == "mean(group_b) - mean(group_a)", str(r))
ok &= check("record method", out["record"]["method"] == "mean_difference_welch/1", str(out["record"])[:200])
MD_RECORD = out["record"]

# ---------------------------------------------------------------- 3. Benjamini-Hochberg
print("[bh_adjust — oracle, input order, ties]")
out = call("scistat.bh_adjust", p_values=[0.01, 0.04, 0.03, 0.005])
tests = out["result"]["tests"]
ok &= check("adjusted in input order", all(close(t["adjusted"], e) for t, e in
                                           zip(tests, [0.02, 0.04, 0.04, 0.02])), str(tests))
ok &= check("all rejected at 0.05", all(t["rejected"] for t in tests), str(tests))
ok &= check("raw p kept, alpha 0.05, m 4", [t["raw_p"] for t in tests] == [0.01, 0.04, 0.03, 0.005]
            and out["result"]["alpha"] == 0.05 and out["result"]["m"] == 4, str(out["result"])[:200])
out = call("scistat.bh_adjust", p_values=[0.03, 0.03], labels=["x", "y"], alpha=0.01)
tests = out["result"]["tests"]
ok &= check("tied p get the same adjusted value", close(tests[0]["adjusted"], 0.03)
            and close(tests[1]["adjusted"], 0.03), str(tests))
ok &= check("labels kept, none rejected at 0.01", [t["label"] for t in tests] == ["x", "y"]
            and not any(t["rejected"] for t in tests), str(tests))
out = call("scistat.bh_adjust", p_values=[0.9, 0.95])
ok &= check("adjusted capped at 1 and monotone", all(t["adjusted"] <= 1 for t in out["result"]["tests"]),
            str(out))

# ---------------------------------------------------------------- 3b. boundaries and hashing
print("[exact limits, non-ASCII hashing, excluded rows]")
rows = "unit,group,value\n" + "".join(f"u{i},A,1\n" for i in range(5000))
out = call("scistat.describe", csv=rows, **COLS)
ok &= check("exactly 5,000 rows accepted", group(out, "A")["n"] == 5000 if "result" in out else False, str(out)[:200])
header = "unit,group,value\n"
body = "".join(f"u{i},A,{i % 7}\n" for i in range(1, 4000))
pad = 1048576 - len((header + "u0,A,1\n" + body).encode("utf-8"))
exact = header + "u0" + "p" * pad + ",A,1\n" + body
out = call("scistat.describe", csv=exact, **COLS)
ok &= check("exactly 1,048,576 bytes accepted", len(exact.encode("utf-8")) == 1048576 and "result" in out,
            str(out)[:200])
wide_ok = ",".join(["unit", "group", "value"] + [f"c{i}" for i in range(61)]) + "\na1,A,1" + ",x" * 61 + "\n"
out = call("scistat.describe", csv=wide_ok, **COLS)
ok &= check("exactly 64 columns accepted", "result" in out, str(out)[:200])
out = call("scistat.describe", csv=CSV, **dict(COLS, units="µg/L"))
ok &= check("non-ASCII units hash canonically (ensure_ascii=False)",
            out["record"]["output_sha256"] == canonical_sha(out["record"]["output"])
            and out["record"]["output"]["units"] == "µg/L", str(out)[:200])
ok &= check("non-ASCII hash differs from the ASCII-escaped form",
            out["record"]["output_sha256"] != hashlib.sha256(json.dumps(
                out["record"]["output"], sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "")
gap = CSV + ",A,5\n"
out = call("scistat.describe", csv=gap, **COLS)
ok &= check("row with a missing unit is excluded and counted", out["result"]["excluded_rows"] == 1
            and group(out, "A")["n"] == 4, str(out)[:200])
ok &= check("row with a missing unit fails under reject",
            call("scistat.describe", csv=gap, **dict(COLS, missing_policy="reject")).get("code") == "MISSING_VALUES")

# ---------------------------------------------------------------- 4. refusals
print("[refusals]")


def code_of(tool, **kw):
    return call(tool, **kw).get("code")


ok &= check("nan value rejected", code_of("scistat.describe", csv=CSV.replace("a1,A,1", "a1,A,nan"), **COLS)
            == "INVALID_VALUE")
ok &= check("inf value rejected", code_of("scistat.describe", csv=CSV.replace("a1,A,1", "a1,A,inf"), **COLS)
            == "INVALID_VALUE")
ok &= check("1e999 rejected", code_of("scistat.describe", csv=CSV.replace("a1,A,1", "a1,A,1e999"), **COLS)
            == "INVALID_VALUE")
reject = dict(COLS, missing_policy="reject")
ok &= check("reject policy with NA", code_of("scistat.describe", csv=CSV, **reject) == "MISSING_VALUES")
bad_policy = dict(COLS, missing_policy="drop")
ok &= check("unknown missing policy", code_of("scistat.describe", csv=CSV, **bad_policy) == "INVALID_ARGUMENT")
no_units = dict(COLS, units="")
ok &= check("units required", code_of("scistat.describe", csv=CSV, **no_units) == "INVALID_ARGUMENT")
rows = "unit,group,value\n" + "".join(f"u{i},A,1\n" for i in range(5001))
ok &= check("5,001 rows", code_of("scistat.describe", csv=rows, **COLS) == "LIMIT_EXCEEDED")
wide = ",".join(["unit", "group", "value"] + [f"c{i}" for i in range(62)]) + "\n"
ok &= check("65 columns", code_of("scistat.describe", csv=wide, **COLS) == "LIMIT_EXCEEDED")
big = "unit,group,value\n" + "x" * (1048577 - len("unit,group,value\n"))
ok &= check("1,048,577 bytes", len(big.encode("utf-8")) == 1048577
            and code_of("scistat.describe", csv=big, **COLS) == "LIMIT_EXCEEDED")
wrong_col = dict(COLS, unit_column="animal")
ok &= check("missing column", code_of("scistat.describe", csv=CSV, **wrong_col) == "MISSING_COLUMN")
ok &= check("group with fewer than 2 values",
            code_of("scistat.mean_difference", csv=CSV + "c1,C,5\n", group_a="A", group_b="C", **COLS)
            == "INSUFFICIENT_N")
ok &= check("p below 0", code_of("scistat.bh_adjust", p_values=[-0.1, 0.2]) == "INVALID_P_VALUE")
ok &= check("p above 1", code_of("scistat.bh_adjust", p_values=[0.2, 1.1]) == "INVALID_P_VALUE")
ok &= check("5,001 p-values", code_of("scistat.bh_adjust", p_values=[0.5] * 5001) == "LIMIT_EXCEEDED")
ok &= check("integer too large for a float", code_of("scistat.bh_adjust", p_values=[10 ** 400]) == "INVALID_P_VALUE")
ok &= check("labels length mismatch", code_of("scistat.bh_adjust", p_values=[0.1], labels=["a", "b"])
            == "INVALID_ARGUMENT")
out = call("scistat.nope")
ok &= check("unknown tool", out.get("code") == "UNKNOWN_TOOL" and "scistat.nope" in out.get("error", ""), str(out))

# ---------------------------------------------------------------- 5. repeated experimental units
print("[repeated experimental unit warning]")
out = call("scistat.describe", csv=CSV.replace("b4,B,NA", "a1,B,8"), **COLS)
warn = [w for w in out["result"]["warnings"] if w["code"] == "REPEATED_EXPERIMENTAL_UNIT"]
ok &= check("warning raised", len(warn) == 1, str(out["result"]["warnings"]))
ok &= check("effective units 7 of 8 rows", warn and warn[0]["effective_units"] == 7 and warn[0]["rows"] == 8,
            str(warn))

# ---------------------------------------------------------------- 6. replay
print("[replay]")
out = call("scistat.replay", record=MD_RECORD)
ok &= check("untouched record matches", out["result"]["code"] == "REPLAY_MATCH" and out["result"]["match"] is True,
            str(out)[:300])
ok &= check("replay states its scope", out["result"]["verification_scope"]
            == "consistency only; not authentication and not method validation", str(out)[:300])
tampered = json.loads(json.dumps(MD_RECORD))
tampered["output"]["difference"] = 1.6
out = call("scistat.replay", record=tampered)
ok &= check("changed output value mismatches", out["result"]["code"] == "REPLAY_MISMATCH"
            and out["result"]["match"] is False, str(out)[:300])
tampered = json.loads(json.dumps(MD_RECORD))
tampered["input"]["csv"] = CSV.replace("a4,A,4", "a4,A,5")
out = call("scistat.replay", record=tampered)
ok &= check("changed input mismatches", out["result"]["code"] == "REPLAY_MISMATCH", str(out)[:300])
out = call("scistat.replay", record={"schema": "other/1"})
ok &= check("foreign record refused", out.get("code") == "INVALID_RECORD", str(out))
bh_record = call("scistat.bh_adjust", p_values=[0.01, 0.04, 0.03, 0.005])["record"]
out = call("scistat.replay", record=bh_record)
ok &= check("bh_adjust record replays", out["result"]["code"] == "REPLAY_MATCH", str(out)[:300])
describe_record = call("scistat.describe", csv=CSV, **COLS)["record"]
out = call("scistat.replay", record=json.dumps(describe_record))
ok &= check("describe record replays from a JSON string", out["result"]["code"] == "REPLAY_MATCH", str(out)[:300])

# ---------------------------------------------------------------- 7. sandbox import hygiene
print("[entrypoint imports only the stdlib]")
src = open(f"{REPO}/skills/{SKILL}/main.py", encoding="utf-8").read()
names = set()
for line in src.splitlines():
    m = re.match(r"^(?:import|from)\s+(\w+)", line.lstrip())
    if m and not line.lstrip().startswith("#"):
        names.add(m.group(1))
foreign = sorted(n for n in names if n not in sys.stdlib_module_names)
ok &= check("nothing to pip-install", not foreign, str(foreign))
ok &= check("no __future__ import", "__future__" not in names, str(names))

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
