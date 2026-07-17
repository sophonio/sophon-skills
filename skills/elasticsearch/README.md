# Elasticsearch Skill

Elasticsearch integration for Sophon — search with the Query DSL, run ES|QL queries, count and fetch documents, list indices, inspect mappings and cluster health, and index documents. Works with Elastic Cloud, Elastic serverless, self-managed Elasticsearch 8/9, and OpenSearch.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `es.search` | None | Search an index with the Query DSL (trimmed hits, totals, aggregations) |
| `es.esql_query` | None | Run an ES\|QL query (Elasticsearch 8.11+) |
| `es.count` | None | Count documents, optionally filtered by a query |
| `es.get_document` | None | Get a single document by index and id |
| `es.list_indices` | None | List indices with health, doc count, and store size |
| `es.get_mapping` | None | Get the field mappings (properties) of an index |
| `es.cluster_health` | None | Get cluster status, node counts, and shard statistics |
| `es.index_document` | Medium | Index (create or overwrite) a document |

## Setup

1. Find your cluster URL:
   - **Elastic Cloud / serverless**: in the Elastic Cloud console, copy the Elasticsearch endpoint of your deployment (e.g. `https://my-cluster.es.us-east-1.aws.elastic.cloud:443`).
   - **Self-managed / OpenSearch**: the REST API base URL, e.g. `https://es.internal.example.com:9200`.
2. Choose an auth method:
   - **API key (recommended for Elasticsearch)**: in Kibana, go to **Stack Management > Security > API Keys** and create an API key. Copy the **Base64/encoded** value (the `id:key` string) — that is what goes in the API Key field. See https://www.elastic.co/guide/en/kibana/current/api-keys.html.
   - **Basic auth (Elasticsearch or OpenSearch)**: use a username and password with read (and, for `es.index_document`, write) privileges on the indices you need. On OpenSearch, use basic auth — API keys are not supported there.
3. If your cluster uses a self-signed or private-CA TLS certificate (common on self-managed clusters), paste the CA certificate in PEM form into the **CA Certificate (PEM)** field. Only as a last resort, set **Skip TLS Verification** to `true` (not recommended — it disables certificate checking).
4. In Sophon, open **Settings > Connections**, click **Connect** on the Elasticsearch card, and fill in the Cluster URL plus either the API Key or the Username and Password (and the CA certificate if needed), then test the connection.

Note: AWS OpenSearch domains configured for IAM/SigV4-only authentication are not supported — this skill needs an API key or basic-auth (internal user database) access.

## Usage Examples

> "Search the logs-* indices for documents where message matches 'connection refused', newest first"

> "How many documents are in the orders index with status 'pending'?"

> "Run the ES|QL query: FROM logs-* | WHERE level == \"error\" | STATS count = COUNT() BY service | LIMIT 10"

> "List the indices in my Elasticsearch cluster and show the cluster health"

> "Index a document into the notes index with title 'Q3 planning' and body 'draft agenda'"

## Requirements

- An Elasticsearch cluster (Elastic Cloud, serverless, or self-managed 8/9) or an OpenSearch cluster reachable over HTTPS/HTTP
- An API key, or a user with read privileges on the indices you query (plus write/index privileges for `es.index_document`)
- `es.esql_query` requires Elasticsearch 8.11 or later (not available on OpenSearch)
- AWS OpenSearch domains in IAM/SigV4-only mode are not supported

## Trademarks

Elasticsearch is a trademark of Elasticsearch B.V. This project is not affiliated with or endorsed by Elasticsearch B.V. OpenSearch is a trademark of the OpenSearch Project. This project is not affiliated with or endorsed by the OpenSearch Project.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
