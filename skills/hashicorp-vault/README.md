# HashiCorp Vault Skill

HashiCorp Vault integration for Sophon — check cluster health, browse secret engines and KV v2 secret keys, inspect secret metadata, read secret values, and review ACL policies. Authenticates with either a static Vault token or AppRole (role_id/secret_id).

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `vault.health` | None | Cluster health: initialized, sealed, standby, version, cluster name (non-200 health codes are normal results) |
| `vault.list_mounts` | Low | List enabled secret engines with path, type, description |
| `vault.list_secrets` | Low | List KV v2 secret key names under a path (names only, no values) |
| `vault.get_secret_metadata` | Low | KV v2 secret metadata: versions, timestamps, custom metadata (no values) |
| `vault.read_secret` | High | Read live secret VALUES (data + version info) into the agent context |
| `vault.list_policies` | Low | List ACL policy names, or fetch one policy's HCL |
| `vault.lookup_token` | None | Look up the current token: display name, policies, TTL, expire time |

## Setup

1. Decide how the skill should authenticate:
   - **Static token** — create a Vault token for the skill. **Strongly recommended:** unless you explicitly want `vault.read_secret` to return live secret values into the agent context, attach a policy scoped to `metadata`/`list` paths only (e.g. `path "secret/metadata/*" { capabilities = ["read", "list"] }`) so the token cannot read `secret/data/*`.
   - **AppRole** — enable the AppRole auth method (`vault auth enable approle`), create a role bound to a similarly scoped policy, and note its `role_id` and `secret_id`. The skill logs in at `/v1/auth/approle/login` and uses the returned client token.
2. Vault-side caveats (need Vault admin):
   - The token/role needs `read` on `auth/token/lookup-self` (default policy grants it) for the connection test.
   - `vault.list_mounts` requires `read` on `sys/mounts`; `vault.list_policies` requires `list`/`read` on `sys/policies/acl` — both are admin-ish paths, so omit them from the policy if you do not want the agent to see them.
   - Secret tools assume **KV version 2** mounts (paths use `/data/` and `/metadata/`). KV v1 mounts are not supported.
   - Vault Enterprise: if the skill should operate inside a namespace, note its path (e.g. `admin/team1`); it is sent as `X-Vault-Namespace` on every call.
   - Self-signed/private TLS: preferably use a properly issued certificate. Only as a last resort set **Skip TLS Verification** to `true` — this disables certificate checks and allows man-in-the-middle attacks.
3. Go to **Settings > Connections** in the Sophon Dashboard
4. Click **Connect** on the HashiCorp Vault card
5. Enter the Vault address (e.g. `https://vault.example.com:8200`) and either the token or the AppRole Role ID + Secret ID (plus namespace if applicable)
6. Test the connection

## Usage Examples

**Check cluster health:**
> "Is our Vault cluster sealed? Check its health."

**Browse secrets:**
> "List the secret engines in Vault, then list the keys under secret/apps"

**Inspect metadata:**
> "When was the secret secret/apps/web/db last updated and how many versions does it have?"

**Read a secret value:**
> "Read the current value of secret/apps/web/db from Vault"

**Review access:**
> "What policies does the Vault token have, and show me the HCL of the 'ci-readonly' policy"

## Requirements

- A reachable HashiCorp Vault server (OSS or Enterprise), unsealed and initialized
- A Vault token or AppRole credentials with policies covering the paths you want the agent to use
- KV secrets engine **version 2** for the secret tools
- Namespaces require Vault Enterprise

## Trademarks

HashiCorp and Vault are trademarks of HashiCorp, Inc. (an IBM company). This skill is an independent integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or sponsored by HashiCorp.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
