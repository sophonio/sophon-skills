# Splunk Skill

Splunk integration for Sophon — run SPL searches (oneshot or as asynchronous jobs), fetch job results, list and dispatch saved searches, and list indexes via the Splunk management REST API using a static authentication token.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `splunk.oneshot_search` | Medium | Run an SPL search synchronously and return results immediately |
| `splunk.create_search_job` | Medium | Dispatch an SPL search as an asynchronous job and return its sid |
| `splunk.get_job_status` | None | Get dispatch state, progress, and counts for a search job |
| `splunk.get_job_results` | None | Fetch results of a completed job, with count/offset paging |
| `splunk.list_saved_searches` | None | List saved searches with their SPL and cron schedule |
| `splunk.run_saved_search` | Low | Dispatch a saved search by name and return its sid |
| `splunk.list_indexes` | None | List indexes with event counts and size on disk |

Search tools are rated Medium because SPL can invoke role-gated write commands (e.g. `outputlookup`, `collect`) depending on the token user's capabilities.

## Setup

1. **Enable token authentication** (Splunk Enterprise, admin required): in Splunk Web go to **Settings > Tokens** and click **Enable Token Authentication** if it is not already on.
2. **Create a token**: still under **Settings > Tokens**, click **New Token**, pick the user the token should act as, set an expiration, and copy the token value (a JWT). Tokens expire — plan to rotate them. Docs: https://docs.splunk.com/Documentation/Splunk/latest/Security/CreateAuthTokens
3. **Find your management API URL**: this is the management port (default `8089`), not the web UI port — e.g. `https://splunk.example.com:8089`.
4. **Splunk Cloud only**: the management API is not exposed by default. You must open a Splunk support case to enable REST API access, or use the Admin Config Service (`search-api/ipallowlists`) to allowlist your egress IPs. Free/trial Splunk Cloud stacks have no REST API access at all.
5. In Sophon, open **Settings > Connections**, click **Connect** on the Splunk card, and fill in:
   - **Management API URL** — e.g. `https://splunk.example.com:8089`
   - **Authentication Token** — the JWT from step 2
   - **Skip TLS Verification** — set to `true` only if your management port uses a self-signed certificate (common on default Splunk Enterprise installs); leave empty otherwise
6. Test the connection.

## Usage Examples

> "Search Splunk for errors in index=main over the last 24 hours"

> "Count events by host in the web index for the past week"

> "Start a Splunk search job for failed logins this month, then check its status and get the results"

> "List my Splunk saved searches and run the one called 'Daily Error Summary'"

> "Show me all Splunk indexes and how big they are"

## Requirements

- Splunk Enterprise or Splunk Cloud Platform with access to the management REST API (typically port 8089).
- Splunk Enterprise 9.0.1+ or Splunk Cloud Platform 9.0.2208+ (the skill uses the `search/v2` job endpoints).
- **Splunk Cloud does not expose the management API by default** — enabling it requires a support case or an Admin Config Service (`search-api/ipallowlists`) IP allowlist entry, and free trial stacks have no REST API access.
- Token authentication must be enabled by an administrator on Splunk Enterprise before tokens can be created.
- Authentication tokens expire and need rotation; the connection will start failing when the token lapses.
- The token's user needs the `search` capability plus access to the target indexes; write-capable SPL commands (e.g. `outputlookup`) additionally depend on that user's role capabilities.

## Trademarks

Splunk is a trademark of Splunk LLC (a Cisco company). This project is not affiliated with or endorsed by Splunk or Cisco.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
