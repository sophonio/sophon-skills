# science-evidence

Checks that a scientific report's claims trace back to their evidence. Part of Sophon Science, with
`science-statistics` (analysis records) and `science-literature` (sources).

Offline and keyless: no network, no credentials, Python standard library only.

## Tools

| Tool | What it does |
|------|--------------|
| `scievidence.canonical_hash` | SHA-256 of a value's canonical JSON, the form every Sophon Science record uses |
| `scievidence.validate_bundle` | Schema check of an evidence bundle |
| `scievidence.verify_bundle` | Schema check plus consistency findings, the bundle hash and the verification scope |

## The evidence bundle (`sophon.science.evidence/1`)

| Field | Holds |
|-------|-------|
| `bundle_id`, `created_at`, `question` | What was asked, and when |
| `sources[]` | `id`, `provider`, `identifiers` (pmid, pmcid, doi), `title`, `retrieved_at`, `response_sha256`, `publication_kind` (`journal_article`, `preprint`, `unknown`), `retraction_status` (`retracted`, `not_flagged`, `unknown`), `license` |
| `analyses[]` | Analysis records from `science-statistics` (`sophon.science.analysis/1`), each with an `id` |
| `claims[]` | `id`, `text`, `kind` (`literature`, `numerical`, `interpretation`), `status` (`supported`, `unsupported`, `contested`, `unverified`), `supports[]` of `{source_id, quote, locator}`, `numbers[]` of `{value, analysis_id, path}` where `path` is a JSON Pointer into the analysis output |
| `reviews[]` | `id`, `reviewer`, `findings[]` |
| `limitations[]` | At least one stated limitation |

`not_flagged` means no retraction notice was found in the provider's data. It does not mean the
work was checked and found sound.

## Finding codes

Errors: `SCHEMA_INVALID`, `DUPLICATE_ID`, `DANGLING_REFERENCE`, `INPUT_HASH_MISMATCH`,
`OUTPUT_HASH_MISMATCH`, `NUMBER_MISMATCH` (relative tolerance 1e-9),
`NUMERICAL_CLAIM_WITHOUT_ANALYSIS`, `MISSING_QUOTE`, `RETRACTED_SUPPORT`, `MISSING_LIMITATIONS`.
Warning: `PREPRINT_SUPPORT`. A bundle is `consistent` when it has no errors.

Paths are JSON Pointers (RFC 6901): `~1` stands for `/`, `~0` for `~`, and array indexes are plain
non-negative integers without leading zeros. A pointer that does not resolve is a `DANGLING_REFERENCE`.

A whole call is refused, with `code` set and no findings, for `LIMIT_EXCEEDED` (over 1 MiB) and
`INVALID_ARGUMENT` (not a JSON object, malformed JSON, NaN or infinity).

## What verification does not mean

Every result states its scope: **consistency only; not authentication and not method validation.**

- Hashes are computed by the same kind of tool that wrote the record. A match shows only that each
  input and output agrees with its recorded hash: anyone who edits a value and recomputes its hash
  passes. They do not prove that a calculation ran; `scistat.replay` recomputes registered methods.
- A resolved citation with a quote does not prove the source supports the claim. A reviewer reads
  the quote in context.
- Whether the method suits the research question is a judgment for a reviewer and a domain expert.
- Nothing here is validated for clinical use.

## Limits

1 MiB per bundle or hashed value.

## License

MIT © Buildersoft LLC. See `LICENSE`.
