"""Regenerate the five standalone database skill packages."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "build" / "database_skill_template.py").read_text(encoding="utf-8")
LICENSE = (ROOT / "skills" / "sql-query" / "LICENSE").read_text(encoding="utf-8")

ENGINES = {
    "postgres": {
        "label": "PostgreSQL", "driver": "pg8000==1.31.5", "default_port": "5432",
        "target": "database", "tags": ["postgres", "postgresql", "sql", "database"],
    },
    "mssql": {
        "label": "Microsoft SQL Server", "driver": "python-tds==1.17.1", "default_port": "1433",
        "target": "database", "tags": ["mssql", "sql-server", "tsql", "database"],
    },
    "oracle": {
        "label": "Oracle Database", "driver": "oracledb==26.0.1", "default_port": "1521",
        "target": "serviceName", "tags": ["oracle", "sql", "database"],
    },
    "mysql": {
        "label": "MySQL and MariaDB", "driver": "PyMySQL==1.2.3", "default_port": "3306",
        "target": "database", "tags": ["mysql", "mariadb", "sql", "database"],
    },
    "sqlite": {
        "label": "SQLite", "driver": None, "default_port": None,
        "target": None, "tags": ["sqlite", "sql", "database", "file"],
    },
}


def field(key, label, kind="text", required=False, **extra):
    return {"key": key, "label": label, "type": kind, "required": required, **extra}


def tool(engine, suffix, description, risk, props=None, required=None, access="read"):
    properties = {"connectionId": {"type": "string", "description":
                                   "ID from db.list_connections; selects a named database connection"}}
    properties.update(props or {})
    return {
        "name": f"{engine}.{suffix}", "description": description, "riskLevel": risk,
        "databaseAccess": access,
        "parameters": {"type": "object", "properties": properties,
                       "required": ["connectionId", *(required or [])]},
    }


def manifest(engine, info):
    fields = []
    if engine != "sqlite":
        fields = [
            field("host", "Host", required=True),
            field("port", "Port", "number", placeholder=info["default_port"]),
            field(info["target"], "Service name" if engine == "oracle" else "Database", required=True),
            field("tlsMode", "TLS", "select", options=["verify", "disable"], required=True,
                  helpText="Use verify for certificate validation; disable only for a trusted local server."),
            field("readUsername", "Read username", required=True),
            field("readPassword", "Read password", "secret", required=True),
            field("writeUsername", "Write username"),
            field("writePassword", "Write password", "secret"),
        ]
    schema_props = {"schema": {"type": "string", "description": "Schema or owner; defaults to the engine's usual schema"}}
    table_props = {**schema_props, "table": {"type": "string", "description": "Unquoted table name"}}
    limit_prop = {"limit": {"type": "integer", "description": "Maximum rows: default 100, maximum 1000"}}
    tools = [tool(engine, "ping", "Test the selected database connection with SELECT 1.", "none")]
    if engine in ("postgres", "mssql", "oracle"):
        tools.append(tool(engine, "list_schemas", "List visible schemas or owners; use before choosing a table.",
                          "none", limit_prop))
    tools.extend([
        tool(engine, "list_tables", "List visible tables and views in the selected database or schema.",
             "none", {**(schema_props if engine in ("postgres", "mssql", "oracle") else {}), **limit_prop}),
        tool(engine, "describe_table", "Inspect columns, types, nullability, keys and relationships for a table.",
             "none", table_props if engine in ("postgres", "mssql", "oracle") else {"table": table_props["table"]},
             ["table"]),
        tool(engine, "query", "Run one SELECT query with the read-only identity. Inspect metadata first; do not guess column names.",
             "low", {"sql": {"type": "string", "description": "One SELECT statement in this engine's SQL dialect"},
                     **limit_prop}, ["sql"]),
        tool(engine, "execute", "Run one SQL statement with the separately configured write identity; may change or delete data or schema. Requires explicit user intent and approval.",
             "high", {"sql": {"type": "string", "description": "One SQL statement to execute"},
                      **limit_prop}, ["sql"], "write"),
    ])
    requirements = ["sqlglot==30.23.0"]
    if info["driver"]:
        requirements.append(info["driver"])
    if engine == "mssql":
        requirements.append("pyOpenSSL==26.4.0")
    return {
        "name": engine, "version": "1.0.0", "author": "Buildersoft LLC", "license": "MIT",
        "description": f"{info['label']} named database connections with schema discovery, read-only natural-language-assisted SQL queries, and separately approved write SQL.",
        "category": "data", "tags": info["tags"], "runtime": "sandbox", "language": "python",
        "entrypoint": "main.py",
        "integration": {
            "service": engine, "displayName": info["label"], "description":
            f"Connect named {info['label']} databases for schema-aware questions and SQL execution.",
            "icon": "database", "authType": "custom", "category": "integration",
            "connectionMode": "named", "fields": fields, "testEndpoint": "",
        },
        "tools": tools,
        "credentials": [] if engine == "sqlite" else [
            {"service": engine, "scopes": ["read", "write"], "required": True, "access": "injected"}],
        "requirements": requirements,
        "sandbox": {"network": engine != "sqlite", "timeoutSeconds": 30, "maxMemoryMb": 256},
        "platforms": [],
    }


def readme(engine, info):
    target = "an uploaded SQLite file" if engine == "sqlite" else "a named server connection"
    return f"""# {info['label']} database skill

Connect {target} to Sophon, inspect its schema, and answer questions using {info['label']} SQL.
The Sophon agent chooses the connection, reads table metadata, writes a query, and explains the
returned rows. The skill itself does not call a language model or sample rows automatically.

## Tools

`{engine}.ping` tests connectivity; `{engine}.list_tables` and `{engine}.describe_table` expose
catalog metadata; `{engine}.query` runs a single SELECT with the read-only identity; and
`{engine}.execute` runs a single statement with the optional write identity and is high risk.
{"`" + engine + ".list_schemas` lists visible schemas or owners.\n" if engine in ('postgres', 'mssql', 'oracle') else ''}
Every tool takes `connectionId` from `db.list_connections`. Queries return columns, rows,
`rowCount`, `truncated`, and `elapsedMs`; the default row limit is 100 and the maximum is 1,000.

## Connection

Create one or more named connections in Sophon's Connections settings. Server connections need
host, port, database or service name, verified TLS, and a database account with read-only grants.
To enable `{engine}.execute`, configure a separate write account. SQLite uses a managed uploaded
database file; Sophon mounts it read-only for read tools and writable only for the high-risk tool.
Credentials are stored in Sophon's vault, and only the selected role's credentials reach a call.

This integration supports password authentication in its first release. TLS verification is on
unless explicitly disabled for a trusted local server. The database server's own grants are the
final authority for which statements can run.

## Third-party software and trademarks

This skill uses the pinned Python dependencies in `manifest.json`. {info['label']} is a trademark
of its respective owner. This is an independent integration, not an official product of that owner.
"""


def main():
    for engine, info in ENGINES.items():
        directory = ROOT / "skills" / engine
        directory.mkdir(exist_ok=True)
        (directory / "main.py").write_text(TEMPLATE.replace("__ENGINE__", engine), encoding="utf-8")
        (directory / "manifest.json").write_text(json.dumps(manifest(engine, info), indent=2) + "\n", encoding="utf-8")
        (directory / "README.md").write_text(readme(engine, info), encoding="utf-8")
        (directory / "LICENSE").write_text(LICENSE, encoding="utf-8")


if __name__ == "__main__":
    main()
