"""Offline JSON/YAML/TOML tools — convert, query, validate, merge, and format.

Runs fully local in the alpine Python sandbox: no network, no credentials. `params` is injected
as a global by the Sophon runtime and carries the tool name and the tool's call arguments.

Third-party parsers (PyYAML, jmespath, jsonschema) are imported lazily inside the handlers so
that argument-validation and unknown-tool errors return clean JSON without importing anything
that a call does not actually need.
"""

import json
import os

tool_name = params.get("tool", "")


def read_input():
    """Return the document text from params['input'] or, failing that, params['inputPath']."""
    text = params.get("input")
    if isinstance(text, str) and text != "":
        return text
    path = params.get("inputPath")
    if path:
        full = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
        if not os.path.isfile(full):
            raise ValueError(f"inputPath does not exist: {path}")
        with open(full, "r", encoding="utf-8") as fh:
            return fh.read()
    if isinstance(text, str):  # explicit empty string was provided
        return text
    raise ValueError("missing input: provide 'input' (string) or 'inputPath'")


def load(text, fmt):
    """Parse a document string in the given format into a Python object."""
    fmt = (fmt or "json").lower()
    if fmt == "json":
        return json.loads(text)
    if fmt == "yaml":
        import yaml
        try:
            return yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ValueError(f"YAML parse error: {exc}") from exc
    if fmt == "toml":
        import tomllib
        try:
            return tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f"TOML parse error: {exc}") from exc
    raise ValueError(f"unsupported format: {fmt}")


def dump(obj, fmt, minify=False):
    """Serialize a Python object to a string in the given output format."""
    fmt = (fmt or "json").lower()
    if fmt == "json":
        if minify:
            return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        return json.dumps(obj, ensure_ascii=False, indent=2)
    if fmt == "yaml":
        import yaml
        return yaml.safe_dump(
            obj,
            default_flow_style=bool(minify),
            sort_keys=False,
            allow_unicode=True,
        ).strip("\n") + "\n"
    raise ValueError(f"unsupported output format: {fmt}")


def deep_merge(base, overlay):
    """Recursively merge overlay into base. Nested dicts merge; everything else is replaced."""
    if isinstance(base, dict) and isinstance(overlay, dict):
        result = dict(base)
        for key, value in overlay.items():
            if key in result:
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    return overlay


# --- Tool handlers ---------------------------------------------------------

def convert():
    src = (params.get("from") or "").lower()
    dst = (params.get("to") or "").lower()
    if dst == "toml":
        print(json.dumps({"error": "toml output not supported"}))
        return
    if src not in ("json", "yaml", "toml"):
        raise ValueError("'from' must be one of: json, yaml, toml")
    if dst not in ("json", "yaml"):
        raise ValueError("'to' must be one of: json, yaml")
    obj = load(read_input(), src)
    print(json.dumps({"format": dst, "output": dump(obj, dst)}))


def query():
    import jmespath
    expression = params.get("expression")
    if not expression:
        raise ValueError("missing 'expression'")
    obj = load(read_input(), params.get("format", "json"))
    try:
        result = jmespath.search(expression, obj)
    except jmespath.exceptions.JMESPathError as exc:
        raise ValueError(f"invalid JMESPath expression: {exc}") from exc
    print(json.dumps({"result": result}))


def validate():
    import jsonschema
    raw_schema = params.get("schema")
    if not raw_schema:
        raise ValueError("missing 'schema'")
    try:
        schema = json.loads(raw_schema) if isinstance(raw_schema, str) else raw_schema
    except json.JSONDecodeError as exc:
        raise ValueError(f"schema is not valid JSON: {exc}") from exc

    obj = load(read_input(), params.get("format", "json"))

    validator_cls = jsonschema.validators.validator_for(schema)
    try:
        validator_cls.check_schema(schema)
    except jsonschema.exceptions.SchemaError as exc:
        raise ValueError(f"invalid JSON Schema: {exc.message}") from exc

    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(obj), key=lambda e: list(e.path))
    if not errors:
        print(json.dumps({"valid": True}))
        return
    print(json.dumps({
        "valid": False,
        "errors": [
            {
                "message": err.message,
                "path": "/".join(str(p) for p in err.path),
                "schemaPath": "/".join(str(p) for p in err.schema_path),
            }
            for err in errors
        ],
    }))


def merge():
    fmt = params.get("format", "json")
    inputs = params.get("inputs")
    if not isinstance(inputs, list) or len(inputs) < 1:
        raise ValueError("'inputs' must be a non-empty array of document strings")
    merged = None
    for idx, text in enumerate(inputs):
        obj = load(text, fmt)
        merged = obj if merged is None else deep_merge(merged, obj)
    print(json.dumps({"format": fmt, "output": dump(merged, fmt)}))


def format_doc():
    fmt = params.get("format", "json")
    action = (params.get("action") or "").lower()
    if action not in ("pretty", "minify"):
        raise ValueError("'action' must be one of: pretty, minify")
    obj = load(read_input(), fmt)
    print(json.dumps({"format": fmt, "output": dump(obj, fmt, minify=(action == "minify"))}))


HANDLERS = {
    "data.convert": convert,
    "data.query": query,
    "data.validate": validate,
    "data.merge": merge,
    "data.format": format_doc,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    else:
        handler()
except ValueError as e:
    print(json.dumps({"error": str(e)}))
except json.JSONDecodeError as e:
    print(json.dumps({"error": f"JSON parse error: {e}"}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
