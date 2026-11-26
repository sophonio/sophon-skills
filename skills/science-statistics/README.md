# science-statistics

Bounded, replayable descriptive statistics for scientific tables. Part of Sophon Science: each result
comes with an analysis record that the `science-evidence` skill can verify and that `scistat.replay`
can recompute later.

Offline and keyless: no network, no credentials, Python standard library only.

## Tools

| Tool | What it does |
|------|--------------|
| `scistat.describe` | Per-group n, missing count, mean, sample standard deviation, median, min and max of a CSV column |
| `scistat.mean_difference` | `mean(group_b) - mean(group_a)` with the Welch standard error and Welch-Satterthwaite degrees of freedom |
| `scistat.bh_adjust` | Benjamini-Hochberg false discovery rate adjustment of p-values you supply |
| `scistat.replay` | Recompute a result from its analysis record and report `REPLAY_MATCH` or `REPLAY_MISMATCH` |

## What you must state

The table tools refuse to run until you name:

- the **units** of the measured value;
- the **experimental-unit** column (the animal, patient, culture or plate a row belongs to);
- the **missing-value policy**, which applies to the value, group and experimental-unit cells only
  (other columns are not read): `exclude_and_report` counts empty and `NA` values and leaves them
  out, and drops rows with a missing group or unit (counted in `excluded_rows`); `reject` fails the
  call on any such missing cell.

Values must be finite decimal numbers: `nan`, `inf` and overflowing values are rejected. When an
experimental unit appears in more than one row, the result carries a `REPEATED_EXPERIMENTAL_UNIT`
warning with the number of distinct units: these statistics treat rows as independent.

## Limits

1 MiB of CSV, 5,000 data rows, 64 columns, 5,000 p-values per call.

## The analysis record

Every successful table or adjustment call returns `{"result": ..., "record": ...}`. The record
(`schema: sophon.science.analysis/1`) holds the tool and version, the method id, the parameters, the
exact input, the output, the SHA-256 of the canonical JSON of input and output, the Python version
and `"provenance": "tool-reported"`.

Canonical JSON is `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
allow_nan=False)` encoded as UTF-8.

## What this skill does not do

- It computes **no p-values, confidence intervals or causal claims**. A mean difference describes
  the samples; it is not evidence of a cause.
- A record is **tool-reported**: matching hashes show the record is internally consistent and that
  the registered method reproduces it. They do not authenticate that a calculation ran, and they do
  not show that the method suits the research question. That judgment stays with a reviewer and a
  domain expert.
- Results are **not validated for clinical use**, dosing or patient care.

## License

MIT © Buildersoft LLC. See `LICENSE`.
