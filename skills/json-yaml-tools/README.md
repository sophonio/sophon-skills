# JSON / YAML Tools

Offline structured-data toolkit for Sophon: convert between JSON, YAML, and TOML; query documents
with [JMESPath](https://jmespath.org/); validate against [JSON Schema](https://json-schema.org/);
deep-merge documents; and pretty-print or minify.

Runs entirely locally in the sandbox — **no network access and no credentials**. Parsing and
serialization use PyYAML, `jmespath`, `jsonschema`, and the standard-library `json` / `tomllib`.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `data.convert` | none | Parse JSON/YAML/TOML and re-emit as JSON or YAML |
| `data.query` | none | Run a JMESPath expression against a JSON/YAML document |
| `data.validate` | none | Validate a JSON/YAML document against a JSON Schema |
| `data.merge` | low | Deep-merge two or more documents left-to-right (last wins) |
| `data.format` | none | Pretty-print or minify a JSON/YAML document |

## Inputs

Every read tool accepts the document as an inline string in `input`. Alternatively, pass
`inputPath` to read the document from a file (relative paths resolve against the working
directory, `/workspace` in the sandbox). `data.merge` takes an `inputs` array of document strings.

## Notes

- **TOML is read-only.** `data.convert` can read TOML (`from: "toml"`) but only writes JSON or
  YAML; `to: "toml"` returns `{"error": "toml output not supported"}` since adding a native TOML
  writer would pull in an out-of-band dependency.
- **Validation results are not errors.** `data.validate` returns `{"valid": true}` or
  `{"valid": false, "errors": [...]}` for a well-formed document that fails the schema. A `{"error":
  ...}` object is only returned for malformed input, a malformed schema, or a bad expression.
- **Merge semantics:** nested objects merge recursively; scalars and arrays from later inputs
  replace earlier ones.
- Each tool prints a single JSON object to stdout: `{"format", "output"}` for convert/merge/format,
  `{"result": ...}` for query, and the validity object for validate.
